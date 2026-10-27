"""Tier interno como marca (docs/ADMIN_SOPORTE_PLAN.md): tiers.internal reemplaza la comparacion con el nombre
"Interno" (no se ofrece como plan ni cuenta en las estadisticas de la plataforma). El tier llamado Interno,
si existe, queda marcado.

Revision ID: 0037
Revises: 0036
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("internal", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE tiers SET internal = true WHERE name = 'Interno'")


def downgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.drop_column("internal")
