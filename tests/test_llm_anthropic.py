"""Cliente nativo de Anthropic (BYOK, docs/BYOK_LLM_PLAN.md, fase 2): mensajes, salida estructurada,
streaming y compatibilidad entre modelos, contra un SDK simulado."""
import asyncio
import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from cryptography.fernet import Fernet

from app.agents.templates import load_reference
from app.config import settings
from app.conversation.models import ConversationState, Message
from app.llm.anthropic_client import (
    OPENING,
    AnthropicClient,
    accepts_sampling,
    supports_effort,
    to_messages,
)
from app.llm.prompt import END_MARKER
from app.llm.resolver import LLMResolver, TurnLLM

from .test_api import V1, admin, client_user, make_client  # noqa: F401
from .test_llm_byok import agent_with_plan, new_connection


def reply(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class FakeStream:
    def __init__(self, chunks: list[str], final):
        self.chunks, self.final = chunks, final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def gen():
            for c in self.chunks:
                yield c
        return gen()

    async def get_final_message(self):
        return self.final


class FakeMessages:
    """create/stream devuelven lo que se encola; guarda los parametros de cada pedido."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls: list[dict] = []

    def _next(self, params):
        self.calls.append(params)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    async def create(self, **params):
        return self._next(params)

    def stream(self, **params):
        out = self._next(params)
        text = out.content[0].text
        return FakeStream([text[i:i + 7] for i in range(0, len(text), 7)], out)


def client_with(*outputs, model="claude-haiku-5-5", **kw) -> tuple[AnthropicClient, FakeMessages]:
    c = AnthropicClient("sk-ant-test", model, **kw)
    fake = FakeMessages(*outputs)
    c.client = SimpleNamespace(messages=fake)
    return c, fake


def bad_request(message="schema not supported"):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.BadRequestError(message, response=httpx2.Response(400, request=request), body=None)


@pytest.fixture
def state():
    return ConversationState(conversation_id="c1", agent_id="a", fields={},
                             messages=[Message(role="assistant", text="Hola, ¿en qué te ayudo?")])


def test_messages_conversion():
    system, msgs = to_messages([{"role": "system", "content": "A"}, {"role": "system", "content": "B"},
                                {"role": "assistant", "content": "Hola"}, {"role": "user", "content": "Che"}])
    assert system == "A\n\nB"
    assert msgs[0] == {"role": "user", "content": OPENING} and [m["role"] for m in msgs] == ["user", "assistant", "user"]
    _, msgs = to_messages([{"role": "user", "content": "x"}])
    assert msgs == [{"role": "user", "content": "x"}]


def test_model_compatibility_table():
    for model in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1", "claude-opus-4-8",
                  "claude-sonnet-4-6", "claude-opus-4-6"):
        assert supports_effort(model), model
    for model in ("claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5", "claude-3-7-sonnet"):
        assert not supports_effort(model), model
    assert accepts_sampling("claude-sonnet-4-6") and accepts_sampling("claude-haiku-4-5")
    for model in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-4-7", "claude-fable-5"):
        assert not accepts_sampling(model), model


def test_process_turn_streams_the_message_and_sends_native_params(state):
    workflow = load_reference("sales_discovery")
    payload = json.dumps({"assistant_message": "Hola Juan, ¿cómo estás?", "answered": False,
                          "next_objective": None, "status": "active"}, ensure_ascii=False)
    client, fake = client_with(reply(payload), temperature=0.4)
    spoken = []
    turn = asyncio.run(client.process_turn(workflow, state, "Hola, soy Juan", on_message=spoken.append))
    assert "".join(spoken) == "Hola Juan, ¿cómo estás?" and len(spoken) > 1     # llegó por partes
    assert turn.assistant_message == "Hola Juan, ¿cómo estás?" and turn.status == "active"
    params = fake.calls[0]
    assert params["output_config"]["format"]["type"] == "json_schema"
    assert params["output_config"]["effort"] == "low"
    assert "temperature" not in params and "thinking" not in params       # haiku 5.5 no lo acepta
    assert params["messages"][0]["role"] == "user" and "system" in params and params["max_tokens"] >= 2048


def test_older_models_get_temperature_and_no_effort(state):
    client, fake = client_with(reply("{}"), model="claude-haiku-4-5", temperature=0.4)
    asyncio.run(client.structured([{"role": "user", "content": "x"}],
                                  {"type": "object", "properties": {}}, "t"))
    params = fake.calls[0]
    assert params["temperature"] == 0.4 and "effort" not in params.get("output_config", {})


def test_root_anyof_schema_is_wrapped_and_unwrapped():
    schema = {"anyOf": [{"type": "object", "properties": {"action": {"enum": ["reply"]}},
                         "required": ["action"], "additionalProperties": False}]}
    client, fake = client_with(reply('{"result": {"action": "reply"}}'))
    raw, reasoning = asyncio.run(client.structured([{"role": "user", "content": "x"}], schema, "paso",
                                                   thinking=True, max_tokens=300))
    assert json.loads(raw) == {"action": "reply"} and reasoning is None
    sent = fake.calls[0]["output_config"]
    assert sent["format"]["schema"]["properties"]["result"] == schema and sent["effort"] == "medium"
    assert fake.calls[0]["max_tokens"] == 2048          # el piso: el razonamiento cuenta contra max_tokens


def test_rejected_schema_falls_back_to_prompt_mode_and_sticks():
    client, fake = client_with(bad_request(), reply('```json\n{"a": "x"}\n```'), reply('{"a": "y"}'))
    schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    raw, _ = asyncio.run(client.structured([{"role": "user", "content": "x"}], schema, "t"))
    assert json.loads(raw) == {"a": "x"}
    assert "format" in fake.calls[0]["output_config"]
    assert "format" not in fake.calls[1].get("output_config", {}) and "JSON Schema" in fake.calls[1]["system"]
    asyncio.run(client.structured([{"role": "user", "content": "x"}], schema, "t"))
    assert "JSON Schema" in fake.calls[2]["system"]        # no vuelve a probar el esquema


def test_refusal_raises_so_the_resolver_can_fall_back():
    client, _ = client_with(reply("", stop_reason="refusal"))
    with pytest.raises(RuntimeError, match="refusal"):
        asyncio.run(client.structured([{"role": "user", "content": "x"}], {"type": "object"}, "t"))


def test_converse_hides_the_end_marker(state):
    workflow = load_reference("sales_discovery")
    client, _ = client_with(reply(f"Chau, que andes bien. {END_MARKER}"))
    spoken = []
    turn = asyncio.run(client.converse(workflow, state, "chau", on_message=spoken.append))
    assert turn.status == "completed" and END_MARKER not in "".join(spoken)
    assert turn.assistant_message == "Chau, que andes bien."


def test_extract_returns_fields(state):
    workflow = load_reference("sales_discovery")
    names = list(workflow.fields)
    payload = json.dumps({n: None for n in names} | {"contact_name": "Juan"})
    client, _ = client_with(reply(payload))
    result = asyncio.run(client.extract(workflow, state))
    assert result.fields["contact_name"] == "Juan"


# --- Conexion y resolver -------------------------------------------------------------------

def test_anthropic_connection_has_fixed_url_and_is_resolved(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    acme = make_client(admin, "acme")
    conn = admin.post(f"{V1}/clients/{acme['id']}/llm-connections", json={
        "name": "Claude", "kind": "anthropic", "api_key": "sk-ant-api03-zzzz1234",
        "default_model": "claude-haiku-5-5", "base_url": "https://evil.example.com"})
    assert conn.status_code == 201, conn.text
    assert conn.json()["base_url"] == "https://api.anthropic.com" and conn.json()["last4"] == "1234"

    plan = {"stages": [{"from_turn": 1, "connection": conn.json()["id"], "model": "claude-haiku-5-5",
                        "temperature": 0.2}]}
    agent = agent_with_plan(admin, acme, plan).json()
    resolver = LLMResolver(local=object(), sessions=api.sessions)
    from app.models import Agent
    with api.sessions() as s:
        workflow = api.engine.definitions.get(agent["id"], s.get(Agent, agent["id"]).version)
    llm = resolver.for_turn(workflow, 1, acme["id"])
    assert isinstance(llm, TurnLLM) and isinstance(llm.primary, AnthropicClient)
    assert llm.provider == "anthropic" and llm.primary.temperature is None      # haiku 5.5: sin muestreo


def test_connection_test_uses_the_anthropic_client(api, admin, monkeypatch):
    from app.services import llm_connections as svc
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme, name="Claude", kind="anthropic", default_model="claude-haiku-5-5")
    fake = FakeMessages(reply('{"ok": true}'))
    original = svc._client

    def build(row, model, mode):
        client = original(row, model, mode)
        assert isinstance(client, AnthropicClient) and client.model == "claude-haiku-5-5"
        client.client = SimpleNamespace(messages=fake)
        return client
    monkeypatch.setattr(svc, "_client", build)
    out = admin.post(f"{V1}/clients/{acme['id']}/llm-connections/{conn['id']}/test", json={}).json()
    assert out["last_test_ok"] is True and out["json_mode"] == "json_schema"
