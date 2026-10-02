"""WhatsApp: cerrar una conversacion desde el dashboard (wa_threads.closed_at).

Cerrada, el proximo mensaje del contacto empieza una conversacion nueva, con la version
vigente del agente (app/whatsapp/store.py, active_thread).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-02
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wa_threads") as t:
        t.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("wa_threads") as t:
        t.drop_column("closed_at")
