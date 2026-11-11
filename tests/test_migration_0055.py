"""Migracion 0055: phone_numbers.record_full_call (false): los numeros existentes no graban la llamada completa."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def _cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("phone_numbers")}


def _value(engine):
    with engine.connect() as conn:
        return conn.execute(sa.text("SELECT record_full_call FROM phone_numbers")).scalar_one()


def test_0055_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0054")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n1', '+541152630001', '', 'anura', '2026-11-11', '2026-11-11')"))
    _run(engine, command.upgrade, "0055")
    assert "record_full_call" in _cols(engine)
    assert not _value(engine)
    _run(engine, command.downgrade, "0054")
    assert "record_full_call" not in _cols(engine)
    _run(engine, command.upgrade, "0055")
    assert not _value(engine)
