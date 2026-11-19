"""Migracion 0062 (minutos unificados): ida y vuelta en SQLite y backfill de la bolsa por el mayor de los
dos sentidos (NULL si alguno era ilimitado)."""
import sqlalchemy as sa
from alembic import command

from .test_migration_0005 import _run


def test_0062_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0061")
    with engine.begin() as conn:
        for name, inbound, outbound in (("Mostrador", 300, 300), ("Free", 20, 0), ("Interno", None, None)):
            conn.execute(sa.text("INSERT INTO tiers (id, name, description, inbound_minutes, outbound_minutes, "
                                 "campaign_channels, created_at, updated_at) "
                                 "VALUES (:n, :n, '', :i, :o, '[]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                         {"n": name, "i": inbound, "o": outbound})
    _run(engine, command.upgrade, "0062")
    with engine.connect() as conn:
        rows = {name: (call, unified) for name, call, unified in
                conn.execute(sa.text("SELECT name, call_minutes, unified_minutes FROM tiers")).all()}
    assert rows == {"Mostrador": (300, 1), "Free": (20, 1), "Interno": (None, 1)}
    _run(engine, command.downgrade, "0061")
    columns = {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
    assert "call_minutes" not in columns and "unified_minutes" not in columns
    _run(engine, command.upgrade, "0062")
    assert {"call_minutes", "unified_minutes"} <= {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
