"""Secretos del cliente y credenciales (docs/TOOLS_PLAN.md, 16): client_secrets (para todos los agentes del
cliente; agent_secrets pisa uno con el mismo nombre) y credentials (la autenticacion de una API, reutilizable
entre herramientas).

Revision ID: 0035
Revises: 0034
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")


def _common() -> list[sa.Column]:
    return [
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "client_secrets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("value_enc", sa.Text(), nullable=False),
        sa.Column("last4", sa.String(8), nullable=False, server_default=""),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        *_common(),
        sa.UniqueConstraint("client_id", "name", name="uq_client_secrets_client_name"),
    )
    op.create_index("ix_client_secrets_client_id", "client_secrets", ["client_id"])
    op.create_table(
        "credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(255), nullable=False, server_default=""),
        sa.Column("auth", JSONDoc, nullable=False),
        *_common(),
        sa.UniqueConstraint("client_id", "slug", name="uq_credentials_client_slug"),
    )
    op.create_index("ix_credentials_client_id", "credentials", ["client_id"])


def downgrade() -> None:
    op.drop_table("credentials")
    op.drop_table("client_secrets")
