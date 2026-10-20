"""Link publico para llamar a un agente desde el navegador (docs/LINK_LLAMADA_PLAN.md):
https://<CALL_LINK_HOST>/<token>. Como un numero de telefono: apunta a un agente del cliente,
se pausa o se revoca, y las llamadas consumen minutos entrantes del tier (CallMode.web)."""
import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ._common import IdMixin, TimestampMixin


class CallLink(IdMixin, TimestampMixin, Base):
    __tablename__ = "call_links"
    __table_args__ = (
        # Un link activo por agente: regenerar es revocar el actual y crear otro.
        Index("uq_call_links_agent_active", "agent_id", unique=True,
              postgresql_where=text("revoked_at IS NULL"), sqlite_where=text("revoked_at IS NULL")),
        CheckConstraint("max_call_seconds > 0", name="ck_call_links_seconds"),
        CheckConstraint("max_concurrent IS NULL OR max_concurrent >= 0", name="ck_call_links_concurrent"),
        CheckConstraint("daily_minutes IS NULL OR daily_minutes >= 0", name="ck_call_links_daily"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    # Lo que va en la URL: aleatorio (secrets.token_urlsafe), no se reutiliza al revocar.
    token: Mapped[str] = mapped_column(String(32), unique=True)
    # Lo que ve quien llama. Vacio: el nombre del agente y el del cliente.
    display_name: Mapped[str] = mapped_column(String(64), default="", server_default="")
    company_name: Mapped[str] = mapped_column(String(128), default="", server_default="")
    subtitle: Mapped[str] = mapped_column(String(120), default="", server_default="")
    # Imagen redonda de arriba: archivo en CALL_LINK_IMAGES_DIR. NULL: la inicial de la empresa.
    image: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_call_seconds: Mapped[int] = mapped_column(Integer, default=300, server_default="300")
    # Topes propios del link, ademas de los del tier. NULL: sin tope.
    max_concurrent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Pausado: la pagina dice "no disponible" y el link se conserva.
    paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Revocado: 404 para siempre.
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
