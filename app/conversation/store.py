from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ..db import create_schema, make_engine, make_sessions
from ..models import ConversationRow
from .models import ConversationState, Progress


class ConversationConflict(Exception):
    """Otro guardo la conversacion despues de que se leyo (conversations.version): el
    guardado se descarta en vez de pisar lo ajeno. La API lo devuelve como 409."""

    def __init__(self, conversation_id: str):
        super().__init__(f"La conversación {conversation_id} cambió mientras se procesaba")
        self.conversation_id = conversation_id


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
                version=row.version or 0,
            )

    def save(self, state: ConversationState) -> None:
        """ConversationConflict si otro la guardo despues de leerla (ver add)."""
        with self.sessions() as s:
            self.add(s, state)
            s.commit()

    @staticmethod
    def add(s: Session, state: ConversationState) -> None:
        """Agrega o actualiza la conversacion en la sesion `s`, sin commit (quien llama
        la guarda junto con lo suyo, ej. la llamada).

        Control optimista (H08): un estado leido con get() trae su version y solo se
        guarda si la fila sigue en esa version (UPDATE ... WHERE version = :v), que sube
        en uno. Si otro guardo en el medio (otro proceso, un turno por la API sobre una
        llamada), ConversationConflict. version None (estado armado a mano): pisa."""
        data = state.model_dump(mode="json")
        values = {"status": state.status, "fields": data["fields"], "messages": data["messages"],
                  "progress": data["progress"], "version": ConversationRow.version + 1}
        q = update(ConversationRow).where(ConversationRow.id == state.conversation_id)
        if state.version is not None:
            q = q.where(ConversationRow.version == state.version)
        if s.execute(q.values(**values)).rowcount:
            if state.version is not None:
                state.version += 1
            return
        if state.version is not None and s.scalar(
                select(ConversationRow.version).where(ConversationRow.id == state.conversation_id)) is not None:
            raise ConversationConflict(state.conversation_id)
        # Nueva. Agente, version, cliente y canal se fijan al crearla y no cambian.
        s.add(ConversationRow(id=state.conversation_id, agent_id=state.agent_id,
                              agent_version=state.agent_version, client_id=state.client_id,
                              channel=state.channel, status=state.status, fields=data["fields"],
                              messages=data["messages"], progress=data["progress"], version=0))
        state.version = 0
