"""Migracion 0013 (apps y operadores): ida y vuelta en SQLite y el esquema migrado coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("apps", "app_links", "wa_operators")
TABLES_0014 = ("app_job_runs",)


def test_0013_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0013")
    assert set(TABLES) <= set(sa.inspect(engine).get_table_names())
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # app_job_runs es de la 0014 (y su FK menciona apps).
    assert [d for d in diff if any(t in repr(d) for t in TABLES) and "app_job_runs" not in repr(d)] == []

    _run(engine, command.downgrade, "0012")
    assert not set(TABLES) & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0013")


def test_0014_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0014")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(t in repr(d) for t in (*TABLES, *TABLES_0014))] == []
    _run(engine, command.downgrade, "0013")
    assert "app_job_runs" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0014")
