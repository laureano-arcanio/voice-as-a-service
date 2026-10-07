"""Migracion 0008 (campañas de WhatsApp): ida y vuelta en SQLite, y que el esquema migrado
coincida con los modelos en las tablas nuevas."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

TABLES = {"wa_campaigns", "wa_campaign_recipients", "wa_optouts"}


def test_0008_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0008")
    assert TABLES <= set(sa.inspect(engine).get_table_names())
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if any(t in repr(d) for t in TABLES)] == []

    _run(engine, command.downgrade, "0007")
    assert not TABLES & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0008")
