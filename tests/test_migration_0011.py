"""Migracion 0011 (ajustes de limites por cliente): ida y vuelta en SQLite, el esquema migrado
coincide con el modelo y borrar el cliente borra sus ajustes."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def test_0011_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0010")
    assert "client_limit_adjustments" not in sa.inspect(engine).get_table_names()

    _run(engine, command.upgrade, "0011")
    inspector = sa.inspect(engine)
    assert "client_limit_adjustments" in inspector.get_table_names()
    assert {i["name"] for i in inspector.get_indexes("client_limit_adjustments")} == {"ix_limit_adj_client_field"}
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "client_limit_adjustments" in repr(d)] == []

    _run(engine, command.downgrade, "0010")
    assert "client_limit_adjustments" not in sa.inspect(engine).get_table_names()
    _run(engine, command.upgrade, "0011")
