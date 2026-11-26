"""Migración 0066: las dos columnas nullable de una corrida (pedido de cancelación y resumen), ida y vuelta."""
from pathlib import Path

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
    _run(engine, command.upgrade, "0065")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('t', 'T', '', '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c', 'C', 'c', 't', 1, '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO agents (id, client_id, name, slug, description, version, definition, "
                             "created_at, updated_at) VALUES ('a', 'c', 'A', 'a', '', 1, '{}', "
                             "'2026-01-01', '2026-01-01')"))
        conn.execute(sa.text(
            "INSERT INTO agent_test_runs (id, client_id, agent_id, status, repetitions, variants, cases, done, "
            "total, input_tokens, output_tokens, created_at) VALUES ('r1', 'c', 'a', 'done', 5, '[]', '[]', 0, 0, "
            "0, 0, '2026-01-01')"))


def test_0066_agrega_las_columnas_nullable_sin_backfill(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _base(engine)
    _run(engine, command.upgrade, "0066")

    cols = {c["name"]: c for c in sa.inspect(engine).get_columns("agent_test_runs")}
    assert cols["cancel_requested_at"]["nullable"] and cols["summary"]["nullable"]

    # La corrida que ya estaba queda sin las dos.
    with engine.begin() as conn:
        row = conn.execute(sa.text("SELECT cancel_requested_at, summary FROM agent_test_runs WHERE id = 'r1'")).one()
        assert row == (None, None)
        conn.execute(sa.text("UPDATE agent_test_runs SET status = 'cancelled', cancel_requested_at = '2026-01-02', "
                             "summary = '[{\"case_id\": \"c1\", \"variants\": []}]' WHERE id = 'r1'"))

    _run(engine, command.downgrade, "0065")
    assert "cancel_requested_at" not in {c["name"] for c in sa.inspect(engine).get_columns("agent_test_runs")}
    assert "summary" not in {c["name"] for c in sa.inspect(engine).get_columns("agent_test_runs")}

    _run(engine, command.upgrade, "0066")
    cols = {c["name"] for c in sa.inspect(engine).get_columns("agent_test_runs")}
    assert {"cancel_requested_at", "summary"} <= cols
