"""Cola de la extraccion final de las llamadas de voz en conversations (docs/ARQUITECTURA.md): estado, intentos y
vencimiento, como el post-call. Nullable, sin backfill: las anteriores quedan en NULL (no corresponde). Solo agrega.

Revision ID: 0067
Revises: 0066
Create Date: 2026-11-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as t:
        t.add_column(sa.Column("analysis_status", sa.String(16), nullable=True))
        t.add_column(sa.Column("analysis_attempts", sa.Integer(), nullable=False, server_default="0"))
        t.add_column(sa.Column("analysis_next_at", sa.DateTime(), nullable=True))
    op.create_index("ix_conversations_analysis", "conversations", ["analysis_status", "analysis_next_at"])


def downgrade() -> None:
    op.drop_index("ix_conversations_analysis", table_name="conversations")
    with op.batch_alter_table("conversations") as t:
        for name in ("analysis_next_at", "analysis_attempts", "analysis_status"):
            t.drop_column(name)
