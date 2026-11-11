"""Grabar la llamada completa por numero (Asterisk, docs/features/EQUIPO_TELEFONIA.md). Solo agrega.

Revision ID: 0055
Revises: 0054
Create Date: 2026-11-11

"""
import sqlalchemy as sa
from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("record_full_call", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_column("record_full_call")
