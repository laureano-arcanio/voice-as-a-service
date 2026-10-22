"""Tablas del CRM (docs/CRM_PLAN.md, seccion 3)."""
import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, JSONDoc, utcnow

# Etapas del lead, en orden. Las tres ultimas cierran.
STAGES = ("nuevo", "contactado", "seguimiento", "respondio", "charla_agendada", "charla_hecha",
          "propuesta", "piloto", "cliente", "sin_respuesta", "no_interesa", "descartado")
CLOSED_STAGES = ("sin_respuesta", "no_interesa", "descartado", "cliente")
# Etapas que implican que el lead respondio (por mail, telefono o LinkedIn).
REPLIED_STAGES = ("respondio", "charla_agendada", "charla_hecha", "propuesta", "piloto", "cliente", "no_interesa")
# Mensajes: estados que cuentan como "salio".
SENT_STATUSES = ("sent", "delivered", "bounced", "complained")


def _now_col():
    return mapped_column(DateTime, default=utcnow, nullable=False)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)          # = utm_content
    name: Mapped[str] = mapped_column(String(200))
    legal_name: Mapped[str | None] = mapped_column(String(200))
    domain: Mapped[str | None] = mapped_column(String(200), unique=True)  # clave de dedupe
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)                 # rubro
    kind: Mapped[str | None] = mapped_column(String(20))                  # cliente, canal
    industry: Mapped[str | None] = mapped_column(String(200))
    tags: Mapped[list] = mapped_column(JSONDoc, default=list)
    country: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(20), default="nuevo", index=True)
    stage_changed_at: Mapped[datetime.datetime] = _now_col()
    next_action: Mapped[str | None] = mapped_column(Text)
    next_action_at: Mapped[datetime.date | None] = mapped_column(Date)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    legacy_ref: Mapped[str | None] = mapped_column(String(20))          # el # de seguimiento.md
    created_by: Mapped[str] = mapped_column(String(20), default="usuario")
    created_at: Mapped[datetime.datetime] = _now_col()
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    people: Mapped[list["Person"]] = relationship(back_populates="lead", cascade="all, delete-orphan",
                                                  order_by="Person.id")
    contacts: Mapped[list["ContactPoint"]] = relationship(back_populates="lead",
                                                          cascade="all, delete-orphan",
                                                          order_by="ContactPoint.id")
    sources: Mapped[list["Source"]] = relationship(back_populates="lead", cascade="all, delete-orphan",
                                                   order_by="Source.id")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    seen_at: Mapped[datetime.date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = _now_col()

    lead: Mapped[Lead] = relationship(back_populates="sources")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(300))
    is_decision_maker: Mapped[bool] = mapped_column(Boolean, default=False)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime.datetime] = _now_col()

    lead: Mapped[Lead] = relationship(back_populates="people")


class ContactPoint(Base):
    """Email, telefono, WhatsApp, LinkedIn o formulario de un lead o de una de sus personas."""
    __tablename__ = "contact_points"
    __table_args__ = (UniqueConstraint("lead_id", "kind", "value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(20))       # email, phone, whatsapp, linkedin, form
    value: Mapped[str] = mapped_column(String(500), index=True)
    label: Mapped[str | None] = mapped_column(String(20))  # persona, area, atencion
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)  # el ★
    status: Mapped[str] = mapped_column(String(20), default="ok")    # ok, bounced, unverified
    verified_at: Mapped[datetime.date | None] = mapped_column(Date)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime.datetime] = _now_col()

    lead: Mapped[Lead] = relationship(back_populates="contacts")
    person: Mapped["Person | None"] = relationship()


class Block(Base):
    """Direcciones o dominios a los que no se manda nada (rebote, queja, baja, a mano)."""
    __tablename__ = "blocklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(300), unique=True)
    reason: Mapped[str] = mapped_column(String(20))     # bounce, complaint, opt_out, manual
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = _now_col()


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)          # = utm_campaign
    name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20), default="email")  # email, linkedin, phone
    segment: Mapped[str | None] = mapped_column(Text)
    from_addr: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")  # draft, active, done
    started_at: Mapped[datetime.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    # Seguimientos despues del primer mail: [{"days": 4, "template_id": 3}, ...]. Cada paso sale
    # `days` dias habiles despues del ultimo mail enviado, si el lead no respondio. Vacia: uno
    # solo a los CRM_FOLLOW_UP_BUSINESS_DAYS, sin plantilla (se elige al armarlo).
    sequence: Mapped[list] = mapped_column(JSONDoc, default=list)
    created_at: Mapped[datetime.datetime] = _now_col()


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(20), default="first")    # first, follow_up, other
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)                # a "ustedes" (casilla de area o atencion)
    body_personal: Mapped[str | None] = mapped_column(Text)  # tuteo, si el destinatario es una persona
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = _now_col()
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Message(Base):
    """Mail saliente o entrante. El hilo de un lead es su lista ordenada por fecha."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"),
                                                    index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(20), default="first")    # first, follow_up, other
    step: Mapped[int | None] = mapped_column(Integer)                  # 0 el primero, 1.. seguimientos
    direction: Mapped[str] = mapped_column(String(3), default="out")  # out, in
    # email, phone, agent, other: los enviados son email; una respuesta a mano puede venir por otro lado
    channel: Mapped[str] = mapped_column(String(10), default="email", server_default="email")
    from_addr: Mapped[str | None] = mapped_column(String(200))
    to_addr: Mapped[str] = mapped_column(String(300), index=True)
    subject: Mapped[str] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text, default="")
    # draft, queued, sent, delivered, bounced, complained, failed, canceled, received
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    resend_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    message_id: Mapped[str | None] = mapped_column(String(300))       # Message-ID del mail
    in_reply_to: Mapped[str | None] = mapped_column(String(300))
    utm_campaign: Mapped[str | None] = mapped_column(String(80))
    utm_content: Mapped[str | None] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(20), default="usuario")
    created_at: Mapped[datetime.datetime] = _now_col()
    queued_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, index=True)
    last_event_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    events_checked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    # Respuestas: lo que dijo el LLM (intencion, resumen, ...) y lo que se aplico al lead
    analysis: Mapped[dict | None] = mapped_column(JSONDoc)

    lead: Mapped[Lead] = relationship()
    campaign: Mapped["Campaign | None"] = relationship()


class Activity(Base):
    """Linea de tiempo: notas, llamadas, charlas, LinkedIn, tareas y cambios de etapa."""
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(20))   # note, call, meeting, linkedin, task, stage_change
    at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSONDoc, default=dict)
    due_at: Mapped[datetime.date | None] = mapped_column(Date)       # tareas
    done: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(20), default="usuario")


class GaVisit(Base):
    """Fila del reporte de GA por dia, fuente/medio, campana y contenido."""
    __tablename__ = "ga_visits"
    __table_args__ = (UniqueConstraint("date", "source_medium", "utm_campaign", "utm_content"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    source_medium: Mapped[str] = mapped_column(String(120))
    utm_campaign: Mapped[str] = mapped_column(String(120))
    utm_content: Mapped[str] = mapped_column(String(120))
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    events: Mapped[int] = mapped_column(Integer, default=0)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"))
    follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class InboundEmail(Base):
    """Cada mail recibido por Resend, con lo que se hizo: asignado a un lead (con su mensaje), sin asignar
    (bandeja, para asignarlo a mano) o ignorado (copias nuestras, rebotes)."""
    __tablename__ = "inbound_emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    resend_id: Mapped[str] = mapped_column(String(80), unique=True)
    from_addr: Mapped[str] = mapped_column(String(300))
    to_addr: Mapped[str] = mapped_column(String(300), default="")
    subject: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    headers: Mapped[dict] = mapped_column(JSONDoc, default=dict)
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)   # assigned, unassigned, ignored
    reason: Mapped[str | None] = mapped_column(String(200))        # como se asigno o por que se ignoro
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    created_at: Mapped[datetime.datetime] = _now_col()


class KV(Base):
    """Estado chico de los loops (proximo envio, ultima sync de GA)."""
    __tablename__ = "kv"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONDoc, default=dict)
