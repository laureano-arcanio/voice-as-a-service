"""Link publico para llamar a un agente desde el navegador (docs/LINK_LLAMADA_PLAN.md).

- call_links nueva: un link activo por agente (indice unico parcial sobre revoked_at IS NULL).
- tiers.max_call_links: los existentes quedan sin tope (NULL), como en la 0017.
- call_logs.call_link_id: el link por el que entro la llamada (mode 'web').

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("company_name", sa.String(128), nullable=False, server_default=""),
        sa.Column("subtitle", sa.String(120), nullable=False, server_default=""),
        sa.Column("max_call_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("max_concurrent", sa.Integer(), nullable=True),
        sa.Column("daily_minutes", sa.Integer(), nullable=True),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("max_call_seconds > 0", name="ck_call_links_seconds"),
        sa.CheckConstraint("max_concurrent IS NULL OR max_concurrent >= 0", name="ck_call_links_concurrent"),
        sa.CheckConstraint("daily_minutes IS NULL OR daily_minutes >= 0", name="ck_call_links_daily"),
    )
    op.create_index("ix_call_links_client_id", "call_links", ["client_id"])
    op.create_index("ix_call_links_agent_id", "call_links", ["agent_id"])
    op.create_index("uq_call_links_agent_active", "call_links", ["agent_id"], unique=True,
                    postgresql_where=sa.text("revoked_at IS NULL"), sqlite_where=sa.text("revoked_at IS NULL"))

    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("max_call_links", sa.Integer(), nullable=True))
        batch.create_check_constraint("ck_tiers_call_links", "max_call_links IS NULL OR max_call_links >= 0")

    with op.batch_alter_table("call_logs") as batch:
        batch.add_column(sa.Column("call_link_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_call_logs_call_link_id", "call_links", ["call_link_id"], ["id"],
                                 ondelete="SET NULL")
        batch.create_index("ix_call_logs_call_link_id", ["call_link_id"])


def downgrade() -> None:
    # Las llamadas por link quedan como de prueba (el modo 'web' no existe antes de la 0018).
    op.execute(sa.text("UPDATE call_logs SET mode = 'prueba' WHERE mode = 'web'"))
    with op.batch_alter_table("call_logs") as batch:
        batch.drop_index("ix_call_logs_call_link_id")
        batch.drop_constraint("fk_call_logs_call_link_id", type_="foreignkey")
        batch.drop_column("call_link_id")
    with op.batch_alter_table("tiers") as batch:
        batch.drop_constraint("ck_tiers_call_links", type_="check")
        batch.drop_column("max_call_links")
    op.drop_index("uq_call_links_agent_active", table_name="call_links")
    op.drop_index("ix_call_links_agent_id", table_name="call_links")
    op.drop_index("ix_call_links_client_id", table_name="call_links")
    op.drop_table("call_links")
