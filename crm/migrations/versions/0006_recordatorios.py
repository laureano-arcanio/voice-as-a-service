"""CRM: recordatorios y reuniones por lead, con su evento en Google Calendar (reminders)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-23 10:30:00
"""
import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('people.id', ondelete='SET NULL'), nullable=True),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('duration_min', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('done_at', sa.DateTime(), nullable=True),
        sa.Column('gcal_event_id', sa.String(length=200), nullable=True),
        sa.Column('gcal_state', sa.String(length=10), nullable=False),
        sa.Column('gcal_error', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    for col in ('lead_id', 'starts_at', 'status', 'gcal_state'):
        op.create_index(f'ix_reminders_{col}', 'reminders', [col])


def downgrade() -> None:
    op.drop_table('reminders')
