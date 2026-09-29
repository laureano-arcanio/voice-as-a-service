"""Inventario de numeros: un numero puede estar libre (sin cliente), el tier fija
cuantos puede tener un cliente, y se registra el proveedor y cuando se asigno.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as t:
        t.add_column(sa.Column("max_phone_numbers", sa.Integer(), nullable=True))
        t.create_check_constraint("ck_tiers_phone_numbers", "max_phone_numbers IS NULL OR max_phone_numbers >= 0")
    postgres = op.get_bind().dialect.name == "postgresql"
    with op.batch_alter_table("phone_numbers") as t:
        t.add_column(sa.Column("provider", sa.String(32), nullable=False, server_default="anura"))
        t.add_column(sa.Column("assigned_at", sa.DateTime(), nullable=True))
        t.alter_column("client_id", existing_type=sa.String(36), nullable=True)
        if postgres:    # en SQLite (dev) la FK no tiene nombre y no se aplica
            t.drop_constraint("phone_numbers_client_id_fkey", type_="foreignkey")
            t.create_foreign_key("fk_phone_numbers_client_id", "clients", ["client_id"], ["id"], ondelete="SET NULL")
        t.create_check_constraint("ck_phone_numbers_agent_needs_client", "agent_id IS NULL OR client_id IS NOT NULL")
    op.execute("UPDATE phone_numbers SET assigned_at = created_at WHERE client_id IS NOT NULL")


def downgrade() -> None:
    # Los numeros libres no tienen a donde volver: se borran.
    op.execute("DELETE FROM phone_numbers WHERE client_id IS NULL")
    postgres = op.get_bind().dialect.name == "postgresql"
    with op.batch_alter_table("phone_numbers") as t:
        t.drop_constraint("ck_phone_numbers_agent_needs_client", type_="check")
        if postgres:
            t.drop_constraint("fk_phone_numbers_client_id", type_="foreignkey")
            t.create_foreign_key("phone_numbers_client_id_fkey", "clients", ["client_id"], ["id"], ondelete="CASCADE")
        t.alter_column("client_id", existing_type=sa.String(36), nullable=False)
        t.drop_column("assigned_at")
        t.drop_column("provider")
    with op.batch_alter_table("tiers") as t:
        t.drop_constraint("ck_tiers_phone_numbers", type_="check")
        t.drop_column("max_phone_numbers")
