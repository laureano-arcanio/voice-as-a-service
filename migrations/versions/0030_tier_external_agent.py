"""Agente externo (docs/AGENTE_EXTERNO_PLAN.md): tiers.external_agent, si el plan incluye el motor external
(el agente del cliente detras de su endpoint). Solo Central e Interno, por ahora (25-oct-2026).

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("external_agent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE tiers SET external_agent = true WHERE name IN ('Central', 'Interno')")


def downgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.drop_column("external_agent")
