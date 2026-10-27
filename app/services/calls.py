"""Inicio de llamadas (salientes, de prueba, de loadtest y entrantes) con los limites del tier,
y borrado de conversaciones (admin)."""
import asyncio
import logging
import re
import shutil
import uuid
from dataclasses import dataclass, field

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..conversation.models import ConversationState
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    Agent,
    CallMode,
    CallRing,
    CallRow,
    CallStatus,
    CampaignContact,
    Client,
    Contact,
    ConversationRow,
    PhoneNumber,
    PhoneNumberMember,
    TeamMember,
    WaMessage,
    WaThread,
)
from . import (
    blocked_numbers,
    events,
    legal_gate,
    limits,
    livekit,
    quota,
    voices,
    wa_routing,
)
from .campaigns import contact_vars
from .contacts import is_opted_out
from .errors import Conflict, Forbidden, Invalid, NotFound, QuotaExceeded, Upstream
from .security import Principal

logger = logging.getLogger(__name__)

# ended_reason de una llamada cortada desde la UI o la API (hang_up).
HANGUP_REASON = "hangup_by_user"
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
    # Derivacion a personas (app/voice/handoff.py) si el agente tiene areas. La demo la apaga salvo con
    # DEMO_HANDOFF; el loadtest y las campañas no derivan nunca.
    handoff: bool = True
    # Intento de una campaña de voz (app/campaigns/dialer.py): el contacto de la campaña, con los datos
    # (`vars`) que la conversacion usa en la apertura, en los campos precargados y en el prompt
    # (app/conversation/contact.py).
    campaign_contact_id: str | None = None
    vars: dict | None = None
    # Llamada por el link publico de un agente (app/services/call_links.py): modo web, consume minutos
    # entrantes. Tope de llamadas activas del link, ademas del tier y del global (CALL_LINK_MAX_CONCURRENT).
    call_link_id: str | None = None
    link_max_concurrent: int | None = None
    # Llamada suelta desde la pantalla Llamadas: un contacto de la agenda (su telefono y sus datos, como en una
    # campaña) y el motivo en texto libre, que va al prompt (app/conversation/contact.py).
    contact_id: str | None = None
    context: str | None = None


@dataclass
class CallStarted:
    conversation_id: str
    room: str
    mode: str
    join_url: str | None = None


def _caller_id(s: Session, client_id: str, from_number_id: str | None) -> PhoneNumber | None:
    if from_number_id:
        number = s.get(PhoneNumber, from_number_id)
        if number is None or number.client_id != client_id:
            raise NotFound("Número de origen inexistente")
        return number
    return s.scalar(select(PhoneNumber).where(PhoneNumber.client_id == client_id)
                    .order_by(PhoneNumber.created_at).limit(1))


def prepare_call(s: Session, engine: ConversationEngine, principal: Principal,
                 req: CallRequest) -> tuple[CallStarted, dict]:
    """Valida, admite con los limites del tier y guarda conversacion + llamada en una
    sola transaccion. Devuelve la llamada y la metadata para el worker de voz."""
    agent = s.get(Agent, req.agent_id)
    if agent is None or not principal.can_access(agent.client_id):
        raise NotFound("Agente inexistente")
    if agent.archived_at is not None:
        raise Conflict("El agente está archivado")
    vars = req.vars
    if req.contact_id:
        contact = s.get(Contact, req.contact_id)
        if contact is None or contact.client_id != agent.client_id:
            raise NotFound("Contacto inexistente para el cliente del agente")
        if contact.archived_at is not None:
            raise Conflict("El contacto está archivado")
        if req.campaign_contact_id or req.loadtest or req.call_link_id:
            raise Invalid("contact_id es solo para llamadas sueltas")
        vars = contact_vars(contact)
        req.phone = req.phone or contact.phone
    elif req.context and vars is None:
        vars = {}   # sin contacto, la apertura igual se limpia de {{variables}}
    phone = normalize_e164(req.phone) if req.phone else None
    if phone and not req.campaign_contact_id and is_opted_out(s, agent.client_id, phone, "voice"):
        raise Conflict("El número pidió no recibir llamadas de este cliente (Contactos, Bajas)", "opted_out")
    if phone and req.loadtest:
        raise Invalid("El loadtest no marca teléfonos")
    if req.campaign_contact_id and not phone:
        raise Invalid("Un intento de campaña necesita teléfono")
    if req.loadtest and not principal.is_admin:
        # El loadtest no corta al completar el workflow: solo admins y el cliente del loadtest.
        client = s.get(Client, agent.client_id)
        if client is None or client.slug != settings.loadtest_client:
            raise Forbidden("Llamadas de loadtest solo para el cliente interno", "loadtest_forbidden")
    voice = req.voice.strip().lower() if req.voice else None
    if voice and voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}", "invalid_voice")
    if req.call_link_id and (phone or req.loadtest):
        raise Invalid("Una llamada por link no marca teléfonos ni es de loadtest")
    mode = (CallMode.saliente if phone else CallMode.loadtest if req.loadtest
            else CallMode.web if req.call_link_id else CallMode.prueba)
    caller_id = _caller_id(s, agent.client_id, req.from_number_id) if phone else None
    try:
        state, _ = engine.new_conversation(agent.id, client_id=agent.client_id, session=s, contact=vars,
                                           phone=phone, context=req.context)
    except KeyError:
        raise NotFound("Agente inexistente") from None

    # Con el lock del cliente tomado (quota.admit) no se pide otra conexion: todo va
    # en `s`. Asi, con muchas llamadas a la vez, no se agota el pool.
    remaining = quota.admit(s, agent.client_id, mode)
    if req.group_max_concurrent is not None and quota.active_calls(
            s, agent.client_id, agent_ids=req.group_agent_ids) >= req.group_max_concurrent:
        raise QuotaExceeded("Los agentes de la demo están ocupados. Probá en unos minutos.", "concurrency_limit")
    if req.call_link_id:
        if req.link_max_concurrent is not None and quota.active_link_calls(
                s, req.call_link_id) >= req.link_max_concurrent:
            raise QuotaExceeded("El link llegó a su tope de llamadas simultáneas", "link_concurrency_limit")
        if quota.active_link_calls(s) >= settings.call_link_max_concurrent:
            raise QuotaExceeded("Hay demasiadas llamadas por link en curso", "link_global_limit")
    engine.store.add(s, state)
    s.flush()   # la conversacion antes que la llamada (foreign key)
    s.add(CallRow(conversation_id=state.conversation_id, client_id=agent.client_id, mode=mode, phone=phone,
                  phone_number_id=caller_id.id if caller_id else None, campaign_contact_id=req.campaign_contact_id,
                  call_link_id=req.call_link_id))
    if req.campaign_contact_id:     # el ultimo intento del contacto, en la misma transaccion que su llamada
        s.execute(update(CampaignContact).where(CampaignContact.id == req.campaign_contact_id)
                  .values(conversation_id=state.conversation_id))
    s.commit()

    room = f"call-{state.conversation_id}"
    max_duration = min(v for v in (settings.call_max_duration_seconds, remaining, req.max_duration_seconds)
                       if v is not None)
    metadata = {"conversation_id": state.conversation_id, "phone": phone, "voice": voice, "loadtest": req.loadtest,
                "max_duration_seconds": max_duration, "from_number": caller_id.e164 if caller_id else None,
                "join_timeout_seconds": req.join_timeout_seconds, "campaign_contact_id": req.campaign_contact_id,
                "call_link_id": req.call_link_id,
                # Derivacion a personas (app/voice/handoff.py): no en el loadtest ni las campañas, y en la demo de
                # la landing solo con DEMO_HANDOFF (docs/DERIVACIONES_PLAN.md, 4.3).
                "handoff": req.handoff and not (req.loadtest or req.campaign_contact_id)}
    return CallStarted(conversation_id=state.conversation_id, room=room, mode=mode), metadata


def _mark_failed(s: Session, conversation_id: str, error: str, reason: str) -> None:
    update_call(s, conversation_id, status=CallStatus.fallida, error=error[:2000], ended_reason=reason,
                ended_at=utcnow())


async def start_call(s: Session, engine: ConversationEngine, principal: Principal, req: CallRequest) -> CallStarted:
    """prepare_call (en un thread: es I/O de base bloqueante) y despacho al worker."""
    started, metadata = await asyncio.to_thread(prepare_call, s, engine, principal, req)
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
class TeamPerson:
    """Una persona del numero: suena en su celular (`phone`) y/o en el panel (`user_id`)."""
    member_id: str
    name: str
    phone: str | None
    user_id: str | None


@dataclass
class TeamRoute:
    """Entrante al equipo (answer_mode=team, docs/LLAMADAS_DIRECTAS_PLAN.md, 5): a quien hacer sonar, en orden,
    donde primero (phone/panel), timbre, horario y que hacer si nadie atiende o esta fuera de horario
    (fallback: agent, voicemail o hangup; agent_id es el agente del numero, para el respaldo)."""
    members: list[TeamPerson]
    ring_first: str
    ring_seconds: int
    schedule: dict | None
    fallback: str
    fallback_message: str
    agent_id: str | None
    number_e164: str = ""
    number_label: str = ""


@dataclass
class InboundCall:
    conversation_id: str
    client_id: str
    opening: str
    # Con answer_mode=team: la conversacion va sin agente y el worker toma la rama directa (app/voice/direct.py).
    team: TeamRoute | None = field(default=None)


def number_people(s: Session, number_id: str, *, usable: bool = False) -> list[TeamMember]:
    """Las personas del numero, en orden. usable: solo las activas con celular o usuario del panel."""
    rows = s.scalars(select(TeamMember).join(PhoneNumberMember, PhoneNumberMember.member_id == TeamMember.id)
                     .where(PhoneNumberMember.phone_number_id == number_id)
                     .order_by(PhoneNumberMember.position)).all()
    if usable:
        rows = [m for m in rows if m.active and (m.phone or m.user_id)]
    return list(rows)


def team_route(s: Session, number: PhoneNumber) -> TeamRoute:
    return TeamRoute(
        members=[TeamPerson(member_id=m.id, name=m.name, phone=m.phone, user_id=m.user_id)
                 for m in number_people(s, number.id, usable=True)],
        ring_first=number.ring_first, ring_seconds=number.ring_seconds, schedule=number.schedule,
        fallback=number.team_fallback, fallback_message=number.team_fallback_message, agent_id=number.agent_id,
        number_e164=number.e164, number_label=number.label)


def dialed_e164(raw: str | None) -> str | None:
    """Numero marcado tal como llega de LiveKit (sip.trunkPhoneNumber) -> E.164."""
    digits = re.sub(r"\D", "", raw or "")
    return f"+{digits}" if digits else None


def start_inbound(s: Session, engine: ConversationEngine, dialed: str | None, caller: str | None,
                  wa_id: str | None = None) -> InboundCall:
    """Rutea la entrante por el numero marcado y la admite con los limites del cliente. Con
    answer_mode=team va al equipo (conversacion sin agente, `team` con el ruteo); con agent, o un numero
    del equipo sin personas, sin la funcion en el plan o con las condiciones vigentes sin aceptar, al agente
    del numero. En una llamada de WhatsApp (wa_id del llamante), manda
    la regla de ruteo por contacto de la cuenta, si hay (tambien sobre el equipo). Si el tier no la deja,
    queda registrada como rechazada y se levanta QuotaExceeded (el worker avisa y corta). Si el que
    llama esta bloqueado por el cliente, igual pero con Forbidden (el worker corta sin atender)."""
    number = s.scalar(select(PhoneNumber).where(PhoneNumber.e164 == dialed_e164(dialed)))
    if number is None or number.client_id is None:
        raise NotFound(f"El número {dialed!r} no tiene cliente o agente asignado", "number_without_agent")
    agent_id, by_rule = number.agent_id, False
    if wa_id:
        # WhatsApp: la regla por contacto de la cuenta pisa al agente por defecto del numero.
        account = wa_routing.account_for_number(s, number.e164)
        if account is not None:
            agent_id = wa_routing.resolve_agent_id(s, account, wa_id) or number.agent_id
            route = wa_routing.route_of(s, account.id, wa_id)
            by_rule = route is not None and agent_id == route.agent_id
    team = team_route(s, number) if number.answer_mode == "team" and not by_rule else None
    if team is not None and not (team.members and
                                 limits.effective_limits(s, s.get(Client, number.client_id)).direct_calls and
                                 legal_gate.client_accepted_current(s, number.client_id)):
        # Sin personas, el plan ya no tiene llamadas directas o el cliente no acepto las condiciones vigentes
        # (graban siempre): al agente del numero, si tiene, como si no tuviera la funcion.
        team = None
    if team is None and agent_id is None:
        raise NotFound(f"El número {dialed!r} no tiene cliente o agente asignado", "number_without_agent")
    if team is not None:
        state, opening = ConversationState(conversation_id=str(uuid.uuid4()), agent_id="",
                                           client_id=number.client_id, channel="voice", fields={}), ""
    else:
        try:
            state, opening = engine.new_conversation(agent_id, client_id=number.client_id, session=s, phone=caller)
        except KeyError:
            raise NotFound(f"El agente del número {dialed!r} está archivado", "number_without_agent") from None
    call = CallRow(conversation_id=state.conversation_id, client_id=number.client_id, mode=CallMode.entrante,
                   phone=caller, phone_number_id=number.id, answered_by="team" if team else "agent")
    try:
        if blocked_numbers.is_blocked(s, number.client_id, caller, wa_id):
            raise Forbidden("El número que llama está bloqueado", "blocked_number")
        if number.suspended_at is not None:
            # El plan del cliente bajo y este numero no entra (app/billing/service.py): no atiende.
            raise QuotaExceeded("El número está suspendido: el plan del cliente no lo incluye", "number_suspended")
        if wa_id:
            limits.check_whatsapp(s, number.client_id)
        quota.admit(s, number.client_id, CallMode.entrante)
    except (QuotaExceeded, Forbidden) as e:
        s.rollback()
        state.messages = []     # la apertura no llego a sonar
        call.status, call.ended_reason, call.ended_at = CallStatus.rechazada, e.code, utcnow()
        engine.store.add(s, state)
        s.flush()
        s.add(call)
        s.commit()
        raise
    engine.store.add(s, state)
    s.flush()
    s.add(call)
    s.commit()
    return InboundCall(conversation_id=state.conversation_id, client_id=number.client_id, opening=opening, team=team)


def update_call(s: Session, conversation_id: str, **values) -> None:
    row = s.get(CallRow, conversation_id)
    if row is None:
        return
    status = values.get("status")
    if status is not None and status != row.status:
        events.record_call_status(s, row, values)
    for k, v in values.items():
        setattr(row, k, v)
    s.commit()


@dataclass
class TestJoin:
    livekit_url: str
    token: str


def join_test_call(s: Session, principal: Principal, conversation_id: str) -> TestJoin:
    """Para conectarse desde el panel a una llamada de prueba en curso (la pagina /calls/<id>/hablar)."""
    call = s.get(CallRow, conversation_id)
    if call is None or not principal.can_access(call.client_id):
        raise NotFound("Llamada inexistente")
    if call.mode != CallMode.prueba:
        raise Conflict("Solo las llamadas de prueba se atienden desde el panel", "not_a_test_call")
    if call.status not in ACTIVE_CALL_STATUSES:
        raise Conflict("La llamada no está en curso", "call_not_active")
    room = call.room or f"call-{conversation_id}"
    return TestJoin(livekit_url=livekit.public_url(), token=livekit.test_participant_token(room))


async def hang_up(s: Session, principal: Principal, conversation_id: str) -> CallRow:
    """Corta una llamada en curso desde la API: cierra su room de LiveKit y el worker la cierra
    como cualquier otra, con ended_reason HANGUP_REASON. Si la room ya no existe (llamada
    colgada), la da por finalizada."""
    call = s.get(CallRow, conversation_id)
    if call is None or not principal.can_access(call.client_id):
        raise NotFound("Llamada inexistente")
    if call.status not in ACTIVE_CALL_STATUSES:
        raise Conflict("La llamada no está en curso", "call_not_active")
    # Antes de cerrar la room: el worker (finalize) respeta un ended_reason ya puesto.
    call.ended_reason = HANGUP_REASON
    s.commit()
    room = call.room or f"call-{conversation_id}"
    try:
        found = await livekit.delete_room(room)
    except Exception as e:
        logger.exception("no se pudo cortar la llamada %s (room %s)", conversation_id, room)
        call.ended_reason = ""
        s.commit()
        raise Upstream("No se pudo cortar la llamada") from e
    if not found:
        logger.warning("llamada %s: la room %s ya no existe, se da por finalizada", conversation_id, room)
        s.refresh(call)
        if call.status in ACTIVE_CALL_STATUSES:
            call.status, call.ended_at = CallStatus.finalizada, utcnow()
            s.commit()
    return call


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


# ---------- borrado (solo admin: lo exige el router) ----------

def delete_conversations(s: Session, ids: list[str]) -> int:
    """Borra conversaciones enteras: la llamada y su consumo del mes, el hilo y los
    mensajes de WhatsApp, el registro de campana y los WAV de las grabaciones.

    No borra las que tienen una llamada activa (el worker las recrearia). Devuelve
    cuantas borro; los ids que no existen se ignoran (el que borra desde la UI puede
    tener una lista vieja)."""
    ids = list(dict.fromkeys(ids))
    found = list(s.scalars(select(ConversationRow.id).where(ConversationRow.id.in_(ids)))) if ids else []
    if not found:
        return 0
    active = s.scalar(select(func.count()).select_from(CallRow).where(
        CallRow.conversation_id.in_(found), CallRow.status.in_(ACTIVE_CALL_STATUSES))) or 0
    if active:
        raise Conflict("Hay conversaciones con una llamada en curso: esperá a que terminen y volvé a intentar",
                       "call_in_progress")
    # Explicitos y en orden: en SQLite de tests las foreign keys no aplican y el
    # ondelete=CASCADE de PostgreSQL no se ve desde el ORM (no hay relationships).
    s.execute(update(CampaignContact).where(CampaignContact.conversation_id.in_(found))
              .values(conversation_id=None))
    s.execute(delete(WaMessage).where(WaMessage.conversation_id.in_(found)))
    s.execute(delete(WaThread).where(WaThread.conversation_id.in_(found)))
    s.execute(delete(CallRing).where(CallRing.conversation_id.in_(found)))
    s.execute(delete(CallRow).where(CallRow.conversation_id.in_(found)))
    s.execute(delete(ConversationRow).where(ConversationRow.id.in_(found)))
    s.commit()
    for conversation_id in found:
        shutil.rmtree(settings.call_recordings_dir / conversation_id, ignore_errors=True)
    return len(found)


def delete_conversation(s: Session, conversation_id: str) -> None:
    if not delete_conversations(s, [conversation_id]):
        raise NotFound("Conversación inexistente")
