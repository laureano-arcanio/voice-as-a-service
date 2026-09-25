"""Registro telefonico de cada conversacion: teléfono, estado de la llamada,
duracion y latencia por turno. La conversacion en si (datos y mensajes) vive en
ConversationStore; esta tabla la complementa para el dashboard.

Estados: pendiente -> sonando -> en_curso -> finalizada | fallida.
Modos: saliente (marca por SIP), entrante (llama el cliente), prueba (navegador),
loadtest (scripts/loadtest/).
"""
import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .conversation.store import Base, ConversationRow, ConversationStore, utcnow


class CallRow(Base):
    __tablename__ = "call_logs"
    conversation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pendiente")
    ended_reason: Mapped[str] = mapped_column(String(128), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    latency: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class CallLog:
    def __init__(self, store: ConversationStore):
        self.sessions = store.sessions
        Base.metadata.create_all(store.engine)

    def create(self, conversation_id: str, mode: str, phone: str | None = None) -> None:
        with self.sessions() as s:
            s.add(CallRow(conversation_id=conversation_id, mode=mode, phone=phone))
            s.commit()

    def update(self, conversation_id: str, **values) -> None:
        with self.sessions() as s:
            row = s.get(CallRow, conversation_id)
            if row is None:
                return
            for k, v in values.items():
                setattr(row, k, v)
            s.commit()

    def get(self, conversation_id: str) -> CallRow | None:
        with self.sessions() as s:
            return s.get(CallRow, conversation_id)

    def created_at(self, conversation_id: str) -> datetime.datetime | None:
        with self.sessions() as s:
            row = s.get(ConversationRow, conversation_id)
            return row.created_at if row else None

    def list(self, since: datetime.datetime | None = None, limit: int | None = None):
        """Conversaciones con su llamada (None si se crearon por la API sin llamada),
        de la mas nueva a la mas vieja."""
        with self.sessions() as s:
            q = s.query(ConversationRow, CallRow).outerjoin(
                CallRow, CallRow.conversation_id == ConversationRow.id)
            if since is not None:
                q = q.filter(ConversationRow.created_at >= since)
            q = q.order_by(ConversationRow.created_at.desc())
            if limit:
                q = q.limit(limit)
            return q.all()
