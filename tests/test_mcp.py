"""Servidor MCP (docs/MCP_PLAN.md): protocolo, auth con el scope `mcp`, herramientas por plan y catálogo."""
import pathlib

import pytest

from app.conversation.models import AgentTurn

from app.mcp import catalog, docs
from app.services import features, livekit

from .test_api import V1, admin, client_user, make_agent, make_client, make_tier  # noqa: F401  (admin: fixture)
from .test_direct_calls import accept_terms
from .test_plan_features import FREE


def new_key(admin, client, scopes=("mcp",)):
    r = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "agente", "scopes": list(scopes)})
    assert r.status_code == 201, r.text
    return r.json()["key"]


class Mcp:
    def __init__(self, api, key, toolsets=None):
        self.http, self.key = api.client, key
        self.url = "/mcp" + (f"?toolsets={toolsets}" if toolsets else "")

    def rpc(self, method, params=None, msg_id=1):
        r = self.http.post(self.url, headers={"Authorization": f"Bearer {self.key}"},
                           json={"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "error" not in body, body
        return body["result"]

    def tools(self):
        return {t["name"]: t for t in self.rpc("tools/list")["tools"]}

    def call(self, tool, /, **arguments):
        return self.rpc("tools/call", {"name": tool, "arguments": arguments})


@pytest.fixture
def full(api, admin):
    """Un cliente con todo el plan (un número para las salientes) y su MCP."""
    c = make_client(admin, slug="acme", outbound_minutes=300, campaign_channels=["whatsapp", "voice"],
                    direct_calls=True)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541152630861"}).raise_for_status()
    agent = make_agent(admin, c)
    return c, agent, Mcp(api, new_key(admin, c))


# ---------- protocolo y auth ----------

def test_initialize_negotiates_and_notifications_are_accepted(api, full):
    _, _, mcp = full
    out = mcp.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                 "clientInfo": {"name": "test", "version": "1"}})
    assert out["protocolVersion"] == "2025-03-26" and out["serverInfo"]["name"] == "atentina"
    assert "tools" in out["capabilities"]
    assert mcp.rpc("initialize", {"protocolVersion": "1999-01-01"})["protocolVersion"] == "2025-06-18"
    r = api.client.post("/mcp", headers={"Authorization": f"Bearer {mcp.key}"},
                        json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert r.status_code == 202
    assert mcp.rpc("ping") == {}
    assert api.client.get("/mcp").status_code == 405


def test_auth_needs_a_key_with_the_mcp_scope(api, admin):
    c = make_client(admin)
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    r = api.client.post("/mcp", json=body)
    assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Bearer")
    calls_key = new_key(admin, c, scopes=["calls"])
    assert api.client.post("/mcp", json=body, headers={"Authorization": f"Bearer {calls_key}"}).status_code == 401
    # La sesión del panel tampoco: el MCP es para agentes, con su key.
    assert admin.post("/mcp", json=body).status_code == 401
    # Una key `mcp` también sirve para la API (las herramientas la usan por dentro).
    assert api.client.get(f"{V1}/agents", headers={"Authorization": f"Bearer {new_key(admin, c)}"}).status_code == 200


def test_foreign_origin_is_rejected(api, full):
    _, _, mcp = full
    r = api.client.post("/mcp", headers={"Authorization": f"Bearer {mcp.key}", "Origin": "https://evil.example"},
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 403


def test_unknown_method_and_tool(api, full):
    _, _, mcp = full
    r = api.client.post("/mcp", headers={"Authorization": f"Bearer {mcp.key}"},
                        json={"jsonrpc": "2.0", "id": 7, "method": "sampling/createMessage"})
    assert r.json()["error"]["code"] == -32601 and r.json()["id"] == 7
    r = api.client.post("/mcp", headers={"Authorization": f"Bearer {mcp.key}"},
                        json={"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "drop_db"}})
    assert r.json()["error"]["code"] == -32602


# ---------- tools/list ----------

def test_list_is_all_by_default_and_toolsets_pick(api, admin, full):
    c, _, mcp = full
    default = mcp.tools()
    every = Mcp(api, mcp.key, "all").tools()
    client_tools = {t.name for t in catalog.TOOLS if t.toolset != "admin"}
    assert set(every) == client_tools
    # Sin parámetro: todas las de cliente menos inference; admin nunca para un cliente.
    assert set(default) == {t.name for t in catalog.TOOLS if t.toolset in catalog.DEFAULT}
    assert not any(n.startswith("admin_") for n in every)
    core = Mcp(api, mcp.key, "core").tools()
    assert {catalog.BY_NAME[n].toolset for n in core} == set(catalog.CORE)
    only = Mcp(api, mcp.key, "contacts").tools()
    # get_plan_tools va siempre.
    assert set(only) == {"get_plan_tools"} | {t.name for t in catalog.TOOLS if t.toolset == "contacts"}
    for t in every.values():
        assert "client_id" not in t["inputSchema"]["properties"], t["name"]
        assert "loadtest" not in t["inputSchema"]["properties"], t["name"]
    assert "contacts" in every["list_contacts"]["description"]
    # Anotaciones: lectura, escritura y las que hay que confirmar.
    assert every["list_agents"]["annotations"]["readOnlyHint"] is True
    assert every["preview_voice"]["annotations"]["readOnlyHint"] is True
    assert every["update_agent_definition"]["annotations"] == {
        "title": "Editar la definición de un agente", "readOnlyHint": False, "openWorldHint": False,
        "destructiveHint": False, "idempotentHint": True}
    assert every["start_call"]["annotations"]["destructiveHint"] is True
    # Los cuerpos salen del OpenAPI, con sus $ref en $defs.
    upsert = every["upsert_contacts"]["inputSchema"]
    assert upsert["required"] == ["contacts"] and upsert["properties"]["contacts"]["items"] == {"$ref": "#/$defs/ContactIn"}
    assert "phone" in upsert["$defs"]["ContactIn"]["properties"]
    assert "format" not in every["preview_voice"]["inputSchema"]["properties"]


# ---------- herramientas ----------

def test_read_tools_work_with_the_key(api, full):
    c, agent, mcp = full
    for name in ("whoami", "get_plan_features", "get_usage", "get_call_emails", "list_agents",
                 "get_agent_schema", "list_agent_templates", "list_voices", "list_calls", "get_stats",
                 "list_phone_numbers", "list_blocked_numbers", "list_whatsapp_accounts",
                 "list_contacts", "list_optouts", "get_campaign_plan", "list_campaigns",
                 "list_team", "list_handoff_areas", "list_events"):
        out = Mcp(api, mcp.key, "all").call(name)
        assert not out.get("isError"), (name, out)
        assert out["content"][0]["type"] == "text"
    out = mcp.call("get_daily_stats", date_from="2026-10-01", date_to="2026-10-24")
    assert not out.get("isError"), out
    out = mcp.call("get_agent", agent_id=agent["id"])
    assert not out.get("isError") and out["structuredContent"]["id"] == agent["id"]
    assert mcp.call("list_agents")["structuredContent"]["items"][0]["id"] == agent["id"]
    assert not mcp.call("list_agent_versions", agent_id=agent["id"]).get("isError")


def test_arguments_are_checked(full):
    _, _, mcp = full
    out = mcp.call("get_agent")
    assert out["isError"] and out["structuredContent"]["code"] == "invalid_arguments"
    out = mcp.call("list_agents", client_id="otro")
    assert out["isError"] and "client_id" in out["structuredContent"]["message"]


def test_other_clients_data_is_not_reachable(api, admin, full):
    _, _, mcp = full
    other = make_client(admin, slug="otra")
    foreign = make_agent(admin, other)
    out = mcp.call("get_agent", agent_id=foreign["id"])
    assert out["isError"] and out["structuredContent"]["http_status"] in (403, 404)
    assert [a["id"] for a in mcp.call("list_agents")["structuredContent"]["items"]] != [foreign["id"]]


# ---------- plan ----------

def test_free_plan_tools_say_what_is_missing(api, admin):
    make_tier(admin, name="Sucursal", price_ars=99000, public=True, sort=2, outbound_minutes=1200,
              max_phone_numbers=3, campaign_channels=["whatsapp", "voice"])
    c = make_client(admin, slug="free", tier=make_tier(admin, **FREE))
    mcp = Mcp(api, new_key(admin, c), "all")
    out = mcp.call("get_plan_tools")["structuredContent"]
    assert out["plan"] == "Free" and out["free"] is True
    blocked = {t["name"]: t for t in out["tools"]["unavailable"]}
    assert "list_agents" in out["tools"]["available"] and "get_call_link" in out["tools"]["available"]
    assert blocked["list_contacts"]["reason"] == "Disponible en el plan Sucursal."
    assert {"list_whatsapp_accounts", "list_campaigns", "list_team"} <= set(blocked)
    assert out["usage"] is not None
    err = mcp.call("list_contacts")
    assert err["isError"]
    assert err["structuredContent"] == {"code": "feature_not_in_plan", "feature": "contacts",
                                        "message": "Tu plan Free no incluye esta función.",
                                        "reason": "Disponible en el plan Sucursal.",
                                        "upgrade_url": "https://app.atentina.com.ar/plan"}


def test_campaign_tools_need_either_channel(api, admin):
    c = make_client(admin, slug="wa", campaign_channels=["whatsapp"])
    out = Mcp(api, new_key(admin, c), "campaigns").call("list_campaigns")
    assert not out.get("isError"), out


# ---------- catálogo y doc ----------

def _body_ref(op):
    """El esquema del cuerpo de la ruta: directo, en un anyOf (opcional) o como items (lista)."""
    schema = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
    for node in [schema, *schema.get("anyOf", [])]:
        node = node.get("items", node)
        if "$ref" in node:
            return node["$ref"].rsplit("/", 1)[1]
    return None


def test_catalog_matches_the_api(api):
    openapi = api.app.openapi()
    paths = openapi["paths"]
    for t in catalog.TOOLS:
        assert t.toolset in catalog.TOOLSETS, t.name
        assert set(t.features) <= set(features.TIER_HAS), t.name
        assert set(t.required) <= t.arg_names(openapi), t.name
        if not t.path:
            continue
        op = paths.get(V1 + t.path, {}).get(t.method.lower())
        assert op is not None, f"{t.name}: {t.method} {t.path} no existe"
        assert t.body == _body_ref(op), (t.name, t.body, _body_ref(op))
        names = {p["name"] for p in op.get("parameters", [])}
        if t.upload:   # multipart: los argumentos son campos del formulario (el archivo va en base64)
            form = op["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"].rsplit("/", 1)[1]
            names |= set(openapi["components"]["schemas"][form]["properties"]) | {t.upload, "filename"}
        assert set(t.params) <= names, t.name
        if t.method == "GET":
            assert t.reads, t.name
    assert len(catalog.BY_NAME) == len(catalog.TOOLS)


def test_tools_doc_is_up_to_date():
    root = pathlib.Path(__file__).parents[1]
    assert (root / docs.DOC).read_text() == docs.render(), "docs/MCP_HERRAMIENTAS.md desactualizado: make mcp-docs"
    assert (root / docs.LANDING_JSON).read_text() == docs.render_landing(), (
        "landing/src/data/mcp-tools.json desactualizado: make mcp-docs")


def test_plan_doc_matches_features():
    assert set(docs.FEATURES) == set(features.TIER_HAS)


# ---------- escritura (fase 2) ----------

def ok(out):
    assert not out.get("isError"), out
    return out.get("structuredContent")


def test_build_and_test_an_agent(api, full):
    _, _, mcp = full
    mcp = Mcp(api, mcp.key, "agents")
    template = ok(mcp.call("list_agent_templates"))["items"][0]
    definition = ok(mcp.call("get_agent_template", template_id=template["id"]))
    assert ok(mcp.call("validate_agent_definition", definition=definition))["valid"] is True
    bad = ok(mcp.call("validate_agent_definition", definition={"conversation": "nope"}))
    assert bad["valid"] is False and bad["errors"]
    agent = ok(mcp.call("create_agent", name="Turnos", definition=definition))
    definition["conversation"]["opening"] = "Hola, te habla Sofía de la peluquería."
    updated = ok(mcp.call("update_agent_definition", agent_id=agent["id"], definition=definition))
    assert updated["version"] == 2
    api.llm.turns = [AgentTurn(assistant_message="¿En qué te ayudo?")]
    started = ok(mcp.call("test_agent_start", agent_id=agent["id"]))
    reply = ok(mcp.call("test_agent_turn", conversation_id=started["conversation_id"], message="Quiero un turno"))
    assert reply["message"] == "¿En qué te ayudo?"
    assert ok(mcp.call("get_test_conversation", conversation_id=started["conversation_id"]))
    assert ok(mcp.call("update_agent", agent_id=agent["id"], archived=True))["archived"] is True
    # Con conversaciones no se borra: el error de la API llega legible.
    out = mcp.call("delete_agent", agent_id=agent["id"])
    assert out["isError"] and out["structuredContent"]["code"] == "agent_in_use"
    unused = ok(mcp.call("create_agent", name="Borrador", template_id=template["id"]))
    assert ok(mcp.call("delete_agent", agent_id=unused["id"])) == {}


def test_outbound_call_and_routing(api, full):
    c, agent, mcp = full
    out = ok(mcp.call("start_call", agent_id=agent["id"], phone="+54 9 11 5555-1234"))
    assert out["conversation_id"] and len(api.dispatched) == 1
    number = ok(mcp.call("list_phone_numbers"))["items"][0]
    assert ok(mcp.call("route_phone_number", number_id=number["id"], agent_id=agent["id"]))["agent_id"] == agent["id"]
    ok(mcp.call("block_number", phone="+5491155559999", note="spam"))
    assert len(ok(mcp.call("list_blocked_numbers"))["items"]) == 1
    ok(mcp.call("unblock_number", phone="+5491155559999"))
    assert ok(mcp.call("list_blocked_numbers"))["items"] == []
    ok(Mcp(api, mcp.key, "account").call("update_call_emails", enabled=False))


def test_direct_calls_tools(api, admin, full, monkeypatch):
    """Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md, 9): las hace una persona; el MCP devuelve el link."""
    c, agent, mcp = full
    every = Mcp(api, mcp.key, "all")
    tools = every.tools()
    start = tools["start_direct_call"]
    assert start["annotations"]["destructiveHint"] is True
    assert "PERSONA" in start["description"] and "start_call" in start["description"]
    assert set(start["inputSchema"]["properties"]) == {"contact_id", "phone", "from_number_id", "confirm_opted_out",
                                                       "user_id"}
    assert {"mode", "user_id", "answered_by"} <= set(tools["list_calls"]["inputSchema"]["properties"])
    assert {"answer_mode", "member_ids", "ring_first", "team_fallback"} <= set(
        tools["route_phone_number"]["inputSchema"]["properties"])
    for name, toolset in (("start_direct_call", "calls"), ("list_team_presence", "team"),
                          ("get_direct_call_settings", "account"), ("update_direct_call_settings", "account")):
        assert catalog.BY_NAME[name].toolset == toolset and catalog.BY_NAME[name].features == ("direct_calls",)

    user = client_user(api, admin, c)
    user_id = user.get(f"{V1}/auth/me").json()["id"]
    # Hasta que el cliente acepta las condiciones vigentes (graban siempre), no se llama.
    out = every.call("start_direct_call", phone="+54 9 351 677-5617", user_id=user_id)
    assert out["isError"] and out["structuredContent"]["code"] == "terms_pending"
    accept_terms(user)
    # Con la key, el usuario que habla es obligatorio y la respuesta trae el link para abrir en el panel.
    out = every.call("start_direct_call", phone="+54 9 351 677-5617")
    assert out["isError"] and out["structuredContent"]["code"] == "user_required"
    started = ok(every.call("start_direct_call", phone="+54 9 351 677-5617", user_id=user_id))
    assert started["token"] is None and started["join_url"].endswith(f"/telefono/llamada/{started['conversation_id']}")
    assert api.dispatched[-1]["direct"] is True and api.dispatched[-1]["join_timeout_seconds"] == 120
    mine = ok(every.call("list_calls", mode="directa", user_id=user_id))
    assert [i["id"] for i in mine["items"]] == [started["conversation_id"]]
    assert ok(every.call("list_calls", answered_by="team"))["items"] == []
    # En la llamada, la persona figura ocupada (el worker la cierra de verdad).
    presence = ok(every.call("list_team_presence"))
    assert [(p["user_id"], p["available"], p["busy"]) for p in presence["items"]] == [(user_id, False, True)]

    async def delete_room(room):
        return True
    monkeypatch.setattr(livekit, "delete_room", delete_room)
    assert ok(every.call("hangup_call", conversation_id=started["conversation_id"]))["ended_reason"] == "hangup_by_user"

    assert ok(every.call("get_direct_call_settings")) == {"recording_notice": False}
    assert ok(every.call("update_direct_call_settings", recording_notice=True)) == {"recording_notice": True}
    assert ok(every.call("get_direct_call_settings")) == {"recording_notice": True}

    # El número lo atiende el equipo: personas en orden, dónde suena primero y el respaldo.
    member = ok(every.call("create_team_member", name="Ana", user_id=user_id))
    number = ok(every.call("list_phone_numbers"))["items"][0]
    routed = ok(every.call("route_phone_number", number_id=number["id"], answer_mode="team", member_ids=[member["id"]],
                           ring_first="panel", ring_seconds=15, team_fallback="agent", agent_id=agent["id"]))
    assert (routed["answer_mode"], routed["ring_first"], routed["ring_seconds"]) == ("team", "panel", 15)
    assert [m["id"] for m in routed["members"]] == [member["id"]]


def test_direct_calls_tools_need_the_plan(api, admin):
    c = make_client(admin, slug="sin", outbound_minutes=300)
    mcp = Mcp(api, new_key(admin, c), "all")
    blocked = {t["name"] for t in mcp.call("get_plan_tools")["structuredContent"]["tools"]["unavailable"]}
    assert {"start_direct_call", "list_team_presence", "get_direct_call_settings",
            "update_direct_call_settings"} <= blocked
    err = mcp.call("start_direct_call", phone="+5493516775617", user_id="x")
    assert err["isError"] and err["structuredContent"]["code"] == "feature_not_in_plan"
    assert err["structuredContent"]["feature"] == "direct_calls"


def test_report_calls_tool_exposes_the_split(api, full):
    _, _, mcp = full
    out = ok(Mcp(api, mcp.key, "reports").call("get_report_calls"))
    assert [t["type"] for t in out["by_type"]] == ["agent", "direct", "team"] and out["by_user"] == []
    assert "directas" in catalog.BY_NAME["get_report_calls"].description


def test_contacts_and_a_campaign_draft(api, full):
    _, agent, mcp = full
    mcp = Mcp(api, mcp.key, "all")
    loaded = ok(mcp.call("upsert_contacts", contacts=[{"phone": "+5491155550001", "name": "Ana", "tags": ["mora"]},
                                                       {"phone": "+5491155550002", "name": "Beto"}]))
    assert loaded
    ok(mcp.call("import_contacts", csv="telefono,nombre\n+5491155550003,Caro\n"))
    contacts = ok(mcp.call("list_contacts"))
    assert contacts["total"] == 3
    created = ok(mcp.call("create_campaign", channel="voice", name="Cobranza", agent_id=agent["id"], tags=["mora"]))
    cid = created["campaign"]["id"]
    assert created["added"] == 1 and created["campaign"]["status"] == "draft"
    ok(mcp.call("update_campaign", campaign_id=cid, name="Cobranza octubre"))
    ok(mcp.call("add_campaign_contacts", campaign_id=cid, contacts=[{"phone": "+5491155550004"}]))
    assert ok(mcp.call("get_campaign", campaign_id=cid))["name"] == "Cobranza octubre"
    report = mcp.call("get_campaign_report", campaign_id=cid)
    assert not report.get("isError") and report["content"][0]["text"].startswith("external_id")
    ok(mcp.call("delete_campaign", campaign_id=cid))
    ok(mcp.call("add_optout", phone="+5491155550002", channel="voice"))
    assert len(ok(mcp.call("list_optouts"))["items"]) == 1
    ok(mcp.call("remove_optout", phone="+5491155550002"))
    ok(mcp.call("archive_contacts", tags=["mora"]))
    # 4 cargados (uno por la campaña) y 1 archivado: archivar no borra.
    assert ok(mcp.call("list_contacts"))["total"] == 3
    assert ok(mcp.call("list_contacts", archived="true"))["total"] == 1


def test_team_and_areas(api, full):
    _, _, mcp = full
    mcp = Mcp(api, mcp.key, "team")
    member = ok(mcp.call("create_team_member", name="Juan", phone="+5491155550005"))
    ok(mcp.call("update_team_member", member_id=member["id"], name="Juan Pérez"))
    assert ok(mcp.call("get_handoff_area_defaults")) and ok(mcp.call("list_hold_music")) is not None
    area = ok(mcp.call("create_handoff_area", name="Ventas", description="Precios y planes", member_ids=[member["id"]]))
    ok(mcp.call("update_handoff_area", area_id=area["id"], active=False))
    ok(mcp.call("delete_handoff_area", area_id=area["id"]))
    ok(mcp.call("delete_team_member", member_id=member["id"]))
    assert ok(mcp.call("list_team"))["items"] == []


def test_call_link_lifecycle(api, full):
    _, agent, mcp = full
    mcp = Mcp(api, mcp.key, "call_links")
    created = ok(mcp.call("create_call_link", agent_id=agent["id"], display_name="Sofía", company_name="Acme"))
    rotated = ok(mcp.call("rotate_call_link", agent_id=agent["id"]))
    assert rotated["url"] != created["url"]
    ok(mcp.call("update_call_link", agent_id=agent["id"], paused=True))
    ok(mcp.call("delete_call_link", agent_id=agent["id"]))


def test_free_plan_cannot_write_what_it_does_not_have(api, admin):
    c = make_client(admin, slug="free", tier=make_tier(admin, **FREE))
    agent = make_agent(admin, c)
    mcp = Mcp(api, new_key(admin, c), "all")
    for name, args in (("create_campaign", {"channel": "voice", "name": "X", "agent_id": agent["id"]}),
                       ("upsert_contacts", {"contacts": [{"phone": "+5491155550001"}]}),
                       ("start_call", {"agent_id": agent["id"], "phone": "+5491155550001"}),
                       ("create_team_member", {"name": "Juan"})):
        out = mcp.call(name, **args)
        assert out["isError"] and out["structuredContent"]["code"] == "feature_not_in_plan", (name, out)
    assert api.dispatched == []


def test_resources_and_prompts(api, full):
    _, _, mcp = full
    uris = {r["uri"] for r in mcp.rpc("resources/list")["resources"]}
    assert "atentina://agents/schema" in uris and "atentina://guides/agentes" in uris
    schema = mcp.rpc("resources/read", {"uri": "atentina://agents/schema"})["contents"][0]
    assert schema["mimeType"] == "application/json" and '"properties"' in schema["text"]
    guide = mcp.rpc("resources/read", {"uri": "atentina://guides/campanas"})["contents"][0]["text"]
    assert "start_campaign" in guide
    names = {p["name"] for p in mcp.rpc("prompts/list")["prompts"]}
    assert names == {"crear_agente", "revisar_llamadas", "lanzar_campana"}
    msg = mcp.rpc("prompts/get", {"name": "revisar_llamadas", "arguments": {"desde": "2026-10-01"}})["messages"][0]
    assert "desde 2026-10-01: usá" in msg["content"]["text"]
    # Las herramientas que nombran las guías y los prompts existen.
    import re
    from app.mcp import guides
    texts = [text for _, text in guides.GUIDES.values()] + [p["text"] for p in guides.PROMPTS.values()]
    named = set(re.findall(r"\b((?:get|list|create|update|delete|start|pause|resume|cancel|test|validate|preview|"
                           r"route|upsert|import)_[a-z_]+)\b", " ".join(texts)))
    assert named and named <= set(catalog.BY_NAME), named - set(catalog.BY_NAME)


# ---------- fase 5: mcp_read, uso por herramienta e inferencia ----------

def test_mcp_read_key_only_sees_and_runs_read_tools(api, admin, full):
    c, agent, _ = full
    key = new_key(admin, c, scopes=["mcp_read"])
    ro = Mcp(api, key)
    tools = ro.tools()
    assert "list_agents" in tools and "validate_agent_definition" in tools
    assert {"get_report_summary", "get_report_outcomes"} <= set(tools)
    assert not any(not catalog.BY_NAME[n].reads for n in tools)
    r = api.client.post("/mcp", headers={"Authorization": f"Bearer {key}"},
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": "delete_agent", "arguments": {"agent_id": agent["id"]}}})
    assert "error" in r.json()
    # Las de lectura por POST (validar) pasan por el MCP; por fuera, la API solo deja GET con esta key.
    assert not ro.call("list_agents").get("isError")
    auth = {"Authorization": f"Bearer {key}"}
    assert api.client.get(f"{V1}/agents", headers=auth).status_code == 200
    assert api.client.delete(f"{V1}/agents/{agent['id']}", headers=auth).status_code == 403


def test_tool_usage_is_recorded_per_client(api, admin, full):
    c, _, mcp = full
    mcp.call("list_agents")
    mcp.call("list_agents")
    mcp.call("get_agent", agent_id="no-existe")
    other = make_client(admin, slug="otro")
    Mcp(api, new_key(admin, other)).call("whoami")
    usage = admin.get(f"{V1}/mcp/usage", params={"client_id": c["id"]}).json()
    by_tool = {t["tool"]: t for t in usage["tools"]}
    assert by_tool["list_agents"]["calls"] == 2 and by_tool["get_agent"]["errors"] == 1
    assert "whoami" not in by_tool
    # El cliente ve solo el suyo, con su key también.
    own = api.client.get(f"{V1}/mcp/usage", headers={"Authorization": f"Bearer {mcp.key}"}).json()
    assert {t["tool"] for t in own["tools"]} == set(by_tool)


def test_inference_tools_are_opt_in_and_need_their_scopes(api, admin, full):
    c, _, mcp = full
    assert "synthesize_speech" not in mcp.tools()
    inf = Mcp(api, mcp.key, "inference")
    assert {"transcribe_audio", "synthesize_speech", "get_inference_usage"} <= set(inf.tools())
    # La key solo tiene `mcp`: la API de inferencia la rechaza con el motivo.
    out = inf.call("synthesize_speech", input="Hola", voice="sofia")
    assert out["isError"] and out["structuredContent"]["http_status"] in (401, 403), out
    bad = inf.call("transcribe_audio", audio_base64="no es base64!", filename="a.wav")
    assert bad["structuredContent"]["code"] == "invalid_arguments"


# ---------- reportes (docs/REPORTES_PLAN.md, 9.4) ----------

REPORT_TOOLS = {"get_report_summary": "/reports/summary", "get_report_calls": "/reports/calls",
                "get_report_outcomes": "/reports/outcomes", "get_report_messages": "/reports/messages",
                "get_report_transfers": "/reports/transfers", "get_report_campaigns": "/reports/campaigns"}
PERIOD = {"date_from": "2026-10-01", "date_to": "2026-10-24"}


def test_report_tools_are_in_the_catalog():
    for name, path in REPORT_TOOLS.items():
        t = catalog.BY_NAME[name]
        assert (t.toolset, t.method, t.path, t.reads) == ("reports", "GET", path, True), name
        assert t.features == (() if name in ("get_report_summary", "get_report_calls") else ("advanced_reports",)), name
    # Lo técnico y la plataforma son del admin: un cliente no los ve, ni con `all`.
    assert catalog.BY_NAME["get_report_technical"].toolset == catalog.BY_NAME["get_report_platform"].toolset == "admin"
    assert "reports" in catalog.DEFAULT and "reports" not in catalog.CORE


def test_report_tools_read_the_reports_api(api, admin):
    c = make_client(admin, slug="rep", advanced_reports=True)
    key = new_key(admin, c)
    mcp = Mcp(api, key, "reports")
    assert {"get_plan_tools", *REPORT_TOOLS} == set(mcp.tools())
    auth = {"Authorization": f"Bearer {key}"}
    for name, path in REPORT_TOOLS.items():
        out = mcp.call(name, **PERIOD)
        direct = api.client.get(f"{V1}{path}", params=PERIOD, headers=auth)
        assert direct.status_code == 200, (name, direct.text)
        assert ok(out) == direct.json(), name
    assert "kpis" in ok(mcp.call("get_report_summary", channel="voice", include_tests=True, **PERIOD))
    # Los filtros se validan antes de pedir; el cliente no elige otro cliente ni ve lo técnico.
    out = mcp.call("get_report_summary", client_id="otro")
    assert out["isError"] and "client_id" in out["structuredContent"]["message"]
    r = api.client.post("/mcp", headers=auth, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                                     "params": {"name": "get_report_technical", "arguments": {}}})
    assert r.json()["error"]["code"] == -32602
    assert api.client.get(f"{V1}/reports/technical", headers=auth).status_code == 403


def test_report_tools_respect_the_plan(api, admin):
    c = make_client(admin, slug="gratis", tier=make_tier(admin, **FREE))
    mcp = Mcp(api, new_key(admin, c), "reports")
    assert "kpis" in ok(mcp.call("get_report_summary", **PERIOD))
    assert "daily" in ok(mcp.call("get_report_calls", **PERIOD))
    plan = mcp.call("get_plan_tools")["structuredContent"]
    blocked = {t["name"] for t in plan["tools"]["unavailable"]}
    assert {"get_report_outcomes", "get_report_messages", "get_report_transfers", "get_report_campaigns"} <= blocked
    assert not {"get_report_summary", "get_report_calls"} & blocked
    for name in ("get_report_outcomes", "get_report_messages", "get_report_transfers", "get_report_campaigns"):
        out = mcp.call(name, **PERIOD)
        assert out["isError"] and out["structuredContent"]["code"] == "feature_not_in_plan", (name, out)
        assert out["structuredContent"]["feature"] == "advanced_reports"
