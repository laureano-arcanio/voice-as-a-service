"""Tablas de Registros (migrations/versions/0001_inicial.py)."""
import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, utcnow

SCOPE_READ = "read"
SCOPE_CHARGE = "charge"
SCOPES = (SCOPE_READ, SCOPE_CHARGE)

RELATION_TITULAR = "titular"
RELATION_CONTACTO = "contacto"


def _id():
    return mapped_column(String(36), primary_key=True, default=new_id)


def _tenant_fk():
    return mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)


def _now():
    return mapped_column(DateTime, default=utcnow, nullable=False)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = _id()
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    charge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ARS", server_default="ARS")
    # El formulario es dato del tenant, cargado por CLI; no hay formularios en el código.
    form_html: Mapped[str | None] = mapped_column(Text)
    form_schema: Mapped[dict | None] = mapped_column(JSONB)
    manifest: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime] = _now()


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = _id()
    tenant_id: Mapped[str] = _tenant_fk()
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scope: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime.datetime] = _now()
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    id: Mapped[str] = _id()
    tenant_id: Mapped[str] = _tenant_fk()
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime.datetime] = _now()


class UserSession(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)


class Person(Base):
    __tablename__ = "persons"
    # Destino de las FK compuestas: una fila no puede apuntar a una ficha de otro tenant.
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_persons_tenant_id"),
        Index("ix_persons_tenant_name", "tenant_id", "name"),
    )

    id: Mapped[str] = _id()
    tenant_id: Mapped[str] = _tenant_fk()
    name: Mapped[str] = mapped_column(String(200))
    titular_name: Mapped[str] = mapped_column(String(200))
    al_dia: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    al_dia_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    al_dia_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime.datetime] = _now()
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class PersonPhone(Base):
    __tablename__ = "person_phones"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "person_id"], ["persons.tenant_id", "persons.id"],
                             name="fk_person_phones_person", ondelete="CASCADE"),
        UniqueConstraint("person_id", "phone", name="uq_person_phones_person_phone"),
        Index("ix_person_phones_tenant_phone", "tenant_id", "phone"),
    )

    id: Mapped[str] = _id()
    tenant_id: Mapped[str] = _tenant_fk()
    person_id: Mapped[str] = mapped_column(String(36))
    phone: Mapped[str] = mapped_column(String(20))
    relation: Mapped[str] = mapped_column(String(16))


class ConversationChoice(Base):
    __tablename__ = "conversation_choices"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "person_id"], ["persons.tenant_id", "persons.id"],
                             name="fk_conversation_choices_person"),
    )

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_phone: Mapped[str] = mapped_column(String(20))
    refs: Mapped[dict] = mapped_column(JSONB, default=dict)
    person_id: Mapped[str | None] = mapped_column(String(36))
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)


class Charge(Base):
    __tablename__ = "charges"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "person_id"], ["persons.tenant_id", "persons.id"],
                             name="fk_charges_person"),
        UniqueConstraint("tenant_id", "conversation_id", name="uq_charges_tenant_conversation"),
        Index("ix_charges_tenant_person", "tenant_id", "person_id"),
    )

    id: Mapped[str] = _id()
    tenant_id: Mapped[str] = _tenant_fk()
    conversation_id: Mapped[str] = mapped_column(String(64))
    person_id: Mapped[str] = mapped_column(String(36))
    titular_name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default="simulated", server_default="simulated")
    from_phone: Mapped[str] = mapped_column(String(20))
    operator_message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = _now()


class RecordLink(Base):
    __tablename__ = "record_links"
    __table_args__ = (UniqueConstraint("tenant_id", "conversation_id", name="uq_record_links_tenant_conversation"),)

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_fk()
    conversation_id: Mapped[str] = mapped_column(String(64))
    person_ids: Mapped[list] = mapped_column(JSONB, default=list)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_action_at", "action", "at"),
        Index("ix_audit_log_tenant_at", "tenant_id", "at"),
    )

    id: Mapped[str] = _id()
    # Nulo solo en un login fallido contra un tenant que no existe.
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40))
    person_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("persons.id", ondelete="SET NULL"))
    detail: Mapped[dict | None] = mapped_column(JSONB)
    at: Mapped[datetime.datetime] = _now()
