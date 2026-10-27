"""Migracion 0032 (herramientas del cliente, docs/TOOLS_PLAN.md): ida y vuelta en SQLite, el esquema de tools,
agent_secrets y tiers coincide con el modelo, y los defaults por plan."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("tools", "agent_secrets", "tiers")


def test_0032_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0031")
    with engine.begin() as conn:
        for name in ("Free", "Mostrador", "Sucursal", "Central", "Interno"):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, campaign_channels, created_at, updated_at) "
                                 "VALUES (:n, :n, '', '[]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"n": name})
    _run(engine, command.upgrade, "0032")
    with engine.connect() as conn:
        rows = {r[0]: tuple(r[1:]) for r in conn.execute(sa.text("SELECT name, max_tools, code_tools FROM tiers"))}
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(f"'{t}'" in repr(d) or f"table_name='{t}'" in repr(d) for t in TABLES)
            and "'white_label'" not in repr(d) and "'advanced_reports'" not in repr(d)
            and "'internal'" not in repr(d)] == []      # 0034, 0036 y 0037
    assert rows == {"Free": (0, 0), "Mostrador": (0, 0), "Sucursal": (10, 0), "Central": (None, 1), "Interno": (None, 1)}
    _run(engine, command.downgrade, "0031")
    inspector = sa.inspect(engine)
    assert "tools" not in inspector.get_table_names() and "agent_secrets" not in inspector.get_table_names()
    assert "max_tools" not in {c["name"] for c in inspector.get_columns("tiers")}
    _run(engine, command.upgrade, "0032")
