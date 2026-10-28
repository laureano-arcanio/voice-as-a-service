"""Terminos y condiciones (docs/features/LEGAL.md): legal_acceptances (prueba de la aceptacion de cada version de
las condiciones y de la politica de privacidad) y consumer_requests (botones de arrepentimiento y de baja). Sin claves
foraneas: la prueba sobrevive a que se borre el cliente.

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_acceptances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("client_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("document", sa.String(16), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(512), nullable=False, server_default=""),
    )
    op.create_index("ix_legal_acceptances_user_doc", "legal_acceptances", ["user_id", "document"])
    op.create_index("ix_legal_acceptances_client_id", "legal_acceptances", ["client_id"])
    op.create_table(
        "consumer_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("code", sa.String(16), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("company", sa.String(120), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("client_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("email_status", sa.String(16), nullable=False, server_default="disabled"),
    )
    op.create_index("ix_consumer_requests_created_at", "consumer_requests", ["created_at"])


def downgrade() -> None:
    op.drop_table("consumer_requests")
    op.drop_table("legal_acceptances")
