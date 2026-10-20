"""Migracion 0019 (imagen del link para llamar): ida y vuelta en SQLite y el esquema migrado coincide
con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def _columns(engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("call_links")}


def test_0019_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0019")
    assert "image" in _columns(engine)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "call_links" in repr(d)] == []

    _run(engine, command.downgrade, "0018")
    assert "image" not in _columns(engine)
    _run(engine, command.upgrade, "0019")
