"""Migracion 0045: el default de quien atiende pasa a ser el agente y los numeros en team sin personas pasan a
agent; los que tienen personas siguen en team."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def _number(conn, id_, mode):
    conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, answer_mode, created_at, updated_at) "
                         "VALUES (:id, :e164, '', 'anura', :mode, '2026-11-02', '2026-11-02')"),
                 {"id": id_, "e164": f"+54115263{id_}", "mode": mode})


def test_0045_upgrade_downgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0044")
    with engine.begin() as conn:
        _number(conn, "0001", "team")   # sin personas
        _number(conn, "0002", "team")   # con personas
        _number(conn, "0003", "agent")
        conn.execute(sa.text("INSERT INTO phone_number_members (phone_number_id, member_id, position) "
                             "VALUES ('0002', 'm1', 0)"))
    _run(engine, command.upgrade, "0045")
    with engine.begin() as conn:
        modes = dict(conn.execute(sa.text("SELECT id, answer_mode FROM phone_numbers")).all())
        assert modes == {"0001": "agent", "0002": "team", "0003": "agent"}
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('0004', '+541152630004', '', 'anura', '2026-11-02', '2026-11-02')"))
        assert conn.execute(sa.text("SELECT answer_mode FROM phone_numbers WHERE id = '0004'")).scalar() == "agent"
    _run(engine, command.downgrade, "0044")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('0005', '+541152630005', '', 'anura', '2026-11-02', '2026-11-02')"))
        assert conn.execute(sa.text("SELECT answer_mode FROM phone_numbers WHERE id = '0005'")).scalar() == "team"
