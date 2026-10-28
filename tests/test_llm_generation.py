"""Parametros de generacion por agente y etapa (docs/features/LLM_CONEXIONES.md, app/llm/params.py):
catalogo, validacion, defaults de la plataforma y traduccion por proveedor."""
import pytest
from pydantic import ValidationError

from app.agents.templates import reference_data
from app.config import settings
from app.conversation.models import Generation, LlmPlan, LlmStage, Workflow
from app.llm.anthropic_client import AnthropicClient
from app.llm.client import LLMClient
from app.llm.params import for_provider, validate_params
from app.llm.resolver import LLMResolver, effective_generation, platform_defaults

from .test_api import V1, admin, make_client  # noqa: F401

WORKFLOW = "sales_discovery"


def workflow(*, generation=None, llm=None) -> Workflow:
    data = reference_data(WORKFLOW)
    return Workflow.model_validate({**data, **({"generation": generation} if generation else {}),
                                    **({"llm": llm} if llm else {})})


# --- Catalogo y validacion -------------------------------------------------------------------

def test_catalog_by_provider():
    vllm = {p.name for p in for_provider("vllm")}
    openai = {p.name for p in for_provider("openai_compatible")}
    anthropic = {p.name for p in for_provider("anthropic")}
    assert {"temperature", "top_p", "top_k", "min_p", "max_tokens", "enable_thinking",
            "thinking_token_budget"} <= vllm
    assert {"temperature", "top_p", "max_tokens", "reasoning_effort"} == openai
    assert {"temperature", "top_p", "max_tokens", "effort"} == anthropic
    assert "top_k" not in openai and "effort" not in vllm


def test_validation_of_params():
    assert validate_params({"temperature": 0.5, "top_p": 0.9, "enable_thinking": True,
                            "effort": "high", "max_tokens": 100}) == {
        "temperature": 0.5, "top_p": 0.9, "enable_thinking": True, "effort": "high", "max_tokens": 100}
    assert validate_params({"temperature": None}) == {}          # None = default del proveedor
    with pytest.raises(ValidationError, match="temperature"):
        Generation(params={"temperature": 3})                    # fuera de rango
    with pytest.raises(ValidationError, match="top_p"):
        Generation(params={"top_p": 2})
    with pytest.raises(ValidationError, match="desconocido"):
        Generation(params={"nope": 1})
    with pytest.raises(ValidationError, match="effort"):
        Generation(params={"effort": "enorme"})                  # no es una opcion
    with pytest.raises(ValidationError, match="entero"):
        Generation(params={"max_tokens": 1.5})


def test_stage_folds_deprecated_temperature_and_allows_local_generation():
    # temperature suelta (viejo) se pliega en generation.temperature.
    st = LlmStage(from_turn=1, connection="c", model="m", temperature=0.3)
    assert st.generation.params == {"temperature": 0.3} and st.temperature is None
    # Una etapa local (sin conexion) puede pisar la generacion del agente.
    local = LlmStage(from_turn=3, generation={"params": {"temperature": 0.1}})
    assert local.connection is None and local.generation.params == {"temperature": 0.1}
    # model sigue necesitando conexion.
    with pytest.raises(ValidationError, match="solo vale"):
        LlmStage(from_turn=1, model="m")


# --- Defaults y merge ------------------------------------------------------------------------

def test_platform_defaults_and_effective_generation(monkeypatch):
    monkeypatch.setattr(settings, "llm_thinking", False)
    monkeypatch.setattr(settings, "llm_thinking_budget", 77)
    assert platform_defaults() == {"thinking": False, "thinking_budget": 77, "max_tokens": None}

    wf = workflow(generation={"params": {"temperature": 0.25, "top_p": 0.5}},
                  llm={"stages": [{"from_turn": 1},
                                  {"from_turn": 3, "generation": {"params": {"temperature": 0.9}}}]})
    plan = wf.llm
    assert effective_generation(wf, plan.stage_for(1)) == {"temperature": 0.25, "top_p": 0.5}
    # La etapa 3 pisa temperature y conserva lo del agente (top_p).
    assert effective_generation(wf, plan.stage_for(3)) == {"temperature": 0.9, "top_p": 0.5}


# --- Cliente local (vLLM) --------------------------------------------------------------------

def test_local_client_applies_generation(monkeypatch):
    monkeypatch.setattr(settings, "llm_temperature", 0.7)
    gen = Generation(params={"temperature": 0.2, "top_p": 0.5, "top_k": 5, "min_p": 0.1,
                             "enable_thinking": True, "thinking_token_budget": 300, "max_tokens": 123})
    c = LLMClient("http://vllm-llm:8000/v1", "k", "cyankiwi/gemma-4-26B-A4B", generation=gen)
    assert c.options["temperature"] == 0.2 and c.options["top_p"] == 0.5
    assert c.options["extra_body"]["top_k"] == 5 and c.options["extra_body"]["min_p"] == 0.1
    assert c.options["extra_body"]["chat_template_kwargs"] == {"enable_thinking": True}
    assert c.options["extra_body"]["thinking_token_budget"] == 300
    assert c._limit() == {"max_tokens": 123}


def test_local_client_without_generation_uses_the_configured_sampling(monkeypatch):
    """El muestreo sale de la configuracion (LLM_TEMPERATURE, ...), no del nombre del modelo; lo no definido no
    se manda."""
    for name, value in (("llm_temperature", 1.0), ("llm_top_p", 0.95), ("llm_top_k", 64), ("llm_min_p", None)):
        monkeypatch.setattr(settings, name, value)
    c = LLMClient("http://vllm-llm:8000/v1", "k", "cualquier/modelo", thinking=False)
    assert (c.options["temperature"], c.options["top_p"], c.options["extra_body"]["top_k"]) == (1.0, 0.95, 64)
    assert "min_p" not in c.options["extra_body"]
    assert c.options["extra_body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert c._limit() == {}
    for name in ("llm_temperature", "llm_top_p", "llm_top_k"):
        monkeypatch.setattr(settings, name, None)
    bare = LLMClient("http://vllm-llm:8000/v1", "k", "m", thinking=False)
    assert bare.options == {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}


# --- Proveedores externos --------------------------------------------------------------------

def test_generic_client_drops_unsupported_and_maps_max_tokens():
    gen = Generation(params={"temperature": 0.2, "top_p": 0.5, "top_k": 5, "enable_thinking": False,
                             "reasoning_effort": "high", "max_tokens": 100})
    c = LLMClient("https://api.openai.com/v1", "k", "gpt", profile="openai_compatible", generation=gen)
    assert c.options == {"temperature": 0.2, "top_p": 0.5, "reasoning_effort": "high"}   # sin top_k/enable_thinking
    assert c._limit() == {"max_completion_tokens": 100}
    other = LLMClient("https://x.example/v1", "k", "m", profile="openrouter", generation=gen)
    assert other._limit() == {"max_tokens": 100}


def test_anthropic_client_generation():
    gen = Generation(params={"temperature": 0.4, "top_p": 0.8, "effort": "high", "max_tokens": 4096})
    # 4-6: acepta effort y todavia acepta temperature/top_p.
    params = AnthropicClient("sk", "claude-haiku-4-6", generation=gen)._params(
        [{"role": "user", "content": "x"}], None)
    assert params["temperature"] == 0.4 and params["top_p"] == 0.8
    assert params["output_config"]["effort"] == "high" and params["max_tokens"] == 4096

    # Los modelos que rechazan temperature/top_p: se descartan, el effort queda.
    newer = AnthropicClient("sk", "claude-haiku-4-7", generation=gen)._params(
        [{"role": "user", "content": "x"}], None)
    assert "temperature" not in newer and "top_p" not in newer and newer["output_config"]["effort"] == "high"

    # Piso de max_tokens para el razonamiento adaptativo.
    floor = AnthropicClient("sk", "claude-haiku-4-5", generation=Generation(params={"max_tokens": 100}))._params(
        [{"role": "user", "content": "x"}], None)
    assert floor["max_tokens"] == 2048


# --- Resolver --------------------------------------------------------------------------------

def test_resolver_builds_and_caches_local_clients(monkeypatch):
    monkeypatch.setattr(settings, "llm_temperature", None)
    wf = workflow(generation={"params": {"temperature": 0.25}},
                  llm={"stages": [{"from_turn": 1},
                                  {"from_turn": 3, "generation": {"params": {"temperature": 0.9}}}]})
    resolver = LLMResolver(LLMClient("http://vllm-llm:8000/v1", "k", "cyankiwi/gemma-4"), sessions=None)
    first = resolver.for_turn(wf, 1, None)
    assert first.options["temperature"] == 0.25
    assert resolver.for_turn(wf, 1, None) is first          # cacheado
    assert resolver.for_turn(wf, 3, None).options["temperature"] == 0.9


# --- API -------------------------------------------------------------------------------------

def test_llm_params_endpoint(api, admin):  # noqa: F811
    out = admin.get(f"{V1}/llm/params").json()
    assert "local_family" not in out
    kinds = {p["kind"] for p in out["providers"]}
    assert kinds == {"vllm", "openai_compatible", "openrouter", "anthropic"}
    vllm = {q["name"] for p in out["providers"] if p["kind"] == "vllm" for q in p["params"]}
    assert {"temperature", "top_p", "top_k", "min_p", "max_tokens", "enable_thinking",
            "thinking_token_budget"} <= vllm
    defaults = out["local_defaults"]
    assert defaults["enable_thinking"] == settings.llm_thinking
    assert defaults["thinking_token_budget"] == settings.llm_thinking_budget
    assert "classic" not in defaults and "assistant" not in defaults


def test_agent_accepts_generation_and_rejects_bad_params(api, admin):  # noqa: F811
    acme = make_client(admin, "gen")
    definition = {**reference_data(WORKFLOW),
                  "generation": {"params": {"temperature": 0.5, "enable_thinking": True}}}
    r = admin.post(f"{V1}/agents", json={"client_id": acme["id"], "name": "Gen", "definition": definition})
    assert r.status_code == 201, r.text
    assert r.json()["definition"]["generation"]["params"] == {"temperature": 0.5, "enable_thinking": True}

    bad = {**reference_data(WORKFLOW), "generation": {"params": {"temperature": 9}}}
    r2 = admin.post(f"{V1}/agents", json={"client_id": acme["id"], "name": "Bad", "definition": bad})
    assert r2.status_code == 422 and r2.json()["code"] == "invalid_definition"
