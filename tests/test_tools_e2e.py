"""Herramientas de punta a punta (docs/features/HERRAMIENTAS.md): todo armado por la API y despues por el MCP, como un
cliente, contra la API falsa (scripts/tools/mock_api.py) y, si esta TOOLS_RUNNER_TEST_URL, el sandbox de codigo
real (make e2e-tools lo levanta). El LLM es falso, con respuestas grabadas: prueba el codigo, no el modelo
(AGENTS.md, "Reglas de desarrollo"). La calidad del modelo la mide make eval-tools."""
import json
import os
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from app.agents.definitions import DbDefinitions
from app.agents.templates import reference_data
from app.api import deps
from app.config import settings
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.llm.client import LLMClient
from scripts.tools import mock_api

from .test_api import V1, admin  # noqa: F401  (fixture)
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)

RUNNER = os.getenv("TOOLS_RUNNER_TEST_URL", "")
SECRETS = {"MOCK_TOKEN": mock_api.TOKEN, "MOCK_KEY": mock_api.API_KEY, "ATENTINA_SIGNING_SECRET": mock_api.SIGNING_SECRET}


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


class Recorded:
    """Un LLM con respuestas grabadas: cada pedido toma la siguiente, (texto, [(herramienta, argumentos)])."""

    def __init__(self):
        self.replies: list[tuple[str, list]] = []
        self.requests: list[dict] = []

    async def create(self, **request):
        self.requests.append(json.loads(json.dumps(request, default=str)))
        text, calls = self.replies.pop(0)
        tool_calls = [SimpleNamespace(id=f"call_{i}", function=SimpleNamespace(name=n, arguments=json.dumps(a)))
                      for i, (n, a) in enumerate(calls)] or None
        message = SimpleNamespace(content=text, reasoning_content=None, tool_calls=tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def world(api, admin, mock_api_url, monkeypatch):  # noqa: F811
    """Tier y cliente, el LLM grabado en el motor de la API y el sandbox de prueba si esta."""
    recorded = Recorded()
    llm = LLMClient("http://llm.invalid/v1", "x", "m")
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=recorded))
    llm.derive = lambda **kw: llm
    engine = ConversationEngine(llm, ConversationStore(api.sessions), DbDefinitions(api.sessions))
    api.app.dependency_overrides[deps.get_conversation_engine] = lambda: engine
    if RUNNER:
        monkeypatch.setattr(settings, "tools_runner_url", RUNNER)
        monkeypatch.setattr(settings, "tools_runner_token", os.getenv("TOOLS_RUNNER_TEST_TOKEN", "tok"))
    tier = admin.post(f"{V1}/tiers", json={"name": "e2e", "max_tools": None, "code_tools": True}).json()
    client = admin.post(f"{V1}/clients", json={"name": "Acme", "slug": "acme", "tier_id": tier["id"]}).json()
    return SimpleNamespace(api=api, admin=admin, client=client, llm=recorded, base=mock_api_url)


def tool_defs(base: str) -> list[dict]:
    bearer = {"type": "bearer", "secret": "MOCK_TOKEN"}
    tools = [
        {"slug": "consultar_turnos", "type": "http", "definition": {
            "description": "Turnos libres de una sucursal en una fecha.",
            "http": {"method": "GET", "url": base + "/sucursales/{sucursal}/turnos", "auth": bearer,
                     "path": {"sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "Sucursal"}},
                     "query": {"fecha": {"type": "string", "description": "AAAA-MM-DD", "required": True}}}}},
        {"slug": "reservar_turno", "type": "http", "definition": {
            "description": "Reserva un turno libre.", "confirm": True,
            "http": {"method": "POST", "url": base + "/reservas", "auth": bearer, "sign": True,
                     "body": {"type": "object", "required": ["fecha", "hora", "nombre"], "properties": {
                         "sucursal": {"type": "string", "value": "centro"},
                         "fecha": {"type": "string", "description": "AAAA-MM-DD"},
                         "hora": {"type": "string", "description": "HH:MM"},
                         "nombre": {"type": "string", "description": "Nombre"}}}}}},
    ]
    if RUNNER:
        port = base.rsplit(":", 1)[1]
        tools.append({"slug": "deuda_cliente", "type": "code", "definition": {
            "description": "Deuda por DNI.", "secrets": ["MOCK_KEY"], "allowed_hosts": [f"mock-api.test:{port}"],
            "parameters": {"type": "object", "properties": {"dni": {"type": "string", "description": "DNI"}},
                           "required": ["dni"]},
            "code": ("export default async function ({ args, secrets }) {\n"
                     f"  const r = await fetch(`http://mock-api.test:{port}/deudores?dni=${{args.dni}}`, "
                     "{ headers: { 'X-API-Key': secrets.MOCK_KEY } });\n"
                     "  const d = await r.json();\n"
                     "  return { deuda: d.cliente?.saldo ?? null };\n}\n")}})
    return tools


def agent_definition(tools: list[dict]) -> dict:
    definition = reference_data("eval_tools")
    definition["tools"] = [{"tool": t["slug"]} for t in tools]
    return definition


def leaked(blob: str) -> bool:
    return any(v in blob for v in SECRETS.values())


def converse(w, agent_id: str, turns: list[str]) -> tuple[list[str], dict]:
    cid = w.admin.post(f"{V1}/conversations", json={"agent_id": agent_id}).json()["conversation_id"]
    replies = [w.admin.post(f"{V1}/conversations/{cid}/turns", json={"message": t}).json()["message"] for t in turns]
    return replies, w.admin.get(f"{V1}/conversations/{cid}").json()


def check_conversations(w, agent_id: str) -> None:
    """Consulta, reserva firmada, codigo (si hay sandbox) y fin de llamada, con el LLM grabado."""
    mock_api.RECEIVED.clear()
    w.llm.replies = [("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-05"})]),
                     ("Hay a las 10, 11:30 y 16.", [])]
    replies, state = converse(w, agent_id, ["¿Turnos el 5 en el centro?"])
    assert replies == ["Hay a las 10, 11:30 y 16."]
    tool_result = json.loads(w.llm.requests[-1]["messages"][-1]["content"])
    assert tool_result["data"]["turnos"] == ["10:00", "11:30", "16:00"]
    assert mock_api.RECEIVED[-1]["headers"]["authorization"] == f"Bearer {mock_api.TOKEN}"
    assert not leaked(json.dumps(state)) and not leaked(json.dumps(w.llm.requests))

    # confirm solo llega como texto en la descripcion: el modelo decide; aca reserva despues del si.
    reserve = next(t for t in w.llm.requests[0]["tools"] if t["function"]["name"] == "reservar_turno")
    assert "confirmá con la persona" in reserve["function"]["description"]
    w.llm.replies = [("¿Te reservo el 5 a las 11:30?", []),
                     ("", [("reservar_turno", {"fecha": "2026-11-05", "hora": "11:30", "nombre": "Ana"})]),
                     ("Listo, reservado.", [("end_call", {"motivo": "terminada"})]),
                     ('{"motivo": "turno"}', [])]          # la extraccion, al terminar
    replies, state = converse(w, agent_id, ["Reservame el de las 11:30, soy Ana.", "Sí."])
    got = [r for r in mock_api.RECEIVED if r["path"] == "/reservas"]
    assert len(got) == 1 and got[0]["signature_ok"] is True
    assert got[0]["headers"]["idempotency-key"].endswith(":call_0")
    assert state["status"] == "completed" and state["fields"]["motivo"] == "turno"

    if RUNNER:
        w.llm.replies = [("", [("deuda_cliente", {"dni": "30111222"})]), ("Debés 15.400.", [])]
        converse(w, agent_id, ["¿Cuánto debo? DNI 30111222"])
        assert json.loads(w.llm.requests[-1]["messages"][-1]["content"]) == {"ok": True, "data": {"deuda": 15400.5}}


def test_tools_by_api(world):
    w = world
    tools = tool_defs(w.base)
    for t in tools:
        assert w.admin.post(f"{V1}/clients/{w.client['id']}/tools", json=t).status_code == 201
    definition = agent_definition(tools)
    blank = {**definition, "tools": []}
    agent = w.admin.post(f"{V1}/agents", json={"client_id": w.client["id"], "name": "Sofía", "slug": "sofia",
                                               "definition": blank}).json()
    for name, value in SECRETS.items():
        assert w.admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": name, "value": value}).status_code == 201
    r = w.admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": {**agent["definition"],
                                                                                   "tools": definition["tools"]}})
    assert r.status_code == 200, r.text
    probe = w.admin.post(f"{V1}/clients/{w.client['id']}/tools/consultar_turnos/test",
                         json={"args": {"sucursal": "norte", "fecha": "2026-11-05"}, "agent_id": agent["id"]}).json()
    assert probe["ok"] and probe["data"]["turnos"] == ["15:00"] and not leaked(json.dumps(probe))
    check_conversations(w, agent["id"])


def test_tools_by_mcp(world):
    w = world
    key = w.admin.post(f"{V1}/clients/{w.client['id']}/api-keys", json={"name": "mcp", "scopes": ["mcp"]}).json()["key"]
    n = iter(range(1, 1000))

    def call(tool: str, **arguments):
        body = w.api.client.post("/mcp", headers={"Authorization": f"Bearer {key}"}, json={
            "jsonrpc": "2.0", "id": next(n), "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
        ).json()
        assert "error" not in body and not body["result"].get("isError"), body
        return body["result"]["structuredContent"]

    assert {"http", "code"} <= set(call("get_tool_schema"))
    tools = tool_defs(w.base)
    for t in tools:
        call("create_tool", **t)
    definition = agent_definition(tools)
    agent = call("create_agent", name="Sofía", slug="sofia_mcp", definition={**definition, "tools": []})
    for name, value in SECRETS.items():
        call("set_agent_secret", agent_id=agent["id"], name=name, value=value)
    assert not leaked(json.dumps(call("list_agent_secrets", agent_id=agent["id"])))
    probe = call("test_tool", slug="consultar_turnos", agent_id=agent["id"], args={"sucursal": "centro",
                                                                                   "fecha": "2026-11-06"})
    assert probe["ok"] and probe["data"]["turnos"] == ["09:00"]
    # Sin guardar: la misma definición con el secreto del agente.
    draft = call("test_tool_draft", type="http", definition=tools[0]["definition"], agent_id=agent["id"],
                 args={"sucursal": "centro", "fecha": "2026-11-06"})
    assert draft["ok"] and draft["data"]["turnos"] == ["09:00"] and not leaked(json.dumps(draft))
    # Rotar: un valor que la API rechaza falla, y el bueno vuelve a andar; después pasa al cliente.
    call("update_agent_secret", agent_id=agent["id"], name="MOCK_TOKEN", value="otro-token")
    bad = call("test_tool", slug="consultar_turnos", agent_id=agent["id"], args={"sucursal": "centro",
                                                                                 "fecha": "2026-11-06"})
    assert not bad["ok"]
    call("update_agent_secret", agent_id=agent["id"], name="MOCK_TOKEN", value=SECRETS["MOCK_TOKEN"],
         description="Token de la API de turnos")
    assert call("promote_agent_secret", agent_id=agent["id"], name="MOCK_TOKEN")["moved"]
    secret = next(x for x in call("list_client_secrets")["items"] if x["name"] == "MOCK_TOKEN")
    assert secret["description"] == "Token de la API de turnos"
    call("update_client_secret", name="MOCK_TOKEN", description="Token rotado")
    probe = call("test_tool", slug="consultar_turnos", args={"sucursal": "centro", "fecha": "2026-11-06"})
    assert probe["ok"]
    call("update_agent_definition", agent_id=agent["id"], definition={**agent["definition"],
                                                                      "tools": definition["tools"]})
    assert [v["revision"] for v in call("list_tool_versions", slug="consultar_turnos")["items"]] == [1]
    check_conversations(w, agent["id"])
