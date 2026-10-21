"""Numeros bloqueados y corte de llamadas desde la API.

- blocked_numbers: telefonos que un cliente no atiende (sus entrantes se cortan sin atender).
- call_logs.room: room de LiveKit de la llamada (la deja el worker), para cortarla desde la API.

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blocked_numbers",
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("phone", sa.String(20), primary_key=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table("call_logs") as batch:
        batch.add_column(sa.Column("room", sa.String(128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as batch:
        batch.drop_column("room")
    op.drop_table("blocked_numbers")
