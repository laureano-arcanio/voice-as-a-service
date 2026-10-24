"""Migracion 0025 (WhatsApp por plan): ida y vuelta en SQLite, el esquema coincide con el modelo y el Free
queda sin WhatsApp, campañas, contactos ni equipo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0025_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0024")
    with engine.begin() as conn:
        for name in ("Free", "Mostrador", "Sucursal"):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, campaign_channels, created_at, updated_at) "
                                 "VALUES (:n, :n, '', '[\"whatsapp\"]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                         {"n": name})
    _run(engine, command.upgrade, "0025")
    with engine.connect() as conn:
        rows = {r.name: r for r in conn.execute(sa.text(
            "SELECT name, whatsapp, campaign_channels, max_contacts, max_team_members, max_call_links FROM tiers"))}
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "tiers" in repr(d)] == []
    assert tuple(rows["Free"])[1:] == (0, "[]", 0, 0, 1)
    assert tuple(rows["Mostrador"])[1:] == (1, "[]", None, None, None)
    assert tuple(rows["Sucursal"])[1:] == (1, '["whatsapp"]', None, None, None)
    _run(engine, command.downgrade, "0024")
    assert "whatsapp" not in {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
    _run(engine, command.upgrade, "0025")
