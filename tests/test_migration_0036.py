"""Migracion 0036 (reportes, docs/features/REPORTES.md): ida y vuelta en SQLite, el esquema de tool_runs,
wa_account_status_log y las columnas nuevas coincide con el modelo, y advanced_reports queda en los planes pagos
e Interno (no en el Free)."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("tool_runs", "wa_account_status_log")
COLUMNS = ("advanced_reports", "outcome", "goal", "conversion", "llm_input_tokens", "llm_output_tokens")


def _ours(d) -> bool:
    text = repr(d)
    return any(f"'{t}'" in text or f"table_name='{t}'" in text for t in TABLES) or any(
        f"'{c}'" in text for c in COLUMNS)


def test_0036_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0035")
    with engine.begin() as conn:
        for i, (name, price) in enumerate((("Free", 0), ("Mostrador", 29000), ("Interno", None))):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, price_ars, public, sort, created_at, "
                                 "updated_at) VALUES (:id, :name, '', :price, false, 0, '2026-10-27', '2026-10-27')"),
                         {"id": f"t{i}", "name": name, "price": price})
    _run(engine, command.upgrade, "0036")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        tiers = dict(conn.execute(sa.text("SELECT name, advanced_reports FROM tiers")).all())
    assert [d for d in diff if _ours(d)] == []
    assert tiers == {"Free": False, "Mostrador": True, "Interno": True}
    _run(engine, command.downgrade, "0035")
    assert not set(TABLES) & set(sa.inspect(engine).get_table_names())
    assert "outcome" not in {c["name"] for c in sa.inspect(engine).get_columns("conversations")}
    _run(engine, command.upgrade, "0036")
