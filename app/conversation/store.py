import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, sessionmaker

from ..db import create_schema, make_engine, make_sessions
from ..models import ConversationRow
from .models import ConversationState, Progress, Workflow
from .workflow import conversion, outcome_goal

if TYPE_CHECKING:
    from ..agents.definitions import DefinitionSource

logger = logging.getLogger(__name__)


class ConversationStore:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions
        # De donde sale la definicion del agente para las columnas de los reportes (conversion, goal); la fija el
        # motor (ConversationEngine). Sin ella, la conversion sale solo del resultado y goal no cambia.
        self.definitions: "DefinitionSource | None" = None

    @classmethod
    def for_dsn(cls, dsn: str) -> "ConversationStore":
        """Store con su propio engine y el esquema creado con create_all: para SQLite en
        tests y scripts (eval). El stack usa las migraciones (make migrate)."""
        engine = make_engine(dsn)
        create_schema(engine)
        return cls(make_sessions(engine))

    def get(self, conversation_id: str) -> ConversationState | None:
        with self.sessions() as s:
            row = s.get(ConversationRow, conversation_id)
            if row is None:
                return None
            return ConversationState(
                conversation_id=row.id, agent_id=row.agent_id or row.legacy_workflow_id or "",
                agent_version=row.agent_version or 1, client_id=row.client_id,
                channel=row.channel or "voice", status=row.status,
                fields=row.fields, messages=row.messages,
                progress=Progress.model_validate(row.progress or {}),
                llm_input_tokens=row.llm_input_tokens or 0, llm_output_tokens=row.llm_output_tokens or 0,
            )

    def save(self, state: ConversationState) -> None:
        with self.sessions() as s:
            self.add(s, state, self.workflow(state, s))
            s.commit()

    def workflow(self, state: ConversationState, s: Session | None = None) -> Workflow | None:
        if self.definitions is None:
            return None
        try:
            return self.definitions.get(state.agent_id, state.agent_version, s)
        except Exception:       # un agente borrado no impide guardar la conversacion
            logger.warning("store: sin definicion de %s v%s", state.agent_id, state.agent_version)
            return None

    @staticmethod
    def add(s: Session, state: ConversationState, workflow: Workflow | None = None) -> None:
        """Agrega o actualiza la conversacion en la sesion `s`, sin commit (quien llama
        la guarda junto con lo suyo, ej. la llamada). workflow: la definicion, para las columnas de los
        reportes (conversion y goal)."""
        data = state.model_dump(mode="json")
        row = s.get(ConversationRow, state.conversation_id)
        if row is None:
            # Agente, version, cliente y canal se fijan al crearla y no cambian.
            row = ConversationRow(id=state.conversation_id, agent_id=state.agent_id,
                                  agent_version=state.agent_version, client_id=state.client_id,
                                  channel=state.channel)
        row.status = state.status
        row.fields = data["fields"]
        row.messages = data["messages"]
        row.progress = data["progress"]
        # Reportes (docs/REPORTES_PLAN.md, 9.1): el resultado al completarse, si cumple el objetivo y la conversion.
        outcome = state.progress.outcome if state.status == "completed" else None
        if workflow is not None:
            row.goal = outcome_goal(workflow, outcome)
        elif outcome != row.outcome:
            row.goal = None
        row.outcome = outcome
        row.conversion = conversion(workflow, state)
        row.llm_input_tokens = state.llm_input_tokens
        row.llm_output_tokens = state.llm_output_tokens
        s.add(row)
