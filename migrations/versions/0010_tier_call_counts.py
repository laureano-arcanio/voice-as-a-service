"""Limites de cantidad de llamadas por hora, dia y mes en los tiers (max_calls_per_hour, _day, _month).

Los tiers que ya existian quedan sin tope (NULL): el limite se carga despues por la UI o la API.
Ver app/services/quota.py.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

COLUMNS = {
    "max_calls_per_hour": "ck_tiers_calls_hour",
    "max_calls_per_day": "ck_tiers_calls_day",
    "max_calls_per_month": "ck_tiers_calls_month",
}


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        for name, check in COLUMNS.items():
            batch.add_column(sa.Column(name, sa.Integer(), nullable=True))
            batch.create_check_constraint(check, f"{name} IS NULL OR {name} >= 0")


def downgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        for name, check in COLUMNS.items():
            batch.drop_constraint(check, type_="check")
            batch.drop_column(name)
