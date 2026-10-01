"""WhatsApp, fase 1 (docs/WHATSAPP_PLAN.md): canal de la conversacion, numeros
conectados (wa_accounts), hilo por conversacion (wa_threads) y mensajes por wamid
(wa_messages: dedupe y estados de entrega).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("conversations") as t:
        t.add_column(sa.Column("channel", sa.String(16), nullable=False, server_default="voice"))

    op.create_table(
        "wa_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("phone_number_id", sa.String(32), nullable=False, unique=True),
        sa.Column("waba_id", sa.String(32), nullable=False),
        sa.Column("display_phone_number", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False, server_default=""),
        sa.Column("access_token", sa.Text(), nullable=True),   # TODO fase 2: cifrado (WA_TOKEN_KEY)
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_wa_accounts_client_id", "wa_accounts", ["client_id"])
    op.create_index("ix_wa_accounts_agent_id", "wa_accounts", ["agent_id"])

    op.create_table(
        "wa_threads",
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("contact_name", sa.String(128), nullable=True),
        sa.Column("last_user_at", sa.DateTime(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_wa_threads_account_waid_created", "wa_threads", ["account_id", "wa_id", "created_at"])

    op.create_table(
        "wa_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("wamid", sa.String(128), nullable=True, unique=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("direction", sa.String(3), nullable=False),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", JSONDoc, nullable=True),
        sa.Column("meta_ts", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_wa_messages_conversation_id", "wa_messages", ["conversation_id"])
    op.create_index("ix_wa_messages_account_created", "wa_messages", ["account_id", "created_at"])


def downgrade() -> None:
    op.drop_table("wa_messages")
    op.drop_table("wa_threads")
    op.drop_table("wa_accounts")
    # Las conversaciones de WhatsApp quedan como si fueran de voz (sin su hilo).
    with op.batch_alter_table("conversations") as t:
        t.drop_column("channel")
