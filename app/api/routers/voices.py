from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...config import settings
from ...services import tts, voices
from ...services.ratelimit import Limit
from ..deps import CurrentPrincipal, rate_limit
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
async def tts_preview(body: TtsPreviewIn, _: CurrentPrincipal):
    """Sintetiza el texto con la voz pedida, directo contra el TTS. `format=wav` (default): el WAV completo.
    `format=pcm`: audio crudo (16 bits, mono, 24 kHz) que se transmite mientras se sintetiza."""
    stream = await (tts.preview_pcm if body.format == "pcm" else tts.preview)(body.voice, body.text)
    return StreamingResponse(stream, media_type="audio/pcm" if body.format == "pcm" else "audio/wav",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
