"""Conexiones de LLM por cliente (BYOK, docs/features/LLM_CONEXIONES.md): llm_connections guarda el proveedor
externo, su API key cifrada y el modelo por defecto. Los agentes la referencian desde su definicion.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("base_url", sa.String(255), nullable=False),
        sa.Column("api_key_enc", sa.Text(), nullable=False),
        sa.Column("last4", sa.String(8), nullable=False, server_default=""),
        sa.Column("default_model", sa.String(128), nullable=False, server_default=""),
        sa.Column("json_mode", sa.String(16), nullable=False, server_default="json_schema"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_detail", sa.String(255), nullable=False, server_default=""),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_llm_connections_client_id", "llm_connections", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_connections_client_id", table_name="llm_connections")
    op.drop_table("llm_connections")
