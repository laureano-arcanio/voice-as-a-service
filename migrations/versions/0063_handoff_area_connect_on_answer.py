"""Derivación a un área: conectar al atender, en handoff_areas. Solo agrega.

Revision ID: 0063
Revises: 0062
Create Date: 2026-11-20

"""
import sqlalchemy as sa
from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("handoff_areas") as t:
        t.add_column(sa.Column("connect_on_answer", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("handoff_areas") as t:
        t.drop_column("connect_on_answer")
