"""Migracion 0023 (equipo, areas de derivacion y eventos): ida y vuelta en SQLite y el esquema
migrado coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = {"team_members", "handoff_areas", "handoff_area_members", "events"}


def test_0023_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0023")
    inspector = sa.inspect(engine)
    assert TABLES <= set(inspector.get_table_names())
    assert "max_team_members" in {c["name"] for c in inspector.get_columns("tiers")}
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # handoff_legs (0024) y phone_number_members (0039) referencian a estas tablas: no son parte de la 0023.
    diff = [d for d in diff if "handoff_legs" not in repr(d) and "phone_number_members" not in repr(d)]
    assert [d for d in diff if any(t in repr(d) for t in TABLES) or "max_team_members" in repr(d)] == []

    _run(engine, command.downgrade, "0022")
    inspector = sa.inspect(engine)
    assert not TABLES & set(inspector.get_table_names())
    assert "max_team_members" not in {c["name"] for c in inspector.get_columns("tiers")}
    _run(engine, command.upgrade, "0023")
