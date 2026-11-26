"""Casos de prueba por agente y sus corridas (docs/features/CASOS_DE_PRUEBA.md).

Revision ID: 0065
Revises: 0064
Create Date: 2026-11-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_test_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_conversation_id", sa.String(36),
                  sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_message_index", sa.Integer(), nullable=True),
        sa.Column("source_agent_version", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(16), nullable=False, server_default="voice"),
        sa.Column("snapshot", JSONDoc, nullable=False),
        sa.Column("tool_results", JSONDoc, nullable=False),
        sa.Column("checks", JSONDoc, nullable=False),
        sa.Column("known_failure", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agent_test_cases_agent_created", "agent_test_cases", ["agent_id", "created_at"])
    op.create_index("ix_agent_test_cases_client", "agent_test_cases", ["client_id"])

    op.create_table(
        "agent_test_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("variants", JSONDoc, nullable=False),
        sa.Column("cases", JSONDoc, nullable=False),
        sa.Column("results", JSONDoc, nullable=True),
        sa.Column("done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_revisions", JSONDoc, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_test_runs_agent_created", "agent_test_runs", ["agent_id", "created_at"])
    op.create_index("ix_agent_test_runs_status", "agent_test_runs", ["status"])
    op.create_index("uq_agent_test_runs_active", "agent_test_runs", ["agent_id"], unique=True,
                    postgresql_where=sa.text("status IN ('queued', 'running')"),
                    sqlite_where=sa.text("status IN ('queued', 'running')"))


def downgrade() -> None:
    op.drop_index("uq_agent_test_runs_active", table_name="agent_test_runs")
    op.drop_index("ix_agent_test_runs_status", table_name="agent_test_runs")
    op.drop_index("ix_agent_test_runs_agent_created", table_name="agent_test_runs")
    op.drop_table("agent_test_runs")
    op.drop_index("ix_agent_test_cases_client", table_name="agent_test_cases")
    op.drop_index("ix_agent_test_cases_agent_created", table_name="agent_test_cases")
    op.drop_table("agent_test_cases")
