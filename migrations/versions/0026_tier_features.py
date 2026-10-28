"""Campañas de llamadas, contactos y equipo por plan (docs/ARQUITECTURA.md).

- Campañas de llamadas (voice): Sucursal (de a 1 llamada) y Central (hasta 3), sin CAP con Gemma todavia;
  Interno, sin tope. Mostrador sigue sin campañas.
- Contactos activos: Mostrador 500, Sucursal 5.000; Central sin tope.
- Equipo (derivacion a personas): Mostrador 1, Sucursal 5; Central sin tope.
Por nombre, como estan en produccion (24-oct-2026); despues se cambian en la pantalla Tiers.

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-24
"""
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE tiers SET max_contacts = 500, max_team_members = 1 WHERE name = 'Mostrador'")
    op.execute("UPDATE tiers SET campaign_channels = '[\"whatsapp\", \"voice\"]', max_campaign_concurrency = 1, "
               "max_contacts = 5000, max_team_members = 5 WHERE name = 'Sucursal'")
    op.execute("UPDATE tiers SET campaign_channels = '[\"whatsapp\", \"voice\"]', max_campaign_concurrency = 3 "
               "WHERE name = 'Central'")
    op.execute("UPDATE tiers SET campaign_channels = '[\"whatsapp\", \"voice\"]' WHERE name = 'Interno'")


def downgrade() -> None:
    op.execute("UPDATE tiers SET max_contacts = NULL, max_team_members = NULL WHERE name = 'Mostrador'")
    op.execute("UPDATE tiers SET campaign_channels = '[\"whatsapp\"]', max_campaign_concurrency = NULL, "
               "max_contacts = NULL, max_team_members = NULL WHERE name = 'Sucursal'")
    op.execute("UPDATE tiers SET campaign_channels = '[\"whatsapp\"]', max_campaign_concurrency = NULL "
               "WHERE name = 'Central'")
    op.execute("UPDATE tiers SET campaign_channels = '[\"whatsapp\"]' WHERE name = 'Interno'")
