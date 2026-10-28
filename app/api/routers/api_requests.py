"""Pedidos a la API de inferencia, uno por uno (services/api_requests.py): el admin ve los de
todos los clientes y el cliente los suyos. Para el consumo contra el plan: /clients/{id}/inference-usage."""
import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Query

from ...config import settings
from ...services import api_requests as service
from ...services.errors import Invalid
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import ApiRequestPage

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
    totales del filtro. Sin contenido: la plataforma no guarda prompts, audios ni textos."""
    try:
        zone = ZoneInfo(tz or settings.billing_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Invalid(f"Zona horaria inexistente: {tz}") from None
    flt = service.RequestFilter(client_id=scoped_client_id(p, client_id), api_key_id=api_key_id, kind=kind or [],
                                status=status or [], source=source or [], stream=stream, date_from=date_from, date_to=date_to, tz=zone)
    items, total = service.page(db, flt, limit, offset)
    return ApiRequestPage(items=items, total=total, summary=service.summary(db, flt))
