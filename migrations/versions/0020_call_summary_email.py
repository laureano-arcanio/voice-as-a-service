"""Resumen por email despues de cada llamada (app/mail/call_summary.py).

- clients.call_emails: el cliente lo apaga para todos sus agentes (default prendido: decide el agente).
- clients.call_emails_to: destinos; vacio = los usuarios activos del cliente.
- call_logs.summary_email / summary_email_attempts: estado del envio (NULL: no corresponde).

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("call_emails", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("call_emails_to", JSONDoc, nullable=False, server_default=sa.text("'[]'")))
    with op.batch_alter_table("call_logs") as batch:
        batch.add_column(sa.Column("summary_email", sa.String(16), nullable=True))
        batch.add_column(sa.Column("summary_email_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.create_index("ix_call_logs_summary_email", ["summary_email"])


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as batch:
        batch.drop_index("ix_call_logs_summary_email")
        batch.drop_column("summary_email_attempts")
        batch.drop_column("summary_email")
    with op.batch_alter_table("clients") as batch:
        batch.drop_column("call_emails_to")
        batch.drop_column("call_emails")
