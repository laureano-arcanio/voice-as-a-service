"""Migracion 0038 (WhatsApp con la app de Meta del cliente, docs/ARQUITECTURA.md): ida y vuelta
en SQLite, el esquema de wa_accounts coincide con el modelo y la clave del webhook es unica."""
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

NEW = {"app_secret", "verify_token", "webhook_key"}


def test_0038_upgrade_downgrade_upgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0038")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert [d for d in diff if "wa_accounts" in repr(d)] == []
    cols = {c["name"] for c in sa.inspect(engine).get_columns("wa_accounts")}
    assert cols >= NEW
    idx = {i["name"]: i for i in sa.inspect(engine).get_indexes("wa_accounts")}
    assert idx["ix_wa_accounts_webhook_key"]["unique"]
    _run(engine, command.downgrade, "0037")
    assert not (NEW & {c["name"] for c in sa.inspect(engine).get_columns("wa_accounts")})
    _run(engine, command.upgrade, "0038")


def test_0038_clave_unica(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0038")
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        for i in range(2):
            conn.execute(sa.text("INSERT INTO wa_accounts (id, client_id, agent_id, phone_number_id, waba_id, "
                                 "display_phone_number, name, active, status, source, webhook_key, created_at, "
                                 "updated_at) VALUES (:id, 'c', 'a', :pnid, 'w', '+1', '', true, 'connected', "
                                 "'own_app', 'misma', '2026-10-27', '2026-10-27')"), {"id": f"w{i}", "pnid": str(i)})
