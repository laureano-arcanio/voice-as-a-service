"""Migracion 0042 (sin restos del puente de WhatsApp; slug demo_booking): ida y vuelta en SQLite y el
esquema coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("team_members", "handoff_areas", "wa_threads")


def _cols(engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def _slugs(engine) -> list[tuple[str, str]]:
    with engine.connect() as conn:
        return sorted(conn.execute(sa.text("SELECT client_id, slug FROM agents")).all())


def test_0042_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0041")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, public, sort, created_at, updated_at) "
                             "VALUES ('t1', 'Free', '', false, 0, '2026-10-28', '2026-10-28')"))
        for cid in ("c1", "c2"):
            conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                                 "VALUES (:id, :id, :id, 't1', 1, '2026-10-28', '2026-10-28')"), {"id": cid})
        # c1 solo tiene el viejo (se renombra); c2 tiene los dos (no se toca).
        for i, (cid, slug) in enumerate((("c1", "demo_booking_classic"), ("c2", "demo_booking_classic"),
                                         ("c2", "demo_booking"))):
            conn.execute(sa.text("INSERT INTO agents (id, client_id, slug, name, description, version, definition, "
                                 "created_at, updated_at) VALUES (:id, :cid, :slug, :slug, '', 1, '{}', "
                                 "'2026-10-28', '2026-10-28')"),
                         {"id": f"a{i}", "cid": cid, "slug": slug})
    assert "whatsapp" in _cols(engine, "team_members")

    _run(engine, command.upgrade, "0042")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(t in repr(d) for t in TABLES)] == []
    assert "whatsapp" not in _cols(engine, "team_members")
    assert "wa_reply_minutes" not in _cols(engine, "handoff_areas")
    assert "paused" not in _cols(engine, "wa_threads")
    assert _slugs(engine) == [("c1", "demo_booking"), ("c2", "demo_booking"), ("c2", "demo_booking_classic")]

    _run(engine, command.downgrade, "0041")
    assert "whatsapp" in _cols(engine, "team_members")
    assert "wa_reply_minutes" in _cols(engine, "handoff_areas")
    assert "paused" in _cols(engine, "wa_threads")
    assert _slugs(engine) == [("c1", "demo_booking_classic"), ("c2", "demo_booking"), ("c2", "demo_booking_classic")]
    _run(engine, command.upgrade, "0042")
