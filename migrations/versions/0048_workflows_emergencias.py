"""Workflows pre-call y post-call, y derivación por WhatsApp: estado del post-call en conversations, aviso por
WhatsApp en team_members, ruteo y envío en handoff_areas, wamid del tramo en handoff_legs y rotación y reenvío
en wa_threads. Solo agrega.

Revision ID: 0048
Revises: 0047
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("conversations") as t:
        t.add_column(sa.Column("post_call_status", sa.String(16), nullable=True))
        t.add_column(sa.Column("post_call_attempts", sa.Integer(), nullable=False, server_default="0"))
        t.add_column(sa.Column("post_call_next_at", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("post_call_note", sa.Text(), nullable=True))
    op.create_index("ix_conversations_post_call", "conversations", ["post_call_status", "post_call_next_at"])

    with op.batch_alter_table("team_members") as t:
        t.add_column(sa.Column("whatsapp_notify", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("handoff_areas") as t:
        t.add_column(sa.Column("after_hours_area_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("no_answer_area_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("delivery", sa.String(16), nullable=False, server_default="call"))
        t.add_column(sa.Column("whatsapp", JSONDoc, nullable=True))
        t.create_foreign_key("fk_handoff_areas_after_hours", "handoff_areas", ["after_hours_area_id"], ["id"],
                             ondelete="SET NULL")
        t.create_foreign_key("fk_handoff_areas_no_answer", "handoff_areas", ["no_answer_area_id"], ["id"],
                             ondelete="SET NULL")

    with op.batch_alter_table("handoff_legs") as t:
        t.add_column(sa.Column("wamid", sa.String(128), nullable=True))
        t.create_unique_constraint("uq_handoff_legs_wamid", ["wamid"])

    with op.batch_alter_table("wa_threads") as t:
        t.add_column(sa.Column("handoff_status", sa.String(16), nullable=True))
        t.add_column(sa.Column("handoff_area_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("handoff_leg_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("handoff_started_at", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("handoff_closed_at", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("handoff_deadline", sa.DateTime(), nullable=True))
        t.add_column(sa.Column("handoff_voice_note", sa.Boolean(), nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("handoff_delivery_tries", sa.Integer(), nullable=False, server_default="0"))
        t.create_foreign_key("fk_wa_threads_handoff_area", "handoff_areas", ["handoff_area_id"], ["id"],
                             ondelete="SET NULL")
        t.create_foreign_key("fk_wa_threads_handoff_leg", "handoff_legs", ["handoff_leg_id"], ["id"],
                             ondelete="SET NULL")
    op.create_index("ix_wa_threads_handoff", "wa_threads", ["handoff_status", "handoff_deadline"])


def downgrade() -> None:
    op.drop_index("ix_wa_threads_handoff", table_name="wa_threads")
    with op.batch_alter_table("wa_threads") as t:
        t.drop_constraint("fk_wa_threads_handoff_leg", type_="foreignkey")
        t.drop_constraint("fk_wa_threads_handoff_area", type_="foreignkey")
        for name in ("handoff_delivery_tries", "handoff_voice_note", "handoff_deadline", "handoff_closed_at",
                     "handoff_started_at", "handoff_leg_id", "handoff_area_id", "handoff_status"):
            t.drop_column(name)

    with op.batch_alter_table("handoff_legs") as t:
        t.drop_constraint("uq_handoff_legs_wamid", type_="unique")
        t.drop_column("wamid")

    with op.batch_alter_table("handoff_areas") as t:
        t.drop_constraint("fk_handoff_areas_no_answer", type_="foreignkey")
        t.drop_constraint("fk_handoff_areas_after_hours", type_="foreignkey")
        for name in ("whatsapp", "delivery", "no_answer_area_id", "after_hours_area_id"):
            t.drop_column(name)

    with op.batch_alter_table("team_members") as t:
        t.drop_column("whatsapp_notify")

    op.drop_index("ix_conversations_post_call", table_name="conversations")
    with op.batch_alter_table("conversations") as t:
        for name in ("post_call_note", "post_call_next_at", "post_call_attempts", "post_call_status"):
            t.drop_column(name)
