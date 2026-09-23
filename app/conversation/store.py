import datetime

from sqlalchemy import JSON, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .models import ConversationState


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class ConversationRow(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    fields: Mapped[dict] = mapped_column(JSON)
    messages: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConversationStore:
    def __init__(self, dsn: str):
        self.engine = create_engine(dsn, pool_pre_ping=True, pool_recycle=1800)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def get(self, conversation_id: str) -> ConversationState | None:
        with self.sessions() as s:
            row = s.get(ConversationRow, conversation_id)
            if row is None:
                return None
            return ConversationState(
                conversation_id=row.id, workflow_id=row.workflow_id, status=row.status,
                fields=row.fields, messages=row.messages,
            )

    def save(self, state: ConversationState) -> None:
        data = state.model_dump(mode="json")
        with self.sessions() as s:
            row = s.get(ConversationRow, state.conversation_id) or ConversationRow(id=state.conversation_id)
            row.workflow_id = state.workflow_id
            row.status = state.status
            row.fields = data["fields"]
            row.messages = data["messages"]
            s.add(row)
            s.commit()
