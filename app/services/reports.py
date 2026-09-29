"""Lo que muestra el dashboard: llamadas (conversacion + llamada), detalle,
indicadores y la serie diaria. Filtrable por cliente, agente y fechas."""
import datetime
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents.definitions import DefinitionSource
from ..agents.templates import load_template
from ..conversation.models import ConversationState, Progress, Workflow
from ..conversation.workflow import INCOMPLETE, is_required, outcome_for
from ..models import Agent, CallRow, Client, ConversationRow, PhoneNumber


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

    def local_date(self, dt: datetime.datetime) -> datetime.date:
        return dt.replace(tzinfo=datetime.UTC).astimezone(self.tz).date()

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
        if self.mode:
            # "api": conversacion por texto, sin llamada.
            conds.append(CallRow.mode.is_(None) if self.mode == "api" else CallRow.mode == self.mode)
        return conds


def _base_query():
    return (select(ConversationRow, CallRow, Agent.name, Client.name)
            .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id)
            .outerjoin(Agent, Agent.id == ConversationRow.agent_id)
            .outerjoin(Client, Client.id == ConversationRow.client_id))


class Reports:
    def __init__(self, s: Session, definitions: DefinitionSource):
        self.s = s
        self.definitions = definitions

    def workflow(self, conv: ConversationRow) -> Workflow | None:
        """La version del agente con que corrio; si es anterior a los agentes, la plantilla."""
        try:
            if conv.agent_id:
                return self.definitions.get(conv.agent_id, conv.agent_version or 1, self.s)
            if conv.legacy_workflow_id:
                return load_template(conv.legacy_workflow_id)
        except KeyError:
            pass
        return None

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
                client_name: str | None) -> dict:
        workflow = self.workflow(conv)
        f = conv.fields
        required = [n for n, spec in workflow.fields.items() if is_required(spec, f)] if workflow else list(f)
        outcome = self.outcome(workflow, conv)
        lat = (call.latency or {}).get("stats", {}).get("total") if call else None
        return {
            "id": conv.id, "client_id": conv.client_id, "client_name": client_name,
            "agent_id": conv.agent_id, "agent_name": agent_name or conv.legacy_workflow_id,
            "agent_version": conv.agent_version, "workflow_status": conv.status,
            "created_at": iso(conv.created_at),
            "contact_name": f.get("contact_name"),
            "company": f.get("company_name") or f.get("company_context"),
            "outcome": outcome.label if outcome else None, "goal": bool(outcome and outcome.goal),
            "captured": sum(f.get(n) is not None for n in required), "required": len(required),
            "mode": call.mode if call else "api", "phone": call.phone if call else None,
            "status": call.status if call else None,
            "duration_seconds": call.duration_seconds if call else 0,
            "ended_reason": call.ended_reason if call else "",
            "latency_avg": lat["avg"] if lat else None,
        }

    def page(self, flt: CallFilter, limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        conds = flt.where()
        total = self.s.scalar(select(func.count()).select_from(ConversationRow)
                              .outerjoin(CallRow, CallRow.conversation_id == ConversationRow.id).where(*conds)) or 0
        rows = self.s.execute(_base_query().where(*conds).order_by(ConversationRow.created_at.desc())
                              .limit(limit).offset(offset)).all()
        return [self.summary(*r) for r in rows], total

    def _all(self, flt: CallFilter) -> list[dict]:
        return [self.summary(*r) for r in self.s.execute(_base_query().where(*flt.where())).all()]

    def detail(self, conversation_id: str) -> dict | None:
        row = self.s.execute(_base_query().where(ConversationRow.id == conversation_id)).first()
        if row is None:
            return None
        conv, call, agent_name, client_name = row
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
        }

    def stats(self, flt: CallFilter) -> dict:
        rows = self._all(flt)
        phone_calls = [r for r in rows if r["mode"] != "api"]
        done = [r for r in phone_calls if r["status"] == "finalizada"]
        completed = [r for r in rows if r["workflow_status"] == "completed"]
        goal = [r for r in rows if r["goal"]]
        latencies = [r["latency_avg"] for r in done if r["latency_avg"] is not None]
        pct = lambda n, d: round(100 * n / d, 1) if d else 0
        return {
            "total": len(rows), "calls": len(phone_calls), "finished": len(done),
            "failed": sum(r["status"] == "fallida" for r in phone_calls),
            "rejected": sum(r["status"] == "rechazada" for r in phone_calls),
            "completed": len(completed), "completed_pct": pct(len(completed), len(rows)),
            "goal": len(goal), "goal_pct": pct(len(goal), len(rows)),
            "total_minutes": round(sum(r["duration_seconds"] for r in done) / 60, 1),
            "avg_duration": round(sum(r["duration_seconds"] for r in done) / len(done)) if done else 0,
            "latency_avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
        }

    def daily(self, flt: CallFilter) -> dict:
        """Conversaciones por dia + % con workflow completo y % que cumplen el objetivo."""
        assert flt.date_from and flt.date_to
        days = [flt.date_from + datetime.timedelta(d) for d in range((flt.date_to - flt.date_from).days + 1)]
        buckets: dict[datetime.date, list[dict]] = {d: [] for d in days}
        for r in self._all(flt):
            day = flt.local_date(datetime.datetime.fromisoformat(r["created_at"].rstrip("Z")))
            if day in buckets:
                buckets[day].append(r)
        pct = lambda rows, key: round(100 * sum(key(r) for r in rows) / len(rows), 1) if rows else None
        return {
            "labels": [d.isoformat() for d in days],
            "totals": [len(buckets[d]) for d in days],
            "completed_pct": [pct(buckets[d], lambda r: r["workflow_status"] == "completed") for d in days],
            "goal_pct": [pct(buckets[d], lambda r: r["goal"]) for d in days],
        }
