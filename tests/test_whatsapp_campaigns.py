"""Campañas salientes de WhatsApp: telefonos y CSV, la API, el envio (sender) y lo que
pasa cuando el contacto responde o pide la baja (service)."""
import pytest
from sqlalchemy import select

from app.models import (
    ConversationRow,
    WaCampaign,
    WaCampaignRecipient,
    WaMessage,
    WaOptout,
)
from app.services.errors import Invalid
from app.whatsapp import campaigns, signup
from app.whatsapp.graph import GraphError
from app.whatsapp.sender import CampaignSender

from .helpers import FakeLLM
from .test_api import V1, client_user, make_agent, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_service import (
    PNID,
    SEND_TO,
    WA_ID,
    FakeGraph,
    conversations,
    make_wa,
    messages,
    reply,
    send,
    status_payload,
    text_payload,
)
from .test_whatsapp_signup import acme, meta, signup_ok  # noqa: F401  (fixtures)

BODY = "Hola {{1}}, probá gratis nuestro agente de voz."


# ---------- telefonos y CSV ----------

@pytest.mark.parametrize("raw, wa_id", [
    ("351 555-1234", "5493515551234"),
    ("0351 5551234", "5493515551234"),
    ("+54 9 351 555-1234", "5493515551234"),
    ("+54 351 555 1234", "5493515551234"),
    ("543515551234", "5493515551234"),
    ("5493515551234", "5493515551234"),
    ("11 2345-6789", "5491123456789"),
    ("+1 (555) 145-6632", "15551456632"),
    ("0034 612 345 678", "34612345678"),
])
def test_normalize_phone(raw, wa_id):
    assert campaigns.normalize_phone(raw) == wa_id


@pytest.mark.parametrize("raw", ["", "abc", "351 15 555-1234", "555-1234", "+54 9 351 555", "+12345"])
def test_normalize_phone_rejects(raw):
    with pytest.raises(ValueError):
        campaigns.normalize_phone(raw)


def test_parse_csv_columns_and_separator():
    rows = campaigns.parse_csv("﻿Nombre;Teléfono;Empresa\nAna;351 555-1234;Acme\n;;\nJuan;3515550000\n")
    assert [(r.phone, r.name, r.params, r.line) for r in rows] == [
        ("351 555-1234", "Ana", ["Ana", "Acme"], 2), ("3515550000", "Juan", ["Juan", ""], 4)]
    with pytest.raises(Invalid):
        campaigns.parse_csv("nombre,empresa\nAna,Acme\n")
    assert campaigns.parse_csv("  ") == []


def test_render_and_optout_text():
    assert campaigns.render(BODY, ["Ana"]) == "Hola Ana, probá gratis nuestro agente de voz."
    assert campaigns.is_optout_text("No me interesa.") and campaigns.is_optout_text("  BAJA ")
    assert campaigns.is_optout_text("no me escriban más!!")
    assert not campaigns.is_optout_text("no me interesa el plan básico, ¿hay otro?")


def test_template_info_checks():
    tpl = {"name": "demo", "language": "es_AR", "category": "MARKETING", "status": "APPROVED",
           "components": [{"type": "HEADER", "format": "TEXT", "text": "Atentina"}, {"type": "BODY", "text": BODY},
                          {"type": "BUTTONS", "buttons": [{"type": "URL", "text": "Probar",
                                                           "url": "https://atentina.com.ar"}]}]}
    info = campaigns.template_info([tpl], "demo", "es_AR")
    assert (info.category, info.body, info.params) == ("MARKETING", BODY, 1)
    with pytest.raises(Invalid, match="No existe"):
        campaigns.template_info([tpl], "demo", "en_US")
    with pytest.raises(Invalid, match="aprobada"):
        campaigns.template_info([{**tpl, "status": "PENDING"}], "demo", "es_AR")
    image = {**tpl, "components": [{"type": "HEADER", "format": "IMAGE"}, {"type": "BODY", "text": BODY}]}
    with pytest.raises(Invalid, match="imagen"):
        campaigns.template_info([image], "demo", "es_AR")
    dyn = {**tpl, "components": [{"type": "BODY", "text": BODY}, {"type": "BUTTONS", "buttons": [
        {"type": "URL", "text": "Ver", "url": "https://x.com/{{1}}"}]}]}
    with pytest.raises(Invalid, match="botones"):
        campaigns.template_info([dyn], "demo", "es_AR")


def test_template_payload_buttons():
    payload = signup.template_payload(
        name="demo", language="es_AR", category="MARKETING", body="Probá", examples=[],
        buttons=[{"type": "QUICK_REPLY", "text": "No me interesa"},
                 {"type": "URL", "text": "Probar la demo", "url": "https://atentina.com.ar"}])
    assert payload["components"][-1] == {"type": "BUTTONS", "buttons": [
        {"type": "URL", "text": "Probar la demo", "url": "https://atentina.com.ar"},
        {"type": "QUICK_REPLY", "text": "No me interesa"}]}
    with pytest.raises(Invalid, match="https"):
        signup.template_payload(name="d", language="es_AR", category="MARKETING", body="x", examples=[],
                                buttons=[{"type": "URL", "text": "Ver", "url": "http://x.com"}])


# ---------- API ----------

@pytest.fixture
def account(meta, acme):  # noqa: F811
    """Un numero conectado por Embedded Signup (token propio) y una plantilla aprobada."""
    meta.templates.append({"id": "t9", "name": "demo", "language": "es_AR", "category": "MARKETING",
                           "status": "APPROVED", "components": [{"type": "BODY", "text": BODY}]})
    c, agent, user = acme
    return user, signup_ok(user, agent), c


def campaign_body(acc, **extra):
    return {"account_id": acc["id"], "name": "Prospectos octubre", "template_name": "demo",
            "csv": "telefono,nombre\n351 555-1234,Ana\n3515551234,Ana repetida\n555,Mal\n351 555-0000,\n", **extra}


def test_create_campaign_loads_recipients(api, account):
    user, acc, _ = account
    r = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(
        acc, recipients=[{"phone": "+54 9 11 2345-6789", "params": ["Juan"]}]))
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["added"] == 2
    assert [(x["phone"], x["line"]) for x in out["skipped"]] == [
        ("3515551234", 3), ("555", 4), ("351 555-0000", 5)]
    assert "repetido" in out["skipped"][0]["reason"] and "variables" in out["skipped"][2]["reason"]
    c = out["campaign"]
    assert (c["status"], c["template_body"], c["template_params"], c["template_category"]) == (
        "draft", BODY, 1, "MARKETING")
    assert c["stats"]["total"] == 2 and c["stats"]["pending"] == 2
    assert c["agent_name"] == "Ventas" and c["display_phone_number"]

    page = user.get(f"{V1}/whatsapp/campaigns/{c['id']}/recipients").json()
    assert page["total"] == 2
    assert [(i["wa_id"], i["params"], i["status"]) for i in page["items"]] == [
        ("5491123456789", ["Juan"], "pending"), ("5493515551234", ["Ana"], "pending")]
    assert [x["id"] for x in user.get(f"{V1}/whatsapp/campaigns").json()] == [c["id"]]


def test_create_campaign_rejects_unapproved_template(api, meta, account):  # noqa: F811
    user, acc, _ = account
    r = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc, template_name="promo"))
    assert r.status_code == 422 and "aprobada" in r.json()["detail"]
    meta.fail["list_templates"] = GraphError("caido", code=2)
    assert user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc)).status_code == 502


def test_campaign_permissions(api, admin, account):  # noqa: F811
    user, acc, c = account
    created = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc)).json()["campaign"]
    other = client_user(api, admin, make_client(admin, slug="otro"), email="otro@x.com")
    assert other.get(f"{V1}/whatsapp/campaigns/{created['id']}").status_code == 404
    assert other.get(f"{V1}/whatsapp/campaigns").json() == []
    # Numero de alta manual (WABA de la plataforma): el cliente no manda campañas.
    agent = make_agent(admin, c, template="demo_booking", name="Otro")
    manual = admin.post(f"{V1}/whatsapp/accounts", json={
        "client_id": c["id"], "agent_id": agent["id"], "phone_number_id": "999", "waba_id": "888",
        "display_phone_number": "+54 351 000"}).json()
    assert user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(manual)).status_code == 403


def test_campaign_lifecycle(api, account):
    user, acc, _ = account
    c = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc)).json()["campaign"]
    url = f"{V1}/whatsapp/campaigns/{c['id']}"
    assert user.post(f"{url}/pause").status_code == 409
    r = user.patch(url, json={"window_start": 20, "window_end": 10})
    assert r.status_code == 422
    assert user.patch(url, json={"rate_per_minute": 5, "name": "Otra"}).json()["rate_per_minute"] == 5

    started = user.post(f"{url}/start").json()
    assert started["status"] == "running" and started["started_at"]
    assert user.post(f"{url}/recipients", json={"csv": "telefono,nombre\n3519990000,Eva"}).status_code == 409
    assert user.delete(url).status_code == 409
    assert user.post(f"{url}/pause").json()["status"] == "paused"
    assert user.post(f"{url}/recipients", json={"csv": "telefono,nombre\n3519990000,Eva"}).json()["added"] == 1
    cancelled = user.post(f"{url}/cancel").json()
    assert cancelled["status"] == "cancelled" and cancelled["stats"]["skipped"] == 2
    assert user.post(f"{url}/start").status_code == 409

    draft = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc, csv=None)).json()["campaign"]
    assert user.post(f"{V1}/whatsapp/campaigns/{draft['id']}/start").status_code == 409   # sin contactos
    assert user.delete(f"{V1}/whatsapp/campaigns/{draft['id']}").status_code == 204


def test_start_rechecks_template(api, meta, account):  # noqa: F811
    user, acc, _ = account
    c = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc)).json()["campaign"]
    meta.templates[-1]["status"] = "PAUSED"
    r = user.post(f"{V1}/whatsapp/campaigns/{c['id']}/start")
    assert r.status_code == 422 and "PAUSED" in r.json()["detail"]


def test_optouts_api(api, account):
    user, acc, _ = account
    r = user.post(f"{V1}/whatsapp/optouts", json={"phone": "351 555-1234"})
    assert r.status_code == 201 and r.json()["wa_id"] == "5493515551234"
    assert user.post(f"{V1}/whatsapp/optouts", json={"phone": "123"}).status_code == 422
    out = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc)).json()
    assert out["added"] == 0 and out["skipped"][0]["reason"] == "pidió la baja"
    assert [o["wa_id"] for o in user.get(f"{V1}/whatsapp/optouts").json()] == ["5493515551234"]
    assert user.delete(f"{V1}/whatsapp/optouts/5493515551234").status_code == 204
    assert user.get(f"{V1}/whatsapp/optouts").json() == []


# ---------- envio ----------

class CampaignGraph(FakeGraph):
    def __init__(self):
        super().__init__()
        self.templates: list[tuple] = []
        self.fail_template: GraphError | None = None

    async def send_template(self, pnid, to, name, language, params=None):
        if self.fail_template:
            raise self.fail_template
        self.templates.append((pnid, to, name, language, params))
        return {"messaging_product": "whatsapp", "messages": [{"id": f"wamid.tpl{len(self.templates)}"}]}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make_campaign(w, *phones, status="running", agent_id=None, rate=60, window=(0, 24), body=BODY) -> str:
    with w.sessions() as s:
        c = WaCampaign(client_id=w.client_id, account_id=w.account_id, agent_id=agent_id, name="C",
                       template_name="demo", template_language="es_AR", template_category="MARKETING",
                       template_body=body, template_params=1, status=status, rate_per_minute=rate,
                       window_start=window[0], window_end=window[1])
        s.add(c)
        s.flush()
        for i, phone in enumerate(phones):
            s.add(WaCampaignRecipient(campaign_id=c.id, wa_id=phone, params=[f"Ana{i}"]))
        s.commit()
        return c.id


def recipients(sessions, campaign_id) -> list[WaCampaignRecipient]:
    with sessions() as s:
        return list(s.scalars(select(WaCampaignRecipient).where(WaCampaignRecipient.campaign_id == campaign_id)
                              .order_by(WaCampaignRecipient.created_at)))


def campaign(sessions, campaign_id) -> WaCampaign:
    with sessions() as s:
        return s.get(WaCampaign, campaign_id)


def sender_for(w, hour=12, clock=None) -> CampaignSender:
    return CampaignSender(w.sessions, graph_factory=lambda token: w.graph, hour=lambda: hour, clock=clock or Clock())


async def test_sender_respects_rate_and_finishes(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001", "5493515550002", rate=12)    # 1 por cada 5 s
    clock = Clock()
    sender = sender_for(w, clock=clock)
    assert await sender.tick() == 1
    assert await sender.tick() == 0      # sin tiempo transcurrido no hay credito
    clock.t += 10
    assert await sender.tick() == 2
    assert w.graph.templates[0] == (PNID, SEND_TO, "demo", "es_AR", ["Ana0"])
    assert [r.status for r in recipients(sessions, cid)] == ["sent"] * 3
    (first, *_) = recipients(sessions, cid)
    assert first.wamid == "wamid.tpl1" and first.sent_at is not None
    out = messages(sessions, direction="out")
    assert {(m.type, m.status, m.conversation_id) for m in out} == {("template", "sent", None)}
    clock.t += 10
    assert await sender.tick() == 0
    assert campaign(sessions, cid).status == "done" and campaign(sessions, cid).finished_at


async def test_sender_waits_for_the_window(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    make_campaign(w, WA_ID, window=(9, 20))
    assert await sender_for(w, hour=21).tick() == 0
    assert await sender_for(w, hour=8).tick() == 0
    assert await sender_for(w, hour=9).tick() == 1


async def test_sender_skips_optouts_and_paused(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001")
    with sessions() as s:
        campaigns.add_optout(s, w.client_id, WA_ID, "manual")
        s.commit()
    paused = make_campaign(w, "5493515550009", status="paused")
    await sender_for(w).tick()
    assert [(r.wa_id, r.status) for r in recipients(sessions, cid)] == [
        (WA_ID, "skipped"), ("5493515550001", "sent")]
    assert [r.status for r in recipients(sessions, paused)] == ["pending"]


async def test_sender_meta_errors(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001", "5493515550002", rate=12)   # 1 por vuelta de 5 s
    clock = Clock()
    sender = sender_for(w, clock=clock)
    # Numero invalido: ese contacto falla y la campaña sigue.
    w.graph.fail_template = GraphError("Invalid parameter", code=100)
    await sender.tick()
    assert [r.status for r in recipients(sessions, cid)] == ["failed", "pending", "pending"]
    assert recipients(sessions, cid)[0].error["code"] == 100
    assert messages(sessions, direction="out", status="failed")[0].type == "template"
    # Limite momentaneo: vuelve a pendiente y la campaña espera un minuto.
    w.graph.fail_template = GraphError("Rate limit", code=130429)
    clock.t += 5
    await sender.tick()
    assert [r.status for r in recipients(sessions, cid)][1:] == ["pending", "pending"]
    w.graph.fail_template = None
    clock.t += 5
    assert await sender.tick() == 0
    clock.t += 60
    assert await sender.tick() == 2
    assert campaign(sessions, cid).status == "running"


async def test_sender_pauses_on_template_or_token_problems(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001")
    w.graph.fail_template = GraphError("Template paused", code=132015)
    assert await sender_for(w).tick() == 0
    c = campaign(sessions, cid)
    assert c.status == "paused" and "baja calidad" in c.status_reason and "132015" in c.status_reason
    assert [r.status for r in recipients(sessions, cid)] == ["pending", "pending"]
    # El numero desactivado tambien la pausa, sin llamar a Meta.
    other = make_campaign(w, "5493515550002")
    from app.models import WaAccount
    with sessions() as s:
        s.get(WaAccount, w.account_id).active = False
        s.commit()
    w.graph.fail_template = None
    await sender_for(w).tick()
    assert campaign(sessions, other).status == "paused" and w.graph.templates == []


async def test_recover_marks_inflight_as_failed(sessions):
    w = make_wa(sessions, graph=CampaignGraph())
    cid = make_campaign(w, WA_ID)
    with sessions() as s:
        s.scalar(select(WaCampaignRecipient)).status = "sending"
        s.commit()
    assert sender_for(w).recover() == 1
    assert recipients(sessions, cid)[0].status == "failed"


# ---------- respuestas y bajas ----------

async def test_reply_opens_conversation_with_the_template(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("¡Genial! ¿Querés que te llame?")), graph=CampaignGraph())
    cid = make_campaign(w, WA_ID)
    await sender_for(w).tick()
    await send(w, status_payload("status_read.json", "wamid.tpl1"))
    await send(w, text_payload("sí, contame", "wamid.in1"))

    (conv,) = conversations(sessions)
    assert [(m["role"], m["text"]) for m in conv.messages][:2] == [
        ("assistant", "Hola Ana0, probá gratis nuestro agente de voz."), ("user", "sí, contame")]
    (r,) = recipients(sessions, cid)
    assert r.conversation_id == conv.id and r.replied_at is not None
    with sessions() as s:
        st = campaigns.stats(s, [cid])[cid]
    assert (st["sent"], st["delivered"], st["read"], st["replied"]) == (1, 1, 1, 1)

    # El siguiente mensaje sigue en la misma conversacion (no vuelve a usar la plantilla).
    w.llm.turns.append(reply("Dale"))
    await send(w, text_payload("a la tarde", "wamid.in2"))
    assert len(conversations(sessions)) == 1


async def test_reply_uses_the_campaign_agent(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()), graph=CampaignGraph())
    from app.agents.templates import reference_data
    from app.models import Client
    from app.services import agents as agent_service
    with sessions() as s:
        other = agent_service.create_agent(s, s.get(Client, w.client_id), name="Ventas", slug="ventas",
                                           description="", definition=reference_data("demo_booking_classic"),
                                           template_id=None, user_id=None)
        s.commit()
        other_id = other.id
    make_campaign(w, WA_ID, agent_id=other_id)
    await sender_for(w).tick()
    await send(w, text_payload("hola", "wamid.in1"))
    (conv,) = conversations(sessions)
    assert conv.agent_id == other_id


async def test_inbound_without_campaign_has_no_opening(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()), graph=CampaignGraph())
    make_campaign(w, "5493515550001")
    await sender_for(w).tick()
    await send(w, text_payload("hola", "wamid.in1"))
    (conv,) = conversations(sessions)
    assert conv.messages[0]["role"] == "user"


async def test_optout_reply(sessions):
    w = make_wa(sessions, llm=FakeLLM(), graph=CampaignGraph())
    make_campaign(w, WA_ID)
    await sender_for(w).tick()
    await send(w, text_payload("No me interesa", "wamid.in1"))
    assert w.graph.sent == [(PNID, SEND_TO, "Listo, no te vamos a escribir más. ¡Gracias!")]
    assert conversations(sessions) == [] and w.llm.calls == []
    with sessions() as s:
        assert s.get(WaOptout, (w.client_id, WA_ID)).source == "keyword"
    # Otra campaña no le escribe.
    cid = make_campaign(w, WA_ID)
    await sender_for(w).tick()
    assert recipients(sessions, cid)[0].status == "skipped"


async def test_optout_text_without_campaign_goes_to_the_agent(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("¿Seguro?")))
    await send(w, text_payload("baja", "wamid.in1"))
    assert w.graph.sent == [(PNID, SEND_TO, "¿Seguro?")]
    with sessions() as s:
        assert s.scalars(select(WaOptout)).all() == []


def test_campaign_conversation_row_count(sessions):
    """Las conversaciones solo se crean al responder: una campaña sin respuestas no llena el dashboard."""
    w = make_wa(sessions, graph=CampaignGraph())
    make_campaign(w, WA_ID)
    with sessions() as s:
        assert s.scalars(select(ConversationRow)).all() == []
        assert s.scalars(select(WaMessage)).all() == []
