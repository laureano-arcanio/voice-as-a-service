"""WhatsApp por plan y lo que incluye el Free (docs/ARQUITECTURA.md).

- tiers.whatsapp: si el plan incluye WhatsApp (cuentas, mensajes y llamadas). Los existentes quedan en true.
- Free: sin WhatsApp, campañas, contactos ni equipo, y un link para llamar. Mostrador: sin campañas.
  Por nombre, como estan en produccion (24-oct-2026); despues se cambian en la pantalla Tiers.

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("whatsapp", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("UPDATE tiers SET whatsapp = false, campaign_channels = '[]', max_contacts = 0, "
               "max_team_members = 0, max_call_links = 1 WHERE name = 'Free'")
    op.execute("UPDATE tiers SET campaign_channels = '[]' WHERE name = 'Mostrador'")


def downgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.drop_column("whatsapp")
