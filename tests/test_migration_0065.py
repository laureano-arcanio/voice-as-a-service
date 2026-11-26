"""Migración 0065: tablas de casos de prueba y corridas, con una sola corrida activa por agente (ida y vuelta)."""
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parent.parent


def _run(engine, fn, revision):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        fn(cfg, revision)


def _base(engine):
    _run(engine, command.upgrade, "0064")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('t', 'T', '', '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c', 'C', 'c', 't', 1, '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO agents (id, client_id, name, slug, description, version, definition, "
                             "created_at, updated_at) VALUES ('a', 'c', 'A', 'a', '', 1, '{}', "
                             "'2026-01-01', '2026-01-01')"))


def _run_row(conn, rid, status, agent_id="a"):
    conn.execute(sa.text(
        "INSERT INTO agent_test_runs (id, client_id, agent_id, status, repetitions, variants, cases, done, total, "
        "input_tokens, output_tokens, created_at) VALUES (:id, 'c', :agent, :status, 5, '[]', '[]', 0, 0, 0, 0, "
        "'2026-01-01')"), {"id": rid, "agent": agent_id, "status": status})


def test_0065_crea_las_tablas_y_el_indice_parcial(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _base(engine)
    _run(engine, command.upgrade, "0065")

    tables = set(sa.inspect(engine).get_table_names())
    assert {"agent_test_cases", "agent_test_runs"} <= tables
    index = {i["name"]: i for i in sa.inspect(engine).get_indexes("agent_test_runs")}
    assert index["uq_agent_test_runs_active"]["unique"]

    # Dos corridas activas del mismo agente no entran; una terminada no molesta.
    with engine.begin() as conn:
        _run_row(conn, "r1", "queued")
    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        _run_row(conn, "r2", "running")
    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE agent_test_runs SET status = 'done' WHERE id = 'r1'"))
        _run_row(conn, "r3", "running")

    # Un caso con su snapshot.
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO agent_test_cases (id, client_id, agent_id, name, channel, snapshot, tool_results, checks, "
            "known_failure, created_at, updated_at) VALUES ('case', 'c', 'a', 'Caso', 'voice', :snap, '[]', '[]', 0, "
            "'2026-01-01', '2026-01-01')"), {"snap": '{"messages": [], "user_message": "hola"}'})

    # Ida y vuelta.
    _run(engine, command.downgrade, "0064")
    assert not {"agent_test_cases", "agent_test_runs"} & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0065")
    assert {"agent_test_cases", "agent_test_runs"} <= set(sa.inspect(engine).get_table_names())
