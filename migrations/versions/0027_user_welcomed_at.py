"""Pop-up de bienvenida del panel para usuarios de cliente: users.welcomed_at (None = mostrarlo).

Los que ya ingresaron alguna vez quedan como vistos (no es su primera vez).

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("welcomed_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET welcomed_at = last_login_at WHERE last_login_at IS NOT NULL")


def downgrade() -> None:
    op.drop_column("users", "welcomed_at")
