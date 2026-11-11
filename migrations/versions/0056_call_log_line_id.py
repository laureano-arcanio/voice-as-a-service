"""Grabacion completa: canal de Asterisk de la entrante en call_logs.line_id (docs/features/EQUIPO_TELEFONIA.md). Solo agrega.

Revision ID: 0056
Revises: 0055
Create Date: 2026-11-11

"""
import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("call_logs") as t:
        t.add_column(sa.Column("line_id", sa.String(64), nullable=True))
    op.create_index("ix_call_logs_line_id", "call_logs", ["line_id"])


def downgrade() -> None:
    op.drop_index("ix_call_logs_line_id", table_name="call_logs")
    with op.batch_alter_table("call_logs") as t:
        t.drop_column("line_id")
