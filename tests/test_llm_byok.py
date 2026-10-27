"""BYOK de LLM (docs/BYOK_LLM_PLAN.md): conexiones del cliente, etapas por turno, fallback al
servidor propio y aislamiento entre clientes."""
import asyncio

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.agents.templates import reference_data
from app.config import settings
from app.conversation.models import AgentTurn, Generation, LlmPlan, LlmStage
from app.llm.client import LLMClient
from app.llm.resolver import BREAKER_FAILS, LLMResolver
from app.services import llm_connections as svc

from .helpers import FakeLLM
from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def turn(text: str) -> AgentTurn:
    return AgentTurn(assistant_message=text, status="active")


class External(FakeLLM):
    """El proveedor externo: como FakeLLM, con modelo y, opcionalmente, un error."""
    label = "openrouter:vendor/model"
    model = "vendor/model"

    def __init__(self, *turns, error: Exception | None = None, **kw):
        super().__init__(*turns, **kw)
        self.error = error

    async def converse(self, workflow, state, user_message, on_message=None):
        if self.error:
            raise self.error
        return await super().converse(workflow, state, user_message, on_message)

    async def extract(self, workflow, state):
        if self.error:
            raise self.error
        return await super().extract(workflow, state)


def new_connection(admin, client, name="Mi OpenRouter", **extra):
    body = {"name": name, "kind": "openrouter", "api_key": "sk-or-v1-abcdef1234", "default_model": "vendor/model",
            **extra}
    r = admin.post(f"{V1}/clients/{client['id']}/llm-connections", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def agent_with_plan(admin, client, plan):
    definition = {**reference_data("sales_discovery"), "llm": plan}
    return admin.post(f"{V1}/agents", json={"client_id": client["id"], "name": "Ventas", "definition": definition})


# --- Definicion -----------------------------------------------------------------------------

def test_plan_validation():
    ok = LlmPlan(stages=[LlmStage(from_turn=1), LlmStage(from_turn=4, connection="c1", model="m")])
    assert ok.stage_for(1).connection is None and ok.stage_for(3).connection is None
    assert ok.stage_for(4).connection == "c1" and ok.stage_for(30).model == "m"
    with pytest.raises(ValidationError, match="turno 1"):
        LlmPlan(stages=[LlmStage(from_turn=2)])
    with pytest.raises(ValidationError, match="crecer"):
        LlmPlan(stages=[LlmStage(from_turn=1), LlmStage(from_turn=1, connection="c", model="m")])
    with pytest.raises(ValidationError, match="necesita el modelo"):
        LlmStage(from_turn=1, connection="c1")
    with pytest.raises(ValidationError, match="solo vale"):
        LlmStage(from_turn=1, model="m")
    with pytest.raises(ValidationError):
        LlmPlan(stages=[LlmStage(from_turn=n) for n in (1, 2, 3, 4)])


# --- Conexiones -----------------------------------------------------------------------------

def test_client_and_admin_manage_connections_and_key_is_never_returned(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    user = client_user(api, admin, acme)
    mine = new_connection(user, acme)
    assert mine["last4"] == "1234" and "api_key" not in mine and mine["base_url"] == "https://openrouter.ai/api/v1"
    assert mine["json_mode"] == "json_schema" and mine["used_by"] == 0

    # La key va cifrada en la base.
    from app.models import LlmConnection
    with api.sessions() as s:
        row = s.get(LlmConnection, mine["id"])
        assert "sk-or-v1" not in row.api_key_enc and row.created_by is not None

    # El admin carga y ve las de cualquier cliente; el cliente, solo las suyas.
    theirs = new_connection(admin, other, name="De otro")
    assert [c["name"] for c in user.get(f"{V1}/clients/{acme['id']}/llm-connections").json()] == ["Mi OpenRouter"]
    assert user.get(f"{V1}/clients/{other['id']}/llm-connections").status_code == 404
    assert user.patch(f"{V1}/clients/{other['id']}/llm-connections/{theirs['id']}", json={"name": "x"}).status_code == 404
    assert user.delete(f"{V1}/clients/{acme['id']}/llm-connections/{theirs['id']}").status_code == 404

    # Rotar la key y renombrar; nombre repetido: 409.
    r = user.patch(f"{V1}/clients/{acme['id']}/llm-connections/{mine['id']}",
                   json={"name": "Principal", "api_key": "sk-or-v1-nueva9999"})
    assert r.status_code == 200 and r.json()["last4"] == "9999" and r.json()["last_test_ok"] is None
    new_connection(user, acme, name="Segunda")
    dup = user.post(f"{V1}/clients/{acme['id']}/llm-connections",
                    json={"name": "segunda", "kind": "openrouter", "api_key": "k"})
    assert dup.status_code == 409

    assert user.delete(f"{V1}/clients/{acme['id']}/llm-connections/{mine['id']}").status_code == 204
    assert [c["name"] for c in user.get(f"{V1}/clients/{acme['id']}/llm-connections").json()] == ["Segunda"]


def test_base_url_blocks_private_networks_for_clients_but_not_admins(api, admin):
    acme = make_client(admin, "acme")
    user = client_user(api, admin, acme)
    url = f"{V1}/clients/{acme['id']}/llm-connections"
    body = {"name": "propio", "kind": "openai_compatible", "api_key": "k", "default_model": "m"}
    for bad in ("http://api.example.com/v1", "https://10.0.0.5/v1", "https://127.0.0.1:8000/v1",
                "https://user:pw@8.8.8.8/v1", "ftp://8.8.8.8/v1"):
        r = user.post(url, json={**body, "base_url": bad})
        assert r.status_code == 422 and r.json()["code"] == "invalid_base_url", bad
    assert user.post(url, json=body).status_code == 422          # falta base_url
    assert admin.post(url, json={**body, "base_url": "http://vllm-llm:8000/v1"}).status_code == 201
    assert user.post(url, json={**body, "name": "publico", "base_url": "https://8.8.8.8/v1"}).status_code == 201


def test_test_endpoint_stores_result_and_json_mode(api, admin, monkeypatch):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)

    async def probe(row, model):
        assert model == "vendor/model"
        return True, "json_schema · 312 ms", "json_schema"
    monkeypatch.setattr(svc, "_probe", probe)
    r = admin.post(f"{V1}/clients/{acme['id']}/llm-connections/{conn['id']}/test", json={})
    assert r.status_code == 200
    out = r.json()
    assert out["last_test_ok"] is True and out["json_mode"] == "json_schema" and "312" in out["last_test_detail"]

    async def failing(row, model):
        return False, "clave inválida o sin permiso", row.json_mode
    monkeypatch.setattr(svc, "_probe", failing)
    out = admin.post(f"{V1}/clients/{acme['id']}/llm-connections/{conn['id']}/test", json={"model": "x"}).json()
    assert out["last_test_ok"] is False and out["json_mode"] == "json_schema"      # no pisa el modo anterior


def test_agent_can_only_use_connections_of_its_client(api, admin):
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    foreign = new_connection(admin, other)
    plan = {"stages": [{"from_turn": 1}, {"from_turn": 3, "connection": foreign["id"], "model": "m"}]}
    r = agent_with_plan(admin, acme, plan)
    assert r.status_code == 422
    assert r.json()["errors"][0]["path"] == "llm.stages.1.connection"

    mine = new_connection(admin, acme)
    plan["stages"][1]["connection"] = mine["id"]
    r = agent_with_plan(admin, acme, plan)
    assert r.status_code == 201, r.text
    assert r.json()["definition"]["llm"]["stages"][1]["from_turn"] == 3
    # Con el agente usandola, la lista lo informa.
    listed = admin.get(f"{V1}/clients/{acme['id']}/llm-connections").json()
    assert listed[0]["used_by"] == 1


# --- Motor: etapas, fallback y breaker ------------------------------------------------------

def setup_agent(api, admin, monkeypatch, external: External, *, fallback=True, from_turn=3):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    external_stage = {"from_turn": from_turn, "connection": conn["id"], "model": "vendor/model"}
    plan = {"stages": ([{"from_turn": 1}] if from_turn > 1 else []) + [external_stage], "fallback_local": fallback}
    agent = agent_with_plan(admin, acme, plan).json()
    monkeypatch.setattr(LLMResolver, "_client", lambda self, data, stage, generation, defaults: external)
    state, _ = api.engine.start_conversation(agent["id"], acme["id"])
    return state.conversation_id, acme


def test_stage_switches_at_the_configured_turn(api, admin, monkeypatch):
    external = External(turn("desde el externo 3"), turn("desde el externo 4"))
    api.llm.turns = [turn("local 1"), turn("local 2")]
    cid, _ = setup_agent(api, admin, monkeypatch, external)

    async def run():
        out = []
        for text in ("uno", "dos", "tres", "cuatro"):
            _, result = await api.engine.process_turn(cid, text)
            out.append(result.assistant_message)
            await api.engine.wait_extraction(cid)
        return out

    assert asyncio.run(run()) == ["local 1", "local 2", "desde el externo 3", "desde el externo 4"]
    state = api.engine.store.get(cid)
    replies = [m for m in state.messages if m.role == "assistant"][1:]
    assert [m.llm[0].get("provider") for m in replies] == [None, None, "openrouter", "openrouter"]
    assert replies[2].llm[0]["model"] == "vendor/model"
    # La extraccion (al terminar) usa la etapa del ultimo turno.
    asyncio.run(api.engine.finish(cid))
    assert len(api.llm.extract_calls) == 0 and len(external.extract_calls) == 1


def test_provider_error_falls_back_to_local(api, admin, monkeypatch):
    external = External(error=RuntimeError("503 del proveedor"))
    api.llm.turns = [turn("respaldo")]
    cid, _ = setup_agent(api, admin, monkeypatch, external, from_turn=1)

    _, result = asyncio.run(api.engine.process_turn(cid, "hola"))
    assert result.assistant_message == "respaldo"
    trace = api.engine.store.get(cid).messages[-1].llm[0]
    assert trace["provider"] == "local" and trace["fallback_from"] == "openrouter:vendor/model"
    assert trace["fallback_reason"] == "RuntimeError"


def test_without_fallback_the_error_surfaces_and_after_speaking_too(api, admin, monkeypatch):
    external = External(error=RuntimeError("boom"))
    cid, _ = setup_agent(api, admin, monkeypatch, external, fallback=False, from_turn=1)
    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(api.engine.process_turn(cid, "hola"))

    # Con fallback, pero el proveedor ya habia empezado a hablar: no se repite la frase con el otro.
    class Spoke(External):
        async def converse(self, workflow, state, user_message, on_message=None):
            on_message("Hola, ")
            raise RuntimeError("cortado")

    api.llm.turns = [turn("no deberia sonar")]
    cid2, _ = setup_agent_again(api, admin, monkeypatch, Spoke())
    heard = []
    with pytest.raises(RuntimeError, match="cortado"):
        asyncio.run(api.engine.process_turn(cid2, "hola", on_message=heard.append))
    assert heard == ["Hola, "]


def setup_agent_again(api, admin, monkeypatch, external):
    other = make_client(admin, "segundo")
    conn = new_connection(admin, other)
    plan = {"stages": [{"from_turn": 1, "connection": conn["id"], "model": "m"}], "fallback_local": True}
    agent = agent_with_plan(admin, other, plan).json()
    monkeypatch.setattr(LLMResolver, "_client", lambda self, data, stage, generation, defaults: external)
    state, _ = api.engine.start_conversation(agent["id"], other["id"])
    return state.conversation_id, other


def test_breaker_skips_a_failing_provider(api, admin, monkeypatch):
    external = External(error=RuntimeError("caido"))
    api.llm.turns = [turn(f"local {i}") for i in range(BREAKER_FAILS + 2)]
    cid, _ = setup_agent(api, admin, monkeypatch, external, from_turn=1)
    calls = []
    original = external.converse

    async def counting(*a, **kw):
        calls.append(1)
        return await original(*a, **kw)
    external.converse = counting

    async def run():
        for i in range(BREAKER_FAILS + 2):
            await api.engine.process_turn(cid, f"m{i}")
            await api.engine.wait_extraction(cid)
    asyncio.run(run())
    # Los errores de turno y de extraccion suman al mismo circuito: abierto, va directo al propio.
    assert 0 < len(calls) < BREAKER_FAILS + 2
    trace = api.engine.store.get(cid).messages[-1].llm[0]
    assert trace["fallback_reason"] == "circuito abierto"


def test_revoked_connection_falls_back_instead_of_breaking(api, admin, monkeypatch):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    plan = {"stages": [{"from_turn": 1, "connection": conn["id"], "model": "m"}]}
    agent = agent_with_plan(admin, acme, plan).json()
    assert admin.delete(f"{V1}/clients/{acme['id']}/llm-connections/{conn['id']}").status_code == 204
    state, _ = api.engine.start_conversation(agent["id"], acme["id"])
    api.llm.turns = [turn("local")]
    _, result = asyncio.run(api.engine.process_turn(state.conversation_id, "hola"))
    assert result.assistant_message == "local"
    # Y no se puede guardar una version nueva que la use.
    r = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": agent["definition"]})
    assert r.status_code == 422


def test_connection_of_another_client_is_not_used_at_runtime(api, admin, monkeypatch):
    """Defensa en profundidad: una definicion guardada con el id de otro cliente no lo usa."""
    acme, other = make_client(admin, "acme"), make_client(admin, "otro")
    foreign = new_connection(admin, other)
    agent = make_agent(admin, acme)
    from app.models import Agent, AgentVersion
    with api.sessions() as s:
        row = s.get(Agent, agent["id"])
        row.definition = {**row.definition, "llm": {"stages": [{"from_turn": 1, "connection": foreign["id"],
                                                                 "model": "m"}], "fallback_local": True}}
        v = s.get(AgentVersion, (agent["id"], row.version))
        v.definition = row.definition
        s.commit()
    api.engine.definitions._cache.clear()
    called = []
    monkeypatch.setattr(LLMResolver, "_client", lambda self, data, stage, generation, defaults: called.append(1))
    state, _ = api.engine.start_conversation(agent["id"], acme["id"])
    api.llm.turns = [turn("local")]
    _, result = asyncio.run(api.engine.process_turn(state.conversation_id, "hola"))
    assert result.assistant_message == "local" and called == []


# --- Cliente OpenAI compatible ---------------------------------------------------------------

def test_generic_profile_sends_no_vllm_extras_and_always_guides_with_json_schema():
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    strict = LLMClient("https://api.openai.com/v1", "k", "gpt", profile="openai_compatible",
                       generation=Generation(params={"temperature": 0.3}))
    assert strict.options == {"temperature": 0.3} and strict._tokens_param == "max_completion_tokens"
    extra = strict._guided("x", schema)
    assert extra["response_format"]["type"] == "json_schema"
    assert extra["response_format"]["json_schema"]["strict"] is True
    other = LLMClient("https://x.example/v1", "k", "m", profile="openrouter")
    assert other.options == {} and other._tokens_param == "max_tokens"

    local = LLMClient("http://vllm-llm:8000/v1", "k", "gemma-x")
    assert "extra_body" in local.options and local.label == "local"
    assert "extra_body" not in strict.options


def test_connection_without_guided_json_is_rejected(api, admin, monkeypatch):
    """La prueba de la conexion solo acepta json_schema: un 400 del proveedor la deja en error."""
    import httpx
    import openai

    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)

    async def structured(self, *a, **kw):
        request = httpx.Request("POST", "https://x.example/v1/chat/completions")
        raise openai.BadRequestError("response_format json_schema not supported",
                                     response=httpx.Response(400, request=request), body=None)
    monkeypatch.setattr(LLMClient, "structured", structured)
    out = admin.post(f"{V1}/clients/{acme['id']}/llm-connections/{conn['id']}/test", json={}).json()
    assert out["last_test_ok"] is False and "json_schema" in out["last_test_detail"]
