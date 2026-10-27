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
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, JSONDoc, utcnow
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
        CheckConstraint("max_campaigns_per_month IS NULL OR max_campaigns_per_month >= 0", name="ck_tiers_campaigns_month"),
        CheckConstraint("max_campaign_contacts IS NULL OR max_campaign_contacts >= 0", name="ck_tiers_campaign_contacts"),
        CheckConstraint("max_campaign_concurrency IS NULL OR max_campaign_concurrency >= 0",
                        name="ck_tiers_campaign_concurrency"),
        CheckConstraint("max_contacts IS NULL OR max_contacts >= 0", name="ck_tiers_contacts"),
        CheckConstraint("max_call_links IS NULL OR max_call_links >= 0", name="ck_tiers_call_links"),
        CheckConstraint("max_team_members IS NULL OR max_team_members >= 0", name="ck_tiers_team_members"),
        CheckConstraint("max_tools IS NULL OR max_tools >= 0", name="ck_tiers_tools"),
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
    # Campañas salientes y agenda de contactos (docs/LLAMADAS_SALIENTES_PLAN.md, 3.5). NULL = sin
    # limite y 0 = no incluido, como el resto. campaign_channels: los canales habilitados ([],
    # ["whatsapp"], ["voice"] o los dos).
    campaign_channels: Mapped[list] = mapped_column(JSONDoc, default=list, server_default=text("'[]'"))
    max_campaigns_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)   # iniciadas por mes calendario
    max_campaign_contacts: Mapped[int | None] = mapped_column(Integer, nullable=True)     # contactos por campaña
    max_campaign_concurrency: Mapped[int | None] = mapped_column(Integer, nullable=True)  # llamadas simultaneas de una de voz
    max_contacts: Mapped[int | None] = mapped_column(Integer, nullable=True)              # contactos activos en la agenda
    campaign_followup: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())   # seguimiento por WhatsApp
    # Links publicos para llamar a un agente desde el navegador (docs/LINK_LLAMADA_PLAN.md). NULL = sin
    # limite, 0 = no incluido.
    max_call_links: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Personas del equipo para derivar llamadas y WhatsApp (docs/DERIVACIONES_PLAN.md). NULL = sin
    # limite, 0 = no incluido.
    max_team_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # WhatsApp: cuentas, mensajes y llamadas (docs/FUNCIONES_POR_PLAN_PLAN.md).
    whatsapp: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    # Motor external: el agente del cliente detras de su endpoint (docs/AGENTE_EXTERNO_PLAN.md).
    external_agent: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Herramientas del cliente (docs/TOOLS_PLAN.md): cuantas puede tener (NULL = sin limite, 0 = no
    # incluido) y si pueden ser codigo (JavaScript en el sandbox).
    max_tools: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_tools: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Marca blanca del panel: logo y colores del cliente en vez de los de Atentina (docs/MARCA_BLANCA_PLAN.md).
    white_label: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Reportes completos (docs/REPORTES_PLAN.md): Resultados, Mensajes, Transferencias y Campañas. Sin esto,
    # solo Resumen y Llamadas.
    advanced_reports: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Tier de Atentina (nosotros): no se ofrece como plan ni cuenta en las estadisticas de la plataforma.
    internal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Llamadas directas: el equipo llama y atiende desde el panel sin el agente (docs/LLAMADAS_DIRECTAS_PLAN.md).
    # La saliente pide ademas outbound_calls.
    direct_calls: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
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
    # Resumen por email despues de cada llamada (app/mail/call_summary.py): lo prende cada agente
    # (Workflow.call_summary_email) y el cliente lo apaga para todos desde Mi cuenta.
    # call_emails_to: destinos; vacio = los usuarios activos del cliente.
    call_emails: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    call_emails_to: Mapped[list] = mapped_column(JSONDoc, default=list, server_default=text("'[]'"))
    # Aviso "Esta llamada está siendo grabada" en las llamadas directas (siempre se graban).
    direct_recording_notice: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    tier: Mapped[Tier] = relationship(lazy="joined", innerjoin=True)


class ClientBranding(Base):
    """Marca blanca del panel (docs/MARCA_BLANCA_PLAN.md): el logo y los tres colores con los que los usuarios
    del cliente ven el dashboard. 1:1 con el cliente (sin fila = sin marca); se aplica solo si `enabled` y el
    tier incluye `white_label`. Lo configura un admin (services/branding.py)."""
    __tablename__ = "client_branding"
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Archivo en storage/branding/<client_id>/ (BRANDING_DIR); NULL = el nombre del cliente en texto.
    logo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    logo_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # #rrggbb en minuscula. Primario: la accion (botones, links, seleccion); encabezado: fondo de la barra;
    # acento: segunda serie de los graficos.
    color_primary: Mapped[str] = mapped_column(String(7), default="#2456e6", server_default="#2456e6")
    color_header: Mapped[str] = mapped_column(String(7), default="#ffffff", server_default="#ffffff")
    color_accent: Mapped[str] = mapped_column(String(7), default="#b45309", server_default="#b45309")
    # "Con tecnologia de Atentina" al pie del menu.
    powered_by: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    updated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


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
    `agent`, un agente del cliente, o el equipo (answer_mode, docs/LLAMADAS_DIRECTAS_PLAN.md);
    las salientes pueden usarlo como caller ID."""
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
    # Quien atiende las entrantes: team (las personas del numero, phone_number_members) o agent. Los numeros
    # anteriores a la 0039 quedaron en agent.
    answer_mode: Mapped[str] = mapped_column(String(8), default="team", server_default="team")
    # Con team: donde suena primero (phone: el celular de cada uno en orden; panel: a los Disponibles a la vez)
    # y, si nadie atiende, en el otro. Timbre por persona y horario (el formato de handoff_areas.schedule).
    ring_first: Mapped[str] = mapped_column(String(8), default="phone", server_default="phone")
    ring_seconds: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    schedule: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    # Si nadie atiende o fuera de horario: agent (el agente del numero), voicemail (mensaje y graba) o hangup.
    team_fallback: Mapped[str] = mapped_column(String(16), default="voicemail", server_default="voicemail")
    team_fallback_message: Mapped[str] = mapped_column(Text, default="", server_default="")


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
    # Cuando cerro el pop-up de bienvenida del panel (solo usuarios de cliente); None = mostrarlo.
    welcomed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


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


class ApiRequest(IdMixin, Base):
    """Un pedido a la API de inferencia (para la lista de pedidos del admin y del cliente). Solo
    metadatos y consumo: ni prompts, ni audios, ni textos. Se anotan los que pasan el tope de
    pedidos por minuto (los rechazados antes, como rate_limited, no tienen tope y no se guardan).
    status: ok, cut (stream cortado: se cobra lo entregado), error (el motor o el pedido) o
    rejected (cupo del mes agotado o motor fuera del plan)."""
    __tablename__ = "api_requests"
    __table_args__ = (Index("ix_api_requests_client_created", "client_id", "created_at"),
                      Index("ix_api_requests_created", "created_at"))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"))
    api_key_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("api_keys.id", ondelete="SET NULL"),
                                                   nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    kind: Mapped[str] = mapped_column(String(8))           # llm, stt, tts
    stream: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    status: Mapped[str] = mapped_column(String(16))
    http_status: Mapped[int] = mapped_column(Integer, default=200, server_default="200")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ttfb_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)   # primer byte (stream y TTS)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    characters: Mapped[int | None] = mapped_column(Integer, nullable=True)   # texto del TTS
    voice: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
