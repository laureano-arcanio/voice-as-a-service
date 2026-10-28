"""Reportes (docs/features/REPORTES.md): resultado, conversion y tokens en conversations (para agregar sin cargar
la definicion del agente), tool_runs (ejecuciones de herramientas), wa_account_status_log (historial de calidad
de las cuentas de WhatsApp) y tiers.advanced_reports (Resultados, Mensajes, Transferencias y Campañas: los planes
pagos e Interno). El resultado y la conversion de las conversaciones anteriores los completa
`make reports-backfill` (necesita las definiciones de los agentes).

Revision ID: 0036
Revises: 0035
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("advanced_reports", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Pagos (price_ars > 0) y a medida (NULL: Interno); el Free no.
    op.execute("UPDATE tiers SET advanced_reports = true WHERE price_ars IS NULL OR price_ars > 0")

    with op.batch_alter_table("conversations") as batch:
        batch.add_column(sa.Column("outcome", sa.String(64), nullable=True))
        batch.add_column(sa.Column("goal", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("conversion", sa.String(16), nullable=True))
        batch.add_column(sa.Column("llm_input_tokens", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("llm_output_tokens", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "tool_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_id", sa.String(36), sa.ForeignKey("tools.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tool_runs_client_created", "tool_runs", ["client_id", "created_at"])
    op.create_index("ix_tool_runs_tool_id", "tool_runs", ["tool_id"])
    op.create_index("ix_tool_runs_conversation_id", "tool_runs", ["conversation_id"])

    op.create_table(
        "wa_account_status_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=True),
        sa.Column("quality_rating", sa.String(16), nullable=True),
        sa.Column("messaging_limit", sa.String(32), nullable=True),
        sa.Column("at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_wa_account_status_log_account_id", "wa_account_status_log", ["account_id"])


def downgrade() -> None:
    op.drop_table("wa_account_status_log")
    op.drop_table("tool_runs")
    with op.batch_alter_table("conversations") as batch:
        for col in ("llm_output_tokens", "llm_input_tokens", "conversion", "goal", "outcome"):
            batch.drop_column(col)
    with op.batch_alter_table("tiers") as batch:
        batch.drop_column("advanced_reports")
