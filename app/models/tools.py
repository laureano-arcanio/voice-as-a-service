"""Herramientas del cliente (docs/TOOLS_PLAN.md): una llamada a una API (http) o una funcion en
JavaScript (code) que un agente puede usar en la conversacion. Son del cliente y los agentes las
referencian por slug desde `Workflow.tools`. Los secretos que usan son de cada agente (agent_secrets):
una herramienta usada por dos agentes toma en cada uno los valores de ese agente."""
import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin


class ClientTool(IdMixin, TimestampMixin, Base):
    __tablename__ = "tools"
    __table_args__ = (UniqueConstraint("client_id", "slug", name="uq_tools_client_slug"),)

    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    # Nombre con el que la ve el LLM y la referencia el agente (tools[].tool).
    slug: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(8))            # http | code
    # La definicion sin slug ni type (app/tools/schema.py).
    definition: Mapped[dict] = mapped_column(JSONDoc)
    # Sube con cada cambio; va en la traza de cada ejecucion.
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_test_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_test_detail: Mapped[str] = mapped_column(String(255), default="")


class AgentSecret(IdMixin, TimestampMixin, Base):
    """Un secreto de un agente: cifrado (Fernet con WA_TOKEN_KEY), no se devuelve nunca."""
    __tablename__ = "agent_secrets"
    __table_args__ = (UniqueConstraint("agent_id", "name", name="uq_agent_secrets_agent_name"),)

    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    value_enc: Mapped[str] = mapped_column(Text)
    last4: Mapped[str] = mapped_column(String(8), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class ToolVersion(IdMixin, Base):
    """Cada revision de una herramienta, para ver con que definicion corrio una llamada (la traza dice la revision)."""
    __tablename__ = "tool_versions"
    __table_args__ = (UniqueConstraint("tool_id", "revision", name="uq_tool_versions_tool_revision"),)

    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("tools.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(8))
    definition: Mapped[dict] = mapped_column(JSONDoc)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
