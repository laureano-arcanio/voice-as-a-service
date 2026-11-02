"""call_logs.from_landing: la llamada de prueba salio de la demo de la landing (/api/v1/demo) y no del panel; hasta
ahora las dos eran mode='prueba' sin nada que las distinga. Las viejas del cliente de la demo se marcan como de la
landing: es lo unico que se sabe de ellas.

Revision ID: 0046
Revises: 0045
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("call_logs") as batch:
        batch.add_column(sa.Column("from_landing", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE call_logs SET from_landing = true WHERE mode = 'prueba' AND client_id IN "
               "(SELECT id FROM clients WHERE slug = 'atentina')")


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as batch:
        batch.drop_column("from_landing")
