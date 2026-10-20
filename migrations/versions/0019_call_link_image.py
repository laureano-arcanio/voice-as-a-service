"""Link para llamar: imagen propia (docs/LINK_LLAMADA_PLAN.md).

- call_links.image: archivo en storage/call-links/ (NULL: la inicial de la empresa).

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("call_links") as batch:
        batch.add_column(sa.Column("image", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("call_links") as batch:
        batch.drop_column("image")
