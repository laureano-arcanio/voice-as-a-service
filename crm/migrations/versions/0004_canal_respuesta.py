"""CRM: canal de cada mensaje (las respuestas cargadas a mano pueden venir por telefono, agente u otro)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 11:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('channel', sa.String(length=10), nullable=False,
                                        server_default='email'))


def downgrade() -> None:
    op.drop_column('messages', 'channel')
