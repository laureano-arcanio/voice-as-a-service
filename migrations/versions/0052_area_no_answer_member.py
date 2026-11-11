"""Si nadie atiende, una persona: handoff_areas.no_answer_member_id (excluyente con no_answer_area_id). Solo agrega.

Revision ID: 0052
Revises: 0051
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("handoff_areas") as t:
        t.add_column(sa.Column("no_answer_member_id", sa.String(36), nullable=True))
        t.create_foreign_key("fk_handoff_areas_no_answer_member", "team_members", ["no_answer_member_id"], ["id"],
                             ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("handoff_areas") as t:
        t.drop_constraint("fk_handoff_areas_no_answer_member", type_="foreignkey")
        t.drop_column("no_answer_member_id")
