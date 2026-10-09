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
        CheckConstraint("max_call_duration_seconds IS NULL OR max_call_duration_seconds > 0",
                        name="ck_tiers_max_call_duration"),
        CheckConstraint("retention_days IS NULL OR retention_days > 0", name="ck_tiers_retention"),
    )
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    max_concurrent_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minutos por mes calendario (settings.billing_timezone).
    inbound_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outbound_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Numeros de telefono que puede tener asignados el cliente.
    max_phone_numbers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Tope duro de cada llamada, en todas las modalidades (tambien sin limites de minutos).
    # NULL: CALL_MAX_DURATION_SECONDS. Ver effective_max_call_seconds.
    max_call_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Dias que se guardan conversaciones y grabaciones. NULL: sin borrado (salvo el del cliente).
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Client(IdMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint("retention_days IS NULL OR retention_days > 0", name="ck_clients_retention"),
    )
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    # RESTRICT: un tier en uso no se borra.
    tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("tiers.id", ondelete="RESTRICT"), index=True)
    # Inactivo: solo lectura. Entra y ve o exporta su historial; no consume (llamadas, texto,
    # WhatsApp, campañas, previews de voz) ni crea API keys. Sus datos quedan.
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Pisa el retention_days del tier (NULL: el del tier). Ver effective_retention_days.
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tier: Mapped[Tier] = relationship(lazy="joined", innerjoin=True)


class PhoneNumber(IdMixin, TimestampMixin, Base):
    """Numero del inventario (los que provee Anura). Libre (sin cliente) o asignado a
    un cliente, hasta el tope de su tier. Las entrantes a este numero las atiende
    `agent`, un agente del cliente; las salientes pueden usarlo como caller ID."""
    __tablename__ = "phone_numbers"
    # El agente es del mismo cliente que el numero (H01): en PostgreSQL lo garantiza la FK
    # compuesta fk_phone_numbers_agent_client (agent_id, client_id) -> agents (id, client_id)
    # ON DELETE SET NULL (agent_id), de la migracion 0009. No se declara aca: en SQLite (tests)
    # create_all no sabe poner en NULL una sola columna y borraria tambien client_id.
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
    # Va en el token (claim sv). Logout, cambio de clave o desactivacion lo suben: invalida
    # todas las sesiones abiertas del usuario.
    session_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


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


def effective_max_call_seconds(client: Client | None) -> int:
    """Tope duro de una llamada del cliente: el de su tier o CALL_MAX_DURATION_SECONDS, y
    nunca mas que CALL_DURATION_CEILING_SECONDS (el corte de SIP y Asterisk)."""
    from ..config import settings

    tier_max = client.tier.max_call_duration_seconds if client is not None else None
    seconds = tier_max or settings.call_max_duration_seconds
    return min(seconds, settings.call_duration_ceiling_seconds)


def effective_retention_days(client: Client) -> int | None:
    """Dias de retencion: los del cliente, si no los del tier; None = sin borrado."""
    if client.retention_days is not None:
        return client.retention_days
    return client.tier.retention_days
