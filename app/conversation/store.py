import datetime

from sqlalchemy import JSON, DateTime, String, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .models import ConversationState, Progress


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
    progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ConversationStore:
    def __init__(self, dsn: str):
        self.engine = create_engine(dsn, pool_pre_ping=True, pool_recycle=1800)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        # create_all no agrega columnas a una tabla existente.
        if "progress" not in {c["name"] for c in inspect(self.engine).get_columns("conversations")}:
            with self.engine.begin() as conn:
                conn.execute(text("ALTER TABLE conversations ADD COLUMN progress JSON NULL"))

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
