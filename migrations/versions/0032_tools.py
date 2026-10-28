"""Herramientas del cliente (docs/features/HERRAMIENTAS.md): tabla tools (http y code), agent_secrets (secretos
cifrados por agente) y los campos del plan: tiers.max_tools (NULL = sin tope, 0 = no incluido) y
tiers.code_tools (herramientas en JavaScript). Defaults del 26-oct-2026: HTTP en Sucursal (10), Central
e Interno (sin tope); codigo en Central e Interno. El motor structured se removio: las definiciones
que lo tienen se leen como classic, sin migrar datos.

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "tools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.Column("definition", JSONDoc, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_detail", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("client_id", "slug", name="uq_tools_client_slug"),
    )
    op.create_index("ix_tools_client_id", "tools", ["client_id"])
    op.create_table(
        "agent_secrets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("value_enc", sa.Text(), nullable=False),
        sa.Column("last4", sa.String(8), nullable=False, server_default=""),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("agent_id", "name", name="uq_agent_secrets_agent_name"),
    )
    op.create_index("ix_agent_secrets_agent_id", "agent_secrets", ["agent_id"])
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("max_tools", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("code_tools", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_check_constraint("ck_tiers_tools", "max_tools IS NULL OR max_tools >= 0")
    op.execute("UPDATE tiers SET max_tools = 0 WHERE name NOT IN ('Sucursal', 'Central', 'Interno')")
    op.execute("UPDATE tiers SET max_tools = 10 WHERE name = 'Sucursal'")
    op.execute("UPDATE tiers SET code_tools = true WHERE name IN ('Central', 'Interno')")


def downgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.drop_constraint("ck_tiers_tools", type_="check")
        batch.drop_column("code_tools")
        batch.drop_column("max_tools")
    op.drop_index("ix_agent_secrets_agent_id", table_name="agent_secrets")
    op.drop_table("agent_secrets")
    op.drop_index("ix_tools_client_id", table_name="tools")
    op.drop_table("tools")
