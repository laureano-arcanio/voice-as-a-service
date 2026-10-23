"""Recordatorios y reuniones de los leads, con su evento en Google Calendar (services/gcal.py)."""
import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas as S
from ..auth import UserOnly, Who
from ..db import get_session
from ..models import Reminder
from ..services import gcal as GC
from ..services import reminders as R
from .leads import get_lead, one

router = APIRouter(prefix="/api", tags=["recordatorios"])
DB = Annotated[Session, Depends(get_session)]


def out(r: Reminder) -> S.ReminderOut:
    return S.ReminderOut.model_validate(r).model_copy(update={"lead_name": r.lead.name})


def _saved(s: Session, r: Reminder) -> S.ReminderOut:
    """Guarda y sube el cambio a Calendar; si falla, queda en error y lo reintenta gcal_loop."""
    s.commit()
    GC.sync(r)
    s.commit()
    return out(r)


@router.post("/leads/{lead_id}/reminders", response_model=S.ReminderOut, status_code=201,
             summary="Recordatorio ('llamame el lunes') o reunión: va al Calendar y a la próxima acción")
def create_reminder(lead_id: int, body: S.ReminderIn, s: DB, who: Who):
    return _saved(s, R.create(s, get_lead(s, lead_id), body.model_dump(), who))


@router.get("/reminders", response_model=list[S.ReminderOut])
def list_reminders(s: DB, _: Who, status: str | None = "pending", lead_id: int | None = None,
                   until: Annotated[datetime.date | None, Query(description="Hasta este dia (hora local), incluido")] = None,
                   limit: Annotated[int, Query(le=1000)] = 200):
    q = select(Reminder)
    if status:
        q = q.where(Reminder.status == status)
    if lead_id:
        q = q.where(Reminder.lead_id == lead_id)
    if until:
        q = q.where(Reminder.starts_at < R.parse_when((until + datetime.timedelta(days=1)).isoformat() + "T00:00"))
    return [out(r) for r in s.scalars(q.order_by(Reminder.starts_at).limit(limit))]


@router.patch("/reminders/{rid}", response_model=S.ReminderOut, summary="Reprogramar o editar")
def patch_reminder(rid: int, body: S.ReminderPatch, s: DB, _: Who):
    r = one(s, Reminder, rid, f"recordatorio {rid}")
    return _saved(s, R.update(s, r, body.model_dump(exclude_unset=True)))


@router.post("/reminders/{rid}/done", response_model=S.ReminderOut, summary="Hecho, con lo que pasó")
def done_reminder(rid: int, body: S.ReminderDoneIn, s: DB, who: Who):
    r = one(s, Reminder, rid, f"recordatorio {rid}")
    return _saved(s, R.complete(s, r, body.outcome, body.no_show, who))


@router.post("/reminders/{rid}/cancel", response_model=S.ReminderOut, summary="Cancelar: borra el evento")
def cancel_reminder(rid: int, s: DB, _: Who):
    return _saved(s, R.cancel(s, one(s, Reminder, rid, f"recordatorio {rid}")))


@router.post("/reminders/sync", summary="Subir a Calendar lo pendiente o con error")
def sync_reminders(s: DB, _: UserOnly):
    return {"synced": GC.sync_pending(s, limit=500)}
