"""Consumo y limites de la API de inferencia (`/api/v1/inference`: LLM, STT y TTS con API key).

Solo cuenta el uso por la API: los agentes integrados (llamadas, WhatsApp) no pasan por aca y
siguen con los limites de minutos del tier (services/quota.py). Los limites son del tier, por
mes calendario en settings.billing_timezone (como los minutos de llamadas), y valen para todas
las keys del cliente juntas:

- `api_llm_input_tokens` / `api_llm_output_tokens`: tokens del prompt y generados, por separado.
- `api_tts_minutes`: minutos de audio sintetizado. `api_stt_minutes`: minutos de audio transcripto.
- `api_rate_limit`: pedidos por minuto (los tres motores juntos).
NULL = ilimitado; 0 = el plan no incluye ese motor (403 `not_in_plan`).

Corte: antes de cada pedido, `check()` rechaza (429) si el cupo del mes ya esta agotado, y devuelve
lo que queda para achicar lo que el pedido puede generar (max_tokens del chat). Despues, `record()`
suma lo que el motor informo. Un pedido puede pasarse del cupo por lo que consume el ultimo que
entro (el audio y el prompt se miden recien al terminar), pero el siguiente ya no pasa.
"""
import datetime
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ApiKey, ApiUsageDaily, Client
from .errors import Forbidden, QuotaExceeded

SCOPE_CALLS = "calls"
INFERENCE_SCOPES = ("llm", "stt", "tts")
ALL_SCOPES = (SCOPE_CALLS, *INFERENCE_SCOPES)


def parse_scopes(value: str | None) -> frozenset[str]:
    return frozenset(p for p in (value or "").replace(" ", "").split(",") if p)


def format_scopes(scopes) -> str:
    """En el orden canonico y sin repetidos (lo que se guarda)."""
    wanted = set(scopes)
    return ",".join(s for s in ALL_SCOPES if s in wanted)


# ---------- periodo ----------

def _tz() -> ZoneInfo:
    return ZoneInfo(settings.billing_timezone)


def today(now: datetime.datetime | None = None) -> datetime.date:
    return (now or datetime.datetime.now(datetime.UTC)).astimezone(_tz()).date()


def month_days(month: str | None = None, now: datetime.datetime | None = None) -> tuple[datetime.date, datetime.date]:
    """[primer dia, primer dia del mes siguiente) del mes `YYYY-MM` (sin el, el actual)."""
    if month:
        year, mon = (int(p) for p in month.split("-"))
    else:
        t = today(now)
        year, mon = t.year, t.month
    return datetime.date(year, mon, 1), datetime.date(year + (mon == 12), mon % 12 + 1, 1)


# ---------- registro ----------

@dataclass
class Totals:
    llm_requests: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    stt_requests: int = 0
    stt_seconds: float = 0.0
    tts_requests: int = 0
    tts_seconds: float = 0.0


_FIELDS = tuple(Totals.__dataclass_fields__)


def record(s: Session, client_id: str, key_id: str, day: datetime.date | None = None, **deltas: float) -> None:
    """Suma al dia (en la zona de facturacion) del cliente y la key. Atomico: un UPDATE que incrementa;
    si no hay fila todavia la crea (y si otro pedido la creo en el medio, reintenta el UPDATE)."""
    unknown = set(deltas) - set(_FIELDS)
    if unknown:
        raise ValueError(f"campos de consumo desconocidos: {sorted(unknown)}")
    day = day or today()
    where = (ApiUsageDaily.client_id == client_id, ApiUsageDaily.api_key_id == key_id, ApiUsageDaily.day == day)
    for _ in range(3):
        if s.execute(update(ApiUsageDaily).where(*where)
                     .values({k: getattr(ApiUsageDaily, k) + v for k, v in deltas.items()})).rowcount:
            s.commit()
            return
        try:
            s.add(ApiUsageDaily(client_id=client_id, api_key_id=key_id, day=day, **deltas))
            s.commit()
            return
        except IntegrityError:
            s.rollback()
    raise RuntimeError("no se pudo registrar el consumo de la API")


def _sums():
    return [func.coalesce(func.sum(getattr(ApiUsageDaily, f)), 0) for f in _FIELDS]


def _totals(row) -> Totals:
    t = Totals(*row)
    t.llm_requests, t.llm_input_tokens, t.llm_output_tokens = int(t.llm_requests), int(t.llm_input_tokens), \
        int(t.llm_output_tokens)
    t.stt_requests, t.tts_requests = int(t.stt_requests), int(t.tts_requests)
    t.stt_seconds, t.tts_seconds = float(t.stt_seconds), float(t.tts_seconds)
    return t


def totals(s: Session, client_id: str, start: datetime.date, end: datetime.date, key_id: str | None = None) -> Totals:
    q = select(*_sums()).where(ApiUsageDaily.client_id == client_id, ApiUsageDaily.day >= start,
                               ApiUsageDaily.day < end)
    if key_id:
        q = q.where(ApiUsageDaily.api_key_id == key_id)
    return _totals(s.execute(q).one())


def totals_by_key(s: Session, client_id: str, start: datetime.date, end: datetime.date) -> dict[str, Totals]:
    q = (select(ApiUsageDaily.api_key_id, *_sums())
         .where(ApiUsageDaily.client_id == client_id, ApiUsageDaily.day >= start, ApiUsageDaily.day < end)
         .group_by(ApiUsageDaily.api_key_id))
    return {row[0]: _totals(row[1:]) for row in s.execute(q)}


# ---------- limites ----------

MINUTE = 60


@dataclass
class Remaining:
    """Lo que le queda al cliente este mes (None: sin tope)."""
    llm_output_tokens: int | None = None
    seconds: float | None = None


def _exhausted(label: str, code: str) -> QuotaExceeded:
    return QuotaExceeded(f"Agotaste {label} de tu plan este mes. Se renueva el día 1.", code)


def _not_in_plan(label: str) -> Forbidden:
    return Forbidden(f"Tu plan no incluye {label} por API.", "not_in_plan")


def check(s: Session, client: Client, kind: str) -> Remaining:
    """Rechaza el pedido si el cupo del mes de ese motor ya se agoto; devuelve lo que queda.
    kind: llm, stt o tts."""
    tier = client.tier
    start, end = month_days()
    used = totals(s, client.id, start, end)
    if kind == "llm":
        tokens = {"in": (tier.api_llm_input_tokens, used.llm_input_tokens, "los tokens de entrada del LLM",
                         "api_llm_input_tokens"),
                  "out": (tier.api_llm_output_tokens, used.llm_output_tokens, "los tokens de salida del LLM",
                          "api_llm_output_tokens")}
        for limit, consumed, label, code in tokens.values():
            if limit == 0:
                raise _not_in_plan(label)
            if limit is not None and consumed >= limit:
                raise _exhausted(label, code)
        out_limit, out_used = tokens["out"][0], tokens["out"][1]
        return Remaining(llm_output_tokens=None if out_limit is None else out_limit - out_used)
    if kind == "stt":
        limit, consumed, label, code = tier.api_stt_minutes, used.stt_seconds, "los minutos de transcripción", \
            "api_stt_minutes"
    elif kind == "tts":
        limit, consumed, label, code = tier.api_tts_minutes, used.tts_seconds, "los minutos de síntesis", \
            "api_tts_minutes"
    else:
        raise ValueError(kind)
    if limit == 0:
        raise _not_in_plan(label)
    if limit is not None and consumed >= limit * MINUTE:
        raise _exhausted(label, code)
    return Remaining(seconds=None if limit is None else limit * MINUTE - consumed)


# ---------- reporte ----------

@dataclass
class Meter:
    used: float
    limit: int | None   # en la unidad del medidor (tokens o minutos)

    @property
    def remaining(self) -> float | None:
        return None if self.limit is None else max(self.limit - self.used, 0)


@dataclass
class KeyUsage:
    key_id: str
    name: str
    prefix: str
    revoked: bool
    scopes: list[str]
    totals: Totals


@dataclass
class InferenceUsage:
    month: str
    period_start: datetime.date
    period_end: datetime.date          # exclusivo
    rate_limit: int | None
    llm_input_tokens: Meter
    llm_output_tokens: Meter
    tts_minutes: Meter
    stt_minutes: Meter
    requests: Totals
    keys: list[KeyUsage] = field(default_factory=list)


def usage(s: Session, client: Client, month: str | None = None, key_id: str | None = None) -> InferenceUsage:
    """Consumo del mes contra los limites del tier. Con key_id, solo el de esa key (los limites son
    del cliente igual)."""
    start, end = month_days(month)
    t = totals(s, client.id, start, end, key_id)
    tier = client.tier
    keys = []
    per_key = totals_by_key(s, client.id, start, end)
    rows = s.scalars(select(ApiKey).where(ApiKey.client_id == client.id).order_by(ApiKey.created_at.desc())).all()
    for k in rows:
        if key_id and k.id != key_id:
            continue
        if k.id in per_key or (k.revoked_at is None and any(sc in INFERENCE_SCOPES for sc in parse_scopes(k.scopes))):
            keys.append(KeyUsage(k.id, k.name, k.prefix, k.revoked_at is not None,
                                 [sc for sc in ALL_SCOPES if sc in parse_scopes(k.scopes)],
                                 per_key.get(k.id, Totals())))
    return InferenceUsage(
        month=f"{start.year:04d}-{start.month:02d}", period_start=start, period_end=end,
        rate_limit=tier.api_rate_limit,
        llm_input_tokens=Meter(t.llm_input_tokens, tier.api_llm_input_tokens),
        llm_output_tokens=Meter(t.llm_output_tokens, tier.api_llm_output_tokens),
        tts_minutes=Meter(round(t.tts_seconds / MINUTE, 2), tier.api_tts_minutes),
        stt_minutes=Meter(round(t.stt_seconds / MINUTE, 2), tier.api_stt_minutes),
        requests=t, keys=keys)
