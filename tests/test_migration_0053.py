"""Migracion 0053: phone_numbers.team_fallback_member_id. Sube sin tocar lo que hay; al bajar, los numeros con
team_fallback='member' quedan en 'voicemail' (el codigo viejo no conoce 'member')."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def _number(conn, id_, fallback):
    conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, team_fallback, created_at, updated_at) "
                         "VALUES (:id, :e164, '', 'anura', :fb, '2026-11-11', '2026-11-11')"),
                 {"id": id_, "e164": f"+54115264{id_}", "fb": fallback})


def test_0053_upgrade_downgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0052")
    with engine.begin() as conn:
        _number(conn, "0001", "agent")
        _number(conn, "0002", "hangup")
    _run(engine, command.upgrade, "0053")
    with engine.begin() as conn:
        rows = dict(conn.execute(sa.text("SELECT id, team_fallback FROM phone_numbers")).all())
        assert rows == {"0001": "agent", "0002": "hangup"}
        assert conn.execute(sa.text("SELECT team_fallback_member_id FROM phone_numbers WHERE id = '0001'")).scalar() \
            is None
        _number(conn, "0003", "member")
        conn.execute(sa.text("UPDATE phone_numbers SET team_fallback_member_id = 'm1' WHERE id = '0003'"))
    _run(engine, command.downgrade, "0052")
    with engine.begin() as conn:
        rows = dict(conn.execute(sa.text("SELECT id, team_fallback FROM phone_numbers")).all())
        assert rows == {"0001": "agent", "0002": "hangup", "0003": "voicemail"}
        cols = [c["name"] for c in sa.inspect(conn).get_columns("phone_numbers")]
        assert "team_fallback_member_id" not in cols
