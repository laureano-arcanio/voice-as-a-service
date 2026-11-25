"""Enrutado a proveedores de OpenRouter por etapa del agente (docs/features/LLM_CONEXIONES.md, "Modelo
de datos"): OpenRouterProvider en LlmStage, validacion al guardar (solo conexiones openrouter) y
provider_body (el dict que va al pedido)."""
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.agents.templates import reference_data
from app.config import settings
from app.conversation.models import LlmPlan, LlmStage
from app.llm.openrouter import OpenRouterProvider, provider_body

from .test_api import V1, admin, make_client  # noqa: F401


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def new_connection(admin, client, kind="openrouter", name="Mi OpenRouter", **extra):
    body = {"name": name, "kind": kind, "api_key": "sk-or-v1-abcdef1234", "default_model": "vendor/model",
            **({"base_url": "https://8.8.8.8/v1"} if kind == "openai_compatible" else {}), **extra}
    r = admin.post(f"{V1}/clients/{client['id']}/llm-connections", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def agent_with_plan(admin, client, plan):
    definition = {**reference_data("sales_discovery"), "llm": plan}
    return admin.post(f"{V1}/agents", json={"client_id": client["id"], "name": "Ventas", "definition": definition})


# --- Modelo ---------------------------------------------------------------------------------

def test_valid_tags_with_zero_to_three_slashes():
    """Regresion del patron: baseten (0 barras), openai/flex (1), deepinfra/fp8/priority (2),
    google-vertex/global/priority (2) y el extremo de 3 barras."""
    provider = OpenRouterProvider(
        only=["baseten", "openai/flex", "deepinfra/fp8/priority", "google-vertex/global/priority",
              "a/b/c/d"])
    assert provider.only == ["baseten", "openai/flex", "deepinfra/fp8/priority",
                             "google-vertex/global/priority", "a/b/c/d"]


def test_tags_are_normalized_dedupe_preserving_order():
    provider = OpenRouterProvider(only=[" Nebius/Fp4 ", "nebius/fp4", "NEBIUS/FP4", "baseten"])
    assert provider.only == ["nebius/fp4", "baseten"]
    assert OpenRouterProvider(only=["a" * 10]).only == ["a" * 10]


def test_invalid_tags_are_a_model_error():
    for bad in ("", "  ", "/flex", "flex/", "openai//flex", "-flex", "open ai", "a" * 65, "a/b/c/d/e"):
        with pytest.raises(ValidationError, match="no es un tag de proveedor"):
            OpenRouterProvider(only=[bad])


def test_more_than_ten_tags_are_a_model_error():
    with pytest.raises(ValidationError):
        OpenRouterProvider(only=[f"prov-{i}" for i in range(11)])


def test_empty_only_normalizes_provider_to_none():
    """only vacio no se guarda: la etapa queda sin provider, no con un objeto sin tags."""
    for empty in ({"only": []}, {"allow_fallbacks": False}, {"only": [], "require_parameters": False}):
        stage = LlmStage(from_turn=1, connection="c1", model="m", provider=empty)
        assert stage.provider is None


def test_provider_without_connection_is_a_model_error():
    with pytest.raises(ValidationError, match="provider"):
        LlmStage(from_turn=1, provider={"only": ["baseten"]})


def test_old_definitions_without_provider_stay_valid():
    """Definiciones viejas sin provider siguen validas; provider no aparece en el dump."""
    plan = LlmPlan(stages=[LlmStage(from_turn=1),
                           LlmStage(from_turn=4, connection="c1", model="m")])
    assert all(st.provider is None for st in plan.stages)
    assert all("provider" not in st.model_dump(exclude_none=True) for st in plan.stages)


def test_provider_body_is_none_without_tags():
    assert provider_body(None) is None
    assert provider_body(OpenRouterProvider(only=[])) is None
    assert provider_body(OpenRouterProvider()) is None
    body = provider_body(OpenRouterProvider(only=["nebius/fp4"], allow_fallbacks=False))
    assert body == {"only": ["nebius/fp4"], "allow_fallbacks": False, "require_parameters": True}


# --- Guardado del agente ---------------------------------------------------------------------

def test_provider_with_non_openrouter_connection_is_rejected(api, admin):
    acme = make_client(admin, "acme")
    compat = new_connection(admin, acme, kind="openai_compatible", name="Compatible")
    plan = {"stages": [{"from_turn": 1, "connection": compat["id"], "model": "m",
                        "provider": {"only": ["baseten"]}}]}
    r = agent_with_plan(admin, acme, plan)
    assert r.status_code == 422, r.text
    assert r.json()["errors"] == [{"path": "llm.stages.0.provider",
                                   "message": "El enrutado de proveedores es solo para conexiones OpenRouter"}]
    # Con una conexion openrouter, el mismo plan pasa (los tags no se validan contra la API al guardar).
    orconn = new_connection(admin, acme, name="OpenRouter")
    plan["stages"][0]["connection"] = orconn["id"]
    assert agent_with_plan(admin, acme, plan).status_code == 201


def test_valid_tags_persist_normalized(api, admin):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    plan = {"stages": [{"from_turn": 1, "connection": conn["id"], "model": "vendor/model",
                        "provider": {"only": ["Nebius/Fp4", "nebius/fp4", " deepinfra/fp8/priority "],
                                     "allow_fallbacks": False}}],
            "fallback_local": False}
    r = agent_with_plan(admin, acme, plan)
    assert r.status_code == 201, r.text
    stage = r.json()["definition"]["llm"]["stages"][0]
    # El guardado normaliza (strip, minusculas, dedupe) y require_parameters default True.
    assert stage["provider"] == {"only": ["nebius/fp4", "deepinfra/fp8/priority"],
                                "allow_fallbacks": False, "require_parameters": True}


def test_old_plan_without_provider_still_saves(api, admin):
    acme = make_client(admin, "acme")
    conn = new_connection(admin, acme)
    plan = {"stages": [{"from_turn": 1}, {"from_turn": 3, "connection": conn["id"], "model": "m"}]}
    r = agent_with_plan(admin, acme, plan)
    assert r.status_code == 201, r.text
    assert "provider" not in r.json()["definition"]["llm"]["stages"][1]
