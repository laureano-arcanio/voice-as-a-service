"""Acceso a wa_accounts, wa_threads y wa_messages (modelos en app/models/whatsapp.py).

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama,
salvo save_inbound y claim_inbound (el dedupe y el reclamo necesitan el commit para valer).
"""
import datetime
import re

from sqlalchemy import and_, null, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import Agent, Client, WaAccount, WaMessage, WaThread
from ..services.errors import Conflict, Invalid, NotFound
from . import crypto

# Estados de un saliente: nunca retrocede (los statuses llegan fuera de orden); failed gana.
OUT_RANK = {"sent": 1, "delivered": 2, "read": 3}
ACCOUNT_FIELDS = ("agent_id", "display_phone_number", "name", "access_token", "active", "waba_id")
ACCOUNT_STATUSES = ("connected", "pending", "disconnected")


# --- Cuentas ---

def list_accounts(s: Session, client_id: str | None = None) -> list[WaAccount]:
    q = select(WaAccount).order_by(WaAccount.created_at)
    if client_id is not None:
        q = q.where(WaAccount.client_id == client_id)
    return list(s.scalars(q))


def get_account(s: Session, account_id: str) -> WaAccount | None:
    return s.get(WaAccount, account_id)


def account_by_pnid(s: Session, phone_number_id: str) -> WaAccount | None:
    return s.scalar(select(WaAccount).where(WaAccount.phone_number_id == phone_number_id))


def accounts_by_waba(s: Session, waba_id: str) -> list[WaAccount]:
    return list(s.scalars(select(WaAccount).where(WaAccount.waba_id == waba_id)))


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def check_agent(s: Session, client_id: str, agent_id: str) -> None:
    agent = s.get(Agent, agent_id)
    if agent is None or agent.client_id != client_id:
        raise NotFound("Agente inexistente para este cliente")
    if agent.archived_at is not None:
        raise Invalid("El agente esta archivado")


def create_account(s: Session, *, client_id: str, agent_id: str, phone_number_id: str, waba_id: str,
                   display_phone_number: str, name: str = "", access_token: str | None = None,
                   **extra) -> WaAccount:
    """Alta. access_token en claro: se guarda cifrado (TokenKeyMissing sin WA_TOKEN_KEY).
    extra: columnas de la fase 2 (status, source, business_id, connected_by, ...)."""
    if s.get(Client, client_id) is None:
        raise NotFound("Cliente inexistente")
    check_agent(s, client_id, agent_id)
    phone_number_id = phone_number_id.strip()
    if not re.fullmatch(r"\d{1,32}", phone_number_id):
        raise Invalid("phone_number_id: solo digitos (el ID del numero en Meta)")
    if account_by_pnid(s, phone_number_id) is not None:
        raise Conflict(f"El numero {phone_number_id} ya esta conectado")
    account = WaAccount(client_id=client_id, agent_id=agent_id, phone_number_id=phone_number_id,
                        waba_id=waba_id.strip(), display_phone_number=display_phone_number.strip(),
                        name=name, access_token=crypto.encrypt(access_token) if access_token else None,
                        active=True, **extra)
    s.add(account)
    s.flush()
    return account


def update_account(s: Session, account: WaAccount, **changes) -> WaAccount:
    unknown = set(changes) - set(ACCOUNT_FIELDS)
    if unknown:
        raise Invalid(f"Campos no editables: {', '.join(sorted(unknown))}")
    if "agent_id" in changes and changes["agent_id"] != account.agent_id:
        check_agent(s, account.client_id, changes["agent_id"])
    if "access_token" in changes:
        # "" lo borra: vuelve al token global. Si no, se cifra.
        changes["access_token"] = crypto.encrypt(changes["access_token"]) if changes["access_token"] else None
    for key, value in changes.items():
        setattr(account, key, value)
    s.flush()
    return account


def mark_status(s: Session, account: WaAccount, status: str, reason: str | None = None) -> None:
    """Cambia el estado de la conexion (visible en la UI). Sin cambio, no toca la fecha."""
    if status not in ACCOUNT_STATUSES:
        raise ValueError(f"estado invalido: {status}")
    reason = reason[:255] if reason else None
    if account.status != status or account.status_reason != reason or account.status_changed_at is None:
        account.status, account.status_reason, account.status_changed_at = status, reason, utcnow()
    s.flush()


def has_own_token(account: WaAccount) -> bool:
    return bool(account.access_token)


def token_for(account: WaAccount) -> str:
    """El token de la cuenta (descifrado) o el del system user. TokenKeyMissing si hay
    uno cifrado y WA_TOKEN_KEY no esta o no lo descifra."""
    return crypto.decrypt(account.access_token) or settings.wa_access_token


def pin_for(account: WaAccount) -> str | None:
    return crypto.decrypt(account.pin_enc)


# --- Hilos ---

def active_thread(s: Session, account_id: str, wa_id: str, now: datetime.datetime,
                  session_hours: float) -> WaThread | None:
    """La conversacion en curso con este contacto: la ultima, no pausada y con un mensaje
    del cliente dentro de las ultimas session_hours. Aunque el agente la haya dado por
    completada: por WhatsApp el chat sigue (un "si" despues del cierre no es otra
    conversacion), asi que se retoma con el historial. Corta por inactividad, por tope o
    porque la cerraron desde el dashboard (close_thread)."""
    since = now - datetime.timedelta(hours=session_hours)
    return s.scalar(
        select(WaThread)
        .where(WaThread.account_id == account_id, WaThread.wa_id == wa_id,
               WaThread.paused.is_(False), WaThread.closed_at.is_(None), WaThread.last_user_at >= since)
        .order_by(WaThread.created_at.desc()).limit(1))


def last_thread(s: Session, account_id: str, wa_id: str) -> WaThread | None:
    """La ultima conversacion con este contacto, cualquiera sea su estado."""
    return s.scalar(select(WaThread).where(WaThread.account_id == account_id, WaThread.wa_id == wa_id)
                    .order_by(WaThread.created_at.desc()).limit(1))


def add_thread(s: Session, *, conversation_id: str, account: WaAccount, wa_id: str,
               contact_name: str | None) -> WaThread:
    now = utcnow()
    thread = WaThread(conversation_id=conversation_id, account_id=account.id, client_id=account.client_id,
                      wa_id=wa_id, contact_name=(contact_name or None) and contact_name[:128],
                      last_user_at=now, created_at=now)
    s.add(thread)
    s.flush()
    return thread


def close_thread(s: Session, thread: WaThread) -> None:
    """La conversacion termino (cerrada desde el dashboard, tope de turnos o vencida): no se
    retoma, y el proximo mensaje del contacto empieza otra, con la version vigente del agente.
    Quien la cierra llama a engine.finish, como el corte de una llamada."""
    thread.closed_at = thread.closed_at or utcnow()


def expired_threads(s: Session, now: datetime.datetime, session_hours: float) -> list[WaThread]:
    """Las que vencieron (session_hours sin mensajes del contacto) y siguen sin cerrar. Las
    pausadas no: las atiende una persona."""
    since = now - datetime.timedelta(hours=session_hours)
    return list(s.scalars(select(WaThread).where(
        WaThread.closed_at.is_(None), WaThread.paused.is_(False), WaThread.last_user_at < since)))


def touch_thread(s: Session, conversation_id: str, at: datetime.datetime) -> None:
    thread = s.get(WaThread, conversation_id)
    if thread is not None and (thread.last_user_at is None or at > thread.last_user_at):
        thread.last_user_at = at


# --- Mensajes ---

# Entrantes durables (H03): received -> processing -> answered | ignored | error.
DONE_STATUSES = ("answered", "ignored", "error")


def save_inbound(s: Session, *, wamid: str, account_id: str | None, wa_id: str, type: str,
                 meta_ts: datetime.datetime | None, body: dict) -> bool:
    """Guarda el entrante con su cuerpo (commit) antes de responderle 200 a Meta. True si hay
    que procesarlo: es nuevo o Meta reenvio uno que sigue `received` (no se descarta: puede
    ser de un proceso que cayo). False si ya esta en proceso o terminado."""
    s.add(WaMessage(wamid=wamid, account_id=account_id, direction="in", wa_id=wa_id, type=type,
                    status="received", meta_ts=meta_ts, body=body))
    try:
        s.commit()
        return True
    except IntegrityError:
        s.rollback()
    prev = s.scalar(select(WaMessage).where(WaMessage.wamid == wamid))
    if prev is None or prev.direction != "in" or prev.status != "received":
        return False
    if prev.body is None:       # fila anterior a la 0009 (sin cuerpo): el reenvio la completa
        prev.body = body
        s.commit()
    return True


def claim_inbound(s: Session, wamid: str, stale_before: datetime.datetime | None = None) -> WaMessage | None:
    """Reclamo atomico (commit): received -> processing, suma un intento. Con stale_before,
    tambien uno processing colgado (claimed_at anterior). None si otro lo tiene o ya termino."""
    cond = WaMessage.status == "received"
    if stale_before is not None:
        cond = or_(cond, and_(WaMessage.status == "processing",
                              or_(WaMessage.claimed_at.is_(None), WaMessage.claimed_at < stale_before)))
    n = s.execute(update(WaMessage).where(WaMessage.wamid == wamid, WaMessage.direction == "in", cond)
                  .values(status="processing", claimed_at=utcnow(), attempts=WaMessage.attempts + 1)
                  .execution_options(synchronize_session=False)).rowcount
    s.commit()
    if n != 1:
        return None
    return s.scalar(select(WaMessage).where(WaMessage.wamid == wamid).execution_options(populate_existing=True))


def stale_inbound(s: Session, before: datetime.datetime, limit: int = 200) -> list[str]:
    """wamids sin terminar que nadie atiende: received desde antes de `before`, o processing
    reclamado antes (el proceso cayo o se colgo). Los mas viejos primero."""
    return list(s.scalars(
        select(WaMessage.wamid).where(
            WaMessage.direction == "in",
            or_(and_(WaMessage.status == "received", WaMessage.created_at < before),
                and_(WaMessage.status == "processing",
                     or_(WaMessage.claimed_at.is_(None), WaMessage.claimed_at < before))))
        .order_by(WaMessage.created_at).limit(limit)))


def link_inbound(s: Session, wamids: list[str], conversation_id: str) -> None:
    """El turno los tomo: quedan con su conversacion y el reclamo renovado (siguen processing)."""
    if wamids:
        s.execute(update(WaMessage).where(WaMessage.wamid.in_(wamids), WaMessage.direction == "in")
                  .values(conversation_id=conversation_id, claimed_at=utcnow())
                  .execution_options(synchronize_session=False))


def mark_replying(s: Session, wamids: list[str]) -> None:
    """processed_at antes de mandar la respuesta a Meta: si el proceso cae en el envio, la
    recuperacion no la reenvia a ciegas (el turno ya esta en la conversacion)."""
    if wamids:
        s.execute(update(WaMessage).where(WaMessage.wamid.in_(wamids), WaMessage.direction == "in")
                  .values(processed_at=utcnow()).execution_options(synchronize_session=False))


def set_inbound(s: Session, wamids: list[str], *, status: str, conversation_id: str | None = None,
                error: dict | None = None) -> None:
    """Estado final. answered e ignored borran el cuerpo (la conversacion ya tiene el texto);
    error lo deja para revisarlo, hasta que lo borre la retencion."""
    if not wamids:
        return
    now = utcnow()
    for msg in s.scalars(select(WaMessage).where(WaMessage.wamid.in_(wamids), WaMessage.direction == "in")):
        msg.status = status
        if conversation_id is not None:
            msg.conversation_id = conversation_id
        if status in DONE_STATUSES:
            msg.processed_at = msg.processed_at or now
            msg.claimed_at = None
        if status in ("answered", "ignored") and msg.body is not None:
            msg.body = null()       # SQL NULL, no el null de JSON
        if error is not None:
            msg.error = error


def _advance(current: str, new: str) -> str:
    if current == "failed" or new == "failed":
        return "failed"
    return new if OUT_RANK.get(new, 0) > OUT_RANK.get(current, 0) else current


def record_outbound(s: Session, *, wamid: str | None, account_id: str | None, conversation_id: str | None,
                    wa_id: str, type: str, status: str = "sent", error: dict | None = None) -> WaMessage:
    """Upsert por wamid: si un status llego antes que la respuesta de send_text, la fila
    ya existe; se completa y se conserva el estado mas avanzado."""
    msg = s.scalar(select(WaMessage).where(WaMessage.wamid == wamid)) if wamid else None
    if msg is None:
        msg = WaMessage(wamid=wamid, account_id=account_id, conversation_id=conversation_id, direction="out",
                        wa_id=wa_id, type=type, status=status, error=error)
        s.add(msg)
    else:
        msg.conversation_id = msg.conversation_id or conversation_id
        msg.account_id = msg.account_id or account_id
        msg.type = type
        msg.status = _advance(msg.status, status)
        msg.error = msg.error or error
    s.flush()
    return msg


def apply_status(s: Session, *, wamid: str, status: str, error: dict | None,
                 meta_ts: datetime.datetime | None, account_id: str | None, wa_id: str) -> None:
    """Webhook statuses (sent/delivered/read/failed) de un saliente."""
    msg = s.scalar(select(WaMessage).where(WaMessage.wamid == wamid))
    if msg is None:
        # Llego antes que la respuesta de send_text, o es de un envio fuera de la app (scripts/wa.py).
        s.add(WaMessage(wamid=wamid, account_id=account_id, direction="out", wa_id=wa_id, type="other",
                        status=status, error=error if status == "failed" else None, meta_ts=meta_ts))
        return
    msg.status = _advance(msg.status, status)
    if status == "failed":
        msg.error = error
    if meta_ts is not None:
        msg.meta_ts = meta_ts
