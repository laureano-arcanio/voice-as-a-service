"""Registro de eventos por conversacion (docs/features/EQUIPO_TELEFONIA.md): la linea de tiempo de una
llamada o un hilo de WhatsApp que ve el cliente en el panel y que sale por la API (y despues por
webhook). Cada evento tiene hora, tipo, quien lo hizo y datos propios; los mensajes siguen en la
conversacion (Message.at), aca no se repiten."""
import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import CallStatus, Event

# Tipos conocidos: un tipo nuevo se agrega aca (y en el plan) antes de usarlo.
TYPES = frozenset({
    # Llamada (services/calls.update_call, al cambiar de estado).
    "call.ringing", "call.answered", "call.ended",
    # Derivacion de una llamada (fase 2): uno por intento con cada miembro del area.
    "handoff.requested", "handoff.dialing", "handoff.answered", "handoff.confirmed",
    "handoff.no_answer", "handoff.busy", "handoff.failed", "handoff.machine", "handoff.not_confirmed",
    "handoff.connected", "handoff.returned_to_ai", "handoff.person_hung_up", "handoff.ended",
    "handoff.unavailable",   # fuera de horario, sin canal, sin minutos o sin miembros
    "hold.started", "hold.ended",
    # Entrante al equipo (llamadas directas): nadie atendio y se uso el respaldo (agent, voicemail o hangup), con el
    # motivo (team_no_answer o after_hours).
    "team.fallback",
    # Puente de WhatsApp (fase 3).
    "wa.handoff.assigned", "wa.handoff.first_reply", "wa.handoff.reassigned", "wa.handoff.closed",
})
ACTORS = frozenset({"system", "agent", "customer", "person"})

# Estado de la llamada -> evento (call.ended lleva el estado final y el motivo).
_CALL_STATUS_EVENTS = {
    CallStatus.sonando: "call.ringing",
    CallStatus.en_curso: "call.answered",
    CallStatus.finalizada: "call.ended",
    CallStatus.fallida: "call.ended",
    CallStatus.rechazada: "call.ended",
    CallStatus.cancelada: "call.ended",
}


def record(s: Session, client_id: str, type: str, *, conversation_id: str | None = None, actor: str = "system",
           area_id: str | None = None, team_member_id: str | None = None, at: datetime.datetime | None = None,
           **data) -> Event:
    if type not in TYPES:
        raise ValueError(f"tipo de evento desconocido: {type}")
    if actor not in ACTORS:
        raise ValueError(f"actor desconocido: {actor}")
    event = Event(client_id=client_id, type=type, actor=actor, conversation_id=conversation_id, area_id=area_id,
                  team_member_id=team_member_id, at=at or utcnow(), data=data)
    s.add(event)
    return event


def record_call_status(s: Session, call, values: dict) -> None:
    """El evento del cambio de estado de la llamada que traen `values` (si corresponde a uno)."""
    status = values["status"]
    type = _CALL_STATUS_EVENTS.get(status)
    if type is None or call.client_id is None:
        return
    data = {"mode": call.mode}
    if type == "call.ended":
        data |= {"status": str(status), "reason": values.get("ended_reason") or call.ended_reason or ""}
        if values.get("sip_status") is not None:
            data["sip_status"] = values["sip_status"]
    record(s, call.client_id, type, conversation_id=call.conversation_id, **data)


def list_events(s: Session, client_id: str | None, *, conversation_id: str | None = None,
                types: list[str] | None = None, since: datetime.datetime | None = None,
                until: datetime.datetime | None = None, after_id: int | None = None,
                limit: int = 100) -> list[Event]:
    """En orden de llegada (id). `after_id` es el cursor para leer de a paginas o seguir leyendo lo
    nuevo; `types` acepta prefijos terminados en punto ("handoff.")."""
    q = select(Event).order_by(Event.id).limit(limit)
    if client_id is not None:
        q = q.where(Event.client_id == client_id)
    if conversation_id is not None:
        q = q.where(Event.conversation_id == conversation_id)
    if types:
        exact = [t for t in types if not t.endswith(".")]
        prefixes = [t for t in types if t.endswith(".")]
        conds = ([Event.type.in_(exact)] if exact else []) + [Event.type.startswith(p) for p in prefixes]
        q = q.where(or_(*conds))
    if since is not None:
        q = q.where(Event.at >= since)
    if until is not None:
        q = q.where(Event.at < until)
    if after_id is not None:
        q = q.where(Event.id > after_id)
    return list(s.scalars(q))
