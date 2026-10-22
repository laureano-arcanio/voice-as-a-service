"""Mensajes: borradores, aprobacion, efectos de envio y rebote, respuestas y seguimientos que vencen."""
import datetime
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import local_today, settings
from ..db import naive_utc, utcnow
from ..models import (
    REPLIED_STAGES,
    SENT_STATUSES,
    Activity,
    Campaign,
    ContactPoint,
    Lead,
    Message,
    Template,
)
from . import leads as L
from .errors import Conflict, CrmError, Invalid
from .templates import render, utm_campaign

logger = logging.getLogger(__name__)
OPEN_STAGES_FOR_REPLY = ("nuevo", "contactado", "seguimiento", "sin_respuesta")


def _thread_parent(s: Session, lead: Lead, to: str | None, campaign: Campaign | None) -> Message | None:
    """El ultimo mail saliente al lead (de la campana, si hay), para responder en su hilo."""
    q = (select(Message).where(Message.lead_id == lead.id, Message.direction == "out",
                               Message.status.in_(SENT_STATUSES))
         # Sin Message-ID (eventos todavia sin leer) no se puede responder en el hilo: va al final.
         .order_by(Message.message_id.is_(None), Message.sent_at.desc()))
    if campaign:
        first = s.scalar(q.where(Message.campaign_id == campaign.id))
        if first:
            return first
    if to:
        first = s.scalar(q.where(Message.to_addr == to))
        if first:
            return first
    return s.scalar(q)


def sequence(campaign: Campaign | None) -> list[dict]:
    """Pasos de seguimiento de la campaña. Sin secuencia: uno, a los N dias habiles, sin plantilla."""
    if campaign and campaign.sequence:
        return campaign.sequence
    return [{"days": settings.follow_up_business_days, "template_id": None}]


def thread_state(msgs: list[Message]) -> tuple[Message | None, list[Message]]:
    """(ultimo primer mail enviado, seguimientos enviados despues de el) entre los mensajes de un lead."""
    sent = sorted((m for m in msgs if m.direction == "out" and m.status in SENT_STATUSES and m.sent_at),
                  key=lambda m: m.sent_at)
    first = next((m for m in reversed(sent) if m.kind == "first"), None)
    if not first:
        return None, []
    return first, [m for m in sent if m.kind == "follow_up" and m.sent_at >= first.sent_at]


def steps_done(lead: Lead, done: list[Message]) -> int:
    """Seguimientos hechos. Un lead en etapa "seguimiento" sin ninguno registrado tuvo uno por fuera del
    CRM (mandado a mano desde otro buzon, antes del CRM)."""
    return max(len(done), 1 if lead.stage == "seguimiento" else 0)


def _lead_messages(s: Session, lead: Lead) -> list[Message]:
    return s.scalars(select(Message).where(Message.lead_id == lead.id,
                                           Message.status.notin_(("canceled", "failed")))).all()


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
    step = 0 if kind == "first" else None
    if kind == "follow_up":
        msgs = _lead_messages(s, lead)
        if any(m.direction == "out" and m.kind == "follow_up" and m.status in ("draft", "queued") for m in msgs):
            raise Conflict(f"{lead.name}: ya tiene un seguimiento pendiente de salir")
        _, done = thread_state(msgs)
        step = steps_done(lead, done) + 1
        seq = sequence(campaign) if campaign else None
        if seq and step > len(seq):
            raise Conflict(f"{lead.name}: ya tiene los {len(seq)} seguimientos de la campaña {campaign.slug}")
        if not template and not text and seq and seq[step - 1].get("template_id"):
            template = s.get(Template, seq[step - 1]["template_id"])
        if not template and not text:
            raise Invalid(f"{lead.name}: la campaña no tiene plantilla para el seguimiento {step}: elegí una",
                          field="template_id")
    elif campaign:
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
                template_id=template.id if template else None, kind=kind, step=step, direction="out",
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
    """Leads que esperan el proximo paso de la secuencia de su campaña: sin respuesta, sin nada
    pendiente de salir y con el ultimo mail enviado hace los dias habiles del paso o mas."""
    today = today or local_today()
    leads = s.scalars(select(Lead).where(Lead.stage.in_(("contactado", "seguimiento")),
                                         Lead.do_not_contact.is_(False))).all()
    by_lead: dict[int, list[Message]] = {x.id: [] for x in leads}
    if leads:
        for m in s.scalars(select(Message).where(Message.lead_id.in_(by_lead),
                                                 Message.status.notin_(("canceled", "failed")))):
            by_lead[m.lead_id].append(m)
    out = []
    for lead in leads:
        msgs = by_lead[lead.id]
        if any(m.direction == "in" or m.status in ("draft", "queued") for m in msgs):
            continue
        first, done = thread_state(msgs)
        if not first or first.status == "bounced":
            continue
        seq, n = sequence(first.campaign), steps_done(lead, done)
        if n >= len(seq):
            continue
        last = done[-1] if done else first
        days = business_days_between(last.sent_at.date(), today)
        if days >= seq[n]["days"]:
            out.append({"lead": lead, "message": last, "campaign": first.campaign, "step": n + 1,
                        "template_id": seq[n].get("template_id"), "business_days": days})
    out.sort(key=lambda d: d["message"].sent_at)
    return out


def auto_followups(s: Session) -> int:
    """Borradores de los pasos que tienen plantilla, en campañas activas. Quedan para aprobar en Hoy."""
    n = 0
    for d in followups_due(s):
        c = d["campaign"]
        if not d["template_id"] or not c or c.status != "active":
            continue
        try:
            with s.begin_nested():
                create_draft(s, d["lead"], campaign=c, kind="follow_up", by="sistema")
            n += 1
        except CrmError as e:
            logger.info("crm: seguimiento %s de %s: %s", d["step"], d["lead"].name, e.detail)
    s.commit()
    return n


def reply_rates(s: Session) -> list[dict]:
    """Reply rate por nivel de la secuencia (0 el primer mail, 1.. seguimientos), en total y por campaña.
    Respondio = mensaje entrante o etapa de respuesta en adelante, como en /stats (las respuestas por telefono o
    LinkedIn se cargan cambiando la etapa). Cuenta para el ultimo mail que el lead recibio antes de responder: el
    mensaje entrante, o el cambio de etapa (sin fecha, el ultimo mail). Los rebotados no cuentan como alcanzados;
    un lead cuenta una vez por nivel y campaña."""
    msgs = s.scalars(select(Message).where(Message.sent_at.is_not(None), (Message.direction == "in") | (
        (Message.direction == "out") & Message.status.in_(SENT_STATUSES) & Message.kind.in_(("first", "follow_up"))))
        .order_by(Message.lead_id, Message.sent_at)).all()
    with_inbound = {m.lead_id for m in msgs if m.direction == "in"}
    stage_at = dict(s.execute(select(Activity.lead_id, func.min(Activity.at)).where(
        Activity.kind == "stage_change", Activity.data["to"].as_string().in_(REPLIED_STAGES))
        .group_by(Activity.lead_id)).all())
    # (lead, momento, es_respuesta, mensaje): por lead y en orden; a igual momento, el envio primero; sin
    # momento (etapa sin cambio registrado), al final
    events = [(m.lead_id, m.sent_at, m.direction == "in", m) for m in msgs]
    events += [(lid, stage_at.get(lid), True, None) for lid in s.scalars(
        select(Lead.id).where(Lead.stage.in_(REPLIED_STAGES))) if lid not in with_inbound]
    events.sort(key=lambda e: (e[0], e[1] is None, e[1] or utcnow(), e[2]))
    reached: dict[tuple, set[int]] = {}
    replied: dict[tuple, set[int]] = {}
    last: dict[int, tuple | None] = {}       # lead -> (campaña, nivel) del ultimo mail sin respuesta
    level: dict[int, int] = {}               # lead -> nivel del ultimo enviado (para los que no tienen step)
    for lid, _, is_reply, m in events:
        if is_reply:
            k = last.get(lid)
            if k:
                for key in (k, (None, k[1])):
                    replied.setdefault(key, set()).add(lid)
                last[lid] = None
            continue
        lvl = m.step if m.step is not None else (0 if m.kind == "first" else level.get(lid, 0) + 1)
        level[lid] = lvl
        if m.status == "bounced":
            continue
        k = (m.campaign.slug if m.campaign else "sin campaña", lvl)
        for key in (k, (None, lvl)):
            reached.setdefault(key, set()).add(lid)
        last[lid] = k
    out = []
    for (camp, lvl), leads in sorted(reached.items(), key=lambda x: (x[0][0] is not None, x[0][0] or "", x[0][1])):
        n = len(replied.get((camp, lvl), set()) & leads)
        out.append({"campaign_slug": camp, "step": lvl, "reached": len(leads), "replied": n,
                    "rate": round(n / len(leads), 4)})
    return out
