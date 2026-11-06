"""Entrante al equipo en orden o rotativa: strategy y last_member_id en phone_numbers, como handoff_areas. Solo agrega.

Revision ID: 0050
Revises: 0049
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("strategy", sa.String(16), nullable=False, server_default="sequential"))
        t.add_column(sa.Column("last_member_id", sa.String(36), nullable=True))
        t.create_foreign_key("fk_phone_numbers_last_member", "team_members", ["last_member_id"], ["id"],
                             ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_constraint("fk_phone_numbers_last_member", type_="foreignkey")
        t.drop_column("last_member_id")
        t.drop_column("strategy")
