import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, create_schema, make_engine, make_sessions, utcnow
from .models import ConversationState, Progress


class ConversationRow(Base):
    """Estado del motor conversacional: datos extraidos, mensajes y progreso."""
    __tablename__ = "conversations"
    __table_args__ = (
        # El dashboard lista de la mas nueva a la mas vieja y filtra por fecha (main.chart).
        Index("ix_conversations_created_at", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    fields: Mapped[dict] = mapped_column(JSONDoc)
    messages: Mapped[list] = mapped_column(JSONDoc)
    progress: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConversationStore:
    def __init__(self, dsn: str):
        self.engine = make_engine(dsn)
        self.sessions = make_sessions(self.engine)
        create_schema(self.engine)

    def get(self, conversation_id: str) -> ConversationState | None:
        with self.sessions() as s:
            row = s.get(ConversationRow, conversation_id)
            if row is None:
                return None
            return ConversationState(
                conversation_id=row.id, workflow_id=row.workflow_id, status=row.status,
                fields=row.fields, messages=row.messages,
                progress=Progress.model_validate(row.progress or {}),
            )

    def save(self, state: ConversationState) -> None:
        data = state.model_dump(mode="json")
        with self.sessions() as s:
            row = s.get(ConversationRow, state.conversation_id) or ConversationRow(id=state.conversation_id)
            row.workflow_id = state.workflow_id
            row.status = state.status
            row.fields = data["fields"]
            row.messages = data["messages"]
            row.progress = data["progress"]
            s.add(row)
            s.commit()
