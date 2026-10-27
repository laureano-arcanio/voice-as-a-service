"""Reportes del panel (docs/REPORTES_PLAN.md, 9.2): una funcion por reporte, con agregados en SQL.

Nada de cargar conversacion por conversacion: se agrupa en la base y, donde no hay SQL portable entre
PostgreSQL y SQLite (dias en otra zona, percentiles), se trae solo lo agregado o columnas chicas.

- Los dias y horas van en la zona del filtro: la base agrupa por hora UTC y Python pasa cada hora a la
  hora local (exacto para zonas de horas enteras, como las de Argentina).
- "Consulta": una conversacion de cliente (llamada, atendida o no, o conversacion de WhatsApp). Sin el
  loadtest nunca; sin las de prueba ni las de la API (sin llamada y canal voice) salvo `include_tests`.
- "Transferencia": conversacion con un pedido de derivacion (REQUEST_EVENTS: la pedida, la que no se pudo
  por horario o sin miembros, y la asignacion de WhatsApp); "atendida": con ANSWER_EVENTS.
- Conversion: conversations.conversion (complete, partial, empty); NULL (anteriores al backfill) cuenta
  como empty.
"""
import datetime
import math
from collections import defaultdict
from dataclasses import dataclass, field, replace
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Float,
    and_,
    case,
    cast,
    column,
    distinct,
    exists,
    false,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import (
    Agent,
    BillingPayment,
    CallRow,
    Campaign,
    CampaignContact,
    Client,
    Contact,
    ContactOptout,
    ConversationRow,
    Event,
    HandoffArea,
    HandoffLeg,
    PhoneNumber,
    Subscription,
    TeamMember,
    Tier,
    ToolRun,
    WaAccount,
    WaAccountStatusLog,
    WaMessage,
    WaThread,
)
from . import limits as limits_service
from . import quota
from .errors import Invalid

CHANNELS = ("voice", "whatsapp", "web")
MAX_DAYS = 366
DEFAULT_DAYS = 30
CALL_MODES = ("entrante", "saliente", "web", "prueba")
REQUEST_EVENTS = ("handoff.requested", "handoff.unavailable", "wa.handoff.assigned")
ANSWER_EVENTS = ("handoff.connected", "wa.handoff.first_reply")
# Rechazos por el plan (services/quota.admit): clientes que no se atendieron.
LIMIT_REASONS = ("concurrency_limit", "calls_per_hour", "calls_per_day", "calls_per_month", "inbound_minutes",
                 "outbound_minutes")
ENDED_REASONS = ("customer_hangup", "agent_end", "off_topic", "hangup_by_user", "blocked_number", "rejected",
                 "failed", "other")
DURATION_BUCKETS = (("0-15s", 15), ("15-60s", 60), ("1-3m", 180), ("3-5m", 300), ("5-10m", 600), ("10m+", None))
EARLY_SECONDS = 15
NO_CONTACT = {"busy": "busy", "no_answer": "no_answer", "voicemail": "voicemail", "invalid": "invalid",
              "failed": "failed", "rejected": "failed"}
NO_CONTACT_REASONS = ("busy", "no_answer", "voicemail", "invalid", "failed", "other")
NEAR_QUOTA_PCT = 80
INACTIVE_DAYS = 14
TOP_CALLERS = 10


@dataclass
class ReportFilter:
    client_id: str | None = None        # None: todos los clientes (solo admin)
    agent_id: str | None = None
    channel: str | None = None          # voice | whatsapp | web
    phone_number_id: str | None = None  # una linea del cliente (solo llamadas)
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None    # inclusive
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo(settings.billing_timezone))
    include_tests: bool = False

    def with_defaults(self, now: datetime.datetime | None = None) -> "ReportFilter":
        """Los ultimos 30 dias hasta hoy (en tz) si faltan las fechas; valida el rango."""
        today = (now or utcnow()).replace(tzinfo=datetime.UTC).astimezone(self.tz).date()
        date_to = self.date_to or (today if self.date_from is None
                                   else min(today, self.date_from + datetime.timedelta(days=DEFAULT_DAYS - 1)))
        date_from = self.date_from or date_to - datetime.timedelta(days=DEFAULT_DAYS - 1)
        if date_to < date_from or (date_to - date_from).days >= MAX_DAYS:
            raise Invalid(f"Rango de fechas inválido (hasta {MAX_DAYS} días)")
        if self.channel is not None and self.channel not in CHANNELS:
            raise Invalid(f"Canal inválido: {self.channel}")
        return replace(self, date_from=date_from, date_to=date_to)

    def previous(self) -> "ReportFilter":
        """El mismo largo, inmediatamente antes."""
        n = (self.date_to - self.date_from).days + 1
        return replace(self, date_from=self.date_from - datetime.timedelta(days=n),
                       date_to=self.date_from - datetime.timedelta(days=1))

    @property
    def start(self) -> datetime.datetime:
        return _utc(self.date_from, self.tz)

    @property
    def end(self) -> datetime.datetime:
        return _utc(self.date_to + datetime.timedelta(days=1), self.tz)

    def days(self) -> list[datetime.date]:
        return [self.date_from + datetime.timedelta(d) for d in range((self.date_to - self.date_from).days + 1)]

    def local(self, dt: datetime.datetime) -> datetime.datetime:
        return dt.replace(tzinfo=datetime.UTC).astimezone(self.tz)


def _utc(day: datetime.date, tz: ZoneInfo) -> datetime.datetime:
    """Medianoche de `day` en `tz`, en UTC naive (como created_at)."""
    return datetime.datetime.combine(day, datetime.time(), tz).astimezone(datetime.UTC).replace(tzinfo=None)


# ---------- helpers de SQL ----------

def _pg(s: Session) -> bool:
    return s.get_bind().dialect.name == "postgresql"


def _hour(s: Session, col):
    """La hora UTC de `col` (truncada), para agrupar."""
    return func.date_trunc("hour", col) if _pg(s) else func.strftime("%Y-%m-%d %H:00:00", col)


def _as_dt(v) -> datetime.datetime:
    return v if isinstance(v, datetime.datetime) else datetime.datetime.fromisoformat(str(v))


def _seconds(s: Session, a, b):
    """Segundos de `a` a `b` (dos DateTime)."""
    if _pg(s):
        return func.extract("epoch", b - a)
    return (func.julianday(b) - func.julianday(a)) * 86400.0


def _n(v) -> int:
    return int(v or 0)


def _pct(n, d) -> float | None:
    return round(100 * n / d, 1) if d else None


def _avg(total, n, digits: int = 0):
    if not n:
        return None
    return round(total / n) if digits == 0 else round(total / n, digits)


def _percentile(values: list[float], q: float) -> float | None:
    """Percentil con interpolacion lineal (como percentile_cont)."""
    if not values:
        return None
    v = sorted(values)
    k = (len(v) - 1) * q
    lo = math.floor(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def _round(v: float | None, digits: int = 3) -> float | None:
    return None if v is None else round(v, digits)


def _count_if(cond):
    return func.coalesce(func.sum(case((cond, 1), else_=0)), 0)


def _has_event(types) -> exists:
    return exists().where(Event.conversation_id == ConversationRow.id, Event.type.in_(types))


KIND = case((ConversationRow.channel == "whatsapp", "whatsapp"), (CallRow.mode == "web", "web"), else_="voice")
CONVERSION = func.coalesce(ConversationRow.conversion, "empty")


def _conv_where(flt: ReportFilter, dates: bool = True) -> list:
    """Las conversaciones del filtro. Pide el outer join con call_logs (_convs)."""
    conds = [ConversationRow.client_id.is_not(None)]
    if flt.client_id:
        conds.append(ConversationRow.client_id == flt.client_id)
    if flt.agent_id:
        conds.append(ConversationRow.agent_id == flt.agent_id)
    if dates:
        conds += [ConversationRow.created_at >= flt.start, ConversationRow.created_at < flt.end]
    if flt.include_tests:
        conds.append(or_(CallRow.mode.is_(None), CallRow.mode != "loadtest"))
    else:
        conds.append(or_(ConversationRow.channel == "whatsapp", CallRow.mode.in_(("entrante", "saliente", "web"))))
    if flt.channel == "whatsapp":
        conds.append(ConversationRow.channel == "whatsapp")
    elif flt.channel == "web":
        conds.append(CallRow.mode == "web")
    elif flt.channel == "voice":
        conds.append(and_(ConversationRow.channel != "whatsapp", or_(CallRow.mode.is_(None), CallRow.mode != "web")))
    if flt.phone_number_id:
        conds.append(CallRow.phone_number_id == flt.phone_number_id)
    return conds


def _convs(flt: ReportFilter, *cols, dates: bool = True):
    return (select(*cols).select_from(ConversationRow)
            .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id).where(*_conv_where(flt, dates)))


def _conv_ids(flt: ReportFilter):
    return _convs(flt, ConversationRow.id)


def _calls(flt: ReportFilter, *cols):
    """Solo las llamadas (con call_logs) del filtro."""
    return _convs(flt, *cols).where(CallRow.mode.is_not(None))


def _local_hours(flt: ReportFilter, rows):
    """(hora UTC, *resto) -> (datetime local, *resto), sin las horas fuera del periodo."""
    for hour, *rest in rows:
        local = flt.local(_as_dt(hour))
        if flt.date_from <= local.date() <= flt.date_to:
            yield local, *rest


def _agent_names(s: Session, ids) -> dict[str, str]:
    ids = [i for i in ids if i]
    if not ids:
        return {}
    return dict(s.execute(select(Agent.id, Agent.name).where(Agent.id.in_(ids))).all())


def _wa_messages(flt: ReportFilter, *cols):
    """Los mensajes de WhatsApp del periodo (por su hora), del cliente y el agente del filtro."""
    q = (select(*cols).select_from(WaMessage).join(WaAccount, WaAccount.id == WaMessage.account_id)
         .outerjoin(ConversationRow, ConversationRow.id == WaMessage.conversation_id)
         .where(WaMessage.created_at >= flt.start, WaMessage.created_at < flt.end))
    if flt.client_id:
        q = q.where(WaAccount.client_id == flt.client_id)
    if flt.agent_id:
        q = q.where(ConversationRow.agent_id == flt.agent_id)
    if (flt.channel and flt.channel != "whatsapp") or flt.phone_number_id:
        q = q.where(false())
    return q


# ---------- resumen ----------

def _kpis(s: Session, flt: ReportFilter) -> dict:
    finished = CallRow.status == "finalizada"
    row = s.execute(_convs(
        flt, func.count(), _count_if(KIND == "voice"), _count_if(KIND == "whatsapp"), _count_if(KIND == "web"),
        _count_if(ConversationRow.conversion == "complete"), _count_if(ConversationRow.goal.is_(True)),
        _count_if(_has_event(REQUEST_EVENTS)), _count_if(_has_event(ANSWER_EVENTS)),
        func.coalesce(func.sum(CallRow.duration_seconds), 0),
        func.coalesce(func.sum(case((finished, CallRow.duration_seconds), else_=0)), 0), _count_if(finished),
        _count_if(and_(CallRow.status == "rechazada", CallRow.ended_reason.in_(LIMIT_REASONS))))).one()
    total, voice, wa, web, complete, goal, transfers, answered, seconds, fin_seconds, fin, rejected = map(_n, row)
    return {
        "conversations": total, "by_channel": {"voice": voice, "whatsapp": wa, "web": web},
        "conversion_pct": _pct(complete, total), "goal_pct": _pct(goal, total),
        "transfers": transfers, "transfers_answered": answered, "transfer_pct": _pct(transfers, total),
        "minutes": round(seconds / 60, 1), "avg_duration": _avg(fin_seconds, fin),
        "rejected_by_limit": rejected,
        "wa_messages": _n(s.scalar(_wa_messages(flt, func.count()))),
    }


def _plan(s: Session, client_id: str) -> dict | None:
    """Consumo del mes en curso (services/quota.usage: los mismos minutos que corta el plan)."""
    client = s.get(Client, client_id)
    if client is None:
        return None
    usage = quota.usage(s, client)
    now = utcnow()
    elapsed = (now - usage.period_start) / (usage.period_end - usage.period_start)
    inbound = usage.inbound.used_seconds / 60
    return {
        "inbound_minutes_used": round(inbound, 1), "inbound_minutes_quota": usage.inbound.limit_minutes,
        "outbound_minutes_used": round(usage.outbound.used_seconds / 60, 1),
        "outbound_minutes_quota": usage.outbound.limit_minutes,
        "projected_inbound_minutes": round(inbound / elapsed, 1) if elapsed > 0 else None,
        "period_start": usage.period_start, "period_end": usage.period_end,
    }


def summary(s: Session, flt: ReportFilter) -> dict:
    """Consultas por canal y transferencias por dia, KPIs contra el periodo anterior y consumo del plan."""
    hour = _hour(s, ConversationRow.created_at)
    rows = s.execute(_convs(flt, hour, KIND, func.count(), _count_if(_has_event(REQUEST_EVENTS)),
                            _count_if(_has_event(ANSWER_EVENTS))).group_by(hour, KIND)).all()
    daily = {d: {"date": d, "voice": 0, "whatsapp": 0, "web": 0, "transfers": 0, "transfers_answered": 0}
             for d in flt.days()}
    for local, kind, n, transfers, answered in _local_hours(flt, rows):
        day = daily[local.date()]
        day[kind] += n
        day["transfers"] += _n(transfers)
        day["transfers_answered"] += _n(answered)
    return {
        "period": {"date_from": flt.date_from, "date_to": flt.date_to},
        "kpis": _kpis(s, flt), "previous": _kpis(s, flt.previous()),
        "plan": _plan(s, flt.client_id) if flt.client_id else None,
        "daily": list(daily.values()),
    }


# ---------- llamadas ----------

ENDED = case(
    (and_(CallRow.status == "rechazada", CallRow.ended_reason == "blocked_number"), "blocked_number"),
    (CallRow.status == "rechazada", "rejected"),
    (CallRow.status == "fallida", "failed"),
    (CallRow.ended_reason == "customer_hangup", "customer_hangup"),
    (CallRow.ended_reason == "completed", "agent_end"),
    (CallRow.ended_reason == "off_topic", "off_topic"),
    (CallRow.ended_reason == "hangup_by_user", "hangup_by_user"),
    else_="other")


def _duration_bucket():
    whens = [(CallRow.duration_seconds < upper, name) for name, upper in DURATION_BUCKETS if upper is not None]
    return case(*whens, else_=DURATION_BUCKETS[-1][0])


def _callers(s: Session, flt: ReportFilter) -> dict:
    """Quien llama o escribe: por telefono (entrantes) o wa_id (WhatsApp), sin el +. Nuevo: su primer contacto
    es del periodo; vuelve: ya habia escrito o llamado antes (con los mismos filtros)."""
    ident = case((ConversationRow.channel == "whatsapp", WaThread.wa_id),
                 else_=func.replace(CallRow.phone, "+", ""))

    def q(dates: bool):
        return (_convs(flt, ident.label("ident"), ConversationRow.created_at, dates=dates)
                .outerjoin(WaThread, WaThread.conversation_id == ConversationRow.id)
                .where(or_(ConversationRow.channel == "whatsapp",
                           and_(CallRow.mode == "entrante", CallRow.phone.is_not(None)))))

    period = q(True).subquery()
    rows = s.execute(select(period.c.ident, func.count(), func.max(period.c.created_at))
                     .where(period.c.ident.is_not(None)).group_by(period.c.ident)).all()
    before = q(False).where(ConversationRow.created_at < flt.start).subquery()
    returning = _n(s.scalar(select(func.count(distinct(before.c.ident)))
                            .where(before.c.ident.in_(select(period.c.ident)))))
    top = sorted((r for r in rows if r[1] > 1), key=lambda r: (-r[1], r[0]))[:TOP_CALLERS]
    return {"new": len(rows) - returning, "returning": returning,
            "top": [{"phone": ident, "count": n, "last_at": _as_dt(last)} for ident, n, last in top]}


def calls(s: Session, flt: ReportFilter) -> dict:
    """Llamadas por modo y dia, mapa de calor, por linea y agente, duracion, como terminan y quien llama."""
    hour = _hour(s, ConversationRow.created_at)
    rows = s.execute(_calls(flt, hour, CallRow.mode, func.count()).group_by(hour, CallRow.mode)).all()
    daily = {d: {"date": d, **{m: 0 for m in CALL_MODES}} for d in flt.days()}
    heat: dict[tuple[int, int], int] = defaultdict(int)
    for local, mode, n in _local_hours(flt, rows):
        if mode in CALL_MODES:
            daily[local.date()][mode] += n
        heat[(local.weekday(), local.hour)] += n

    finished = CallRow.status == "finalizada"
    complete = _count_if(ConversationRow.conversion == "complete")
    secs = func.coalesce(func.sum(CallRow.duration_seconds), 0)
    by_line = [
        {"phone_number_id": pid, "number": number, "calls": n, "minutes": round(_n(sec) / 60, 1),
         "conversion_pct": _pct(_n(comp), n)}
        for pid, number, n, sec, comp in s.execute(
            _calls(flt, CallRow.phone_number_id, PhoneNumber.e164, func.count(), secs, complete)
            .join(PhoneNumber, PhoneNumber.id == CallRow.phone_number_id)
            .group_by(CallRow.phone_number_id, PhoneNumber.e164).order_by(func.count().desc()))]
    agent_rows = s.execute(_calls(
        flt, ConversationRow.agent_id, func.count(), secs,
        func.coalesce(func.sum(case((finished, CallRow.duration_seconds), else_=0)), 0), _count_if(finished),
        complete, _count_if(ConversationRow.goal.is_(True)))
        .where(ConversationRow.agent_id.is_not(None)).group_by(ConversationRow.agent_id)).all()
    names = _agent_names(s, [r[0] for r in agent_rows])
    by_agent = sorted(({"agent_id": aid, "agent_name": names.get(aid, ""), "calls": n,
                        "minutes": round(_n(sec) / 60, 1), "avg_duration": _avg(_n(fsec), _n(fin)),
                        "conversion_pct": _pct(_n(comp), n), "goal_pct": _pct(_n(goal), n)}
                       for aid, n, sec, fsec, fin, comp, goal in agent_rows), key=lambda r: -r["calls"])

    bucket = _duration_bucket()
    counts = dict(s.execute(_calls(flt, bucket, func.count()).where(finished).group_by(bucket)).all())
    ended = dict(s.execute(_calls(flt, ENDED, func.count()).group_by(ENDED)).all())
    early = s.scalar(_calls(flt, func.count()).where(finished, CallRow.duration_seconds < EARLY_SECONDS))
    return {
        "daily": list(daily.values()),
        "heatmap": [{"weekday": w, "hour": h, "count": n} for (w, h), n in sorted(heat.items())],
        "by_line": by_line, "by_agent": by_agent,
        "durations": [{"bucket": name, "count": _n(counts.get(name))} for name, _ in DURATION_BUCKETS],
        "ended": [{"reason": r, "count": _n(ended.get(r))} for r in ENDED_REASONS],
        "early_hangups": _n(early),
        "callers": _callers(s, flt),
    }


# ---------- resultados ----------

def _outcome_defs(definition: dict | None) -> dict[str, dict]:
    from ..conversation.workflow import INCOMPLETE, OFF_TOPIC
    defs = {o.id: {"label": o.label, "goal": o.goal} for o in (INCOMPLETE, OFF_TOPIC)}
    for o in ((definition or {}).get("completion") or {}).get("outcomes") or []:
        if isinstance(o, dict) and o.get("id"):
            defs[o["id"]] = {"label": o.get("label") or o["id"], "goal": bool(o.get("goal"))}
    return defs


def _required_fields(definition: dict | None) -> list[tuple[str, str]]:
    """Los datos obligatorios (required) de la definicion, por prioridad: (nombre, etiqueta)."""
    fields = (definition or {}).get("fields") or {}
    specs = sorted(((n, f) for n, f in fields.items() if isinstance(f, dict) and f.get("required")),
                   key=lambda kv: kv[1].get("priority", 0))
    return [(n, f.get("label") or n) for n, f in specs]


def outcomes(s: Session, flt: ReportFilter) -> dict:
    """Conversion por dia y agente, resultados, embudo, datos capturados y comparacion por version."""
    hour = _hour(s, ConversationRow.created_at)
    rows = s.execute(_convs(flt, hour, CONVERSION, func.count()).group_by(hour, CONVERSION)).all()
    daily = {d: {"date": d, "complete": 0, "partial": 0, "empty": 0} for d in flt.days()}
    for local, conv, n in _local_hours(flt, rows):
        daily[local.date()][conv if conv in ("complete", "partial") else "empty"] += n

    goal = _count_if(ConversationRow.goal.is_(True))
    agent_rows = s.execute(_convs(
        flt, ConversationRow.agent_id, func.count(), _count_if(CONVERSION == "complete"),
        _count_if(CONVERSION == "partial"), goal).where(ConversationRow.agent_id.is_not(None))
        .group_by(ConversationRow.agent_id)).all()
    agents = {a.id: a for a in s.scalars(select(Agent).where(Agent.id.in_([r[0] for r in agent_rows])))}
    name = lambda aid: agents[aid].name if aid in agents else ""
    by_agent = sorted(({"agent_id": aid, "agent_name": name(aid), "total": n, "complete": _n(c), "partial": _n(p),
                        "empty": n - _n(c) - _n(p), "goal": _n(g)} for aid, n, c, p, g in agent_rows),
                      key=lambda r: -r["total"])

    out = []
    defs = {aid: _outcome_defs(a.definition) for aid, a in agents.items()}
    for aid, oid, n, g in s.execute(_convs(flt, ConversationRow.agent_id, ConversationRow.outcome, func.count(), goal)
                                    .where(ConversationRow.outcome.is_not(None), ConversationRow.agent_id.is_not(None))
                                    .group_by(ConversationRow.agent_id, ConversationRow.outcome)):
        d = defs.get(aid, {}).get(oid)
        out.append({"agent_id": aid, "agent_name": name(aid), "outcome": oid, "label": d["label"] if d else oid,
                    "goal": d["goal"] if d else _n(g) > 0, "count": n})
    out.sort(key=lambda r: (r["agent_name"], -r["count"]))

    total, with_data, complete, goals = map(_n, s.execute(_convs(
        flt, func.count(), _count_if(CONVERSION.in_(("complete", "partial"))), _count_if(CONVERSION == "complete"),
        goal)).one())

    fields = []
    for aid, a in agents.items():
        required = _required_fields(a.definition)
        if not required:
            continue
        cols = [func.count()]
        for fname, _ in required:
            value = ConversationRow.fields[fname].as_string()
            cols.append(_count_if(and_(value.is_not(None), value != "")))
        n, *captured = s.execute(_convs(flt, *cols).where(ConversationRow.agent_id == aid)).one()
        fields += [{"agent_id": aid, "agent_name": a.name, "field": fname, "label": label, "captured": _n(c),
                    "total": _n(n), "pct": _pct(_n(c), _n(n))} for (fname, label), c in zip(required, captured)]

    by_version = [
        {"agent_id": aid, "agent_name": name(aid), "version": version, "total": n,
         "conversion_pct": _pct(_n(c), n), "goal_pct": _pct(_n(g), n)}
        for aid, version, n, c, g in s.execute(_convs(
            flt, ConversationRow.agent_id, ConversationRow.agent_version, func.count(),
            _count_if(CONVERSION == "complete"), goal)
            .where(ConversationRow.agent_id.is_not(None), ConversationRow.agent_version.is_not(None))
            .group_by(ConversationRow.agent_id, ConversationRow.agent_version)
            .order_by(ConversationRow.agent_id, ConversationRow.agent_version))]
    return {
        "conversion_daily": list(daily.values()), "by_agent": by_agent, "outcomes": out,
        "funnel": {"conversations": total, "with_data": with_data, "complete": complete, "goal": goals},
        "fields": fields, "by_version": by_version,
    }


# ---------- mensajes (WhatsApp) ----------

def messages(s: Session, flt: ReportFilter) -> dict:
    """Mensajes de WhatsApp por dia y hora, entrega, fallas, conversion y estado de las cuentas."""
    hour = _hour(s, WaMessage.created_at)
    audio = WaMessage.type == "audio"
    rows = s.execute(_wa_messages(flt, hour, WaMessage.direction, func.count(), _count_if(audio))
                     .group_by(hour, WaMessage.direction)).all()
    daily = {d: {"date": d, "inbound": 0, "outbound": 0, "inbound_audio": 0, "outbound_audio": 0, "conversations": 0}
             for d in flt.days()}
    heat: dict[tuple[int, int], int] = defaultdict(int)
    for local, direction, n, audios in _local_hours(flt, rows):
        key = "inbound" if direction == "in" else "outbound"
        daily[local.date()][key] += n
        daily[local.date()][f"{key}_audio"] += _n(audios)
        if direction == "in":
            heat[(local.weekday(), local.hour)] += n

    wa = replace(flt, channel="whatsapp") if not flt.phone_number_id and flt.channel in (None, "whatsapp") else None
    conversion = {"complete": 0, "partial": 0, "empty": 0}
    if wa is not None:
        chour = _hour(s, ConversationRow.created_at)
        for local, n in _local_hours(flt, s.execute(_convs(wa, chour, func.count()).group_by(chour)).all()):
            daily[local.date()]["conversations"] += n
        for conv, n in s.execute(_convs(wa, CONVERSION, func.count()).group_by(CONVERSION)):
            conversion[conv if conv in conversion else "empty"] += n

    out = WaMessage.direction == "out"
    sent, delivered, read, failed = map(_n, s.execute(_wa_messages(
        flt, _count_if(and_(out, WaMessage.status.in_(("sent", "delivered", "read")))),
        _count_if(and_(out, WaMessage.status.in_(("delivered", "read")))),
        _count_if(and_(out, WaMessage.status == "read")), _count_if(and_(out, WaMessage.status == "failed")))).one())
    code, text = WaMessage.error["code"].as_string(), WaMessage.error["message"].as_string()
    failures = [{"code": None if c is None else str(c), "message": m, "count": n} for c, m, n in s.execute(
        _wa_messages(flt, code, text, func.count()).where(out, WaMessage.status == "failed")
        .group_by(code, text).order_by(func.count().desc()).limit(20))]
    n_msgs, n_convs = s.execute(_wa_messages(flt, func.count(), func.count(distinct(WaMessage.conversation_id)))
                                .where(WaMessage.conversation_id.is_not(None))).one()

    accounts = []
    if wa is not None:
        q = select(WaAccount).order_by(WaAccount.display_phone_number)
        if flt.client_id:
            q = q.where(WaAccount.client_id == flt.client_id)
        if flt.agent_id:
            q = q.where(WaAccount.agent_id == flt.agent_id)
        found = list(s.scalars(q))
        history = defaultdict(list)
        if found:
            for log in s.scalars(select(WaAccountStatusLog).where(
                    WaAccountStatusLog.account_id.in_([a.id for a in found]), WaAccountStatusLog.at >= flt.start,
                    WaAccountStatusLog.at < flt.end).order_by(WaAccountStatusLog.at)):
                history[log.account_id].append({"at": log.at, "status": log.status,
                                                "quality_rating": log.quality_rating,
                                                "messaging_limit": log.messaging_limit})
        accounts = [{"account_id": a.id, "display_phone_number": a.display_phone_number, "status": a.status,
                     "quality_rating": a.quality_rating, "messaging_limit": a.messaging_limit,
                     "history": history[a.id]} for a in found]
    return {
        "daily": list(daily.values()),
        "heatmap": [{"weekday": w, "hour": h, "count": n} for (w, h), n in sorted(heat.items())],
        "delivery": {"sent": sent, "delivered": delivered, "read": read, "failed": failed},
        "failures": failures, "per_conversation_avg": _avg(_n(n_msgs), _n(n_convs), 1),
        "conversion": conversion, "accounts": accounts,
    }


# ---------- transferencias ----------

def transfers(s: Session, flt: ReportFilter) -> dict:
    """Derivaciones por conversacion y area (pedidas, atendidas, no atendidas, sin disponibilidad), por dia,
    por area y por persona; WhatsApp aparte."""
    ids = _conv_ids(flt)
    flag = lambda types: func.max(case((Event.type.in_(types), 1), else_=0))
    pairs = s.execute(
        select(Event.conversation_id, Event.area_id,
               func.min(case((Event.type.in_(REQUEST_EVENTS), Event.at))),
               flag(REQUEST_EVENTS), flag(ANSWER_EVENTS), flag(("handoff.unavailable",)))
        .where(Event.conversation_id.in_(ids), Event.type.in_(REQUEST_EVENTS + ANSWER_EVENTS))
        .group_by(Event.conversation_id, Event.area_id)).all()
    daily = {d: {"date": d, "requested": 0, "answered": 0} for d in flt.days()}
    areas: dict[str | None, dict] = {}
    kpis = {"requested": 0, "answered": 0, "not_answered": 0, "unavailable": 0}
    for _, area_id, at, requested, answered, unavailable in pairs:
        if not requested:
            continue
        status = "answered" if answered else "unavailable" if unavailable else "not_answered"
        area = areas.setdefault(area_id, {"area_id": area_id, "name": "", "requested": 0, "answered": 0,
                                          "not_answered": 0, "unavailable": 0})
        for target in (kpis, area):
            target["requested"] += 1
            target[status] += 1
        day = flt.local(_as_dt(at)).date() if at is not None else None
        if day in daily:
            daily[day]["requested"] += 1
            daily[day]["answered"] += int(status == "answered")
    if areas:
        names = dict(s.execute(select(HandoffArea.id, HandoffArea.name)
                               .where(HandoffArea.id.in_([a for a in areas if a]))).all())
        for a in areas.values():
            a["name"] = names.get(a["area_id"], "") if a["area_id"] else ""

    answered_leg = HandoffLeg.connected_at.is_not(None)
    wait = case((HandoffLeg.answered_at.is_not(None), _seconds(s, HandoffLeg.created_at, HandoffLeg.answered_at)))
    leg_rows = s.execute(
        select(HandoffLeg.team_member_id, func.count(), _count_if(answered_leg),
               _count_if(and_(HandoffLeg.result != "dialing", ~answered_leg)),
               func.avg(case((answered_leg, wait))), func.coalesce(func.sum(HandoffLeg.billed_seconds), 0))
        .where(HandoffLeg.conversation_id.in_(ids)).group_by(HandoffLeg.team_member_id)).all()
    members = dict(s.execute(select(TeamMember.id, TeamMember.name)
                             .where(TeamMember.id.in_([r[0] for r in leg_rows if r[0]]))).all())
    by_member = sorted(({"team_member_id": mid, "name": members.get(mid, ""), "attempts": n, "answered": _n(a),
                         "not_answered": _n(na), "avg_answer_seconds": _round(w, 1), "minutes": round(_n(b) / 60, 1)}
                        for mid, n, a, na, w, b in leg_rows if mid), key=lambda r: -r["attempts"])
    avg_wait, billed = s.execute(select(func.avg(case((answered_leg, wait))),
                                        func.coalesce(func.sum(HandoffLeg.billed_seconds), 0))
                                 .where(HandoffLeg.conversation_id.in_(ids))).one()
    kpis |= {"answer_pct": _pct(kpis["answered"], kpis["requested"]), "avg_answer_seconds": _round(avg_wait, 1),
             "minutes": round(_n(billed) / 60, 1)}

    # WhatsApp: de la asignacion a la primera respuesta del vendedor, por conversacion.
    wa_rows = s.execute(
        select(Event.conversation_id, func.min(case((Event.type == "wa.handoff.assigned", Event.at))),
               func.min(case((Event.type == "wa.handoff.first_reply", Event.at))),
               _count_if(Event.type == "wa.handoff.reassigned"))
        .where(Event.conversation_id.in_(ids), Event.type.startswith("wa.handoff."))
        .group_by(Event.conversation_id)).all()
    waits = [(_as_dt(r) - _as_dt(a)).total_seconds() for _, a, r, _ in wa_rows if a is not None and r is not None]
    whatsapp = {"assigned": sum(a is not None for _, a, _, _ in wa_rows),
                "first_reply": sum(r is not None for _, _, r, _ in wa_rows),
                "avg_first_reply_seconds": round(sum(waits) / len(waits), 1) if waits else None,
                "reassigned": sum(_n(n) for *_, n in wa_rows)}
    return {"kpis": kpis, "daily": list(daily.values()),
            "by_area": sorted(areas.values(), key=lambda a: -a["requested"]), "by_member": by_member,
            "whatsapp": whatsapp}


# ---------- campañas ----------

def campaigns(s: Session, flt: ReportFilter) -> dict:
    """Campañas que corrieron en el periodo (comparativo), motivos de no contacto y mejores horarios."""
    q = select(Campaign).where(Campaign.started_at.is_not(None), Campaign.started_at < flt.end,
                               or_(Campaign.finished_at.is_(None), Campaign.finished_at >= flt.start))
    if flt.client_id:
        q = q.where(Campaign.client_id == flt.client_id)
    if flt.agent_id:
        q = q.where(Campaign.agent_id == flt.agent_id)
    if flt.channel in ("voice", "whatsapp"):
        q = q.where(Campaign.channel == flt.channel)
    elif flt.channel == "web":
        q = q.where(false())
    found = list(s.scalars(q.order_by(Campaign.started_at.desc())))
    ids = [c.id for c in found]
    if not ids:
        return {"campaigns": [], "no_contact": [{"reason": r, "count": 0} for r in NO_CONTACT_REASONS],
                "best_hours": []}

    cc = CampaignContact
    conv = ConversationRow
    per = {cid: vals for cid, *vals in s.execute(
        select(cc.campaign_id, func.count(), func.coalesce(func.sum(cc.attempts), 0), _count_if(cc.sent_at.is_not(None)),
               _count_if(cc.result == "answered"), _count_if(cc.replied_at.is_not(None)),
               _count_if(conv.conversion == "complete"), _count_if(conv.goal.is_(True)))
        .outerjoin(conv, conv.id == func.coalesce(cc.followup_conversation_id, cc.conversation_id))
        .where(cc.campaign_id.in_(ids)).group_by(cc.campaign_id))}
    minutes = dict(s.execute(
        select(cc.campaign_id, func.coalesce(func.sum(CallRow.duration_seconds), 0))
        .join(CallRow, CallRow.campaign_contact_id == cc.id).where(cc.campaign_id.in_(ids))
        .group_by(cc.campaign_id)).all())
    optouts = dict(s.execute(
        select(cc.campaign_id, func.count(distinct(ContactOptout.phone)))
        .join(Contact, Contact.id == cc.contact_id).join(Campaign, Campaign.id == cc.campaign_id)
        .join(ContactOptout, and_(ContactOptout.client_id == Campaign.client_id, ContactOptout.phone == Contact.phone,
                                  ContactOptout.created_at >= Campaign.started_at))
        .where(cc.campaign_id.in_(ids)).group_by(cc.campaign_id)).all())
    rows = []
    for c in found:
        n, attempts, sent, answered, replied, complete, goal = map(_n, per.get(c.id, [0] * 7))
        voice = c.channel == "voice"
        rows.append({"campaign_id": c.id, "name": c.name, "channel": c.channel, "status": c.status, "contacts": n,
                     "attempts": attempts if voice else sent, "reached": answered if voice else replied,
                     "complete": complete, "goal": goal, "optouts": _n(optouts.get(c.id)),
                     "minutes": round(_n(minutes.get(c.id)) / 60, 1)})

    reasons: dict[str, int] = defaultdict(int)
    for result, n in s.execute(select(cc.result, func.count()).join(Campaign, Campaign.id == cc.campaign_id)
                               .where(cc.campaign_id.in_(ids), Campaign.channel == "voice", cc.result.is_not(None),
                                      cc.result != "answered").group_by(cc.result)):
        reasons[NO_CONTACT.get(result, "other")] += n

    # Mejores horarios: los intentos de voz del periodo por hora local; atendio si la llamada se conecto.
    hour = _hour(s, CallRow.created_at)
    best: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])
    for local, n, reached in _local_hours(flt, s.execute(
            select(hour, func.count(), _count_if(CallRow.started_at.is_not(None)))
            .join(cc, cc.id == CallRow.campaign_contact_id)
            .where(cc.campaign_id.in_(ids), CallRow.created_at >= flt.start, CallRow.created_at < flt.end)
            .group_by(hour)).all()):
        best[(local.weekday(), local.hour)][0] += n
        best[(local.weekday(), local.hour)][1] += _n(reached)
    return {"campaigns": rows, "no_contact": [{"reason": r, "count": reasons[r]} for r in NO_CONTACT_REASONS],
            "best_hours": [{"weekday": w, "hour": h, "attempts": a, "reached": r}
                           for (w, h), (a, r) in sorted(best.items())]}


# ---------- tecnico (admin) ----------

def _messages_llm(s: Session):
    """(conversations, mensaje, traza) para leer messages[].llm[] en SQL: devuelve (join, role, kind, provider,
    model, ms, error) segun el dialecto. Los mensajes sin llm no dan filas de traza."""
    if _pg(s):
        m = func.jsonb_array_elements(ConversationRow.messages).table_valued(column("value", JSONB), name="m")
        llm = m.c.value["llm"]
        arr = case((func.jsonb_typeof(llm) == "array", llm), else_=cast(literal("[]"), JSONB))
        t = func.jsonb_array_elements(arr).table_valued(column("value", JSONB), name="t")
        get = lambda col, key: col.c.value[key].astext
        return m, t, get
    m = func.json_each(ConversationRow.messages).table_valued("value", name="m")
    t = func.json_each(func.json_extract(m.c.value, "$.llm")).table_valued("value", name="t")
    get = lambda col, key: func.json_extract(col.c.value, f"$.{key}")
    return m, t, get


def technical(s: Session, flt: ReportFilter) -> dict:
    """Latencia por dia (segundos, de call_logs.latency), turnos por proveedor del LLM, herramientas, errores,
    mails de resumen fallidos y tokens."""
    by_day: dict[datetime.date, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for created, latency in s.execute(_calls(flt, CallRow.created_at, CallRow.latency)
                                      .where(CallRow.latency.is_not(None))):
        day = flt.local(created).date()
        for turn in (latency or {}).get("turns") or []:
            for key in ("total", "stt", "eou", "llm", "tts"):
                if isinstance(turn.get(key), (int, float)):
                    by_day[day][key].append(float(turn[key]))
    latency_daily = []
    for d in flt.days():
        v = by_day.get(d, {})
        latency_daily.append({"date": d, "p50": _round(_percentile(v.get("total", []), 0.5)),
                              "p95": _round(_percentile(v.get("total", []), 0.95)),
                              **{f"{k}_p50": _round(_percentile(v.get(k, []), 0.5))
                                 for k in ("stt", "eou", "llm", "tts")}})

    m, t, get = _messages_llm(s)
    provider, model = func.coalesce(get(t, "provider"), "local"), get(t, "model")
    ms = cast(get(t, "ms"), Float())
    by_provider = [
        {"provider": p, "model": mo, "turns": n, "avg_ms": None if a is None else round(a), "errors": _n(e)}
        for p, mo, n, a, e in s.execute(
            _convs(flt, provider, model, func.count(), func.avg(ms), _count_if(get(t, "error").is_not(None)))
            .join(m, true()).join(t, true()).where(get(t, "kind") == "turno")
            .group_by(provider, model).order_by(func.count().desc()))]
    user_msgs = s.scalar(_convs(flt, func.count()).join(m, true()).where(get(m, "role") == "user"))
    convs = s.scalar(_convs(flt, func.count()))

    tools = _tools(s, flt)
    reason = func.coalesce(func.nullif(CallRow.ended_reason, ""), "unknown")
    errors = [{"reason": r, "count": n} for r, n in s.execute(
        _calls(flt, reason, func.count()).where(CallRow.status == "fallida").group_by(reason)
        .order_by(func.count().desc()))]
    failed_mails = s.scalar(_calls(flt, func.count()).where(CallRow.summary_email == "failed"))

    hour = _hour(s, ConversationRow.created_at)
    tokens_day = {d: {"date": d, "input": 0, "output": 0} for d in flt.days()}
    for local, i, o in _local_hours(flt, s.execute(_convs(
            flt, hour, func.coalesce(func.sum(ConversationRow.llm_input_tokens), 0),
            func.coalesce(func.sum(ConversationRow.llm_output_tokens), 0)).group_by(hour)).all()):
        tokens_day[local.date()]["input"] += _n(i)
        tokens_day[local.date()]["output"] += _n(o)
    return {
        "latency_daily": latency_daily, "by_provider": by_provider, "tools": tools,
        "turns_avg": _avg(_n(user_msgs), _n(convs), 1), "errors": errors, "failed_summary_emails": _n(failed_mails),
        "tokens": {"input": sum(d["input"] for d in tokens_day.values()),
                   "output": sum(d["output"] for d in tokens_day.values()), "by_day": list(tokens_day.values())},
    }


def _tools(s: Session, flt: ReportFilter) -> list[dict]:
    """Por herramienta: usos, errores y tiempos (tool_runs). El canal y la linea no aplican."""
    conds = [ToolRun.created_at >= flt.start, ToolRun.created_at < flt.end]
    if flt.client_id:
        conds.append(ToolRun.client_id == flt.client_id)
    if flt.agent_id:
        conds.append(ToolRun.agent_id == flt.agent_id)
    runs: dict[tuple, dict] = {}
    for tool_id, slug, type_, ok, ms in s.execute(select(ToolRun.tool_id, ToolRun.slug, ToolRun.type, ToolRun.ok,
                                                         ToolRun.ms).where(*conds)):
        r = runs.setdefault((tool_id, slug, type_), {"ms": [], "errors": 0})
        r["ms"].append(ms)
        r["errors"] += int(not ok)
    last = {}
    for tool_id, slug, error, at in s.execute(select(ToolRun.tool_id, ToolRun.slug, ToolRun.error, ToolRun.created_at)
                                              .where(*conds, ToolRun.ok.is_(False))
                                              .order_by(ToolRun.created_at)):
        last[(tool_id, slug)] = (error, at)
    out = []
    for (tool_id, slug, type_), r in runs.items():
        n = len(r["ms"])
        error, at = last.get((tool_id, slug), (None, None))
        out.append({"tool_id": tool_id, "slug": slug, "type": type_, "runs": n, "errors": r["errors"],
                    "error_pct": _pct(r["errors"], n), "p50_ms": _round(_percentile(r["ms"], 0.5), 0),
                    "p95_ms": _round(_percentile(r["ms"], 0.95), 0), "last_error": error or None,
                    "last_error_at": at})
    return sorted(out, key=lambda r: (-r["runs"], r["slug"]))


# ---------- plataforma (admin, todos los clientes) ----------

def platform(s: Session, flt: ReportFilter) -> dict:
    """Tabla por cliente con alertas, negocio (planes, altas, ingresos) y operacion (concurrencia, fallas)."""
    # cli importa servicios: aca, para no hacer un ciclo.
    from ..cli import INTERNAL_TIER
    flt = replace(flt, client_id=None)
    stats = {cid: vals for cid, *vals in s.execute(_convs(
        flt, ConversationRow.client_id, func.count(), func.coalesce(func.sum(CallRow.duration_seconds), 0),
        _count_if(ConversationRow.conversion == "complete"), _count_if(CallRow.status == "fallida"))
        .group_by(ConversationRow.client_id))}
    prev = dict(s.execute(_convs(flt.previous(), ConversationRow.client_id, func.count())
                          .group_by(ConversationRow.client_id)).all())
    last = dict(s.execute(select(ConversationRow.client_id, func.max(ConversationRow.created_at))
                          .where(ConversationRow.client_id.is_not(None)).group_by(ConversationRow.client_id)).all())
    now = utcnow()
    start, end = quota.month_bounds(now.replace(tzinfo=datetime.UTC))
    clients, alerts = [], []
    for c in s.scalars(select(Client).order_by(Client.name)):
        n, secs, complete, errors = map(_n, stats.get(c.id, [0, 0, 0, 0]))
        lim = limits_service.effective_limits(s, c, now)
        quota_pct = None
        if lim.inbound_minutes:
            used = quota.used_seconds(s, c.id, "entrante", start, end, now) / 60
            quota_pct = round(100 * used / lim.inbound_minutes, 1)
        before = _n(prev.get(c.id))
        last_at = _as_dt(last[c.id]) if last.get(c.id) else None
        clients.append({"client_id": c.id, "name": c.name, "tier": c.tier.name, "conversations": n,
                        "minutes": round(secs / 60, 1), "quota_pct": quota_pct, "conversion_pct": _pct(complete, n),
                        "errors": errors, "last_activity_at": last_at,
                        "delta_pct": round(100 * (n - before) / before, 1) if before else None})
        if not c.active or c.tier.name == INTERNAL_TIER:
            continue
        if quota_pct is not None and quota_pct >= NEAR_QUOTA_PCT:
            alerts.append({"client_id": c.id, "name": c.name, "kind": "near_quota",
                           "detail": f"{quota_pct:g} % de los minutos entrantes del mes"})
        idle_since = last_at or c.created_at
        if idle_since is not None and now - idle_since >= datetime.timedelta(days=INACTIVE_DAYS):
            days = (now - idle_since).days
            detail = f"{days} días sin conversaciones" if last_at else f"Sin conversaciones desde el alta ({days} días)"
            alerts.append({"client_id": c.id, "name": c.name, "kind": "inactive", "detail": detail})
    return {"clients": clients, "alerts": alerts, "business": _business(s, flt, start, end),
            "operation": _operation(s, flt)}


def _business(s: Session, flt: ReportFilter, month_start, month_end) -> dict:
    by_tier = [{"tier": t, "count": n} for t, n in s.execute(
        select(Tier.name, func.count()).join(Client, Client.tier_id == Tier.id).where(Client.active.is_(True))
        .group_by(Tier.name).order_by(func.count().desc(), Tier.name))]
    hour = _hour(s, Client.created_at)
    signups = {d: 0 for d in flt.days()}
    for local, n in _local_hours(flt, s.execute(
            select(hour, func.count()).where(Client.created_via == "signup", Client.created_at >= flt.start,
                                             Client.created_at < flt.end).group_by(hour)).all()):
        signups[local.date()] += n
    paying = (Subscription.status.in_(("active", "past_due")))
    mrr = s.scalar(select(func.coalesce(func.sum(Tier.price_ars), 0)).select_from(Subscription)
                   .join(Tier, Tier.id == Subscription.tier_id).where(paying))
    tz = ZoneInfo(settings.billing_timezone)
    first_day = month_start.replace(tzinfo=datetime.UTC).astimezone(tz).date()
    last_day = month_end.replace(tzinfo=datetime.UTC).astimezone(tz).date()
    approved = BillingPayment.status == "approved"
    payments = s.scalar(select(func.coalesce(func.sum(BillingPayment.amount_ars), 0))
                        .where(approved, BillingPayment.paid_on >= first_day, BillingPayment.paid_on < last_day))
    past_due = s.scalar(select(func.count()).select_from(Subscription).where(Subscription.status == "past_due"))
    # Free -> pago: clientes del registro con su primer pago aprobado en el periodo.
    first = (select(BillingPayment.client_id, func.min(BillingPayment.paid_on).label("first"))
             .where(approved).group_by(BillingPayment.client_id).subquery())
    free_to_paid = s.scalar(select(func.count()).select_from(first).join(Client, Client.id == first.c.client_id)
                            .where(Client.created_via == "signup", first.c.first >= flt.date_from,
                                   first.c.first <= flt.date_to))
    return {"clients_by_tier": by_tier, "signups": [{"date": d, "count": n} for d, n in signups.items()],
            "mrr_ars": _n(mrr), "payments_month_ars": _n(payments), "past_due": _n(past_due),
            "free_to_paid": _n(free_to_paid)}


def _operation(s: Session, flt: ReportFilter) -> dict:
    """Pico de llamadas simultaneas por hora local (de inicio y fin), fallidas por dia y rechazadas."""
    spans = s.execute(_calls(flt, CallRow.started_at, CallRow.ended_at, CallRow.duration_seconds)
                      .where(CallRow.started_at.is_not(None))).all()
    edges = []
    for start, end, secs in spans:
        end = end or start + datetime.timedelta(seconds=secs or 0)
        edges += [(start, 1), (max(end, start), -1)]
    peaks: dict[tuple[datetime.date, int], int] = {}
    current = 0
    for at, delta in sorted(edges, key=lambda e: (e[0], e[1])):
        current += delta
        local = flt.local(at)
        if delta > 0 and flt.date_from <= local.date() <= flt.date_to:
            key = (local.date(), local.hour)
            peaks[key] = max(peaks.get(key, 0), current)
    hour = _hour(s, ConversationRow.created_at)
    reason = func.coalesce(func.nullif(CallRow.ended_reason, ""), "unknown")
    failures: dict[tuple, int] = defaultdict(int)
    for local, r, n in _local_hours(flt, s.execute(_calls(flt, hour, reason, func.count())
                                                   .where(CallRow.status == "fallida").group_by(hour, reason)).all()):
        failures[(local.date(), r)] += n
    rejected = [{"reason": r, "count": n} for r, n in s.execute(
        _calls(flt, reason, func.count()).where(CallRow.status == "rechazada").group_by(reason)
        .order_by(func.count().desc()))]
    return {"peak_concurrency": [{"date": d, "hour": h, "peak": p} for (d, h), p in sorted(peaks.items())],
            "failures": [{"date": d, "reason": r, "count": n} for (d, r), n in sorted(failures.items())],
            "rejected": rejected}
