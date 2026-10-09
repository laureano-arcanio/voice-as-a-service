"""WhatsApp (Cloud API de Meta, docs/WHATSAPP_PLAN.md): numeros conectados, el hilo
de cada conversacion (lo que call_logs es a la telefonia) y los mensajes por wamid
(dedupe y estados de entrega). La conversacion esta en conversations.messages; el
entrante guarda ademas su cuerpo (body) hasta procesarlo, para no perderlo si el proceso cae.
"""
import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin


class WaAccount(IdMixin, TimestampMixin, Base):
    """Un numero de WhatsApp conectado: lo atiende `agent`, un agente del cliente.

    Alta manual (admin, numeros de nuestro portafolio) o por Embedded Signup (el cliente
    conecta el suyo, app/whatsapp/signup.py). Secretos cifrados (app/whatsapp/crypto.py)."""
    __tablename__ = "wa_accounts"
    __table_args__ = (
        CheckConstraint("status IN ('connected', 'pending', 'disconnected')", name="ck_wa_accounts_status"),
        Index("ix_wa_accounts_waba_id", "waba_id"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="RESTRICT"), index=True)
    phone_number_id: Mapped[str] = mapped_column(String(32), unique=True)   # ID de Meta
    waba_id: Mapped[str] = mapped_column(String(32))
    display_phone_number: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128), default="", server_default="")
    # NULL: se usa settings.wa_access_token (system user de nuestro portafolio).
    # Si no, "fernet:<token>" (business token del cliente); sin prefijo, legado en claro.
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    # connected: atiende. pending: falta suscribir o registrar (reintento desde la UI).
    # disconnected: Meta rechazo el token (190) o el cliente nos quito el acceso; no se usa mas.
    status: Mapped[str] = mapped_column(String(16), default="connected", server_default="connected")
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_changed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    quality_rating: Mapped[str | None] = mapped_column(String(16), nullable=True)   # GREEN, YELLOW, RED...
    messaging_limit: Mapped[str | None] = mapped_column(String(32), nullable=True)  # current_limit de Meta
    business_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")  # manual, embedded_signup, coexistence
    pin_enc: Mapped[str | None] = mapped_column(Text, nullable=True)   # PIN de dos pasos, cifrado
    connected_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL", name="fk_wa_accounts_connected_by_users"),
        nullable=True)


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
    # Cerrada desde el dashboard: el proximo mensaje del contacto empieza otra conversacion.
    closed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class WaMessage(IdMixin, Base):
    __tablename__ = "wa_messages"
    __table_args__ = (
        Index("ix_wa_messages_account_created", "account_id", "created_at"),
        # Barrido al arrancar y reintentos: entrantes received/processing por antiguedad.
        Index("ix_wa_messages_direction_status_created", "direction", "status", "created_at"),
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
    # in (durable: se guarda con el cuerpo antes del 200 a Meta):
    #   received: guardado, sin procesar (o devuelto a la cola para reintentar).
    #   processing: tomado por un proceso (claimed_at); si queda colgado, se reintenta.
    #   answered: respondido. ignored: no corresponde responder (pausado, baja, duplicado...).
    #   error: fallo tras WA_MAX_ATTEMPTS intentos (o no se puede reprocesar).
    # out: sent, delivered, read, failed.
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)   # {code, subcode, message}
    meta_ts: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # in: lo minimo para reprocesar el mensaje de Meta (tipo, texto, media id, contacto...).
    body: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    claimed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Se marca antes de mandar la respuesta a Meta: un processing con processed_at es un envio
    # incierto (cayo el proceso mandando) y la recuperacion lo pasa a error sin reenviar.
    # El cuerpo se borra con sql null() (answered/ignored; JSONDoc no guarda None como NULL).
    processed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class WaCampaign(IdMixin, TimestampMixin, Base):
    """Campaña saliente: una plantilla aprobada a una lista de contactos, por un numero
    conectado, con ritmo y horario (app/whatsapp/campaigns.py). La respuesta de un contacto
    abre la conversacion con el texto de la plantilla como apertura."""
    __tablename__ = "wa_campaigns"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'running', 'paused', 'done', 'cancelled')", name="ck_wa_campaigns_status"),
        CheckConstraint("rate_per_minute > 0", name="ck_wa_campaigns_rate"),
        CheckConstraint("window_start >= 0 AND window_start <= 23 AND window_end >= 1 AND window_end <= 24 "
                        "AND window_start < window_end", name="ck_wa_campaigns_window"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("wa_accounts.id", ondelete="RESTRICT"), index=True)
    # NULL: responde el agente del numero.
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    # Copia de la plantilla de Meta al crearla: el cuerpo es la apertura de la conversacion.
    template_name: Mapped[str] = mapped_column(String(512))
    template_language: Mapped[str] = mapped_column(String(16))
    template_category: Mapped[str] = mapped_column(String(32), default="", server_default="")
    template_body: Mapped[str] = mapped_column(Text, default="", server_default="")
    template_params: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    # Motivo de la ultima pausa automatica (token rechazado, plantilla pausada por Meta...).
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rate_per_minute: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    # Horario de envio, en horas locales de settings.billing_timezone: [window_start, window_end).
    window_start: Mapped[int] = mapped_column(Integer, default=9, server_default="9")
    window_end: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL", name="fk_wa_campaigns_created_by_users"),
        nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class WaCampaignRecipient(IdMixin, Base):
    """Un contacto de una campaña. Entregado y leido salen de wa_messages (por wamid)."""
    __tablename__ = "wa_campaign_recipients"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sending', 'sent', 'failed', 'skipped')",
                        name="ck_wa_campaign_recipients_status"),
        UniqueConstraint("campaign_id", "wa_id", name="uq_wa_campaign_recipients_campaign_waid"),
        Index("ix_wa_campaign_recipients_campaign_status", "campaign_id", "status"),
        Index("ix_wa_campaign_recipients_waid_sent", "wa_id", "sent_at"),
    )
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("wa_campaigns.id", ondelete="CASCADE"))
    wa_id: Mapped[str] = mapped_column(String(32))      # normalizado como lo manda Meta (549351...)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    params: Mapped[list] = mapped_column(JSONDoc)       # valores de {{1}}..{{n}}
    # pending, sending (en vuelo), sent (Meta lo acepto), failed, skipped (baja o cancelada).
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    error: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)   # {code, subcode, message}
    wamid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # La conversacion que abrio su respuesta.
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    replied_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Cuando un sender lo paso a sending (reclamo atomico); uno colgado se puede reclamar de nuevo.
    claimed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class WaOptout(Base):
    """Contacto que pidio no recibir mas mensajes de un cliente: ninguna campaña le escribe."""
    __tablename__ = "wa_optouts"
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    wa_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(16))     # keyword (lo escribio), manual (UI o API)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
