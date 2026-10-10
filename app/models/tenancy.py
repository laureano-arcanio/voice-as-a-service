"""Clientes (tenants), sus tiers, numeros, usuarios y API keys."""
import datetime
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
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
        CheckConstraint("max_calls_per_hour IS NULL OR max_calls_per_hour >= 0", name="ck_tiers_calls_hour"),
        CheckConstraint("max_calls_per_day IS NULL OR max_calls_per_day >= 0", name="ck_tiers_calls_day"),
        CheckConstraint("max_calls_per_month IS NULL OR max_calls_per_month >= 0", name="ck_tiers_calls_month"),
        CheckConstraint("api_llm_input_tokens IS NULL OR api_llm_input_tokens >= 0", name="ck_tiers_api_llm_in"),
        CheckConstraint("api_llm_output_tokens IS NULL OR api_llm_output_tokens >= 0", name="ck_tiers_api_llm_out"),
        CheckConstraint("api_tts_minutes IS NULL OR api_tts_minutes >= 0", name="ck_tiers_api_tts"),
        CheckConstraint("api_stt_minutes IS NULL OR api_stt_minutes >= 0", name="ck_tiers_api_stt"),
        CheckConstraint("api_rate_limit IS NULL OR api_rate_limit >= 0", name="ck_tiers_api_rate"),
        CheckConstraint("price_ars IS NULL OR price_ars >= 0", name="ck_tiers_price"),
    )
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    max_concurrent_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minutos por mes calendario (settings.billing_timezone).
    inbound_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outbound_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Numeros de telefono que puede tener asignados el cliente.
    max_phone_numbers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Llamadas (entrantes y salientes) que puede empezar por hora, dia y mes calendario
    # (settings.billing_timezone). Ver services/quota.py.
    max_calls_per_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_calls_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_calls_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # API de inferencia (/api/v1/inference: LLM, STT y TTS con una API key). Solo cuenta ese uso,
    # no los agentes integrados (llamadas, WhatsApp). Mensuales como los minutos; NULL = ilimitado
    # y 0 = no incluido. Ver services/api_usage.py.
    api_llm_input_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    api_llm_output_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    api_tts_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)   # audio sintetizado
    api_stt_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)   # audio transcripto
    # Pedidos por minuto a la API de inferencia, sumando las tres y todas las keys del cliente.
    api_rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Autoservicio (docs/SUSCRIPCIONES_PLAN.md): precio mensual en pesos, lo que se cobra (NULL = no
    # se vende por el dashboard; 0 = gratis). `public`: se ofrece en el registro y en /plan. El tier
    # publico con precio 0 es el del registro.
    price_ars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Client(IdMixin, TimestampMixin, Base):
    __tablename__ = "clients"
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    # RESTRICT: un tier en uso no se borra.
    tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("tiers.id", ondelete="RESTRICT"), index=True)
    # Inactivo: no puede hacer ni recibir llamadas; sus datos quedan.
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # admin (lo creo un admin) o signup (registro desde la landing).
    created_via: Mapped[str] = mapped_column(String(16), default="admin", server_default="admin")
    # Datos para la factura (la emite Atentina a mano). tax_condition: ri, monotributo, exento o cf.
    legal_name: Mapped[str] = mapped_column(String(128), default="", server_default="")
    tax_id: Mapped[str] = mapped_column(String(13), default="", server_default="")
    tax_condition: Mapped[str] = mapped_column(String(16), default="", server_default="")

    tier: Mapped[Tier] = relationship(lazy="joined", innerjoin=True)


class ClientLimitAdjustment(IdMixin, TimestampMixin, Base):
    """Ajuste de un limite del tier para un cliente en particular (mas minutos, una linea mas,
    un tope propio). `add` suma al valor del tier; `set` lo reemplaza (value NULL = ilimitado).
    Vigente entre `starts_on` y `ends_on` (inclusive, en billing_timezone); sin fechas, permanente.
    Se resuelve en services/limits.py."""
    __tablename__ = "client_limit_adjustments"
    __table_args__ = (
        CheckConstraint("mode IN ('add', 'set')", name="ck_limit_adj_mode"),
        CheckConstraint("value IS NULL OR value >= 0", name="ck_limit_adj_value"),
        CheckConstraint("mode = 'set' OR value IS NOT NULL", name="ck_limit_adj_add_value"),
        CheckConstraint("starts_on IS NULL OR ends_on IS NULL OR starts_on <= ends_on", name="ck_limit_adj_dates"),
        Index("ix_limit_adj_client_field", "client_id", "field"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"))
    # Un campo numerico de Tier (services/limits.LIMIT_FIELDS).
    field: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(8))
    value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    starts_on: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


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
    # Suspendido: el cliente bajo a un plan con menos numeros por falta de pago. Sigue asignado
    # pero no atiende; a los BILLING_NUMBER_HOLD_DAYS vuelve al inventario (app/billing/service.py).
    suspended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


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
    # Que puede hacer, separado por comas: `calls` (API de llamadas, agentes y reportes) y/o
    # `llm`, `stt`, `tts` (API de inferencia). Una key de un tipo no sirve para el otro.
    scopes: Mapped[str] = mapped_column(String(64), default="calls", server_default="calls")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class ApiUsageDaily(Base):
    """Consumo de la API de inferencia por cliente, key y dia (en BILLING_TIMEZONE): la base del
    control de limites del tier. Un dia por fila (no un registro por pedido): el consumo del mes
    suma a lo sumo ~31 filas por key."""
    __tablename__ = "api_usage_daily"
    __table_args__ = (Index("ix_api_usage_daily_client_day", "client_id", "day"),)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    api_key_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_keys.id", ondelete="CASCADE"),
                                            primary_key=True)
    day: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    llm_requests: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    llm_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    llm_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    stt_requests: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    stt_seconds: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    tts_requests: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    tts_seconds: Mapped[float] = mapped_column(Float, default=0, server_default="0")
