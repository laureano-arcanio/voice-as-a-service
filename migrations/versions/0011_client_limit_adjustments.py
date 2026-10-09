"""Ajustes de limites por cliente (client_limit_adjustments): sumar o reemplazar un limite del
tier para un cliente en particular, con vigencia opcional. Ver app/services/limits.py.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_limit_adjustments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("note", sa.String(255), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("mode IN ('add', 'set')", name="ck_limit_adj_mode"),
        sa.CheckConstraint("value IS NULL OR value >= 0", name="ck_limit_adj_value"),
        sa.CheckConstraint("mode = 'set' OR value IS NOT NULL", name="ck_limit_adj_add_value"),
        sa.CheckConstraint("starts_on IS NULL OR ends_on IS NULL OR starts_on <= ends_on", name="ck_limit_adj_dates"),
    )
    op.create_index("ix_limit_adj_client_field", "client_limit_adjustments", ["client_id", "field"])


def downgrade() -> None:
    op.drop_index("ix_limit_adj_client_field", table_name="client_limit_adjustments")
    op.drop_table("client_limit_adjustments")
