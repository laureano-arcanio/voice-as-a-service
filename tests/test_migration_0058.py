"""Migracion 0058: ajuste del contenido de la API en clients (true/30 en los existentes y en los nuevos) y
api_requests.content_bytes (NULL)."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def _cols(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def _client(conn, cid):
    conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                         "VALUES (:id, :id, :id, 't', 1, '2026-01-01', '2026-01-01')"), {"id": cid})


def test_0058_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0057")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('t', 'T', '', '2026-01-01', '2026-01-01')"))
        _client(conn, "viejo")
        conn.execute(sa.text("INSERT INTO api_requests (id, client_id, created_at, kind, status) "
                             "VALUES ('r', 'viejo', '2026-01-01', 'llm', 'ok')"))
    _run(engine, command.upgrade, "0058")
    with engine.begin() as conn:
        _client(conn, "nuevo")
        rows = conn.execute(sa.text("SELECT id, store_api_content, api_content_retention_days FROM clients "
                                    "ORDER BY id")).all()
        assert [(r[0], bool(r[1]), r[2]) for r in rows] == [("nuevo", True, 30), ("viejo", True, 30)]
        assert conn.execute(sa.text("SELECT content_bytes FROM api_requests")).scalar_one() is None
    _run(engine, command.downgrade, "0057")
    assert not {"store_api_content", "api_content_retention_days"} & _cols(engine, "clients")
    assert "content_bytes" not in _cols(engine, "api_requests")
    _run(engine, command.upgrade, "0058")
    assert "content_bytes" in _cols(engine, "api_requests")
