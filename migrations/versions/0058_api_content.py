"""Contenido de la API de inferencia y de las pruebas de voz (docs/API_INFERENCIA.md). Solo agrega.

- `clients.store_api_content` (true) y `clients.api_content_retention_days` (30; NULL = indefinido): el ajuste por
  cliente. El server_default llena las filas existentes y las altas.
- `api_requests.content_bytes` (NULL = no hay contenido guardado en disco).

Revision ID: 0058
Revises: 0057
Create Date: 2026-11-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("clients") as t:
        t.add_column(sa.Column("store_api_content", sa.Boolean(), nullable=False, server_default=sa.true()))
        t.add_column(sa.Column("api_content_retention_days", sa.Integer(), nullable=True, server_default="30"))
    with op.batch_alter_table("api_requests") as t:
        t.add_column(sa.Column("content_bytes", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("api_requests") as t:
        t.drop_column("content_bytes")
    with op.batch_alter_table("clients") as t:
        t.drop_column("api_content_retention_days")
        t.drop_column("store_api_content")
