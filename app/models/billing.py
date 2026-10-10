"""Cobro de los planes (docs/SUSCRIPCIONES_PLAN.md): la suscripcion de cada cliente y sus pagos.
Las transiciones viven en app/billing/service.py; el tier vigente sigue siendo clients.tier_id."""
import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, JSONDoc
from ._common import IdMixin, TimestampMixin

SUBSCRIPTION_STATUSES = ("pending", "active", "past_due", "canceled")
PAYMENT_METHODS = ("transfer", "mercadopago")


class Subscription(IdMixin, TimestampMixin, Base):
    """Plan pago de un cliente. A lo sumo una no cancelada por cliente (lo cuida el servicio, con
    lock de la fila del cliente).

    pending: pedida, sin pago (el cliente sigue en su tier). active: pagada hasta
    `current_period_end` (inclusive). past_due: vencida sin pago, con el tier pago hasta
    `grace_until`. canceled: terminada; el cliente vuelve al Free."""
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'active', 'past_due', 'canceled')", name="ck_subscriptions_status"),
        CheckConstraint("method IN ('transfer', 'mercadopago')", name="ck_subscriptions_method"),
        Index("ix_subscriptions_client_status", "client_id", "status"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"))
    tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("tiers.id", ondelete="RESTRICT"))
    method: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # Cambio pedido que se aplica con el proximo pago (bajada, o el plan nuevo de una transferencia).
    pending_tier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tiers.id", ondelete="SET NULL"), nullable=True)
    # Ultimo dia pago (en BILLING_TIMEZONE) y fin de la gracia.
    current_period_end: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    grace_until: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    # El cliente la dio de baja: dura hasta current_period_end, sin gracia.
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    canceled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    # Vencimiento del ultimo recordatorio enviado (uno por periodo).
    reminded_for: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    # Mercado Pago (fase 3).
    mp_preapproval_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    payer_email: Mapped[str] = mapped_column(String(254), default="", server_default="")


class BillingPayment(IdMixin, TimestampMixin, Base):
    """Un pago recibido (o rechazado, en Mercado Pago). `invoiced_at`: cuando se emitio la factura,
    que se hace a mano fuera de la app."""
    __tablename__ = "billing_payments"
    __table_args__ = (
        CheckConstraint("status IN ('approved', 'rejected', 'refunded')", name="ck_billing_payments_status"),
        CheckConstraint("method IN ('transfer', 'mercadopago')", name="ck_billing_payments_method"),
        CheckConstraint("amount_ars >= 0", name="ck_billing_payments_amount"),
        Index("ix_billing_payments_client_paid", "client_id", "paid_on"),
    )
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"))
    subscription_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    tier_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tiers.id", ondelete="SET NULL"),
                                                nullable=True)
    method: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="approved")
    amount_ars: Mapped[int] = mapped_column(Integer)
    paid_on: Mapped[datetime.date] = mapped_column(Date)
    # Hasta que dia cubre (inclusive).
    period_end: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    mp_payment_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    recorded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(String(255), default="", server_default="")
    raw: Mapped[dict | None] = mapped_column(JSONDoc, nullable=True)
    invoiced_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
