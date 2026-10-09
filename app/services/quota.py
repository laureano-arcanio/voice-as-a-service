"""Limites del tier de cada cliente: llamadas simultaneas y minutos por mes.

- Concurrencia: llamadas del cliente en pendiente, sonando o en curso (todas las
  modalidades; la de prueba y el loadtest tambien ocupan agente e inferencia).
- Minutos: entrantes y salientes por separado, por mes calendario en
  settings.billing_timezone. Una llamada cuenta en el mes en que empezo; la que esta
  en curso cuenta lo que lleva. Las de prueba y loadtest no consumen minutos.

- Tope global: MAX_CONCURRENT_CALLS_GLOBAL llamadas activas entre todos los clientes
  (la inferencia es una sola); INBOUND_RESERVE_CALLS de esos lugares quedan para las
  entrantes, que no se pueden reprogramar.
- Duracion: cada llamada se corta a los effective_max_call_seconds() de su cliente (tier o
  CALL_MAX_DURATION_SECONDS), en todas las modalidades, aunque el tier no tenga limites.

Corte duro: admit() rechaza la llamada nueva si no hay lugar o minutos, y devuelve
cuantos segundos le quedan (tope de duracion). Durante la llamada el worker vuelve a
mirar remaining_seconds() y corta al agotarse o al llegar a call_limit_seconds()
(app/voice/worker.py).
"""
import datetime
from collections.abc import Collection
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    CallMode,
    CallRow,
    Client,
    ConversationRow,
    effective_max_call_seconds,
)
from .errors import QuotaExceeded

MINUTE_MODES = {CallMode.entrante: "inbound", CallMode.saliente: "outbound"}
# Una llamada "activa" que paso su tope de duracion + este margen (desde started_at, o
# created_at si no arranco) quedo colgada: se cayo el worker sin cerrarla y la conciliacion
# con LiveKit (services/reconcile.py) todavia no la cerro. Deja de ocupar lugar, pero su
# consumo sigue contando hasta el tope (used_seconds). El margen cubre la espera de la de
# prueba (5 min) y el timbre de la saliente.
STALE_MARGIN_SECONDS = 600
# Clave de pg_advisory_xact_lock que serializa todas las admisiones (tope global). Fija:
# cualquier numero sirve mientras nadie mas la use.
GLOBAL_ADMIT_LOCK = 0x41544E01
PLATFORM_BUSY_MESSAGE = "En este momento estamos al máximo de llamadas simultáneas. Probá en unos minutos."


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


def _since():
    """Desde cuando corre el tope de una llamada: started_at, o created_at si no arranco."""
    return func.coalesce(CallRow.started_at, CallRow.created_at)


def _stale_before(now: datetime.datetime, max_seconds: int) -> datetime.datetime:
    return now - datetime.timedelta(seconds=max_seconds + STALE_MARGIN_SECONDS)


def _client_max_seconds(s: Session, client_id: str | None) -> int:
    return effective_max_call_seconds(s.get(Client, client_id) if client_id else None)


def _active_filter(client_id: str, now: datetime.datetime, max_seconds: int):
    return (CallRow.client_id == client_id, CallRow.status.in_(ACTIVE_CALL_STATUSES),
            _since() >= _stale_before(now, max_seconds))


def _agents_filter(agent_ids: Collection[str] | None):
    """Solo las llamadas de esos agentes (la demo de la landing, que comparte cliente)."""
    if agent_ids is None:
        return ()
    return (CallRow.conversation_id.in_(select(ConversationRow.id).where(ConversationRow.agent_id.in_(agent_ids))),)


def active_calls(s: Session, client_id: str, now: datetime.datetime | None = None,
                 agent_ids: Collection[str] | None = None) -> int:
    filters = _active_filter(client_id, now or utcnow(), _client_max_seconds(s, client_id))
    return s.scalar(select(func.count()).select_from(CallRow).where(*filters, *_agents_filter(agent_ids))) or 0


def active_calls_global(s: Session, now: datetime.datetime | None = None) -> int:
    """Llamadas activas de todos los clientes (y sin cliente), cada una con el tope de su tier.
    La base filtra con el techo (CALL_DURATION_CEILING_SECONDS) y el resto se mira aca: son
    pocas filas (las activas) y el tope depende del tier de cada una."""
    now = now or utcnow()
    rows = s.execute(
        select(CallRow.started_at, CallRow.created_at, Client)
        .outerjoin(Client, Client.id == CallRow.client_id)
        .where(CallRow.status.in_(ACTIVE_CALL_STATUSES),
               _since() >= _stale_before(now, settings.call_duration_ceiling_seconds))).all()
    return sum(1 for started, created, client in rows
               if (started or created) >= _stale_before(now, effective_max_call_seconds(client)))


def used_seconds(s: Session, client_id: str, mode: str, start: datetime.datetime, end: datetime.datetime,
                 now: datetime.datetime | None = None, agent_ids: Collection[str] | None = None) -> int:
    """Segundos de `mode` que empezaron en [start, end): terminadas + lo que llevan las en curso.

    Una en curso cuenta hasta el tope de duracion del cliente: la que quedo colgada (se cayo
    el worker sin cerrarla) no ocupa lugar despues del tope, pero su consumo no vuelve a 0."""
    now = now or utcnow()
    max_seconds = _client_max_seconds(s, client_id)
    in_period = (CallRow.client_id == client_id, CallRow.mode == mode,
                 CallRow.started_at >= start, CallRow.started_at < end, *_agents_filter(agent_ids))
    done = s.scalar(select(func.coalesce(func.sum(CallRow.duration_seconds), 0))
                    .where(*in_period, CallRow.status.notin_(ACTIVE_CALL_STATUSES))) or 0
    running = s.scalars(select(CallRow.started_at).where(*in_period, CallRow.status.in_(ACTIVE_CALL_STATUSES))).all()
    return int(done) + sum(min(max(int((now - t).total_seconds()), 0), max_seconds) for t in running)


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


def call_limit_seconds(s: Session, conversation_id: str, requested: int | None = None) -> int:
    """Segundos que puede durar la llamada desde que arranca: el tope del tier
    (effective_max_call_seconds, tambien sin limites de minutos), los minutos que le quedan
    al cliente en esa modalidad y `requested` (el max_duration_seconds del pedido)."""
    call = s.get(CallRow, conversation_id)
    client = s.get(Client, call.client_id) if call is not None and call.client_id else None
    limits = [effective_max_call_seconds(client)]
    if requested:
        limits.append(requested)
    if client is not None and call.mode in MINUTE_MODES:
        remaining = remaining_seconds(s, client, call.mode)
        if remaining is not None:
            limits.append(remaining)
    return max(min(limits), 0)


def _lock_global(s: Session) -> None:
    """Serializa las admisiones de todos los clientes hasta el commit (tope global). Va
    antes del lock de la fila del cliente: siempre en ese orden, para no trabarse. En
    SQLite (tests) no hace falta: las escrituras ya van de a una."""
    if s.get_bind().dialect.name == "postgresql":
        s.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": GLOBAL_ADMIT_LOCK})


def _check_global(s: Session, mode: str, now: datetime.datetime) -> None:
    """MAX_CONCURRENT_CALLS_GLOBAL entre todos; las que no son entrantes, ademas, dejan
    INBOUND_RESERVE_CALLS libres (una saliente o una prueba se pueden repetir; una entrante no)."""
    limit = settings.max_concurrent_calls_global
    if mode != CallMode.entrante:
        limit -= settings.inbound_reserve_calls
    if active_calls_global(s, now) >= limit:
        raise QuotaExceeded(PLATFORM_BUSY_MESSAGE, "platform_busy")


def admit(s: Session, client_id: str, mode: str) -> int | None:
    """Toma los locks y verifica que pueda empezar una llamada de `mode`: cliente activo,
    tier (concurrencia y minutos) y tope global. Devuelve los segundos de minutos que le
    quedan (None: sin tope) o levanta QuotaExceeded.

    Los locks (advisory global y fila del cliente) serializan las admisiones hasta el
    commit: quien llama tiene que crear la CallRow activa en la misma sesion y hacer
    commit, asi la siguiente admision la cuenta."""
    _lock_global(s)
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
    _check_global(s, mode, now)
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

