"""Migracion 0010 (cantidad de llamadas por hora, dia y mes en los tiers): ida y vuelta en SQLite,
el esquema migrado coincide con los modelos y los tiers que ya existian quedan sin tope."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _columns, _run

COLUMNS = {"max_calls_per_hour", "max_calls_per_day", "max_calls_per_month"}
# Agregado despues (0012) que menciona a tiers: el modelo lo tiene y la base en 0010 no.
LATER_TIER_COLUMNS = ("'price_ars'", "'public'", "'sort'", "ck_tiers_price", "'subscriptions'", "'billing_payments'")


def test_0010_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0009")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, inbound_minutes, created_at, updated_at) "
                             "VALUES ('pyme', 'Pyme', '', 100, '2026-01-01', '2026-01-01')"))

    _run(engine, command.upgrade, "0010")
    assert COLUMNS <= _columns(engine, "tiers")
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT max_calls_per_hour, max_calls_per_day, max_calls_per_month FROM tiers")).one()
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert tuple(row) == (None, None, None)
    assert [d for d in diff if "tiers" in repr(d) and not any(c in repr(d) for c in LATER_TIER_COLUMNS)] == []

    _run(engine, command.downgrade, "0009")
    assert not COLUMNS & _columns(engine, "tiers")
    _run(engine, command.upgrade, "0010")
