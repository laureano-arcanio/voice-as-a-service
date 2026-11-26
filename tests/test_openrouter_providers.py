"""Endpoint del catalogo de proveedores de OpenRouter (GET /api/v1/llm/openrouter-providers,
docs/features/LLM_CONEXIONES.md): los tags que van en `provider.only` de una etapa. Sin red real:
httpx.MockTransport intercepta el pedido a openrouter.ai."""
import asyncio

import httpx
import pytest

from app.llm import openrouter

from .test_api import V1, admin  # noqa: F401

PATH = f"{V1}/llm/openrouter-providers"


@pytest.fixture(autouse=True)
def cache_limpia():
    """El catalogo cachea 5 min por modelo en memoria (y los 404): cada test arranca y termina sin entradas."""
    openrouter._catalog.clear()
    openrouter._missing.clear()
    yield
    openrouter._catalog.clear()
    openrouter._missing.clear()


def mock_openrouter(monkeypatch, handler):
    """provider_catalog arma su AsyncClient: se le inyecta el MockTransport (patron de test_demo.py)."""
    real = httpx.AsyncClient
    monkeypatch.setattr(openrouter.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def payload(*endpoints: dict) -> dict:
    """Respuesta de GET /api/v1/models/{model}/endpoints (solo lo que lee el catalogo)."""
    return {"data": {"id": "vendor/model", "endpoints": list(endpoints)}}


# El primero y el segundo son el mismo tag (tiers distintos): dedupe. baseten no declara
# structured_outputs; unknow, nada; el ultimo no tiene tag y va al descarte.
EPS = [
    {"tag": "nebius/fp4", "provider_name": "Nebius", "quantization": "fp4",
     "supported_parameters": ["tools", "structured_outputs", "reasoning"]},
    {"tag": "nebius/fp4", "provider_name": "Nebius", "quantization": "fp4",
     "supported_parameters": ["tools", "structured_outputs"]},
    {"tag": "baseten", "provider_name": "Basent", "quantization": "fp8",
     "supported_parameters": ["tools", "response_format"]},
    {"tag": "unknow/host", "provider_name": "Unknow", "quantization": None,
     "supported_parameters": []},
    {"tag": "", "provider_name": "Sin tag", "supported_parameters": ["tools"]},
]


def test_requiere_sesion(api):
    assert api.client.get(PATH, params={"model": "vendor/model"}).status_code == 401


def test_modelo_invalido_422_sin_pedido(api, admin, monkeypatch):
    """Validacion antes de armar la URL: nada llega a la red (host fijo, sin path traversal ni query)."""
    seen = []
    mock_openrouter(monkeypatch, lambda r: seen.append(r) or httpx.Response(200, json=payload()))
    for bad in ("gpt-4o", "vendor/", "/model", "vendor//model", "../etc/passwd", "a/b?x=1",
                "a/b#frag", "ven dor/model", "%2e%2e/model", "x" * 66 + "/model", "a/b/c"):
        r = admin.get(PATH, params={"model": bad})
        assert r.status_code == 422, bad
        assert r.json()["code"] == "invalid_model"
    assert seen == []


def test_sin_parametro_modelo_422(api, admin):
    assert admin.get(PATH).status_code == 422


def test_devuelve_tags_deduplicados_y_soporte(api, admin, monkeypatch):
    seen = []
    mock_openrouter(monkeypatch, lambda r: seen.append(str(r.url)) or httpx.Response(200, json=payload(*EPS)))
    # Se normaliza (espacios, mayusculas) antes de armar la URL.
    r = admin.get(PATH, params={"model": "  Vendor/Model "})
    assert r.status_code == 200, r.text
    assert seen == ["https://openrouter.ai/api/v1/models/vendor/model/endpoints"]
    # Dedupe por tag y orden por provider_name/tag; response_format no cuenta como json_schema.
    assert r.json() == [
        {"tag": "baseten", "provider_name": "Basent", "quantization": "fp8",
         "supports_json_schema": False, "supports_tools": True},
        {"tag": "nebius/fp4", "provider_name": "Nebius", "quantization": "fp4",
         "supports_json_schema": True, "supports_tools": True},
        {"tag": "unknow/host", "provider_name": "Unknow", "quantization": None,
         "supports_json_schema": False, "supports_tools": False},
    ]


def test_sin_endpoints_lista_vacia(api, admin, monkeypatch):
    mock_openrouter(monkeypatch, lambda r: httpx.Response(200, json=payload()))
    assert admin.get(PATH, params={"model": "vendor/model"}).json() == []


def test_cachea_5_min_por_modelo(api, admin, monkeypatch):
    hits = {"n": 0}

    def handler(r):
        hits["n"] += 1
        return httpx.Response(200, json=payload())

    mock_openrouter(monkeypatch, handler)
    assert admin.get(PATH, params={"model": "vendor/model"}).status_code == 200
    assert admin.get(PATH, params={"model": "vendor/model"}).status_code == 200
    assert hits["n"] == 1                                   # segundo pedido, cache
    assert admin.get(PATH, params={"model": "otro/model"}).status_code == 200
    assert hits["n"] == 2                                   # otro modelo, nuevo pedido


def test_error_de_red_invalid(api, admin, monkeypatch):
    def handler(r):
        raise httpx.ConnectError("sin red", request=r)

    mock_openrouter(monkeypatch, handler)
    r = admin.get(PATH, params={"model": "vendor/model"})
    assert r.status_code == 422
    assert r.json() == {"detail": "No se pudo leer el catalogo de OpenRouter: ConnectError",
                        "code": "catalog_unreachable", "errors": []}


def test_modelo_inexistente_invalid(api, admin, monkeypatch):
    mock_openrouter(monkeypatch, lambda r: httpx.Response(404, json={"error": {"message": "no"}}))
    r = admin.get(PATH, params={"model": "vendor/model"})
    assert r.status_code == 422
    assert r.json() == {"detail": "El modelo 'vendor/model' no existe en OpenRouter",
                        "code": "model_not_found", "errors": []}


def test_el_404_tambien_se_cachea(api, admin, monkeypatch):
    """La validacion del editor pide el catalogo en cada tecla: un modelo inexistente no se vuelve a pedir."""
    hits = {"n": 0}

    def handler(r):
        hits["n"] += 1
        return httpx.Response(404, json={"error": {"message": "no"}})

    mock_openrouter(monkeypatch, handler)
    for _ in range(2):
        assert admin.get(PATH, params={"model": "vendor/model"}).json()["code"] == "model_not_found"
    assert hits["n"] == 1
    # Otro modelo no usa esa cache negativa.
    admin.get(PATH, params={"model": "otro/model"})
    assert hits["n"] == 2


def test_model_status_con_sufijo_prueba_el_slug_base(monkeypatch):
    """Un :free/:nitro da 404 o una lista vacia en endpoints: los proveedores son los del slug base."""
    seen = []

    def handler(r):
        seen.append(str(r.url))
        if str(r.url).endswith(":free/endpoints"):
            return httpx.Response(200, json=payload())
        return httpx.Response(200, json=payload(*EPS))

    mock_openrouter(monkeypatch, handler)
    assert asyncio.run(openrouter.model_status("vendor/model:free")) == "ok"
    assert seen == ["https://openrouter.ai/api/v1/models/vendor/model:free/endpoints",
                    "https://openrouter.ai/api/v1/models/vendor/model/endpoints"]


def test_model_status_sin_sufijo(monkeypatch):
    mock_openrouter(monkeypatch, lambda r: httpx.Response(200, json=payload()))
    assert asyncio.run(openrouter.model_status("vendor/model")) == "no_endpoints"


def test_model_status_inexistente_o_invalido(monkeypatch):
    mock_openrouter(monkeypatch, lambda r: httpx.Response(404, json={"error": {"message": "no"}}))
    assert asyncio.run(openrouter.model_status("otro/model")) == "not_found"
    assert asyncio.run(openrouter.model_status("sin-autor")) == "invalid"   # no llega a la red
