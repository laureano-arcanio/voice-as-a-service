"""Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md, seccion 13): el equipo del cliente llama y atiende sin
el agente.

- call_logs: user_id (quien llamo o atendio), answered_by (agent/team en las entrantes) y
  opted_out_confirmed (se llamo a un contacto dado de baja con confirmacion). CallMode.directa es un valor
  nuevo de call_logs.mode (String, no enum de SQL): no cambia el esquema.
- phone_numbers: quien atiende (answer_mode), donde suena primero, timbre, horario y respaldo. Los
  existentes quedan en `agent` (los ya ruteados siguen con el agente; decision del 27-oct-2026); los nuevos,
  en `team`.
- phone_number_members: las personas del numero, en orden.
- user_presence y call_rings: Disponible en el panel y el timbre de cada usuario en una entrante.
- tiers.direct_calls: en true en todos salvo el Free (precio 0), como advanced_reports en la 0036.
- clients.direct_recording_notice: aviso de grabacion en las directas (apagado).

Revision ID: 0039
Revises: 0038
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("call_logs") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("answered_by", sa.String(8), nullable=True))
        batch.add_column(sa.Column("opted_out_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_foreign_key("fk_call_logs_user_id_users", "users", ["user_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_call_logs_user_id", ["user_id"])

    with op.batch_alter_table("phone_numbers") as batch:
        batch.add_column(sa.Column("answer_mode", sa.String(8), nullable=False, server_default="team"))
        batch.add_column(sa.Column("ring_first", sa.String(8), nullable=False, server_default="phone"))
        batch.add_column(sa.Column("ring_seconds", sa.Integer(), nullable=False, server_default="20"))
        batch.add_column(sa.Column("schedule", JSONDoc, nullable=True))
        batch.add_column(sa.Column("team_fallback", sa.String(16), nullable=False, server_default="voicemail"))
        batch.add_column(sa.Column("team_fallback_message", sa.Text(), nullable=False, server_default=""))
    op.execute("UPDATE phone_numbers SET answer_mode = 'agent'")

    op.create_table(
        "phone_number_members",
        sa.Column("phone_number_id", sa.String(36), sa.ForeignKey("phone_numbers.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("member_id", sa.String(36), sa.ForeignKey("team_members.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_phone_number_members_member_id", "phone_number_members", ["member_id"])

    op.create_table(
        "user_presence",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_presence_client_id", "user_presence", ["client_id"])

    op.create_table(
        "call_rings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ringing"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_call_rings_conversation_user"),
    )
    op.create_index("ix_call_rings_user_status", "call_rings", ["user_id", "status"])

    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("direct_calls", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Pagos (price_ars > 0) y a medida (NULL: Interno); el Free no.
    op.execute("UPDATE tiers SET direct_calls = true WHERE price_ars IS NULL OR price_ars > 0")

    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("direct_recording_notice", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("clients") as batch:
        batch.drop_column("direct_recording_notice")
    with op.batch_alter_table("tiers") as batch:
        batch.drop_column("direct_calls")
    op.drop_index("ix_call_rings_user_status", table_name="call_rings")
    op.drop_table("call_rings")
    op.drop_index("ix_user_presence_client_id", table_name="user_presence")
    op.drop_table("user_presence")
    op.drop_index("ix_phone_number_members_member_id", table_name="phone_number_members")
    op.drop_table("phone_number_members")
    with op.batch_alter_table("phone_numbers") as batch:
        for col in ("team_fallback_message", "team_fallback", "schedule", "ring_seconds", "ring_first", "answer_mode"):
            batch.drop_column(col)
    with op.batch_alter_table("call_logs") as batch:
        batch.drop_index("ix_call_logs_user_id")
        batch.drop_constraint("fk_call_logs_user_id_users", type_="foreignkey")
        for col in ("opted_out_confirmed", "answered_by", "user_id"):
            batch.drop_column(col)
