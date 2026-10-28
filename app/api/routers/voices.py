from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ...config import settings
from ...models import Client
from ...services import tts, voices
from ...services.ratelimit import Limit
from ..deps import DB, CurrentPrincipal, rate_limit
from ..schemas import TtsPreviewIn, VoiceOut

router = APIRouter(tags=["voices"])


@router.get("/voices", response_model=list[VoiceOut])
def list_voices(_: CurrentPrincipal, genero: str | None = None, wer_max: float | None = None,
                car_min: float | None = None, car_max: float | None = None):
    """Voces del TTS con sus metricas (tts/finetune/voces.tsv), filtradas; de menor a mayor WER."""
    return voices.search(genero or None, wer_max, car_min, car_max)


@router.post("/tts/preview", response_class=StreamingResponse,
             responses={200: {"content": {"audio/wav": {}, "audio/pcm": {}}}, 429: {"description": "Limite de uso por hora"}},
             dependencies=[Depends(rate_limit("tts_preview", lambda: Limit(settings.rate_tts_preview_per_hour, 3600)))])
async def tts_preview(body: TtsPreviewIn, p: CurrentPrincipal, db: DB):
    """Sintetiza el texto con la voz pedida, directo contra el TTS. `format=wav` (default): el WAV completo.
    `format=pcm`: audio crudo (16 bits, mono, 24 kHz) que se transmite mientras se sintetiza.
    Queda en los pedidos de la API del cliente como prueba de voz; no suma al cupo de TTS del plan."""
    # Un admin sin cliente elegido prueba en el cliente de la demo (Atentina).
    client_id = p.client_id or db.scalar(select(Client.id).where(Client.slug == settings.demo_client))
    start = (tts.preview_pcm if body.format == "pcm" else tts.preview)(body.voice, body.text)
    if client_id is None:
        stream = await start
    else:
        key_id = p.id if p.kind == "api_key" else None
        source = tts.SOURCE_PANEL if p.kind == "user" and not p.oauth else tts.SOURCE_API
        stream = await tts.tracked(start, sessionmaker(bind=db.get_bind()), client_id=client_id, key_id=key_id,
                                   source=source, voice=body.voice, characters=len(body.text.strip()),
                                   audio_format=body.format)
    return StreamingResponse(stream, media_type="audio/pcm" if body.format == "pcm" else "audio/wav",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
