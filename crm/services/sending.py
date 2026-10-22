"""Cola de envio y estado de lo enviado.

Cola: un mail `queued` por ventana (CRM_SEND_WINDOW_SECONDS), en un momento al azar, con al menos
CRM_SEND_MIN_GAP_SECONDS entre dos, solo en horario habil y hasta CRM_SEND_DAILY_MAX por dia.
Antes de cada uno vuelve a chequear blocklist, no contactar y si el lead respondio.

Eventos: lee de Resend el ultimo evento de lo enviado en los ultimos CRM_EVENTS_DAYS dias (cada
CRM_EVENTS_INTERVAL_SECONDS o a pedido, con el boton del Tablero; nunca dos a la vez).

Secuencias: en el mismo loop, arma los borradores de los seguimientos que tienen plantilla.
"""
import asyncio
import datetime
import logging
import random
import threading
import time
import zoneinfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_sessionmaker, utcnow
from ..models import KV, Message
from . import leads as L
from . import messages as M
from . import resend

logger = logging.getLogger(__name__)
NEXT_KEY = "send.next_at"
EVENTS_KEY = "events.last"
_events_lock = threading.Lock()


def _local_now() -> datetime.datetime:
    return datetime.datetime.now(zoneinfo.ZoneInfo(settings.send_timezone))


def in_hours(now: datetime.datetime | None = None) -> bool:
    now = now or _local_now()
    start, end = (int(x) for x in settings.send_hours.split("-"))
    return now.weekday() < 5 and start <= now.hour < end


def sent_today(s: Session) -> int:
    local = _local_now()
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(datetime.UTC).replace(tzinfo=None)
    return s.scalar(select(func.count(Message.id)).where(
        Message.direction == "out", Message.sent_at >= start_utc, Message.resend_id.isnot(None),
        Message.status.notin_(("failed", "canceled")))) or 0


def _get_next(s: Session) -> float:
    kv = s.get(KV, NEXT_KEY)
    return float(kv.value.get("t", 0)) if kv else 0.0


def _set_next(s: Session, t: float) -> None:
    kv = s.get(KV, NEXT_KEY) or KV(key=NEXT_KEY, value={})
    kv.value = {"t": t}
    s.add(kv)


def status(s: Session) -> dict:
    queued = s.scalar(select(func.count(Message.id)).where(Message.status == "queued")) or 0
    nxt = _get_next(s)
    return {"enabled": settings.send_enabled and bool(settings.resend_api_key), "queued": queued,
            "sent_today": sent_today(s), "daily_max": settings.send_daily_max, "in_hours": in_hours(),
            "hours": settings.send_hours, "window_seconds": settings.send_window_seconds,
            "next_at": datetime.datetime.fromtimestamp(nxt, datetime.UTC).isoformat() if nxt else None,
            "events_running": _events_lock.locked(), "events_last": (s.get(KV, EVENTS_KEY) or KV(value={})).value}


def send_one(s: Session, m: Message) -> None:
    """Manda un mensaje de la cola (o lo cancela si ya no corresponde)."""
    lead = m.lead
    reason = None
    if lead.do_not_contact:
        reason = "no contactar"
    elif L.is_blocked(s, m.to_addr):
        reason = "en la blocklist"
    elif s.scalar(select(Message.id).where(Message.lead_id == lead.id, Message.direction == "in",
                                           Message.created_at >= m.created_at)):
        reason = "respondió"
    if reason:
        m.status, m.error = "canceled", reason
        return
    try:
        rid = resend.send(idempotency_key=f"crm-msg-{m.id}", from_addr=m.from_addr or settings.mail_from,
                          to=m.to_addr, subject=m.subject, text=m.text, in_reply_to=m.in_reply_to,
                          bcc=settings.mail_bcc or None)
    except resend.ResendError as e:
        m.status, m.error = "failed", str(e)[:500]
        logger.warning("crm: mensaje %s fallo: %s", m.id, e)
        return
    M.mark_sent(s, m, rid)
    logger.info("crm: mensaje %s enviado a %s (%s)", m.id, m.to_addr, rid)


def tick(s: Session, now: float | None = None) -> Message | None:
    """Un paso de la cola: manda uno si toca. Devuelve el mensaje procesado."""
    now = now or time.time()
    if not (settings.send_enabled and settings.resend_api_key) or not in_hours():
        return None
    if sent_today(s) >= settings.send_daily_max or now < _get_next(s):
        return None
    m = s.scalar(select(Message).where(Message.status == "queued").order_by(Message.queued_at, Message.id)
                 .limit(1))
    if not m:
        return None
    send_one(s, m)
    w = settings.send_window_seconds
    _set_next(s, now + max(settings.send_min_gap_seconds, random.uniform(0.5 * w, 1.5 * w)))
    s.commit()
    return m


def check_events(s: Session) -> int | None:
    """Lee los eventos; None si ya hay una revision en curso."""
    if not _events_lock.acquire(blocking=False):
        return None
    try:
        n = _check_events(s)
        kv = s.get(KV, EVENTS_KEY) or KV(key=EVENTS_KEY, value={})
        kv.value = {"at": utcnow().isoformat() + "Z", "changed": n}
        s.add(kv)
        s.commit()
        return n
    finally:
        _events_lock.release()


def events_running() -> bool:
    return _events_lock.locked()


def check_events_now() -> None:
    """Para el boton: corre en segundo plano con su propia sesion."""
    with get_sessionmaker()() as s:
        check_events(s)


def _check_events(s: Session) -> int:
    # Un entregado puede rebotar despues (rebote asincronico), pero casi siempre en el dia: se
    # revisan los "sent" de CRM_EVENTS_DAYS y los "delivered" de los ultimos 3 dias. Resend limita
    # a 2 pedidos por segundo: una pausa entre cada uno.
    now = utcnow()
    recent = now - datetime.timedelta(minutes=5)
    msgs = s.scalars(select(Message).where(
        Message.direction == "out", Message.resend_id.isnot(None),
        ((Message.status == "sent") & (Message.sent_at >= now - datetime.timedelta(days=settings.events_days)))
        | ((Message.status == "delivered") & (Message.sent_at >= now - datetime.timedelta(days=3))),
        (Message.events_checked_at.is_(None)) | (Message.events_checked_at < recent))).all()
    n = 0
    for i, m in enumerate(msgs):
        if i:
            time.sleep(0.6)
        try:
            d = resend.get(m.resend_id)
        except resend.ResendError as e:
            logger.warning("crm: estado de %s: %s", m.resend_id, e)
            continue
        m.events_checked_at = utcnow()
        if d.get("message_id") and not m.message_id:
            m.message_id = d["message_id"]
        ev = d.get("last_event")
        if ev and ev not in ("sent", "queued", "scheduled"):
            M.mark_event(s, m, ev)
            n += 1
        s.commit()
    return n


async def send_loop() -> None:
    while True:
        try:
            with get_sessionmaker()() as s:
                await asyncio.to_thread(tick, s)
        except Exception:
            logger.exception("crm: cola de envio")
        await asyncio.sleep(5)


async def events_loop() -> None:
    while True:
        try:
            with get_sessionmaker()() as s:
                await asyncio.to_thread(check_events, s)
        except Exception:
            logger.exception("crm: eventos de Resend")
        try:
            with get_sessionmaker()() as s:
                n = await asyncio.to_thread(M.auto_followups, s)
                if n:
                    logger.info("crm: %s seguimientos armados para aprobar", n)
        except Exception:
            logger.exception("crm: seguimientos de las secuencias")
        await asyncio.sleep(settings.events_interval_seconds)
