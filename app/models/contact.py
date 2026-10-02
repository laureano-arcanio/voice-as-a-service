"""Pedidos de contacto del formulario de la landing (POST /api/v1/demo/contact).

Se guardan antes de avisar por mail: si Resend falla, el pedido no se pierde.
"""
import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, utcnow
from ._common import IdMixin


class ContactRequest(IdMixin, Base):
    __tablename__ = "contact_requests"
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, index=True)
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str] = mapped_column(String(120), default="", server_default="")
    email: Mapped[str] = mapped_column(String(254), default="", server_default="")
    phone: Mapped[str] = mapped_column(String(40), default="", server_default="")
    message: Mapped[str] = mapped_column(Text, default="", server_default="")
    page: Mapped[str] = mapped_column(String(64), default="", server_default="")   # path de la landing
    ip: Mapped[str] = mapped_column(String(45), default="", server_default="")
    # sent, failed o disabled (sin RESEND_API_KEY o CONTACT_TO).
    email_status: Mapped[str] = mapped_column(String(16), default="disabled", server_default="disabled")
    email_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # id de Resend
    email_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
