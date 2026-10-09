"""API de inferencia: LLM, STT y TTS propios detras de una API key del cliente.

Compatible con la API de OpenAI (`/chat/completions`, `/audio/transcriptions`, `/audio/speech`):
sirve el SDK de OpenAI apuntado a `/api/v1/inference`. La app autentica la key, aplica los limites
del tier (services/api_usage.py), reenvia al motor con la clave interna (VLLM_API_KEY) y suma lo
consumido: tokens que informa el LLM, y segundos de audio que informa el STT o que miden los bytes
del TTS. Los agentes integrados (llamadas, WhatsApp) no pasan por aca.

Cada pedido usa su propio cliente HTTP y su propia sesion de base (el consumo se registra al
terminar, tambien en un stream que el cliente corta); en los tests se inyecta un transporte falso.
"""
import json
import logging
import struct
from collections.abc import AsyncIterator
from functools import cache

import anyio
import httpx
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import get_sessionmaker
from . import api_usage, voices
from .errors import Invalid, ServiceError, Upstream

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 3        # estimacion cuando el motor no informa el uso (stream cortado)
WAV_HEADER_BYTES = 44
PCM_SAMPLE_RATE = 24_000   # Qwen3-TTS: 24 kHz, mono, 16 bits
TTS_FORMATS = ("wav", "pcm")
STT_FORMATS = ("json", "text", "verbose_json")
# Lo unico que se reenvia al LLM: el resto (guided_*, chat_template_kwargs, logprobs...) lo fija
# la plataforma o no se admite.
CHAT_PARAMS = ("messages", "temperature", "top_p", "stop", "seed", "presence_penalty", "frequency_penalty",
               "response_format", "tools", "tool_choice")


def _message(text: str) -> str:
    """El mensaje de error de un motor ({"error": {"message"}}, {"detail"} o texto plano)."""
    try:
        body = json.loads(text)
    except ValueError:
        return text.strip()[:300]
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])[:300]
        if body.get("detail"):
            return str(body["detail"])[:300]
    return text.strip()[:300]


def _upstream_error(engine: str, status: int, text: str) -> ServiceError:
    """El motor rechazo el pedido. Un 4xx de pedido invalido (texto largo, formato) vuelve como 400
    con su mensaje; lo demas (caido, nuestra clave interna, saturado) es 502 sin detalles."""
    if status in (400, 404, 413, 422):
        return ServiceError(f"El motor {engine} rechazó el pedido: {_message(text)}", "upstream_rejected")
    logger.warning("inferencia %s: el motor respondio %s: %s", engine, status, text[:300])
    return Upstream(f"El motor {engine} no está disponible ({status})", "upstream_error")


def _positive_int(value, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise Invalid(f"{name} tiene que ser un entero positivo", "invalid_request")
    return value


class InferenceGateway:
    def __init__(self, sessions: sessionmaker[Session], transport: httpx.AsyncBaseTransport | None = None):
        self.sessions = sessions
        self.transport = transport

    # ---------- comun ----------

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=httpx.Timeout(settings.inference_timeout_seconds, connect=5),
                                 transport=self.transport)

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.vllm_api_key}"}

    def _record_sync(self, access, **deltas) -> None:
        with self.sessions() as s:
            api_usage.record(s, access.client.id, access.key.id, **deltas)

    async def _record(self, access, **deltas) -> None:
        # Blindado: en un stream que el cliente corta, la tarea se cancela y el consumo igual se anota.
        with anyio.CancelScope(shield=True):
            try:
                await anyio.to_thread.run_sync(lambda: self._record_sync(access, **deltas))
            except Exception:
                logger.exception("no se pudo registrar el consumo de la API de %s", access.client.slug)

    # ---------- LLM ----------

    def _chat_request(self, body: dict, access) -> dict:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
            raise Invalid("messages tiene que ser una lista con al menos un mensaje", "invalid_request")
        if body.get("n") not in (None, 1):
            raise Invalid("Solo se admite n=1", "invalid_request")
        upstream = {k: body[k] for k in CHAT_PARAMS if body.get(k) is not None}
        cap = settings.inference_llm_max_tokens
        requested = _positive_int(body.get("max_completion_tokens"), "max_completion_tokens") \
            or _positive_int(body.get("max_tokens"), "max_tokens")
        max_tokens = min(requested or cap, cap)
        left = access.remaining.llm_output_tokens
        if left is not None:   # el pedido no puede generar mas de lo que le queda al cliente este mes
            max_tokens = max(min(max_tokens, left), 1)
        upstream |= {"model": settings.vllm_llm_model, "max_tokens": max_tokens, "stream": bool(body.get("stream")),
                     "chat_template_kwargs": {"enable_thinking": settings.llm_thinking}}
        if upstream["stream"]:
            upstream["stream_options"] = {"include_usage": True}   # sin esto vLLM no informa los tokens
        return upstream

    @staticmethod
    def _prompt_estimate(messages: list[dict]) -> int:
        chars = sum(len(json.dumps(m.get("content", ""), ensure_ascii=False)) for m in messages)
        return chars // CHARS_PER_TOKEN + 1

    async def chat(self, access, body: dict):
        upstream = self._chat_request(body, access)
        url = f"{settings.vllm_llm_base_url}/chat/completions"
        http = self._http()
        try:
            if not upstream["stream"]:
                async with http:
                    r = await http.post(url, json=upstream, headers=self._headers())
                if r.status_code != 200:
                    raise _upstream_error("LLM", r.status_code, r.text)
                data = r.json()
                usage = data.get("usage") or {}
                await self._record(
                    access, llm_requests=1,
                    llm_input_tokens=int(usage.get("prompt_tokens") or self._prompt_estimate(upstream["messages"])),
                    llm_output_tokens=int(usage.get("completion_tokens") or 0))
                return JSONResponse(data)
            response = await http.send(http.build_request("POST", url, json=upstream, headers=self._headers()),
                                       stream=True)
        except httpx.HTTPError as e:
            await http.aclose()
            raise Upstream(f"El motor LLM no responde: {type(e).__name__}", "upstream_error") from e
        except BaseException:
            await http.aclose()
            raise
        if response.status_code != 200:
            text = (await response.aread()).decode(errors="replace")
            await response.aclose()
            await http.aclose()
            raise _upstream_error("LLM", response.status_code, text)
        return StreamingResponse(self._chat_stream(access, upstream, http, response), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    async def _chat_stream(self, access, upstream: dict, http: httpx.AsyncClient,
                           response: httpx.Response) -> AsyncIterator[bytes]:
        """Reenvia el SSE tal cual y lee el chunk final con `usage`. Si el stream se corta antes,
        estima: los tokens de salida como los chunks con contenido y los de entrada por caracteres."""
        usage: dict | None = None
        chunks = 0
        tail = b""
        try:
            async for data in response.aiter_bytes():
                yield data
                lines = (tail + data).split(b"\n")
                tail = lines.pop()
                for line in lines:
                    if not line.startswith(b"data:") or b"[DONE]" in line:
                        continue
                    if b'"usage":{' in line or b'"usage": {' in line:
                        try:
                            found = json.loads(line[5:]).get("usage")
                        except ValueError:
                            found = None
                        usage = found or usage
                    elif b'"content"' in line:
                        chunks += 1
        except httpx.HTTPError as e:
            logger.warning("inferencia LLM: stream cortado: %s", type(e).__name__)
        finally:
            await response.aclose()
            await http.aclose()
            usage = usage or {}
            await self._record(
                access, llm_requests=1,
                llm_input_tokens=int(usage.get("prompt_tokens") or self._prompt_estimate(upstream["messages"])),
                llm_output_tokens=int(usage.get("completion_tokens") or chunks))

    # ---------- STT ----------

    async def transcribe(self, access, audio: bytes, filename: str | None, content_type: str | None,
                         language: str | None, response_format: str):
        if response_format not in STT_FORMATS:
            raise Invalid(f"response_format no soportado: {response_format} (usá {', '.join(STT_FORMATS)})",
                          "invalid_request")
        if not audio:
            raise Invalid("El archivo de audio está vacío", "invalid_request")
        form = {"model": settings.vllm_stt_model, "response_format": "verbose_json"}   # verbose: trae la duracion
        if language:
            form["language"] = language
        files = {"file": (filename or "audio", audio, content_type or "application/octet-stream")}
        try:
            async with self._http() as http:
                r = await http.post(f"{settings.vllm_stt_base_url}/audio/transcriptions", data=form, files=files,
                                    headers=self._headers())
        except httpx.HTTPError as e:
            raise Upstream(f"El motor STT no responde: {type(e).__name__}", "upstream_error") from e
        if r.status_code != 200:
            raise _upstream_error("STT", r.status_code, r.text)
        result = r.json()
        seconds = float(result.get("duration") or 0)
        await self._record(access, stt_requests=1, stt_seconds=seconds)
        text = result.get("text", "")
        if response_format == "text":
            return PlainTextResponse(text)
        if response_format == "verbose_json":
            return JSONResponse({**result, "language": result.get("language") or language, "duration": seconds})
        return JSONResponse({"text": text, "usage": {"type": "duration", "seconds": round(seconds, 3)}})

    # ---------- TTS ----------

    async def speech(self, access, voice: str, text: str, response_format: str):
        voice = voice.strip().lower()
        # Una voz que el checkpoint no tiene mata el engine de vllm-tts (AGENTS.md): solo las del catalogo.
        if voice not in voices.catalog():
            raise Invalid(f"Voz inexistente: {voice}. Las disponibles están en GET /api/v1/inference/voices",
                          "invalid_voice")
        text = text.strip()
        if not text:
            raise Invalid("input vacío", "invalid_request")
        if len(text) > settings.inference_tts_max_chars:
            raise Invalid(f"input de más de {settings.inference_tts_max_chars} caracteres: partilo en pedidos más "
                          "cortos", "invalid_request")
        if response_format not in TTS_FORMATS:
            raise Invalid(f"response_format no soportado: {response_format} (usá {', '.join(TTS_FORMATS)})",
                          "invalid_request")
        body = {"model": settings.vllm_tts_model, "voice": voice, "input": text, "response_format": response_format}
        http = self._http()
        try:
            response = await http.send(
                http.build_request("POST", f"{settings.vllm_tts_base_url}/audio/speech", json=body,
                                   headers=self._headers()), stream=True)
        except httpx.HTTPError as e:
            await http.aclose()
            raise Upstream(f"El motor TTS no responde: {type(e).__name__}", "upstream_error") from e
        if response.status_code != 200:
            detail = (await response.aread()).decode(errors="replace")
            await response.aclose()
            await http.aclose()
            raise _upstream_error("TTS", response.status_code, detail)
        media = "audio/wav" if response_format == "wav" else "audio/pcm"
        return StreamingResponse(self._speech_stream(access, response_format, http, response), media_type=media,
                                 headers={"Cache-Control": "no-store"})

    async def _speech_stream(self, access, response_format: str, http: httpx.AsyncClient,
                             response: httpx.Response) -> AsyncIterator[bytes]:
        """Reenvia el audio y cuenta los bytes: los segundos salen del formato (del encabezado del WAV)."""
        header = b""
        total = 0
        try:
            async for data in response.aiter_bytes():
                if len(header) < WAV_HEADER_BYTES:
                    header += data[:WAV_HEADER_BYTES - len(header)]
                total += len(data)
                yield data
        except httpx.HTTPError as e:
            logger.warning("inferencia TTS: stream cortado: %s", type(e).__name__)
        finally:
            await response.aclose()
            await http.aclose()
            await self._record(access, tts_requests=1, tts_seconds=audio_seconds(response_format, header, total))

    # ---------- catalogo ----------

    @staticmethod
    def models() -> list[dict]:
        return [{"id": settings.vllm_llm_model, "object": "model", "owned_by": "atentina", "engine": "llm"},
                {"id": settings.vllm_stt_model, "object": "model", "owned_by": "atentina", "engine": "stt"},
                {"id": settings.vllm_tts_model, "object": "model", "owned_by": "atentina", "engine": "tts"}]


def audio_seconds(response_format: str, header: bytes, total_bytes: int) -> float:
    """Duracion del audio que salio: WAV (44 bytes de encabezado, con su frecuencia, canales y bits) o
    PCM crudo (24 kHz, mono, 16 bits)."""
    rate, channels, bits, body = PCM_SAMPLE_RATE, 1, 16, total_bytes
    if response_format == "wav" and len(header) >= WAV_HEADER_BYTES and header[:4] == b"RIFF":
        channels, rate, _, _, bits = struct.unpack("<HIIHH", header[22:36])
        body = max(total_bytes - WAV_HEADER_BYTES, 0)
    per_second = rate * channels * (bits // 8)
    return body / per_second if per_second else 0.0


@cache
def get_gateway() -> InferenceGateway:
    return InferenceGateway(get_sessionmaker())
