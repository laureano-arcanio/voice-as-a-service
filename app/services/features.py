"""Que funciones incluye el plan de un cliente, con el motivo de las que no (docs/FUNCIONES_POR_PLAN_PLAN.md).

La UI bloquea con esto cada pantalla (`GET /plan/features`); el corte de verdad lo hace cada servicio con
los mismos campos del tier (quota, limits.check_*). Sale de los limites efectivos (tier + ajustes), nunca
del nombre del plan: un plan pago sin numeros tampoco hace salientes.
"""
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Client, PhoneNumber, Tier
from . import limits as limits_service


@dataclass
class Feature:
    enabled: bool
    reason: str | None = None   # lo que hace falta, en lenguaje del cliente


@dataclass
class PlanFeatures:
    client_id: str
    tier_name: str
    free: bool
    features: dict[str, Feature]


# Que tier incluye cada funcion: los mismos campos que lee plan_features(), sin los ajustes de un cliente.
TIER_HAS: dict[str, Callable[[Tier], bool]] = {
    "outbound_calls": lambda t: t.outbound_minutes != 0 and t.max_phone_numbers != 0,
    "campaigns_voice": lambda t: "voice" in (t.campaign_channels or ()),
    "campaigns_whatsapp": lambda t: "whatsapp" in (t.campaign_channels or ()),
    "whatsapp": lambda t: bool(t.whatsapp),
    "contacts": lambda t: t.max_contacts != 0,
    "team": lambda t: t.max_team_members != 0,
    "call_links": lambda t: t.max_call_links != 0,
    "external_agent": lambda t: bool(t.external_agent),
}


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


def _where(tiers: list[Tier], key: str) -> str:
    """En que planes esta: "Disponible en los planes Mostrador, Sucursal y Central"."""
    names = [t.name for t in tiers if TIER_HAS[key](t)]
    if not names:
        return "Escribinos y la sumamos a tu plan"
    return f"Disponible en el plan {names[0]}" if len(names) == 1 else f"Disponible en los planes {_names(names)}"


def _upgrade_tiers(s: Session, client: Client) -> list[Tier]:
    """Los planes a los que puede pasar: todos menos el suyo, los gratis y el interno; los que se venden
    por el dashboard primero, por su orden."""
    from ..cli import INTERNAL_TIER     # cli importa servicios: aca, para no hacer un ciclo
    tiers = s.scalars(select(Tier).where(Tier.id != client.tier_id, Tier.name != INTERNAL_TIER)).all()
    tiers = [t for t in tiers if t.price_ars != 0]
    return sorted(tiers, key=lambda t: (t.price_ars is None, t.sort, t.price_ars or 0, t.name))


def plan_features(s: Session, client: Client) -> PlanFeatures:
    lim = limits_service.effective_limits(s, client)
    numbers = s.scalar(select(func.count()).select_from(PhoneNumber).where(PhoneNumber.client_id == client.id)) or 0
    enabled = {
        "outbound_calls": lim.outbound_minutes != 0 and numbers > 0,
        "campaigns_voice": "voice" in lim.campaign_channels,
        "campaigns_whatsapp": "whatsapp" in lim.campaign_channels,
        "whatsapp": lim.whatsapp,
        "contacts": lim.max_contacts != 0,
        "team": lim.max_team_members != 0,
        "call_links": lim.max_call_links != 0,
        "external_agent": lim.external_agent,
    }
    tiers = _upgrade_tiers(s, client) if not all(enabled.values()) else []
    features = {}
    for key, on in enabled.items():
        if on:
            features[key] = Feature(True)
        elif key == "outbound_calls" and lim.outbound_minutes != 0:
            features[key] = Feature(False, "Hace falta un número asignado a tu cuenta.")
        elif key == "outbound_calls":
            features[key] = Feature(False, f"{_where(tiers, key)}, con números asignados.")
        else:
            features[key] = Feature(False, f"{_where(tiers, key)}.")
    return PlanFeatures(client_id=client.id, tier_name=lim.tier_name, free=client.tier.price_ars == 0,
                        features=features)
