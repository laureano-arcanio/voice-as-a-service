"""Tope de retomas de la rotación por WhatsApp: handoff_retakes en wa_threads. Solo agrega.

Revision ID: 0049
Revises: 0048
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wa_threads") as t:
        t.add_column(sa.Column("handoff_retakes", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("wa_threads") as t:
        t.drop_column("handoff_retakes")
