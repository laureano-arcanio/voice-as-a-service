"""Lo que muestra el dashboard: llamadas (conversacion + llamada), detalle,
indicadores y la serie diaria. Filtrable por cliente, agente y fechas.

Las conversaciones de WhatsApp (channel="whatsapp") no tienen CallRow: su origen es
"whatsapp", el telefono es el wa_id del hilo y no cuentan como llamadas.

Indicadores y serie diaria se agregan en SQL (count/sum/group by) sin leer mensajes
ni latencias por turno (H09): el dashboard los pide cada 30-60 s."""
import dataclasses
import datetime
from collections import Counter
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, literal_column, or_, select
from sqlalchemy.orm import Session, defer

from ..agents.definitions import DefinitionSource
from ..agents.templates import load_reference
from ..conversation.models import ConversationState, Progress, Workflow
from ..conversation.workflow import INCOMPLETE, is_required, outcome_for
from ..models import (
    Agent,
    CallRow,
    Client,
    ConversationRow,
    PhoneNumber,
    WaAccount,
    WaMessage,
    WaThread,
)
from .errors import Invalid

# Rango de indicadores sin fechas (dias locales) y la diferencia maxima entre las dos
# fechas (la misma que valida /stats/daily).
DEFAULT_RANGE_DAYS = 30
MAX_RANGE_DAYS = 366


def iso(dt: datetime.datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _utc(day: datetime.date, tz: ZoneInfo) -> datetime.datetime:
    """Medianoche de `day` en `tz`, en UTC naive (como created_at)."""
    return datetime.datetime.combine(day, datetime.time(), tz).astimezone(datetime.UTC).replace(tzinfo=None)


@dataclass
class CallFilter:
    client_id: str | None = None
    agent_id: str | None = None
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None     # inclusive
    status: list[str] = field(default_factory=list)
    mode: str | None = None
    # Zona de las fechas: date_from/date_to y los dias del grafico son dias locales.
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))

    def bounded(self) -> "CallFilter":
        """Con las dos fechas: sin hasta, hoy; sin desde, DEFAULT_RANGE_DAYS antes del hasta.
        Invalid si el rango esta al reves o pasa de MAX_RANGE_DAYS."""
        today = datetime.datetime.now(self.tz).date()
        date_to = self.date_to or max(today, self.date_from or today)
        date_from = self.date_from or date_to - datetime.timedelta(DEFAULT_RANGE_DAYS - 1)
        if date_to < date_from or (date_to - date_from).days > MAX_RANGE_DAYS:
            raise Invalid(f"Rango de fechas invalido (hasta {MAX_RANGE_DAYS} dias)", "invalid_date_range")
        return dataclasses.replace(self, date_from=date_from, date_to=date_to)

    def where(self) -> list:
        conds = []
        if self.client_id:
            conds.append(ConversationRow.client_id == self.client_id)
        if self.agent_id:
            conds.append(ConversationRow.agent_id == self.agent_id)
        if self.date_from:
            conds.append(ConversationRow.created_at >= _utc(self.date_from, self.tz))
        if self.date_to:
            conds.append(ConversationRow.created_at < _utc(self.date_to + datetime.timedelta(days=1), self.tz))
        if self.status:
            conds.append(CallRow.status.in_(self.status))
        if self.mode == "whatsapp":
            conds.append(ConversationRow.channel == "whatsapp")
        elif self.mode == "api":
            # Conversacion por texto desde la API o la UI: sin llamada y no de WhatsApp.
            conds.append(CallRow.mode.is_(None) & (ConversationRow.channel == "voice"))
        elif self.mode:
            conds.append(CallRow.mode == self.mode)
        return conds


# Latencia media de la llamada (call_logs.latency.stats.total.avg), leida en SQL: el
# documento entero trae cada turno.
_LATENCY_AVG = CallRow.latency[("stats", "total", "avg")].as_float()
# Resultado guardado al completar (progress.outcome).
_OUTCOME_ID = ConversationRow.progress["outcome"].as_string()
# Llamada telefonica o de prueba: tiene CallRow y no es de WhatsApp.
_IS_CALL = and_(CallRow.conversation_id.is_not(None), ConversationRow.channel.is_distinct_from("whatsapp"))
_DONE = and_(_IS_CALL, CallRow.status == "finalizada")
_COMPLETED = ConversationRow.status == "completed"


def _count(cond):
    return func.coalesce(func.sum(case((cond, 1), else_=0)), 0)


def _eq(col, value):
    return col.is_(None) if value is None else col == value


def _base_query():
    return (select(ConversationRow, CallRow, Agent.name, Client.name, WaThread, WaAccount.display_phone_number)
            .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id)
            .outerjoin(Agent, Agent.id == ConversationRow.agent_id)
            .outerjoin(Client, Client.id == ConversationRow.client_id)
            .outerjoin(WaThread, WaThread.conversation_id == ConversationRow.id)
            .outerjoin(WaAccount, WaAccount.id == WaThread.account_id))


class Reports:
    def __init__(self, s: Session, definitions: DefinitionSource):
        self.s = s
        self.definitions = definitions
        self._workflows: dict[tuple, Workflow | None] = {}

    def workflow(self, conv: ConversationRow) -> Workflow | None:
        """La version del agente con que corrio; si es anterior a los agentes, la de referencia."""
        return self._workflow(conv.agent_id, conv.agent_version, conv.legacy_workflow_id)

    def _workflow(self, agent_id: str | None, version: int | None, legacy_id: str | None) -> Workflow | None:
        key = (agent_id, version, legacy_id)
        if key not in self._workflows:
            wf = None
            try:
                if agent_id:
                    wf = self.definitions.get(agent_id, version or 1, self.s)
                elif legacy_id:
                    wf = load_reference(legacy_id)
            except KeyError:
                pass
            self._workflows[key] = wf
        return self._workflows[key]

    def outcome(self, workflow: Workflow | None, conv: ConversationRow):
        """Resultado de una conversacion completa (el guardado, o calculado si es anterior a outcomes)."""
        if workflow is None or conv.status != "completed":
            return None
        progress = Progress.model_validate(conv.progress or {})
        outcome = next((o for o in [*workflow.completion.outcomes, INCOMPLETE] if o.id == progress.outcome), None)
        if outcome is None:
            outcome = outcome_for(workflow, ConversationState(
                conversation_id=conv.id, agent_id=conv.agent_id or "", fields=conv.fields, progress=Progress()))
        return outcome

    def summary(self, conv: ConversationRow, call: CallRow | None, agent_name: str | None,
                client_name: str | None, thread: WaThread | None, business_number: str | None,
                latency_avg: float | None) -> dict:
        """Fila de la lista. latency_avg: _LATENCY_AVG (la latencia de la llamada no se carga)."""
        workflow = self.workflow(conv)
        f = conv.fields
        required = [n for n, spec in workflow.fields.items() if is_required(spec, f)] if workflow else list(f)
        outcome = self.outcome(workflow, conv)
        if conv.channel == "whatsapp":
            mode, phone = "whatsapp", thread.wa_id if thread else None
        else:
            mode, phone = (call.mode, call.phone) if call else ("api", None)
        return {
            "id": conv.id, "client_id": conv.client_id, "client_name": client_name,
            "agent_id": conv.agent_id, "agent_name": agent_name or conv.legacy_workflow_id,
            "agent_version": conv.agent_version, "workflow_status": conv.status,
            "created_at": iso(conv.created_at),
            "contact_name": f.get("contact_name"),
            "company": f.get("company_name") or f.get("company_context"),
            "outcome": outcome.label if outcome else None, "goal": bool(outcome and outcome.goal),
            "captured": sum(f.get(n) is not None for n in required), "required": len(required),
            "mode": mode, "phone": phone,
            "status": call.status if call else None,
            "duration_seconds": call.duration_seconds if call else 0,
            "ended_reason": call.ended_reason if call else "",
            "latency_avg": latency_avg if call else None,
        }

    def page(self, flt: CallFilter, limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        conds = flt.where()
        total = self.s.scalar(select(func.count()).select_from(ConversationRow)
                              .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id).where(*conds)) or 0
        # Sin mensajes ni latencia por turno: la lista no los muestra y se refresca cada 5 s.
        rows = self.s.execute(_base_query().add_columns(_LATENCY_AVG).where(*conds)
                              .options(defer(ConversationRow.messages), defer(CallRow.latency))
                              .order_by(ConversationRow.created_at.desc()).limit(limit).offset(offset)).all()
        return [self.summary(*r) for r in rows], total

    def detail(self, conversation_id: str) -> dict | None:
        row = self.s.execute(_base_query().where(ConversationRow.id == conversation_id)).first()
        if row is None:
            return None
        conv, call, agent_name, client_name, thread, business_number = row
        workflow = self.workflow(conv)
        progress = Progress.model_validate(conv.progress or {})
        if workflow:
            specs = sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)
            fields = [{"name": n, "description": spec.description.strip(), "value": conv.fields.get(n),
                       "required": is_required(spec, conv.fields)} for n, spec in specs]
        else:
            fields = [{"name": n, "description": n, "value": v, "required": True} for n, v in conv.fields.items()]
        for f in fields:
            f["rejected"] = progress.rejected.get(f["name"])
        outcome = self.outcome(workflow, conv)
        number = self.s.get(PhoneNumber, call.phone_number_id) if call and call.phone_number_id else None
        return {
            "id": conv.id, "client_id": conv.client_id, "client_name": client_name,
            "agent_id": conv.agent_id, "agent_name": agent_name or conv.legacy_workflow_id,
            "agent_version": conv.agent_version, "created_at": iso(conv.created_at),
            "workflow_status": conv.status, "fields": fields,
            "outcome": None if outcome is None else {"label": outcome.label, "goal": outcome.goal},
            "messages": conv.messages,
            "call": None if call is None else {
                "mode": call.mode, "phone": call.phone, "status": call.status,
                "client_number": number.e164 if number else None,
                "ended_reason": call.ended_reason, "error": call.error,
                "duration_seconds": call.duration_seconds, "latency": call.latency,
                "created_at": iso(call.created_at), "started_at": iso(call.started_at),
                "ended_at": iso(call.ended_at),
            },
            "whatsapp": self._whatsapp(conv, thread, business_number),
        }

    def _whatsapp(self, conv: ConversationRow, thread: WaThread | None, business_number: str | None) -> dict | None:
        if conv.channel != "whatsapp" or thread is None:
            return None
        failed = list(self.s.scalars(select(WaMessage).where(
            WaMessage.conversation_id == conv.id, WaMessage.status == "failed").order_by(WaMessage.updated_at)))
        return {
            "wa_id": thread.wa_id, "contact_name": thread.contact_name, "business_number": business_number,
            "account_id": thread.account_id, "last_user_at": iso(thread.last_user_at),
            "closed_at": iso(thread.closed_at),
            "failed_messages": len(failed), "last_error": failed[-1].error if failed else None,
        }

    def _goals(self, conds: list, bucket=None) -> Counter:
        """Conversaciones completas cuyo resultado es objetivo, por `bucket` (sin el, todas en 0).

        Se agrupan por agente, version y resultado guardado: el workflow se resuelve una
        vez por grupo. Solo las anteriores a progress.outcome (o con un resultado que ya
        no esta en la definicion) se calculan fila por fila con sus datos."""
        keys = [ConversationRow.agent_id, ConversationRow.agent_version, ConversationRow.legacy_workflow_id]
        day = bucket.label("day") if bucket is not None else literal_column("0").label("day")
        sub = (select(*keys, _OUTCOME_ID.label("outcome"), day).select_from(ConversationRow)
               .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id)
               .where(*conds, _COMPLETED).subquery())
        goals: Counter = Counter()
        unresolved = []
        for agent_id, version, legacy, outcome_id, d, n in self.s.execute(
                select(*sub.c, func.count()).group_by(*sub.c)):
            workflow = self._workflow(agent_id, version, legacy)
            if workflow is None:
                continue
            outcome = next((o for o in [*workflow.completion.outcomes, INCOMPLETE] if o.id == outcome_id), None)
            if outcome is None:
                unresolved.append((agent_id, version, legacy, outcome_id))
            elif outcome.goal:
                goals[d] += n
        if unresolved:
            match = or_(*[and_(_eq(keys[0], a), _eq(keys[1], v), _eq(keys[2], lg), _eq(_OUTCOME_ID, o))
                          for a, v, lg, o in unresolved])
            for conv_id, agent_id, version, legacy, fields, d in self.s.execute(
                    select(ConversationRow.id, *keys, ConversationRow.fields, day)
                    .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id)
                    .where(*conds, _COMPLETED, match)):
                outcome = outcome_for(self._workflow(agent_id, version, legacy), ConversationState(
                    conversation_id=conv_id, agent_id=agent_id or "", fields=fields, progress=Progress()))
                if outcome.goal:
                    goals[d] += 1
        return goals

    def stats(self, flt: CallFilter) -> dict:
        """Indicadores del rango (sin fechas, los ultimos DEFAULT_RANGE_DAYS dias)."""
        conds = flt.bounded().where()
        row = self.s.execute(
            select(func.count(), _count(_IS_CALL), _count(_DONE),
                   _count(_IS_CALL & (CallRow.status == "fallida")),
                   _count(_IS_CALL & (CallRow.status == "rechazada")),
                   _count(_COMPLETED),
                   func.coalesce(func.sum(case((_DONE, CallRow.duration_seconds), else_=0)), 0),
                   func.sum(case((_DONE, _LATENCY_AVG))), func.count(case((_DONE, _LATENCY_AVG))),
                   _count(ConversationRow.channel == "whatsapp"))
            .select_from(ConversationRow).outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id)
            .where(*conds)).one()
        total, calls, done, failed, rejected, completed, seconds, lat_sum, lat_n, whatsapp = row
        goal = self._goals(conds)[0]
        pct = lambda n, d: round(100 * n / d, 1) if d else 0
        return {
            "total": total, "calls": calls, "finished": done, "failed": failed, "rejected": rejected,
            "completed": completed, "completed_pct": pct(completed, total),
            "goal": goal, "goal_pct": pct(goal, total),
            "total_minutes": round(seconds / 60, 1),
            "avg_duration": round(seconds / done) if done else 0,
            "latency_avg": round(lat_sum / lat_n, 2) if lat_n else None,
            "whatsapp": whatsapp,
        }

    def daily(self, flt: CallFilter) -> dict:
        """Conversaciones por dia + % con workflow completo y % que cumplen el objetivo."""
        flt = flt.bounded()
        days = [flt.date_from + datetime.timedelta(d) for d in range((flt.date_to - flt.date_from).days + 1)]
        # Dia local de cada conversacion en SQL, contra la medianoche UTC de cada dia (sirve
        # para cualquier zona y con cambio de horario, igual en PostgreSQL y SQLite).
        ends = [_utc(d + datetime.timedelta(1), flt.tz) for d in days]
        bucket = case(*[(ConversationRow.created_at < end, literal_column(str(i))) for i, end in enumerate(ends)])
        conds = flt.where()
        sub = (select(bucket.label("day"), _COMPLETED.label("completed")).select_from(ConversationRow)
               .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id).where(*conds).subquery())
        totals, completed = Counter(), Counter()
        for d, n, c in self.s.execute(select(sub.c.day, func.count(), _count(sub.c.completed))
                                      .group_by(sub.c.day)):
            totals[d], completed[d] = n, c
        goals = self._goals(conds, bucket)
        pct = lambda n, d: round(100 * n / d, 1) if d else None
        return {
            "labels": [d.isoformat() for d in days],
            "totals": [totals[i] for i in range(len(days))],
            "completed_pct": [pct(completed[i], totals[i]) for i in range(len(days))],
            "goal_pct": [pct(goals[i], totals[i]) for i in range(len(days))],
        }
