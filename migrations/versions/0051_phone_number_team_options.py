"""Entrante al equipo: conectar al atender y música mientras suena, en phone_numbers. Solo agrega.

Revision ID: 0051
Revises: 0050
Create Date: 2026-11-11

"""
import sqlalchemy as sa
from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("team_connect_on_answer", sa.Boolean(), nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("team_hold_music", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_column("team_hold_music")
        t.drop_column("team_connect_on_answer")
