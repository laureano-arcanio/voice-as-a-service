"""Coexistencia de WhatsApp: wa_accounts.attendance (agent | owner, quien atiende el numero) y
on_biz_app (el numero sigue en la app de WhatsApp Business); wa_messages.origin ('app' en los ecos del
dueno). Solo agrega: las cuentas existentes quedan en agent y los mensajes sin origin.

Revision ID: 0061
Revises: 0060
Create Date: 2026-11-18

"""
import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wa_accounts") as t:
        t.add_column(sa.Column("attendance", sa.String(8), nullable=False, server_default="agent"))
        t.add_column(sa.Column("on_biz_app", sa.Boolean(), nullable=True))
        t.create_check_constraint("ck_wa_accounts_attendance", "attendance IN ('agent','owner')")
    with op.batch_alter_table("wa_messages") as t:
        t.add_column(sa.Column("origin", sa.String(8), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("wa_messages") as t:
        t.drop_column("origin")
    with op.batch_alter_table("wa_accounts") as t:
        t.drop_constraint("ck_wa_accounts_attendance", type_="check")
        t.drop_column("on_biz_app")
        t.drop_column("attendance")
