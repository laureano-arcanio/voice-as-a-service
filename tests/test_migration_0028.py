"""Migracion 0028 (OAuth del servidor MCP): ida y vuelta en SQLite y sin diferencias con los modelos."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = {"oauth_clients", "oauth_grants", "oauth_codes", "oauth_tokens"}


def test_0028_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0028")
    assert TABLES <= set(sa.inspect(engine).get_table_names())
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # oauth_grants.client_id nullable lo hace la 0029.
    later = "modify_nullable', None, 'oauth_grants', 'client_id'"
    assert [d for d in diff if any(t in repr(d) for t in TABLES) and later not in repr(d)] == []
    _run(engine, command.downgrade, "0027")
    assert not (TABLES & set(sa.inspect(engine).get_table_names()))
    _run(engine, command.upgrade, "0028")
    engine.dispose()
