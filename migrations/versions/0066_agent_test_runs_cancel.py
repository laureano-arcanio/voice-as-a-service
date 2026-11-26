"""Cancelar una corrida de pruebas y el resumen por caso (docs/features/CASOS_DE_PRUEBA.md).

`cancel_requested_at`: el pedido de cancelación de una corrida en curso (la escribe la API y la mira el vigía de la
cola; en cola la corrida pasa a `cancelled` en el acto). `summary`: el `pasa X/N` por variante de cada caso, para la
lista y el historial sin bajar `results`. Las dos nullable, sin backfill: una corrida vieja sin `summary` cae a
`results`.

Revision ID: 0066
Revises: 0065
Create Date: 2026-11-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

JSONDoc = sa.JSON().with_variant(JSONB(), "postgresql")

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_test_runs") as batch:
        batch.add_column(sa.Column("cancel_requested_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("summary", JSONDoc, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("agent_test_runs") as batch:
        batch.drop_column("summary")
        batch.drop_column("cancel_requested_at")
