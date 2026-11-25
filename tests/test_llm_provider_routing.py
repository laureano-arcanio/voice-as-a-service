"""Runtime del enrutado a proveedores de OpenRouter (docs/features/LLM_CONEXIONES.md, "Flujo: LLM por
etapa"): el `provider` de una etapa viaja en cada pedido (turno, extraccion, structured) de una conexion
openrouter, y no en las demas. Sin modelo real: el body se captura con httpx.MockTransport."""
import asyncio
import json

import httpx
import pytest

from app.agents.templates import load_reference
from app.conversation.models import ConversationState, Generation, LlmStage, Message
from app.llm import client as client_module
from app.llm.anthropic_client import AnthropicClient
from app.llm.client import LLMClient
from app.llm.openrouter import OpenRouterProvider, provider_body
from app.llm.resolver import ConnectionData, LLMResolver

PROVIDER = {"only": ["nebius/fp4"], "allow_fallbacks": False, "require_parameters": True}


def chat_reply(content):
    """La respuesta minima de chat.completions que el SDK parsea (sin tool_calls: un solo pedido)."""
    return {"id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": "vendor/model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


def state():
    return ConversationState(conversation_id="c1", agent_id="a", fields={},
                             messages=[Message(role="assistant", text="Hola, ¿en qué te ayudo?")])


# --- LLMClient ------------------------------------------------------------------------------

def test_client_with_provider_builds_extra_body():
    client = LLMClient("https://openrouter.ai/api/v1", "k", "vendor/model", profile="openrouter",
                       provider=PROVIDER)
    assert client.provider == PROVIDER
    assert client.options["extra_body"]["provider"] == PROVIDER


def test_client_without_provider_has_no_extra_body():
    client = LLMClient("https://openrouter.ai/api/v1", "k", "vendor/model", profile="openrouter")
    assert client.provider is None
    assert "extra_body" not in client.options


def test_provider_does_not_touch_sampling():
    """extra_body lleva el provider aparte: no pisa los parametros de sampling del agente."""
    client = LLMClient("https://openrouter.ai/api/v1", "k", "vendor/model", profile="openrouter",
                       generation=Generation(params={"temperature": 0.3}), provider=PROVIDER)
    assert client.options["temperature"] == 0.3
    assert client.options["extra_body"] == {"provider": PROVIDER}


def test_derive_preserves_provider():
    client = LLMClient("https://openrouter.ai/api/v1", "k", "vendor/model", profile="openrouter",
                       provider=PROVIDER)
    derived = client.derive(generation=Generation(params={"temperature": 0.5}))
    assert derived.provider == PROVIDER
    assert derived.options["extra_body"]["provider"] == PROVIDER
    assert derived.options["temperature"] == 0.5


# --- provider_body --------------------------------------------------------------------------

def test_provider_body_none_without_tags_and_dict_with_them():
    assert provider_body(None) is None
    assert provider_body(OpenRouterProvider(only=[])) is None
    assert provider_body(OpenRouterProvider(only=["nebius/fp4"], allow_fallbacks=False)) == PROVIDER


# --- LLMResolver._client --------------------------------------------------------------------

def resolver_without_sessions():
    return LLMResolver(local=object(), sessions=None)


def conn(kind="openrouter", **extra):
    base = {"openrouter": "https://openrouter.ai/api/v1", "openai_compatible": "https://x.example/v1",
            "anthropic": "https://api.anthropic.com"}[kind]
    return ConnectionData(id=f"c-{kind}", client_id="acme", kind=kind, base_url=base, api_key="k",
                          json_mode="json_schema", stamp=0.0, **extra)


def test_resolver_passes_provider_for_openrouter_only():
    resolver = resolver_without_sessions()
    stage = LlmStage(from_turn=1, connection="c1", model="vendor/model", provider=PROVIDER)

    orclient = resolver._client(conn("openrouter"), stage, {}, {"max_tokens": None})
    assert isinstance(orclient, LLMClient) and orclient.provider == PROVIDER

    compat = resolver._client(conn("openai_compatible"), stage, {}, {"max_tokens": None})
    assert isinstance(compat, LLMClient) and compat.provider is None

    anth = resolver._client(conn("anthropic"), stage, {}, {"max_tokens": None})
    assert isinstance(anth, AnthropicClient)


def test_resolver_stage_without_provider_gets_no_provider():
    resolver = resolver_without_sessions()
    stage = LlmStage(from_turn=1, connection="c1", model="vendor/model")
    client = resolver._client(conn("openrouter"), stage, {}, {"max_tokens": None})
    assert isinstance(client, LLMClient) and client.provider is None
    assert "extra_body" not in client.options


def test_cache_key_changes_with_the_provider():
    """Dos etapas con distinto provider no comparten cliente; la misma etapa, si."""
    resolver = resolver_without_sessions()
    data = conn("openrouter")
    stage_a = LlmStage(from_turn=1, connection="c1", model="vendor/model",
                       provider={"only": ["baseten"]})
    stage_b = LlmStage(from_turn=1, connection="c1", model="vendor/model",
                       provider={"only": ["nebius/fp4"]})

    a = resolver._client(data, stage_a, {}, {"max_tokens": None})
    b = resolver._client(data, stage_b, {}, {"max_tokens": None})
    assert a is not b
    assert a.provider["only"] == ["baseten"] and b.provider["only"] == ["nebius/fp4"]

    a2 = resolver._client(data, stage_a, {}, {"max_tokens": None})
    assert a2 is a


# --- El provider llega al body (converse / extract / structured) ------------------------------

@pytest.fixture
def captured(monkeypatch):
    """Un LLMClient openrouter con provider, cuyo AsyncOpenAI manda a un MockTransport que guarda
    cada body de chat.completions y contesta lo que se encola."""
    real = client_module.AsyncOpenAI
    seen = []
    replies = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=replies.pop(0))

    monkeypatch.setattr(client_module, "AsyncOpenAI",
                        lambda **kw: real(**kw, http_client=httpx.AsyncClient(
                            transport=httpx.MockTransport(handler))))
    client = LLMClient("https://openrouter.ai/api/v1", "k", "vendor/model", profile="openrouter",
                       provider=PROVIDER)
    return client, seen, replies


def test_provider_reaches_converse_extract_and_structured(captured):
    client, seen, replies = captured
    workflow = load_reference("sales_discovery")

    replies.append(chat_reply("Hola, Juan."))
    turn = asyncio.run(client.converse(workflow, state(), "Hola, soy Juan"))
    assert turn.assistant_message == "Hola, Juan."

    replies.append(chat_reply(json.dumps({"fields": {}, "summary": None})))
    asyncio.run(client.extract(workflow, state()))

    replies.append(chat_reply('{"ok": true}'))
    raw, _ = asyncio.run(client.structured([{"role": "user", "content": "x"}],
                                           {"type": "object", "properties": {}}, "paso"))
    assert json.loads(raw) == {"ok": True}

    assert len(seen) == 3
    for body in seen:
        # extra_body lo fusiona el SDK al body: provider va como clave de primer nivel.
        assert body["provider"] == PROVIDER
