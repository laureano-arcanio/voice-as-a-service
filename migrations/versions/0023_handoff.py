"""Derivacion a personas y registro de eventos (docs/DERIVACIONES_PLAN.md, fase 1).

- team_members: el equipo del cliente (telefono, WhatsApp, usuario).
- handoff_areas y handoff_area_members: areas con sus miembros en orden, horario y mensajes.
- events: linea de tiempo por conversacion (llamada o hilo de WhatsApp).
- tiers.max_team_members: los existentes quedan sin tope (NULL), como en la 0018.

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "team_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("whatsapp", sa.String(20), nullable=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("client_id", "whatsapp", name="uq_team_members_client_whatsapp"),
    )
    op.create_index("ix_team_members_client_id", "team_members", ["client_id"])

    op.create_table(
        "handoff_areas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("strategy", sa.String(16), nullable=False, server_default="sequential"),
        sa.Column("ring_seconds", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("schedule", JSONDoc, nullable=True),
        sa.Column("fallback", sa.String(16), nullable=False, server_default="take_message"),
        sa.Column("on_person_hangup", sa.String(8), nullable=False, server_default="resume"),
        sa.Column("return_digits", sa.String(4), nullable=False, server_default="2"),
        sa.Column("wa_reply_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("messages", JSONDoc, nullable=False, server_default="{}"),
        sa.Column("last_member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("client_id", "name", name="uq_handoff_areas_client_name"),
    )
    op.create_index("ix_handoff_areas_client_id", "handoff_areas", ["client_id"])

    op.create_table(
        "handoff_area_members",
        sa.Column("area_id", sa.String(36), sa.ForeignKey("handoff_areas.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_handoff_area_members_member_id", "handoff_area_members", ["member_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("type", sa.String(48), nullable=False),
        sa.Column("actor", sa.String(16), nullable=False, server_default="system"),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("area_id", sa.String(36), sa.ForeignKey("handoff_areas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("data", JSONDoc, nullable=False, server_default="{}"),
    )
    op.create_index("ix_events_client_at", "events", ["client_id", "at"])
    op.create_index("ix_events_conversation_at", "events", ["conversation_id", "at"])

    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("max_team_members", sa.Integer(), nullable=True))
        batch.create_check_constraint("ck_tiers_team_members", "max_team_members IS NULL OR max_team_members >= 0")


def downgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.drop_constraint("ck_tiers_team_members", type_="check")
        batch.drop_column("max_team_members")
    op.drop_index("ix_events_conversation_at", table_name="events")
    op.drop_index("ix_events_client_at", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_handoff_area_members_member_id", table_name="handoff_area_members")
    op.drop_table("handoff_area_members")
    op.drop_index("ix_handoff_areas_client_id", table_name="handoff_areas")
    op.drop_table("handoff_areas")
    op.drop_index("ix_team_members_client_id", table_name="team_members")
    op.drop_table("team_members")
