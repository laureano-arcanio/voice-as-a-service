"""Migracion 0005 (WhatsApp fase 2 y users.session_version): ida y vuelta en SQLite, y
que el esquema migrado coincida con los modelos en las tablas que toca."""
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from app.db import Base

ROOT = Path(__file__).resolve().parent.parent
NEW_WA_COLUMNS = {"status", "status_reason", "status_changed_at", "quality_rating", "messaging_limit",
                  "business_id", "source", "pin_enc", "connected_by"}


def _run(engine, fn, revision):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        fn(cfg, revision)


def _columns(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_0005_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0004")
    with engine.begin() as conn:   # una fila previa: toma los defaults
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('t', 'T', '', '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c', 'C', 'c', 't', 1, '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO wa_accounts (id, client_id, agent_id, phone_number_id, waba_id, "
                             "display_phone_number, name, active, created_at, updated_at) "
                             "VALUES ('w', 'c', 'a', '1', '2', '+1', '', 1, '2026-01-01', '2026-01-01')"))

    _run(engine, command.upgrade, "0005")
    assert NEW_WA_COLUMNS <= _columns(engine, "wa_accounts") and "session_version" in _columns(engine, "users")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT status, source FROM wa_accounts")).one() == ("connected", "manual")
    insp = sa.inspect(engine)
    assert "ix_wa_accounts_waba_id" in {i["name"] for i in insp.get_indexes("wa_accounts")}
    assert "fk_wa_accounts_connected_by_users" in {fk["name"] for fk in insp.get_foreign_keys("wa_accounts")}

    # Sin diferencias con los modelos en las tablas de la migracion.
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    touched = [d for d in diff if "wa_accounts" in repr(d) or "'users'" in repr(d)]
    assert touched == []

    _run(engine, command.downgrade, "0004")
    assert not (NEW_WA_COLUMNS & _columns(engine, "wa_accounts"))
    assert "session_version" not in _columns(engine, "users")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT id FROM wa_accounts")).scalar() == "w"

    _run(engine, command.upgrade, "head")
    assert NEW_WA_COLUMNS <= _columns(engine, "wa_accounts")
    engine.dispose()
