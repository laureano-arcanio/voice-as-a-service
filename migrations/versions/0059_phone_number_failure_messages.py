"""Entrante al equipo: avisos apenas una persona da ocupado o no atiende, en phone_numbers. Solo agrega.

Revision ID: 0059
Revises: 0058
Create Date: 2026-11-17

"""
import sqlalchemy as sa
from alembic import op

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("team_busy_message", sa.Text(), nullable=False, server_default=""))
        t.add_column(sa.Column("team_no_answer_message", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_column("team_no_answer_message")
        t.drop_column("team_busy_message")
