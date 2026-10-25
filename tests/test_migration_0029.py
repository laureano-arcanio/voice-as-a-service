"""Migracion 0029 (MCP fase 5): oauth_grants.client_id nullable y mcp_tool_usage; ida y vuelta en SQLite y sin
diferencias con los modelos."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = {"oauth_grants", "mcp_tool_usage"}


def test_0029_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0029")
    insp = sa.inspect(engine)
    assert "mcp_tool_usage" in insp.get_table_names()
    assert {c["name"]: c["nullable"] for c in insp.get_columns("oauth_grants")}["client_id"] is True
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(t in repr(d) for t in TABLES)] == []
    _run(engine, command.downgrade, "0028")
    insp = sa.inspect(engine)
    assert "mcp_tool_usage" not in insp.get_table_names()
    assert {c["name"]: c["nullable"] for c in insp.get_columns("oauth_grants")}["client_id"] is False
    _run(engine, command.upgrade, "0029")
    engine.dispose()
