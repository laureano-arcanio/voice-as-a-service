"""Migracion 0059: phone_numbers.team_busy_message y team_no_answer_message (''): los numeros existentes usan los
avisos por defecto de la entrante al equipo."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

NEW = {"team_busy_message", "team_no_answer_message"}


def _cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("phone_numbers")}


def _row(engine):
    with engine.connect() as conn:
        return tuple(conn.execute(sa.text(
            "SELECT team_busy_message, team_no_answer_message FROM phone_numbers")).one())


def test_0059_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0058")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n1', '+541152630001', '', 'anura', '2026-11-17', '2026-11-17')"))
    _run(engine, command.upgrade, "0059")
    assert NEW <= _cols(engine)
    assert _row(engine) == ("", "")
    _run(engine, command.downgrade, "0058")
    assert not NEW & _cols(engine)
    _run(engine, command.upgrade, "0059")
    assert _row(engine) == ("", "")
