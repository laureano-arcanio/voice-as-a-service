"""Migracion 0016 (llm_connections, BYOK de LLM): ida y vuelta en SQLite y el esquema migrado
coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("llm_connections",)


def test_0016_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0016")
    assert set(TABLES) <= set(sa.inspect(engine).get_table_names())
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(t in repr(d) for t in TABLES)] == []

    _run(engine, command.downgrade, "0015")
    assert "llm_connections" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0016")
