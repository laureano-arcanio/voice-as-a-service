"""Migracion 0035 (secretos del cliente y credenciales, docs/features/HERRAMIENTAS.md): ida y vuelta en SQLite y el
esquema de client_secrets y credentials coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = ("client_secrets", "credentials")


def test_0035_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0035")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(f"'{t}'" in repr(d) or f"table_name='{t}'" in repr(d) for t in TABLES)] == []
    _run(engine, command.downgrade, "0034")
    assert not set(TABLES) & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0035")
