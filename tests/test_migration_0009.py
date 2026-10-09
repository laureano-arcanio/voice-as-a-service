"""Migracion 0009 (produccion multi-cliente): ida y vuelta en SQLite con filas previas, que el
esquema migrado coincida con los modelos, y el chequeo de numeros con agente de otro cliente.
Con TEST_DB_DSN (PostgreSQL 15+) prueba ademas la FK compuesta de phone_numbers."""
import os

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _columns, _run

NEW_COLUMNS = {
    "tiers": {"max_call_duration_seconds", "retention_days"},
    "clients": {"retention_days"},
    "wa_messages": {"body", "attempts", "claimed_at", "processed_at"},
    "conversations": {"version", "purged_at"},
    "call_logs": {"idempotency_key"},
    "wa_campaign_recipients": {"claimed_at"},
}
TS = "'2026-01-01'"


def _seed(conn, mixed=False):
    """Una fila previa por tabla tocada. mixed: el numero de c1 ruteado a un agente de c2."""
    conn.execute(sa.text(f"INSERT INTO tiers (id, name, description, created_at, updated_at) "
                         f"VALUES ('t', 'T', '', {TS}, {TS})"))
    for c in ("c1", "c2"):
        conn.execute(sa.text(f"INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             f"VALUES ('{c}', '{c}', '{c}', 't', true, {TS}, {TS})"))
        conn.execute(sa.text(f"INSERT INTO agents (id, client_id, name, slug, description, version, definition, "
                             f"created_at, updated_at) VALUES ('a-{c}', '{c}', 'A', 'a', '', 1, '{{}}', {TS}, {TS})"))
    agent = "a-c2" if mixed else "a-c1"
    conn.execute(sa.text(f"INSERT INTO phone_numbers (id, client_id, e164, label, provider, agent_id, "
                         f"created_at, updated_at) VALUES ('p', 'c1', '+5493510000000', '', 'anura', '{agent}', "
                         f"{TS}, {TS})"))
    conn.execute(sa.text(f"INSERT INTO conversations (id, client_id, agent_id, channel, status, fields, messages, "
                         f"created_at, updated_at) VALUES ('v', 'c1', 'a-c1', 'voice', 'active', '{{}}', '[]', "
                         f"{TS}, {TS})"))
    conn.execute(sa.text(f"INSERT INTO call_logs (conversation_id, client_id, mode, status, ended_reason, error, "
                         f"duration_seconds, created_at) VALUES ('v', 'c1', 'entrante', 'finalizada', '', '', 0, {TS})"))
    conn.execute(sa.text(f"INSERT INTO wa_messages (id, wamid, direction, wa_id, type, status, created_at, "
                         f"updated_at) VALUES ('m', 'wamid.1', 'in', '549351', 'text', 'answered', {TS}, {TS})"))


def test_0009_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0008")
    with engine.begin() as conn:
        _seed(conn)

    _run(engine, command.upgrade, "0009")
    for table, cols in NEW_COLUMNS.items():
        assert cols <= _columns(engine, table), table
    with engine.connect() as conn:   # las filas previas toman los defaults
        assert conn.execute(sa.text("SELECT attempts, body FROM wa_messages")).one() == (0, None)
        assert conn.execute(sa.text("SELECT version, purged_at FROM conversations")).one() == (0, None)
    insp = sa.inspect(engine)
    assert "ix_wa_messages_direction_status_created" in {i["name"] for i in insp.get_indexes("wa_messages")}
    assert "uq_agents_id_client" in {u["name"] for u in insp.get_unique_constraints("agents")}
    assert "uq_call_logs_client_idempotency" in {u["name"] for u in insp.get_unique_constraints("call_logs")}
    assert {"ck_tiers_max_call_duration", "ck_tiers_retention"} <= {c["name"] for c in insp.get_check_constraints("tiers")}

    # En head, el esquema migrado es el de los modelos.
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # Salvo la FK phone_numbers.client_id: 0003 la pasa a SET NULL solo en PostgreSQL.
    assert [d for d in diff if not (isinstance(d, tuple) and d[0] in ("remove_fk", "add_fk")
                                    and d[1].parent.name == "phone_numbers")] == []

    # Los CHECK > 0 se aplican.
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.execute(sa.text("UPDATE tiers SET retention_days = 0"))
    # Idempotency-Key unica por cliente (NULL no choca).
    with engine.begin() as conn:
        conn.execute(sa.text(f"INSERT INTO conversations (id, client_id, channel, status, fields, messages, "
                             f"created_at, updated_at) VALUES ('v2', 'c1', 'voice', 'active', '{{}}', '[]', {TS}, {TS})"))
        conn.execute(sa.text(f"INSERT INTO call_logs (conversation_id, client_id, mode, status, ended_reason, error, "
                             f"duration_seconds, created_at) VALUES ('v2', 'c1', 'saliente', 'pendiente', '', '', 0, {TS})"))
        conn.execute(sa.text("UPDATE call_logs SET idempotency_key = 'k1' WHERE conversation_id = 'v'"))
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.execute(sa.text("UPDATE call_logs SET idempotency_key = 'k1' WHERE conversation_id = 'v2'"))

    _run(engine, command.downgrade, "0008")
    for table, cols in NEW_COLUMNS.items():
        assert not (cols & _columns(engine, table)), table
    assert "uq_agents_id_client" not in {u["name"] for u in sa.inspect(engine).get_unique_constraints("agents")}
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT agent_id FROM phone_numbers")).scalar() == "a-c1"
        assert conn.execute(sa.text("SELECT count(*) FROM call_logs")).scalar() == 2

    _run(engine, command.upgrade, "head")
    assert NEW_COLUMNS["wa_messages"] <= _columns(engine, "wa_messages")
    engine.dispose()


def test_0009_rejects_number_routed_to_another_clients_agent(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0008")
    with engine.begin() as conn:
        _seed(conn, mixed=True)
    with pytest.raises(RuntimeError, match=r"\+5493510000000"):
        _run(engine, command.upgrade, "0009")
    # No quedo a medias: sigue en 0008 y se puede corregir y reintentar.
    assert "retention_days" not in _columns(engine, "tiers")
    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE phone_numbers SET agent_id = NULL"))
    _run(engine, command.upgrade, "0009")
    assert "retention_days" in _columns(engine, "tiers")
    engine.dispose()


@pytest.mark.skipif(not (os.getenv("TEST_DB_DSN") or "").startswith("postgresql"),
                    reason="FK compuesta: solo PostgreSQL (TEST_DB_DSN)")
def test_0009_postgres_composite_fk():
    """Base de prueba descartable: se borra el esquema public entero."""
    engine = sa.create_engine(os.environ["TEST_DB_DSN"])
    with engine.begin() as conn:
        conn.execute(sa.text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    _run(engine, command.upgrade, "0008")
    with engine.begin() as conn:
        _seed(conn)
    _run(engine, command.upgrade, "0009")
    fks = {fk["name"]: fk for fk in sa.inspect(engine).get_foreign_keys("phone_numbers")}
    assert fks["fk_phone_numbers_agent_client"]["constrained_columns"] == ["agent_id", "client_id"]

    # El numero de c1 no puede apuntar a un agente de c2.
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.execute(sa.text("UPDATE phone_numbers SET agent_id = 'a-c2'"))
    # Ni pasar a otro cliente sin soltar el agente.
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.execute(sa.text("UPDATE phone_numbers SET client_id = 'c2'"))
    # Borrar el agente deja el numero con su cliente y sin agente.
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM conversations"))
        conn.execute(sa.text("DELETE FROM agents WHERE id = 'a-c1'"))
        assert conn.execute(sa.text("SELECT client_id, agent_id FROM phone_numbers")).one() == ("c1", None)

    _run(engine, command.downgrade, "0008")
    assert "fk_phone_numbers_agent_client" not in {
        fk["name"] for fk in sa.inspect(engine).get_foreign_keys("phone_numbers")}
    _run(engine, command.upgrade, "head")
    engine.dispose()
