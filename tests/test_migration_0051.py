"""Migracion 0051: phone_numbers.team_connect_on_answer (false) y team_hold_music (true); los numeros existentes
suenan con musica y piden la tecla, como antes."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def _cols(engine):
    return {c["name"] for c in sa.inspect(engine).get_columns("phone_numbers")}


def test_0051_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0050")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n1', '+541152630001', '', 'anura', '2026-11-11', '2026-11-11')"))
    _run(engine, command.upgrade, "0051")
    assert {"team_connect_on_answer", "team_hold_music"} <= _cols(engine)
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT team_connect_on_answer, team_hold_music FROM phone_numbers")).one()
    assert (bool(row[0]), bool(row[1])) == (False, True)
    _run(engine, command.downgrade, "0050")
    assert not {"team_connect_on_answer", "team_hold_music"} & _cols(engine)
    _run(engine, command.upgrade, "0051")
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT team_connect_on_answer, team_hold_music FROM phone_numbers")).one()
    assert (bool(row[0]), bool(row[1])) == (False, True)
