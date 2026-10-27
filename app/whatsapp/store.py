"""Acceso a wa_accounts, wa_threads y wa_messages (modelos en app/models/whatsapp.py).

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama,
salvo record_inbound (el dedupe necesita el commit para valer).
"""
import datetime
import re

from sqlalchemy import event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import Agent, Client, WaAccount, WaAccountStatusLog, WaMessage, WaThread
from ..models._common import new_id
from ..services import limits
from ..services.errors import Conflict, Invalid, NotFound
from . import crypto

# Estados de un saliente: nunca retrocede (los statuses llegan fuera de orden); failed gana.
OUT_RANK = {"sent": 1, "delivered": 2, "read": 3}
ACCOUNT_FIELDS = ("agent_id", "display_phone_number", "name", "access_token", "active", "waba_id")
ACCOUNT_STATUSES = ("connected", "pending", "disconnected")


# --- Cuentas ---

STATUS_LOG_FIELDS = ("status", "quality_rating", "messaging_limit")


@event.listens_for(Session, "before_flush")
def _log_account_status(s: Session, _ctx, _instances) -> None:
    """Historial de estado, calidad y limite de las cuentas (wa_account_status_log, docs/REPORTES_PLAN.md): una
    fila al crear la cuenta y otra cada vez que cambia alguno de los tres, venga de donde venga (webhook de Meta,
    chequeo, conexion o la API)."""
    for obj in [*s.new, *s.dirty]:
        if not isinstance(obj, WaAccount):
            continue
        if obj in s.new:
            obj.id = obj.id or new_id()
        else:
            state = inspect(obj)
            if not any(state.attrs[f].history.has_changes() for f in STATUS_LOG_FIELDS):
                continue
        s.add(WaAccountStatusLog(account_id=obj.id, status=obj.status or "connected",
                                 quality_rating=obj.quality_rating, messaging_limit=obj.messaging_limit, at=utcnow()))


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
    limits.check_whatsapp(s, client_id)
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

def open_thread(s: Session, account_id: str, wa_id: str) -> WaThread | None:
    """El hilo sin cerrar con este contacto (a lo sumo uno a la vez: lo cierra el que lo da
    por vencido antes de abrir otro). No mira cuanto hace del ultimo mensaje: eso depende de
    la ventana de contexto temporal del agente que lo abrio (Workflow.wa_session_minutes, o el
    default global si no la fijo), que resuelve el que llama."""
    return s.scalar(
        select(WaThread)
        .where(WaThread.account_id == account_id, WaThread.wa_id == wa_id,
               WaThread.paused.is_(False), WaThread.closed_at.is_(None))
        .order_by(WaThread.created_at.desc()).limit(1))


def last_thread(s: Session, account_id: str, wa_id: str) -> WaThread | None:
    """La ultima conversacion con este contacto, cualquiera sea su estado."""
    return s.scalar(select(WaThread).where(WaThread.account_id == account_id, WaThread.wa_id == wa_id)
                    .order_by(WaThread.created_at.desc()).limit(1))


def add_thread(s: Session, *, conversation_id: str, account: WaAccount, wa_id: str,
               contact_name: str | None, client_id: str | None = None) -> WaThread:
    """client_id: el de la conversacion (el de un operador); sin pasarlo, el del numero."""
    now = utcnow()
    thread = WaThread(conversation_id=conversation_id, account_id=account.id,
                      client_id=client_id or account.client_id,
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


def open_threads(s: Session) -> list[WaThread]:
    """Todos los hilos sin cerrar (sweep): el que llama decide cuales vencieron, agente por
    agente. Los pausados no entran: los atiende una persona."""
    return list(s.scalars(select(WaThread).where(
        WaThread.closed_at.is_(None), WaThread.paused.is_(False))))


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
