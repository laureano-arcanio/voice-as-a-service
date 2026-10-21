import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from ...config import settings
from ...services import calls as service
from ...services.errors import Invalid, NotFound
from ...services.reports import CallFilter, Reports
from ..deps import DB, AdminPrincipal, CurrentPrincipal, Definitions, Engine, scoped_client_id
from ..schemas import (
    CallBulkDeleteIn,
    CallBulkDeleteOut,
    CallDetail,
    CallHangupOut,
    CallIn,
    CallPage,
    CallStartedOut,
    DailyOut,
    StatsOut,
)

router = APIRouter(tags=["calls"])

TzQuery = Annotated[str | None, Query(description="Zona IANA de las fechas (ej. America/Argentina/Buenos_Aires); "
                                                  "default BILLING_TIMEZONE")]
CampaignQuery = Annotated[str | None, Query(description="Solo las llamadas y conversaciones de esa campaña")]


def _filter(p, client_id, agent_id, date_from, date_to, tz, status=None, mode=None, campaign_id=None) -> CallFilter:
    try:
        zone = ZoneInfo(tz or settings.billing_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise Invalid(f"Zona horaria inexistente: {tz}") from None
    return CallFilter(client_id=scoped_client_id(p, client_id), agent_id=agent_id, date_from=date_from,
                      date_to=date_to, status=status or [], mode=mode, campaign_id=campaign_id, tz=zone)


@router.post("/calls", response_model=CallStartedOut, status_code=201,
             responses={429: {"description": "Limite del tier (concurrencia o minutos)"}})
async def start_call(body: CallIn, p: CurrentPrincipal, db: DB, engine: Engine):
    """Con `phone`, llamada saliente; sin el, de prueba por navegador (devuelve join_url).
    429 si el cliente esta al tope de llamadas simultaneas o sin minutos del mes."""
    started = await service.start_call(db, engine, p, service.CallRequest(**body.model_dump()))
    return CallStartedOut(**started.__dict__)


@router.get("/calls", response_model=CallPage)
def list_calls(p: CurrentPrincipal, db: DB, definitions: Definitions,
               client_id: str | None = None, agent_id: str | None = None,
               date_from: datetime.date | None = None, date_to: datetime.date | None = None, tz: TzQuery = None,
               status: Annotated[list[str] | None, Query(description="Uno o varios (status=a&status=b)")] = None,
               mode: str | None = None, campaign_id: CampaignQuery = None,
               limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    """Conversaciones con su llamada, de la mas nueva a la mas vieja."""
    items, total = Reports(db, definitions).page(
        _filter(p, client_id, agent_id, date_from, date_to, tz, status, mode, campaign_id), limit, offset)
    return CallPage(items=items, total=total)


@router.get("/calls/{conversation_id}", response_model=CallDetail)
def get_call(conversation_id: str, p: CurrentPrincipal, db: DB, definitions: Definitions):
    detail = Reports(db, definitions).detail(conversation_id)
    if detail is None or not p.can_access(detail["client_id"]):
        raise NotFound("Conversación inexistente")
    return detail


@router.post("/calls/{conversation_id}/hangup", response_model=CallHangupOut,
             responses={409: {"description": "La llamada no está en curso"}})
async def hang_up_call(conversation_id: str, p: CurrentPrincipal, db: DB):
    """Corta una llamada en curso: cuelga a la otra punta y la llamada termina con
    ended_reason `hangup_by_user`. Para no volver a atender ese número: /blocked-numbers."""
    call = await service.hang_up(db, p, conversation_id)
    return CallHangupOut(status=call.status, ended_reason=call.ended_reason)


@router.delete("/calls/{conversation_id}", status_code=204)
def delete_call(conversation_id: str, _: AdminPrincipal, db: DB):
    """Borra la conversacion con su llamada (y el consumo del mes), su hilo y mensajes de
    WhatsApp y sus grabaciones. Solo admin; 409 si la llamada esta en curso."""
    service.delete_conversation(db, conversation_id)


@router.post("/calls/bulk-delete", response_model=CallBulkDeleteOut)
def bulk_delete_calls(body: CallBulkDeleteIn, _: AdminPrincipal, db: DB):
    """Borra varias conversaciones (las seleccionadas en la UI). Devuelve cuantas habia;
    los ids inexistentes se ignoran. Solo admin; 409 si alguna llamada esta en curso."""
    return CallBulkDeleteOut(deleted=service.delete_conversations(db, body.ids))


@router.get("/calls/{conversation_id}/recordings/{n}")
def get_recording(conversation_id: str, n: int, p: CurrentPrincipal, db: DB, definitions: Definitions):
    """El WAV de ese mensaje (agent.record_audio prendido): CALL_RECORDINGS_DIR/<id>/NNN.wav."""
    detail = Reports(db, definitions).detail(conversation_id)
    if detail is None or not p.can_access(detail["client_id"]):
        raise NotFound("Conversación inexistente")
    path = settings.call_recordings_dir / conversation_id / f"{n:03d}.wav"
    if not path.is_file():
        raise NotFound("Grabación inexistente")
    return FileResponse(path, media_type="audio/wav", filename=path.name)


@router.get("/stats", response_model=StatsOut)
def stats(p: CurrentPrincipal, db: DB, definitions: Definitions, client_id: str | None = None,
          agent_id: str | None = None, date_from: datetime.date | None = None, date_to: datetime.date | None = None,
          tz: TzQuery = None, campaign_id: CampaignQuery = None):
    return Reports(db, definitions).stats(_filter(p, client_id, agent_id, date_from, date_to, tz, campaign_id=campaign_id))


@router.get("/stats/daily", response_model=DailyOut)
def daily(p: CurrentPrincipal, db: DB, definitions: Definitions, date_from: datetime.date, date_to: datetime.date,
          client_id: str | None = None, agent_id: str | None = None, tz: TzQuery = None,
          campaign_id: CampaignQuery = None):
    """Conversaciones por dia local y % con workflow completo y con objetivo cumplido."""
    if date_to < date_from or (date_to - date_from).days > 366:
        raise Invalid("Rango de fechas invalido (hasta un año)")
    return Reports(db, definitions).daily(_filter(p, client_id, agent_id, date_from, date_to, tz, campaign_id=campaign_id))
