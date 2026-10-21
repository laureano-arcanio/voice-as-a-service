"""Registro telefonico de cada conversacion: telefono, estado de la llamada,
duracion y latencia por turno. La conversacion en si (datos y mensajes) vive en
ConversationRow; esta tabla la complementa y es la base del consumo por tier.
"""
import datetime
import enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow


class CallStatus(enum.StrEnum):
    pendiente = "pendiente"
    sonando = "sonando"
    en_curso = "en_curso"
    finalizada = "finalizada"
    fallida = "fallida"
    rechazada = "rechazada"     # limite del tier (concurrencia o minutos) o cliente inactivo


ACTIVE_CALL_STATUSES = (CallStatus.pendiente, CallStatus.sonando, CallStatus.en_curso)


class CallMode(enum.StrEnum):
    saliente = "saliente"   # marca por SIP
    entrante = "entrante"   # llama el cliente final a un numero del cliente
    prueba = "prueba"       # navegador (LiveKit Meet)
    web = "web"             # navegador, por el link publico de un agente (call_links); consume minutos entrantes
    loadtest = "loadtest"   # scripts/loadtest y scripts/capacity


class CallRow(Base):
    __tablename__ = "call_logs"
    __table_args__ = (
        # Consumo del mes y llamadas activas por cliente (services/quota.py).
        Index("ix_call_logs_client_started", "client_id", "started_at"),
        Index("ix_call_logs_client_status", "client_id", "status"),
    )
    # Una llamada por conversacion; se va con ella.
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True)
    mode: Mapped[str] = mapped_column(String(16))
    # Del otro lado: a quien se llamo (saliente) o quien llamo (entrante).
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Numero del cliente: el marcado (entrante) o el caller ID (saliente).
    phone_number_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True)
    # Si es un intento de una campaña de voz: el contacto de la campaña (app/models/campaigns.py).
    campaign_contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("campaign_contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    # Si entro por el link publico de un agente (app/models/call_links.py).
    call_link_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("call_links.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default=CallStatus.pendiente)
    # Codigo SIP con el que termino el intento saliente (486 ocupado, 408 no atiende...), si lo hubo.
    sip_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ended_reason: Mapped[str] = mapped_column(String(128), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    latency: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    # Resumen por email al cliente (app/mail/call_summary.py): pending (lo deja el worker al terminar,
    # si el agente lo tiene prendido), sent, disabled (sin RESEND_API_KEY), skipped (apagado en el
    # cliente o sin destinos) o failed. NULL: no corresponde.
    summary_email: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    summary_email_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Room de LiveKit (la deja el worker): para cortar la llamada desde la API (services/calls.hang_up).
    room: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class BlockedNumber(Base):
    """Telefono que el cliente no atiende: sus entrantes (por linea o llamada de WhatsApp) se cortan
    sin atender y quedan como rechazadas (blocked_number). No toca las salientes (eso son las bajas)."""
    __tablename__ = "blocked_numbers"
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), primary_key=True)     # E.164, normalizado (services/phones.py)
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
