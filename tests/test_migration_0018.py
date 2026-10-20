"""Migracion 0018 (call_links, link para llamar): ida y vuelta en SQLite y el esquema migrado
coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("call_links",)
# Columnas nuevas en tablas que ya existian.
COLUMNS = ("max_call_links", "call_link_id")


def test_0018_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0018")
    assert set(TABLES) <= set(sa.inspect(engine).get_table_names())
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # call_links.image es de la 0019.
    assert [d for d in diff if any(t in repr(d) for t in (*TABLES, *COLUMNS)) and "'image'" not in repr(d)] == []

    _run(engine, command.downgrade, "0017")
    assert "call_links" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0018")
