"""Campañas unificadas (docs/LLAMADAS_SALIENTES_PLAN.md, fase 1): la API /campaigns para WhatsApp y
voz, el plan del tier, los contactos de la agenda, la programacion y el alias /whatsapp/campaigns."""
import datetime
import uuid

import pytest
from sqlalchemy import select

from app.db import utcnow
from app.models import Campaign, CampaignContact, Contact
from app.services import campaigns as common
from app.whatsapp.sender import CampaignSender

from .test_api import V1, client_user, make_agent, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_campaigns import (  # noqa: F401  (fixtures)
    CampaignGraph,
    Clock,
    account,
    campaign_body,
    make_campaign,
    recipients,
    sender_for,
)
from .test_whatsapp_service import WA_ID, make_wa
from .test_whatsapp_signup import acme, meta  # noqa: F401  (fixtures)

PHONES = ["351 555-1001", "351 555-1002", "351 555-1003"]


def iso(dt: datetime.datetime) -> str:
    return dt.replace(tzinfo=datetime.UTC).isoformat()


def load_contacts(user, rows=None, **extra) -> list[dict]:
    """Contactos a la agenda (POST /contacts) y los devuelve."""
    rows = rows or [{"phone": p, "name": f"Ana{i}", "attributes": {"deuda": 100 * i}, "tags": ["mora"]}
                    for i, p in enumerate(PHONES, start=1)]
    r = user.post(f"{V1}/contacts", json=rows, **extra)
    assert r.status_code in (200, 201), r.text
    return r.json()["contacts"]


@pytest.fixture
def voice(api, admin):  # noqa: F811
    """Un cliente cuyo plan incluye campañas de voz, con un agente y un usuario."""
    c = make_client(admin, slug="vox", campaign_channels=["voice"])
    agent = make_agent(admin, c, template="demo_booking")
    return client_user(api, admin, c, email="vox@x.com"), agent, c


def voice_body(agent, **extra):
    return {"channel": "voice", "name": "Cobranza", "agent_id": agent["id"], **extra}


# ---------- WhatsApp por la API nueva ----------

def wa_body(acc, **extra):
    return {"channel": "whatsapp", "account_id": acc["id"], "name": "Mora", "template_name": "demo", **extra}


def test_whatsapp_campaign_from_agenda_with_param_names(api, account):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user)
    r = user.post(f"{V1}/campaigns", json=wa_body(acc, contact_ids=[rows[0]["id"], rows[1]["id"]],
                                                  tags=["mora"], param_names=["nombre"]))
    assert r.status_code == 201, r.text
    out = r.json()
    # El tercero entra por la etiqueta; los dos primeros ya estaban (repetidos) y no se cuentan dos veces.
    assert out["added"] == 3 and [s["reason"] for s in out["skipped"]] == ["repetido", "repetido"]
    c = out["campaign"]
    assert (c["channel"], c["status"], c["param_names"], c["template_params"]) == ("whatsapp", "draft", ["nombre"], 1)
    assert c["total"] == 3 and c["progress"]["pending"] == 3 and c["percent"] == 0
    assert c["results"] == {"sent": 0, "delivered": 0, "read": 0, "replied": 0}
    page = user.get(f"{V1}/campaigns/{c['id']}/contacts").json()
    assert [(i["phone"], i["vars"]["params"], i["vars"]["deuda"], i["status"]) for i in page["items"]] == [
        ("+5493515551001", ["Ana1"], 100, "pending"), ("+5493515551002", ["Ana2"], 200, "pending"),
        ("+5493515551003", ["Ana3"], 300, "pending")]
    assert page["items"][0]["vars"]["telefono"] == "+5493515551001"


def test_whatsapp_campaign_vars_are_a_copy(api, account):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user)
    cid = user.post(f"{V1}/campaigns", json=wa_body(acc, contact_ids=[rows[0]["id"]],
                                                    param_names=["nombre"])).json()["campaign"]["id"]
    assert user.patch(f"{V1}/contacts/{rows[0]['id']}", json={"name": "Otro", "attributes": {"deuda": 1}}).status_code == 200
    item = user.get(f"{V1}/campaigns/{cid}/contacts").json()["items"][0]
    assert item["name"] == "Otro" and item["vars"]["params"] == ["Ana1"] and item["vars"]["deuda"] == 100


def test_whatsapp_param_names_need_attributes(api, account):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user, [{"phone": PHONES[0]}, {"phone": PHONES[1], "name": "Eva"}])
    # Sin param_names no se sabe como completar {{1}} desde la agenda.
    r = user.post(f"{V1}/campaigns", json=wa_body(acc, contact_ids=[rows[0]["id"]]))
    assert r.status_code == 422 and "param_names" in r.json()["detail"]
    r = user.post(f"{V1}/campaigns", json=wa_body(acc, param_names=["a", "b"]))
    assert r.status_code == 422
    out = user.post(f"{V1}/campaigns", json=wa_body(acc, param_names=["nombre"],
                                                    contact_ids=[x["id"] for x in rows])).json()
    assert out["added"] == 1 and "faltan valores" in out["skipped"][0]["reason"]


def test_campaign_accepts_new_contacts_and_csv(api, account):  # noqa: F811
    user, acc, _ = account
    csv = "telefono,nombre,deuda,tags\n351 555-2001,Eva,500,mora\n555,Mal,1,\n351 555-2002,,2,\n"
    r = user.post(f"{V1}/campaigns", json=wa_body(
        acc, param_names=["nombre"], csv=csv, contacts=[{"phone": "351 555-2003", "name": "Juan"}],
        recipients=[{"phone": "351 555-2004", "params": ["Luz"]}]))
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["added"] == 3      # Luz (recipients), Juan y Eva; la fila 4 no tiene nombre
    assert sorted((s["phone"], s["line"]) for s in out["skipped"] if s["line"]) == [
        ("351 555-2002", 4), ("555", 3)]
    # Todos entraron tambien en la agenda.
    agenda = user.get(f"{V1}/contacts").json()
    assert {c["phone"] for c in agenda["items"]} >= {"+5493515552001", "+5493515552003", "+5493515552004"}
    eva = next(c for c in agenda["items"] if c["name"] == "Eva")
    assert eva["attributes"] == {"deuda": "500"} and eva["tags"] == ["mora"] and eva["source"] == "csv"


def test_archived_contacts_are_not_added(api, account):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user)
    assert user.post(f"{V1}/contacts/{rows[0]['id']}/archive").status_code == 200
    out = user.post(f"{V1}/campaigns", json=wa_body(acc, contact_ids=[x["id"] for x in rows], tags=["mora"],
                                                    param_names=["nombre"])).json()
    assert out["added"] == 2
    assert [(s["phone"], s["reason"]) for s in out["skipped"]] == [
        ("+5493515551001", "contacto archivado"), ("+5493515551002", "repetido"), ("+5493515551003", "repetido")]
    r = user.post(f"{V1}/campaigns/{out['campaign']['id']}/contacts", json={"contact_ids": ["no-existe"]})
    assert r.json()["skipped"] == [{"phone": "no-existe", "reason": "contacto inexistente", "line": None}]


def test_optout_by_channel_skips(api, account, voice):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user)
    assert user.post(f"{V1}/contacts/optouts", json={"phone": PHONES[0], "channel": "voice"}).status_code == 201
    assert user.post(f"{V1}/contacts/optouts", json={"phone": PHONES[1], "channel": "whatsapp"}).status_code == 201
    out = user.post(f"{V1}/campaigns", json=wa_body(acc, param_names=["nombre"],
                                                    contact_ids=[x["id"] for x in rows])).json()
    assert out["added"] == 2 and [s["phone"] for s in out["skipped"]] == ["+5493515551002"]


def test_polling_detail_and_whatsapp_results(api, account):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user)
    c = user.post(f"{V1}/campaigns", json=wa_body(acc, param_names=["nombre"],
                                                  contact_ids=[x["id"] for x in rows])).json()["campaign"]
    with api.sessions() as s:
        members = list(s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == c["id"])
                                 .order_by(CampaignContact.created_at, CampaignContact.id)))
        now = utcnow()
        members[0].status, members[0].result, members[0].sent_at, members[0].wamid = "done", "sent", now, "w1"
        members[1].status, members[1].result, members[1].sent_at, members[1].replied_at = "done", "sent", now, now
        members[2].status, members[2].error = "failed", {"code": 131026}
        s.get(Campaign, c["id"]).status = "running"
        s.get(Campaign, c["id"]).started_at = now - datetime.timedelta(minutes=2)
        s.commit()
    d = user.get(f"{V1}/campaigns/{c['id']}").json()
    assert d["progress"] == {"pending": 0, "in_progress": 0, "retry": 0, "done": 2, "failed": 1, "skipped": 0}
    assert d["results"] == {"sent": 2, "delivered": 0, "read": 0, "replied": 1}
    assert d["total"] == 3 and d["percent"] == 100.0 and d["eta_minutes"] == 0 and d["minutes_used"] is None
    assert d["in_window"] in (True, False) and d["timezone"]
    done = user.get(f"{V1}/campaigns/{c['id']}/contacts", params={"result": "replied"}).json()
    assert done["total"] == 1 and done["items"][0]["result"] == "replied"
    assert user.get(f"{V1}/campaigns/{c['id']}/contacts", params={"status": "failed"}).json()["items"][0]["result"] == "failed"
    assert user.get(f"{V1}/campaigns/{c['id']}/contacts", params={"result": "busy"}).status_code == 422
    assert user.get(f"{V1}/campaigns/{c['id']}/contacts", params={"status": "nope"}).status_code == 422


def test_list_filters_by_channel_and_status(api, account, admin):  # noqa: F811
    user, acc, _ = account
    rows = load_contacts(user)
    user.post(f"{V1}/campaigns", json=wa_body(acc, param_names=["nombre"], contact_ids=[rows[0]["id"]]))
    started = user.post(f"{V1}/campaigns", json=wa_body(acc, name="Otra", param_names=["nombre"],
                                                        contact_ids=[rows[1]["id"]], start=True)).json()["campaign"]
    assert started["status"] == "running"
    assert len(user.get(f"{V1}/campaigns").json()) == 2
    assert [c["id"] for c in user.get(f"{V1}/campaigns", params={"status": "running"}).json()] == [started["id"]]
    assert user.get(f"{V1}/campaigns", params={"channel": "voice"}).json() == []
    assert len(admin.get(f"{V1}/campaigns").json()) == 2


# ---------- el alias de WhatsApp ----------

def test_alias_param_names_and_scheduled_campaigns(api, account):  # noqa: F811
    user, acc, _ = account
    load_contacts(user)
    created = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(
        acc, csv=None, param_names=["nombre"], recipients=[{"phone": PHONES[0]}, {"phone": PHONES[1], "params": ["Eva"]}]))
    assert created.status_code == 201, created.text
    assert created.json()["added"] == 2
    cid = created.json()["campaign"]["id"]
    page = user.get(f"{V1}/whatsapp/campaigns/{cid}/recipients").json()["items"]
    assert [i["params"] for i in page] == [["Ana1"], ["Eva"]]       # el primero salio de la agenda
    # Una campaña programada desde la API nueva se ve (y pausa) por el alias.
    soon = iso(utcnow() + datetime.timedelta(hours=1))
    user.patch(f"{V1}/campaigns/{cid}", json={"starts_at": soon})
    assert user.post(f"{V1}/whatsapp/campaigns/{cid}/start").json()["status"] == "scheduled"
    assert user.get(f"{V1}/whatsapp/campaigns").json()[0]["status"] == "scheduled"
    assert user.post(f"{V1}/whatsapp/campaigns/{cid}/pause").json()["status"] == "paused"


# ---------- voz ----------

def test_voice_campaign_create_and_validate(api, voice, admin):  # noqa: F811
    user, agent, c = voice
    load_contacts(user)
    r = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"], concurrency=3))
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["added"] == 3 and out["skipped"] == []
    camp = out["campaign"]
    assert (camp["channel"], camp["status"], camp["concurrency"], camp["max_attempts"], camp["retry_minutes"]) == (
        "voice", "draft", 3, 3, 60)
    assert camp["retry_on"] == ["no_answer", "busy", "voicemail", "failed"] and camp["account_id"] is None
    assert camp["results"] == {k: 0 for k in common.VOICE_RESULTS} and camp["minutes_used"] == 0.0
    # Los fijos tambien se llaman: no hay restriccion de WhatsApp.
    landline = user.post(f"{V1}/campaigns/{camp['id']}/contacts", json={"contacts": [{"phone": "+54 351 4551234"}]})
    assert landline.json()["added"] == 1

    # Validaciones.
    assert user.post(f"{V1}/campaigns", json={"channel": "voice", "name": "x"}).status_code == 422
    assert user.post(f"{V1}/campaigns", json=voice_body({"id": "no-es"})).status_code == 404
    assert user.post(f"{V1}/campaigns", json=voice_body(agent, from_number_id="no-es")).status_code == 404
    assert user.post(f"{V1}/campaigns", json=voice_body(agent, retry_on=["answered"])).status_code == 422
    assert user.post(f"{V1}/campaigns", json=voice_body(agent, voice="no-existe")).status_code == 422
    assert user.post(f"{V1}/campaigns", json=voice_body(agent, window_start=20, window_end=9)).status_code == 422
    assert user.post(f"{V1}/campaigns", json=voice_body(agent, weekdays=[7])).status_code == 422
    past = iso(utcnow() - datetime.timedelta(hours=1))
    assert user.post(f"{V1}/campaigns", json=voice_body(agent, ends_at=past)).status_code == 422
    # El admin indica el cliente.
    assert admin.post(f"{V1}/campaigns", json=voice_body(agent)).status_code == 422
    assert admin.post(f"{V1}/campaigns", json=voice_body(agent, client_id=c["id"])).status_code == 201


def test_voice_campaign_lifecycle(api, voice):
    user, agent, _ = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"])).json()["campaign"]
    url = f"{V1}/campaigns/{camp['id']}"
    assert user.post(f"{url}/resume").status_code == 409
    assert user.post(f"{url}/pause").status_code == 409
    assert user.patch(url, json={"concurrency": 5, "retry_on": ["busy"], "weekdays": [0, 1, 2, 3, 4]}).json()[
        "weekdays"] == [0, 1, 2, 3, 4]
    assert user.patch(url, json={"window_start": 21}).status_code == 422
    assert user.patch(url, json={"nope": 1}).json()["name"] == "Cobranza"      # campos desconocidos: se ignoran
    started = user.post(f"{url}/start").json()
    assert started["status"] == "running" and started["started_at"]
    assert user.post(f"{url}/start").status_code == 409
    assert user.delete(url).status_code == 409
    assert user.post(f"{url}/contacts", json={"contacts": [{"phone": "351 555-9999"}]}).status_code == 409
    paused = user.post(f"{url}/pause").json()
    assert paused["status"] == "paused"
    assert user.post(f"{url}/contacts", json={"contacts": [{"phone": "351 555-9999"}]}).json()["added"] == 1
    assert user.post(f"{url}/resume").json()["status"] == "running"
    cancelled = user.post(f"{url}/cancel").json()
    assert cancelled["status"] == "cancelled" and cancelled["progress"]["skipped"] == 4
    assert user.post(f"{url}/resume").status_code == 409 and user.patch(url, json={"name": "x"}).status_code == 409

    empty = user.post(f"{V1}/campaigns", json=voice_body(agent)).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{empty['id']}/start").status_code == 409      # sin contactos
    assert user.delete(f"{V1}/campaigns/{empty['id']}").status_code == 204


def test_voice_results_and_minutes(api, voice):
    from app.models import CallRow, ConversationRow
    user, agent, c = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"])).json()["campaign"]
    with api.sessions() as s:
        members = list(s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])
                                 .order_by(CampaignContact.created_at, CampaignContact.id)))
        for m, result in zip(members, ("answered", "busy", "no_answer"), strict=True):
            m.status, m.result, m.attempts, m.last_attempt_at = "done", result, 1, utcnow()
        members[2].status = "retry"
        conv = ConversationRow(id=str(uuid.uuid4()), client_id=c["id"], agent_id=agent["id"], channel="voice",
                               status="completed", fields={}, messages=[])
        s.add(conv)
        s.flush()
        s.add(CallRow(conversation_id=conv.id, client_id=c["id"], mode="saliente", phone=PHONES[0],
                      campaign_contact_id=members[0].id, duration_seconds=90))
        s.get(Campaign, camp["id"]).status = "running"
        s.get(Campaign, camp["id"]).started_at = utcnow() - datetime.timedelta(minutes=5)
        s.commit()
    d = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert d["results"]["answered"] == 1 and d["results"]["busy"] == 1 and d["results"]["no_answer"] == 1
    assert d["progress"]["done"] == 2 and d["progress"]["retry"] == 1 and d["percent"] == 66.7
    assert d["minutes_used"] == 1.5 and d["eta_minutes"] is not None and d["eta_minutes"] >= 1
    assert user.get(f"{V1}/campaigns/{camp['id']}/contacts", params={"result": "busy"}).json()["total"] == 1


def test_voice_agent_archived_blocks_start(api, voice, admin):  # noqa: F811
    user, agent, _ = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"])).json()["campaign"]
    assert admin.patch(f"{V1}/agents/{agent['id']}", json={"archived": True}).status_code == 200
    r = user.post(f"{V1}/campaigns/{camp['id']}/start")
    assert r.status_code == 409 and "archivado" in r.json()["detail"]


def test_campaign_permissions_between_clients(api, voice, admin):  # noqa: F811
    user, agent, _ = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"])).json()["campaign"]
    other = client_user(api, admin, make_client(admin, slug="otro", campaign_channels=["voice"]), email="o@x.com")
    for verb, path in (("get", ""), ("post", "/start"), ("post", "/pause"), ("get", "/contacts")):
        assert getattr(other, verb)(f"{V1}/campaigns/{camp['id']}{path}").status_code == 404
    assert other.get(f"{V1}/campaigns").json() == []
    assert other.post(f"{V1}/campaigns", json=voice_body(agent)).status_code == 404     # agente de otro cliente


# ---------- plan ----------

def test_plan_without_channel(api, admin, voice):  # noqa: F811
    user, _, _ = voice
    none = client_user(api, admin, make_client(admin, slug="sinplan"), email="s@x.com")
    other = make_agent(admin, {"id": none.get(f"{V1}/auth/me").json()["client_id"]}, template="demo_booking")
    r = none.post(f"{V1}/campaigns", json=voice_body(other))
    assert r.status_code == 429 and r.json()["code"] == "campaign_channel_not_in_plan"
    assert user.post(f"{V1}/campaigns", json={"channel": "whatsapp", "name": "x"}).status_code == 422


def test_whatsapp_channel_not_in_plan(api, account, admin):  # noqa: F811
    user, acc, c = account
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"campaign_channels": ["voice"]})
    for url, body in ((f"{V1}/campaigns", wa_body(acc)), (f"{V1}/whatsapp/campaigns", campaign_body(acc))):
        r = user.post(url, json=body)
        assert r.status_code == 429 and r.json()["code"] == "campaign_channel_not_in_plan", url


def test_campaigns_per_month_counts_started(api, voice, admin):  # noqa: F811
    user, agent, c = voice
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaigns_per_month": 2})
    load_contacts(user)
    ids = [user.post(f"{V1}/campaigns", json=voice_body(agent, name=f"C{i}", tags=["mora"])).json()["campaign"]["id"]
           for i in range(3)]
    # Crear no gasta cupo; iniciar si.
    assert user.post(f"{V1}/campaigns/{ids[0]}/start").status_code == 200
    assert user.post(f"{V1}/campaigns/{ids[1]}/start").status_code == 200
    r = user.post(f"{V1}/campaigns/{ids[2]}/start")
    assert r.status_code == 429 and r.json()["code"] == "campaigns_per_month"
    # Cancelar no devuelve el cupo, pero retomar una pausada que ya empezo no gasta otro.
    assert user.post(f"{V1}/campaigns/{ids[0]}/cancel").status_code == 200
    assert user.post(f"{V1}/campaigns/{ids[2]}/start").status_code == 429
    assert user.post(f"{V1}/campaigns/{ids[1]}/pause").status_code == 200
    assert user.post(f"{V1}/campaigns/{ids[1]}/resume").status_code == 200
    # Mas cupo en el plan, y entra.
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaigns_per_month": 3})
    assert user.post(f"{V1}/campaigns/{ids[2]}/start").status_code == 200


def test_campaign_contacts_and_concurrency_caps(api, voice, admin):  # noqa: F811
    user, agent, c = voice
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaign_contacts": 2, "max_campaign_concurrency": 4})
    load_contacts(user)
    out = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"])).json()
    assert out["added"] == 2 and out["skipped"][0]["reason"] == "tope de 2 contactos por campaña"
    r = user.post(f"{V1}/campaigns", json=voice_body(agent, concurrency=5))
    assert r.status_code == 429 and r.json()["code"] == "campaign_concurrency"
    assert user.patch(f"{V1}/campaigns/{out['campaign']['id']}", json={"concurrency": 9}).status_code == 429
    assert user.patch(f"{V1}/campaigns/{out['campaign']['id']}", json={"concurrency": 4}).status_code == 200
    # Un ajuste por cliente sube el tope.
    adj = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json={
        "field": "max_campaign_contacts", "mode": "add", "value": 5})
    assert adj.status_code == 201, adj.text
    assert user.post(f"{V1}/campaigns/{out['campaign']['id']}/contacts", json={"tags": ["mora"]}).json()["added"] == 1


def test_campaign_contacts_cap_is_rechecked_on_start(api, voice, admin):  # noqa: F811
    user, agent, c = voice
    load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"])).json()["campaign"]
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaign_contacts": 1})     # el plan bajo
    r = user.post(f"{V1}/campaigns/{camp['id']}/start")
    assert r.status_code == 429 and r.json()["code"] == "campaign_contacts"


def test_agenda_cap_applies_to_new_contacts_in_a_campaign(api, voice, admin):  # noqa: F811
    user, agent, c = voice
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_contacts": 1})
    out = user.post(f"{V1}/campaigns", json=voice_body(agent, contacts=[{"phone": PHONES[0]}, {"phone": PHONES[1]}])).json()
    assert out["added"] == 1 and "tope de contactos" in out["skipped"][0]["reason"]


def test_downgrade_pauses_campaigns_of_a_channel_outside_the_plan(api, account, admin):  # noqa: F811
    user, acc, c = account
    rows = load_contacts(user)
    cid = user.post(f"{V1}/campaigns", json=wa_body(acc, param_names=["nombre"], start=True,
                                                    contact_ids=[x["id"] for x in rows])).json()["campaign"]["id"]
    assert user.get(f"{V1}/campaigns/{cid}").json()["status"] == "running"
    # Otro plan sin campañas: el cliente baja y la campaña se pausa con el motivo.
    free = admin.post(f"{V1}/tiers", json={"name": "Free"}).json()
    assert admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": free["id"]}).status_code == 200
    d = user.get(f"{V1}/campaigns/{cid}").json()
    assert d["status"] == "paused" and "no incluye campañas por WhatsApp" in d["status_reason"]
    r = user.post(f"{V1}/campaigns/{cid}/resume")
    assert r.status_code == 429 and r.json()["code"] == "campaign_channel_not_in_plan"
    # Vuelve al plan con WhatsApp: se retoma. Y sacar el canal del plan tambien pausa.
    admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": c["tier"]["id"]})
    assert user.post(f"{V1}/campaigns/{cid}/resume").json()["status"] == "running"
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"campaign_channels": []})
    assert user.get(f"{V1}/campaigns/{cid}").json()["status"] == "paused"


# ---------- programacion ----------

def test_scheduled_start_and_roll(api, voice):
    user, agent, _ = voice
    load_contacts(user)
    later = utcnow() + datetime.timedelta(hours=2)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"], starts_at=iso(later),
                                                        ends_at=iso(later + datetime.timedelta(hours=4)),
                                                        start=True)).json()["campaign"]
    assert camp["status"] == "scheduled" and camp["started_at"]
    # Todavia no es la hora; pasada, arranca; pasado el fin, termina y los pendientes se saltean.
    with api.sessions() as s:
        assert common.roll_schedule(s, ("voice",), now=utcnow()) == 0
        assert common.roll_schedule(s, ("whatsapp",), now=later + datetime.timedelta(minutes=1)) == 0
        assert common.roll_schedule(s, ("voice",), now=later + datetime.timedelta(minutes=1)) == 1
        assert s.get(Campaign, camp["id"]).status == "running"
        assert common.roll_schedule(s, ("voice",), now=later + datetime.timedelta(hours=5)) == 1
        c = s.get(Campaign, camp["id"])
        assert (c.status, c.finished_at is not None) == ("done", True)
        assert {m.status for m in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == c.id))} == {
            "skipped"}
        s.rollback()


def test_pause_a_scheduled_campaign(api, voice):
    user, agent, _ = voice
    load_contacts(user)
    later = iso(utcnow() + datetime.timedelta(hours=2))
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"], starts_at=later, start=True)).json()["campaign"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").json()["status"] == "paused"
    assert user.post(f"{V1}/campaigns/{camp['id']}/resume").json()["status"] == "scheduled"


def test_start_after_ends_at_is_rejected(api, voice):
    user, agent, _ = voice
    load_contacts(user)
    soon = utcnow() + datetime.timedelta(seconds=1)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"], ends_at=iso(soon))).json()["campaign"]
    with api.sessions() as s:
        s.get(Campaign, camp["id"]).ends_at = utcnow() - datetime.timedelta(minutes=1)
        s.commit()
    assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 409


async def test_sender_rolls_the_schedule_of_whatsapp(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, status="scheduled")
    with sessions() as s:
        s.get(Campaign, cid).starts_at = utcnow() - datetime.timedelta(minutes=1)
        s.commit()
    assert await sender_for(w, clock=Clock()).tick() == 1      # arranco y mando en la misma vuelta
    with sessions() as s:
        assert s.get(Campaign, cid).status in ("running", "done")


async def test_sender_ends_campaigns_past_ends_at(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001")
    with sessions() as s:
        s.get(Campaign, cid).ends_at = utcnow() - datetime.timedelta(minutes=1)
        s.commit()
    assert await sender_for(w, clock=Clock()).tick() == 0
    assert w.graph.templates == []
    assert [r.status for r in recipients(sessions, cid)] == ["skipped", "skipped"]
    with sessions() as s:
        assert s.get(Campaign, cid).status == "done"


# ---------- contactos archivados en una campaña en curso ----------

async def test_sender_skips_contacts_archived_after_loading(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001", "5493515550002")
    with sessions() as s:
        archived = s.scalar(select(Contact).where(Contact.phone == "+5493515550001"))
        archived.archived_at = utcnow()     # archivado "a mano", sin pasar por contacts.archive
        s.commit()
    assert await sender_for(w, clock=Clock()).tick() == 2
    states = {r.contact.phone: (r.status, (r.error or {}).get("reason")) for r in recipients(sessions, cid)}
    assert states["+5493515550001"] == ("skipped", "contact_archived")
    assert [t[1] for t in w.graph.templates if t[1].endswith("0001")] == []


def test_archiving_a_contact_skips_its_pending_attempts_in_open_campaigns(api, voice):
    user, agent, _ = voice
    rows = load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, tags=["mora"], start=True)).json()["campaign"]
    assert user.post(f"{V1}/contacts/{rows[0]['id']}/archive").status_code == 200
    d = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert d["progress"]["skipped"] == 1 and d["progress"]["pending"] == 2
    page = user.get(f"{V1}/campaigns/{camp['id']}/contacts", params={"status": "skipped"}).json()
    assert page["items"][0]["error"]["reason"] == "contact_archived"


def test_sender_does_not_take_voice_campaigns(sessions):
    """El sender es de WhatsApp: una campaña de voz en curso no la toca."""
    w = make_wa(sessions, graph=CampaignGraph())
    with sessions() as s:
        c = Campaign(client_id=w.client_id, channel="voice", agent_id=w.agent_id, name="V", status="running",
                     concurrency=1, window_start=0, window_end=24)
        s.add(c)
        s.flush()
        contact = Contact(client_id=w.client_id, phone="+5493515559999")
        s.add(CampaignContact(campaign_id=c.id, contact=contact, vars={}))
        s.commit()
        cid = c.id
    sender = CampaignSender(sessions, graph_factory=lambda token: w.graph, hour=lambda: 12, clock=Clock())
    import asyncio
    assert asyncio.run(sender.tick()) == 0
    assert {r.status for r in recipients(sessions, cid)} == {"pending"}


# ---------- plan y ficha del contacto (para la UI) ----------

def test_campaign_plan_endpoint(api, voice, admin):  # noqa: F811
    user, _, c = voice
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaign_concurrency": 4, "max_contacts": 50})
    load_contacts(user)
    r = user.get(f"{V1}/campaigns/plan")
    assert r.status_code == 200, r.text
    plan = r.json()
    assert (plan["channels"], plan["followup"], plan["max_campaign_concurrency"], plan["max_contacts"]) == (
        ["voice"], False, 4, 50)
    assert (plan["campaigns_started"], plan["contacts_active"], plan["client_id"]) == (0, 3, c["id"])
    # El admin indica el cliente; sin cliente, 422. Otro cliente no se ve.
    assert admin.get(f"{V1}/campaigns/plan").status_code == 422
    assert admin.get(f"{V1}/campaigns/plan", params={"client_id": c["id"]}).json()["channels"] == ["voice"]
    other = client_user(api, admin, make_client(admin, slug="otro"), email="o@x.com")
    assert other.get(f"{V1}/campaigns/plan").json()["channels"] == []
    assert other.get(f"{V1}/campaigns/plan", params={"client_id": c["id"]}).status_code == 403


def test_contact_campaigns(api, voice, admin):  # noqa: F811
    user, agent, _ = voice
    rows = load_contacts(user)
    camp = user.post(f"{V1}/campaigns", json=voice_body(agent, contact_ids=[rows[0]["id"]])).json()["campaign"]
    r = user.get(f"{V1}/contacts/{rows[0]['id']}/campaigns")
    assert r.status_code == 200, r.text
    assert [(x["campaign_id"], x["channel"], x["campaign_status"], x["status"]) for x in r.json()] == [
        (camp["id"], "voice", "draft", "pending")]
    assert user.get(f"{V1}/contacts/{rows[1]['id']}/campaigns").json() == []
    other = client_user(api, admin, make_client(admin, slug="otro"), email="o@x.com")
    assert other.get(f"{V1}/contacts/{rows[0]['id']}/campaigns").status_code == 404
