"""Leads, personas, contactos, fuentes, actividad, respuestas y linea de tiempo."""
import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import schemas as S
from ..auth import UserOnly, Who
from ..config import local_today
from ..db import get_session, naive_utc
from ..models import Activity, ContactPoint, GaVisit, Lead, Message, Person
from ..services import leads as L
from ..services import messages as M
from ..services.errors import Conflict, NotFound

router = APIRouter(prefix="/api", tags=["leads"])
DB = Annotated[Session, Depends(get_session)]


def one(s: Session, model, id_: int, label: str):
    obj = s.get(model, id_)
    if not obj:
        raise NotFound(label)
    return obj


def get_lead(s: Session, lead_id: int) -> Lead:
    return one(s, Lead, lead_id, f"lead {lead_id}")


def summaries(s: Session, leads: list[Lead]) -> list[S.LeadSummary]:
    ids = [x.id for x in leads]
    if not ids:
        return []
    last_out = dict(s.execute(select(Message.lead_id, func.max(Message.sent_at)).where(
        Message.lead_id.in_(ids), Message.direction == "out", Message.sent_at.isnot(None))
        .group_by(Message.lead_id)).all())
    last_in = dict(s.execute(select(Message.lead_id, func.max(Message.sent_at)).where(
        Message.lead_id.in_(ids), Message.direction == "in").group_by(Message.lead_id)).all())
    ga = dict(s.execute(select(GaVisit.lead_id, func.sum(GaVisit.active_users)).where(
        GaVisit.lead_id.in_(ids)).group_by(GaVisit.lead_id)).all())
    out = []
    for x in leads:
        pe = L.primary_email(x)
        out.append(S.LeadSummary.model_validate(x).model_copy(update={
            "primary_email": pe.value if pe else None, "last_out_at": last_out.get(x.id),
            "last_in_at": last_in.get(x.id), "ga_users": int(ga.get(x.id) or 0)}))
    return out


def full(s: Session, lead: Lead) -> S.LeadOut:
    base = summaries(s, [lead])[0]
    return S.LeadOut.model_validate(lead).model_copy(update=base.model_dump(
        include={"primary_email", "last_out_at", "last_in_at", "ga_users"}))


@router.get("/leads", response_model=S.LeadPage, summary="Lista de leads con filtros")
def list_leads(s: DB, _: Who,
               q: str | None = Query(None, description="Busca en nombre, dominio, email y rubro"),
               stage: str | None = Query(None, description="Una o varias, separadas por coma"),
               tag: str | None = None, industry: str | None = None, kind: str | None = None,
               campaign_id: int | None = Query(None, description="Con algun mail de esa campaña"),
               has_clicks: bool | None = Query(None, description="Con visitas de GA"),
               next_action_due: bool | None = Query(None, description="Proxima accion vencida u hoy"),
               limit: int = Query(100, le=500), offset: int = 0):
    query = select(Lead)
    if q:
        like = f"%{q.lower()}%"
        sub = select(ContactPoint.lead_id).where(func.lower(ContactPoint.value).like(like))
        query = query.where(or_(func.lower(Lead.name).like(like), func.lower(Lead.domain).like(like),
                                func.lower(Lead.description).like(like), Lead.id.in_(sub),
                                Lead.legacy_ref == q.lstrip("#")))
    if stage:
        query = query.where(Lead.stage.in_(stage.split(",")))
    if industry:
        query = query.where(Lead.industry == industry)
    if kind:
        query = query.where(Lead.kind == kind)
    if campaign_id:
        query = query.where(Lead.id.in_(select(Message.lead_id).where(Message.campaign_id == campaign_id)))
    if has_clicks is not None:
        sub = select(GaVisit.lead_id).where(GaVisit.lead_id.isnot(None))
        query = query.where(Lead.id.in_(sub) if has_clicks else Lead.id.notin_(sub))
    if next_action_due:
        query = query.where(Lead.next_action_at <= local_today())
    items = s.scalars(query.order_by(Lead.stage_changed_at.desc(), Lead.id.desc())).all()
    if tag:
        items = [x for x in items if tag in (x.tags or [])]
    total = len(items)
    return {"total": total, "items": summaries(s, items[offset:offset + limit])}


@router.get("/leads/check", summary="¿Ya existe o esta bloqueado? (antes de proponer un lead)")
def check(s: DB, _: Who, domain: str | None = None, email: str | None = None):
    out: dict = {"lead": None, "blocked": None}
    d = L.norm_domain(domain or (email.split("@")[-1] if email else None))
    lead = s.scalar(select(Lead).where(Lead.domain == d)) if d else None
    if not lead and email:
        lead = s.scalar(select(Lead).join(ContactPoint).where(ContactPoint.value == email.lower()))
    if lead:
        out["lead"] = {"id": lead.id, "name": lead.name, "stage": lead.stage}
    if email:
        b = L.is_blocked(s, email)
        out["blocked"] = b.reason if b else None
    return out


@router.post("/leads", response_model=S.UpsertResult, summary="Crear o actualizar un lead (por dominio)")
def upsert(body: S.LeadUpsert, s: DB, who: Who, response: Response):
    lead, created = L.upsert(s, body.model_dump(exclude_none=True), who, require_source=who == "agente")
    s.commit()
    s.refresh(lead)
    response.status_code = 201 if created else 200
    return {"result": "created" if created else "updated", "lead": full(s, lead)}


@router.get("/leads/{lead_id}", response_model=S.LeadOut)
def get(lead_id: int, s: DB, _: Who):
    return full(s, get_lead(s, lead_id))


@router.patch("/leads/{lead_id}", response_model=S.LeadOut)
def patch(lead_id: int, body: S.LeadPatch, s: DB, who: Who):
    lead = get_lead(s, lead_id)
    data = body.model_dump(exclude_unset=True)
    stage = data.pop("stage", None)
    if data.get("website"):
        d = L.norm_domain(data["website"])
        other = s.scalar(select(Lead.id).where(Lead.domain == d, Lead.id != lead.id)) if d else None
        if other:
            raise Conflict(f"el dominio {d} ya es del lead {other}", field="website")
        lead.domain = d or lead.domain
    for k, v in data.items():
        setattr(lead, k, v)
    if stage:
        L.set_stage(s, lead, stage, who)
    s.commit()
    return full(s, lead)


@router.delete("/leads/{lead_id}", status_code=204)
def delete(lead_id: int, s: DB, _: UserOnly):
    s.delete(get_lead(s, lead_id))
    s.commit()


@router.post("/leads/{lead_id}/people", response_model=S.PersonOut, status_code=201)
def add_person(lead_id: int, body: S.PersonIn, s: DB, _: Who):
    p = L.add_person(s, get_lead(s, lead_id), body.model_dump(exclude_none=True))
    s.commit()
    return p


@router.patch("/people/{person_id}", response_model=S.PersonOut)
def patch_person(person_id: int, body: S.PersonIn, s: DB, _: Who):
    p = one(s, Person, person_id, f"persona {person_id}")
    for k, v in body.model_dump(exclude_unset=True, exclude={"source_url", "source_seen_at"}).items():
        setattr(p, k, v)
    s.commit()
    return p


@router.delete("/people/{person_id}", status_code=204)
def delete_person(person_id: int, s: DB, _: Who):
    p = one(s, Person, person_id, f"persona {person_id}")
    s.delete(p)
    s.commit()


@router.post("/leads/{lead_id}/contacts", response_model=S.ContactOut, status_code=201,
             summary="Sumar un email, telefono, WhatsApp, LinkedIn o formulario")
def add_contact(lead_id: int, body: S.ContactIn, s: DB, who: Who):
    c = L.add_contact(s, get_lead(s, lead_id), body.model_dump(exclude_none=True), require_source=who == "agente")
    s.commit()
    return c


@router.patch("/contacts/{contact_id}", response_model=S.ContactOut)
def patch_contact(contact_id: int, body: S.ContactIn, s: DB, _: Who):
    c = one(s, ContactPoint, contact_id, f"contacto {contact_id}")
    data = body.model_dump(exclude_unset=True)
    if data.get("is_primary"):
        for other in c.lead.contacts:
            if other.kind == c.kind:
                other.is_primary = other is c
    for k in ("label", "verified_at"):
        if k in data:
            setattr(c, k, data[k])
    s.commit()
    return c


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, s: DB, _: Who):
    c = one(s, ContactPoint, contact_id, f"contacto {contact_id}")
    s.delete(c)
    s.commit()


@router.post("/leads/{lead_id}/sources", response_model=S.SourceOut, status_code=201)
def add_source(lead_id: int, body: S.SourceIn, s: DB, _: Who):
    src = L.add_source(s, get_lead(s, lead_id), body.url, body.seen_at, body.title, body.note)
    s.commit()
    return src


@router.get("/leads/{lead_id}/timeline", response_model=list[S.TimelineItem],
            summary="Mails, actividad y visitas de GA, del mas nuevo al mas viejo")
def timeline(lead_id: int, s: DB, _: Who):
    get_lead(s, lead_id)
    items = []
    for m in s.scalars(select(Message).where(Message.lead_id == lead_id)):
        d = S.MessageOut.model_validate(m).model_dump(mode="json")
        d["campaign_slug"] = m.campaign.slug if m.campaign else None
        items.append({"type": "message", "at": m.sent_at or m.queued_at or m.created_at, "data": d})
    for a in s.scalars(select(Activity).where(Activity.lead_id == lead_id)):
        items.append({"type": "activity", "at": a.at, "data": S.ActivityOut.model_validate(a).model_dump(mode="json")})
    for v in s.scalars(select(GaVisit).where(GaVisit.lead_id == lead_id)):
        items.append({"type": "visit", "at": datetime.datetime.combine(v.date, datetime.time(12)),
                      "data": S.GaVisitOut.model_validate(v).model_dump(mode="json")})
    return sorted(items, key=lambda x: x["at"], reverse=True)


@router.post("/leads/{lead_id}/activities", response_model=S.ActivityOut, status_code=201,
             summary="Nota, llamada, charla, LinkedIn o tarea")
def add_activity(lead_id: int, body: S.ActivityIn, s: DB, who: Who):
    get_lead(s, lead_id)
    data = body.model_dump(exclude_none=True)
    if body.kind == "task" and "done" not in body.model_fields_set:
        data["done"] = False
    if data.get("at"):
        data["at"] = naive_utc(data["at"])
    a = Activity(lead_id=lead_id, created_by=who, **data)
    s.add(a)
    s.commit()
    return a


@router.get("/activities", response_model=list[S.ActivityOut], summary="Tareas abiertas y actividad reciente")
def list_activities(s: DB, _: Who, open_tasks: bool = False, kind: str | None = None, limit: int = 100):
    q = select(Activity)
    if open_tasks:
        q = q.where(Activity.kind == "task", Activity.done.is_(False))
    if kind:
        q = q.where(Activity.kind == kind)
    return s.scalars(q.order_by(Activity.at.desc()).limit(limit)).all()


@router.patch("/activities/{activity_id}", response_model=S.ActivityOut)
def patch_activity(activity_id: int, body: S.ActivityPatch, s: DB, _: Who):
    a = one(s, Activity, activity_id, f"actividad {activity_id}")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    s.commit()
    return a


@router.post("/leads/{lead_id}/inbound", response_model=S.MessageOut, status_code=201,
             summary="Registrar una respuesta del lead (cambia la etapa a respondio y frena lo pendiente)")
def inbound(lead_id: int, body: S.InboundIn, s: DB, who: Who):
    m = M.record_inbound(s, get_lead(s, lead_id), from_addr=body.from_addr, subject=body.subject,
                         text=body.text, at=body.at, by=who, auto=body.auto_reply)
    s.commit()
    return m
