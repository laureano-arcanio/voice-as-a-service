"""Migracion 0020 (resumen por email de cada llamada): ida y vuelta en SQLite y el esquema migrado
coincide con el modelo."""
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def test_0020_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0020")
    assert {"call_emails", "call_emails_to"} <= _columns(engine, "clients")
    assert {"summary_email", "summary_email_attempts"} <= _columns(engine, "call_logs")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    # call_logs.room es de la 0021; user_id, answered_by, opted_out_confirmed y direct_recording_notice, de la 0039;
    # clients.industry y website, de la 0044.
    later = ("'room'", "'user_id'", "'answered_by'", "'opted_out_confirmed'", "ix_call_logs_user_id",
             "'direct_recording_notice'", "Column('industry',", "Column('website',")
    assert [d for d in diff if ("'clients'" in repr(d) or "call_logs" in repr(d))
            and not any(c in repr(d) for c in later)] == []

    _run(engine, command.downgrade, "0019")
    assert "call_emails" not in _columns(engine, "clients")
    assert "summary_email" not in _columns(engine, "call_logs")
    _run(engine, command.upgrade, "0020")
