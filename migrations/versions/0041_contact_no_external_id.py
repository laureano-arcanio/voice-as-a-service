"""Contactos sin ID externo: el contacto es teléfono, nombre, email y nota.

- contacts.external_id se borra (el reporte de campaña tampoco lo lleva).

Revision ID: 0041
Revises: 0040
Create Date: 2026-10-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("contacts") as batch:
        batch.drop_column("external_id")


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch:
        batch.add_column(sa.Column("external_id", sa.String(128), nullable=True))
