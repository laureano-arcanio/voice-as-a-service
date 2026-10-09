"""API de inferencia: LLM, STT y TTS propios con una API key del cliente (docs/API_INFERENCIA.md).

Compatible con el SDK de OpenAI (base_url = `<app>/api/v1/inference`). Cada motor pide una key con
su alcance (`llm`, `stt`, `tts`) y cuenta contra los limites del tier del cliente: tokens, minutos y
pedidos por minuto (services/api_usage.py). Los agentes integrados no pasan por aca.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from ...config import settings
from ...services import api_usage, voices
from ...services.errors import ServiceError
from ...services.inference import InferenceGateway, get_gateway
from ..deps import DB, LlmAccess, SttAccess, TtsAccess, _bearer, inference_key
from ..routers.clients import inference_usage_out
from ..schemas import (
    ChatCompletionIn,
    InferenceModelsOut,
    InferenceUsageOut,
    SpeechIn,
    VoiceOut,
)

router = APIRouter(prefix="/inference", tags=["inference"])
Gateway = Annotated[InferenceGateway, Depends(get_gateway)]
Bearer = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]

LIMIT_RESPONSES = {401: {"description": "Sin API key valida"},
                   403: {"description": "La key no tiene ese motor (scope_missing) o el plan no lo incluye (not_in_plan)"},
                   429: {"description": "Pedidos por minuto (rate_limited) o cupo del mes agotado (api_*)"}}


@router.post("/chat/completions", responses={**LIMIT_RESPONSES, 200: {"description": "Chat completion de OpenAI, o SSE con stream=true"}})
async def chat_completions(body: ChatCompletionIn, access: LlmAccess, gateway: Gateway):
    """LLM. Requiere una key con alcance `llm`. Cuenta los tokens de entrada y de salida que informa el
    motor; `max_tokens` se achica a lo que le queda al cliente este mes. Con `stream=true` responde SSE
    y agrega el chunk final con `usage`."""
    return await gateway.chat(access, body.model_dump(exclude_none=True))


@router.post("/audio/transcriptions", responses=LIMIT_RESPONSES)
async def transcriptions(access: SttAccess, gateway: Gateway,
                         file: Annotated[UploadFile, File(description="Audio (wav, mp3, flac, ogg...)")],
                         model: Annotated[str | None, Form()] = None,
                         language: Annotated[str | None, Form()] = None,
                         response_format: Annotated[str, Form(description="json, text o verbose_json")] = "json"):
    """STT. Requiere una key con alcance `stt`. Cuenta los segundos de audio transcripto."""
    limit = settings.inference_stt_max_bytes
    audio = await file.read(limit + 1)
    if len(audio) > limit:
        raise ServiceError(f"El audio supera los {limit // (1024 * 1024)} MB", "payload_too_large")
    return await gateway.transcribe(access, audio, file.filename, file.content_type, language, response_format)


@router.post("/audio/speech", response_class=StreamingResponse,
             responses={**LIMIT_RESPONSES, 200: {"content": {"audio/wav": {}, "audio/pcm": {}, "text/event-stream": {}}}})
async def speech(body: SpeechIn, access: TtsAccess, gateway: Gateway):
    """TTS. Requiere una key con alcance `tts`. `response_format=wav` (default) devuelve el archivo completo;
    `pcm` (24 kHz, mono, 16 bits) se transmite a medida que se sintetiza, y con `stream_format=sse` llega como
    eventos `speech.audio.delta` (audio en base64) y un `speech.audio.done` final. Cuenta los segundos
    sintetizados, también si el cliente corta el stream."""
    return await gateway.speech(access, body.voice, body.input, body.response_format, body.stream_format)


@router.get("/models", response_model=InferenceModelsOut)
def models(db: DB, creds: Bearer, gateway: Gateway):
    """Los modelos que sirve la plataforma (el campo `model` de los pedidos se ignora)."""
    inference_key(db, creds, None)
    return {"data": gateway.models()}


@router.get("/voices", response_model=list[VoiceOut])
def list_voices(db: DB, creds: Bearer, genero: str | None = None, wer_max: float | None = None,
                car_min: float | None = None, car_max: float | None = None):
    """Voces del TTS para el campo `voice` de /audio/speech, de menor a mayor WER. Requiere alcance `tts`."""
    inference_key(db, creds, "tts")
    return voices.search(genero or None, wer_max, car_min, car_max)


@router.get("/usage", response_model=InferenceUsageOut)
def usage(db: DB, creds: Bearer,
          month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")] = None):
    """Consumo del mes del cliente de la key contra los limites de su tier. Consultarlo no gasta cupo."""
    _, client = inference_key(db, creds, None)
    return inference_usage_out(api_usage.usage(db, client, month))
