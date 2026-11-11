"""Migracion 0054: phone_numbers.team_retry_seconds (0), team_retry_interval_seconds (30) y team_retry_message (''):
los numeros existentes no reintentan, como antes."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

NEW = {"team_retry_seconds", "team_retry_interval_seconds", "team_retry_message"}


def _cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("phone_numbers")}


def _row(engine):
    with engine.connect() as conn:
        return tuple(conn.execute(sa.text(
            "SELECT team_retry_seconds, team_retry_interval_seconds, team_retry_message FROM phone_numbers")).one())


def test_0054_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0053")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n1', '+541152630001', '', 'anura', '2026-11-11', '2026-11-11')"))
    _run(engine, command.upgrade, "0054")
    assert NEW <= _cols(engine)
    assert _row(engine) == (0, 30, "")
    _run(engine, command.downgrade, "0053")
    assert not NEW & _cols(engine)
    _run(engine, command.upgrade, "0054")
    assert _row(engine) == (0, 30, "")
