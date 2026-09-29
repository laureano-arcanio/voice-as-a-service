"""Esquema anterior a Alembic: conversations y call_logs (los creaba create_all).

Idempotente: en una base que ya los tiene (creada por la app antes de las
migraciones) no hace nada, y `alembic upgrade head` sigue con 0002.

Revision ID: 0001
Revises:
Create Date: 2026-09-29
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "conversations" not in tables:
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workflow_id", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("fields", JSONDoc, nullable=False),
            sa.Column("messages", JSONDoc, nullable=False),
            sa.Column("progress", JSONDoc, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_conversations_created_at", "conversations", ["created_at"])
    if "call_logs" not in tables:
        op.create_table(
            "call_logs",
            sa.Column("conversation_id", sa.String(36),
                      sa.ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("mode", sa.String(16), nullable=False),
            sa.Column("phone", sa.String(32), nullable=True),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("ended_reason", sa.String(128), nullable=False),
            sa.Column("error", sa.Text(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=False),
            sa.Column("latency", JSONDoc, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("call_logs")
    op.drop_table("conversations")
