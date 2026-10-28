"""Agenda de contactos del cliente y campañas salientes por WhatsApp o voz
(docs/LLAMADAS_SALIENTES_PLAN.md, seccion 3).

- `contacts`: la agenda; el telefono (E.164) es unico por cliente. No se borran: se archivan.
- `contact_optouts`: no contactar, por telefono y canal. Aparte de `contacts` a proposito: la
  baja es del telefono, sigue aunque el contacto se archive y se puede cargar sin ficha.
- `campaigns`: una tabla para los dos canales (los campos de cada uno, en NULL en el otro).
- `campaign_contacts`: un contacto en una campaña, con el estado y el resultado de su envio o llamada.
"""
import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, JSONDoc, utcnow
from ._common import IdMixin, TimestampMixin

CONTACT_SOURCES = ("manual", "csv", "api", "campaign", "inbound")
OPTOUT_CHANNELS = ("whatsapp", "voice", "all")
OPTOUT_SOURCES = ("keyword", "outcome", "manual")
CAMPAIGN_CHANNELS = ("whatsapp", "voice")
CAMPAIGN_STATUSES = ("draft", "scheduled", "running", "paused", "done", "cancelled")
CAMPAIGN_PURPOSES = ("comercial", "cobranza", "turnos", "aviso")
CAMPAIGN_CONTACT_STATUSES = ("pending", "in_progress", "retry", "done", "failed", "skipped")
# Seguimiento por WhatsApp de un contacto de voz: pending (a enviar), in_progress (en vuelo), sent, failed o skipped
# (fijo, baja de WhatsApp, archivado, sin variables o campaña cancelada).
FOLLOWUP_STATUSES = ("pending", "in_progress", "sent", "failed", "skipped")
CALLBACK_EVENTS = ("contact.finished", "contact.followup", "campaign.finished")
CALLBACK_STATUSES = ("pending", "sent", "failed")
CAMPAIGN_CONTACT_RESULTS = ("sent", "delivered", "read", "replied", "answered", "no_answer", "busy", "voicemail",
                            "invalid", "rejected", "failed")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Contact(IdMixin, TimestampMixin, Base):
    """Un contacto de la agenda del cliente. Lo unico obligatorio es el telefono."""
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("client_id", "phone", name="uq_contacts_client_phone"),
        CheckConstraint(_in("source", CONTACT_SOURCES), name="ck_contacts_source"),
        Index("ix_contacts_client_archived", "client_id", "archived_at"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="RESTRICT"))
    phone: Mapped[str] = mapped_column(String(20))      # E.164: +549351... (celular), +54... (fijo)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)   # id en el sistema del cliente
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)     # nota libre, como la de un contacto del telefono
    source: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")
    # NULL: activo. Archivar no borra: se conservan el historial y los reportes.
    archived_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class ContactOptout(Base):
    """Telefono que pidio no ser contactado por un canal (o por todos) de un cliente."""
    __tablename__ = "contact_optouts"
    __table_args__ = (
        CheckConstraint(_in("channel", OPTOUT_CHANNELS), name="ck_contact_optouts_channel"),
        CheckConstraint(_in("source", OPTOUT_SOURCES), name="ck_contact_optouts_source"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), primary_key=True)     # E.164
    channel: Mapped[str] = mapped_column(String(16), primary_key=True)
    # keyword (lo escribio), outcome (resultado del agente en una llamada), manual (UI o API).
    source: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class Campaign(IdMixin, TimestampMixin, Base):
    """Campaña saliente a una lista de contactos, por WhatsApp (una plantilla aprobada, por un
    numero conectado: app/whatsapp/campaigns.py y sender.py) o por voz (llamadas del agente).
    La respuesta de un contacto de WhatsApp abre la conversacion con el cuerpo de la plantilla
    como apertura."""
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(_in("channel", CAMPAIGN_CHANNELS), name="ck_campaigns_channel"),
        CheckConstraint(_in("status", CAMPAIGN_STATUSES), name="ck_campaigns_status"),
        CheckConstraint("purpose IS NULL OR " + _in("purpose", CAMPAIGN_PURPOSES), name="ck_campaigns_purpose"),
        CheckConstraint("rate_per_minute > 0", name="ck_campaigns_rate"),
        CheckConstraint("window_start >= 0 AND window_start <= 23 AND window_end >= 1 AND window_end <= 24 "
                        "AND window_start < window_end", name="ck_campaigns_window"),
        # Cada canal exige sus campos.
        CheckConstraint("channel <> 'whatsapp' OR (account_id IS NOT NULL AND template_name IS NOT NULL "
                        "AND template_language IS NOT NULL)", name="ck_campaigns_whatsapp_fields"),
        CheckConstraint("channel <> 'voice' OR concurrency IS NOT NULL", name="ck_campaigns_voice_fields"),
        CheckConstraint("concurrency IS NULL OR concurrency >= 1", name="ck_campaigns_concurrency"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    # NULL en WhatsApp: responde el agente del numero.
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    channel: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    # Motivo de la ultima pausa automatica (token rechazado, plantilla pausada por Meta...).
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Envios o arranques de llamada por minuto.
    rate_per_minute: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    # Horario permitido, en horas locales de settings.billing_timezone: [window_start, window_end).
    window_start: Mapped[int] = mapped_column(Integer, default=9, server_default="9")
    window_end: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    # Dias de la semana permitidos (0 = lunes ... 6 = domingo). NULL: todos.
    weekdays: Mapped[list | None] = mapped_column(JSONDoc, nullable=True)
    # Programacion: no arranca antes de starts_at y se cierra pasado ends_at (UTC).
    starts_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # comercial, cobranza, turnos o aviso (las comerciales confirman el Registro No Llame).
    purpose: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Cuando se confirmo, al iniciar una campaña comercial, que la lista se filtro contra el Registro No Llame.
    no_call_confirmed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL", name="fk_campaigns_created_by_users"),
        nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Webhook por cada contacto que termina y al terminar la campaña (firmado con callback_secret, que
    # va cifrado con WA_TOKEN_KEY: app/services/campaign_callbacks.py).
    callback_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    callback_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- WhatsApp ---
    account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=True, index=True)
    # Copia de la plantilla de Meta al crearla: el cuerpo es la apertura de la conversacion.
    template_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    template_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    template_category: Mapped[str] = mapped_column(String(32), default="", server_default="")
    template_body: Mapped[str] = mapped_column(Text, default="", server_default="")
    template_params: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Atributo del contacto que completa cada {{n}} (["nombre", "deuda"]: {{1}} = nombre, {{2}} = deuda);
    # NULL: los valores van posicionales en vars["params"] de cada contacto.
    template_param_names: Mapped[list | None] = mapped_column(JSONDoc, nullable=True)

    # --- Voz ---
    # Caller ID (numero del cliente) y voz del TTS; NULL: los defaults.
    from_number_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True)
    voice: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Llamadas simultaneas de la campaña: 1 = secuencial, N = paralelo.
    concurrency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Reintentos por contacto (default 3 intentos, 60 min, no_answer/busy/voicemail/failed).
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_on: Mapped[list | None] = mapped_column(JSONDoc, nullable=True)
    # Seguimiento por WhatsApp a quien no atendio (plan, seccion 6); NULL: apagado. {after, account_id,
    # template_name, template_language, template_body, template_params, params, agent_id}
    # (services/campaigns.py, followup_config).
    followup: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)


class CampaignContact(IdMixin, Base):
    """Un contacto en una campaña. En WhatsApp, entregado y leido salen de wa_messages (por wamid)."""
    __tablename__ = "campaign_contacts"
    __table_args__ = (
        CheckConstraint(_in("status", CAMPAIGN_CONTACT_STATUSES), name="ck_campaign_contacts_status"),
        CheckConstraint("result IS NULL OR " + _in("result", CAMPAIGN_CONTACT_RESULTS),
                        name="ck_campaign_contacts_result"),
        CheckConstraint("followup_status IS NULL OR " + _in("followup_status", FOLLOWUP_STATUSES),
                        name="ck_campaign_contacts_followup_status"),
        UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_contacts_campaign_contact"),
        Index("ix_campaign_contacts_campaign_status", "campaign_id", "status"),
        Index("ix_campaign_contacts_campaign_followup", "campaign_id", "followup_status"),
        Index("ix_campaign_contacts_contact_sent", "contact_id", "sent_at"),
    )
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"))
    contact_id: Mapped[str] = mapped_column(String(36), ForeignKey("contacts.id", ondelete="RESTRICT"))
    # Copia de los datos del contacto al agregarlo, mas los propios de la campaña: la campaña no
    # cambia si despues se edita el contacto. En WhatsApp, "params" son los valores de {{1}}..{{n}}
    # (el mapeo por nombre llega con las variables, fase 3 del plan).
    vars: Mapped[dict] = mapped_column(JSONDoc, default=dict)
    # pending, in_progress (en vuelo), retry, done, failed, skipped (baja, archivado o cancelada).
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    # WhatsApp: sent (Meta lo acepto; delivered, read y replied salen de wa_messages y replied_at).
    # Voz: answered, no_answer, busy, voicemail, invalid, rejected, failed.
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)   # {code, subcode, message} de Meta o SIP
    # La que abrio su respuesta (WhatsApp) o el ultimo intento (voz).
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    # WhatsApp.
    wamid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    replied_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Voz.
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Seguimiento por WhatsApp de una campaña de voz. Si el contacto responde a la plantilla, `replied_at`
    # es cuando y `followup_conversation_id` la charla (la del ultimo intento de voz queda en conversation_id).
    followup_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    followup_wamid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    followup_sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    followup_error: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    followup_conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)

    contact: Mapped[Contact] = relationship(lazy="joined", innerjoin=True)

    @property
    def params(self) -> list[str]:
        """Valores de {{1}}..{{n}} de la plantilla (campañas de WhatsApp)."""
        return list((self.vars or {}).get("params") or [])

    @property
    def wa_id(self) -> str:
        """El id de WhatsApp del contacto: su E.164 sin el +."""
        return self.contact.phone.removeprefix("+")

    @property
    def name(self) -> str | None:
        return self.contact.name


class CampaignCallback(IdMixin, Base):
    """Outbox del webhook de una campaña (callback_url): un POST firmado por evento, con reintentos.
    El payload se arma al entregar (app/campaigns/callbacks.py), con los mismos campos del reporte."""
    __tablename__ = "campaign_callbacks"
    __table_args__ = (
        CheckConstraint(_in("event", CALLBACK_EVENTS), name="ck_campaign_callbacks_event"),
        CheckConstraint(_in("status", CALLBACK_STATUSES), name="ck_campaign_callbacks_status"),
        Index("ix_campaign_callbacks_status_next", "status", "next_attempt_at"),
    )
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    campaign_contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("campaign_contacts.id", ondelete="CASCADE"), nullable=True)
    event: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    delivered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
