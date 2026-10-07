"""WhatsApp: campañas salientes por plantilla (wa_campaigns), sus contactos
(wa_campaign_recipients) y las bajas por cliente (wa_optouts). Ver app/whatsapp/campaigns.py.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-07
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "wa_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("template_name", sa.String(512), nullable=False),
        sa.Column("template_language", sa.String(16), nullable=False),
        sa.Column("template_category", sa.String(32), nullable=False, server_default=""),
        sa.Column("template_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("template_params", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("status_reason", sa.String(255), nullable=True),
        sa.Column("rate_per_minute", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("window_start", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("window_end", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("created_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_wa_campaigns_created_by_users"),
                  nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'running', 'paused', 'done', 'cancelled')",
                           name="ck_wa_campaigns_status"),
        sa.CheckConstraint("rate_per_minute > 0", name="ck_wa_campaigns_rate"),
        sa.CheckConstraint("window_start >= 0 AND window_start <= 23 AND window_end >= 1 AND window_end <= 24 "
                           "AND window_start < window_end", name="ck_wa_campaigns_window"),
    )
    op.create_index("ix_wa_campaigns_client_id", "wa_campaigns", ["client_id"])
    op.create_index("ix_wa_campaigns_account_id", "wa_campaigns", ["account_id"])

    op.create_table(
        "wa_campaign_recipients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("wa_campaigns.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column("params", JSONDoc, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error", JSONDoc, nullable=True),
        sa.Column("wamid", sa.String(128), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'sending', 'sent', 'failed', 'skipped')",
                           name="ck_wa_campaign_recipients_status"),
        sa.UniqueConstraint("campaign_id", "wa_id", name="uq_wa_campaign_recipients_campaign_waid"),
    )
    op.create_index("ix_wa_campaign_recipients_campaign_status", "wa_campaign_recipients", ["campaign_id", "status"])
    op.create_index("ix_wa_campaign_recipients_waid_sent", "wa_campaign_recipients", ["wa_id", "sent_at"])
    op.create_index("ix_wa_campaign_recipients_wamid", "wa_campaign_recipients", ["wamid"])

    op.create_table(
        "wa_optouts",
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("wa_id", sa.String(32), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("wa_optouts")
    op.drop_table("wa_campaign_recipients")
    op.drop_table("wa_campaigns")
