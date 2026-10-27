"""Migraciones 0013 y 0014 (apps y operadores; quitadas en la 0033): ida y vuelta en SQLite. Los modelos ya no
existen, asi que no hay esquema con que comparar."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

TABLES = ("apps", "app_links", "wa_operators")
TABLES_0014 = ("app_job_runs",)


def test_0013_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0013")
    assert set(TABLES) <= set(sa.inspect(engine).get_table_names())
    _run(engine, command.downgrade, "0012")
    assert not set(TABLES) & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0013")
    assert set(TABLES) <= set(sa.inspect(engine).get_table_names())


def test_0014_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0014")
    assert set(TABLES_0014) <= set(sa.inspect(engine).get_table_names())
    _run(engine, command.downgrade, "0013")
    assert "app_job_runs" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0014")
