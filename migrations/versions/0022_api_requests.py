"""Pedidos a la API de inferencia, uno por fila (lista del admin y del cliente).

- api_requests: tipo, key, estado, duracion y consumo de cada pedido, sin su contenido.

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("stream", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ttfb_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("audio_seconds", sa.Float(), nullable=True),
        sa.Column("characters", sa.Integer(), nullable=True),
        sa.Column("voice", sa.String(64), nullable=True),
        sa.Column("response_format", sa.String(16), nullable=True),
    )
    op.create_index("ix_api_requests_client_created", "api_requests", ["client_id", "created_at"])
    op.create_index("ix_api_requests_created", "api_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_api_requests_created", table_name="api_requests")
    op.drop_index("ix_api_requests_client_created", table_name="api_requests")
    op.drop_table("api_requests")
