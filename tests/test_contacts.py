"""Agenda de contactos: telefonos E.164, servicio (upsert, archivar, CSV, bajas), la API de
/contacts, el tope del plan y los limites de campañas del tier."""
import datetime

import pytest
from sqlalchemy import select

from app.models import Campaign, CampaignContact, Client, Contact, Tier
from app.services import contacts, limits, phones
from app.services.errors import Invalid, NotFound, QuotaExceeded

from .test_api import V1, client_user, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)

# ---------- telefonos ----------

@pytest.mark.parametrize("raw, e164", [
    ("351 555-1234", "+5493515551234"),
    ("0351 5551234", "+5493515551234"),
    ("+54 9 351 555-1234", "+5493515551234"),
    ("+54 351 555 1234", "+5493515551234"),     # sin el 9: se toma como celular
    ("543515551234", "+5493515551234"),
    ("11 2345-6789", "+5491123456789"),
    ("+1 (555) 145-6632", "+15551456632"),
    ("0034 612 345 678", "+34612345678"),
])
def test_normalize_phone_e164(raw, e164):
    assert phones.normalize_phone(raw) == e164
    assert phones.normalize_phone(e164) == e164     # idempotente


@pytest.mark.parametrize("raw", ["", "abc", "351 15 555-1234", "555-1234", "+54 9 351 555", "+12345"])
def test_normalize_phone_rejects(raw):
    with pytest.raises(ValueError):
        phones.normalize_phone(raw)


def test_wa_id_and_whatsapp():
    assert phones.wa_id("+5493515551234") == "5493515551234"
    assert phones.from_wa_id("5493515551234") == "+5493515551234" == phones.from_wa_id("+5493515551234")
    assert phones.has_whatsapp("+5493515551234") and phones.has_whatsapp("+15551456632")
    assert not phones.has_whatsapp("+543515551234")     # un fijo argentino (+54 sin el 9)


# ---------- servicio ----------

@pytest.fixture
def client_id(sessions):
    with sessions() as s:
        tier = Tier(name="T")
        s.add(tier)
        s.flush()
        c = Client(name="Acme", slug="acme", tier_id=tier.id)
        s.add(c)
        s.commit()
        return c.id


def row(phone, **kw):
    return contacts.ContactRow(phone=phone, **kw)


def test_upsert_creates_updates_and_merges(sessions, client_id):
    with sessions() as s:
        r = contacts.upsert(s, client_id, [
            row("351 555-1234", name="Ana", notes="Prefiere la tarde", line=2),
            row("3515551234", email="ana@acme.com", line=3),
            row("555", line=4), row("3515550000", email="sin-arroba", line=5),
            row("3515550001", notes="x" * 2001)],
            source="csv")
        s.commit()
        assert [c.phone for c in r.created] == ["+5493515551234"] and r.updated == []
        assert [(x.phone, x.line) for x in r.invalid] == [("555", 4), ("3515550000", 5), ("3515550001", None)]
        assert "email" in r.invalid[1].reason and "notas" in r.invalid[2].reason
        ana = r.created[0]
        assert (ana.name, ana.email, ana.source, ana.notes) == ("Ana", "ana@acme.com", "csv", "Prefiere la tarde")

        # Otra carga: actualiza y no pisa lo que no viene (la nota vacia tampoco); con nota, la reemplaza.
        r = contacts.upsert(s, client_id, [row("+54 9 351 555 1234", notes="  ")])
        s.commit()
        assert r.created == [] and [c.id for c in r.updated] == [ana.id] and r.archived == []
        assert (ana.name, ana.notes) == ("Ana", "Prefiere la tarde")
        contacts.upsert(s, client_id, [row("3515551234", notes="Llamar después de las 18")])
        assert ana.notes == "Llamar después de las 18"
        assert s.scalar(select(Contact.id).where(Contact.client_id == client_id).limit(2)) == ana.id


def test_upsert_does_not_unarchive_and_reports_it(sessions, client_id):
    with sessions() as s:
        ana = contacts.upsert(s, client_id, [row("3515551234", name="Ana")]).created[0]
        assert contacts.archive(s, [ana]) == 1 and ana.archived_at is not None
        r = contacts.upsert(s, client_id, [row("3515551234", name="Ana Maria")])
        assert r.created == [] and r.archived == [ana] and ana.name == "Ana Maria" and ana.archived_at is not None
        contacts.unarchive(s, ana)
        assert ana.archived_at is None


def test_max_contacts_counts_only_active(sessions, client_id):
    with sessions() as s:
        s.get(Client, client_id).tier.max_contacts = 2
        s.commit()
        r = contacts.upsert(s, client_id, [row("3515550001"), row("3515550002"), row("3515550003")])
        assert len(r.created) == 2 and r.limit_hit and "tope" in r.invalid[0].reason
        # Existente: se actualiza aunque la agenda este llena.
        assert len(contacts.upsert(s, client_id, [row("3515550001", name="Uno")]).updated) == 1
        # Archivar libera un lugar; desarchivar sin lugar falla.
        first = r.created[0]
        contacts.archive(s, [first])
        third = contacts.upsert(s, client_id, [row("3515550003")]).created[0]
        with pytest.raises(QuotaExceeded) as e:
            contacts.unarchive(s, first)
        assert e.value.code == "contacts_limit"
        contacts.archive(s, [third])
        contacts.unarchive(s, first)


def test_archive_skips_pending_campaign_contacts(sessions, client_id):
    with sessions() as s:
        ana, beto = contacts.upsert(s, client_id, [row("3515550001"), row("3515550002")]).created
        open_c = Campaign(client_id=client_id, channel="whatsapp", account_id="a", name="A", template_name="t",
                          template_language="es_AR", status="running")
        done_c = Campaign(client_id=client_id, channel="whatsapp", account_id="a", name="B", template_name="t",
                          template_language="es_AR", status="done")
        s.add_all([open_c, done_c])
        s.flush()
        items = [CampaignContact(campaign_id=open_c.id, contact=ana, vars={}),
                 CampaignContact(campaign_id=open_c.id, contact=beto, vars={}, status="in_progress"),
                 CampaignContact(campaign_id=done_c.id, contact=ana, vars={})]
        s.add_all(items)
        s.commit()
        contacts.archive_many(s, client_id, contact_ids=[ana.id, beto.id])
        s.commit()
        assert [(i.status, (i.error or {}).get("reason")) for i in items] == [
            ("skipped", "contact_archived"), ("in_progress", None), ("pending", None)]


def test_archive_many_and_list_filters(sessions, client_id):
    with sessions() as s:
        _, _, cris = contacts.upsert(s, client_id, [row("3515550001", name="Ana"), row("3515550002", name="Beto"),
                                                    row("3515550003", name="Cris", email="c@x.com")]).created
        assert contacts.archive_many(s, client_id, contact_ids=["no-existe"]) == 0
        ana_id = s.scalar(select(Contact.id).where(Contact.client_id == client_id, Contact.name == "Ana"))
        assert contacts.archive_many(s, client_id, contact_ids=[ana_id, cris.id]) == 2
        with pytest.raises(Invalid):
            contacts.archive_many(s, client_id, [])
        s.commit()

        def phones_of(**kw):
            return sorted(c.phone[-1] for c in contacts.list_contacts(s, client_id, **kw)[0])
        assert phones_of() == ["2"] and phones_of(archived="true") == ["1", "3"] and phones_of(archived="all") == ["1", "2", "3"]
        assert phones_of(archived="all", q="cris") == ["3"] and phones_of(archived="all", q="555000") == ["1", "2", "3"]
        assert contacts.list_contacts(s, client_id, archived="all", limit=2)[1] == 3
        with pytest.raises(Invalid):
            contacts.list_contacts(s, client_id, archived="quizas")


def test_parse_csv():
    rows = contacts.parse_csv("﻿Nombre;Teléfono;Email;ID;Notas;Deuda;Fecha de vencimiento\n"
                              "Ana;351 555-1234;ana@x.com;C-1;Cliente desde 2020;15000;2026-11-01\n;;;;;;\nJuan;3515550000;;;;;\n")
    # Las columnas que no son del contacto (deuda, fecha) se ignoran.
    assert [(r.phone, r.name, r.email, r.external_id, r.notes, r.line) for r in rows] == [
        ("351 555-1234", "Ana", "ana@x.com", "C-1", "Cliente desde 2020", 2),
        ("3515550000", "Juan", None, None, None, 4)]
    with pytest.raises(Invalid):
        contacts.parse_csv("nombre,empresa\nAna,Acme\n")
    assert contacts.parse_csv("  ") == []


def test_optouts_by_channel(sessions, client_id):
    with sessions() as s:
        contacts.add_optout(s, client_id, "+5493515550001", "whatsapp", "keyword")
        contacts.add_optout(s, client_id, "+5493515550002", "all", "manual")
        assert contacts.add_optout(s, client_id, "+5493515550001", "whatsapp", "manual").source == "keyword"
        assert contacts.is_opted_out(s, client_id, "+5493515550001", "whatsapp")
        assert not contacts.is_opted_out(s, client_id, "+5493515550001", "voice")
        assert contacts.is_opted_out(s, client_id, "+5493515550002", "voice")
        assert contacts.opted_out_phones(s, client_id, "voice") == {"+5493515550002"}
        with pytest.raises(Invalid):
            contacts.add_optout(s, client_id, "+5493515550003", "sms", "manual")
        with pytest.raises(NotFound):
            contacts.remove_optout(s, client_id, "+5493515550003")
        assert contacts.remove_optout(s, client_id, "+5493515550002") == 1
        # La baja es del telefono: sobrevive a archivar o recargar el contacto.
        ana = contacts.upsert(s, client_id, [row("3515550001")]).created[0]
        contacts.archive(s, [ana])
        assert contacts.is_opted_out(s, client_id, ana.phone, "whatsapp")


# ---------- API ----------

def test_api_upsert_list_patch_archive(api, admin):  # noqa: F811
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    user = client_user(api, admin, acme)
    r = user.post(f"{V1}/contacts", json={"phone": "351 555-1234", "name": "Ana", "notes": "Prefiere WhatsApp",
                                          "tags": ["VIP"], "attributes": {"deuda": 100}})
    assert r.status_code == 201, r.text
    ana = r.json()["contacts"][0]
    assert (r.json()["created"], ana["phone"], ana["notes"], ana["source"], ana["client_id"]) == (
        1, "+5493515551234", "Prefiere WhatsApp", "api", acme["id"])
    # Etiquetas y datos por contacto ya no existen: no se guardan ni se devuelven.
    assert "tags" not in ana and "attributes" not in ana
    # Lista: uno nuevo, uno existente y uno invalido.
    r = user.post(f"{V1}/contacts", json=[{"phone": "3515551234", "email": "ana@x.com"}, {"phone": "3515550000"},
                                          {"phone": "nope"}])
    assert r.status_code == 201 and (r.json()["created"], r.json()["updated"], r.json()["invalid"]) == (
        1, 1, [{"phone": "nope", "reason": "sin número", "line": None}])
    assert user.post(f"{V1}/contacts", json={"phone": "nope"}).status_code == 422
    assert user.post(f"{V1}/contacts", json=[]).status_code == 422
    # Un solo contacto que ya existe: 200.
    assert user.post(f"{V1}/contacts", json={"phone": "3515551234"}).status_code == 200

    page = user.get(f"{V1}/contacts", params={"q": "ana"}).json()
    assert page["total"] == 1 and page["items"][0]["email"] == "ana@x.com"
    assert user.get(f"{V1}/contacts", params={"archived": "talvez"}).status_code == 422

    r = user.patch(f"{V1}/contacts/{ana['id']}", json={"name": None, "notes": "Nota nueva"})
    assert r.status_code == 200 and (r.json()["name"], r.json()["notes"]) == (None, "Nota nueva")
    # Solo cambia lo que viene; la nota se borra con null y tiene tope.
    assert user.patch(f"{V1}/contacts/{ana['id']}", json={"email": "a@x.com"}).json()["notes"] == "Nota nueva"
    assert user.patch(f"{V1}/contacts/{ana['id']}", json={"notes": "  "}).json()["notes"] is None
    assert user.patch(f"{V1}/contacts/{ana['id']}", json={"notes": "x" * 2001}).status_code == 422

    r = user.post(f"{V1}/contacts/{ana['id']}/archive")
    assert r.status_code == 200 and r.json()["archived_at"]
    assert user.get(f"{V1}/contacts").json()["total"] == 1
    assert user.get(f"{V1}/contacts", params={"archived": "true"}).json()["total"] == 1
    assert user.get(f"{V1}/contacts", params={"archived": "all"}).json()["total"] == 2
    # Recargar uno archivado: se actualiza y se informa, sigue archivado.
    r = user.post(f"{V1}/contacts", json={"phone": "3515551234", "name": "Ana M"})
    assert r.json()["archived"] == 1 and r.json()["contacts"][0]["archived_at"]
    r = user.post(f"{V1}/contacts/{ana['id']}/unarchive")
    assert r.status_code == 200 and r.json()["archived_at"] is None
    assert user.delete(f"{V1}/contacts/{ana['id']}").status_code == 405     # no se borra

    # Lote por ids.
    assert user.post(f"{V1}/contacts/archive", json={"contact_ids": [ana["id"]]}).json() == {"archived": 1}
    assert user.post(f"{V1}/contacts/archive", json={}).status_code == 422
    assert user.post(f"{V1}/contacts/archive", json={"tags": ["b2b"]}).status_code == 422

    # Otro cliente: no ve ni toca; un admin tiene que indicar el cliente.
    stranger = client_user(api, admin, other, email="otro@x.com")
    assert stranger.get(f"{V1}/contacts").json()["total"] == 0
    assert stranger.get(f"{V1}/contacts/{ana['id']}").status_code == 404
    assert stranger.post(f"{V1}/contacts/{ana['id']}/archive").status_code == 404
    assert user.get(f"{V1}/contacts", params={"client_id": other["id"]}).status_code == 403
    assert admin.post(f"{V1}/contacts", json={"phone": "3515559999"}).status_code == 422
    assert admin.post(f"{V1}/contacts", params={"client_id": other["id"]}, json={"phone": "3515559999"}).status_code == 201
    assert admin.get(f"{V1}/contacts", params={"archived": "all"}).json()["total"] == 3
    assert api.client.get(f"{V1}/contacts").status_code == 401


def test_api_import_csv(api, admin):  # noqa: F811
    user = client_user(api, admin, make_client(admin, "acme"))
    csv = ("telefono,nombre,deuda,notas\n351 555-1234,Ana,100,Primera\n555,Mal,1,\n351 555-0000,Juan,,\n"
           "3515551234,Ana de nuevo,200,Segunda\n")
    r = user.post(f"{V1}/contacts/import", json={"csv": csv})
    assert r.status_code == 200, r.text
    out = r.json()
    assert (out["created"], out["updated"]) == (2, 0)      # el repetido se suma al mismo contacto
    assert out["invalid"] == [{"phone": "555", "reason": "formato no reconocido: código de área + número sin el 15 "
                                                        "(351 555-1234), o +54 9 ...", "line": 3}]
    ana = next(c for c in out["contacts"] if c["phone"].endswith("1234"))
    assert (ana["name"], ana["notes"], ana["source"]) == ("Ana de nuevo", "Segunda", "csv")
    assert "attributes" not in ana and "tags" not in ana
    assert user.post(f"{V1}/contacts/import", json={"csv": "nombre\nAna"}).status_code == 422
    # Reimportar actualiza.
    assert user.post(f"{V1}/contacts/import", json={"csv": "telefono,nombre\n3515550000,Juan P\n"}).json()["updated"] == 1


def test_api_contacts_limit(api, admin):  # noqa: F811
    acme = make_client(admin, "acme", max_contacts=1)
    user = client_user(api, admin, acme)
    assert user.post(f"{V1}/contacts", json={"phone": "3515550001"}).status_code == 201
    r = user.post(f"{V1}/contacts", json={"phone": "3515550002"})
    assert r.status_code == 429 and r.json()["code"] == "contacts_limit"
    r = user.post(f"{V1}/contacts", json=[{"phone": "3515550001"}, {"phone": "3515550002"}])
    assert r.status_code == 200 and (r.json()["updated"], r.json()["invalid"][0]["reason"]) == (
        1, "tope de contactos del plan")
    # Un ajuste del cliente sube el tope (max_contacts es ajustable como el resto).
    admin.post(f"{V1}/clients/{acme['id']}/limit-adjustments", json={"field": "max_contacts", "mode": "add", "value": 1})
    assert user.post(f"{V1}/contacts", json={"phone": "3515550002"}).status_code == 201


def test_api_optouts(api, admin):  # noqa: F811
    user = client_user(api, admin, make_client(admin, "acme"))
    r = user.post(f"{V1}/contacts/optouts", json={"phone": "351 555-1234", "channel": "voice"})
    assert r.status_code == 201 and (r.json()["phone"], r.json()["channel"], r.json()["source"]) == (
        "+5493515551234", "voice", "manual")
    assert user.post(f"{V1}/contacts/optouts", json={"phone": "351 555-1234"}).json()["channel"] == "all"
    assert user.post(f"{V1}/contacts/optouts", json={"phone": "123"}).status_code == 422
    assert len(user.get(f"{V1}/contacts/optouts").json()) == 2
    assert [o["channel"] for o in user.get(f"{V1}/contacts/optouts", params={"channel": "voice"}).json()] == ["voice"]
    assert user.delete(f"{V1}/contacts/optouts/+5493515551234", params={"channel": "voice"}).status_code == 204
    assert user.delete(f"{V1}/contacts/optouts/5493515551234").status_code == 204       # el resto
    assert user.delete(f"{V1}/contacts/optouts/5493515551234").status_code == 404
    # El alias de WhatsApp ve solo el canal whatsapp.
    user.post(f"{V1}/contacts/optouts", json={"phone": "3515550000", "channel": "whatsapp"})
    user.post(f"{V1}/contacts/optouts", json={"phone": "3515550001", "channel": "voice"})
    assert [o["wa_id"] for o in user.get(f"{V1}/whatsapp/optouts").json()] == ["5493515550000"]


# ---------- limites de campañas del tier ----------

def test_campaign_limits(sessions, client_id):
    with sessions() as s:
        client = s.get(Client, client_id)
        tier = client.tier
        tier.campaign_channels = ["whatsapp"]
        tier.max_campaigns_per_month, tier.max_campaign_contacts, tier.max_campaign_concurrency = 2, 100, 3
        s.commit()
        eff = limits.effective_limits(s, client)
        assert (eff.campaign_channels, eff.campaign_followup, eff.max_campaigns_per_month) == (("whatsapp",), False, 2)

        limits.check_campaign_channel(eff, "whatsapp")
        with pytest.raises(QuotaExceeded) as e:
            limits.check_campaign_channel(eff, "voice")
        assert e.value.code == "campaign_channel_not_in_plan"
        with pytest.raises(QuotaExceeded):
            limits.check_campaign_followup(eff)
        limits.check_campaign_contacts(eff, 100)
        with pytest.raises(QuotaExceeded):
            limits.check_campaign_contacts(eff, 101)
        limits.check_campaign_concurrency(eff, 3)
        with pytest.raises(QuotaExceeded):
            limits.check_campaign_concurrency(eff, 4)
        assert limits.campaign_contacts_room(eff, 90, 10_000) == 10 and limits.campaign_contacts_room(eff, 90, 95) == 5

        # Por mes: cuenta las iniciadas (started_at); cancelar no devuelve el cupo.
        now = datetime.datetime(2026, 10, 15, 15, 0)
        for i, (started, status) in enumerate([(datetime.datetime(2026, 10, 2, 12), "cancelled"),
                                               (datetime.datetime(2026, 10, 9, 12), "running"),
                                               (datetime.datetime(2026, 9, 28, 12), "done"), (None, "draft")]):
            s.add(Campaign(client_id=client_id, channel="voice", concurrency=1, name=str(i), status=status,
                           started_at=started))
        s.commit()
        assert limits.campaigns_started(s, client_id, now) == 2
        with pytest.raises(QuotaExceeded) as e:
            limits.check_campaign_month(s, client_id, eff, now)
        assert e.value.code == "campaigns_per_month"
        limits.check_campaign_month(s, client_id, eff, datetime.datetime(2026, 11, 3, 15, 0))
        tier.max_campaigns_per_month = None
        limits.check_campaign_month(s, client_id, limits.effective_limits(s, client), now)
        tier.max_campaigns_per_month = 0
        with pytest.raises(QuotaExceeded):
            limits.check_campaign_month(s, client_id, limits.effective_limits(s, client), datetime.datetime(2026, 11, 3))


def test_pause_campaigns_outside_plan(sessions, client_id):
    with sessions() as s:
        client = s.get(Client, client_id)
        client.tier.campaign_channels = ["whatsapp"]
        for i, (channel, status) in enumerate([("whatsapp", "running"), ("voice", "running"), ("voice", "scheduled"),
                                               ("voice", "done"), ("voice", "draft")]):
            s.add(Campaign(client_id=client_id, channel=channel, name=str(i), status=status, concurrency=1,
                           account_id="a", template_name="t", template_language="es_AR"))
        s.flush()
        assert limits.pause_campaigns_outside_plan(s, client, limits.effective_limits(s, client)) == 2
        s.commit()
        states = {c.name: (c.status, c.status_reason) for c in s.scalars(select(Campaign))}
        assert states["0"] == ("running", None) and states["3"][0] == "done" and states["4"][0] == "draft"
        assert states["1"][0] == states["2"][0] == "paused" and "llamadas" in states["1"][1]


def test_tier_api_campaign_fields(api, admin):  # noqa: F811
    t = admin.post(f"{V1}/tiers", json={"name": "Camp"}).json()
    assert (t["campaign_channels"], t["max_campaigns_per_month"], t["max_contacts"], t["campaign_followup"]) == (
        [], None, None, False)
    r = admin.patch(f"{V1}/tiers/{t['id']}", json={"campaign_channels": ["voice", "whatsapp", "voice"],
                                                   "max_campaign_concurrency": 4, "campaign_followup": True})
    assert r.status_code == 200 and (r.json()["campaign_channels"], r.json()["max_campaign_concurrency"],
                                     r.json()["campaign_followup"]) == (["voice", "whatsapp"], 4, True)
    r = admin.patch(f"{V1}/tiers/{t['id']}", json={"campaign_channels": None, "campaign_followup": None, "max_contacts": 5})
    assert (r.json()["campaign_channels"], r.json()["campaign_followup"], r.json()["max_contacts"]) == (
        ["voice", "whatsapp"], True, 5)
    assert admin.patch(f"{V1}/tiers/{t['id']}", json={"campaign_channels": ["sms"]}).status_code == 422
    assert admin.post(f"{V1}/tiers", json={"name": "X", "max_contacts": -1}).status_code == 422
