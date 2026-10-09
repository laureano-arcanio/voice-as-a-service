"""Inicio de llamadas (salientes, de prueba, de loadtest y entrantes) con los limites del tier."""
import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..db import utcnow
from ..models import (
    Agent,
    CallMode,
    CallRow,
    CallStatus,
    Client,
    ConversationRow,
    PhoneNumber,
    effective_max_call_seconds,
)
from . import livekit, quota, voices
from .errors import Conflict, Forbidden, Invalid, NotFound, QuotaExceeded, Upstream
from .security import Principal

logger = logging.getLogger(__name__)
E164_RE = re.compile(r"\+\d{8,15}")


def normalize_e164(raw: str) -> str:
    phone = re.sub(r"[\s()\-.]", "", raw)
    if not E164_RE.fullmatch(phone):
        raise Invalid("Número inválido: usar formato internacional, ej. +5491155551234", "invalid_phone")
    return phone


@dataclass
class CallRequest:
    agent_id: str
    phone: str | None = None
    # Numero del cliente para el caller ID; sin el, el primero del cliente.
    from_number_id: str | None = None
    # Voz del TTS para esta llamada; sin voz, la del agente (agent.voice).
    voice: str | None = None
    # Llamada del loadtest (scripts/loadtest, scripts/capacity): como la de prueba, pero
    # el agente no corta al completar el workflow, asi dura los turnos que pide el caller.
    loadtest: bool = False
    max_duration_seconds: int | None = None
    join_timeout_seconds: int | None = None
    # Tope de llamadas activas entre estos agentes, ademas del tier (la demo de la landing:
    # sus agentes comparten cliente con el resto de Atentina, que no tiene limites).
    group_agent_ids: tuple[str, ...] = ()
    group_max_concurrent: int | None = None
    # Header Idempotency-Key de POST /calls: un reintento con la misma clave devuelve la
    # llamada ya creada en vez de marcar dos veces (unica por cliente, call_logs).
    idempotency_key: str | None = None


@dataclass
class CallStarted:
    conversation_id: str
    room: str
    mode: str
    join_url: str | None = None
    # Ya existia con esa Idempotency-Key: no se despacha de nuevo (la API responde 200).
    replayed: bool = False


def _caller_id(s: Session, client_id: str, from_number_id: str | None) -> PhoneNumber | None:
    if from_number_id:
        number = s.get(PhoneNumber, from_number_id)
        if number is None or number.client_id != client_id:
            raise NotFound("Número de origen inexistente")
        return number
    return s.scalar(select(PhoneNumber).where(PhoneNumber.client_id == client_id)
                    .order_by(PhoneNumber.created_at).limit(1))


def _fingerprint(agent_id: str, phone: str | None, req: CallRequest) -> str:
    """Huella del pedido completo (lo que cambia la llamada): un reintento con la misma
    Idempotency-Key tiene que ser el mismo pedido."""
    voice = req.voice.strip().lower() if req.voice else None
    body = {"agent_id": agent_id, "phone": phone, "from_number_id": req.from_number_id or None,
            "voice": voice or None, "loadtest": bool(req.loadtest)}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _replay(s: Session, client_id: str, req: CallRequest, agent: Agent, phone: str | None) -> CallStarted | None:
    """La llamada del cliente con esa Idempotency-Key, si ya existe. Con otro pedido (otro
    agente, telefono, numero de origen, voz o loadtest) la clave esta mal reusada: Conflict.
    Una llamada que no se pudo despachar suelta su clave (_mark_failed): el reintento marca."""
    if not req.idempotency_key:
        return None
    call = s.scalar(select(CallRow).where(CallRow.client_id == client_id,
                                          CallRow.idempotency_key == req.idempotency_key))
    if call is None:
        return None
    if call.idempotency_fingerprint is not None:
        same = call.idempotency_fingerprint == _fingerprint(agent.id, phone, req)
    else:
        conv_agent = s.scalar(select(ConversationRow.agent_id).where(ConversationRow.id == call.conversation_id))
        same = conv_agent == agent.id and call.phone == phone
    if not same:
        raise Conflict("La Idempotency-Key ya se usó para otra llamada", "idempotency_key_reused")
    return CallStarted(conversation_id=call.conversation_id, room=f"call-{call.conversation_id}",
                       mode=call.mode, replayed=True)


def prepare_call(s: Session, engine: ConversationEngine, principal: Principal,
                 req: CallRequest) -> tuple[CallStarted, dict | None]:
    """Valida, admite con los limites del tier y guarda conversacion + llamada en una
    sola transaccion. Devuelve la llamada y la metadata para el worker de voz (None si
    es un reintento con la misma Idempotency-Key: ya se despacho)."""
    agent = s.get(Agent, req.agent_id)
    if agent is None or not principal.can_access(agent.client_id):
        raise NotFound("Agente inexistente")
    phone = normalize_e164(req.phone) if req.phone else None
    if replayed := _replay(s, agent.client_id, req, agent, phone):
        return replayed, None
    if agent.archived_at is not None:
        raise Conflict("El agente está archivado")
    if phone and req.loadtest:
        raise Invalid("El loadtest no marca teléfonos")
    if req.loadtest and not principal.is_admin:
        # El loadtest no corta al completar el workflow: solo admins y el cliente del loadtest.
        client = s.get(Client, agent.client_id)
        if client is None or client.slug != settings.loadtest_client:
            raise Forbidden("Llamadas de loadtest solo para el cliente interno", "loadtest_forbidden")
    voice = req.voice.strip().lower() if req.voice else None
    if voice and voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}", "invalid_voice")
    mode = CallMode.saliente if phone else CallMode.loadtest if req.loadtest else CallMode.prueba
    caller_id = _caller_id(s, agent.client_id, req.from_number_id) if phone else None
    if phone and caller_id is None and not principal.is_admin:
        # Sin numero propio la llamada saldria con el DID de Atentina (ANURA_DID, que pone
        # Asterisk): el contacto veria otro numero y devolveria la llamada a nuestro agente (H05).
        raise Conflict("El cliente no tiene un número propio para identificar la llamada: pedí uno para "
                       "hacer salientes", "no_caller_id")
    try:
        state, _ = engine.new_conversation(agent.id, client_id=agent.client_id, session=s)
    except KeyError:
        raise NotFound("Agente inexistente") from None

    # Con el lock del cliente tomado (quota.admit) no se pide otra conexion: todo va
    # en `s`. Asi, con muchas llamadas a la vez, no se agota el pool.
    remaining = quota.admit(s, agent.client_id, mode)
    if req.group_max_concurrent is not None and quota.active_calls(
            s, agent.client_id, agent_ids=req.group_agent_ids) >= req.group_max_concurrent:
        raise QuotaExceeded("Los agentes de la demo están ocupados. Probá en unos minutos.", "concurrency_limit")
    client = s.get(Client, agent.client_id)
    engine.store.add(s, state)
    s.flush()   # la conversacion antes que la llamada (foreign key)
    s.add(CallRow(conversation_id=state.conversation_id, client_id=agent.client_id, mode=mode, phone=phone,
                  phone_number_id=caller_id.id if caller_id else None, idempotency_key=req.idempotency_key,
                  idempotency_fingerprint=_fingerprint(agent.id, phone, req) if req.idempotency_key else None))
    try:
        s.commit()
    except IntegrityError:
        # Dos pedidos con la misma Idempotency-Key a la vez: gano el otro (UNIQUE por cliente).
        s.rollback()
        if replayed := _replay(s, agent.client_id, req, agent, phone):
            return replayed, None
        raise

    room = f"call-{state.conversation_id}"
    # Tope duro: el del tier del cliente (H02), los minutos que le quedan y el del pedido.
    max_duration = min(v for v in (effective_max_call_seconds(client), remaining, req.max_duration_seconds)
                       if v is not None)
    metadata = {"conversation_id": state.conversation_id, "phone": phone, "voice": voice, "loadtest": req.loadtest,
                "max_duration_seconds": max_duration, "from_number": caller_id.e164 if caller_id else None,
                "join_timeout_seconds": req.join_timeout_seconds}
    return CallStarted(conversation_id=state.conversation_id, room=room, mode=mode), metadata


def _mark_failed(s: Session, conversation_id: str, error: str, reason: str) -> None:
    # Sin despacho la llamada no salio: suelta la Idempotency-Key para que el reintento del
    # integrador (lo normal ante un 502) marque, en vez de recibir 200 con esta fallida.
    update_call(s, conversation_id, status=CallStatus.fallida, error=error[:2000], ended_reason=reason,
                ended_at=utcnow(), idempotency_key=None, idempotency_fingerprint=None)


def _prepare_or_rollback(s: Session, engine: ConversationEngine, principal: Principal,
                         req: CallRequest) -> tuple[CallStarted, dict | None]:
    """prepare_call, y si falla, rollback: suelta el lock del cliente (quota.admit) ya,
    no cuando se cierra la sesion del pedido."""
    try:
        return prepare_call(s, engine, principal, req)
    except Exception:
        s.rollback()
        raise


async def start_call(s: Session, engine: ConversationEngine, principal: Principal, req: CallRequest) -> CallStarted:
    """prepare_call (en un thread: es I/O de base bloqueante) y despacho al worker."""
    started, metadata = await asyncio.to_thread(_prepare_or_rollback, s, engine, principal, req)
    if metadata is None:
        # Reintento con la misma Idempotency-Key: la llamada ya se despacho.
        if started.mode != CallMode.saliente:
            started.join_url = livekit.build_test_join_url(started.room)
        return started
    try:
        await livekit.dispatch_call(started.room, metadata)
    except Exception as e:
        logger.exception("despacho de la llamada %s", started.conversation_id)
        await asyncio.to_thread(_mark_failed, s, started.conversation_id, str(e), "dispatch_failed")
        raise Upstream("No se pudo iniciar la llamada") from e
    if started.mode != CallMode.saliente:
        started.join_url = livekit.build_test_join_url(started.room)
    return started


# ---------- entrantes (worker de voz) ----------

@dataclass
class InboundCall:
    conversation_id: str
    client_id: str
    opening: str
    # Tope duro de esta entrante: el del tier (H02) o los minutos que le quedan, el menor.
    max_duration_seconds: int | None = None


def dialed_e164(raw: str | None) -> str | None:
    """Numero marcado tal como llega de LiveKit (sip.trunkPhoneNumber) -> E.164."""
    digits = re.sub(r"\D", "", raw or "")
    return f"+{digits}" if digits else None


def start_inbound(s: Session, engine: ConversationEngine, dialed: str | None, caller: str | None) -> InboundCall:
    """Rutea la entrante por el numero marcado al agente de ese numero y la admite
    con los limites del cliente. Si el tier no la deja, queda registrada como
    rechazada y se levanta QuotaExceeded (el worker avisa y corta)."""
    number = s.scalar(select(PhoneNumber).where(PhoneNumber.e164 == dialed_e164(dialed)))
    if number is None or number.client_id is None or number.agent_id is None:
        raise NotFound(f"El número {dialed!r} no tiene cliente o agente asignado", "number_without_agent")
    agent = s.get(Agent, number.agent_id)
    if agent is None or agent.client_id != number.client_id:
        # No deberia pasar (lock al rutear y FK compuesta en PostgreSQL, H01); si pasa, no se
        # atiende con el agente de otro cliente: se corta y queda en el log como error.
        logger.error("entrante a %s: el agente %s no es del cliente %s del numero", number.e164,
                     number.agent_id, number.client_id)
        raise NotFound(f"El agente del número {dialed!r} es de otro cliente", "number_agent_mismatch")
    try:
        state, opening = engine.new_conversation(number.agent_id, client_id=number.client_id, session=s)
    except KeyError:
        raise NotFound(f"El agente del número {dialed!r} está archivado", "number_without_agent") from None
    call = CallRow(conversation_id=state.conversation_id, client_id=number.client_id, mode=CallMode.entrante,
                   phone=caller, phone_number_id=number.id)
    try:
        remaining = quota.admit(s, number.client_id, CallMode.entrante)
    except QuotaExceeded as e:
        s.rollback()
        state.messages = []     # la apertura no llego a sonar
        call.status, call.ended_reason, call.ended_at = CallStatus.rechazada, e.code, utcnow()
        engine.store.add(s, state)
        s.flush()
        s.add(call)
        s.commit()
        raise
    max_duration = min(v for v in (effective_max_call_seconds(s.get(Client, number.client_id)), remaining)
                       if v is not None)
    engine.store.add(s, state)
    s.flush()
    s.add(call)
    s.commit()
    return InboundCall(conversation_id=state.conversation_id, client_id=number.client_id, opening=opening,
                       max_duration_seconds=max_duration)


def update_call(s: Session, conversation_id: str, **values) -> None:
    row = s.get(CallRow, conversation_id)
    if row is None:
        return
    for k, v in values.items():
        setattr(row, k, v)
    s.commit()


def call_remaining_seconds(s: Session, conversation_id: str) -> int | None:
    """Segundos que le quedan al cliente de la llamada en su modalidad (None: sin tope).
    0 si el cliente se desactivo durante la llamada."""
    call = s.get(CallRow, conversation_id)
    client = s.get(Client, call.client_id) if call and call.client_id else None
    if client is None:
        return None
    if not client.active:
        return 0
    return quota.remaining_seconds(s, client, call.mode)
