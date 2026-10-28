"""Contactos como los de un telefono: una nota libre en lugar de etiquetas y datos por contacto.

- contacts.notes: texto libre (hasta 2000 caracteres, lo valida la API).
- Los `attributes` que habia se pasan a `notes` como lineas `clave: valor` (para no perder lo cargado).
- contacts.tags y contacts.attributes se borran. Las campañas ya no eligen destinatarios por etiqueta ni
  completan variables con datos propios del contacto: solo nombre, telefono, email e id externo.

Revision ID: 0040
Revises: 0039
Create Date: 2026-10-27
"""
import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
MAX_NOTES = 2000


def _lines(attributes) -> str:
    if isinstance(attributes, str):
        attributes = json.loads(attributes)
    return "\n".join(f"{k}: {'' if v is None else v}" for k, v in (attributes or {}).items())[:MAX_NOTES]


def upgrade() -> None:
    with op.batch_alter_table("contacts") as batch:
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))

    contacts = sa.table("contacts", sa.column("id", sa.String), sa.column("attributes", JSONDoc),
                        sa.column("notes", sa.Text))
    bind = op.get_bind()
    for contact_id, attributes in bind.execute(sa.select(contacts.c.id, contacts.c.attributes)).all():
        text = _lines(attributes)
        if text:
            bind.execute(contacts.update().where(contacts.c.id == contact_id).values(notes=text))

    with op.batch_alter_table("contacts") as batch:
        batch.drop_column("tags")
        batch.drop_column("attributes")


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch:
        batch.add_column(sa.Column("attributes", JSONDoc, nullable=False, server_default=sa.text("'{}'")))
        batch.add_column(sa.Column("tags", JSONDoc, nullable=False, server_default=sa.text("'[]'")))
    with op.batch_alter_table("contacts") as batch:
        batch.alter_column("attributes", server_default=None)
        batch.alter_column("tags", server_default=None)
        batch.drop_column("notes")
