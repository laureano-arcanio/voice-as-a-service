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
from ..models import Client, ClientLimitAdjustment, Tier

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
    return Limits(**values, tier_name=tier.name, adjusted=adjusted)


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
