"""Migracion 0034 (marca blanca): ida y vuelta en SQLite, el esquema coincide con el modelo y solo Central e Interno
incluyen la marca blanca."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0034_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0033")
    with engine.begin() as conn:
        for name in ("Free", "Mostrador", "Sucursal", "Central", "Interno"):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, campaign_channels, created_at, updated_at) "
                                 "VALUES (:n, :n, '', '[]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"n": name})
    _run(engine, command.upgrade, "0034")
    with engine.connect() as conn:
        rows = dict(conn.execute(sa.text("SELECT name, white_label FROM tiers")).all())
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "tiers" in repr(d) or "client_branding" in repr(d)] == []
    assert rows == {"Free": 0, "Mostrador": 0, "Sucursal": 0, "Central": 1, "Interno": 1}
    _run(engine, command.downgrade, "0033")
    assert "white_label" not in {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
    assert "client_branding" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0034")
