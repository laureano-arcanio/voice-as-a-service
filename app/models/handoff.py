"""Derivacion a personas del cliente (docs/features/EQUIPO_TELEFONIA.md) y registro de eventos.

- team_members: el equipo del cliente (telefono para transferir llamadas, WhatsApp para el puente de la
  bandeja, usuario para el softphone web). Las mismas personas sirven para llamadas y WhatsApp.
- handoff_areas: un area ("Ventas", "Posventa") con sus miembros en orden, horario, timbre, codigo de
  vuelta a la IA, que hacer si la persona corta y los mensajes (services/handoff.py tiene los defaults).
- handoff_legs: cada llamada a una persona en una derivacion (fase 2): resultado, tiempos y segundos que se
  descuentan como salientes; tambien cuenta para el tope de canales de Anura.
- events: la linea de tiempo de una llamada o un hilo (timbre, espera, cada intento de derivacion, quien
  atendio); la leen el panel del cliente y el webhook.
"""
import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin


class TeamMember(IdMixin, TimestampMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("client_id", "whatsapp", name="uq_team_members_client_whatsapp"),)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)      # E.164 argentino (services/phones.py)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)   # E.164; unico por cliente (puente)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)   # softphone web (fase 6)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class HandoffArea(IdMixin, TimestampMixin, Base):
    __tablename__ = "handoff_areas"
    __table_args__ = (UniqueConstraint("client_id", "name", name="uq_handoff_areas_client_name"),)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    # Que atiende, en lenguaje natural: lo lee el LLM para elegir el area.
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    strategy: Mapped[str] = mapped_column(String(16), default="sequential", server_default="sequential")
    # Timbre por miembro: el buzon de Claro atiende a los ~33 s (spike, plan 11.1); con 20 se corta antes.
    ring_seconds: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    # Horario: {"tz": ..., "week": {"mon": [["09:00", "18:00"]], ...}, "closed": ["2026-12-25"]}; NULL = siempre.
    schedule: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    # Fuera de horario o si nadie atiende: take_message (el agente toma el mensaje y deja la ficha).
    fallback: Mapped[str] = mapped_column(String(16), default="take_message", server_default="take_message")
    # La persona corta estando conectada: resume (el agente vuelve) o end (se despide y corta).
    on_person_hangup: Mapped[str] = mapped_column(String(8), default="resume", server_default="resume")
    # Tecla de la persona para devolverle la llamada a la IA. Nunca con *: Anura toma * + digito (plan 11.2).
    return_digits: Mapped[str] = mapped_column(String(4), default="2", server_default="2")
    # Minutos sin respuesta del vendedor en el puente de WhatsApp antes de reasignar (fase 3).
    wa_reply_minutes: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    # Textos que cambian los defaults (services/handoff.DEFAULT_MESSAGES), por clave.
    messages: Mapped[dict] = mapped_column(JSONDoc, default=dict, server_default="{}")
    # Round robin: el ultimo miembro al que se le paso (se rota a partir del siguiente).
    last_member_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True)


class HandoffAreaMember(Base):
    __tablename__ = "handoff_area_members"
    area_id: Mapped[str] = mapped_column(String(36), ForeignKey("handoff_areas.id", ondelete="CASCADE"),
                                         primary_key=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_members.id", ondelete="CASCADE"),
                                           primary_key=True, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class PhoneNumberMember(Base):
    """Las personas que atienden un numero con answer_mode=team, en orden (docs/features/EQUIPO_TELEFONIA.md)."""
    __tablename__ = "phone_number_members"
    phone_number_id: Mapped[str] = mapped_column(String(36), ForeignKey("phone_numbers.id", ondelete="CASCADE"),
                                                 primary_key=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_members.id", ondelete="CASCADE"),
                                           primary_key=True, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class HandoffLeg(IdMixin, Base):
    """Un intento de derivacion: la llamada a una persona del area desde una llamada en curso."""
    __tablename__ = "handoff_legs"
    __table_args__ = (Index("ix_handoff_legs_client_created", "client_id", "created_at"),)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    area_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("handoff_areas.id", ondelete="SET NULL"), nullable=True)
    team_member_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True)
    phone: Mapped[str] = mapped_column(String(20))
    # dialing, connected, no_answer, busy, machine, not_confirmed, failed (voice/handoff.py)
    result: Mapped[str] = mapped_column(String(16), default="dialing", server_default="dialing")
    sip_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)   # empieza a sonar
    answered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    connected_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Salientes que se descuentan: desde que atiende, solo si se conecto (plan 4.6). Un contestador que se
    # corta en la deteccion lo cobra Anura, pero no se le descuenta al cliente.
    billed_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_client_at", "client_id", "at"),
        Index("ix_events_conversation_at", "conversation_id", "at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"))
    at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    type: Mapped[str] = mapped_column(String(48))            # services/events.TYPES
    actor: Mapped[str] = mapped_column(String(16), default="system", server_default="system")
    # La llamada (call_logs) o el hilo de WhatsApp (wa_threads) tienen de clave la conversacion.
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    area_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("handoff_areas.id", ondelete="SET NULL"), nullable=True)
    team_member_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True)
    data: Mapped[dict] = mapped_column(JSONDoc, default=dict, server_default="{}")
