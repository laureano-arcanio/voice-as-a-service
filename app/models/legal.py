"""Aceptacion de las condiciones y pedidos de arrepentimiento o baja (docs/features/LEGAL.md).

Las dos tablas son prueba: no tienen claves foraneas (sobreviven a que se borre el cliente o el usuario) y guardan
el email y el nombre de la empresa de ese momento. Las aceptaciones solo se agregan, nunca se cambian.
"""
import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, utcnow
from ._common import IdMixin


class LegalAcceptance(IdMixin, Base):
    __tablename__ = "legal_acceptances"
    __table_args__ = (Index("ix_legal_acceptances_user_doc", "user_id", "document"),)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    user_id: Mapped[str] = mapped_column(String(36))
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(254))
    client_name: Mapped[str] = mapped_column(String(120), default="", server_default="")
    document: Mapped[str] = mapped_column(String(16))     # terms | privacy (app/legal.DOCS)
    version: Mapped[str] = mapped_column(String(16))      # AAAA-MM-DD
    sha256: Mapped[str] = mapped_column(String(64))       # del archivo de esa version
    statement: Mapped[str] = mapped_column(Text)          # el texto de la casilla, tal cual
    channel: Mapped[str] = mapped_column(String(16))      # signup | panel
    ip: Mapped[str] = mapped_column(String(45), default="", server_default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="", server_default="")


class ConsumerRequest(IdMixin, Base):
    """Boton de arrepentimiento o de baja de la landing (Disp. 954/2025): el codigo se manda al email del que
    pide; el admin lo resuelve y lo marca."""
    __tablename__ = "consumer_requests"
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(16))          # revocation (arrepentimiento) | cancellation (baja)
    code: Mapped[str] = mapped_column(String(16), unique=True)   # ARR-XXXXXXXX | BAJ-XXXXXXXX
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    company: Mapped[str] = mapped_column(String(120), default="", server_default="")
    message: Mapped[str] = mapped_column(Text, default="", server_default="")
    ip: Mapped[str] = mapped_column(String(45), default="", server_default="")
    # Cliente con un usuario de ese email al momento del pedido (para encontrarlo rapido; puede no haber).
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open")   # open | done | rejected
    resolution: Mapped[str] = mapped_column(Text, default="", server_default="")
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Mail con el codigo al que pidio: sent, failed o disabled (como contact_requests).
    email_status: Mapped[str] = mapped_column(String(16), default="disabled", server_default="disabled")
