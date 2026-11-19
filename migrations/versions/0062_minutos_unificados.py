"""Minutos unificados por plan: tiers.call_minutes (total mensual de la bolsa compartida, NULL =
ilimitado) y tiers.unified_minutes (true = una bolsa para entrantes y salientes, false = dos). Solo
agrega: los tiers existentes quedan en una bolsa con el mayor de sus minutos de cada sentido (NULL si
alguno era NULL).

Revision ID: 0062
Revises: 0061
Create Date: 2026-11-18

"""
import sqlalchemy as sa
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as t:
        t.add_column(sa.Column("call_minutes", sa.Integer(), nullable=True))
        t.add_column(sa.Column("unified_minutes", sa.Boolean(), nullable=False, server_default=sa.true()))
        t.create_check_constraint("ck_tiers_call_minutes", "call_minutes IS NULL OR call_minutes >= 0")
    op.execute("""
        UPDATE tiers SET call_minutes = CASE
            WHEN inbound_minutes IS NULL OR outbound_minutes IS NULL THEN NULL
            WHEN inbound_minutes >= outbound_minutes THEN inbound_minutes
            ELSE outbound_minutes END
    """)


def downgrade() -> None:
    with op.batch_alter_table("tiers") as t:
        t.drop_constraint("ck_tiers_call_minutes", type_="check")
        t.drop_column("unified_minutes")
        t.drop_column("call_minutes")
