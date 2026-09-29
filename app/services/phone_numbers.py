"""Inventario de numeros: se cargan libres (los provee Anura), se asignan a un
cliente hasta el tope de su tier y el cliente los rutea a sus agentes."""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Agent, Client, PhoneNumber, Tier
from .calls import normalize_e164
from .errors import Conflict, Invalid, NotFound


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
    limit = client.tier.max_phone_numbers
    if limit is not None and numbers_count(s, client.id) >= limit:
        raise Conflict(f"El plan {client.tier.name} permite {limit} número{'s' if limit != 1 else ''} y "
                       f"{client.name} ya los tiene", "phone_numbers_limit")
    number.client_id, number.agent_id, number.assigned_at = client.id, None, utcnow()


def release(number: PhoneNumber) -> None:
    """Vuelve al inventario: sin cliente ni agente (las entrantes dejan de atenderse)."""
    number.client_id, number.agent_id, number.assigned_at = None, None, None


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


def check_tier_fits(s: Session, client: Client, tier: Tier) -> None:
    """Un cliente no puede quedar con mas numeros que los que permite su tier."""
    count = numbers_count(s, client.id)
    if tier.max_phone_numbers is not None and count > tier.max_phone_numbers:
        raise Conflict(f"{client.name} tiene {count} números y el plan {tier.name} permite "
                       f"{tier.max_phone_numbers}: liberá números primero", "phone_numbers_limit")
