"""Migracion 0009 (API de inferencia): ida y vuelta en SQLite, el esquema migrado coincide con los
modelos y los tiers y keys que ya existian quedan cerrados (sin inferencia) salvo el ilimitado."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _columns, _run

TIER_COLUMNS = {"api_llm_input_tokens", "api_llm_output_tokens", "api_tts_minutes", "api_stt_minutes",
                "api_rate_limit"}


def test_0009_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0008")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, inbound_minutes, created_at, updated_at) "
                             "VALUES ('pyme', 'Pyme', '', 100, '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('int', 'Interno', '', '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c', 'C', 'c', 'pyme', 1, '2026-01-01', '2026-01-01')"))
        conn.execute(sa.text("INSERT INTO api_keys (id, client_id, name, prefix, key_hash, created_at) "
                             "VALUES ('k', 'c', 'CRM', 'vaas_abc', 'h', '2026-01-01')"))

    _run(engine, command.upgrade, "0009")
    assert TIER_COLUMNS <= _columns(engine, "tiers") and "scopes" in _columns(engine, "api_keys")
    assert "api_usage_daily" in sa.inspect(engine).get_table_names()
    with engine.connect() as conn:
        tiers = {r[0]: r[1:] for r in conn.execute(sa.text(
            "SELECT id, api_llm_input_tokens, api_llm_output_tokens, api_tts_minutes, api_stt_minutes, api_rate_limit "
            "FROM tiers"))}
        scopes = conn.execute(sa.text("SELECT scopes FROM api_keys")).scalar_one()
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert tiers["pyme"] == (0, 0, 0, 0, 60)          # con limites: sin inferencia hasta que se la den
    assert tiers["int"] == (None,) * 5                  # sin ningun limite (Atentina): ilimitado
    assert scopes == "calls"
    # Lo de 0010 (llamadas por hora, dia y mes) todavia no esta en este esquema.
    diff = [d for d in diff if not any(t in repr(d) for t in ("max_calls_per", "ck_tiers_calls"))]
    assert [d for d in diff if any(t in repr(d) for t in ("api_usage_daily", "api_keys", "tiers"))] == []

    _run(engine, command.downgrade, "0008")
    assert not TIER_COLUMNS & _columns(engine, "tiers") and "scopes" not in _columns(engine, "api_keys")
    assert "api_usage_daily" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0009")
