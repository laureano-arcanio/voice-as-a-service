"""Limites del tier de cada cliente: llamadas simultaneas y minutos por mes.

- Concurrencia: llamadas del cliente en pendiente, sonando o en curso (todas las
  modalidades; la de prueba y el loadtest tambien ocupan agente e inferencia).
- Minutos: entrantes y salientes por separado, por mes calendario en
  settings.billing_timezone. Una llamada cuenta en el mes en que empezo; la que esta
  en curso cuenta lo que lleva. Las de prueba y loadtest no consumen minutos.

Corte duro: admit() rechaza la llamada nueva si no hay lugar o minutos, y devuelve
cuantos segundos le quedan (tope de duracion). Durante la llamada el worker vuelve a
mirar remaining_seconds() y corta al agotarse (app/voice/worker.py).
"""
import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import ACTIVE_CALL_STATUSES, CallMode, CallRow, Client
from .errors import QuotaExceeded

MINUTE_MODES = {CallMode.entrante: "inbound", CallMode.saliente: "outbound"}
# Una llamada "activa" mas vieja que esto quedo colgada (se cayo el worker sin
# cerrarla): no ocupa lugar. Cubre la espera de la de prueba (5 min) + la duracion maxima.
STALE_MARGIN_SECONDS = 600


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


def _active_filter(client_id: str, now: datetime.datetime):
    stale = now - datetime.timedelta(seconds=settings.call_max_duration_seconds + STALE_MARGIN_SECONDS)
    return (CallRow.client_id == client_id, CallRow.status.in_(ACTIVE_CALL_STATUSES), CallRow.created_at >= stale)


def active_calls(s: Session, client_id: str, now: datetime.datetime | None = None) -> int:
    return s.scalar(select(func.count()).select_from(CallRow).where(*_active_filter(client_id, now or utcnow()))) or 0


def used_seconds(s: Session, client_id: str, mode: str, start: datetime.datetime, end: datetime.datetime,
                 now: datetime.datetime | None = None) -> int:
    """Segundos de `mode` que empezaron en [start, end): terminadas + lo que llevan las en curso."""
    now = now or utcnow()
    in_period = (CallRow.client_id == client_id, CallRow.mode == mode,
                 CallRow.started_at >= start, CallRow.started_at < end)
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
class Usage:
    month: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    active_calls: int
    max_concurrent_calls: int | None
    inbound: MinutesUsage
    outbound: MinutesUsage


def usage(s: Session, client: Client, month: str | None = None) -> Usage:
    now = utcnow()
    start, end = month_bounds(now.replace(tzinfo=datetime.UTC), month)
    local = start.replace(tzinfo=datetime.UTC).astimezone(ZoneInfo(settings.billing_timezone))
    return Usage(
        month=f"{local.year:04d}-{local.month:02d}", period_start=start, period_end=end,
        active_calls=active_calls(s, client.id, now), max_concurrent_calls=client.tier.max_concurrent_calls,
        inbound=MinutesUsage(used_seconds(s, client.id, CallMode.entrante, start, end, now), client.tier.inbound_minutes),
        outbound=MinutesUsage(used_seconds(s, client.id, CallMode.saliente, start, end, now), client.tier.outbound_minutes),
    )

