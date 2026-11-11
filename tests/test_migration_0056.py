"""Migracion 0056: call_logs.line_id (NULL en las llamadas existentes), con indice."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def _cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("call_logs")}


def _indexes(engine):
    return {i["name"] for i in sa.inspect(engine).get_indexes("call_logs")}


def test_0056_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0055")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO call_logs (conversation_id, mode, status, ended_reason, error, "
                             "duration_seconds, created_at) VALUES ('c1', 'entrante', 'finalizada', '', '', 0, "
                             "'2026-11-11')"))
    _run(engine, command.upgrade, "0056")
    assert "line_id" in _cols(engine)
    assert "ix_call_logs_line_id" in _indexes(engine)
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT line_id FROM call_logs")).scalar_one() is None
    _run(engine, command.downgrade, "0055")
    assert "line_id" not in _cols(engine)
    _run(engine, command.upgrade, "0056")
    assert "line_id" in _cols(engine)
