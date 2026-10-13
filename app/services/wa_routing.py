"""Ruteo por contacto de los numeros de WhatsApp (wa_routes): que agente atiende a cada
contacto, en los mensajes y en las llamadas de WhatsApp. La cuenta mantiene su agente por
defecto (wa_accounts.agent_id), que atiende a los contactos sin regla.

Los contactos se guardan como los manda Meta (549351...); para comparar se canonizan:
solo digitos y, en Argentina, sin el 9 internacional del celular (Meta manda 54911...,
Anura entrega 5411... para el mismo numero).
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Agent, WaAccount, WaRoute
from .errors import Conflict, Invalid

CONTACT_RE = re.compile(r"\d{8,15}")


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def canonical_wa_id(value: str | None) -> str:
    """Forma canonica de un wa_id/telefono para comparar."""
    number = digits(value)
    if len(number) == 13 and number.startswith("549"):
        return "54" + number[3:]
    return number


def same_number(a: str | None, b: str | None) -> bool:
    """True si los dos son el mismo numero (ignora formato, +, y el 9 argentino)."""
    return bool(a and b) and canonical_wa_id(a) == canonical_wa_id(b)


def normalize_contact(raw: str) -> str:
    """Contacto cargado a mano: solo digitos (acepta +, espacios y guiones). 422 si no
    tiene pinta de telefono internacional."""
    number = digits(raw)
    if not CONTACT_RE.fullmatch(number):
        raise Invalid(
            f"Contacto inválido: {raw.strip()!r} (usar el WhatsApp con código de país, ej. 5491155551234)",
            "invalid_contact")
    return number


def account_for_number(s: Session, e164: str) -> WaAccount | None:
    """La cuenta activa cuyo numero visible es este (el DID de una llamada de WhatsApp)."""
    for account in s.scalars(select(WaAccount).where(WaAccount.active.is_(True)).order_by(WaAccount.created_at)):
        if same_number(account.display_phone_number, e164):
            return account
    return None


def routes_for(s: Session, account_id: str) -> list[WaRoute]:
    return list(s.scalars(select(WaRoute).where(WaRoute.account_id == account_id)
                          .order_by(WaRoute.created_at)))


def _usable(s: Session, agent_id: str) -> bool:
    """El agente existe y no esta archivado (al que se le puede abrir una conversacion)."""
    agent = s.get(Agent, agent_id)
    return agent is not None and agent.archived_at is None


def resolve_agent_id(s: Session, account: WaAccount, wa_id: str) -> str | None:
    """El agente que atiende este contacto: el de su regla, o el de la cuenta. None si
    ninguno existe o esta archivado (el que llama decide el fallback)."""
    contact = canonical_wa_id(wa_id)
    if contact:
        for route in routes_for(s, account.id):
            if any(canonical_wa_id(c) == contact for c in route.contacts or []):
                if _usable(s, route.agent_id):
                    return route.agent_id
                # Regla con el agente archivado: se ignora y sigue el de la cuenta.
    return account.agent_id if _usable(s, account.agent_id) else None


def route_of(s: Session, account_id: str, wa_id: str) -> WaRoute | None:
    """La regla del contacto en esa cuenta, si hay (aunque su agente no sirva)."""
    contact = canonical_wa_id(wa_id)
    if not contact:
        return None
    for route in routes_for(s, account_id):
        if any(canonical_wa_id(c) == contact for c in route.contacts or []):
            return route
    return None


def set_routes(s: Session, account: WaAccount, routes: list[tuple[str, list[str]]]) -> list[WaRoute]:
    """Reemplaza las reglas de la cuenta. routes: [(agent_id, [contactos])]. Un contacto
    esta en una sola regla de la cuenta (409 si se repite); agente ajeno o archivado, 422;
    una regla sin contactos, 422."""
    prepared: list[tuple[str, list[str]]] = []
    agents: set[str] = set()
    seen: dict[str, str] = {}
    for agent_id, raw_contacts in routes:
        if agent_id in agents:
            raise Conflict("El agente ya tiene una regla en este número: unificá los contactos",
                           "route_agent_duplicated")
        agents.add(agent_id)
        agent = s.get(Agent, agent_id)
        if agent is None or agent.client_id != account.client_id:
            raise Invalid("El agente no es del cliente de la cuenta", "invalid_agent")
        if agent.archived_at is not None:
            raise Invalid("El agente está archivado", "invalid_agent")
        contacts: list[str] = []
        here: set[str] = set()
        for raw in raw_contacts:
            number = normalize_contact(raw)
            key = canonical_wa_id(number)
            if key in here:
                continue            # repetido en la misma lista: se unifica
            if key in seen:
                raise Conflict(f"El contacto {number} ya está en la regla de otro agente",
                               "wa_contact_duplicated")
            here.add(key)
            seen[key] = number
            contacts.append(number)
        if not contacts:
            raise Invalid(f"La regla de {agent.name} no tiene contactos", "route_without_contacts")
        prepared.append((agent_id, contacts))
    for route in routes_for(s, account.id):
        s.delete(route)
    s.flush()
    created = [WaRoute(account_id=account.id, agent_id=agent_id, contacts=contacts)
               for agent_id, contacts in prepared]
    s.add_all(created)
    s.flush()
    return created
