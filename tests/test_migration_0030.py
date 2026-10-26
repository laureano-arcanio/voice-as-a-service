"""Migracion 0030 (agente externo por plan): ida y vuelta en SQLite, el esquema coincide con el modelo y solo
Central e Interno lo incluyen."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0030_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0029")
    with engine.begin() as conn:
        for name in ("Free", "Mostrador", "Sucursal", "Central", "Interno"):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, campaign_channels, created_at, updated_at) "
                                 "VALUES (:n, :n, '', '[]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"n": name})
    _run(engine, command.upgrade, "0030")
    with engine.connect() as conn:
        rows = dict(conn.execute(sa.text("SELECT name, external_agent FROM tiers")).all())
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "tiers" in repr(d) and "'white_label'" not in repr(d)] == []
    assert rows == {"Free": 0, "Mostrador": 0, "Sucursal": 0, "Central": 1, "Interno": 1}
    _run(engine, command.downgrade, "0029")
    assert "external_agent" not in {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
    _run(engine, command.upgrade, "0030")
