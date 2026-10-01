"""WhatsApp (Cloud API de Meta, docs/WHATSAPP_PLAN.md): numeros conectados, el hilo
de cada conversacion (lo que call_logs es a la telefonia) y los mensajes por wamid
(dedupe y estados de entrega). El texto no se guarda aca: esta en conversations.messages.
"""
import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, false, true
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin


class WaAccount(IdMixin, TimestampMixin, Base):
    """Un numero de WhatsApp conectado: lo atiende `agent`, un agente del cliente."""
    __tablename__ = "wa_accounts"
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    phone_number_id: Mapped[str] = mapped_column(String(32), unique=True)   # ID de Meta
    waba_id: Mapped[str] = mapped_column(String(32))
    display_phone_number: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128), default="", server_default="")
    # NULL: se usa settings.wa_access_token (system user de nuestro portafolio).
    # TODO fase 2: cifrar con WA_TOKEN_KEY (tokens de Embedded Signup de los clientes).
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class WaThread(Base):
    """Una fila por conversacion de WhatsApp: con quien y por que numero."""
    __tablename__ = "wa_threads"
    __table_args__ = (
        Index("ix_wa_threads_account_waid_created", "account_id", "wa_id", "created_at"),
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("wa_accounts.id", ondelete="RESTRICT"))
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True)
    wa_id: Mapped[str] = mapped_column(String(32))          # tal cual llega (549351...)
    contact_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_user_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    # Fase 3: derivada a humano. En la fase 1 solo se respeta (no se responde).
    paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class WaMessage(IdMixin, Base):
    __tablename__ = "wa_messages"
    __table_args__ = (
        Index("ix_wa_messages_account_created", "account_id", "created_at"),
    )
    # NULL: un envio que fallo antes de que Meta le diera un wamid.
    wamid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(3))        # in | out
    wa_id: Mapped[str] = mapped_column(String(32))
    # text, audio, image, document, sticker, video, location, template, other
    type: Mapped[str] = mapped_column(String(16))
    # in: received, answered, ignored, error. out: sent, delivered, read, failed.
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)   # {code, subcode, message}
    meta_ts: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
