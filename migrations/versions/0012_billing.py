"""Registro autoservicio y cobro de planes (docs/SUSCRIPCIONES_PLAN.md): precio y visibilidad de los
tiers, origen y datos fiscales del cliente, numeros suspendidos, y las tablas subscriptions y
billing_payments.

Los tiers que ya existian quedan sin precio y no publicos: se ofrecen recien cuando se cargan por la UI.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("price_ars", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("public", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("sort", sa.Integer(), nullable=False, server_default="0"))
        batch.create_check_constraint("ck_tiers_price", "price_ars IS NULL OR price_ars >= 0")
    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("created_via", sa.String(16), nullable=False, server_default="admin"))
        batch.add_column(sa.Column("legal_name", sa.String(128), nullable=False, server_default=""))
        batch.add_column(sa.Column("tax_id", sa.String(13), nullable=False, server_default=""))
        batch.add_column(sa.Column("tax_condition", sa.String(16), nullable=False, server_default=""))
    with op.batch_alter_table("phone_numbers") as batch:
        batch.add_column(sa.Column("suspended_at", sa.DateTime(), nullable=True))

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier_id", sa.String(36), sa.ForeignKey("tiers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("pending_tier_id", sa.String(36), sa.ForeignKey("tiers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_period_end", sa.Date(), nullable=True),
        sa.Column("grace_until", sa.Date(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("reminded_for", sa.Date(), nullable=True),
        sa.Column("mp_preapproval_id", sa.String(64), nullable=True, unique=True),
        sa.Column("payer_email", sa.String(254), nullable=False, server_default=""),
        sa.CheckConstraint("status IN ('pending', 'active', 'past_due', 'canceled')", name="ck_subscriptions_status"),
        sa.CheckConstraint("method IN ('transfer', 'mercadopago')", name="ck_subscriptions_method"),
    )
    op.create_index("ix_subscriptions_client_status", "subscriptions", ["client_id", "status"])

    op.create_table(
        "billing_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("tier_id", sa.String(36), sa.ForeignKey("tiers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("amount_ars", sa.Integer(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("mp_payment_id", sa.String(64), nullable=True, unique=True),
        sa.Column("recorded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.String(255), nullable=False, server_default=""),
        sa.Column("raw", JSONDoc, nullable=True),
        sa.Column("invoiced_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('approved', 'rejected', 'refunded')", name="ck_billing_payments_status"),
        sa.CheckConstraint("method IN ('transfer', 'mercadopago')", name="ck_billing_payments_method"),
        sa.CheckConstraint("amount_ars >= 0", name="ck_billing_payments_amount"),
    )
    op.create_index("ix_billing_payments_client_paid", "billing_payments", ["client_id", "paid_on"])


def downgrade() -> None:
    op.drop_index("ix_billing_payments_client_paid", table_name="billing_payments")
    op.drop_table("billing_payments")
    op.drop_index("ix_subscriptions_client_status", table_name="subscriptions")
    op.drop_table("subscriptions")
    with op.batch_alter_table("phone_numbers") as batch:
        batch.drop_column("suspended_at")
    with op.batch_alter_table("clients") as batch:
        for name in ("tax_condition", "tax_id", "legal_name", "created_via"):
            batch.drop_column(name)
    with op.batch_alter_table("tiers") as batch:
        batch.drop_constraint("ck_tiers_price", type_="check")
        for name in ("sort", "public", "price_ars"):
            batch.drop_column(name)
