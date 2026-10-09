from fastapi import APIRouter, Depends
from fastapi.responses import Response

from ...config import settings
from ...services import tts, voices
from ...services.ratelimit import Limit
from ..deps import ActiveClientPrincipal, CurrentPrincipal, rate_limit
from ..schemas import TtsPreviewIn, VoiceOut

router = APIRouter(tags=["voices"])


# El cupo es el de services/tts.py, compartido con la demo de la landing (H04).
_PreviewSlots = tts.PreviewSlots
TtsBusy = tts.TtsBusy


@router.get("/voices", response_model=list[VoiceOut])
def list_voices(_: CurrentPrincipal, genero: str | None = None, wer_max: float | None = None,
                car_min: float | None = None, car_max: float | None = None):
    """Voces del TTS con sus metricas (tts/finetune/voces.tsv), filtradas; de menor a mayor WER."""
    return voices.search(genero or None, wer_max, car_min, car_max)


@router.post("/tts/preview", response_class=Response,
             responses={200: {"content": {"audio/wav": {}}}, 429: {"description": "Limite de uso por hora"},
                        503: {"description": "Demasiadas pruebas de voz a la vez (Retry-After)"}},
             dependencies=[Depends(rate_limit("tts_preview", lambda: Limit(settings.rate_tts_preview_per_hour, 3600),
                                              per="client"))])
async def tts_preview(body: TtsPreviewIn, _: ActiveClientPrincipal):
    """Sintetiza el texto con la voz pedida y devuelve el WAV, directo contra el TTS.
    503 tts_busy si ya hay TTS_PREVIEW_MAX_CONCURRENT pruebas en curso (con las de la demo)."""
    audio = await tts.synthesize_bounded(body.voice, body.text)
    return Response(audio, media_type="audio/wav", headers={"Cache-Control": "no-store"})
