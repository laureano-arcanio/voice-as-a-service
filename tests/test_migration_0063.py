"""Migracion 0063: conectar al atender en handoff_areas (false). Solo agrega: las areas existentes quedan como estaban."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

CONNECT = "connect_on_answer"


def _cols(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_0063_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0062")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c1', 'QA', 'qa-0063', 'pyme', 1, '2026-11-20', '2026-11-20')"))
        conn.execute(sa.text("INSERT INTO handoff_areas (id, client_id, name, created_at, updated_at) "
                             "VALUES ('a1', 'c1', 'Ventas', '2026-11-20', '2026-11-20')"))
    _run(engine, command.upgrade, "0063")
    assert CONNECT in _cols(engine, "handoff_areas")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT connect_on_answer FROM handoff_areas")).one() == (0,)
    _run(engine, command.downgrade, "0062")
    assert CONNECT not in _cols(engine, "handoff_areas")
    _run(engine, command.upgrade, "0063")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT connect_on_answer FROM handoff_areas")).one() == (0,)
