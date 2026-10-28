"""Migracion 0041 (contactos sin ID externo): ida y vuelta en SQLite y el esquema coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0041_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0040")
    assert "external_id" in {c["name"] for c in sa.inspect(engine).get_columns("contacts")}
    _run(engine, command.upgrade, "0041")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "contacts" in repr(d)] == []
    assert "external_id" not in {c["name"] for c in sa.inspect(engine).get_columns("contacts")}
    _run(engine, command.downgrade, "0040")
    assert "external_id" in {c["name"] for c in sa.inspect(engine).get_columns("contacts")}
    _run(engine, command.upgrade, "0041")
