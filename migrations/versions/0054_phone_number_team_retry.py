"""Entrante al equipo: reintentos con espera si nadie atiende, en phone_numbers. Solo agrega.

Revision ID: 0054
Revises: 0053
Create Date: 2026-11-11

"""
import sqlalchemy as sa
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("team_retry_seconds", sa.Integer(), nullable=False, server_default="0"))
        t.add_column(sa.Column("team_retry_interval_seconds", sa.Integer(), nullable=False, server_default="30"))
        t.add_column(sa.Column("team_retry_message", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_column("team_retry_message")
        t.drop_column("team_retry_interval_seconds")
        t.drop_column("team_retry_seconds")
