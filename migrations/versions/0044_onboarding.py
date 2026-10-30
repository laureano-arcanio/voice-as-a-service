"""Asistente de primera vez (docs/features/PRIMERA_VEZ.md): rubro y sitio del cliente, celular del usuario
y cuando lo verifico con el codigo por WhatsApp.

Revision ID: 0044
Revises: 0043
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("industry", sa.String(24), nullable=False, server_default=""))
        batch.add_column(sa.Column("website", sa.String(200), nullable=False, server_default=""))
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("phone", sa.String(32), nullable=True))
        batch.add_column(sa.Column("phone_verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("phone_verified_at")
        batch.drop_column("phone")
    with op.batch_alter_table("clients") as batch:
        batch.drop_column("website")
        batch.drop_column("industry")
