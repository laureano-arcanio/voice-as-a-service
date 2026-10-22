"""Campanas, plantillas, mensajes y cola, blocklist, GA, "Hoy" y tablero."""
import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas as S
from ..auth import UserOnly, Who
from ..config import local_today
from ..db import get_session, naive_utc, utcnow
from ..models import (
    CLOSED_STAGES,
    REPLIED_STAGES,
    SENT_STATUSES,
    STAGES,
    Activity,
    Block,
    Campaign,
    GaVisit,
    Lead,
    Message,
    Template,
)
from ..services import ga as GA
from ..services import leads as L
from ..services import messages as M
from ..services import sending
from ..services.errors import Conflict, CrmError, Invalid
from ..services.templates import check as check_template
from ..services.templates import render
from .leads import get_lead, one, summaries

router = APIRouter(prefix="/api")
DB = Annotated[Session, Depends(get_session)]


def _commit_unique(s: Session, what: str) -> None:
    try:
        s.commit()
    except IntegrityError as e:
        s.rollback()
        raise Conflict(f"{what}: ya existe") from e


def msg_out(m: Message) -> S.MessageOut:
    return S.MessageOut.model_validate(m).model_copy(update={
        "lead_name": m.lead.name if m.lead else None, "campaign_slug": m.campaign.slug if m.campaign else None})


# --- Campanas ---

def campaign_stats(s: Session, cid: int) -> dict:
    rows = s.execute(select(Message.kind, Message.direction, Message.status, func.count(Message.id))
                     .where(Message.campaign_id == cid).group_by(Message.kind, Message.direction, Message.status)).all()
    st = {"leads": s.scalar(select(func.count(func.distinct(Message.lead_id))).where(Message.campaign_id == cid)) or 0,
          "first_sent": 0, "follow_up_sent": 0, "drafts": 0, "queued": 0, "bounced": 0, "replies": 0}
    for kind, direction, status, n in rows:
        if direction == "in":
            st["replies"] += n
        elif status in SENT_STATUSES:
            st["first_sent" if kind == "first" else "follow_up_sent"] += n
            if status == "bounced":
                st["bounced"] += n
        elif status == "draft":
            st["drafts"] += n
        elif status == "queued":
            st["queued"] += n
    st["ga_users"] = int(s.scalar(select(func.sum(GaVisit.active_users)).where(GaVisit.campaign_id == cid)) or 0)
    return st


def camp_out(s: Session, c: Campaign) -> S.CampaignOut:
    return S.CampaignOut.model_validate(c).model_copy(update={"stats": campaign_stats(s, c.id)})


@router.get("/campaigns", response_model=list[S.CampaignOut], tags=["campañas"])
def list_campaigns(s: DB, _: Who):
    return [camp_out(s, c) for c in s.scalars(select(Campaign).order_by(Campaign.started_at.desc().nulls_last(),
                                                                       Campaign.id.desc()))]


def check_sequence(s: Session, steps: list[dict]) -> None:
    for i, st in enumerate(steps, 1):
        if st.get("template_id"):
            t = s.get(Template, st["template_id"])
            if not t:
                raise Invalid(f"seguimiento {i}: no existe la plantilla {st['template_id']}", field="sequence")
            if t.kind == "first":
                raise Invalid(f"seguimiento {i}: la plantilla {t.name} es de primer mail", field="sequence")


@router.post("/campaigns", response_model=S.CampaignOut, status_code=201, tags=["campañas"])
def create_campaign(body: S.CampaignIn, s: DB, _: Who):
    check_sequence(s, body.model_dump()["sequence"])
    c = Campaign(**body.model_dump())
    s.add(c)
    _commit_unique(s, f"campaña {body.slug}")
    return camp_out(s, c)


@router.get("/campaigns/{cid}", response_model=S.CampaignOut, tags=["campañas"])
def get_campaign(cid: int, s: DB, _: Who):
    return camp_out(s, one(s, Campaign, cid, f"campaña {cid}"))


@router.patch("/campaigns/{cid}", response_model=S.CampaignOut, tags=["campañas"])
def patch_campaign(cid: int, body: S.CampaignPatch, s: DB, _: Who):
    c = one(s, Campaign, cid, f"campaña {cid}")
    data = body.model_dump(exclude_unset=True)
    if data.get("sequence") is not None:
        check_sequence(s, data["sequence"])
    elif "sequence" in data:
        data["sequence"] = []
    for k, v in data.items():
        setattr(c, k, v)
    s.commit()
    return camp_out(s, c)


@router.post("/campaigns/{cid}/drafts", response_model=S.BulkDraftOut, tags=["campañas"],
             summary="Borradores de una plantilla para varios leads (los que no pueden, en skipped)")
def bulk_drafts(cid: int, body: S.BulkDraftIn, s: DB, who: Who):
    c = one(s, Campaign, cid, f"campaña {cid}")
    t = one(s, Template, body.template_id, f"plantilla {body.template_id}")
    created, skipped = [], []
    for lid in body.lead_ids:
        lead = s.get(Lead, lid)
        if not lead:
            skipped.append({"lead_id": lid, "reason": "no existe"})
            continue
        try:
            with s.begin_nested():
                created.append(M.create_draft(s, lead, campaign=c, kind=body.kind, by=who, template=t))
        except CrmError as e:
            skipped.append({"lead_id": lid, "reason": e.detail})
    s.commit()
    return {"created": [msg_out(m) for m in created], "skipped": skipped}


@router.post("/followups/drafts", response_model=S.BulkDraftOut, tags=["campañas"],
             summary="Borradores del seguimiento que le toca a cada lead (con la plantilla del paso o la elegida)")
def followup_drafts(body: S.FollowUpDraftIn, s: DB, who: Who):
    due = {d["lead"].id: d for d in M.followups_due(s)}
    t = one(s, Template, body.template_id, f"plantilla {body.template_id}") if body.template_id else None
    created, skipped = [], []
    for lid in body.lead_ids:
        d = due.get(lid)
        if not d:
            skipped.append({"lead_id": lid, "reason": "no le toca seguimiento"})
            continue
        try:
            with s.begin_nested():
                created.append(M.create_draft(s, d["lead"], campaign=d["campaign"], kind="follow_up", by=who,
                                              template=t))
        except CrmError as e:
            skipped.append({"lead_id": lid, "reason": e.detail})
    s.commit()
    return {"created": [msg_out(m) for m in created], "skipped": skipped}


# --- Plantillas ---

@router.get("/templates", response_model=list[S.TemplateOut], tags=["plantillas"])
def list_templates(s: DB, _: Who, archived: bool = False):
    q = select(Template)
    if not archived:
        q = q.where(Template.archived.is_(False))
    return s.scalars(q.order_by(Template.name)).all()


@router.post("/templates", response_model=S.TemplateOut, status_code=201, tags=["plantillas"])
def create_template(body: S.TemplateIn, s: DB, _: Who):
    t = Template(**body.model_dump())
    check_template(t)
    s.add(t)
    _commit_unique(s, f"plantilla {body.name}")
    return t


@router.patch("/templates/{tid}", response_model=S.TemplateOut, tags=["plantillas"])
def patch_template(tid: int, body: S.TemplatePatch, s: DB, _: Who):
    t = one(s, Template, tid, f"plantilla {tid}")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    check_template(t)
    _commit_unique(s, f"plantilla {t.name}")
    return t


@router.post("/templates/{tid}/preview", response_model=S.PreviewOut, tags=["plantillas"])
def preview(tid: int, body: S.PreviewIn, s: DB, _: Who):
    t = one(s, Template, tid, f"plantilla {tid}")
    lead = get_lead(s, body.lead_id)
    c = one(s, Campaign, body.campaign_id, f"campaña {body.campaign_id}") if body.campaign_id else None
    contact = L.primary_email(lead)
    subject, text = render(t, lead, contact, c, body.kind)
    return {"to": contact.value if contact else None, "subject": subject, "text": text}


# --- Mensajes y cola ---

@router.get("/messages", response_model=S.MessagePage, tags=["mensajes"])
def list_messages(s: DB, _: Who, lead_id: int | None = None, campaign_id: int | None = None,
                  status: str | None = Query(None, description="Uno o varios, separados por coma"),
                  direction: str | None = None, kind: str | None = None,
                  limit: int = Query(100, le=500), offset: int = 0):
    q = select(Message)
    if lead_id:
        q = q.where(Message.lead_id == lead_id)
    if campaign_id:
        q = q.where(Message.campaign_id == campaign_id)
    if status:
        q = q.where(Message.status.in_(status.split(",")))
    if direction:
        q = q.where(Message.direction == direction)
    if kind:
        q = q.where(Message.kind == kind)
    total = s.scalar(select(func.count()).select_from(q.subquery()))
    items = s.scalars(q.order_by(func.coalesce(Message.sent_at, Message.queued_at, Message.created_at).desc(),
                                 Message.id.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [msg_out(m) for m in items]}


@router.post("/messages", response_model=S.MessageOut, status_code=201, tags=["mensajes"],
             summary="Borrador (no sale hasta que el usuario lo aprueba)")
def create_draft(body: S.DraftIn, s: DB, who: Who):
    c = one(s, Campaign, body.campaign_id, f"campaña {body.campaign_id}") if body.campaign_id else None
    t = one(s, Template, body.template_id, f"plantilla {body.template_id}") if body.template_id else None
    m = M.create_draft(s, get_lead(s, body.lead_id), campaign=c, kind=body.kind, by=who, template=t,
                       subject=body.subject, text=body.text, to=body.to)
    s.commit()
    return msg_out(m)


@router.patch("/messages/{mid}", response_model=S.MessageOut, tags=["mensajes"], summary="Editar un borrador")
def edit_draft(mid: int, body: S.DraftPatch, s: DB, _: Who):
    m = one(s, Message, mid, f"mensaje {mid}")
    if m.status != "draft":
        raise Conflict(f"mensaje {mid}: está {m.status}, solo se editan borradores")
    for k in ("subject", "text"):
        v = getattr(body, k)
        if v:
            setattr(m, k, v)
    s.commit()
    return msg_out(m)


@router.post("/messages/approve", response_model=list[S.MessageOut], tags=["mensajes"],
             summary="Aprobar borradores: pasan a la cola (solo el usuario)")
def approve(body: S.IdsIn, s: DB, _: UserOnly):
    out = M.approve(s, body.ids)
    s.commit()
    return [msg_out(m) for m in out]


@router.post("/messages/{mid}/cancel", response_model=S.MessageOut, tags=["mensajes"])
def cancel(mid: int, s: DB, _: Who):
    m = one(s, Message, mid, f"mensaje {mid}")
    M.cancel(s, m)
    s.commit()
    return msg_out(m)


@router.post("/messages/import", response_model=S.MessageOut, status_code=201, tags=["mensajes"],
             summary="Cargar un mail historico ya enviado o recibido (solo el usuario)")
def import_message(body: S.MessageImport, s: DB, _: UserOnly):
    get_lead(s, body.lead_id)
    if body.resend_id and s.scalar(select(Message.id).where(Message.resend_id == body.resend_id)):
        raise Conflict(f"resend_id {body.resend_id}: ya cargado")
    sent_at = naive_utc(body.sent_at)
    m = Message(**body.model_dump(exclude={"sent_at"}), sent_at=sent_at, created_by="importacion")
    s.add(m)
    s.flush()
    if body.status == "bounced":
        M.on_bounce(s, m)
    s.commit()
    return msg_out(m)


@router.get("/queue", tags=["mensajes"], summary="Estado de la cola de envio")
def queue(s: DB, _: Who):
    return sending.status(s)


@router.post("/events/check", tags=["mensajes"],
             summary="Revisar ya en Resend entregas y rebotes de lo enviado (en segundo plano)")
def events_check(tasks: BackgroundTasks, _: UserOnly):
    if sending.events_running():
        return {"started": False, "running": True}
    tasks.add_task(sending.check_events_now)
    return {"started": True, "running": True}


# --- Blocklist ---

@router.get("/blocklist", response_model=list[S.BlockOut], tags=["blocklist"])
def list_blocks(s: DB, _: Who, value: str | None = None):
    q = select(Block)
    if value:
        q = q.where(Block.value == value.lower())
    return s.scalars(q.order_by(Block.created_at.desc())).all()


@router.post("/blocklist", response_model=S.BlockOut, status_code=201, tags=["blocklist"])
def add_block(body: S.BlockIn, s: DB, _: Who):
    b = L.block(s, body.value, body.reason, body.note)
    for m in s.scalars(select(Message).where(Message.to_addr == b.value, Message.status.in_(("draft", "queued")))):
        m.status, m.error = "canceled", "blocklist"
    s.commit()
    return b


@router.delete("/blocklist/{bid}", status_code=204, tags=["blocklist"])
def delete_block(bid: int, s: DB, _: UserOnly):
    s.delete(one(s, Block, bid, f"blocklist {bid}"))
    s.commit()


# --- GA ---

@router.post("/ga/sync", tags=["ga"], summary="Bajar el reporte de GA (por defecto, los ultimos 3 dias)")
def ga_sync(s: DB, _: UserOnly, start: datetime.date | None = None, end: datetime.date | None = None):
    try:
        return GA.sync(s, start, end)
    except GA.GaError as e:
        raise CrmError(str(e)) from e


@router.post("/ga/visits", tags=["ga"], summary="Cargar filas del reporte a mano (historico)")
def ga_import(rows: list[S.GaRow], s: DB, _: UserOnly):
    return GA.store(s, [r.model_dump() for r in rows])


@router.get("/ga/visits", response_model=list[S.GaVisitOut], tags=["ga"])
def ga_visits(s: DB, _: Who, lead_id: int | None = None, unmatched: bool = False, limit: int = 500):
    q = select(GaVisit)
    if lead_id:
        q = q.where(GaVisit.lead_id == lead_id)
    if unmatched:
        q = q.where(GaVisit.lead_id.is_(None))
    return s.scalars(q.order_by(GaVisit.date.desc()).limit(limit)).all()


# --- Hoy y tablero ---

@router.get("/today", tags=["tablero"], summary="Lo que hay que hacer hoy")
def today(s: DB, _: Who):
    due = M.followups_due(s)
    drafts = s.scalars(select(Message).where(Message.status == "draft").order_by(Message.created_at)).all()
    tasks = s.scalars(select(Activity).where(Activity.kind == "task", Activity.done.is_(False))
                      .order_by(Activity.due_at.nulls_last())).all()
    week = utcnow() - datetime.timedelta(days=7)
    replies = s.scalars(select(Message).where(Message.direction == "in", Message.sent_at >= week)
                        .order_by(Message.sent_at.desc())).all()
    actions = s.scalars(select(Lead).where(Lead.next_action_at <= local_today(),
                                           Lead.stage.notin_(CLOSED_STAGES)).order_by(Lead.next_action_at)).all()
    lead_sum = {x.id: x for x in summaries(s, [d["lead"] for d in due])}
    return {
        "follow_ups_due": [S.FollowUpDue(lead=lead_sum[d["lead"].id],
                                         campaign_id=d["campaign"].id if d["campaign"] else None,
                                         campaign_slug=d["campaign"].slug if d["campaign"] else None,
                                         step=d["step"], template_id=d["template_id"],
                                         last_message_id=d["message"].id, sent_at=d["message"].sent_at,
                                         business_days=d["business_days"]) for d in due],
        "drafts": [msg_out(m) for m in drafts],
        "tasks": [S.ActivityOut.model_validate(a) for a in tasks],
        "replies": [msg_out(m) for m in replies],
        "next_actions": summaries(s, actions),
        "queue": sending.status(s),
    }


@router.get("/stats", tags=["tablero"], summary="Numeros generales (el 'Resumen' del seguimiento)")
def stats(s: DB, _: Who):
    by_stage = dict(s.execute(select(Lead.stage, func.count(Lead.id)).group_by(Lead.stage)).all())
    out_msgs = dict(s.execute(select(Message.kind, func.count(func.distinct(Message.lead_id))).where(
        Message.direction == "out", Message.status.in_(SENT_STATUSES)).group_by(Message.kind)).all())
    return {
        "leads": sum(by_stage.values()),
        "by_stage": {k: by_stage.get(k, 0) for k in STAGES},
        "contacted": out_msgs.get("first", 0),
        "followed_up": out_msgs.get("follow_up", 0),
        # Mensaje entrante registrado o etapa de respuesta en adelante (respuestas por telefono o LinkedIn).
        "replied": s.scalar(select(func.count(Lead.id)).where(
            Lead.stage.in_(REPLIED_STAGES) | Lead.id.in_(select(Message.lead_id).where(Message.direction == "in")))) or 0,
        "bounced_addresses": s.scalar(select(func.count(Block.id)).where(Block.reason == "bounce")) or 0,
        "with_clicks": s.scalar(select(func.count(func.distinct(GaVisit.lead_id)))) or 0,
        "sent_last_7d": s.scalar(select(func.count(Message.id)).where(
            Message.direction == "out", Message.status.in_(SENT_STATUSES),
            Message.sent_at >= utcnow() - datetime.timedelta(days=7))) or 0,
    }

