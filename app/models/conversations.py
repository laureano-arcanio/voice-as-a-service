import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow


class ConversationRow(Base):
    """Estado del motor conversacional: datos extraidos, mensajes y progreso."""
    __tablename__ = "conversations"
    __table_args__ = (
        # El dashboard lista de la mas nueva a la mas vieja y filtra por fecha y cliente.
        Index("ix_conversations_created_at", "created_at"),
        Index("ix_conversations_client_created", "client_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # RESTRICT: un cliente o agente con conversaciones no se borra (se desactiva o archiva).
    # Sin cliente: conversaciones de plantillas (eval, tests) o anteriores a los clientes.
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True, index=True)
    agent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Workflow YAML con que corrio una conversacion anterior a los agentes en la base;
    # `python -m app.cli seed` la asocia al agente de igual slug del cliente interno.
    legacy_workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # voice | whatsapp. Se fija al crearla y no cambia (cambia las reglas del prompt).
    channel: Mapped[str] = mapped_column(String(16), default="voice", server_default="voice")
    status: Mapped[str] = mapped_column(String(16))
    fields: Mapped[dict] = mapped_column(JSONDoc)
    messages: Mapped[list] = mapped_column(JSONDoc)
    progress: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    # Para los reportes (docs/REPORTES_PLAN.md), sin cargar la definicion del agente: el resultado
    # (Outcome.id, el mismo de progress.outcome) y si cumple el objetivo, al completarse; la conversion
    # (complete: todos los datos requeridos; partial: alguno; empty: ninguno), al guardar cada turno.
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    conversion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Tokens del LLM sumados de todos los turnos (el usage de cada respuesta; 0 si el proveedor no lo da).
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
