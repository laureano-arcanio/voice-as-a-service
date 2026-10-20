"""Migracion 0017 (agenda de contactos y campañas unificadas): los datos de WhatsApp sembrados en
0016 sobreviven al upgrade, el downgrade los devuelve, y el esquema coincide con los modelos."""
import json

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base

from .test_migration_0005 import _run

NEW_TABLES = {"contacts", "contact_optouts", "campaigns", "campaign_contacts", "campaign_callbacks"}
OLD_TABLES = {"wa_campaigns", "wa_campaign_recipients", "wa_optouts"}
TIER_COLUMNS = {"campaign_channels", "max_campaigns_per_month", "max_campaign_contacts",
                "max_campaign_concurrency", "max_contacts", "campaign_followup"}
T0 = "2026-10-01 10:00:00"


def _exec(conn, sql, **params):
    conn.execute(sa.text(sql), params)


def _seed(engine):
    """Datos de produccion en 0016: dos clientes, dos campañas de WhatsApp con destinatarios en
    todos los estados (uno repetido en otra campaña del mismo cliente y en otro cliente) y bajas."""
    with engine.begin() as conn:
        _exec(conn, "INSERT INTO tiers (id, name, description, created_at, updated_at) "
                    f"VALUES ('t', 'T', '', '{T0}', '{T0}')")
        for client in ("c1", "c2"):
            _exec(conn, "INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                        f"VALUES ('{client}', '{client}', '{client}', 't', 1, '{T0}', '{T0}')")
        _exec(conn, "INSERT INTO wa_accounts (id, client_id, agent_id, phone_number_id, waba_id, "
                    "display_phone_number, name, active, created_at, updated_at) "
                    f"VALUES ('w1', 'c1', 'a', '1', '2', '+1', '', 1, '{T0}', '{T0}'), "
                    f"('w2', 'c2', 'a', '3', '4', '+2', '', 1, '{T0}', '{T0}')")
        for cid, client, account, status in (("k1", "c1", "w1", "running"), ("k2", "c1", "w1", "done"),
                                             ("k3", "c2", "w2", "draft")):
            _exec(conn, "INSERT INTO wa_campaigns (id, client_id, account_id, agent_id, name, template_name, "
                        "template_language, template_category, template_body, template_params, status, "
                        "rate_per_minute, window_start, window_end, created_at, updated_at) "
                        f"VALUES ('{cid}', '{client}', '{account}', 'a', 'Camp {cid}', 'demo', 'es_AR', 'MARKETING', "
                        f"'Hola {{{{1}}}}', 1, '{status}', 30, 9, 20, '{T0}', '{T0}')")
        recipients = [
            ("r1", "k1", "5493515550001", "Ana", ["Ana"], "sent", "wamid.1", "2026-10-01 10:05:00", None),
            ("r2", "k1", "5493515550002", None, ["Beto"], "pending", None, None, None),
            ("r3", "k1", "5493515550003", "Cris", ["Cris"], "sending", None, None, None),
            ("r4", "k1", "5493515550004", None, ["Dani"], "failed", None, None, {"code": 131026, "message": "x"}),
            ("r5", "k1", "5493515550005", None, ["Eli"], "skipped", None, None, {"message": "baja"}),
            ("r6", "k2", "5493515550001", "Ana Maria", ["Ana"], "sent", "wamid.6", "2026-10-02 10:05:00", None),
            ("r7", "k3", "5493515550001", None, ["Otro cliente"], "pending", None, None, None),
        ]
        for i, (rid, cid, wa_id, name, params, status, wamid, sent_at, error) in enumerate(recipients):
            _exec(conn, "INSERT INTO wa_campaign_recipients (id, campaign_id, wa_id, name, params, status, error, "
                        "wamid, sent_at, replied_at, created_at) VALUES (:id, :cid, :wa, :name, :params, :status, "
                        ":error, :wamid, :sent, :replied, :created)",
                  id=rid, cid=cid, wa=wa_id, name=name, params=json.dumps(params), status=status,
                  error=json.dumps(error) if error else None, wamid=wamid, sent=sent_at,
                  replied=sent_at if rid == "r6" else None, created=f"2026-10-01 10:0{i}:00")
        _exec(conn, "INSERT INTO wa_optouts (client_id, wa_id, source, created_at) VALUES "
                    f"('c1', '5493515550009', 'keyword', '{T0}'), ('c2', '5493515550001', 'manual', '{T0}')")


def _diff(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    touched = NEW_TABLES | TIER_COLUMNS | {"call_logs"}
    # Lo de la 0018 (link para llamar) todavia no esta en este esquema.
    later = ("call_link", "max_call_links", "ck_tiers_call_links")
    return [d for d in diff if any(t in repr(d) for t in touched) and not any(t in repr(d) for t in later)]


def test_0017_upgrade_keeps_whatsapp_data(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0016")
    _seed(engine)
    _run(engine, command.upgrade, "0017")

    tables = set(sa.inspect(engine).get_table_names())
    assert NEW_TABLES <= tables and not OLD_TABLES & tables
    assert _diff(engine) == []
    with engine.connect() as conn:
        # Tiers: los existentes quedan con WhatsApp y sin topes.
        tier = conn.execute(sa.text("SELECT campaign_channels, max_contacts, max_campaigns_per_month, "
                                    "campaign_followup FROM tiers")).one()
        assert (json.loads(tier[0]), tier[1], tier[2], tier[3]) == (["whatsapp"], None, None, 0)

        # Campañas: mismo id y datos, channel whatsapp.
        rows = conn.execute(sa.text("SELECT id, channel, status, account_id, template_name, template_body, "
                                    "rate_per_minute, weekdays, concurrency FROM campaigns ORDER BY id")).all()
        assert [tuple(r) for r in rows] == [
            ("k1", "whatsapp", "running", "w1", "demo", "Hola {{1}}", 30, None, None),
            ("k2", "whatsapp", "done", "w1", "demo", "Hola {{1}}", 30, None, None),
            ("k3", "whatsapp", "draft", "w2", "demo", "Hola {{1}}", 30, None, None)]

        # Un contacto por (cliente, wa_id): el de Ana esta en dos campañas del mismo cliente y en otro cliente.
        contacts = conn.execute(sa.text("SELECT client_id, phone, name, source, archived_at FROM contacts "
                                        "ORDER BY client_id, phone")).all()
        assert [tuple(c) for c in contacts] == [
            ("c1", "+5493515550001", "Ana", "campaign", None), ("c1", "+5493515550002", None, "campaign", None),
            ("c1", "+5493515550003", "Cris", "campaign", None), ("c1", "+5493515550004", None, "campaign", None),
            ("c1", "+5493515550005", None, "campaign", None), ("c2", "+5493515550001", None, "campaign", None)]

        members = conn.execute(sa.text(
            "SELECT m.id, m.campaign_id, c.client_id, c.phone, m.status, m.result, m.vars, m.error, m.wamid, "
            "m.replied_at IS NOT NULL, m.attempts FROM campaign_contacts m JOIN contacts c ON c.id = m.contact_id "
            "ORDER BY m.id")).all()
        got = {r[0]: (r[1], r[2], r[3], r[4], r[5], json.loads(r[6]), json.loads(r[7]) if r[7] else None, r[8],
                      bool(r[9]), r[10]) for r in members}
        assert got == {
            "r1": ("k1", "c1", "+5493515550001", "done", "sent", {"params": ["Ana"], "nombre": "Ana"}, None,
                   "wamid.1", False, 0),
            "r2": ("k1", "c1", "+5493515550002", "pending", None, {"params": ["Beto"]}, None, None, False, 0),
            "r3": ("k1", "c1", "+5493515550003", "in_progress", None, {"params": ["Cris"], "nombre": "Cris"}, None,
                   None, False, 0),
            "r4": ("k1", "c1", "+5493515550004", "failed", None, {"params": ["Dani"]},
                   {"code": 131026, "message": "x"}, None, False, 0),
            "r5": ("k1", "c1", "+5493515550005", "skipped", None, {"params": ["Eli"]}, {"message": "baja"}, None,
                   False, 0),
            "r6": ("k2", "c1", "+5493515550001", "done", "sent", {"params": ["Ana"], "nombre": "Ana Maria"}, None,
                   "wamid.6", True, 0),
            "r7": ("k3", "c2", "+5493515550001", "pending", None, {"params": ["Otro cliente"]}, None, None, False, 0)}
        # r1 y r6 comparten contacto.
        ids = dict(conn.execute(sa.text("SELECT id, contact_id FROM campaign_contacts")).all())
        assert ids["r1"] == ids["r6"] and ids["r1"] != ids["r7"]

        optouts = conn.execute(sa.text("SELECT client_id, phone, channel, source FROM contact_optouts "
                                       "ORDER BY client_id")).all()
        assert [tuple(o) for o in optouts] == [("c1", "+5493515550009", "whatsapp", "keyword"),
                                               ("c2", "+5493515550001", "whatsapp", "manual")]

        call_columns = {c["name"] for c in sa.inspect(engine).get_columns("call_logs")}
        assert {"campaign_contact_id", "sip_status"} <= call_columns


def test_0017_downgrade_restores_whatsapp_tables(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0016")
    _seed(engine)
    _run(engine, command.upgrade, "0017")
    with engine.begin() as conn:    # una de voz y una programada de WhatsApp: la de voz no vuelve
        _exec(conn, "INSERT INTO campaigns (id, created_at, updated_at, client_id, name, channel, status, "
                    f"concurrency) VALUES ('v1', '{T0}', '{T0}', 'c1', 'Voz', 'voice', 'running', 2)")
        _exec(conn, "UPDATE campaigns SET status = 'scheduled' WHERE id = 'k3'")
        _exec(conn, f"INSERT INTO contact_optouts VALUES ('c1', '+5493515550009', 'all', 'manual', '{T0}')")

    _run(engine, command.downgrade, "0016")
    tables = set(sa.inspect(engine).get_table_names())
    assert OLD_TABLES <= tables and not NEW_TABLES & tables
    assert not TIER_COLUMNS & {c["name"] for c in sa.inspect(engine).get_columns("tiers")}
    assert not {"campaign_contact_id", "sip_status"} & {c["name"] for c in sa.inspect(engine).get_columns("call_logs")}
    with engine.connect() as conn:
        assert [tuple(r) for r in conn.execute(sa.text("SELECT id, status FROM wa_campaigns ORDER BY id"))] == [
            ("k1", "running"), ("k2", "done"), ("k3", "draft")]
        rows = conn.execute(sa.text("SELECT id, campaign_id, wa_id, name, params, status, wamid FROM "
                                    "wa_campaign_recipients ORDER BY id")).all()
        assert [(r[0], r[1], r[2], r[3], json.loads(r[4]), r[5], r[6]) for r in rows] == [
            ("r1", "k1", "5493515550001", "Ana", ["Ana"], "sent", "wamid.1"),
            ("r2", "k1", "5493515550002", None, ["Beto"], "pending", None),
            ("r3", "k1", "5493515550003", "Cris", ["Cris"], "sending", None),
            ("r4", "k1", "5493515550004", None, ["Dani"], "failed", None),
            ("r5", "k1", "5493515550005", None, ["Eli"], "skipped", None),
            ("r6", "k2", "5493515550001", "Ana", ["Ana"], "sent", "wamid.6"),
            ("r7", "k3", "5493515550001", None, ["Otro cliente"], "pending", None)]
        # La baja de whatsapp y la de todos los canales de un mismo numero quedan en una.
        assert [tuple(o[:2]) for o in conn.execute(sa.text("SELECT client_id, wa_id, source FROM wa_optouts "
                                                           "ORDER BY client_id"))] == [
            ("c1", "5493515550009"), ("c2", "5493515550001")]

    _run(engine, command.upgrade, "0017")   # y vuelve a subir sin perder nada
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT count(*) FROM campaign_contacts")).scalar() == 7
        assert conn.execute(sa.text("SELECT count(*) FROM contacts")).scalar() == 6
