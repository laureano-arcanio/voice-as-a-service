"""WhatsApp con la app de Meta propia del cliente (docs/ADMIN_SOPORTE_PLAN.md, seccion 4): sin Tech Provider
no hay Embedded Signup, asi que el cliente conecta su numero con su app. La cuenta guarda el app secret
(firma de sus webhooks) y el verify token cifrados, y una clave unica para su URL de webhook
(/wa/webhook/<clave>). source = own_app.

Revision ID: 0038
Revises: 0037
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wa_accounts", sa.Column("app_secret", sa.Text(), nullable=True))
    op.add_column("wa_accounts", sa.Column("verify_token", sa.Text(), nullable=True))
    op.add_column("wa_accounts", sa.Column("webhook_key", sa.String(48), nullable=True))
    op.create_index("ix_wa_accounts_webhook_key", "wa_accounts", ["webhook_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_wa_accounts_webhook_key", table_name="wa_accounts")
    op.drop_column("wa_accounts", "webhook_key")
    op.drop_column("wa_accounts", "verify_token")
    op.drop_column("wa_accounts", "app_secret")
