"""WhatsApp fase 2 (Embedded Signup, docs/WHATSAPP_PLAN.md 3.3) y sesiones revocables.

- users.session_version: el logout y el cambio de clave invalidan los JWT emitidos.
- wa_accounts: estado de la conexion (connected, pending, disconnected), calidad y
  limite de Meta, origen del alta, PIN cifrado y quien la conecto. access_token no
  cambia de esquema: pasa a guardar "fernet:<token>" (app/whatsapp/crypto.py).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

WA_COLUMNS = ("status", "status_reason", "status_changed_at", "quality_rating", "messaging_limit",
              "business_id", "source", "pin_enc", "connected_by")


def upgrade() -> None:
    with op.batch_alter_table("users") as t:
        t.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("wa_accounts") as t:
        t.add_column(sa.Column("status", sa.String(16), nullable=False, server_default="connected"))
        t.add_column(sa.Column("status_reason", sa.String(255), nullable=True))
        t.add_column(sa.Column("status_changed_at", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("quality_rating", sa.String(16), nullable=True))
        t.add_column(sa.Column("messaging_limit", sa.String(32), nullable=True))
        t.add_column(sa.Column("business_id", sa.String(32), nullable=True))
        t.add_column(sa.Column("source", sa.String(16), nullable=False, server_default="manual"))
        t.add_column(sa.Column("pin_enc", sa.Text(), nullable=True))
        t.add_column(sa.Column("connected_by", sa.String(36), nullable=True))
        t.create_check_constraint("ck_wa_accounts_status", "status IN ('connected', 'pending', 'disconnected')")
        t.create_foreign_key("fk_wa_accounts_connected_by_users", "users", ["connected_by"], ["id"],
                             ondelete="SET NULL")
    op.create_index("ix_wa_accounts_waba_id", "wa_accounts", ["waba_id"])


def downgrade() -> None:
    op.drop_index("ix_wa_accounts_waba_id", table_name="wa_accounts")
    with op.batch_alter_table("wa_accounts") as t:
        t.drop_constraint("fk_wa_accounts_connected_by_users", type_="foreignkey")
        t.drop_constraint("ck_wa_accounts_status", type_="check")
        for name in WA_COLUMNS:
            t.drop_column(name)
    with op.batch_alter_table("users") as t:
        t.drop_column("session_version")
