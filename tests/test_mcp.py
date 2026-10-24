"""Servidor MCP (docs/MCP_PLAN.md): protocolo, auth con el scope `mcp`, herramientas por plan y catálogo."""
import pathlib

import pytest

from app.mcp import catalog, docs
from app.services import features

from .test_api import V1, admin, make_agent, make_client, make_tier  # noqa: F401  (admin: fixture)
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

    def call(self, name, **arguments):
        return self.rpc("tools/call", {"name": name, "arguments": arguments})


@pytest.fixture
def full(api, admin):
    """Un cliente con todo el plan (un número para las salientes) y su MCP."""
    c = make_client(admin, slug="acme", outbound_minutes=300, campaign_channels=["whatsapp", "voice"])
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

def test_list_is_core_by_default_and_toolsets_pick(api, admin, full):
    c, _, mcp = full
    core = mcp.tools()
    assert {catalog.BY_NAME[n].toolset for n in core} == set(catalog.CORE)
    every = Mcp(api, mcp.key, "all").tools()
    assert set(every) == set(catalog.BY_NAME)
    only = Mcp(api, mcp.key, "contacts").tools()
    # get_plan_tools va siempre.
    assert set(only) == {"get_plan_tools"} | {t.name for t in catalog.TOOLS if t.toolset == "contacts"}
    for t in every.values():
        assert "client_id" not in t["inputSchema"]["properties"], t["name"]
        assert t["annotations"]["readOnlyHint"] is True
    assert "contacts" in every["list_contacts"]["description"]


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

def test_catalog_matches_the_api(api):
    paths = api.app.openapi()["paths"]
    for t in catalog.TOOLS:
        assert t.toolset in catalog.TOOLSETS, t.name
        assert set(t.features) <= set(features.TIER_HAS), t.name
        assert set(t.required) <= set(t.params), t.name
        if not t.path:
            continue
        op = paths.get(V1 + t.path, {}).get(t.method.lower())
        assert op is not None, f"{t.name}: {t.method} {t.path} no existe"
        api_params = {p["name"] for p in op.get("parameters", [])} | (
            set(op["requestBody"]["content"]["application/json"]["schema"].get("properties", {}))
            if "requestBody" in op else set())
        assert set(t.params) <= api_params, (t.name, set(t.params) - api_params)


def test_tools_doc_is_up_to_date():
    path = pathlib.Path(__file__).parents[1] / docs.DOC
    assert path.read_text() == docs.render(), "docs/MCP_HERRAMIENTAS.md desactualizado: make mcp-docs"
