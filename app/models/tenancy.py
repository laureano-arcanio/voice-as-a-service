"""Clientes (tenants), sus tiers, numeros, usuarios y API keys."""
import datetime
import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, utcnow
from ._common import IdMixin, TimestampMixin


class Tier(IdMixin, TimestampMixin, Base):
    """Plan con limites mensuales. Un limite en NULL es ilimitado."""
    __tablename__ = "tiers"
    __table_args__ = (
        CheckConstraint("max_concurrent_calls IS NULL OR max_concurrent_calls >= 0", name="ck_tiers_concurrency"),
        CheckConstraint("inbound_minutes IS NULL OR inbound_minutes >= 0", name="ck_tiers_inbound"),
        CheckConstraint("outbound_minutes IS NULL OR outbound_minutes >= 0", name="ck_tiers_outbound"),
        CheckConstraint("max_phone_numbers IS NULL OR max_phone_numbers >= 0", name="ck_tiers_phone_numbers"),
    )
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    max_concurrent_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minutos por mes calendario (settings.billing_timezone).
    inbound_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outbound_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Numeros de telefono que puede tener asignados el cliente.
    max_phone_numbers: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Client(IdMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    # RESTRICT: un tier en uso no se borra.
    tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("tiers.id", ondelete="RESTRICT"), index=True)
    # Inactivo: no puede hacer ni recibir llamadas; sus datos quedan.
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tier: Mapped[Tier] = relationship(lazy="joined", innerjoin=True)


class PhoneNumber(IdMixin, TimestampMixin, Base):
    """Numero del inventario (los que provee Anura). Libre (sin cliente) o asignado a
    un cliente, hasta el tope de su tier. Las entrantes a este numero las atiende
    `agent`, un agente del cliente; las salientes pueden usarlo como caller ID."""
    __tablename__ = "phone_numbers"
    __table_args__ = (
        CheckConstraint("agent_id IS NULL OR client_id IS NOT NULL", name="ck_phone_numbers_agent_needs_client"),
    )
    # SET NULL: si se borra el cliente, el numero vuelve al inventario.
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    # E.164 (+5491155551234). Unico en todo el sistema: define a que cliente va la entrante.
    e164: Mapped[str] = mapped_column(String(16), unique=True)
    label: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(32), default="anura")
    assigned_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)


class Role(enum.StrEnum):
    admin = "admin"     # opera la plataforma: ve y administra todo
    client = "client"   # usuario de un cliente: ve lo suyo y hace llamadas


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("(role = 'admin' AND client_id IS NULL) OR (role = 'client' AND client_id IS NOT NULL)",
                        name="ck_users_role_client"),
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)  # en minusculas
    name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class ApiKey(IdMixin, Base):
    """Acceso por API de un cliente (sus sistemas disparan llamadas). Se guarda el
    SHA-256 de la clave; la clave se muestra una sola vez al crearla."""
    __tablename__ = "api_keys"
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    prefix: Mapped[str] = mapped_column(String(16))     # para reconocerla en la UI
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
