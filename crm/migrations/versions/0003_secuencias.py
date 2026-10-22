"""CRM: secuencia de seguimientos por campaña y numero de paso por mensaje

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21 21:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('campaigns', sa.Column(
        'sequence', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
        nullable=False, server_default=sa.text("'[]'")))
    op.add_column('messages', sa.Column('step', sa.Integer(), nullable=True))
    # Paso de lo que ya salio: 0 el primero; los seguimientos, en orden por lead.
    op.execute("UPDATE messages SET step = 0 WHERE direction = 'out' AND kind = 'first'")
    op.execute("""
        UPDATE messages m SET step = r.n FROM (
            SELECT id, row_number() OVER (PARTITION BY lead_id ORDER BY coalesce(sent_at, created_at), id) AS n
            FROM messages
            WHERE direction = 'out' AND kind = 'follow_up' AND status NOT IN ('canceled', 'failed')
        ) r WHERE m.id = r.id""")


def downgrade() -> None:
    op.drop_column('messages', 'step')
    op.drop_column('campaigns', 'sequence')
