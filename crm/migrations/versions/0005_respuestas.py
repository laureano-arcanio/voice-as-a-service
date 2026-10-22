"""CRM: respuestas recibidas por Resend (inbound_emails) y analisis del LLM en cada mensaje

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-22 18:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.add_column('messages', sa.Column('analysis', JSON, nullable=True))
    op.create_table(
        'inbound_emails',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('resend_id', sa.String(length=80), nullable=False, unique=True),
        sa.Column('from_addr', sa.String(length=300), nullable=False),
        sa.Column('to_addr', sa.String(length=300), nullable=False),
        sa.Column('subject', sa.String(length=300), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('headers', JSON, nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=True),
        sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_inbound_emails_received_at', 'inbound_emails', ['received_at'])
    op.create_index('ix_inbound_emails_status', 'inbound_emails', ['status'])


def downgrade() -> None:
    op.drop_table('inbound_emails')
    op.drop_column('messages', 'analysis')
