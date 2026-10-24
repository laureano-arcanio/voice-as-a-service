"""Migracion 0026 (campañas de llamadas, contactos y equipo por plan): ida y vuelta en SQLite."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

COLS = "campaign_channels, max_campaign_concurrency, max_contacts, max_team_members"


def _rows(engine) -> dict:
    with engine.connect() as conn:
        return {r[0]: tuple(r[1:]) for r in conn.execute(sa.text(f"SELECT name, {COLS} FROM tiers"))}


def test_0026_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0025")
    with engine.begin() as conn:
        for name in ("Free", "Mostrador", "Sucursal", "Central", "Interno"):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, campaign_channels, created_at, updated_at) "
                                 "VALUES (:n, :n, '', '[\"whatsapp\"]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                         {"n": name})
        conn.execute(sa.text("UPDATE tiers SET campaign_channels = '[]', max_contacts = 0, max_team_members = 0 "
                             "WHERE name = 'Free'"))
        conn.execute(sa.text("UPDATE tiers SET campaign_channels = '[]' WHERE name = 'Mostrador'"))
    before = _rows(engine)
    _run(engine, command.upgrade, "0026")
    rows = _rows(engine)
    voice = '["whatsapp", "voice"]'
    assert rows["Free"] == ("[]", None, 0, 0)
    assert rows["Mostrador"] == ("[]", None, 500, 1)
    assert rows["Sucursal"] == (voice, 1, 5000, 5)
    assert rows["Central"] == (voice, 3, None, None)
    assert rows["Interno"] == (voice, None, None, None)
    _run(engine, command.downgrade, "0025")
    assert _rows(engine) == before
    _run(engine, command.upgrade, "0026")
