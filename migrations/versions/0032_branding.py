"""Marca blanca del panel (docs/MARCA_BLANCA_PLAN.md): client_branding (logo y 3 colores por cliente, 1:1) y
tiers.white_label (si el plan la incluye; Central e Interno).

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("white_label", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE tiers SET white_label = true WHERE name IN ('Central', 'Interno')")
    op.create_table(
        "client_branding",
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("logo", sa.String(80), nullable=True),
        sa.Column("logo_ratio", sa.Float(), nullable=True),
        sa.Column("color_primary", sa.String(7), nullable=False, server_default="#2456e6"),
        sa.Column("color_header", sa.String(7), nullable=False, server_default="#ffffff"),
        sa.Column("color_accent", sa.String(7), nullable=False, server_default="#b45309"),
        sa.Column("powered_by", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("client_branding")
    with op.batch_alter_table("tiers") as batch:
        batch.drop_column("white_label")
