"""Limites efectivos de un cliente: los de su tier mas los ajustes vigentes.

El tier es el plan que comparten muchos clientes. Para darle algo distinto a uno solo (una linea
mas, 10 minutos mas este mes, un tope propio) se carga un ajuste (`ClientLimitAdjustment`) en vez de
tocar el tier o clonarlo. Todo lo que aplica limites (services/quota.py, api_usage.py, numeros,
rate limit de la API de inferencia) lee `effective_limits()`, no `client.tier`.

Reglas, por campo:
- `set` reemplaza el valor del tier (value NULL = ilimitado). Si hay varios vigentes, gana el
  ultimo cargado.
- `add` suma al resultado. Se acumulan. Sobre un valor ilimitado (NULL) no tiene efecto.
- Un ajuste vale desde `starts_on` hasta `ends_on`, ambos inclusive, en settings.billing_timezone;
  sin fechas es permanente. Al vencer solo, el cliente vuelve al valor del tier.
"""
import datetime
from collections.abc import Iterable
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import (
    Campaign,
    CampaignContact,
    Client,
    ClientLimitAdjustment,
    Contact,
    Tier,
)
from .errors import QuotaExceeded

# Los limites de Tier que se pueden ajustar (todos los numericos).
LIMIT_FIELDS = (
    "max_concurrent_calls",
    "max_calls_per_hour",
    "max_calls_per_day",
    "max_calls_per_month",
    "inbound_minutes",
    "outbound_minutes",
    "max_phone_numbers",
    "api_llm_input_tokens",
    "api_llm_output_tokens",
    "api_tts_minutes",
    "api_stt_minutes",
    "api_rate_limit",
    "max_campaigns_per_month",
    "max_campaign_contacts",
    "max_campaign_concurrency",
    "max_contacts",
    "max_call_links",
    "max_team_members",
    "max_tools",
)
MODES = ("add", "set")


@dataclass(frozen=True)
class Limits:
    """Lo mismo que lee el codigo de un Tier (mismos nombres), ya con los ajustes aplicados.
    None = ilimitado; en los api_*, 0 = no incluido."""
    max_concurrent_calls: int | None = None
    max_calls_per_hour: int | None = None
    max_calls_per_day: int | None = None
    max_calls_per_month: int | None = None
    inbound_minutes: int | None = None
    outbound_minutes: int | None = None
    max_phone_numbers: int | None = None
    api_llm_input_tokens: int | None = None
    api_llm_output_tokens: int | None = None
    api_tts_minutes: int | None = None
    api_stt_minutes: int | None = None
    api_rate_limit: int | None = None
    # Campañas y agenda (plan de llamadas salientes, 3.5). None = ilimitado, 0 = no incluido.
    max_campaigns_per_month: int | None = None
    max_campaign_contacts: int | None = None
    max_campaign_concurrency: int | None = None
    max_contacts: int | None = None
    # Links publicos para llamar a un agente (docs/LINK_LLAMADA_PLAN.md). None = ilimitado, 0 = no incluido.
    max_call_links: int | None = None
    # Personas del equipo para derivar (docs/DERIVACIONES_PLAN.md). None = ilimitado, 0 = no incluido.
    max_team_members: int | None = None
    # Herramientas del cliente (docs/TOOLS_PLAN.md). None = ilimitado, 0 = no incluido.
    max_tools: int | None = None
    # No son numericos, asi que no se ajustan por cliente: salen del tier.
    campaign_channels: tuple[str, ...] = ()
    campaign_followup: bool = False
    whatsapp: bool = True
    external_agent: bool = False
    code_tools: bool = False
    white_label: bool = False
    tier_name: str = ""
    # Campos cuyo valor difiere del tier por un ajuste vigente.
    adjusted: frozenset[str] = field(default_factory=frozenset)


def today(now: datetime.datetime | None = None) -> datetime.date:
    """El dia en curso en billing_timezone. `now` en UTC naive."""
    aware = (now or utcnow()).replace(tzinfo=datetime.UTC)
    return aware.astimezone(ZoneInfo(settings.billing_timezone)).date()


def is_active(adj: ClientLimitAdjustment, day: datetime.date) -> bool:
    return (adj.starts_on is None or adj.starts_on <= day) and (adj.ends_on is None or day <= adj.ends_on)


def status(adj: ClientLimitAdjustment, day: datetime.date) -> str:
    """active, scheduled (todavia no empezo) o expired."""
    if adj.starts_on is not None and adj.starts_on > day:
        return "scheduled"
    if adj.ends_on is not None and day > adj.ends_on:
        return "expired"
    return "active"


def _active_where(day: datetime.date):
    """El filtro SQL de is_active()."""
    return (or_(ClientLimitAdjustment.starts_on.is_(None), ClientLimitAdjustment.starts_on <= day),
            or_(ClientLimitAdjustment.ends_on.is_(None), ClientLimitAdjustment.ends_on >= day))


def apply(tier: Tier, adjustments: Iterable[ClientLimitAdjustment], day: datetime.date) -> Limits:
    """El tier con los ajustes vigentes en `day` aplicados."""
    values = {f: getattr(tier, f) for f in LIMIT_FIELDS}
    active = sorted((a for a in adjustments if is_active(a, day)),
                    key=lambda a: (a.created_at.isoformat() if a.created_at else "", a.id or ""))
    for a in active:
        if a.mode == "set":
            values[a.field] = a.value
    for a in active:
        if a.mode == "add" and values[a.field] is not None:
            values[a.field] += a.value
    adjusted = frozenset(f for f, v in values.items() if v != getattr(tier, f))
    return Limits(**values, campaign_channels=tuple(tier.campaign_channels or ()),
                  campaign_followup=bool(tier.campaign_followup), whatsapp=bool(tier.whatsapp),
                  external_agent=bool(tier.external_agent), code_tools=bool(tier.code_tools),
                  white_label=bool(tier.white_label),
                  tier_name=tier.name, adjusted=adjusted)


def effective_limits(s: Session, client: Client, now: datetime.datetime | None = None,
                     tier: Tier | None = None) -> Limits:
    """Limites del cliente hoy. `tier`: calcularlos como si tuviera ese tier (para validar un
    cambio de tier antes de aplicarlo)."""
    day = today(now)
    rows = s.scalars(select(ClientLimitAdjustment).where(
        ClientLimitAdjustment.client_id == client.id, *_active_where(day))).all()
    return apply(tier or client.tier, rows, day)


def active_count(s: Session, client_id: str, now: datetime.datetime | None = None) -> int:
    """Cuantos ajustes vigentes hoy tiene el cliente."""
    return s.scalar(select(func.count()).select_from(ClientLimitAdjustment).where(
        ClientLimitAdjustment.client_id == client_id, *_active_where(today(now)))) or 0


def adjustments(s: Session, client_id: str) -> list[ClientLimitAdjustment]:
    """Todos los ajustes del cliente (vigentes, futuros y vencidos), los mas nuevos primero."""
    return list(s.scalars(select(ClientLimitAdjustment).where(ClientLimitAdjustment.client_id == client_id)
                          .order_by(ClientLimitAdjustment.created_at.desc(), ClientLimitAdjustment.id)))


def check_whatsapp(s: Session, client_id: str) -> None:
    """WhatsApp (cuentas, mensajes y llamadas) solo si el plan del cliente lo incluye."""
    client = s.get(Client, client_id)
    if client is not None and not effective_limits(s, client).whatsapp:
        raise QuotaExceeded("Tu plan no incluye WhatsApp.", "whatsapp_not_in_plan")


def check_external_agent(s: Session, client_id: str) -> None:
    """Motor external (el agente del cliente en su endpoint) solo si el plan lo incluye."""
    client = s.get(Client, client_id)
    if client is not None and not effective_limits(s, client).external_agent:
        raise QuotaExceeded("Tu plan no incluye usar tu propio agente.", "external_agent_not_in_plan")


# ---------- campañas y agenda (docs/LLAMADAS_SALIENTES_PLAN.md, 3.5) ----------
#
# Las valida quien crea, completa o inicia una campaña y quien carga contactos. None = sin tope,
# 0 = no incluido. Las llamadas de una campaña de voz cuentan ademas en los limites de siempre
# (services/quota.py).

CHANNEL_NAMES = {"whatsapp": "WhatsApp", "voice": "llamadas"}


def check_campaign_channel(limits: Limits, channel: str) -> None:
    if channel not in limits.campaign_channels:
        raise QuotaExceeded(f"Tu plan no incluye campañas por {CHANNEL_NAMES.get(channel, channel)}.",
                            "campaign_channel_not_in_plan")


def campaigns_started(s: Session, client_id: str, now: datetime.datetime | None = None) -> int:
    """Campañas que el cliente inicio en el mes calendario (billing_timezone): started_at se
    fija al pasar de borrador a programada o en curso. Cancelar no devuelve el cupo."""
    from .quota import month_bounds
    start, end = month_bounds(now.replace(tzinfo=datetime.UTC) if now else None)    # now: UTC naive
    return s.scalar(select(func.count()).select_from(Campaign).where(
        Campaign.client_id == client_id, Campaign.started_at >= start, Campaign.started_at < end)) or 0


def check_campaign_month(s: Session, client_id: str, limits: Limits, now: datetime.datetime | None = None) -> None:
    """Para iniciar una campaña nueva (la que ya empezo y se retoma no gasta cupo)."""
    cap = limits.max_campaigns_per_month
    if cap is not None and campaigns_started(s, client_id, now) >= cap:
        raise QuotaExceeded(("Tu plan no incluye campañas." if cap == 0 else
                             f"Tu plan permite {cap} campañas por mes y ya iniciaste {cap}."),
                            "campaigns_per_month")


def check_campaign_contacts(limits: Limits, total: int) -> None:
    cap = limits.max_campaign_contacts
    if cap is not None and total > cap:
        raise QuotaExceeded(f"Tu plan permite {cap} contactos por campaña.", "campaign_contacts")


def campaign_contacts_room(limits: Limits, total: int, ceiling: int) -> int:
    """Cuantos contactos mas entran en una campaña que ya tiene `total`: el tope del plan
    (si lo hay) y `ceiling`, el techo global."""
    cap = ceiling if limits.max_campaign_contacts is None else min(limits.max_campaign_contacts, ceiling)
    return max(cap - total, 0)


def check_campaign_concurrency(limits: Limits, concurrency: int) -> None:
    cap = limits.max_campaign_concurrency
    if cap is not None and concurrency > cap:
        raise QuotaExceeded(f"Tu plan permite hasta {cap} llamadas simultaneas por campaña.", "campaign_concurrency")


def check_campaign_followup(limits: Limits) -> None:
    if not limits.campaign_followup:
        raise QuotaExceeded("Tu plan no incluye el seguimiento por WhatsApp.", "campaign_followup_not_in_plan")


def check_campaign_start(s: Session, campaign: Campaign, limits: Limits, now: datetime.datetime | None = None) -> None:
    """Lo que el plan exige para iniciar o retomar una campaña: el canal, el cupo del mes (solo
    la primera vez: una pausada que ya empezo no gasta otro), los contactos y, en voz, la concurrencia."""
    check_campaign_channel(limits, campaign.channel)
    if campaign.started_at is None:
        check_campaign_month(s, campaign.client_id, limits, now)
    total = s.scalar(select(func.count()).select_from(CampaignContact)
                     .where(CampaignContact.campaign_id == campaign.id)) or 0
    check_campaign_contacts(limits, total)
    if campaign.channel == "voice":
        check_campaign_concurrency(limits, campaign.concurrency or 1)


def active_contacts(s: Session, client_id: str) -> int:
    """Contactos activos de la agenda (los archivados no cuentan para el tope)."""
    return s.scalar(select(func.count()).select_from(Contact).where(
        Contact.client_id == client_id, Contact.archived_at.is_(None))) or 0


def contacts_room(s: Session, client_id: str, limits: Limits) -> int | None:
    """Cuantos contactos activos mas entran en la agenda; None si no hay tope."""
    cap = limits.max_contacts
    return None if cap is None else max(cap - active_contacts(s, client_id), 0)


def pause_campaigns_outside_plan(s: Session, client: Client, limits: Limits) -> int:
    """Al bajar de plan: las campañas en curso o programadas de un canal que el plan nuevo no
    incluye pasan a pausadas, con el motivo. Devuelve cuantas."""
    rows = s.scalars(select(Campaign).where(
        Campaign.client_id == client.id, Campaign.status.in_(("running", "scheduled")),
        Campaign.channel.not_in(limits.campaign_channels or ("",))))
    n = 0
    for c in rows:
        c.status = "paused"
        c.status_reason = f"El plan {limits.tier_name} no incluye campañas por {CHANNEL_NAMES.get(c.channel, c.channel)}"
        n += 1
    s.flush()
    return n
