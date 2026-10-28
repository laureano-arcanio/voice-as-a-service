"""Tramos de una derivacion de llamada (docs/features/EQUIPO_TELEFONIA.md, fase 2).

- handoff_legs: cada llamada a una persona del area desde una llamada en curso, con su resultado, los
  tiempos y los segundos salientes que se descuentan del plan. Tambien la cuenta el tope de canales.

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "handoff_legs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("area_id", sa.String(36), sa.ForeignKey("handoff_areas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("result", sa.String(16), nullable=False, server_default="dialing"),
        sa.Column("sip_status", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("billed_seconds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_handoff_legs_client_created", "handoff_legs", ["client_id", "created_at"])
    op.create_index("ix_handoff_legs_conversation_id", "handoff_legs", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_handoff_legs_conversation_id", table_name="handoff_legs")
    op.drop_index("ix_handoff_legs_client_created", table_name="handoff_legs")
    op.drop_table("handoff_legs")
