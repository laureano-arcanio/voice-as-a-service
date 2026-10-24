"""OAuth 2.1 del servidor MCP (docs/MCP_PLAN.md, 4.2): oauth_clients, oauth_grants, oauth_codes y
oauth_tokens, nuevas. Sin datos que migrar.

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.String(512), primary_key=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("client_uri", sa.String(512), nullable=True),
        sa.Column("redirect_uris", JSONDoc, nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "oauth_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("oauth_client_id", sa.String(512), sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("resource", sa.String(512), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    for col in ("oauth_client_id", "user_id", "client_id"):
        op.create_index(f"ix_oauth_grants_{col}", "oauth_grants", [col])
    op.create_table(
        "oauth_codes",
        sa.Column("code_hash", sa.String(64), primary_key=True),
        sa.Column("grant_id", sa.String(36), sa.ForeignKey("oauth_grants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_oauth_codes_grant_id", "oauth_codes", ["grant_id"])
    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("grant_id", sa.String(36), sa.ForeignKey("oauth_grants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_oauth_tokens_grant_id", "oauth_tokens", ["grant_id"])


def downgrade() -> None:
    op.drop_table("oauth_tokens")
    op.drop_table("oauth_codes")
    op.drop_table("oauth_grants")
    op.drop_table("oauth_clients")
