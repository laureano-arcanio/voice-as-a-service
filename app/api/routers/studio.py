"""Estudio: texto a voz y transcripcion para todos los planes (docs/features/ESTUDIO.md). Descuenta de los minutos
de sintesis o de transcripcion del plan (los de la API de inferencia) y deja todo guardado en el cliente. Un admin que entro como el cliente solo ve y baja: no gasta minutos ajenos."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse

from ...config import settings
from ...models import StudioItem
from ...services import studio as service
from ...services.errors import Invalid, NotFound
from ...services.ratelimit import Limit
from ..deps import DB, CurrentPrincipal, NotSupportPrincipal, rate_limit, scoped_client_id
from ..schemas import StudioItemOut, StudioItemPage, StudioSpeechIn

router = APIRouter(prefix="/studio", tags=["studio"])
RATE = Depends(rate_limit("studio", lambda: Limit(settings.rate_studio_per_hour, 3600)))
QUOTA_RESPONSE = {
    403: {"description": "El plan no incluye minutos de síntesis o de transcripción (not_in_plan)"},
    429: {"description": "Sin minutos de síntesis o de transcripción (api_tts_minutes, api_stt_minutes) "
                         "o demasiados trabajos por hora"},
}


def _client_id(p) -> str:
    if not p.client_id:
        raise Invalid("Entrá como un cliente para usar el Estudio", "client_required")
    return p.client_id


def _user_id(p) -> str | None:
    return p.id if p.kind == "user" else None


def _item(db, p, item_id: str) -> StudioItem:
    item = db.get(StudioItem, item_id)
    if item is None or item.deleted_at is not None or not p.can_access(item.client_id):
        raise NotFound("No existe ese elemento")
    return item


def _out(item: StudioItem, full: bool = False) -> StudioItemOut:
    text = item.text or ""
    return StudioItemOut(id=item.id, kind=item.kind, origin=item.origin, status=item.status, title=item.title,
                         voice=item.voice, progress=item.progress, audio_seconds=item.audio_seconds,
                         billed_seconds=item.billed_seconds, error=item.error, created_at=item.created_at,
                         finished_at=item.finished_at, excerpt=text[:200], text=text if full else None)


@router.post("/speech", response_model=StudioItemOut, status_code=201, responses=QUOTA_RESPONSE, dependencies=[RATE])
def create_speech(body: StudioSpeechIn, p: NotSupportPrincipal, db: DB):
    """Encola la sintesis del texto con esa voz y reserva los minutos estimados."""
    return _out(service.create_speech(db, _client_id(p), _user_id(p), body.text, body.voice), full=True)


@router.post("/transcriptions", response_model=StudioItemOut, status_code=201, responses=QUOTA_RESPONSE,
             dependencies=[RATE])
def create_transcription(file: Annotated[UploadFile, File(description="Audio o video con sonido")],
                         p: NotSupportPrincipal, db: DB):
    """Guarda el archivo, reserva los minutos que dura y encola la transcripcion."""
    return _out(service.create_transcription(db, _client_id(p), _user_id(p), file.file, file.filename))


@router.get("/items", response_model=StudioItemPage)
def list_items(p: CurrentPrincipal, db: DB, kind: Literal["tts", "stt"] | None = None,
               client_id: str | None = None, limit: int = Query(default=50, ge=1, le=200),
               offset: int = Query(default=0, ge=0)):
    """Lo sintetizado y transcripto, del mas nuevo al mas viejo. `excerpt` trae el comienzo del texto."""
    items, total = service.page(db, scoped_client_id(p, client_id), kind, limit, offset)
    return StudioItemPage(items=[_out(i) for i in items], total=total)


@router.get("/items/{item_id}", response_model=StudioItemOut)
def get_item(item_id: str, p: CurrentPrincipal, db: DB):
    return _out(_item(db, p, item_id), full=True)


@router.get("/items/{item_id}/audio", response_class=FileResponse,
            responses={200: {"content": {"audio/wav": {}, "audio/mpeg": {}, "audio/ogg": {}, "audio/flac": {}}}})
def get_audio(item_id: str, p: CurrentPrincipal, db: DB, format: Literal["wav", "mp3", "ogg", "flac"] = "wav",
              download: bool = False):
    """El audio: en texto a voz, en el formato pedido; en una transcripcion, el archivo que se subio."""
    item = _item(db, p, item_id)
    path, media_type, suffix = service.audio_file(item, format)
    if not path.is_file():
        raise NotFound("El audio no está disponible")
    stem = item.title.rsplit(".", 1)[0] if item.kind == "stt" else item.title
    return FileResponse(path, media_type=media_type, filename=f"{stem[:60].strip() or 'audio'}{suffix}",
                        content_disposition_type="attachment" if download else "inline")


@router.delete("/items/{item_id}", status_code=204, response_class=Response, responses={409: {"description": "studio_busy"}})
def delete_item(item_id: str, p: NotSupportPrincipal, db: DB):
    """Borra el audio y el texto. Lo ya usado no vuelve a los minutos del plan."""
    service.delete_item(db, _item(db, p, item_id))
