"""Restos del puente de WhatsApp (nunca se construyo) y slug del agente de demo sin el sufijo _classic.

- team_members.whatsapp (y uq_team_members_client_whatsapp), handoff_areas.wa_reply_minutes y
  wa_threads.paused se borran: nada los usaba (wa_threads.paused nunca se ponia en true).
- agents.slug 'demo_booking_classic' pasa a 'demo_booking' si el cliente no tiene ya un 'demo_booking'.
  El downgrade no puede saber cuales se renombraron: vuelve 'demo_booking' a 'demo_booking_classic'
  solo donde no haya ya un 'demo_booking_classic'.

Revision ID: 0042
Revises: 0041
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def _rename(old: str, new: str) -> None:
    op.execute(sa.text(
        "UPDATE agents SET slug = :new WHERE slug = :old AND NOT EXISTS ("
        "SELECT 1 FROM agents a2 WHERE a2.client_id = agents.client_id AND a2.slug = :new)"
    ).bindparams(old=old, new=new))


def upgrade() -> None:
    with op.batch_alter_table("team_members") as batch:
        batch.drop_constraint("uq_team_members_client_whatsapp", type_="unique")
        batch.drop_column("whatsapp")
    with op.batch_alter_table("handoff_areas") as batch:
        batch.drop_column("wa_reply_minutes")
    with op.batch_alter_table("wa_threads") as batch:
        batch.drop_column("paused")
    _rename("demo_booking_classic", "demo_booking")


def downgrade() -> None:
    _rename("demo_booking", "demo_booking_classic")
    with op.batch_alter_table("wa_threads") as batch:
        batch.add_column(sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("handoff_areas") as batch:
        batch.add_column(sa.Column("wa_reply_minutes", sa.Integer(), nullable=False, server_default="10"))
    with op.batch_alter_table("team_members") as batch:
        batch.add_column(sa.Column("whatsapp", sa.String(20), nullable=True))
        batch.create_unique_constraint("uq_team_members_client_whatsapp", ["client_id", "whatsapp"])
