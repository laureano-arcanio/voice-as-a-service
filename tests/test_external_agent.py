"""Agente externo (docs/features/LLM_CONEXIONES.md): el motor external le pide cada turno al endpoint del cliente
(compatible con OpenAI, en streaming), con las herramientas end_call y transfer_call; errores sin respaldo al LLM
propio y solo en los planes que lo incluyen."""
import asyncio
import json

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.agents.templates import reference_data
from app.config import settings
from app.conversation.models import Workflow
from app.llm import client as client_module
from app.llm import external as external_module
from app.services import llm_connections as svc

from .test_api import V1, admin, make_client, make_tier  # noqa: F401
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)
from .voice_harness import add_tool, http_tool

REAL_CHECK = svc.check_base_url


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


@pytest.fixture(autouse=True)
def fake_endpoint_url(monkeypatch):
    """Los endpoints de prueba son http://agent.test (el servidor solo acepta https y hosts publicos, tambien
    del admin desde el 27-oct-2026): sin DNS ni red, el chequeo de la URL se salta; su prueba usa REAL_CHECK."""
    monkeypatch.setattr(svc, "check_base_url", lambda u: u)


def sse(*chunks: dict) -> bytes:
    lines = [f"data: {json.dumps({'id': 'x', 'object': 'chat.completion.chunk', 'created': 0, 'model': 'm', 'choices': [{'index': 0, 'delta': c, 'finish_reason': None}]})}\n\n"
             for c in chunks]
    return ("".join(lines) + "data: [DONE]\n\n").encode()


class Endpoint:
    """El endpoint del cliente: guarda cada pedido y contesta lo que diga `reply` (bytes SSE, un status o sleep)."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.replies: list = []

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies.pop(0) if self.replies else sse({"content": "ok"})
        if isinstance(reply, int):
            return httpx.Response(reply, json={"error": {"message": "boom"}})
        if isinstance(reply, float):
            await asyncio.sleep(reply)
            reply = sse({"content": "tarde"})
        return httpx.Response(200, content=reply, headers={"content-type": "text/event-stream"})

    def body(self, n: int = -1) -> dict:
        return json.loads(self.requests[n].content)


@pytest.fixture
def endpoint(monkeypatch):
    ep = Endpoint()
    real = external_module.AsyncOpenAI
    for module in (external_module, client_module):     # el motor y la prueba de la conexion
        monkeypatch.setattr(module, "AsyncOpenAI", lambda **kw: real(
            **kw, http_client=httpx.AsyncClient(transport=httpx.MockTransport(ep.handle))))
    return ep


def external_definition(connection: str, **cfg) -> dict:
    return {**reference_data("sales_discovery"),
            "external": {"connection": connection, "first_token_timeout_ms": 1500, **cfg}}


SEQ = iter(range(1000))


def setup(admin, *, plan: bool = True, kind: str = "openai_compatible", **cfg):
    """Cliente con el plan, su conexion y el agente externo. Devuelve (cliente, conexion, respuesta del alta)."""
    n = next(SEQ)
    tier = make_tier(admin, name=f"tier-{n}", external_agent=plan)
    acme = make_client(admin, f"acme{n}", tier=tier)
    body = {"name": "Mi agente", "kind": kind, "api_key": "sk-agent-1234", "default_model": "acme-agent"}
    if kind == "openai_compatible":
        body["base_url"] = "http://agent.test/v1"
    r = admin.post(f"{V1}/clients/{acme['id']}/llm-connections", json=body)
    assert r.status_code == 201, r.text
    conn = r.json()
    r = admin.post(f"{V1}/agents", json={"client_id": acme["id"], "name": "Externo",
                                         "definition": external_definition(conn["id"], **cfg)})
    return acme, conn, r


# --- Definicion y alta -------------------------------------------------------------------------

def test_definition_validation():
    base = {**reference_data("sales_discovery"), "id": "x", "version": 1}
    # Un solo motor: "Tu propio agente" es tener `external`. Una definicion vieja con engine external y sin
    # la conexion se lee como un agente comun.
    assert Workflow.model_validate({**base, "engine": "external"}).external is None
    with pytest.raises(ValidationError, match="external.connection"):
        Workflow.model_validate({**base, "external": {}})
    with pytest.raises(ValidationError, match="las herramientas son las de tu agente"):
        Workflow.model_validate({**base, "tools": [{"tool": "consultar"}], "external": {"connection": "c"}})
    with pytest.raises(ValidationError, match="on_errors"):
        Workflow.model_validate({**base, "external": {"connection": "c", "on_errors": "transfer:a1"}})
    w = Workflow.model_validate({**base, "engine": "external", "analysis": {"outcomes": [
        {"id": "fin", "label": "Fin"}]}, "external": {"connection": "c", "model": " "}})
    assert w.analysis_fields == {} and w.external.model is None and w.external.on_errors == "hang_up"
    # Sin analysis, sin resultados: el agente no elige outcome.
    bare = Workflow.model_validate({"id": "x", "version": 1, "agent": {"name": "A", "language": "es"},
                                    "external": {"connection": "c"}})
    assert bare.outcomes == [] and bare.analysis is None


def test_create_requires_plan_and_openai_compatible_connection(api, admin):
    _, _, r = setup(admin, plan=False)
    assert r.status_code == 429 and r.json()["code"] == "external_agent_not_in_plan"
    _, _, r = setup(admin, kind="openrouter")
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "external.connection"
    acme, conn, r = setup(admin)
    assert r.status_code == 201, r.text
    assert r.json()["own_agent"] is True and "engine" not in r.json()["definition"]
    features = admin.get(f"{V1}/plan/features", params={"client_id": acme["id"]})
    if features.status_code == 200:
        assert features.json()["features"]["external_agent"]["enabled"] is True


# --- Turnos ------------------------------------------------------------------------------------

async def start(api, admin, **cfg):
    acme, conn, r = setup(admin, **cfg)
    assert r.status_code == 201, r.text
    state, opening = api.engine.start_conversation(r.json()["id"], acme["id"])
    return state


async def test_turn_streams_text_and_sends_history_tools_and_headers(api, admin, endpoint):
    state = await start(api, admin, system="Sos el agente de Acme.")
    endpoint.replies = [sse({"content": "Hola, "}, {"content": "¿en qué te ayudo?"})]
    spoken = []
    state, turn = await api.engine.process_turn(state.conversation_id, "Quiero un turno", on_message=spoken.append)
    assert spoken == ["Hola, ", "¿en qué te ayudo?"] and turn.assistant_message == "Hola, ¿en qué te ayudo?"
    assert turn.status == "active" and state.messages[-1].llm[0]["provider"] == "external"

    body, request = endpoint.body(), endpoint.requests[-1]
    assert request.url.path == "/v1/chat/completions" and request.headers["authorization"] == "Bearer sk-agent-1234"
    assert body["model"] == "acme-agent" and body["stream"] is True and body["user"] == state.conversation_id
    assert [m["role"] for m in body["messages"]] == ["system", "assistant", "user"]
    assert body["messages"][0]["content"] == "Sos el agente de Acme." and body["messages"][-1]["content"] == "Quiero un turno"
    assert [t["function"]["name"] for t in body["tools"]] == ["end_call"]     # sin areas, sin transfer_call
    assert request.headers["x-atentina-conversation-id"] == state.conversation_id
    assert request.headers["x-atentina-channel"] == "voice" and request.headers["x-atentina-turn"] == "1"
    assert set(body) <= {"model", "messages", "tools", "stream", "user"}   # solo campos estandar

    # El turno siguiente lleva todo el historial.
    await api.engine.process_turn(state.conversation_id, "El jueves")
    assert [m["content"] for m in endpoint.body()["messages"][1:]] == [
        state.messages[0].text, "Quiero un turno", "Hola, ¿en qué te ayudo?", "El jueves"]


async def test_end_call_completes_with_outcome(api, admin, endpoint):
    state = await start(api, admin)
    outcomes = [o["id"] for o in reference_data("sales_discovery")["analysis"]["outcomes"]]
    endpoint.replies = [sse({"content": "Chau."}, {"tool_calls": [
        {"index": 0, "id": "c1", "type": "function", "function": {"name": "end_call", "arguments": ""}}]},
        {"tool_calls": [{"index": 0, "function": {"arguments": json.dumps({"outcome": outcomes[0]})}}]})]
    state, turn = await api.engine.process_turn(state.conversation_id, "Nada más")
    assert turn.status == "completed" and turn.end_reason is None and turn.assistant_message == "Chau."
    assert state.status == "completed" and state.progress.outcome == outcomes[0]

    # Un outcome que no existe: el default (el ultimo).
    state = await start(api, admin)
    endpoint.replies = [sse({"tool_calls": [{"index": 0, "id": "c", "type": "function",
                                             "function": {"name": "end_call", "arguments": '{"outcome": "x"}'}}]})]
    state, turn = await api.engine.process_turn(state.conversation_id, "Chau")
    assert turn.status == "completed" and state.progress.outcome == outcomes[-1]


async def test_transfer_call_only_with_areas(api, admin, endpoint):
    state = await start(api, admin)
    st = api.engine.store.get(state.conversation_id)
    st.progress.handoff_areas = [{"id": "a1", "name": "Ventas", "when": "si quiere comprar"}]
    api.engine.store.save(st)
    endpoint.replies = [sse({"content": "Te paso."}, {"tool_calls": [
        {"index": 0, "id": "c", "type": "function", "function": {"name": "transfer_call", "arguments": '{"area": "Ventas"}'}}]})]
    state, turn = await api.engine.process_turn(state.conversation_id, "Quiero comprar")
    tool = endpoint.body()["tools"][1]["function"]
    assert tool["name"] == "transfer_call" and tool["parameters"]["properties"]["area"]["enum"] == ["Ventas"]
    assert turn.handoff == "Ventas" and turn.status == "active"


async def test_errors_say_message_then_hang_up(api, admin, endpoint):
    state = await start(api, admin, max_errors=2)
    endpoint.replies = [500, 2.5, sse({"content": "Volví"}), 500, 500]
    spoken = []
    state, turn = await api.engine.process_turn(state.conversation_id, "Hola", on_message=spoken.append)
    assert spoken == ["Disculpá, se me cortó. ¿Me lo repetís?"] and turn.status == "active"
    assert state.progress.external_errors == 1 and "endpoint_error" in state.messages[-1].llm[0]["error"]

    # Sin primer token a tiempo (1500 ms): segundo error seguido, corta.
    state, turn = await api.engine.process_turn(state.conversation_id, "¿Hola?")
    assert turn.status == "completed" and turn.end_reason == "external_error"
    assert "timeout" in state.messages[-1].llm[0]["error"] and state.progress.outcome is None

    # Un turno bueno pone el contador en cero.
    state = await start(api, admin, max_errors=2)
    state, _ = await api.engine.process_turn(state.conversation_id, "Hola")
    assert state.progress.external_errors == 0
    state, turn = await api.engine.process_turn(state.conversation_id, "Sigo")
    assert turn.status == "active" and state.progress.external_errors == 1


async def test_plan_without_feature_hangs_up(api, admin, endpoint):
    state = await start(api, admin)
    with api.sessions() as s:
        from app.models import Client, Tier
        s.get(Tier, s.get(Client, state.client_id).tier_id).external_agent = False
        s.commit()
    api.engine.external = None      # sin la cache de 30 s
    state, turn = await api.engine.process_turn(state.conversation_id, "Hola")
    assert turn.status == "completed" and turn.end_reason == "external_agent_not_in_plan"
    assert endpoint.requests == []


def test_connection_test_as_agent_endpoint(api, admin, endpoint):
    acme, conn, _ = setup(admin)
    url = f"{V1}/clients/{acme['id']}/llm-connections/{conn['id']}/test"
    endpoint.replies = [sse({"content": "Hola, "}, {"content": "todo bien."})]
    r = admin.post(url, json={"mode": "external"})
    assert r.status_code == 200 and r.json()["last_test_ok"] is True
    assert r.json()["last_test_detail"].startswith("streaming · primer texto") and "todo bien" in r.json()["last_test_detail"]
    body = endpoint.body()
    assert body["stream"] is True and body["tools"][0]["function"]["name"] == "end_call"
    assert endpoint.requests[-1].headers["x-atentina-mode"] == "prueba"

    endpoint.replies = [401]
    r = admin.post(url, json={"mode": "external"})
    assert r.json()["last_test_ok"] is False and "clave" in r.json()["last_test_detail"]


# --- Todo por API key y por MCP -------------------------------------------------------------------

def test_api_key_and_mcp_manage_the_endpoint(api, admin, endpoint, monkeypatch):
    from .test_mcp import Mcp, new_key

    tier = make_tier(admin, name="tier-keys", external_agent=True)
    acme = make_client(admin, "acmekeys", tier=tier)
    calls = api.client
    key = new_key(admin, acme, scopes=["calls"])
    auth = {"Authorization": f"Bearer {key}"}
    url = f"{V1}/clients/{acme['id']}/llm-connections"
    # Nadie puede apuntar a una red interna ni a http: el endpoint de prueba es publico y https.
    monkeypatch.setattr(svc, "check_base_url", REAL_CHECK)
    body = {"name": "Mi agente", "kind": "openai_compatible", "base_url": "http://agent.test/v1",
            "api_key": "sk-agent-1234", "default_model": "acme-agent"}
    assert calls.post(url, json=body, headers=auth).json()["code"] == "invalid_base_url"
    monkeypatch.setattr(svc, "check_base_url", lambda u: u)
    r = calls.post(url, json=body, headers=auth)
    assert r.status_code == 201 and r.json()["created_by"] is None, r.text
    conn = r.json()
    r = calls.post(f"{url}/{conn['id']}/test", json={"mode": "external"}, headers=auth)
    assert r.status_code == 200 and r.json()["last_test_ok"] is True
    r = calls.post(f"{V1}/agents", headers=auth, json={"name": "Externo", "definition": external_definition(conn["id"])})
    assert r.status_code == 201, r.text

    # mcp_read: lista pero no carga.
    read = {"Authorization": f"Bearer {new_key(admin, acme, scopes=['mcp_read'])}"}
    assert [c["id"] for c in calls.get(url, headers=read).json()] == [conn["id"]]
    assert calls.post(url, json={**body, "name": "Otra"}, headers=read).status_code == 403

    # MCP: cargar (destructiva: el cliente la confirma) y probar.
    mcp = Mcp(api, new_key(admin, acme))
    tools = mcp.tools()
    assert tools["create_llm_connection"]["annotations"]["destructiveHint"] is True
    out = mcp.call("create_llm_connection", **{**body, "name": "Por MCP"})
    assert not out.get("isError"), out
    new_id = out["structuredContent"]["id"]
    out = mcp.call("test_llm_connection", connection_id=new_id, mode="external")
    assert not out.get("isError") and out["structuredContent"]["last_test_ok"] is True
    # Cambiar (rotar la clave) y borrar, también destructivas.
    assert tools["update_llm_connection"]["annotations"]["destructiveHint"] is True
    out = mcp.call("update_llm_connection", connection_id=new_id, name="Renombrada", api_key="sk-agent-5678")
    assert not out.get("isError") and out["structuredContent"]["name"] == "Renombrada", out
    out = mcp.call("delete_llm_connection", connection_id=new_id)
    assert not out.get("isError"), out
    assert new_id not in [c["id"] for c in calls.get(url, headers=auth).json()]


# --- Workflows -------------------------------------------------------------------------------------

async def test_pre_call_reaches_the_external_agent_by_header_not_prompt(api, admin, endpoint, mock_api_url):  # noqa: F811
    """Tu propio agente no usa el prompt de la definicion: el pre-call corre igual, lo visible va en
    X-Atentina-Variables (como los datos de campaña), lo oculto no sale, y la apertura se renderiza. La guia de
    WhatsApp no aplica: el cuerpo lleva el system de la conexion, sin datos."""
    acme, conn, r = setup(admin, system="Sos el agente de Acme.")
    assert r.status_code == 201, r.text
    assert admin.patch(f"{V1}/tiers/{acme['tier']['id']}", json={"max_tools": None}).status_code == 200
    tool = http_tool("buscar_ficha", mock_api_url + "/identificar", assign=[
        {"var": "nombre", "path": "name"}, {"var": "nota", "path": "operator_note", "hide": True}])
    add_tool(admin, acme, tool)
    agent = r.json()
    definition = {**agent["definition"], "workflows": {"pre_call": {"tool": "buscar_ficha"}}}
    definition["first_message"] = "Hola {{nombre}}."
    saved = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition})
    assert saved.status_code == 200, saved.text

    state, _ = api.engine.start_conversation(agent["id"], acme["id"])
    assert await api.engine.run_pre_call(state.conversation_id) == "Hola María Gómez."
    endpoint.replies = [sse({"content": "Hola María."})]
    await api.engine.process_turn(state.conversation_id, "Buen día")

    assert json.loads(endpoint.requests[-1].headers["x-atentina-variables"]) == {"nombre": "María Gómez"}
    assert "x-atentina-contact" not in endpoint.requests[-1].headers
    assert "x-atentina-context" not in endpoint.requests[-1].headers
    body = endpoint.body()
    assert body["messages"][0]["content"] == "Sos el agente de Acme."
    assert "al día" not in json.dumps(body) and "al d" not in endpoint.requests[-1].headers["x-atentina-variables"]
    assert api.engine.store.get(state.conversation_id).progress.variables["nota"] == "María Gómez, al día"
