"""Pedidos de contacto del formulario de la landing (docs/LANDING.md, "Formulario de contacto").

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-02
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("company", sa.String(120), nullable=False, server_default=""),
        sa.Column("email", sa.String(254), nullable=False, server_default=""),
        sa.Column("phone", sa.String(40), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("page", sa.String(64), nullable=False, server_default=""),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("email_status", sa.String(16), nullable=False, server_default="disabled"),
        sa.Column("email_id", sa.String(64), nullable=True),
        sa.Column("email_error", sa.String(255), nullable=True),
    )
    op.create_index("ix_contact_requests_created_at", "contact_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_contact_requests_created_at", table_name="contact_requests")
    op.drop_table("contact_requests")
