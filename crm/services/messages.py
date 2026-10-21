"""Mensajes: borradores, aprobacion, efectos de envio y rebote, respuestas y seguimientos que vencen."""
import datetime
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import local_today, settings
from ..db import naive_utc, utcnow
from ..models import SENT_STATUSES, Campaign, ContactPoint, Lead, Message, Template
from . import leads as L
from .errors import Conflict, Invalid
from .templates import render, utm_campaign

OPEN_STAGES_FOR_REPLY = ("nuevo", "contactado", "seguimiento", "sin_respuesta")


def _thread_parent(s: Session, lead: Lead, to: str | None, campaign: Campaign | None) -> Message | None:
    """El ultimo mail saliente al lead (de la campana, si hay), para responder en su hilo."""
    q = (select(Message).where(Message.lead_id == lead.id, Message.direction == "out",
                               Message.status.in_(SENT_STATUSES))
         .order_by(Message.sent_at.desc()))
    if campaign:
        first = s.scalar(q.where(Message.campaign_id == campaign.id))
        if first:
            return first
    if to:
        first = s.scalar(q.where(Message.to_addr == to))
        if first:
            return first
    return s.scalar(q)


def create_draft(s: Session, lead: Lead, *, campaign: Campaign | None, kind: str, by: str,
                 template: Template | None = None, subject: str | None = None, text: str | None = None,
                 to: str | None = None) -> Message:
    if lead.do_not_contact:
        raise Conflict(f"{lead.name}: marcado como no contactar")
    if lead.stage in ("no_interesa", "descartado"):
        raise Conflict(f"{lead.name}: etapa {lead.stage}")
    parent = _thread_parent(s, lead, to, campaign) if kind == "follow_up" else None
    if kind == "follow_up" and not parent:
        raise Conflict(f"{lead.name}: no hay un mail enviado al que responder")
    contact: ContactPoint | None = None
    if to:
        to = L.norm_value("email", to)
        contact = next((c for c in lead.contacts if c.kind == "email" and c.value == to), None)
    elif parent:
        to = parent.to_addr
        contact = next((c for c in lead.contacts if c.kind == "email" and c.value == to), None)
    else:
        contact = L.primary_email(lead)
        if not contact:
            raise Conflict(f"{lead.name}: sin email valido")
        to = contact.value
    if L.is_blocked(s, to):
        raise Conflict(f"{to}: en la blocklist")
    if contact and contact.status != "ok":
        raise Conflict(f"{to}: {contact.status}")
    if campaign:
        dup = s.scalar(select(Message.id).where(
            Message.lead_id == lead.id, Message.campaign_id == campaign.id, Message.kind == kind,
            Message.direction == "out", Message.status.notin_(("canceled", "failed"))))
        if dup:
            raise Conflict(f"{lead.name}: ya tiene un mail '{kind}' en la campaña {campaign.slug}")
    if template:
        subject, text = render(template, lead, contact, campaign, kind)
    if not subject or not text:
        raise Invalid("falta template_id, o subject y text", field="template_id")
    if parent:
        base = parent.subject.removeprefix("Re: ").removeprefix("RE: ")
        subject = "Re: " + base
    m = Message(lead_id=lead.id, campaign_id=campaign.id if campaign else None,
                template_id=template.id if template else None, kind=kind, direction="out",
                from_addr=(campaign.from_addr if campaign and campaign.from_addr else settings.mail_from),
                to_addr=to, subject=subject, text=text, status="draft",
                in_reply_to=parent.message_id if parent else None,
                utm_campaign=utm_campaign(campaign, kind) if campaign else None, utm_content=lead.slug,
                created_by=by)
    s.add(m)
    s.flush()
    return m


def approve(s: Session, ids: list[int]) -> list[Message]:
    out = []
    for m in s.scalars(select(Message).where(Message.id.in_(ids))):
        if m.status != "draft":
            raise Conflict(f"mensaje {m.id}: está {m.status}, no es borrador")
        m.status, m.queued_at = "queued", utcnow()
        out.append(m)
    s.flush()
    return out


def cancel(s: Session, m: Message) -> None:
    if m.status not in ("draft", "queued"):
        raise Conflict(f"mensaje {m.id}: ya está {m.status}")
    m.status = "canceled"


def mark_sent(s: Session, m: Message, resend_id: str | None, at: datetime.datetime | None = None) -> None:
    m.status, m.resend_id, m.sent_at, m.error = "sent", resend_id, at or utcnow(), None
    lead = m.lead
    if m.kind == "first" and lead.stage == "nuevo":
        L.set_stage(s, lead, "contactado", "sistema")
    elif m.kind == "follow_up" and lead.stage in ("nuevo", "contactado"):
        L.set_stage(s, lead, "seguimiento", "sistema")


def mark_event(s: Session, m: Message, event: str, at: datetime.datetime | None = None) -> None:
    """Ultimo evento de Resend: delivered, bounced, complained, suppressed, failed."""
    m.last_event_at = at or utcnow()
    if event == "delivered" and m.status == "sent":
        m.status = "delivered"
    elif event in ("bounced", "suppressed", "failed") and m.status in ("sent", "delivered"):
        m.status = "bounced"
        on_bounce(s, m)
    elif event == "complained":
        m.status = "complained"
        L.block(s, m.to_addr, "complaint", f"queja en el mensaje {m.id}")
        m.lead.do_not_contact = True


def on_bounce(s: Session, m: Message) -> None:
    lead = m.lead
    L.block(s, m.to_addr, "bounce", f"rebote del mensaje {m.id}")
    for c in lead.contacts:
        if c.kind == "email" and c.value == m.to_addr:
            c.status = "bounced"
    if not L.primary_email(lead):
        L.set_stage(s, lead, "descartado", "sistema", f"rebotó {m.to_addr} y no hay otro email")


def record_inbound(s: Session, lead: Lead, *, from_addr: str, subject: str, text: str,
                   at: datetime.datetime | None, by: str, auto: bool = False) -> Message:
    """Respuesta del lead (a mano en esta version). Cambia la etapa salvo autorespuestas."""
    own = re.search(r"[\w.+-]+@[\w.-]+", settings.mail_from)
    m = Message(lead_id=lead.id, direction="in", kind="other", from_addr=from_addr,
                to_addr=own.group(0) if own else settings.mail_from, subject=subject or "(sin asunto)",
                text=text or "", status="received", sent_at=naive_utc(at) or utcnow(), created_by=by)
    parent = _thread_parent(s, lead, None, None)
    if parent:
        m.campaign_id, m.in_reply_to = parent.campaign_id, parent.message_id
    s.add(m)
    if not auto and lead.stage in OPEN_STAGES_FOR_REPLY:
        L.set_stage(s, lead, "respondio", by)
    # Lo que quedaba por salir a ese lead ya no va.
    for q in s.scalars(select(Message).where(Message.lead_id == lead.id,
                                             Message.status.in_(("draft", "queued")))):
        q.status, q.error = "canceled", "respondió"
    s.flush()
    return m


def business_days_between(a: datetime.date, b: datetime.date) -> int:
    """Dias habiles (lunes a viernes) despues de `a` hasta `b` inclusive."""
    days, d = 0, a
    while d < b:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def followups_due(s: Session, today: datetime.date | None = None) -> list[dict]:
    """Leads con primer mail enviado hace N dias habiles o mas, sin seguimiento ni respuesta."""
    today = today or local_today()
    n = settings.follow_up_business_days
    firsts = s.execute(
        select(Message, Lead).join(Lead, Lead.id == Message.lead_id)
        .where(Message.kind == "first", Message.direction == "out", Message.status.in_(("sent", "delivered")),
               Lead.stage == "contactado", Lead.do_not_contact.is_(False))
        .order_by(Message.sent_at)).all()
    out, seen = [], set()
    for m, lead in firsts:
        if lead.id in seen:
            continue
        others = s.scalar(select(func.count(Message.id)).where(
            Message.lead_id == lead.id, Message.status.notin_(("canceled", "failed")),
            ((Message.direction == "in") | (Message.kind == "follow_up"))))
        if others:
            continue
        days = business_days_between(m.sent_at.date(), today)
        if days >= n:
            seen.add(lead.id)
            out.append({"lead": lead, "message": m, "business_days": days})
    return out
