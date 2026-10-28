"""Inventario de numeros: se cargan libres (los provee Anura), se asignan a un
cliente hasta el tope de su tier y el cliente elige quien atiende cada uno: un agente o
el equipo (personas en orden, donde suena primero, timbre, horario y respaldo;
docs/features/EQUIPO_TELEFONIA.md)."""
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, object_session

from ..db import utcnow
from ..models import Agent, Client, PhoneNumber, PhoneNumberMember, TeamMember, Tier
from . import legal_gate
from .calls import normalize_e164
from .errors import Conflict, Invalid, NotFound
from .handoff import validate_schedule
from .limits import check_direct_calls, effective_limits

ANSWER_MODES = ("team", "agent")
RING_FIRST = ("phone", "panel")
TEAM_FALLBACKS = ("agent", "voicemail", "hangup")
FALLBACK_MESSAGE_MAX = 500


@dataclass
class LoadResult:
    created: list[PhoneNumber]
    skipped: list[dict]     # [{"number": lo que vino, "reason": por que no se cargo}]


def load(s: Session, numbers: list[str], label: str = "", provider: str = "anura") -> LoadResult:
    """Carga numeros libres. Los repetidos o invalidos se saltean (no cortan la carga)."""
    created, skipped, seen = [], [], set()
    existing = set(s.scalars(select(PhoneNumber.e164)))
    for raw in numbers:
        raw = raw.strip()
        if not raw:
            continue
        try:
            e164 = normalize_e164(raw)
        except Invalid as e:
            skipped.append({"number": raw, "reason": e.message})
            continue
        if e164 in existing or e164 in seen:
            skipped.append({"number": raw, "reason": "Ya está cargado"})
            continue
        seen.add(e164)
        number = PhoneNumber(e164=e164, label=label, provider=provider)
        s.add(number)
        created.append(number)
    s.flush()
    return LoadResult(created, skipped)


def numbers_count(s: Session, client_id: str) -> int:
    return s.scalar(select(func.count()).select_from(PhoneNumber).where(PhoneNumber.client_id == client_id)) or 0


def assign(s: Session, number: PhoneNumber, client_id: str) -> None:
    """Asigna un numero libre a un cliente, si su tier tiene lugar."""
    # Lock del cliente (como la admision de llamadas): dos asignaciones a la vez no
    # pueden pasarse del tope. Y del numero: no puede ir a dos clientes.
    client = s.scalar(select(Client).where(Client.id == client_id).with_for_update(key_share=True, of=Client))
    if client is None:
        raise NotFound("Cliente inexistente")
    s.refresh(number, with_for_update=True)
    if number.client_id == client.id:
        return
    if number.client_id is not None:
        raise Conflict(f"El número {number.e164} ya está asignado a otro cliente: liberalo primero", "number_assigned")
    limits = effective_limits(s, client)
    limit = limits.max_phone_numbers
    if limit is not None and numbers_count(s, client.id) >= limit:
        raise Conflict(f"El plan {limits.tier_name} permite {limit} número{'s' if limit != 1 else ''} y "
                       f"{client.name} ya los tiene", "phone_numbers_limit")
    number.client_id, number.agent_id, number.assigned_at = client.id, None, utcnow()
    _reset_team(s, number)


def _reset_team(s: Session | None, number: PhoneNumber) -> None:
    """Quien atiende vuelve al default (el equipo, sin personas): las del cliente anterior no siguen."""
    if s is not None and number.id:
        s.execute(delete(PhoneNumberMember).where(PhoneNumberMember.phone_number_id == number.id))
    number.answer_mode, number.ring_first, number.ring_seconds = "team", "phone", 20
    number.schedule, number.team_fallback, number.team_fallback_message = None, "voicemail", ""


def release(number: PhoneNumber) -> None:
    """Vuelve al inventario: sin cliente ni agente (las entrantes dejan de atenderse) ni personas."""
    number.client_id, number.agent_id, number.assigned_at, number.suspended_at = None, None, None, None
    _reset_team(object_session(number), number)


def set_agent(s: Session, number: PhoneNumber, agent_id: str | None) -> None:
    if agent_id is None:
        number.agent_id = None
        return
    if number.client_id is None:
        raise Invalid("Asigná el número a un cliente antes de elegir el agente", "number_unassigned")
    agent = s.get(Agent, agent_id)
    if agent is None or agent.client_id != number.client_id:
        raise Invalid("El agente no es del cliente del número", "invalid_agent")
    if agent.archived_at is not None:
        raise Invalid("El agente está archivado", "invalid_agent")
    number.agent_id = agent.id


def member_ids(s: Session, number_id: str) -> list[str]:
    return list(s.scalars(select(PhoneNumberMember.member_id).where(PhoneNumberMember.phone_number_id == number_id)
                          .order_by(PhoneNumberMember.position)))


def members(s: Session, number_id: str) -> list[TeamMember]:
    """Las personas del numero, en orden."""
    ids = member_ids(s, number_id)
    by_id = {m.id: m for m in s.scalars(select(TeamMember).where(TeamMember.id.in_(ids)))} if ids else {}
    return [by_id[i] for i in ids if i in by_id]


def _set_members(s: Session, number: PhoneNumber, ids: list[str]) -> None:
    if len(set(ids)) != len(ids):
        raise Invalid("Una persona aparece dos veces en el número", "invalid_members")
    found = {m.id: m for m in s.scalars(select(TeamMember).where(
        TeamMember.id.in_(ids), TeamMember.client_id == number.client_id))} if ids else {}
    if any(i not in found for i in ids):
        raise Invalid("Hay personas que no son del equipo de este cliente", "invalid_members")
    without = [found[i].name for i in ids if not (found[i].phone or found[i].user_id)]
    if without:
        raise Invalid(f"Sin celular ni usuario del panel no le puede sonar: {', '.join(without)}", "invalid_members")
    s.execute(delete(PhoneNumberMember).where(PhoneNumberMember.phone_number_id == number.id))
    s.flush()
    for i, member_id in enumerate(ids):
        s.add(PhoneNumberMember(phone_number_id=number.id, member_id=member_id, position=i))
    s.flush()


def set_answering(s: Session, number: PhoneNumber, changes: dict) -> None:
    """Quien atiende las entrantes (PATCH del numero): answer_mode, member_ids (en orden), ring_first,
    ring_seconds, schedule, team_fallback y team_fallback_message. Valida el resultado entero: con team, al
    menos una persona; con respaldo agent, un agente en el numero. El agente se cambia antes (set_agent)."""
    keys = ("answer_mode", "member_ids", "ring_first", "ring_seconds", "schedule", "team_fallback",
            "team_fallback_message")
    if not any(k in changes for k in keys):
        if "agent_id" in changes:   # sacarle el agente a un numero cuyo respaldo es el agente
            _check_fallback(number)
        return
    if number.client_id is None:
        raise Invalid("Asigná el número a un cliente antes de elegir quién atiende", "number_unassigned")
    nulls = sorted(k for k in keys if k in changes and changes[k] is None and k != "schedule")
    if nulls:
        raise Invalid(f"No pueden ir vacíos: {', '.join(nulls)}")
    if "answer_mode" in changes:
        if changes["answer_mode"] not in ANSWER_MODES:
            raise Invalid("answer_mode: team o agent")
        number.answer_mode = changes["answer_mode"]
    if "ring_first" in changes:
        if changes["ring_first"] not in RING_FIRST:
            raise Invalid("ring_first: phone o panel")
        number.ring_first = changes["ring_first"]
    if "ring_seconds" in changes:
        if not 5 <= int(changes["ring_seconds"]) <= 60:
            raise Invalid("El timbre por persona va de 5 a 60 segundos")
        number.ring_seconds = int(changes["ring_seconds"])
    if "schedule" in changes:
        number.schedule = validate_schedule(changes["schedule"])
    if "team_fallback" in changes:
        if changes["team_fallback"] not in TEAM_FALLBACKS:
            raise Invalid("team_fallback: agent, voicemail o hangup")
        number.team_fallback = changes["team_fallback"]
    if "team_fallback_message" in changes:
        text = changes["team_fallback_message"].strip()
        if len(text) > FALLBACK_MESSAGE_MAX:
            raise Invalid(f"El mensaje va hasta {FALLBACK_MESSAGE_MAX} caracteres")
        number.team_fallback_message = text
    if "member_ids" in changes:
        _set_members(s, number, list(changes["member_ids"]))
    if number.answer_mode == "team":
        check_direct_calls(s, number.client_id)     # que atienda el equipo es parte de las llamadas directas
        legal_gate.check_client_accepted(s, number.client_id)    # y graba siempre: condiciones 2026-10-28+ aceptadas
    if number.answer_mode == "team" and not member_ids(s, number.id):
        raise Invalid("Para que atienda el equipo, elegí al menos una persona", "members_required")
    _check_fallback(number)


def _check_fallback(number: PhoneNumber) -> None:
    if number.answer_mode == "team" and number.team_fallback == "agent" and number.agent_id is None:
        raise Invalid("Para pasar al agente si nadie atiende, elegí el agente del número", "agent_required")


def check_tier_fits(s: Session, client: Client, tier: Tier) -> None:
    """Un cliente no puede quedar con mas numeros que los que permite su tier (con sus ajustes)."""
    count = numbers_count(s, client.id)
    limit = effective_limits(s, client, tier=tier).max_phone_numbers
    if limit is not None and count > limit:
        raise Conflict(f"{client.name} tiene {count} números y el plan {tier.name} permite "
                       f"{limit}: liberá números primero", "phone_numbers_limit")
