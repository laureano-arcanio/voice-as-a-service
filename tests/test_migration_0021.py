"""Migracion 0021 (numeros bloqueados y room de la llamada): ida y vuelta en SQLite y el esquema
migrado coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0021_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0021")
    inspector = sa.inspect(engine)
    assert "blocked_numbers" in inspector.get_table_names()
    assert "room" in {c["name"] for c in inspector.get_columns("call_logs")}
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "blocked_numbers" in repr(d) or "call_logs" in repr(d)] == []

    _run(engine, command.downgrade, "0020")
    inspector = sa.inspect(engine)
    assert "blocked_numbers" not in inspector.get_table_names()
    assert "room" not in {c["name"] for c in inspector.get_columns("call_logs")}
    _run(engine, command.upgrade, "0021")
