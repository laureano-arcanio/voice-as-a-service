"""Migracion 0039 (llamadas directas, docs/LLAMADAS_DIRECTAS_PLAN.md): ida y vuelta en SQLite, el esquema
coincide con el modelo, los numeros existentes quedan con el agente y los tiers salvo el Free con
direct_calls."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

OURS = ("user_id", "answered_by", "opted_out_confirmed", "answer_mode", "ring_first", "ring_seconds", "schedule",
        "team_fallback", "phone_number_members", "user_presence", "call_rings", "direct_calls",
        "direct_recording_notice")


def _ours(d) -> bool:
    text = repr(d)
    return any(f"'{name}'" in text for name in OURS)


def test_0039_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0038")
    with engine.begin() as conn:
        for i, (name, price) in enumerate((("Free", 0), ("Mostrador", 29000), ("Interno", None))):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, price_ars, public, sort, created_at, "
                                 "updated_at) VALUES (:id, :name, '', :price, false, 0, '2026-10-27', '2026-10-27')"),
                         {"id": f"t{i}", "name": name, "price": price})
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n1', '+541152630861', '', 'anura', '2026-10-27', '2026-10-27')"))
    _run(engine, command.upgrade, "0039")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        tiers = dict(conn.execute(sa.text("SELECT name, direct_calls FROM tiers")).all())
        number = conn.execute(sa.text("SELECT answer_mode, ring_first, ring_seconds, team_fallback, "
                                      "team_fallback_message FROM phone_numbers")).one()
    assert [d for d in diff if _ours(d)] == []
    assert tiers == {"Free": False, "Mostrador": True, "Interno": True}
    assert tuple(number) == ("agent", "phone", 20, "voicemail", "")
    # Los numeros nuevos van al equipo.
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO phone_numbers (id, e164, label, provider, created_at, updated_at) "
                             "VALUES ('n2', '+541152630862', '', 'anura', '2026-10-27', '2026-10-27')"))
        assert conn.execute(sa.text("SELECT answer_mode FROM phone_numbers WHERE id = 'n2'")).scalar() == "team"
    _run(engine, command.downgrade, "0038")
    insp = sa.inspect(engine)
    assert "direct_calls" not in {c["name"] for c in insp.get_columns("tiers")}
    assert "user_id" not in {c["name"] for c in insp.get_columns("call_logs")}
    assert not {"call_rings", "user_presence", "phone_number_members"} & set(insp.get_table_names())
    _run(engine, command.upgrade, "0039")
