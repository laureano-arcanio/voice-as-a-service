"""Registro telefonico de cada conversacion: telefono, estado de la llamada,
duracion y latencia por turno. La conversacion en si (datos y mensajes) vive en
ConversationRow; esta tabla la complementa y es la base del consumo por tier.
"""
import datetime
import enum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    loadtest = "loadtest"   # scripts/loadtest y scripts/capacity


class CallRow(Base):
    __tablename__ = "call_logs"
    __table_args__ = (
        # Consumo del mes y llamadas activas por cliente (services/quota.py).
        Index("ix_call_logs_client_started", "client_id", "started_at"),
        Index("ix_call_logs_client_status", "client_id", "status"),
        # Reintento de POST /calls con el mismo Idempotency-Key: devuelve la misma llamada.
        UniqueConstraint("client_id", "idempotency_key", name="uq_call_logs_client_idempotency"),
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
    status: Mapped[str] = mapped_column(String(16), default=CallStatus.pendiente)
    ended_reason: Mapped[str] = mapped_column(String(128), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    latency: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    # Header Idempotency-Key de POST /calls (NULL: sin el).
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # sha256 del pedido (agente, telefono, numero de origen, voz, loadtest): la misma clave
    # con otro pedido da 409 idempotency_key_reused.
    idempotency_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
