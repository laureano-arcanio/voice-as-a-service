"""Migracion 0037 (tiers.internal, docs/ADMIN_SOPORTE_PLAN.md): ida y vuelta en SQLite, el esquema coincide con el
modelo y solo el tier llamado Interno queda marcado."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def _ours(d) -> bool:
    return "'internal'" in repr(d)


def test_0037_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0036")
    with engine.begin() as conn:
        for i, (name, price) in enumerate((("Free", 0), ("Mostrador", 29000), ("Interno", None))):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, price_ars, public, sort, created_at, "
                                 "updated_at) VALUES (:id, :name, '', :price, false, 0, '2026-10-27', '2026-10-27')"),
                         {"id": f"t{i}", "name": name, "price": price})
    _run(engine, command.upgrade, "0037")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        tiers = dict(conn.execute(sa.text("SELECT name, internal FROM tiers")).all())
    assert [d for d in diff if _ours(d)] == []
    assert tiers == {"Free": False, "Mostrador": False, "Interno": True}
    _run(engine, command.downgrade, "0036")
    assert "internal" not in {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
    _run(engine, command.upgrade, "0037")
