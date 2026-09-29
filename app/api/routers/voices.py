from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...services import tts, voices
from ..deps import CurrentPrincipal
from ..schemas import TtsPreviewIn, VoiceOut

router = APIRouter(tags=["voices"])


@router.get("/voices", response_model=list[VoiceOut])
def list_voices(_: CurrentPrincipal, genero: str | None = None, wer_max: float | None = None,
                car_min: float | None = None, car_max: float | None = None):
    """Voces del TTS con sus metricas (tts/finetune/voces.tsv), filtradas; de menor a mayor WER."""
    return voices.search(genero or None, wer_max, car_min, car_max)


@router.post("/tts/preview", response_class=StreamingResponse,
             responses={200: {"content": {"audio/wav": {}}}})
async def tts_preview(body: TtsPreviewIn, _: CurrentPrincipal):
    """Sintetiza el texto con la voz pedida y devuelve el WAV, directo contra el TTS."""
    stream = await tts.preview(body.voice, body.text)
    return StreamingResponse(stream, media_type="audio/wav", headers={"Cache-Control": "no-store"})
