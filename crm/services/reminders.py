"""Recordatorios y reuniones de un lead. El evento en Calendar lo sube gcal.sync (gcal_state=pending).

La proxima accion del lead sigue al recordatorio o reunion pendiente mas cercano; al cerrarlos, si la
proxima accion era uno de ellos, se limpia.
"""
import datetime
import zoneinfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import naive_utc, utcnow
from ..models import CLOSED_STAGES, STAGES, Activity, Lead, Person, Reminder
from . import leads as L
from .errors import Conflict, Invalid

DURATION = {"reminder": 15, "meeting": 30}


def parse_when(value: str) -> datetime.datetime:
    """'2026-10-27T11:00' (hora de Argentina si no trae zona) o '2026-10-27' (a las CRM_REMINDER_HOUR) -> UTC."""
    try:
        if len(value.strip()) == 10:
            dt = datetime.datetime.combine(datetime.date.fromisoformat(value.strip()),
                                           datetime.time(settings.reminder_hour))
        else:
            dt = datetime.datetime.fromisoformat(value.strip())
    except ValueError as e:
        raise Invalid(f"fecha inválida: {value!r} (2026-10-27 o 2026-10-27T11:00)", field="starts_at") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo(settings.send_timezone))
    return naive_utc(dt)


def local_date(dt: datetime.datetime) -> datetime.date:
    return dt.replace(tzinfo=datetime.UTC).astimezone(zoneinfo.ZoneInfo(settings.send_timezone)).date()


def _person(s: Session, lead: Lead, person_id: int | None) -> Person | None:
    if not person_id:
        return None
    p = s.get(Person, person_id)
    if not p or p.lead_id != lead.id:
        raise Invalid(f"la persona {person_id} no es de este lead", field="person_id")
    return p


def default_title(kind: str, lead: Lead, person: Person | None) -> str:
    if kind == "meeting":
        return f"Reunión: {lead.name}" + (f" ({person.name})" if person else "")
    return f"Llamar a {person.name} ({lead.name})" if person else f"Llamar a {lead.name}"


def _before(stage: str, target: str) -> bool:
    return stage not in CLOSED_STAGES and STAGES.index(stage) < STAGES.index(target)


def refresh_next_action(s: Session, lead: Lead) -> None:
    s.flush()
    rs = s.scalars(select(Reminder).where(Reminder.lead_id == lead.id)).all()
    pending = sorted((r for r in rs if r.status == "pending"), key=lambda r: r.starts_at)
    if pending:
        lead.next_action, lead.next_action_at = pending[0].title, local_date(pending[0].starts_at)
    elif lead.next_action in {r.title for r in rs}:
        lead.next_action = lead.next_action_at = None


def create(s: Session, lead: Lead, data: dict, by: str) -> Reminder:
    kind = data.get("kind") or "reminder"
    person = _person(s, lead, data.get("person_id"))
    r = Reminder(lead=lead, person=person, kind=kind, title=(data.get("title") or "").strip()[:300]
                 or default_title(kind, lead, person), notes=data.get("notes") or "",
                 location=data.get("location") or None, starts_at=parse_when(data["starts_at"]),
                 duration_min=data.get("duration_min") or DURATION[kind], created_by=by, gcal_state="pending")
    s.add(r)
    if kind == "meeting" and _before(lead.stage, "charla_agendada"):
        L.set_stage(s, lead, "charla_agendada", by)
    refresh_next_action(s, lead)
    return r


def _pending(r: Reminder) -> None:
    if r.status != "pending":
        raise Conflict(f"recordatorio {r.id}: ya está {r.status}")


def update(s: Session, r: Reminder, changes: dict) -> Reminder:
    _pending(r)
    if "person_id" in changes:
        r.person = _person(s, r.lead, changes["person_id"])
    for k in ("title", "notes", "duration_min"):
        if changes.get(k) is not None:
            setattr(r, k, changes[k])
    if "location" in changes:
        r.location = changes["location"] or None
    if changes.get("starts_at"):
        r.starts_at = parse_when(changes["starts_at"])
    r.gcal_state = "pending"
    refresh_next_action(s, r.lead)
    return r


def complete(s: Session, r: Reminder, outcome: str, no_show: bool, by: str) -> Reminder:
    """Hecho (o no se presento): queda en la linea de tiempo; una reunion hecha pasa el lead a charla_hecha."""
    _pending(r)
    r.status = "no_show" if no_show else "done"
    r.outcome, r.done_at, r.gcal_state = outcome.strip() or None, utcnow(), "pending"
    what = "No se presentó" if no_show else "Hecho"
    s.add(Activity(lead_id=r.lead_id, person_id=r.person_id, kind="meeting" if r.kind == "meeting" else "task",
                   text=f"{r.title} — {what}" + (f": {r.outcome}" if r.outcome else ""), done=True,
                   data={"reminder_id": r.id}, created_by=by))
    if r.kind == "meeting" and not no_show and _before(r.lead.stage, "charla_hecha"):
        L.set_stage(s, r.lead, "charla_hecha", by)
    refresh_next_action(s, r.lead)
    return r


def cancel(s: Session, r: Reminder) -> Reminder:
    _pending(r)
    r.status, r.gcal_state = "canceled", "pending"
    refresh_next_action(s, r.lead)
    return r
