"""Reparto agente/equipo de la entrante (A/B): phone_numbers.agent_percent (0, no nulo),
split_experiment, split_started_at y split_max_agent_calls; call_logs.split_arm, split_reason,
split_percent y split_experiment. Solo agrega: los números existentes quedan en 0 (sin reparto)
y las llamadas, con todo NULL.

Revision ID: 0060
Revises: 0059
Create Date: 2026-11-17

"""
import sqlalchemy as sa
from alembic import op

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("agent_percent", sa.SmallInteger(), nullable=False, server_default="0"))
        t.add_column(sa.Column("split_experiment", sa.String(16), nullable=True))
        t.add_column(sa.Column("split_started_at", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("split_max_agent_calls", sa.Integer(), nullable=True))
    with op.batch_alter_table("call_logs") as t:
        t.add_column(sa.Column("split_arm", sa.String(8), nullable=True))
        t.add_column(sa.Column("split_reason", sa.String(24), nullable=True))
        t.add_column(sa.Column("split_percent", sa.SmallInteger(), nullable=True))
        t.add_column(sa.Column("split_experiment", sa.String(16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as t:
        t.drop_column("split_experiment")
        t.drop_column("split_percent")
        t.drop_column("split_reason")
        t.drop_column("split_arm")
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_column("split_max_agent_calls")
        t.drop_column("split_started_at")
        t.drop_column("split_experiment")
        t.drop_column("agent_percent")
