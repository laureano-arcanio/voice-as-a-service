import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Header, Query, Response

from ...config import settings
from ...services import calls as service
from ...services.errors import Invalid, NotFound
from ...services.reports import CallFilter, Reports
from ..deps import (
    DB,
    ActiveClientPrincipal,
    CurrentPrincipal,
    Definitions,
    Engine,
    scoped_client_id,
)
from ..schemas import CallDetail, CallIn, CallPage, CallStartedOut, DailyOut, StatsOut

router = APIRouter(tags=["calls"])

TzQuery = Annotated[str | None, Query(description="Zona IANA de las fechas (ej. America/Argentina/Buenos_Aires); "
                                                  "default BILLING_TIMEZONE")]


def _filter(p, client_id, agent_id, date_from, date_to, tz, status=None, mode=None) -> CallFilter:
    try:
        zone = ZoneInfo(tz or settings.billing_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Invalid(f"Zona horaria inexistente: {tz}") from None
    return CallFilter(client_id=scoped_client_id(p, client_id), agent_id=agent_id, date_from=date_from,
                      date_to=date_to, status=status or [], mode=mode, tz=zone)


IdempotencyKey = Annotated[str | None, Header(
    alias="Idempotency-Key", min_length=1, max_length=128,
    description="Opcional: un reintento con la misma clave devuelve la misma llamada (200) sin marcar de nuevo")]


@router.post("/calls", response_model=CallStartedOut, status_code=201,
             responses={200: {"description": "Ya existia una llamada con esa Idempotency-Key"},
                        409: {"description": "Saliente sin numero propio del cliente (no_caller_id) o "
                                            "Idempotency-Key reusada para otra llamada"},
                        429: {"description": "Limite del tier (concurrencia o minutos)"}})
async def start_call(body: CallIn, p: ActiveClientPrincipal, db: DB, engine: Engine, response: Response,
                     idempotency_key: IdempotencyKey = None):
    """Con `phone`, llamada saliente; sin el, de prueba por navegador (devuelve join_url).
    Saliente: sale con un numero del cliente (from_number_id o el primero); sin numero
    propio, 409 no_caller_id. 429 si el cliente esta al tope de llamadas simultaneas o
    sin minutos del mes."""
    req = service.CallRequest(**body.model_dump(), idempotency_key=idempotency_key)
    started = await service.start_call(db, engine, p, req)
    if started.replayed:
        response.status_code = 200
    return CallStartedOut(conversation_id=started.conversation_id, room=started.room, mode=started.mode,
                          join_url=started.join_url)


@router.get("/calls", response_model=CallPage)
def list_calls(p: CurrentPrincipal, db: DB, definitions: Definitions,
               client_id: str | None = None, agent_id: str | None = None,
               date_from: datetime.date | None = None, date_to: datetime.date | None = None, tz: TzQuery = None,
               status: Annotated[list[str] | None, Query(description="Uno o varios (status=a&status=b)")] = None,
               mode: str | None = None,
               limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    """Conversaciones con su llamada, de la mas nueva a la mas vieja."""
    items, total = Reports(db, definitions).page(
        _filter(p, client_id, agent_id, date_from, date_to, tz, status, mode), limit, offset)
    return CallPage(items=items, total=total)


@router.get("/calls/{conversation_id}", response_model=CallDetail)
def get_call(conversation_id: str, p: CurrentPrincipal, db: DB, definitions: Definitions):
    detail = Reports(db, definitions).detail(conversation_id)
    if detail is None or not p.can_access(detail["client_id"]):
        raise NotFound("Conversación inexistente")
    return detail


@router.get("/stats", response_model=StatsOut)
def stats(p: CurrentPrincipal, db: DB, definitions: Definitions, client_id: str | None = None,
          agent_id: str | None = None, date_from: datetime.date | None = None, date_to: datetime.date | None = None,
          tz: TzQuery = None):
    return Reports(db, definitions).stats(_filter(p, client_id, agent_id, date_from, date_to, tz))


@router.get("/stats/daily", response_model=DailyOut)
def daily(p: CurrentPrincipal, db: DB, definitions: Definitions, date_from: datetime.date, date_to: datetime.date,
          client_id: str | None = None, agent_id: str | None = None, tz: TzQuery = None):
    """Conversaciones por dia local y % con workflow completo y con objetivo cumplido."""
    if date_to < date_from or (date_to - date_from).days > 366:
        raise Invalid("Rango de fechas invalido (hasta un año)")
    return Reports(db, definitions).daily(_filter(p, client_id, agent_id, date_from, date_to, tz))
