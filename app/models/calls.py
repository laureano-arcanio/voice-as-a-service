"""Registro telefonico de cada conversacion: telefono, estado de la llamada,
duracion y latencia por turno. La conversacion en si (datos y mensajes) vive en
ConversationRow; esta tabla la complementa y es la base del consumo por tier.
"""
import datetime
import enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin


class CallStatus(enum.StrEnum):
    pendiente = "pendiente"
    sonando = "sonando"
    en_curso = "en_curso"
    finalizada = "finalizada"
    fallida = "fallida"
    rechazada = "rechazada"     # limite del tier (concurrencia o minutos) o cliente inactivo
    cancelada = "cancelada"     # la directa que el usuario corto antes de que atiendan (no es una falla)


ACTIVE_CALL_STATUSES = (CallStatus.pendiente, CallStatus.sonando, CallStatus.en_curso)


class CallMode(enum.StrEnum):
    saliente = "saliente"   # marca por SIP
    entrante = "entrante"   # llama el cliente final a un numero del cliente
    prueba = "prueba"       # navegador (LiveKit Meet)
    web = "web"             # navegador, por el link publico de un agente (call_links); consume minutos entrantes
    loadtest = "loadtest"   # scripts/loadtest y scripts/capacity
    directa = "directa"     # saliente de una persona del cliente, sin agente (docs/features/EQUIPO_TELEFONIA.md)
    celular = "celular"     # de prueba al celular verificado del usuario; no gasta minutos (docs/features/PRIMERA_VEZ.md)


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
    # Llamadas directas (docs/features/EQUIPO_TELEFONIA.md): el usuario que llamo o atendio (en el panel o en su
    # celular, por TeamMember.user_id), quien atiende una entrante (agent o team) y si se llamo a un contacto
    # dado de baja con confirmacion.
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    answered_by: Mapped[str | None] = mapped_column(String(8), nullable=True)
    opted_out_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
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


class UserPresence(Base):
    """Disponible en el panel para atender entrantes directas: el pulso (PUT /me/presence) de los ultimos
    PRESENCE_TTL_SECONDS (services/direct_calls.py). Sin fila, no disponible."""
    __tablename__ = "user_presence"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    last_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class CallRing(IdMixin, Base):
    """El timbre de una entrante directa en el panel de un usuario: ringing, answered (la tomo), declined o
    cancelled (la tomo otro, se corto o paso al celular). Uno por usuario y llamada."""
    __tablename__ = "call_rings"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_call_rings_conversation_user"),
        Index("ix_call_rings_user_status", "user_id", "status"),
    )
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), default="ringing", server_default="ringing")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
