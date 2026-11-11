"""Si nadie atiende en un numero del equipo, una persona: team_fallback suma 'member' y
phone_numbers.team_fallback_member_id. Solo agrega; el downgrade pasa 'member' a 'voicemail' (el codigo viejo no lo
conoce) antes de borrar la columna.

Revision ID: 0053
Revises: 0052
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("team_fallback_member_id", sa.String(36), nullable=True))
        t.create_foreign_key("fk_phone_numbers_team_fallback_member", "team_members", ["team_fallback_member_id"],
                             ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.execute("UPDATE phone_numbers SET team_fallback = 'voicemail' WHERE team_fallback = 'member'")
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_constraint("fk_phone_numbers_team_fallback_member", type_="foreignkey")
        t.drop_column("team_fallback_member_id")
