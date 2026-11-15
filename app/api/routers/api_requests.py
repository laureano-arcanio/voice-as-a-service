"""Pedidos a la API de inferencia, uno por uno (services/api_requests.py): el admin ve los de
todos los clientes y el cliente los suyos. Para el consumo contra el plan: /clients/{id}/inference-usage.
El contenido guardado de cada pedido (services/api_content.py) se ve, se baja y se borra aca."""
import datetime
import json
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse

from ...config import settings
from ...models import ApiRequest
from ...services import api_content
from ...services import api_requests as service
from ...services.errors import Invalid, NotFound
from ...services.studio import UPLOAD_TYPES
from ..deps import DB, CurrentPrincipal, SessionPrincipal, scoped_client_id
from ..schemas import ApiRequestContentOut, ApiRequestPage

router = APIRouter(tags=["inference"])


@router.get("/api-requests", response_model=ApiRequestPage)
def list_api_requests(
        p: CurrentPrincipal, db: DB, client_id: str | None = None, api_key_id: str | None = None,
        kind: Annotated[list[Literal["llm", "stt", "tts"]] | None, Query(description="Uno o varios")] = None,
        status: Annotated[list[Literal["ok", "cut", "error", "rejected"]] | None,
                          Query(description="Uno o varios")] = None,
        source: Annotated[list[Literal["api", "voice_test_panel", "voice_test_api", "voice_test_landing"]] | None,
                          Query(description="api (inferencia) o prueba de voz; uno o varios")] = None,
        stream: bool | None = None,
        date_from: datetime.date | None = None, date_to: datetime.date | None = None,
        tz: Annotated[str | None, Query(description="Zona IANA de las fechas; default BILLING_TIMEZONE")] = None,
        limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    """Pedidos a la API de inferencia (LLM, STT, TTS) y pruebas de voz, del mas nuevo al mas viejo, con los
    totales del filtro. `has_content`: si hay contenido guardado (GET /api-requests/{id}/content)."""
    try:
        zone = ZoneInfo(tz or settings.billing_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Invalid(f"Zona horaria inexistente: {tz}") from None
    flt = service.RequestFilter(client_id=scoped_client_id(p, client_id), api_key_id=api_key_id, kind=kind or [],
                                status=status or [], source=source or [], stream=stream, date_from=date_from, date_to=date_to, tz=zone)
    items, total = service.page(db, flt, limit, offset)
    return ApiRequestPage(items=items, total=total, summary=service.summary(db, flt))


def _row(db, p, request_id: str) -> tuple[ApiRequest, dict]:
    """El pedido con contenido y sus archivos; 404 si no existe, es de otro cliente o no tiene contenido."""
    row = db.get(ApiRequest, request_id)
    files = api_content.files_of(row) if row is not None and (p.is_admin or row.client_id == p.client_id) else {}
    if not files:
        raise NotFound("Ese pedido no tiene contenido guardado", "content_not_found")
    return row, files


def _audio(files: dict, which: str):
    """El archivo de audio de entrada (input.<ext> del STT) o de salida (output.wav del TTS)."""
    if which == "output":
        return files.get("output.wav")
    return next((path for name, path in files.items() if name.startswith("input.")), None)


def _media_type(path) -> str:
    return "audio/wav" if path.name == "output.wav" else UPLOAD_TYPES.get(path.suffix, "application/octet-stream")


def _json(files: dict, name: str) -> dict | None:
    path = files.get(name)
    if path is None:
        return None
    try:
        return json.loads(path.read_bytes())
    except ValueError:
        return None


@router.get("/api-requests/{request_id}/content", response_model=ApiRequestContentOut)
def read_api_request_content(request_id: str, p: CurrentPrincipal, db: DB):
    """Lo que se mando y se recibio en el pedido: el body y la respuesta en JSON, y los audios (se bajan por
    /audio/{input|output}). 404 content_not_found si no se guardo, vencio o se borro."""
    row, files = _row(db, p, request_id)
    request = _json(files, "request.json")

    def audio(which):
        path = _audio(files, which)
        return None if path is None else {"content_type": _media_type(path), "bytes": path.stat().st_size}

    return ApiRequestContentOut(id=row.id, kind=row.kind, source=row.source, created_at=row.created_at,
                                request=request, response=_json(files, "response.json"),
                                input_audio=audio("input"), output_audio=audio("output"),
                                truncated=bool(isinstance(request, dict) and request.get("truncated") is True))


@router.get("/api-requests/{request_id}/audio/{which}", response_class=FileResponse,
            responses={200: {"content": {"audio/*": {}}}})
def read_api_request_audio(request_id: str, which: Literal["input", "output"], p: CurrentPrincipal, db: DB,
                           download: bool = False):
    """El audio subido al STT (input) o el sintetizado por el TTS (output). download=true lo baja como adjunto."""
    _, files = _row(db, p, request_id)
    path = _audio(files, which)
    if path is None:
        raise NotFound("Ese pedido no tiene ese audio", "content_not_found")
    if download:
        return FileResponse(path, media_type=_media_type(path), filename=f"{request_id}-{which}{path.suffix}")
    return FileResponse(path, media_type=_media_type(path))


@router.delete("/api-requests/{request_id}/content", status_code=204)
def delete_api_request_content(request_id: str, p: SessionPrincipal, db: DB):
    """Borra el contenido guardado del pedido; la fila (consumo, estado) queda. Solo con sesion del panel."""
    row, _ = _row(db, p, request_id)
    api_content.delete(db, row)
    db.commit()
    return Response(status_code=204)
