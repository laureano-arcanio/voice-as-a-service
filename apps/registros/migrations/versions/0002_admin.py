"""Tenant administrador: sus usuarios administran los demás tenants desde /admin.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Un solo tenant admin.
    op.create_index("uq_tenants_is_admin", "tenants", ["is_admin"], unique=True,
                    postgresql_where=sa.text("is_admin"))


def downgrade() -> None:
    op.drop_index("uq_tenants_is_admin", table_name="tenants")
    op.drop_column("tenants", "is_admin")
