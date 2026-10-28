"""MCP, fase 5 (docs/features/MCP.md): oauth_grants.client_id pasa a nullable (un admin que
autoriza "Toda la plataforma" no actúa en un cliente) y mcp_tool_usage, nueva (uso por herramienta y día).

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("oauth_grants") as batch:
        batch.alter_column("client_id", existing_type=sa.String(36), nullable=True)
    op.create_table(
        "mcp_tool_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("tool", sa.String(64), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ms", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_index("ix_mcp_tool_usage_day_client", "mcp_tool_usage", ["day", "client_id"])


def downgrade() -> None:
    op.drop_index("ix_mcp_tool_usage_day_client", table_name="mcp_tool_usage")
    op.drop_table("mcp_tool_usage")
    # Los permisos de admin sin cliente no tienen lugar en el esquema anterior.
    op.execute("DELETE FROM oauth_grants WHERE client_id IS NULL")
    with op.batch_alter_table("oauth_grants") as batch:
        batch.alter_column("client_id", existing_type=sa.String(36), nullable=False)
