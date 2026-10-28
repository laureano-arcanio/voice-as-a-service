"""api_requests.source: de donde viene el pedido. `api` (la de inferencia, los que ya estaban) o una prueba
de voz (`voice_test_panel`, `voice_test_api`, `voice_test_landing`), que se ve en el uso pero no suma al cupo.

Revision ID: 0043
Revises: 0042
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("api_requests") as batch:
        batch.add_column(sa.Column("source", sa.String(24), nullable=False, server_default="api"))


def downgrade() -> None:
    op.execute("DELETE FROM api_requests WHERE source <> 'api'")
    with op.batch_alter_table("api_requests") as batch:
        batch.drop_column("source")
