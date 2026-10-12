"""Apps por cliente y operadores de WhatsApp (docs/APPS_PLAN.md): las tablas apps (contenedores
registrados, inventario como los numeros), app_links (links firmados a sus vistas) y wa_operators
(el dueño de un negocio que le habla a su asistente por un numero compartido).

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "apps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("base_url", sa.String(255), nullable=False),
        sa.Column("token_enc", sa.Text(), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("manifest", JSONDoc, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("last_error", sa.String(255), nullable=True),
        sa.Column("last_health_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('ok', 'down', 'invalid')", name="ck_apps_status"),
    )
    op.create_index("ix_apps_client_id", "apps", ["client_id"])

    op.create_table(
        "app_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("app_id", sa.String(36), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("view", sa.String(64), nullable=False),
        sa.Column("params", JSONDoc, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("opens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_opened_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_app_links_app_id", "app_links", ["app_id"])

    op.create_table(
        "wa_operators",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("account_id", "wa_id", name="uq_wa_operators_account_waid"),
    )
    op.create_index("ix_wa_operators_client_id", "wa_operators", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_wa_operators_client_id", table_name="wa_operators")
    op.drop_table("wa_operators")
    op.drop_index("ix_app_links_app_id", table_name="app_links")
    op.drop_table("app_links")
    op.drop_index("ix_apps_client_id", table_name="apps")
    op.drop_table("apps")
