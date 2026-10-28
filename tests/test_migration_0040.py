"""Migracion 0040 (contactos con una nota en lugar de etiquetas y datos): ida y vuelta en SQLite, el esquema coincide
con el modelo y los datos que habia pasan a la nota como lineas `clave: valor`."""
import json

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run


def _contact(conn, id, phone, attributes, tags):
    conn.execute(sa.text(
        "INSERT INTO contacts (id, created_at, updated_at, client_id, phone, attributes, tags, source) "
        "VALUES (:id, '2026-10-27', '2026-10-27', 'c1', :phone, :attributes, :tags, 'manual')"),
        {"id": id, "phone": phone, "attributes": json.dumps(attributes), "tags": json.dumps(tags)})


def test_0040_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0039")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tiers (id, name, description, price_ars, public, sort, created_at, "
                             "updated_at) VALUES ('t1', 'Free', '', 0, true, 0, '2026-10-27', '2026-10-27')"))
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, created_at, updated_at) "
                             "VALUES ('c1', 'Acme', 'acme', 't1', '2026-10-27', '2026-10-27')"))
        _contact(conn, "k1", "+5493515551001", {"deuda": 15000, "vence": "2026-11-01"}, ["mora"])
        _contact(conn, "k2", "+5493515551002", {}, ["vip"])
    _run(engine, command.upgrade, "0040")
    with engine.connect() as conn:
        notes = dict(conn.execute(sa.text("SELECT id, notes FROM contacts")).all())
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert notes == {"k1": "deuda: 15000\nvence: 2026-11-01", "k2": None}
    assert [d for d in diff if "contacts" in repr(d) and "external_id" not in repr(d)] == []     # la 0041 lo quita
    cols = {c["name"] for c in sa.inspect(engine).get_columns("contacts")}
    assert "notes" in cols and not cols & {"tags", "attributes"}
    _run(engine, command.downgrade, "0039")
    cols = {c["name"] for c in sa.inspect(engine).get_columns("contacts")}
    assert {"tags", "attributes"} <= cols and "notes" not in cols
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT count(*) FROM contacts")).scalar() == 2
    _run(engine, command.upgrade, "0040")
