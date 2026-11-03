"""studio_items: lo que un cliente sintetiza o transcribe en el Estudio y sus pruebas de voz, con los
segundos que descuenta de sus minutos (docs/features/ESTUDIO.md).

Revision ID: 0047
Revises: 0046
Create Date: 2026-11-03
"""
import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "studio_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False, server_default="studio"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("voice", sa.String(64), nullable=True),
        sa.Column("language", sa.String(8), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audio_seconds", sa.Float(), nullable=True),
        sa.Column("billed_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("file_name", sa.String(200), nullable=True),
        sa.Column("error", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_studio_items_client_created", "studio_items", ["client_id", "created_at"])
    op.create_index("ix_studio_items_status_created", "studio_items", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_studio_items_status_created", table_name="studio_items")
    op.drop_index("ix_studio_items_client_created", table_name="studio_items")
    op.drop_table("studio_items")
