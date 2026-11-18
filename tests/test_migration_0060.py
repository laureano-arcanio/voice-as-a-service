"""Migracion 0060: reparto agente/equipo. phone_numbers.agent_percent (0) y las split_* nulas;
call_logs.split_* nulas. Solo agrega: los numeros existentes quedan sin reparto."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

PHONE = {"agent_percent", "split_experiment", "split_started_at", "split_max_agent_calls"}
CALLS = {"split_arm", "split_reason", "split_percent", "split_experiment"}


def _cols(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_0060_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0059")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n1', '+541152630001', '', 'anura', '2026-11-17', '2026-11-17')"))
    _run(engine, command.upgrade, "0060")
    assert PHONE <= _cols(engine, "phone_numbers") and CALLS <= _cols(engine, "call_logs")
    with engine.connect() as conn:
        assert conn.execute(sa.text(
            "SELECT agent_percent, split_experiment, split_started_at, split_max_agent_calls "
            "FROM phone_numbers")).one() == (0, None, None, None)
    _run(engine, command.downgrade, "0059")
    assert not (PHONE & _cols(engine, "phone_numbers")) and not (CALLS & _cols(engine, "call_logs"))
    _run(engine, command.upgrade, "0060")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT agent_percent FROM phone_numbers")).one() == (0,)
