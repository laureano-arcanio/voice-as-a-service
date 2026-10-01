"""Acceso a wa_accounts, wa_threads y wa_messages (modelos en app/models/whatsapp.py).

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama,
salvo record_inbound (el dedupe necesita el commit para valer).
"""
import datetime
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import Agent, Client, ConversationRow, WaAccount, WaMessage, WaThread
from ..services.errors import Conflict, Invalid, NotFound

# Estados de un saliente: nunca retrocede (los statuses llegan fuera de orden); failed gana.
OUT_RANK = {"sent": 1, "delivered": 2, "read": 3}
ACCOUNT_FIELDS = ("agent_id", "display_phone_number", "name", "access_token", "active", "waba_id")


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


def _check_agent(s: Session, client_id: str, agent_id: str) -> None:
    agent = s.get(Agent, agent_id)
    if agent is None or agent.client_id != client_id:
        raise NotFound("Agente inexistente para este cliente")
    if agent.archived_at is not None:
        raise Invalid("El agente esta archivado")


def create_account(s: Session, *, client_id: str, agent_id: str, phone_number_id: str, waba_id: str,
                   display_phone_number: str, name: str = "", access_token: str | None = None) -> WaAccount:
    if s.get(Client, client_id) is None:
        raise NotFound("Cliente inexistente")
    _check_agent(s, client_id, agent_id)
    phone_number_id = phone_number_id.strip()
    if not re.fullmatch(r"\d{1,32}", phone_number_id):
        raise Invalid("phone_number_id: solo digitos (el ID del numero en Meta)")
    if account_by_pnid(s, phone_number_id) is not None:
        raise Conflict(f"El numero {phone_number_id} ya esta conectado")
    account = WaAccount(client_id=client_id, agent_id=agent_id, phone_number_id=phone_number_id,
                        waba_id=waba_id.strip(), display_phone_number=display_phone_number.strip(),
                        name=name, access_token=access_token or None, active=True)
    s.add(account)
    s.flush()
    return account


def update_account(s: Session, account: WaAccount, **changes) -> WaAccount:
    unknown = set(changes) - set(ACCOUNT_FIELDS)
    if unknown:
        raise Invalid(f"Campos no editables: {', '.join(sorted(unknown))}")
    if "agent_id" in changes and changes["agent_id"] != account.agent_id:
        _check_agent(s, account.client_id, changes["agent_id"])
    if "access_token" in changes:
        changes["access_token"] = changes["access_token"] or None   # "" lo borra: vuelve al token global
    for key, value in changes.items():
        setattr(account, key, value)
    s.flush()
    return account


def token_for(account: WaAccount) -> str:
    return account.access_token or settings.wa_access_token


# --- Hilos ---

def active_thread(s: Session, account_id: str, wa_id: str, now: datetime.datetime,
                  session_hours: float) -> WaThread | None:
    """La conversacion en curso con este contacto: la ultima, activa, no pausada y con
    un mensaje del cliente dentro de las ultimas session_hours."""
    since = now - datetime.timedelta(hours=session_hours)
    return s.scalar(
        select(WaThread).join(ConversationRow, ConversationRow.id == WaThread.conversation_id)
        .where(WaThread.account_id == account_id, WaThread.wa_id == wa_id,
               ConversationRow.status == "active", WaThread.paused.is_(False), WaThread.last_user_at >= since)
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


def touch_thread(s: Session, conversation_id: str, at: datetime.datetime) -> None:
    thread = s.get(WaThread, conversation_id)
    if thread is not None and (thread.last_user_at is None or at > thread.last_user_at):
        thread.last_user_at = at


# --- Mensajes ---

def record_inbound(s: Session, *, wamid: str, account_id: str | None, wa_id: str, type: str,
                   meta_ts: datetime.datetime | None) -> bool:
    """Registra el entrante y hace commit. False si el wamid ya estaba: Meta reenvia."""
    s.add(WaMessage(wamid=wamid, account_id=account_id, direction="in", wa_id=wa_id, type=type,
                    status="received", meta_ts=meta_ts))
    try:
        s.commit()
    except IntegrityError:
        s.rollback()
        return False
    return True


def set_inbound(s: Session, wamids: list[str], *, status: str, conversation_id: str | None = None) -> None:
    if not wamids:
        return
    for msg in s.scalars(select(WaMessage).where(WaMessage.wamid.in_(wamids), WaMessage.direction == "in")):
        msg.status = status
        if conversation_id is not None:
            msg.conversation_id = conversation_id


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
