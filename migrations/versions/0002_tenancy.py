"""Clientes, tiers, numeros, usuarios, API keys y agentes versionados.

Las conversaciones pasan de workflow_id (YAML) a agent_id + agent_version; el
workflow_id anterior queda en legacy_workflow_id y `python -m app.cli seed` las
asocia a los agentes del cliente interno.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _timestamps() -> list[sa.Column]:
    return [sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False)]


def upgrade() -> None:
    op.create_table(
        "tiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("max_concurrent_calls", sa.Integer(), nullable=True),
        sa.Column("inbound_minutes", sa.Integer(), nullable=True),
        sa.Column("outbound_minutes", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("max_concurrent_calls IS NULL OR max_concurrent_calls >= 0", name="ck_tiers_concurrency"),
        sa.CheckConstraint("inbound_minutes IS NULL OR inbound_minutes >= 0", name="ck_tiers_inbound"),
        sa.CheckConstraint("outbound_minutes IS NULL OR outbound_minutes >= 0", name="ck_tiers_outbound"),
    )
    op.create_table(
        "clients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("tier_id", sa.String(36), sa.ForeignKey("tiers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index("ix_clients_tier_id", "clients", ["tier_id"])
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("(role = 'admin' AND client_id IS NULL) OR (role = 'client' AND client_id IS NOT NULL)",
                           name="ck_users_role_client"),
    )
    op.create_index("ix_users_client_id", "users", ["client_id"])
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_api_keys_client_id", "api_keys", ["client_id"])
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", JSONDoc, nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("client_id", "slug", name="uq_agents_client_slug"),
    )
    op.create_index("ix_agents_client_id", "agents", ["client_id"])
    op.create_table(
        "agent_versions",
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("definition", JSONDoc, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_table(
        "phone_numbers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("e164", sa.String(16), nullable=False, unique=True),
        sa.Column("label", sa.String(64), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_phone_numbers_client_id", "phone_numbers", ["client_id"])
    op.create_index("ix_phone_numbers_agent_id", "phone_numbers", ["agent_id"])

    with op.batch_alter_table("conversations") as t:
        t.alter_column("workflow_id", new_column_name="legacy_workflow_id", existing_type=sa.String(64), nullable=True)
        t.add_column(sa.Column("client_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("agent_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("agent_version", sa.Integer(), nullable=True))
        t.create_foreign_key("fk_conversations_client_id", "clients", ["client_id"], ["id"], ondelete="RESTRICT")
        t.create_foreign_key("fk_conversations_agent_id", "agents", ["agent_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_conversations_client_created", "conversations", ["client_id", "created_at"])
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"])

    with op.batch_alter_table("call_logs") as t:
        t.add_column(sa.Column("client_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("phone_number_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("ended_at", sa.DateTime(), nullable=True))
        t.create_foreign_key("fk_call_logs_client_id", "clients", ["client_id"], ["id"], ondelete="RESTRICT")
        t.create_foreign_key("fk_call_logs_phone_number_id", "phone_numbers", ["phone_number_id"], ["id"],
                             ondelete="SET NULL")
    op.create_index("ix_call_logs_client_started", "call_logs", ["client_id", "started_at"])
    op.create_index("ix_call_logs_client_status", "call_logs", ["client_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_call_logs_client_status", "call_logs")
    op.drop_index("ix_call_logs_client_started", "call_logs")
    with op.batch_alter_table("call_logs") as t:
        t.drop_constraint("fk_call_logs_phone_number_id", type_="foreignkey")
        t.drop_constraint("fk_call_logs_client_id", type_="foreignkey")
        t.drop_column("ended_at")
        t.drop_column("phone_number_id")
        t.drop_column("client_id")
    op.drop_index("ix_conversations_agent_id", "conversations")
    op.drop_index("ix_conversations_client_created", "conversations")
    # Las conversaciones creadas con agentes no tienen workflow_id: se usa el slug del agente.
    op.execute("UPDATE conversations SET legacy_workflow_id = COALESCE(legacy_workflow_id, "
               "(SELECT slug FROM agents WHERE agents.id = conversations.agent_id), '')")
    with op.batch_alter_table("conversations") as t:
        t.drop_constraint("fk_conversations_agent_id", type_="foreignkey")
        t.drop_constraint("fk_conversations_client_id", type_="foreignkey")
        t.drop_column("agent_version")
        t.drop_column("agent_id")
        t.drop_column("client_id")
        t.alter_column("legacy_workflow_id", new_column_name="workflow_id", existing_type=sa.String(64),
                       nullable=False)
    for table in ("phone_numbers", "agent_versions", "agents", "api_keys", "users", "clients", "tiers"):
        op.drop_table(table)
