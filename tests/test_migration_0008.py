"""Migracion 0008 (campañas de WhatsApp): ida y vuelta en SQLite. Sus tablas las reemplazo la
0017 (campaigns, campaign_contacts, contact_optouts: tests/test_migration_0017.py), asi que ya
no se compara con los modelos."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run

TABLES = {"wa_campaigns", "wa_campaign_recipients", "wa_optouts"}


def test_0008_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0008")
    assert TABLES <= set(sa.inspect(engine).get_table_names())

    _run(engine, command.downgrade, "0007")
    assert not TABLES & set(sa.inspect(engine).get_table_names())
    _run(engine, command.upgrade, "0008")
