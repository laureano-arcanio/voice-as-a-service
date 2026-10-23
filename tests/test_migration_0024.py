"""Migracion 0024 (tramos de la derivacion): ida y vuelta en SQLite y el esquema coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0024_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0024")
    assert "handoff_legs" in sa.inspect(engine).get_table_names()
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "handoff_legs" in repr(d)] == []
    _run(engine, command.downgrade, "0023")
    assert "handoff_legs" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0024")
