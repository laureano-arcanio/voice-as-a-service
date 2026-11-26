"""Casos de prueba de un agente y sus corridas (docs/features/CASOS_DE_PRUEBA.md)."""
import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import new_id


class AgentTestCase(Base):
    """Una conversacion grabada hasta un turno del usuario, con los resultados de herramienta de ese turno y sus
    chequeos. Es una copia: si se borra la llamada, el caso sigue."""
    __tablename__ = "agent_test_cases"
    __table_args__ = (
        Index("ix_agent_test_cases_agent_created", "agent_id", "created_at"),
        Index("ix_agent_test_cases_client", "client_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # La conversacion de origen: si se borra la llamada, el caso conserva su copia.
    source_conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    source_message_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_agent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), default="voice", server_default="voice")
    # {messages, user_message, progress, channel, handoff}: la copia de la conversacion.
    snapshot: Mapped[dict] = mapped_column(JSONDoc)
    # [{name, arguments, result}]: lo que recibio el modelo en el turno (la herramienta se simula).
    tool_results: Mapped[list] = mapped_column(JSONDoc, default=list)
    checks: Mapped[list] = mapped_column(JSONDoc, default=list)
    # Un caso que se sabe que falla (se muestra aparte y no se espera que pase).
    known_failure: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"),
                                                   nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentTestRun(Base):
    """Una corrida de casos: las variantes (publicada y cambios sin guardar), el progreso y las respuestas."""
    __tablename__ = "agent_test_runs"
    __table_args__ = (
        Index("ix_agent_test_runs_agent_created", "agent_id", "created_at"),
        Index("ix_agent_test_runs_status", "status"),
        # Dos clics no arman dos corridas: una sola queued/running por agente.
        Index("uq_agent_test_runs_active", "agent_id", unique=True,
              postgresql_where=text("status IN ('queued', 'running')"),
              sqlite_where=text("status IN ('queued', 'running')")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", server_default="queued")
    repetitions: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    # [{key, version, definition?}]: "publicada" con la version guardada y "borrador" con la definicion enviada.
    variants: Mapped[list] = mapped_column(JSONDoc, default=list)
    # Copia de nombre y chequeos de cada caso corrido (el caso puede cambiar despues).
    cases: Mapped[list] = mapped_column(JSONDoc, default=list)
    results: Mapped[list | None] = mapped_column(JSONDoc, nullable=True)
    # [{case_id, variants: [{key, passed, total}]}]: el `pasa X/N` sin las respuestas, para la lista y el historial.
    summary: Mapped[list | None] = mapped_column(JSONDoc, nullable=True)
    done: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tool_revisions: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"),
                                                   nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Pedido de cancelación de una corrida en curso: la cola deja de mandar turnos y la termina como `cancelled`.
    cancel_requested_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
