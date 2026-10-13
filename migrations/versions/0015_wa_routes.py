"""Ruteo por contacto de un numero de WhatsApp (docs/WHATSAPP_PLAN.md): wa_routes guarda,
por cuenta, los contactos (wa_id) que atiende cada agente en lugar del agente por defecto
del numero, en mensajes y llamadas de WhatsApp.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-13
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "wa_routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contacts", JSONDoc, nullable=False),
        sa.UniqueConstraint("account_id", "agent_id", name="uq_wa_routes_account_agent"),
    )
    op.create_index("ix_wa_routes_account_id", "wa_routes", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_wa_routes_account_id", table_name="wa_routes")
    op.drop_table("wa_routes")
