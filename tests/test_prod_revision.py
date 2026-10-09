"""Correcciones de la revision de produccion (8-oct-2026): tope global de sintesis fuera de
llamadas (la demo comparte el de /tts/preview) y de turnos de texto por la API (H04), cliente
inactivo en solo lectura tambien para ediciones y la extraccion final de WhatsApp (H12),
Idempotency-Key con huella del pedido y reintento despues de un dispatch_failed, retencion de
telefonos, numeros de WhatsApp y variables de campañas, y /health/ready solo local."""
import asyncio
import datetime
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.config import settings
from app.conversation.models import AgentTurn
from app.db import utcnow
from app.models import (
    Agent,
    CallRow,
    Client,
    ConversationRow,
    Tier,
    WaAccount,
    WaCampaign,
    WaCampaignRecipient,
    WaMessage,
    WaOptout,
    WaThread,
)
from app.services import livekit, tts
from app.services.retention import purge

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
)
from .test_demo import landing, session  # noqa: F401  (landing: fixture)

PHONE = "+5491155551234"


def _fake_preview(calls: list):
    async def fake(voice, text):
        calls.append((voice, text))

        async def stream():
            yield b"RIFF"
            yield b"data"
        return stream()
    return fake


# ---------- H04: demo publica con el cupo global del TTS ----------

def test_demo_tts_shares_global_slots(landing, monkeypatch):  # noqa: F811
    calls = []
    monkeypatch.setattr(tts, "preview", _fake_preview(calls))
    headers = session(landing)
    cached = {"voice": "sofia", "text": "Hola"}
    assert landing.client.post("/api/v1/demo/tts", json=cached, headers=headers).content == b"RIFFdata"
    assert tts.PreviewSlots.in_use == 0

    monkeypatch.setattr(tts.PreviewSlots, "in_use", settings.tts_preview_max_concurrent)
    r = landing.client.post("/api/v1/demo/tts", json={"voice": "sofia", "text": "Otro texto"}, headers=headers)
    assert r.status_code == 503 and r.json()["code"] == "tts_busy" and int(r.headers["Retry-After"]) > 0
    # Lo que ya esta en cache no usa el TTS: sale aunque el cupo este lleno.
    assert landing.client.post("/api/v1/demo/tts", json=cached, headers=headers).status_code == 200
    assert len(calls) == 1


def test_demo_tts_capped_per_session(landing, monkeypatch):  # noqa: F811
    """Un Turnstile resuelto no sirve para sintetizar sin limite desde muchas IP."""
    monkeypatch.setattr(tts, "preview", _fake_preview([]))
    monkeypatch.setattr(settings, "demo_ip_tts_per_hour", 100)
    monkeypatch.setattr(settings, "demo_session_tts_max", 2)
    headers = session(landing)
    for i in range(2):
        r = landing.client.post("/api/v1/demo/tts", json={"voice": "sofia", "text": f"t{i}"}, headers=headers)
        assert r.status_code == 200
    r = landing.client.post("/api/v1/demo/tts", json={"voice": "sofia", "text": "t3"}, headers=headers)
    assert r.status_code == 429
    other = session(landing)
    assert landing.client.post("/api/v1/demo/tts", json={"voice": "sofia", "text": "t3"},
                               headers=other).status_code == 200


# ---------- H04: turnos de texto por la API ----------

def test_api_text_turns_global_cap(api, admin, monkeypatch):  # noqa: F811
    from app.api.routers import conversations as router

    agent = make_agent(admin, make_client(admin))
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    monkeypatch.setattr(router._TurnSlots, "in_use", settings.api_max_concurrent_turns)
    r = admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Hola"})
    assert r.status_code == 503 and r.json()["code"] == "llm_busy" and int(r.headers["Retry-After"]) > 0
    assert conv not in router._in_progress

    monkeypatch.setattr(router._TurnSlots, "in_use", 0)
    api.llm.turns = [AgentTurn(assistant_message="Hola, ¿en qué te ayudo?")]
    assert admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Hola"}).status_code == 200
    assert router._TurnSlots.in_use == 0

    async def broken(*a, **kw):
        raise RuntimeError("vllm caido")

    monkeypatch.setattr(api.engine, "process_turn", broken)
    assert admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Hola"}).status_code == 502
    assert router._TurnSlots.in_use == 0          # el cupo se devuelve aunque falle


# ---------- H12: inactivo = solo lectura ----------

def _deactivate(admin, c):  # noqa: F811
    assert admin.patch(f"{V1}/clients/{c['id']}", json={"active": False}).status_code == 200


def test_admin_cannot_consume_llm_for_inactive_client(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    _deactivate(admin, c)
    for path, body in ((f"/conversations/{conv}/turns", {"message": "Hola"}),
                       ("/conversations", {"agent_id": agent["id"]})):
        r = admin.post(f"{V1}{path}", json=body)
        assert r.status_code == 403 and r.json()["code"] == "client_inactive", path


def test_inactive_client_cannot_edit_agents_or_route_numbers(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    r = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541100000001"})
    number = r.json()
    ana = client_user(api, admin, c)
    _deactivate(admin, c)
    detail = admin.get(f"{V1}/agents/{agent['id']}").json()
    denied = [("POST", "/agents", {"name": "Otro", "template_id": "asistente"}),
              ("PATCH", f"/agents/{agent['id']}", {"name": "X"}),
              ("PUT", f"/agents/{agent['id']}/definition", {"definition": detail["definition"]}),
              ("DELETE", f"/agents/{agent['id']}", None),
              ("PATCH", f"/phone-numbers/{number['id']}", {"agent_id": agent["id"]})]
    for method, path, body in denied:
        r = ana.request(method, f"{V1}{path}", json=body)
        assert r.status_code == 403 and r.json()["code"] == "client_inactive", (path, r.text)
    # Lo ve igual, y el admin puede preparar sus agentes antes de reactivarlo.
    assert ana.get(f"{V1}/agents/{agent['id']}").status_code == 200
    assert admin.patch(f"{V1}/agents/{agent['id']}", json={"name": "Nuevo"}).status_code == 200


def _wa_setup(api, client_id: str, agent_id: str) -> tuple[str, str]:
    with api.sessions() as s:
        acc = WaAccount(client_id=client_id, agent_id=agent_id, phone_number_id=uuid.uuid4().hex[:12],
                        waba_id="1", display_phone_number="+1")
        s.add(acc)
        s.flush()
        camp = WaCampaign(client_id=client_id, account_id=acc.id, name="C", template_name="t",
                          template_language="es_AR")
        s.add(camp)
        s.commit()
        return acc.id, camp.id


def test_inactive_client_whatsapp_writes(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    acc, camp = _wa_setup(api, c["id"], agent["id"])
    with api.sessions() as s:
        s.add(WaOptout(client_id=c["id"], wa_id="5491155551234", source="manual"))
        s.commit()
    _deactivate(admin, c)
    denied = [("PATCH", f"/whatsapp/accounts/{acc}", {"active": True}),
              ("PATCH", f"/whatsapp/accounts/{acc}", {"name": "Otro"}),
              ("PATCH", f"/whatsapp/campaigns/{camp}", {"name": "Otra"}),
              ("DELETE", f"/whatsapp/optouts/5491155551234?client_id={c['id']}", None)]
    for method, path, body in denied:
        r = admin.request(method, f"{V1}{path}", json=body)
        assert r.status_code == 403 and r.json()["code"] == "client_inactive", (path, r.text)
    # Apagar el numero y sumar una baja protegen: se pueden.
    assert admin.patch(f"{V1}/whatsapp/accounts/{acc}", json={"active": False}).status_code == 200
    r = admin.post(f"{V1}/whatsapp/optouts", json={"client_id": c["id"], "phone": "+5491155550000"})
    assert r.status_code == 201, r.text


def test_whatsapp_end_skips_extraction_for_inactive_client(api, admin, monkeypatch):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    finished = []

    async def finish(conversation_id, *a, **kw):
        finished.append(conversation_id)

    monkeypatch.setattr(api.engine, "finish", finish)
    asyncio.run(api.wa_service._end(conv))
    assert finished == [conv]
    _deactivate(admin, c)
    asyncio.run(api.wa_service._end(conv))
    assert finished == [conv]                     # sin otra extraccion con el LLM


# ---------- Idempotency-Key ----------

def test_idempotency_key_compares_whole_request(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    first_n = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541100000001"}).json()
    second_n = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541100000002"}).json()
    h = {"Idempotency-Key": "k1"}
    body = {"agent_id": agent["id"], "phone": PHONE, "from_number_id": first_n["id"]}
    assert admin.post(f"{V1}/calls", json=body, headers=h).status_code == 201
    assert admin.post(f"{V1}/calls", json=body, headers=h).status_code == 200
    for change in ({"from_number_id": second_n["id"]}, {"voice": "martin"}):
        r = admin.post(f"{V1}/calls", json={**body, **change}, headers=h)
        assert r.status_code == 409 and r.json()["code"] == "idempotency_key_reused", change
    h2 = {"Idempotency-Key": "k2"}
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}, headers=h2).status_code == 201
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "loadtest": True}, headers=h2)
    assert r.status_code == 409 and r.json()["code"] == "idempotency_key_reused"
    assert len(api.dispatched) == 2


def test_idempotency_retry_after_dispatch_failed_dials(api, admin, monkeypatch):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541100000001"})
    real = livekit.dispatch_call

    async def down(room, metadata):
        raise ConnectionError("livekit caido")

    monkeypatch.setattr(livekit, "dispatch_call", down)
    h = {"Idempotency-Key": "reintento"}
    body = {"agent_id": agent["id"], "phone": PHONE}
    failed = admin.post(f"{V1}/calls", json=body, headers=h)
    assert failed.status_code == 502
    monkeypatch.setattr(livekit, "dispatch_call", real)
    r = admin.post(f"{V1}/calls", json=body, headers=h)
    assert r.status_code == 201 and len(api.dispatched) == 1
    assert admin.post(f"{V1}/calls", json=body, headers=h).status_code == 200    # y despues, idempotente
    with api.sessions() as s:
        rows = {row.status: row for row in s.scalars(select(CallRow))}
        assert rows["fallida"].ended_reason == "dispatch_failed" and rows["fallida"].idempotency_key is None
        assert rows["pendiente"].idempotency_key == "reintento"


# ---------- retencion ----------

def _retention_client(sessions, days: int) -> tuple[str, str]:
    with sessions() as s:
        tier = Tier(name=f"T{uuid.uuid4().hex[:6]}", retention_days=days)
        s.add(tier)
        s.flush()
        slug = uuid.uuid4().hex[:8]
        client = Client(name=slug, slug=slug, tier_id=tier.id)
        s.add(client)
        s.flush()
        agent = Agent(client_id=client.id, slug="a", name="A", definition={})
        s.add(agent)
        s.flush()
        acc = WaAccount(client_id=client.id, agent_id=agent.id, phone_number_id=uuid.uuid4().hex[:12],
                        waba_id="1", display_phone_number="+1")
        s.add(acc)
        s.commit()
        return client.id, acc.id


def test_retention_masks_phones_and_campaign_data(sessions, monkeypatch):
    monkeypatch.setattr(settings, "wa_campaign_reply_days", 7)
    client_id, acc = _retention_client(sessions, days=30)
    old = utcnow() - datetime.timedelta(days=40)
    with sessions() as s:
        for cid, channel in (("c-voz", "voice"), ("c-wa", "whatsapp"), ("c-new", "voice")):
            s.add(ConversationRow(id=cid, client_id=client_id, channel=channel, status="completed",
                                  messages=[{"role": "user", "text": "hola"}], fields={}, progress={}))
        s.flush()
        s.add(CallRow(conversation_id="c-voz", client_id=client_id, mode="saliente", phone="+5493510001234",
                      status="finalizada", duration_seconds=95))
        s.add(CallRow(conversation_id="c-new", client_id=client_id, mode="entrante", phone="+5493510009999",
                      status="finalizada", duration_seconds=10))
        s.add(WaThread(conversation_id="c-wa", account_id=acc, client_id=client_id, wa_id="5493510005678",
                       contact_name="Ana", last_user_at=old))
        s.add(WaMessage(wamid="w1", account_id=acc, direction="in", wa_id="5493510005678", type="text",
                        status="answered", body={"x": 1}, created_at=old))
        s.add(WaMessage(wamid="w-orphan", account_id=None, direction="in", wa_id="5493510004321", type="text",
                        status="error", body={"x": 1}, created_at=utcnow() - datetime.timedelta(days=60)))
        done = WaCampaign(client_id=client_id, account_id=acc, name="Cobranza", template_name="t",
                          template_language="es_AR", status="done", finished_at=old)
        recent = WaCampaign(client_id=client_id, account_id=acc, name="Nueva", template_name="t",
                            template_language="es_AR", status="done", finished_at=utcnow())
        s.add_all([done, recent])
        s.flush()
        s.add(WaCampaignRecipient(campaign_id=done.id, wa_id="5493510005678", name="Ana",
                                  params=["Ana", "$ 12.000"], status="sent"))
        s.add(WaCampaignRecipient(campaign_id=recent.id, wa_id="5493510005678", name="Ana",
                                  params=["Ana", "$ 3.000"], status="sent"))
        s.commit()
        s.execute(update(ConversationRow).where(ConversationRow.id.in_(["c-voz", "c-wa"])).values(updated_at=old))
        s.commit()

    totals = purge(sessions)
    assert totals == {"conversations": 2, "wa_bodies": 1, "campaign_recipients": 1, "wa_orphans": 1}
    with sessions() as s:
        calls = {c.conversation_id: c for c in s.scalars(select(CallRow))}
        assert calls["c-voz"].phone == "***1234" and calls["c-voz"].duration_seconds == 95
        assert calls["c-new"].phone == "+5493510009999"            # dentro de la retencion
        thread = s.get(WaThread, "c-wa")
        assert (thread.wa_id, thread.contact_name) == ("***5678", None)
        msgs = {m.wamid: m for m in s.scalars(select(WaMessage))}
        assert (msgs["w1"].body, msgs["w1"].wa_id) == (None, "***5678")
        assert (msgs["w-orphan"].body, msgs["w-orphan"].wa_id) == (None, "***4321")
        recips = {r.campaign_id: r for r in s.scalars(select(WaCampaignRecipient))}
        assert (recips[done.id].name, recips[done.id].params) == (None, [])
        assert recips[done.id].wa_id == "5493510005678"             # la baja por texto lo necesita
        assert recips[recent.id].params == ["Ana", "$ 3.000"]
    assert not any(purge(sessions).values())                        # idempotente


def test_retention_orphans_without_client_retention(sessions, monkeypatch):
    """Los entrantes sin cuenta tienen tope de la plataforma aunque ningun cliente tenga dias."""
    monkeypatch.setattr(settings, "retention_orphan_wa_days", 30)
    with sessions() as s:
        s.add(WaMessage(wamid="o1", account_id=None, direction="in", wa_id="5491100001111", type="text",
                        status="error", body={"x": 1}, created_at=utcnow() - datetime.timedelta(days=31)))
        s.add(WaMessage(wamid="o2", account_id=None, direction="in", wa_id="5491100002222", type="text",
                        status="error", body={"x": 1}, created_at=utcnow() - datetime.timedelta(days=5)))
        s.commit()
    assert purge(sessions)["wa_orphans"] == 1
    with sessions() as s:
        assert s.get(WaMessage, s.scalar(select(WaMessage.id).where(WaMessage.wamid == "o2"))).body == {"x": 1}


# ---------- /health/ready solo local ----------

def test_health_ready_only_local(api):
    local = TestClient(api.app, client=("127.0.0.1", 50000))
    assert local.get("/health/ready").status_code == 200
    # Por el tunel (cloudflared entra por localhost con CF-Connecting-IP) o desde otra IP: no.
    r = local.get("/health/ready?inference=true", headers={"CF-Connecting-IP": "203.0.113.9"})
    assert r.status_code == 403 and "checks" not in r.text
    lan = TestClient(api.app, client=("192.168.1.50", 50000))
    assert lan.get("/health/ready").status_code == 403
    assert api.client.get("/health").json() == {"ok": True}       # liveness sigue publico
