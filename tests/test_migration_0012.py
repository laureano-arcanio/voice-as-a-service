"""Migracion 0012 (cobro de planes): ida y vuelta en SQLite y el esquema migrado coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("subscriptions", "billing_payments")


def test_0012_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0011")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, created_at, updated_at) "
                             "VALUES ('t1', 'Interno', '', '2026-10-01', '2026-10-01')"))

    _run(engine, command.upgrade, "0012")
    inspector = sa.inspect(engine)
    assert set(TABLES) <= set(inspector.get_table_names())
    assert {"price_ars", "public", "sort"} <= {c["name"] for c in inspector.get_columns("tiers")}
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT price_ars, public, sort FROM tiers")).one() == (None, 0, 0)
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # Las tablas nuevas y las columnas agregadas (las FK sin nombre de las tablas que recrea el
    # batch de SQLite aparecen como diferencia desde antes de esta migracion).
    touched = (*TABLES, "price_ars", "'public'", "'sort'", "suspended_at", "created_via", "legal_name", "tax_id",
               "tax_condition", "ck_tiers_price")
    assert [d for d in diff if d[0] != "remove_fk" and any(t in repr(d) for t in touched)] == []

    _run(engine, command.downgrade, "0011")
    assert not set(TABLES) & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0012")
