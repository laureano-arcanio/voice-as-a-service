"""Limites del tier de cada cliente: llamadas simultaneas, cantidad de llamadas por hora, dia y mes,
y minutos por mes.

- Concurrencia: llamadas del cliente en pendiente, sonando o en curso (todas las
  modalidades; la de prueba y el loadtest tambien ocupan agente e inferencia).
- Cantidad: entrantes y salientes juntas que se crearon en la hora, el dia o el mes calendario en
  settings.billing_timezone (se renuevan al empezar la hora, a las 00:00 y el dia 1). Cuentan
  las atendidas o falladas; no las rechazadas por el tier ni las de prueba o loadtest.
- Minutos: entrantes y salientes por separado, por mes calendario en
  settings.billing_timezone. Una llamada cuenta en el mes en que empezo; la que esta
  en curso cuenta lo que lleva. Las de prueba y loadtest no consumen minutos.

Corte duro: admit() rechaza la llamada nueva si no hay lugar o minutos, y devuelve
cuantos segundos le quedan (tope de duracion). Durante la llamada el worker vuelve a
mirar remaining_seconds() y corta al agotarse (app/voice/worker.py).
"""
import datetime
from collections.abc import Collection
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    CallMode,
    CallRow,
    CallStatus,
    Client,
    ConversationRow,
)
from .errors import QuotaExceeded

MINUTE_MODES = {CallMode.entrante: "inbound", CallMode.saliente: "outbound"}
# Una llamada "activa" mas vieja que esto quedo colgada (se cayo el worker sin
# cerrarla): no ocupa lugar. Cubre la espera de la de prueba (5 min) + la duracion maxima.
STALE_MARGIN_SECONDS = 600
# Topes de cantidad de llamadas: (periodo, campo del tier, como se dice, cuando se renueva).
CALL_COUNT_LIMITS = (
    ("hour", "max_calls_per_hour", "por hora", "al empezar la proxima hora"),
    ("day", "max_calls_per_day", "por dia", "a las 00:00"),
    ("month", "max_calls_per_month", "por mes", "el dia 1"),
)


def month_bounds(now: datetime.datetime | None = None, month: str | None = None) -> tuple[datetime.datetime, datetime.datetime]:
    """[inicio, fin) del mes en UTC naive. month: 'YYYY-MM'; sin el, el mes en curso."""
    tz = ZoneInfo(settings.billing_timezone)
    if month:
        year, mon = (int(p) for p in month.split("-"))
    else:
        local = (now or datetime.datetime.now(datetime.UTC)).astimezone(tz)
        year, mon = local.year, local.month
    start = datetime.datetime(year, mon, 1, tzinfo=tz)
    end = datetime.datetime(year + (mon == 12), mon % 12 + 1, 1, tzinfo=tz)
    to_utc = lambda d: d.astimezone(datetime.UTC).replace(tzinfo=None)
    return to_utc(start), to_utc(end)


def period_start(period: str, now: datetime.datetime) -> datetime.datetime:
    """Inicio (UTC naive) de la hora, el dia o el mes calendario en curso, en billing_timezone.
    `now` en UTC naive."""
    aware = now.replace(tzinfo=datetime.UTC)
    if period == "month":
        return month_bounds(aware)[0]
    local = aware.astimezone(ZoneInfo(settings.billing_timezone)).replace(minute=0, second=0, microsecond=0)
    if period == "day":
        local = local.replace(hour=0)
    return local.astimezone(datetime.UTC).replace(tzinfo=None)


def calls_started(s: Session, client_id: str, since: datetime.datetime,
                  until: datetime.datetime | None = None) -> int:
    """Entrantes y salientes creadas en [since, until) que no rechazo el tier."""
    where = [CallRow.client_id == client_id, CallRow.mode.in_(list(MINUTE_MODES)),
             CallRow.status != CallStatus.rechazada, CallRow.created_at >= since]
    if until is not None:
        where.append(CallRow.created_at < until)
    return s.scalar(select(func.count()).select_from(CallRow).where(*where)) or 0


def _active_filter(client_id: str, now: datetime.datetime):
    stale = now - datetime.timedelta(seconds=settings.call_max_duration_seconds + STALE_MARGIN_SECONDS)
    return (CallRow.client_id == client_id, CallRow.status.in_(ACTIVE_CALL_STATUSES), CallRow.created_at >= stale)


def _agents_filter(agent_ids: Collection[str] | None):
    """Solo las llamadas de esos agentes (la demo de la landing, que comparte cliente)."""
    if agent_ids is None:
        return ()
    return (CallRow.conversation_id.in_(select(ConversationRow.id).where(ConversationRow.agent_id.in_(agent_ids))),)


def active_calls(s: Session, client_id: str, now: datetime.datetime | None = None,
                 agent_ids: Collection[str] | None = None) -> int:
    return s.scalar(select(func.count()).select_from(CallRow)
                    .where(*_active_filter(client_id, now or utcnow()), *_agents_filter(agent_ids))) or 0


def used_seconds(s: Session, client_id: str, mode: str, start: datetime.datetime, end: datetime.datetime,
                 now: datetime.datetime | None = None, agent_ids: Collection[str] | None = None) -> int:
    """Segundos de `mode` que empezaron en [start, end): terminadas + lo que llevan las en curso."""
    now = now or utcnow()
    in_period = (CallRow.client_id == client_id, CallRow.mode == mode,
                 CallRow.started_at >= start, CallRow.started_at < end, *_agents_filter(agent_ids))
    done = s.scalar(select(func.coalesce(func.sum(CallRow.duration_seconds), 0))
                    .where(*in_period, CallRow.status.notin_(ACTIVE_CALL_STATUSES))) or 0
    running = s.scalars(select(CallRow.started_at).where(*in_period, *_active_filter(client_id, now))).all()
    return int(done) + sum(max(int((now - t).total_seconds()), 0) for t in running)


def limit_seconds(client: Client, mode: str) -> int | None:
    """Tope de minutos del tier para esa modalidad, en segundos. None: sin tope."""
    kind = MINUTE_MODES.get(mode)
    if kind is None:
        return None
    minutes = getattr(client.tier, f"{kind}_minutes")
    return None if minutes is None else minutes * 60


def remaining_seconds(s: Session, client: Client, mode: str, now: datetime.datetime | None = None) -> int | None:
    limit = limit_seconds(client, mode)
    if limit is None:
        return None
    now = now or utcnow()
    start, end = month_bounds(now.replace(tzinfo=datetime.UTC))
    return limit - used_seconds(s, client.id, mode, start, end, now)


def admit(s: Session, client_id: str, mode: str) -> int | None:
    """Toma el lock del cliente y verifica que pueda empezar una llamada de `mode`.
    Devuelve los segundos que le quedan (None: sin tope) o levanta QuotaExceeded.

    El lock (sobre la fila del cliente) serializa las admisiones del
    mismo cliente hasta el commit: quien llama tiene que crear la CallRow activa en
    la misma sesion y hacer commit, asi la siguiente admision la cuenta."""
    # FOR NO KEY UPDATE (key_share): serializa las admisiones del cliente pero no
    # bloquea los FOR KEY SHARE de las foreign keys (insertar la conversacion en otra
    # sesion mientras se tiene el lock, services/calls.py). Con FOR UPDATE se trababa.
    client = s.scalar(select(Client).where(Client.id == client_id).with_for_update(key_share=True, of=Client))
    if client is None or not client.active:
        raise QuotaExceeded("El cliente esta inactivo", "client_inactive")
    now = utcnow()
    tier = client.tier
    if tier.max_concurrent_calls is not None and active_calls(s, client.id, now) >= tier.max_concurrent_calls:
        raise QuotaExceeded(f"Llegaste al limite de {tier.max_concurrent_calls} llamadas simultaneas de tu plan",
                            "concurrency_limit")
    if mode in MINUTE_MODES:
        for period, attr, label, renews in CALL_COUNT_LIMITS:
            limit = getattr(tier, attr)
            if limit is not None and calls_started(s, client.id, period_start(period, now)) >= limit:
                raise QuotaExceeded(f"Llegaste al limite de {limit} llamadas {label} de tu plan. "
                                    f"Se renueva {renews}", f"calls_per_{period}")
    remaining = remaining_seconds(s, client, mode, now)
    if remaining is not None and remaining <= 0:
        kind = MINUTE_MODES[mode]
        label = "entrantes" if kind == "inbound" else "salientes"
        raise QuotaExceeded(f"No quedan minutos {label} en el plan este mes", f"{kind}_minutes")
    return remaining


@dataclass
class MinutesUsage:
    used_seconds: int
    limit_minutes: int | None


@dataclass
class CallsUsage:
    used: int
    limit: int | None


@dataclass
class Usage:
    month: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    active_calls: int
    max_concurrent_calls: int | None
    inbound: MinutesUsage
    outbound: MinutesUsage
    # La hora y el dia son los en curso; el mes, el pedido.
    calls_hour: CallsUsage
    calls_day: CallsUsage
    calls_month: CallsUsage


def usage(s: Session, client: Client, month: str | None = None) -> Usage:
    now = utcnow()
    tier = client.tier
    start, end = month_bounds(now.replace(tzinfo=datetime.UTC), month)
    local = start.replace(tzinfo=datetime.UTC).astimezone(ZoneInfo(settings.billing_timezone))
    return Usage(
        month=f"{local.year:04d}-{local.month:02d}", period_start=start, period_end=end,
        active_calls=active_calls(s, client.id, now), max_concurrent_calls=client.tier.max_concurrent_calls,
        inbound=MinutesUsage(used_seconds(s, client.id, CallMode.entrante, start, end, now), client.tier.inbound_minutes),
        outbound=MinutesUsage(used_seconds(s, client.id, CallMode.saliente, start, end, now), client.tier.outbound_minutes),
        calls_hour=CallsUsage(calls_started(s, client.id, period_start("hour", now)), tier.max_calls_per_hour),
        calls_day=CallsUsage(calls_started(s, client.id, period_start("day", now)), tier.max_calls_per_day),
        calls_month=CallsUsage(calls_started(s, client.id, start, end), tier.max_calls_per_month),
    )

