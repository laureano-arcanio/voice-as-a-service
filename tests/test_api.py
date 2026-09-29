"""API: auth, permisos por cliente, tiers, clientes, agentes versionados, numeros y llamadas."""
import pytest

from app.conversation.models import AgentTurn
from app.models import CallMode, CallRow, CallStatus, Role, User
from app.services.security import hash_password

V1 = "/api/v1"
ADMIN = ("admin@example.com", "admin-password-1")


@pytest.fixture
def admin(api):
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    return api.login(*ADMIN)


def make_tier(admin, **limits):
    r = admin.post(f"{V1}/tiers", json={"name": limits.pop("name", "Pyme"), **limits})
    assert r.status_code == 201, r.text
    return r.json()


def make_client(admin, slug="acme", tier=None, **tier_limits):
    tier = tier or make_tier(admin, name=f"tier-{slug}", **tier_limits)
    r = admin.post(f"{V1}/clients", json={"name": slug.title(), "slug": slug, "tier_id": tier["id"]})
    assert r.status_code == 201, r.text
    return r.json()


def make_agent(admin, client, template="sales_discovery", **extra):
    r = admin.post(f"{V1}/agents", json={"client_id": client["id"], "name": "Ventas", "template_id": template, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def client_user(api, admin, client, email="ana@acme.com"):
    r = admin.post(f"{V1}/users", json={"email": email, "password": "cliente-password-1", "role": "client",
                                         "client_id": client["id"]})
    assert r.status_code == 201, r.text
    return api.login(email, "cliente-password-1")


# ---------- auth ----------

def test_login_me_logout(api, admin):
    me = admin.get(f"{V1}/auth/me").json()
    assert me["email"] == ADMIN[0] and me["role"] == "admin" and me["client_id"] is None
    assert admin.post(f"{V1}/auth/logout").status_code == 204
    assert admin.get(f"{V1}/auth/me").status_code == 401


def test_login_rejects_bad_password_and_unknown_email(api, admin):
    assert api.client.post(f"{V1}/auth/login", json={"email": ADMIN[0], "password": "nope"}).status_code == 401
    r = api.client.post(f"{V1}/auth/login", json={"email": "otro@example.com", "password": "nope"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"


def test_requires_auth(api):
    assert api.client.get(f"{V1}/agents").status_code == 401


def test_deactivated_user_loses_access(api, admin):
    c = make_client(admin)
    user = client_user(api, admin, c)
    uid = user.get(f"{V1}/auth/me").json()["id"]
    admin.patch(f"{V1}/users/{uid}", json={"active": False})
    assert user.get(f"{V1}/auth/me").status_code == 401


def test_api_key_auth_and_revoke(api, admin):
    c = make_client(admin)
    created = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "crm"}).json()
    assert created["key"].startswith("vaas_") and created["prefix"] == created["key"][:12]
    headers = {"Authorization": f"Bearer {created['key']}"}
    assert api.client.get(f"{V1}/agents", headers=headers).status_code == 200
    # Una API key no administra API keys ni ve otros clientes.
    assert api.client.get(f"{V1}/clients/{c['id']}/api-keys", headers=headers).status_code == 403
    admin.delete(f"{V1}/clients/{c['id']}/api-keys/{created['id']}")
    assert api.client.get(f"{V1}/agents", headers=headers).status_code == 401


# ---------- permisos ----------

def test_client_user_sees_only_its_client(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    make_agent(admin, acme)
    other_agent = make_agent(admin, other)
    user = client_user(api, admin, acme)
    assert [c["slug"] for c in user.get(f"{V1}/clients").json()] == ["acme"]
    assert {a["client_id"] for a in user.get(f"{V1}/agents").json()} == {acme["id"]}
    assert user.get(f"{V1}/agents", params={"client_id": other["id"]}).status_code == 403
    # Recurso de otro cliente: 404, no se revela que existe.
    assert user.get(f"{V1}/agents/{other_agent['id']}").status_code == 404
    assert user.get(f"{V1}/clients/{other['id']}/usage").status_code == 404


def test_client_user_cannot_administer(api, admin):
    acme = make_client(admin)
    user = client_user(api, admin, acme)
    assert user.get(f"{V1}/tiers").status_code == 403
    assert user.post(f"{V1}/agents", json={"client_id": acme["id"], "name": "x", "template_id": "demo_booking"}
                     ).status_code == 403
    assert user.patch(f"{V1}/clients/{acme['id']}", json={"active": False}).status_code == 403


# ---------- tiers y clientes ----------

def test_tier_crud_and_in_use(api, admin):
    tier = make_tier(admin, name="Basico", max_concurrent_calls=2, inbound_minutes=100)
    assert tier["outbound_minutes"] is None
    assert admin.post(f"{V1}/tiers", json={"name": "Basico"}).status_code == 409
    upd = admin.patch(f"{V1}/tiers/{tier['id']}", json={"inbound_minutes": None, "outbound_minutes": 50}).json()
    assert upd["inbound_minutes"] is None and upd["outbound_minutes"] == 50 and upd["max_concurrent_calls"] == 2
    make_client(admin, tier=tier)
    assert admin.delete(f"{V1}/tiers/{tier['id']}").status_code == 409
    assert admin.post(f"{V1}/tiers", json={"name": "x", "inbound_minutes": -1}).status_code == 422


def test_client_create_and_change_tier(api, admin):
    c = make_client(admin)
    assert admin.post(f"{V1}/clients", json={"name": "A", "slug": "acme", "tier_id": c["tier"]["id"]}
                      ).status_code == 409
    assert admin.post(f"{V1}/clients", json={"name": "A", "slug": "Mal Slug", "tier_id": c["tier"]["id"]}
                      ).status_code == 422
    gold = make_tier(admin, name="Gold")
    assert admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": gold["id"]}).json()["tier"]["name"] == "Gold"


def test_client_with_conversations_cannot_be_deleted(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    admin.post(f"{V1}/calls", json={"agent_id": agent["id"]})
    assert admin.delete(f"{V1}/clients/{c['id']}").status_code == 409
    empty = make_client(admin, "vacio")
    assert admin.delete(f"{V1}/clients/{empty['id']}").status_code == 204


# ---------- agentes ----------

def test_agent_from_template_and_versions(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c, template="demo_booking")
    assert agent["slug"] == "ventas" and agent["version"] == 1 and agent["engine"] == "structured"
    assert agent["definition"]["id"] == "ventas" and agent["voice"] == "sofia"

    definition = agent["definition"]
    definition["conversation"]["opening"] = "Hola, soy Sofía."
    v2 = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition}).json()
    assert v2["version"] == 2 and v2["definition"]["version"] == 2
    # Sin cambios no crea version.
    same = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": v2["definition"]}).json()
    assert same["version"] == 2
    versions = admin.get(f"{V1}/agents/{agent['id']}/versions").json()
    assert [v["version"] for v in versions] == [2, 1]
    v1 = admin.get(f"{V1}/agents/{agent['id']}/versions/1").json()
    assert v1["definition"]["conversation"]["opening"] != "Hola, soy Sofía."


def test_invalid_definition_reports_paths(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    bad = {**agent["definition"], "fields": {"Mal Nombre": {"priority": 1, "description": "x", "question": "?"}}}
    r = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": bad})
    assert r.status_code == 422 and r.json()["code"] == "invalid_definition"
    assert any("fields" in e["path"] or "fields" in e["message"] for e in r.json()["errors"])
    no_default = {**agent["definition"]}
    no_default["completion"] = {"outcomes": [{"id": "a", "label": "A", "when": {"contact_name": "x"}, "message": "m"}]}
    check = admin.post(f"{V1}/agents/validate", json={"definition": no_default}).json()
    assert check["valid"] is False and "default" in check["errors"][0]["message"]
    wrong_voice = {**agent["definition"], "agent": {**agent["definition"]["agent"], "voice": "no_existe"}}
    r = admin.post(f"{V1}/agents/validate", json={"definition": wrong_voice}).json()
    assert r["errors"][0]["path"] == "agent.voice"


def test_agent_slug_unique_per_client(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    make_agent(admin, acme)
    assert admin.post(f"{V1}/agents", json={"client_id": acme["id"], "name": "Ventas", "template_id": "demo_booking"}
                      ).status_code == 409
    make_agent(admin, other)


def test_archived_agent_cannot_call_and_used_agent_cannot_be_deleted(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).status_code == 201
    assert admin.delete(f"{V1}/agents/{agent['id']}").status_code == 409
    assert admin.patch(f"{V1}/agents/{agent['id']}", json={"archived": True}).json()["archived"] is True
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).status_code == 409
    assert admin.get(f"{V1}/agents").json() == []
    assert len(admin.get(f"{V1}/agents", params={"include_archived": True}).json()) == 1


def test_templates_and_schema(api, admin):
    templates = {t["id"]: t for t in admin.get(f"{V1}/agent-templates").json()}
    assert templates["demo_booking_classic"]["engine"] == "classic"
    assert admin.get(f"{V1}/agent-templates/demo_booking").json()["id"] == "demo_booking"
    assert "fields" in admin.get(f"{V1}/agents/schema").json()["properties"]


# ---------- numeros ----------

def test_phone_numbers(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    agent, other_agent = make_agent(admin, acme), make_agent(admin, other)
    n = admin.post(f"{V1}/phone-numbers", json={"client_id": acme["id"], "e164": "+541152630861",
                                                 "agent_id": agent["id"]}).json()
    assert n["agent_name"] == "Ventas"
    assert admin.post(f"{V1}/phone-numbers", json={"client_id": other["id"], "e164": "+541152630861"}
                      ).status_code == 409
    assert admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_id": other_agent["id"]}).status_code == 422
    assert admin.post(f"{V1}/phone-numbers", json={"client_id": acme["id"], "e164": "1152630861"}).status_code == 422
    assert admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_id": None}).json()["agent_id"] is None


# ---------- llamadas ----------

def test_test_call_and_outbound_call(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    number = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541100000001"}).json()
    test = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()
    assert test["mode"] == "prueba" and test["join_url"].endswith(test["room"])
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+54 9 11 5555-1234"}).json()
    assert out["mode"] == "saliente" and out["join_url"] is None
    meta = api.dispatched[-1]
    assert meta["phone"] == "+5491155551234" and meta["from_number"] == number["e164"]
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "123"}).status_code == 422
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "voice": "nadie"}).status_code == 422

    page = admin.get(f"{V1}/calls", params={"client_id": c["id"]}).json()
    assert page["total"] == 2 and {i["mode"] for i in page["items"]} == {"prueba", "saliente"}
    detail = admin.get(f"{V1}/calls/{out['conversation_id']}").json()
    assert detail["agent_name"] == "Ventas" and detail["call"]["client_number"] == number["e164"]
    assert admin.get(f"{V1}/stats", params={"client_id": c["id"]}).json()["calls"] == 2


def test_concurrency_limit(api, admin):
    c = make_client(admin, max_concurrent_calls=1)
    agent = make_agent(admin, c)
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).status_code == 201
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]})
    assert r.status_code == 429 and r.json()["code"] == "concurrency_limit"
    with api.sessions() as s:     # termina la primera
        s.query(CallRow).update({"status": CallStatus.finalizada})
        s.commit()
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).status_code == 201


def test_outbound_minutes_limit(api, admin):
    import datetime

    c = make_client(admin, outbound_minutes=1)
    agent = make_agent(admin, c)
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234"})
    assert r.status_code == 201 and api.dispatched[-1]["max_duration_seconds"] == 60
    with api.sessions() as s:
        s.query(CallRow).update({"status": CallStatus.finalizada, "duration_seconds": 60,
                                 "started_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None)})
        s.commit()
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234"})
    assert r.status_code == 429 and r.json()["code"] == "outbound_minutes"
    # Las de prueba no consumen minutos.
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).status_code == 201
    usage = admin.get(f"{V1}/clients/{c['id']}/usage").json()
    assert usage["outbound"] == {"used_seconds": 60, "used_minutes": 1.0, "limit_minutes": 1, "remaining_minutes": 0.0}
    assert usage["inbound"]["limit_minutes"] is None and usage["active_calls"] == 1


def test_inactive_client_cannot_call(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    admin.patch(f"{V1}/clients/{c['id']}", json={"active": False})
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]})
    assert r.status_code == 429 and r.json()["code"] == "client_inactive"


def test_client_api_key_starts_calls_for_its_agents_only(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    mine, theirs = make_agent(admin, acme), make_agent(admin, other)
    key = admin.post(f"{V1}/clients/{acme['id']}/api-keys", json={"name": "crm"}).json()["key"]
    headers = {"Authorization": f"Bearer {key}"}
    assert api.client.post(f"{V1}/calls", json={"agent_id": mine["id"]}, headers=headers).status_code == 201
    assert api.client.post(f"{V1}/calls", json={"agent_id": theirs["id"]}, headers=headers).status_code == 404
    assert api.client.get(f"{V1}/calls", headers=headers).json()["total"] == 1


# ---------- conversacion por texto ----------

def test_text_conversation(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    api.llm.turns = [AgentTurn(next_objective="company_name", assistant_message="¿En qué empresa trabajás?")]
    api.llm.extractions = [{"contact_name": "Juan"}]
    started = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()
    assert started["state"]["agent_version"] == 1 and started["state"]["client_id"] == c["id"]
    body = admin.post(f"{V1}/conversations/{started['conversation_id']}/turns", json={"message": "Juan."}).json()
    assert body["state"]["fields"]["contact_name"] == "Juan"
    assert body["next_objective"] == "company_name" and body["status"] == "active"
    assert admin.post(f"{V1}/conversations", json={"agent_id": "nope"}).status_code == 404


def test_conversation_keeps_its_agent_version(api, admin):
    """Editar el agente no cambia las conversaciones que ya empezaron."""
    c = make_client(admin)
    agent = make_agent(admin, c)
    started = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()
    definition = agent["definition"]
    definition["fields"]["extra"] = {"priority": 999, "description": "Dato nuevo", "question": "¿?", "required": True}
    admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition})
    detail = admin.get(f"{V1}/calls/{started['conversation_id']}").json()
    assert detail["agent_version"] == 1 and "extra" not in {f["name"] for f in detail["fields"]}


# ---------- entrantes ----------

def test_inbound_routed_by_dialed_number(api, admin):
    from app.services import calls as call_service

    c = make_client(admin, max_concurrent_calls=1)
    agent = make_agent(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541152630861", "agent_id": agent["id"]})
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, "+541152630861", "+5491100000000")
    assert inbound.client_id == c["id"]
    detail = admin.get(f"{V1}/calls/{inbound.conversation_id}").json()
    assert detail["call"]["mode"] == CallMode.entrante and detail["call"]["phone"] == "+5491100000000"

    # Al tope de concurrencia: queda registrada como rechazada.
    from app.services.errors import NotFound, QuotaExceeded
    with api.sessions() as s, pytest.raises(QuotaExceeded):
        call_service.start_inbound(s, api.engine, "541152630861", "+5491100000001")
    rejected = admin.get(f"{V1}/calls", params={"status": "rechazada"}).json()["items"]
    assert len(rejected) == 1 and rejected[0]["ended_reason"] == "concurrency_limit"
    with api.sessions() as s, pytest.raises(NotFound):
        call_service.start_inbound(s, api.engine, "+541199999999", None)


def test_remaining_seconds_during_call(api, admin):
    """Lo que mira el worker cada QUOTA_CHECK_SECONDS para cortar."""
    from app.services import calls as call_service

    c = make_client(admin, outbound_minutes=2)
    agent = make_agent(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234"}).json()
    with api.sessions() as s:
        assert call_service.call_remaining_seconds(s, out["conversation_id"]) == 120
    admin.patch(f"{V1}/clients/{c['id']}", json={"active": False})
    with api.sessions() as s:
        assert call_service.call_remaining_seconds(s, out["conversation_id"]) == 0


def test_date_filters_use_local_days_and_multiple_status(api, admin):
    import datetime

    from app.models import ConversationRow

    c = make_client(admin)
    agent = make_agent(admin, c)
    cid = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()["conversation_id"]
    # 30-sep 23:30 en Buenos Aires = 1-oct 02:30 UTC: cuenta el 30-sep.
    with api.sessions() as s:
        s.get(ConversationRow, cid).created_at = datetime.datetime(2026, 10, 1, 2, 30)  # noqa: DTZ001
        s.commit()
    q = {"client_id": c["id"], "date_from": "2026-09-30", "date_to": "2026-09-30"}
    assert admin.get(f"{V1}/calls", params=q).json()["total"] == 1
    assert admin.get(f"{V1}/calls", params={**q, "tz": "UTC"}).json()["total"] == 0
    assert admin.get(f"{V1}/stats/daily", params=q).json()["totals"] == [1]
    live = admin.get(f"{V1}/calls", params={"status": ["pendiente", "en_curso"]}).json()
    assert live["total"] == 1
    assert admin.get(f"{V1}/calls", params={"tz": "Marte/Base"}).status_code == 422


def test_turn_llm_failure_is_502_json(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    started = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()
    api.llm.turns = []      # el FakeLLM falla (pop de lista vacia)
    r = admin.post(f"{V1}/conversations/{started['conversation_id']}/turns", json={"message": "Hola"})
    assert r.status_code == 502 and r.json()["code"] == "upstream_error"


# ---------- inventario de numeros ----------

def test_bulk_load_into_inventory(api, admin):
    r = admin.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+54 11 5263-0861", "+541152630862", "123",
                                                                  "+541152630861", ""], "label": "Lote sep"})
    body = r.json()
    assert r.status_code == 201 and [n["e164"] for n in body["created"]] == ["+541152630861", "+541152630862"]
    assert {s["number"] for s in body["skipped"]} == {"123", "+541152630861"}
    assert all(n["client_id"] is None and n["provider"] == "anura" for n in body["created"])
    assert len(admin.get(f"{V1}/phone-numbers", params={"status": "free"}).json()) == 2


def test_assign_respects_tier_limit_and_release(api, admin):
    c = make_client(admin, max_phone_numbers=1)
    agent = make_agent(admin, c)
    a, b = admin.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+541100000001", "+541100000002"]}).json()["created"]
    assigned = admin.post(f"{V1}/phone-numbers/{a['id']}/assign", json={"client_id": c["id"]}).json()
    assert assigned["client_name"] == "Acme" and assigned["assigned_at"]
    r = admin.post(f"{V1}/phone-numbers/{b['id']}/assign", json={"client_id": c["id"]})
    assert r.status_code == 409 and r.json()["code"] == "phone_numbers_limit"
    other = make_client(admin, "otro")
    r = admin.post(f"{V1}/phone-numbers/{a['id']}/assign", json={"client_id": other["id"]})
    assert r.status_code == 409 and r.json()["code"] == "number_assigned"
    assert admin.get(f"{V1}/clients/{c['id']}/usage").json()["phone_numbers"] == {"used": 1, "limit": 1}

    admin.patch(f"{V1}/phone-numbers/{a['id']}", json={"agent_id": agent["id"]})
    assert admin.delete(f"{V1}/phone-numbers/{a['id']}").status_code == 409
    released = admin.post(f"{V1}/phone-numbers/{a['id']}/release").json()
    assert released["client_id"] is None and released["agent_id"] is None
    assert admin.delete(f"{V1}/phone-numbers/{a['id']}").status_code == 204
    # Libre: no se le puede poner agente.
    r = admin.patch(f"{V1}/phone-numbers/{b['id']}", json={"agent_id": agent["id"]})
    assert r.status_code == 422 and r.json()["code"] == "number_unassigned"


def test_tier_downgrade_blocked_by_numbers(api, admin):
    c = make_client(admin, max_phone_numbers=2)
    for n in admin.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+541100000001", "+541100000002"]}).json()["created"]:
        admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": c["id"]})
    small = make_tier(admin, name="Chico", max_phone_numbers=1)
    r = admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": small["id"]})
    assert r.status_code == 409 and r.json()["code"] == "phone_numbers_limit"
    r = admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_phone_numbers": 1})
    assert r.status_code == 409


def test_client_routes_its_numbers_to_its_agents(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    mine, theirs = make_agent(admin, acme), make_agent(admin, other)
    n, free = admin.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+541100000001", "+541100000002"]}).json()["created"]
    admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": acme["id"]})
    user = client_user(api, admin, acme)
    assert [x["e164"] for x in user.get(f"{V1}/phone-numbers").json()] == ["+541100000001"]
    assert user.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_id": mine["id"]}).json()["agent_name"] == "Ventas"
    assert user.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_id": theirs["id"]}).status_code == 422
    assert user.patch(f"{V1}/phone-numbers/{free['id']}", json={"label": "x"}).status_code == 404
    assert user.post(f"{V1}/phone-numbers/{n['id']}/release").status_code == 403
    assert user.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+541100000003"]}).status_code == 403


def test_inbound_to_free_number_is_not_answered(api, admin):
    from app.services import calls as call_service
    from app.services.errors import NotFound

    admin.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+541100000009"]})
    with api.sessions() as s, pytest.raises(NotFound):
        call_service.start_inbound(s, api.engine, "+541100000009", None)
