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
    # La 0042 quita team_members.whatsapp (y su unique) y handoff_areas.wa_reply_minutes.
    diff = [d for d in diff if not any(c in repr(d) for c in ("'whatsapp'", "wa_reply_minutes", "uq_team_members_client_whatsapp"))]
    # La 0048 agrega el aviso por WhatsApp y el ruteo entre areas (no_answer_member_id, la 0052).
    later = ("whatsapp_notify", "after_hours_area_id", "no_answer_area_id", "no_answer_member_id", "'delivery'", "fk_handoff_areas",
             "handoff_area_id", "fk_wa_threads_handoff")
    diff = [d for d in diff if not any(c in repr(d) for c in later)]
    # La 0050, la 0051 y la 0053 agregan columnas a phone_numbers (last_member_id y team_fallback_member_id ->
    # team_members, opciones del equipo).
    diff = [d for d in diff if "phone_numbers" not in repr(d)]
    assert [d for d in diff if any(t in repr(d) for t in TABLES) or "max_team_members" in repr(d)] == []

    _run(engine, command.downgrade, "0022")
    inspector = sa.inspect(engine)
    assert not TABLES & set(inspector.get_table_names())
    assert "max_team_members" not in {c["name"] for c in inspector.get_columns("tiers")}
    _run(engine, command.upgrade, "0023")
