"""Agentes de voz de cada cliente. La definicion es un workflow en JSON
(app.conversation.models.Workflow) y se versiona: cada cambio crea una version
nueva inmutable, y cada conversacion guarda con que version corrio."""
import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin


class Agent(IdMixin, TimestampMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("client_id", "slug", name="uq_agents_client_slug"),)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    # Identificador legible, unico por cliente; es el `id` de la definicion (va en el prompt).
    slug: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    # Version vigente y su definicion (copia de agent_versions, para no hacer join).
    version: Mapped[int] = mapped_column(Integer, default=1)
    definition: Mapped[dict] = mapped_column(JSONDoc)
    # Archivado: no se puede usar en llamadas nuevas; queda para el historial.
    archived_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    definition: Mapped[dict] = mapped_column(JSONDoc)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
