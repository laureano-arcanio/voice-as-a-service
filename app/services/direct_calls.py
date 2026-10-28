"""Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md): el equipo del cliente llama y atiende sin el agente.

- Saliente: un usuario del cliente (el de la sesion o, por API key o MCP, `user_id`) llama a un contacto o a
  un numero desde un numero del cliente. Se admite como `directa` (minutos salientes y un canal de Anura), la
  conversacion va sin agente y el worker (app/voice/direct.py) espera a que el usuario entre a la room para
  marcar. Por API, en vez de token, `join_url`: la pagina del panel que entra con la sesion de ese usuario.
- Entrante al equipo: services/calls.start_inbound arma el ruteo (TeamRoute) y el worker hace sonar a las
  personas; en el panel suena con `call_rings` (ring_panel) a los usuarios Disponibles y no ocupados. El
  primero que atiende (answer) se queda con la llamada.
- Presencia: Disponible = un pulso (PUT /me/presence) en los ultimos PRESENCE_TTL_SECONDS; ocupado = tiene
  una llamada activa con su user_id.
- Un admin en "ver como cliente" no llama, no atiende ni se pone Disponible (403 support_read_only).
- Hasta que el cliente acepta las condiciones que cubren la grabacion siempre (2026-10-28 o posteriores), no
  llama ni atiende: 403 terms_pending (services/legal_gate.check_client_accepted; plan, seccion 7).
"""
import asyncio
import datetime
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..conversation.models import ConversationState
from ..conversation.store import ConversationStore
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    CallMode,
    CallRing,
    CallRow,
    CallStatus,
    Client,
    Contact,
    ConversationRow,
    PhoneNumber,
    Role,
    TeamMember,
    User,
    UserPresence,
)
from . import blocked_numbers, calls, legal_gate, livekit, phones, quota
from . import limits as limits_service
from .contacts import is_opted_out
from .errors import Conflict, Forbidden, Invalid, NotFound, QuotaExceeded, Upstream
from .security import Principal

logger = logging.getLogger(__name__)

PRESENCE_TTL_SECONDS = 60
USER_PREFIX = "user-"     # identidad de un usuario del panel en la room
# Un timbre del panel suena como mucho ring_seconds (60) mas la espera a que entre el navegador: uno mas viejo
# es de un worker que se cayo sin apagarlo (no se muestra ni se atiende).
RING_MAX_SECONDS = 90
# Cuanto espera el worker a que el usuario entre antes de marcar: desde el panel ya esta entrando; por API o
# MCP tiene que abrir el join_url.
JOIN_TIMEOUT_PANEL = 30
JOIN_TIMEOUT_API = 120


def user_identity(user_id: str) -> str:
    """Identidad de un usuario del panel en la room (la que espera el worker)."""
    return f"{USER_PREFIX}{user_id}"


def join_url(conversation_id: str) -> str:
    """La pagina del panel que entra a una llamada creada por API o MCP."""
    return f"{settings.app_url.rstrip('/')}/telefono/llamada/{conversation_id}"


def _display_name(user: User) -> str:
    return user.name or user.email


def _not_support(p: Principal) -> None:
    if p.support:
        raise Forbidden("Entrando como el cliente no se puede llamar ni atender", "support_read_only")


def _panel_user(s: Session, p: Principal) -> User:
    """El usuario del panel que pide (sesion): atender, rechazar, volver a entrar y la presencia."""
    _not_support(p)
    if p.kind != "user" or p.oauth or p.client_id is None:
        raise Forbidden("Requiere la sesión de un usuario del cliente en el panel", "panel_user_required")
    user = s.get(User, p.id)
    if user is None or not user.active or user.client_id != p.client_id:
        raise Forbidden("Requiere la sesión de un usuario del cliente en el panel", "panel_user_required")
    return user


# ---------- saliente ----------

@dataclass
class DirectCallRequest:
    contact_id: str | None = None
    phone: str | None = None
    # Numero del cliente para el caller ID; sin el, el primero del cliente.
    from_number_id: str | None = None
    # El contacto (o el numero) pidio no recibir llamadas: sin esto, 409 opted_out.
    confirm_opted_out: bool = False
    # Por API key o MCP: quien llama (un usuario activo del cliente). Con sesion, el de la sesion.
    user_id: str | None = None


@dataclass
class DirectCallStarted:
    conversation_id: str
    room: str
    status: str
    livekit_url: str
    token: str | None = None
    join_url: str | None = None


def _caller(s: Session, p: Principal, user_id: str | None) -> tuple[User, bool]:
    """Quien llama y si es por API (API key o MCP: devuelve join_url en vez de token)."""
    by_api = p.kind != "user" or p.oauth
    if not by_api:
        if user_id and user_id != p.id:
            raise Invalid("Desde el panel llama el usuario de la sesión: user_id es para la API", "invalid_user")
        user_id = p.id
    elif not user_id and p.oauth:
        user_id = p.id      # el usuario que autorizo al agente, si es del cliente
    if not user_id:
        raise Invalid("Indicá user_id: el usuario del cliente que va a hablar", "user_required")
    user = s.get(User, user_id)
    if user is None or not user.active or user.role != Role.client or user.client_id != p.client_id:
        raise Invalid("user_id tiene que ser un usuario activo del cliente", "invalid_user")
    return user, by_api


def prepare_direct_call(s: Session, p: Principal, req: DirectCallRequest) -> tuple[DirectCallStarted, dict, bool]:
    """Valida (plan, contacto, bloqueados, bajas, caller ID), admite como `directa` y guarda conversacion (sin
    agente) + llamada en una transaccion. Devuelve la llamada, la metadata del worker y si es por API."""
    _not_support(p)
    if p.client_id is None:
        raise Forbidden("Las llamadas directas las hace un usuario del cliente", "client_required")
    client_id = p.client_id
    limits_service.check_direct_calls(s, client_id)
    legal_gate.check_client_accepted(s, client_id)
    user, by_api = _caller(s, p, req.user_id)
    raw = req.phone
    if req.contact_id:
        contact = s.get(Contact, req.contact_id)
        if contact is None or contact.client_id != client_id:
            raise NotFound("Contacto inexistente")
        if contact.archived_at is not None:
            raise Conflict("El contacto está archivado")
        raw = raw or contact.phone
    if not raw:
        raise Invalid("Indicá contact_id o phone", "phone_required")
    phone = calls.normalize_e164(raw)
    if blocked_numbers.is_blocked(s, client_id, phone):
        raise Forbidden("El número está bloqueado (Contactos, Bloqueados)", "blocked_number")
    opted_out = is_opted_out(s, client_id, phone, "voice")
    if opted_out and not req.confirm_opted_out:
        raise Conflict("Este contacto pidió no recibir llamadas", "opted_out")
    number = calls._caller_id(s, client_id, req.from_number_id)
    if number is None:
        raise Conflict("Hace falta un número asignado a tu cuenta para llamar", "no_phone_number")
    if number.suspended_at is not None:
        raise QuotaExceeded("El número está suspendido: tu plan no lo incluye", "number_suspended")

    state = ConversationState(conversation_id=str(uuid.uuid4()), agent_id="", client_id=client_id,
                              channel="voice", fields={})
    # Con el lock del cliente tomado no se pide otra conexion: todo va en `s` (como calls.prepare_call).
    remaining = quota.admit(s, client_id, CallMode.directa)
    if quota.busy_channels(s) >= settings.anura_channels:
        raise QuotaExceeded("Todas las líneas están ocupadas. Probá en unos minutos.", "no_channel")
    ConversationStore.add(s, state)
    s.flush()   # la conversacion antes que la llamada (foreign key)
    s.add(CallRow(conversation_id=state.conversation_id, client_id=client_id, mode=CallMode.directa, phone=phone,
                  phone_number_id=number.id, user_id=user.id, opted_out_confirmed=opted_out))
    client = s.get(Client, client_id)
    s.commit()

    room = f"call-{state.conversation_id}"
    max_duration = min(v for v in (settings.call_max_duration_seconds, remaining) if v is not None)
    metadata = {"conversation_id": state.conversation_id, "direct": True, "phone": phone, "from_number": number.e164,
                "user_identity": user_identity(user.id), "user_name": _display_name(user),
                "max_duration_seconds": max_duration,
                "join_timeout_seconds": JOIN_TIMEOUT_API if by_api else JOIN_TIMEOUT_PANEL,
                "recording_notice": bool(client.direct_recording_notice),
                # Sin voz propia del cliente: el worker usa VLLM_TTS_VOICE para el aviso.
                "voice": None}
    started = DirectCallStarted(conversation_id=state.conversation_id, room=room, status=CallStatus.pendiente,
                                livekit_url=livekit.public_url())
    if by_api:
        started.join_url = join_url(state.conversation_id)
    else:
        started.token = livekit.user_participant_token(room, user_identity(user.id), _display_name(user))
    return started, metadata, by_api


async def start_direct_call(s: Session, p: Principal, req: DirectCallRequest) -> DirectCallStarted:
    """prepare_direct_call (en un thread: I/O de base bloqueante) y despacho al worker."""
    started, metadata, _ = await asyncio.to_thread(prepare_direct_call, s, p, req)
    try:
        await livekit.dispatch_call(started.room, metadata)
    except Exception as e:
        logger.exception("despacho de la llamada directa %s", started.conversation_id)
        await asyncio.to_thread(calls._mark_failed, s, started.conversation_id, str(e), "dispatch_failed")
        raise Upstream("No se pudo iniciar la llamada") from e
    return started


@dataclass
class DirectJoin:
    livekit_url: str
    token: str


def _active_call(s: Session, p: Principal, conversation_id: str) -> CallRow:
    call = s.get(CallRow, conversation_id)
    if call is None or not p.can_access(call.client_id):
        raise NotFound("Llamada inexistente")
    if call.status not in ACTIVE_CALL_STATUSES:
        raise Conflict("La llamada no está en curso", "call_not_active")
    return call


def _lock_call(s: Session, conversation_id: str) -> CallRow | None:
    """La llamada con su fila bloqueada (SELECT ... FOR UPDATE). Atender, apagar y soltar timbres la toman antes
    de tocar call_rings: con el mismo orden en todos los caminos no hay deadlock en PostgreSQL."""
    return s.scalar(select(CallRow).where(CallRow.conversation_id == conversation_id).with_for_update()
                    .execution_options(populate_existing=True))


def _ring_since(now: datetime.datetime) -> datetime.datetime:
    return now - datetime.timedelta(seconds=RING_MAX_SECONDS)


def _token(call: CallRow, user: User) -> DirectJoin:
    room = call.room or f"call-{call.conversation_id}"
    return DirectJoin(livekit_url=livekit.public_url(),
                      token=livekit.user_participant_token(room, user_identity(user.id), _display_name(user)))


def join(s: Session, p: Principal, conversation_id: str) -> DirectJoin:
    """Token nuevo para (volver a) entrar a la llamada: solo el usuario de la llamada y mientras sigue activa
    (recargo la pagina, o la abrio por el join_url de una creada por API)."""
    user = _panel_user(s, p)
    call = s.get(CallRow, conversation_id)
    if call is None or not p.can_access(call.client_id):
        raise NotFound("Llamada inexistente")
    if call.user_id != user.id:
        raise Forbidden("La llamada es de otro usuario", "not_your_call")
    if call.status not in ACTIVE_CALL_STATUSES:
        raise Conflict("La llamada no está en curso", "call_not_active")
    return _token(call, user)


# ---------- entrante en el panel: timbre, atender y rechazar ----------

def answer(s: Session, p: Principal, conversation_id: str) -> DirectJoin:
    """Atiende una entrante que le suena en el panel. Atomico: el primero fija call_logs.user_id y su timbre
    queda answered; los demas, cancelled. Si ya la tomo otro, 409 already_answered."""
    user = _panel_user(s, p)
    call = _active_call(s, p, conversation_id)
    legal_gate.check_client_accepted(s, call.client_id)
    # Serializa con los otros que atienden y con el worker (cancel_rings, release_answer): primero la llamada.
    call = _lock_call(s, conversation_id)
    now = utcnow()
    if call is None or call.status not in ACTIVE_CALL_STATUSES or call.created_at < _stale_before(now):
        s.rollback()
        raise Conflict("La llamada no está en curso", "call_not_active")
    ring = s.scalar(select(CallRing).where(CallRing.conversation_id == conversation_id, CallRing.user_id == user.id)
                    .execution_options(populate_existing=True))
    if ring is None:
        s.rollback()
        raise NotFound("Esa llamada no te está sonando", "not_ringing")
    if call.user_id == user.id:     # ya es suya (doble click): el mismo token
        s.rollback()
        return _token(call, user)
    if call.user_id is not None:
        s.rollback()
        raise Conflict("Otra persona ya atendió la llamada", "already_answered")
    if ring.status != "ringing" or ring.created_at < _ring_since(now):
        s.rollback()
        raise Conflict("La llamada ya no te está sonando", "not_ringing")
    # El timbre, solo si sigue sonando (sin PostgreSQL no hay lock: la condicion lo cubre igual).
    still = s.execute(update(CallRing).where(CallRing.id == ring.id, CallRing.status == "ringing")
                      .values(status="answered", ended_at=now)).rowcount
    if not still:
        s.rollback()
        raise Conflict("La llamada ya no te está sonando", "not_ringing")
    # La toma: solo si nadie la tomo entre la lectura y aca (dos que atienden a la vez).
    taken = s.execute(update(CallRow).where(
        CallRow.conversation_id == conversation_id, CallRow.user_id.is_(None),
        CallRow.status.in_(ACTIVE_CALL_STATUSES)).values(user_id=user.id)).rowcount
    if not taken:
        s.rollback()
        raise Conflict("Otra persona ya atendió la llamada", "already_answered")
    s.execute(update(CallRing).where(CallRing.conversation_id == conversation_id, CallRing.id != ring.id,
                                     CallRing.status == "ringing").values(status="cancelled", ended_at=now))
    s.commit()
    s.refresh(call)
    return _token(call, user)


def decline(s: Session, p: Principal, conversation_id: str) -> None:
    """Rechaza el timbre propio (la llamada sigue sonando a los demas). Sin timbre sonando, no hace nada."""
    user = _panel_user(s, p)
    call = s.get(CallRow, conversation_id)
    if call is None or not p.can_access(call.client_id):
        raise NotFound("Llamada inexistente")
    s.execute(update(CallRing).where(CallRing.conversation_id == conversation_id, CallRing.user_id == user.id,
                                     CallRing.status == "ringing").values(status="declined", ended_at=utcnow()))
    s.commit()


@dataclass
class Ringing:
    conversation_id: str
    phone: str | None
    contact_id: str | None
    contact_name: str | None
    number_e164: str | None
    number_label: str | None
    started_at: datetime.datetime


def ringing(s: Session, p: Principal) -> list[Ringing]:
    """Las entrantes que le suenan ahora al usuario en el panel (timbres ringing de llamadas activas). Sin los
    de una llamada colgada ni los timbres vencidos (se cayo el worker sin apagarlos)."""
    user = _panel_user(s, p)
    now = utcnow()
    rows = s.execute(select(CallRing, CallRow).join(CallRow, CallRow.conversation_id == CallRing.conversation_id)
                     .where(CallRing.user_id == user.id, CallRing.status == "ringing",
                            CallRing.created_at >= _ring_since(now), CallRow.created_at >= _stale_before(now),
                            CallRow.status.in_(ACTIVE_CALL_STATUSES), CallRow.client_id == user.client_id)
                     .order_by(CallRing.created_at)).all()
    out = []
    for ring, call in rows:
        number = s.get(PhoneNumber, call.phone_number_id) if call.phone_number_id else None
        # El caller llega como lo manda Anura (sin + o sin el 9): la agenda esta en E.164 (como Reports).
        phone = _e164(call.phone)
        contact = s.scalar(select(Contact).where(Contact.client_id == call.client_id, Contact.phone == phone,
                                                 Contact.archived_at.is_(None))) if phone else None
        out.append(Ringing(conversation_id=call.conversation_id, phone=call.phone,
                           contact_id=contact.id if contact else None, contact_name=contact.name if contact else None,
                           number_e164=number.e164 if number else None, number_label=number.label if number else None,
                           started_at=call.created_at))
    return out


def _e164(raw: str | None) -> str | None:
    try:
        return phones.normalize_phone(raw or "")
    except ValueError:
        return None


# ---------- presencia ----------

def _stale_before(now: datetime.datetime) -> datetime.datetime:
    return now - datetime.timedelta(seconds=quota.STALE_MARGIN_SECONDS + settings.call_max_duration_seconds)


def busy_user_ids(s: Session, client_id: str, now: datetime.datetime | None = None) -> set[str]:
    """Usuarios del cliente con una llamada activa (saliente directa o entrante que atendieron)."""
    now = now or utcnow()
    return set(s.scalars(select(CallRow.user_id).where(
        CallRow.client_id == client_id, CallRow.user_id.is_not(None), CallRow.status.in_(ACTIVE_CALL_STATUSES),
        CallRow.created_at >= _stale_before(now))))


def available_user_ids(s: Session, client_id: str, now: datetime.datetime | None = None) -> set[str]:
    """Usuarios activos del cliente con un pulso en los ultimos PRESENCE_TTL_SECONDS (sin mirar si estan ocupados)."""
    now = now or utcnow()
    since = now - datetime.timedelta(seconds=PRESENCE_TTL_SECONDS)
    return set(s.scalars(select(UserPresence.user_id).join(User, User.id == UserPresence.user_id).where(
        UserPresence.client_id == client_id, UserPresence.last_seen >= since, User.active.is_(True),
        User.client_id == client_id)))


def available_users(s: Session, client_id: str, user_ids: list[str], now: datetime.datetime | None = None) -> list[str]:
    """De `user_ids` (en orden), los Disponibles en el panel y no ocupados: a quienes se les puede hacer sonar."""
    now = now or utcnow()
    available = available_user_ids(s, client_id, now) - busy_user_ids(s, client_id, now)
    return [u for u in dict.fromkeys(user_ids) if u in available]


@dataclass
class Presence:
    available: bool
    last_seen: datetime.datetime | None


def set_presence(s: Session, p: Principal, available: bool) -> Presence:
    """El pulso del panel (cada ~20 s mientras el usuario esta Disponible); available=false lo borra."""
    user = _panel_user(s, p)
    row = s.get(UserPresence, user.id)
    if not available:
        if row is not None:
            s.delete(row)
            s.commit()
        return Presence(False, None)
    now = utcnow()
    if row is None:
        row = UserPresence(user_id=user.id, client_id=user.client_id)
        s.add(row)
    row.client_id, row.last_seen = user.client_id, now
    s.commit()
    return Presence(True, now)


@dataclass
class TeamPresence:
    user_id: str
    team_member_id: str | None
    name: str
    available: bool
    busy: bool


def team_presence(s: Session, client_id: str) -> list[TeamPresence]:
    """Los usuarios activos del cliente: si estan Disponibles en el panel y si estan en una llamada."""
    now = utcnow()
    available, busy = available_user_ids(s, client_id, now), busy_user_ids(s, client_id, now)
    members = {m.user_id: m for m in s.scalars(select(TeamMember).where(
        TeamMember.client_id == client_id, TeamMember.user_id.is_not(None)))}
    users = s.scalars(select(User).where(User.client_id == client_id, User.active.is_(True))
                      .order_by(User.name, User.email))
    out = []
    for u in users:
        member = members.get(u.id)
        out.append(TeamPresence(user_id=u.id, team_member_id=member.id if member else None,
                                name=member.name if member else _display_name(u),
                                available=u.id in available, busy=u.id in busy))
    return out


# ---------- para el worker (entrante al equipo) ----------

def ring_panel(s: Session, conversation_id: str, user_ids: list[str]) -> list[str]:
    """Hace sonar la entrante en el panel de los usuarios de `user_ids` que esten Disponibles y no ocupados
    (crea o reabre su timbre). Devuelve a quienes les suena; vacio si no hay nadie o la llamada no existe."""
    call = _lock_call(s, conversation_id)
    if call is None or call.client_id is None:
        s.rollback()
        return []
    targets = available_users(s, call.client_id, user_ids)
    existing = {r.user_id: r for r in s.scalars(select(CallRing).where(CallRing.conversation_id == conversation_id))}
    now = utcnow()
    for user_id in targets:
        ring = existing.get(user_id)
        if ring is None:
            s.add(CallRing(conversation_id=conversation_id, user_id=user_id, created_at=now))
        elif ring.status != "answered":
            ring.status, ring.ended_at, ring.created_at = "ringing", None, now
    s.commit()
    return targets


def cancel_rings(s: Session, conversation_id: str) -> None:
    """Apaga los timbres que siguen sonando (nadie atendio, paso al celular, colgo el que llama)."""
    _lock_call(s, conversation_id)
    s.execute(update(CallRing).where(CallRing.conversation_id == conversation_id, CallRing.status == "ringing")
              .values(status="cancelled", ended_at=utcnow()))
    s.commit()


def fallback_to_agent(s: Session, engine, conversation_id: str, agent_id: str | None,
                      phone: str | None = None) -> str | None:
    """Respaldo `agent` de una entrante al equipo (nadie atendio o fuera de horario): la conversacion pasa al
    agente del numero (agente, version, campos y su apertura) y la llamada queda answered_by=agent. Devuelve la
    apertura, o None si no hay agente o esta archivado (el worker toma el mensaje)."""
    row = s.get(ConversationRow, conversation_id)
    if not agent_id or row is None:
        return None
    try:
        fresh, opening = engine.new_conversation(agent_id, client_id=row.client_id, session=s, phone=phone)
    except KeyError:
        return None
    previous = engine.store.get(conversation_id)
    fresh.conversation_id = conversation_id
    fresh.messages = [*(previous.messages if previous else []), *fresh.messages]
    row.agent_id, row.agent_version = agent_id, fresh.agent_version
    ConversationStore.add(s, fresh, engine.store.workflow(fresh, s))
    if (call := s.get(CallRow, conversation_id)) is not None:
        call.answered_by = "agent"
    s.commit()
    return opening


def release_answer(s: Session, conversation_id: str) -> None:
    """Atendio en el panel pero no entro a la room a tiempo: la llamada vuelve a quedar sin usuario (no queda a
    su nombre ni ocupado) y su timbre, apagado."""
    _lock_call(s, conversation_id)
    s.execute(update(CallRing).where(CallRing.conversation_id == conversation_id, CallRing.status == "answered")
              .values(status="cancelled", ended_at=utcnow()))
    s.execute(update(CallRow).where(CallRow.conversation_id == conversation_id).values(user_id=None))
    s.commit()


def answered_user(s: Session, conversation_id: str) -> str | None:
    """El usuario que atendio la entrante en el panel (su timbre answered), o None."""
    return s.scalar(select(CallRing.user_id).where(CallRing.conversation_id == conversation_id,
                                                   CallRing.status == "answered").limit(1))


# ---------- configuracion del cliente ----------

def get_settings(client: Client) -> dict:
    return {"recording_notice": bool(client.direct_recording_notice)}


def update_settings(s: Session, client: Client, recording_notice: bool) -> dict:
    """Aviso "Esta llamada está siendo grabada" al empezar las directas (siempre se graban)."""
    client.direct_recording_notice = bool(recording_notice)
    s.commit()
    return get_settings(client)

