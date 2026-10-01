from sqlalchemy.orm import Session, sessionmaker

from ..db import create_schema, make_engine, make_sessions
from ..models import ConversationRow
from .models import ConversationState, Progress


class ConversationStore:
    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions

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
            )

    def save(self, state: ConversationState) -> None:
        with self.sessions() as s:
            self.add(s, state)
            s.commit()

    @staticmethod
    def add(s: Session, state: ConversationState) -> None:
        """Agrega o actualiza la conversacion en la sesion `s`, sin commit (quien llama
        la guarda junto con lo suyo, ej. la llamada)."""
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
        s.add(row)
