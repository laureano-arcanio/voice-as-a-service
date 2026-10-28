"""Migracion 0033 (un solo motor, AGENTS.md): borra apps, app_links, app_job_runs y wa_operators,
archiva los agentes con motor assistant, crea tool_versions con la revision vigente de cada herramienta, y la
ida y vuelta en SQLite. El esquema de tool_versions coincide con el modelo."""
import json

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

DROPPED = ("apps", "app_links", "app_job_runs", "wa_operators")
NOW = "2026-10-20 10:00:00"


def _agent(conn, agent_id: str, definition: dict, archived_at=None) -> None:
    conn.execute(sa.text("INSERT INTO agents (id, client_id, name, slug, version, definition, archived_at, "
                         "created_at, updated_at) VALUES (:id, 'c', :id, :id, 1, :d, :a, :t, :t)"),
                 {"id": agent_id, "d": json.dumps(definition), "a": archived_at, "t": NOW})


def test_0033_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0032")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, campaign_channels, created_at, updated_at) "
                             "VALUES ('t', 'T', '', '[]', :t, :t)"), {"t": NOW})
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c', 'C', 'c', 't', 1, :t, :t)"), {"t": NOW})
        _agent(conn, "asistente", {"engine": "assistant"})
        _agent(conn, "viejo", {"engine": "assistant"}, archived_at="2026-01-01 00:00:00")
        _agent(conn, "clasico", {"engine": "classic"})
        _agent(conn, "sin_motor", {})
        conn.execute(sa.text("INSERT INTO tools (id, client_id, slug, type, definition, revision, created_at, "
                             "updated_at) VALUES ('h', 'c', 'consultar', 'http', :d, 3, :t, :t)"),
                     {"d": json.dumps({"description": "x"}), "t": NOW})
        conn.execute(sa.text("INSERT INTO apps (id, slug, name, client_id, base_url, token_enc, version, manifest, "
                             "created_at, updated_at) VALUES ('a', 'gym', 'Gym', 'c', 'http://x', 'x', '1', '{}', "
                             ":t, :t)"), {"t": NOW})

    _run(engine, command.upgrade, "0033")
    tables = set(sa.inspect(engine).get_table_names())
    assert not set(DROPPED) & tables and "tool_versions" in tables
    with engine.connect() as conn:
        archived = dict(conn.execute(sa.text("SELECT id, archived_at FROM agents")).all())
        versions = conn.execute(sa.text("SELECT tool_id, revision, type, definition FROM tool_versions")).all()
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # Los del motor assistant quedan archivados (el que ya lo estaba conserva su fecha); el resto, no.
    assert archived["asistente"] is not None and str(archived["viejo"]).startswith("2026-01-01")
    assert archived["clasico"] is None and archived["sin_motor"] is None
    assert [(v.tool_id, v.revision, v.type, json.loads(v.definition)) for v in versions] == [
        ("h", 3, "http", {"description": "x"})]
    assert [d for d in diff if "tool_versions" in repr(d)] == []
    # Las tablas quitadas tampoco estan en los modelos.
    assert not set(DROPPED) & set(Base.metadata.tables)

    _run(engine, command.downgrade, "0032")
    tables = set(sa.inspect(engine).get_table_names())
    assert set(DROPPED) <= tables and "tool_versions" not in tables
    _run(engine, command.upgrade, "0033")
    assert "tool_versions" in sa.inspect(engine).get_table_names()
    engine.dispose()
