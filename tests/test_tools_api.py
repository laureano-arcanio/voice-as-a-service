"""API de herramientas del cliente y secretos de los agentes (docs/TOOLS_PLAN.md, 3 y 8): plan, alta y
cambio, validacion al guardar el agente, secretos que no se devuelven nunca, prueba y permisos."""
import pytest
from cryptography.fernet import Fernet

from app.agents.templates import reference_data
from app.config import settings
from scripts.tools import mock_api

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_client,
    make_tier,
)
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def turnos_tool(base: str = "https://api.acme.com") -> dict:
    return {"slug": "consultar_turnos", "type": "http", "definition": {
        "description": "Busca turnos libres de una sucursal para una fecha.",
        "messages": {"start": "Dame un segundo que me fijo."},
        "http": {"method": "GET", "url": base + "/sucursales/{sucursal}/turnos",
                 "path": {"sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "Sucursal"}},
                 "query": {"fecha": {"type": "string", "description": "AAAA-MM-DD", "required": True}},
                 "auth": {"type": "bearer", "secret": "MOCK_TOKEN"}}}}


def code_tool() -> dict:
    return {"slug": "deuda", "type": "code", "definition": {
        "description": "Busca la deuda por DNI.", "secrets": ["MOCK_KEY"], "allowed_hosts": ["api.acme.com"],
        "parameters": {"type": "object", "properties": {"dni": {"type": "string", "description": "DNI"}},
                       "required": ["dni"]},
        "code": "export default async function ({ args }) { return { dni: args.dni }; }"}}


def classic_agent(admin, client, tools=None):
    definition = reference_data("demo_booking")
    if tools is not None:
        definition["tools"] = tools
    r = admin.post(f"{V1}/agents", json={"client_id": client["id"], "name": "Turnos", "slug": "turnos",
                                         "definition": definition})
    return r


def put_tools(admin, agent, tools):
    return admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": {**agent["definition"], "tools": tools}})


# ---------- plan ----------

def test_plan_gates_tools(api, admin):
    free = make_client(admin, "free")                               # max_tools 0 por default
    r = admin.post(f"{V1}/clients/{free['id']}/tools", json=turnos_tool())
    assert r.status_code == 429 and r.json()["code"] == "tools_not_in_plan"
    http_only = make_client(admin, "solohttp", max_tools=1)
    r = admin.post(f"{V1}/clients/{http_only['id']}/tools", json=code_tool())
    assert r.status_code == 429 and r.json()["code"] == "code_tools_not_in_plan"
    assert admin.post(f"{V1}/clients/{http_only['id']}/tools", json=turnos_tool()).status_code == 201
    r = admin.post(f"{V1}/clients/{http_only['id']}/tools", json={**turnos_tool(), "slug": "otra"})
    assert r.status_code == 429 and r.json()["code"] == "tools_limit"
    features = admin.get(f"{V1}/plan/features", params={"client_id": http_only["id"]}).json()["features"]
    assert features["custom_tools"]["enabled"] and not features["code_tools"]["enabled"]


def test_tier_fields_are_configurable(api, admin):
    tier = make_tier(admin, name="con-herramientas", max_tools=5, code_tools=True)
    assert (tier["max_tools"], tier["code_tools"]) == (5, True)
    out = admin.patch(f"{V1}/tiers/{tier['id']}", json={"max_tools": None, "code_tools": False}).json()
    assert (out["max_tools"], out["code_tools"]) == (None, False)


# ---------- alta, cambio y baja ----------

def test_create_update_and_describe(api, admin):
    c = make_client(admin, max_tools=None, code_tools=True)
    r = admin.post(f"{V1}/clients/{c['id']}/tools", json=turnos_tool())
    assert r.status_code == 201, r.text
    tool = r.json()
    assert tool["revision"] == 1 and tool["secrets"] == ["MOCK_TOKEN"]
    assert tool["llm_tool"]["function"]["parameters"]["required"] == ["sucursal", "fecha"]
    assert admin.post(f"{V1}/clients/{c['id']}/tools", json=turnos_tool()).json()["code"] == "tool_slug_taken"
    same = admin.put(f"{V1}/clients/{c['id']}/tools/consultar_turnos",
                     json={"type": "http", "definition": tool["definition"]}).json()
    assert same["revision"] == 1
    changed = {**tool["definition"], "description": "Otra descripción."}
    assert admin.put(f"{V1}/clients/{c['id']}/tools/consultar_turnos",
                     json={"type": "http", "definition": changed}).json()["revision"] == 2
    code = admin.post(f"{V1}/clients/{c['id']}/tools", json=code_tool())
    assert code.status_code == 201 and code.json()["secrets"] == ["MOCK_KEY"]
    assert [t["slug"] for t in admin.get(f"{V1}/clients/{c['id']}/tools").json()] == ["consultar_turnos", "deuda"]
    assert "http" in admin.get(f"{V1}/tools/schema").json()
    assert "export default" in admin.get(f"{V1}/tools/code-template").json()["code"]


def test_invalid_tool_has_the_path(api, admin):
    c = make_client(admin, max_tools=None)
    bad = turnos_tool()
    bad["definition"]["http"]["path"] = {}
    r = admin.post(f"{V1}/clients/{c['id']}/tools", json=bad)
    assert r.status_code == 422 and r.json()["code"] == "invalid_tool"
    assert r.json()["errors"][0]["path"].startswith("definition.http")


# ---------- en el agente ----------

def test_agent_needs_the_tool_and_its_secrets(api, admin):
    c = make_client(admin, max_tools=None)
    r = classic_agent(admin, c, [{"tool": "consultar_turnos"}])
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "tools.0.tool"
    admin.post(f"{V1}/clients/{c['id']}/tools", json=turnos_tool())
    agent = classic_agent(admin, c).json()
    r = put_tools(admin, agent, [{"tool": "consultar_turnos"}])
    assert r.status_code == 422 and "MOCK_TOKEN" in r.json()["errors"][0]["message"]
    secrets = admin.get(f"{V1}/agents/{agent['id']}/secrets").json()
    assert secrets == []
    r = admin.post(f"{V1}/agents/{agent['id']}/secrets",
                   json={"name": "MOCK_TOKEN", "value": mock_api.TOKEN, "description": "API de turnos"})
    assert r.status_code == 201 and mock_api.TOKEN not in r.text and r.json()["last4"] == mock_api.TOKEN[-4:]
    r = put_tools(admin, agent, [{"tool": "consultar_turnos", "confirm": False}])
    assert r.status_code == 200, r.text
    listed = admin.get(f"{V1}/agents/{agent['id']}/secrets")
    assert listed.json()[0]["used_by"] == ["consultar_turnos"] and mock_api.TOKEN not in listed.text
    # En uso: no se borra el secreto ni la herramienta.
    assert admin.delete(f"{V1}/agents/{agent['id']}/secrets/MOCK_TOKEN").json()["code"] == "secret_in_use"
    assert admin.delete(f"{V1}/clients/{c['id']}/tools/consultar_turnos").json()["code"] == "tool_in_use"
    # Cambiar la herramienta para que pida otro secreto rompe al agente: no se guarda.
    tool = admin.get(f"{V1}/clients/{c['id']}/tools/consultar_turnos").json()
    tool["definition"]["http"]["headers"] = {"X-Extra": "{{secrets.OTRO}}"}
    r = admin.put(f"{V1}/clients/{c['id']}/tools/consultar_turnos", json={"type": "http", "definition": tool["definition"]})
    assert r.status_code == 422 and r.json()["code"] == "missing_secret"
    # Rotar el valor no crea version del agente.
    assert admin.patch(f"{V1}/agents/{agent['id']}/secrets/MOCK_TOKEN", json={"value": "nuevo-valor-123456"}).status_code == 200
    assert admin.get(f"{V1}/agents/{agent['id']}").json()["version"] == 2


def test_old_app_grants_are_dropped_when_read(api, admin):
    """Las herramientas de apps ({app, tools}) ya no existen: una definicion vieja se lee sin ellas."""
    c = make_client(admin, max_tools=None)
    r = classic_agent(admin, c, [{"app": "gestion", "tools": ["alumnos"]}])
    assert r.status_code == 201, r.text
    assert r.json()["definition"]["tools"] == []


def test_tool_versions_keep_every_revision(api, admin):
    c = make_client(admin, max_tools=None)
    tool = turnos_tool()
    assert admin.post(f"{V1}/clients/{c['id']}/tools", json=tool).status_code == 201
    changed = {**tool["definition"], "description": "Turnos libres de una sucursal."}
    r = admin.put(f"{V1}/clients/{c['id']}/tools/consultar_turnos", json={"type": "http", "definition": changed})
    assert r.status_code == 200, r.text
    versions = admin.get(f"{V1}/clients/{c['id']}/tools/consultar_turnos/versions")
    assert versions.status_code == 200, versions.text
    out = versions.json()
    assert [v["revision"] for v in out] == [2, 1]           # la mas nueva primero
    assert out[0]["definition"]["description"] == "Turnos libres de una sucursal."
    assert out[1]["definition"]["description"] == tool["definition"]["description"]
    assert all(v["type"] == "http" for v in out)
    other = make_client(admin, "otro", max_tools=None)
    user = client_user(api, admin, other, "luis@otro.com")
    assert user.get(f"{V1}/clients/{c['id']}/tools/consultar_turnos/versions").status_code == 404


def test_other_client_cannot_see_or_use(api, admin):
    acme, other = make_client(admin, "acme", max_tools=None), make_client(admin, "otro", max_tools=None)
    admin.post(f"{V1}/clients/{acme['id']}/tools", json=turnos_tool())
    agent = classic_agent(admin, acme).json()
    admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "MOCK_TOKEN", "value": "x" * 20})
    user = client_user(api, admin, other, "luis@otro.com")
    assert user.get(f"{V1}/clients/{acme['id']}/tools").status_code == 404
    assert user.get(f"{V1}/agents/{agent['id']}/secrets").status_code == 404
    # Un agente del otro cliente no puede referenciar la herramienta de acme.
    theirs = classic_agent(admin, other).json()
    assert put_tools(admin, theirs, [{"tool": "consultar_turnos"}]).status_code == 422
    # Ni probarla con los secretos de un agente ajeno.
    r = user.post(f"{V1}/clients/{other['id']}/tools/test",
                  json={**turnos_tool(), "args": {"sucursal": "centro", "fecha": "2026-11-05"}, "agent_id": agent["id"]})
    assert r.status_code == 404


# ---------- prueba ----------

def test_test_with_agent_secrets_and_with_inline_secrets(api, admin, mock_api_url):
    c = make_client(admin, max_tools=None)
    tool = admin.post(f"{V1}/clients/{c['id']}/tools", json=turnos_tool(mock_api_url)).json()
    agent = classic_agent(admin, c).json()
    admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "MOCK_TOKEN", "value": mock_api.TOKEN})
    r = admin.post(f"{V1}/clients/{c['id']}/tools/consultar_turnos/test",
                   json={"args": {"sucursal": "centro", "fecha": "2026-11-05"}, "agent_id": agent["id"]})
    out = r.json()
    assert out["ok"] and out["data"]["turnos"] == ["10:00", "11:30", "16:00"], out
    assert mock_api.TOKEN not in r.text and "[secreto:MOCK_TOKEN]" in out["request"]["headers"]["Authorization"]
    assert admin.get(f"{V1}/clients/{c['id']}/tools/consultar_turnos").json()["last_test_ok"] is True
    draft = admin.post(f"{V1}/clients/{c['id']}/tools/test",
                       json={"type": "http", "definition": tool["definition"],
                             "args": {"sucursal": "norte", "fecha": "2026-11-05"},
                             "secrets": {"MOCK_TOKEN": mock_api.TOKEN}}).json()
    assert draft["ok"] and draft["data"]["turnos"] == ["15:00"]
    missing = admin.post(f"{V1}/clients/{c['id']}/tools/test",
                         json={"type": "http", "definition": tool["definition"],
                               "args": {"sucursal": "norte", "fecha": "2026-11-05"}}).json()
    assert not missing["ok"] and "MOCK_TOKEN" in missing["error"]


def test_code_test_without_runner_says_so(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "tools_runner_url", "")
    c = make_client(admin, max_tools=None, code_tools=True)
    out = admin.post(f"{V1}/clients/{c['id']}/tools/test",
                     json={**code_tool(), "args": {"dni": "1"}, "secrets": {"MOCK_KEY": "x" * 10}}).json()
    assert not out["ok"] and "no están disponibles" in out["error"]
