"""Herramientas HTTP del cliente (docs/features/HERRAMIENTAS.md): formato, armado del pedido por metodo, cada
auth, firma, templates, respuesta, tachado de secretos, timeouts, reintentos y SSRF. Contra la API falsa
de scripts/tools/mock_api.py, de verdad (sin mocks de httpx)."""
import base64
import json

import pytest
from pydantic import ValidationError

from app.config import settings
from app.tools import runtime
from app.tools import schema as S
from app.tools.runtime import ToolContext, ToolSpec
from scripts.tools import mock_api

from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)

SECRETS = {"MOCK_TOKEN": mock_api.TOKEN, "MOCK_KEY": mock_api.API_KEY, "MOCK_PASSWORD": mock_api.PASSWORD,
           "MOCK_CLIENT_SECRET": mock_api.CLIENT_SECRET, "ATENTINA_SIGNING_SECRET": mock_api.SIGNING_SECRET}


def http_tool(url: str, **http) -> dict:
    return {"description": "Prueba.", "http": {"url": url, **http}}


def spec(definition: dict, slug: str = "prueba") -> ToolSpec:
    return ToolSpec(slug=slug, type="http", revision=1, tool=S.parse("http", definition))


def ctx(**kw) -> ToolContext:
    return ToolContext(conversation_id="conv-1", channel="voice", mode="entrante", from_="+5491155551234",
                       to="+5493515550000", agent_slug="turnos", secrets=dict(SECRETS), **kw)


TURNOS = {
    "method": "GET",
    "path": {"sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "Sucursal"}},
    "query": {"fecha": {"type": "string", "description": "AAAA-MM-DD", "required": True},
              "origen": {"value": "atentina"}, "tel": {"value": "{{call.from}}"}},
    "headers": {"X-Tenant": "acme", "X-Conversacion": "{{call.id}}"},
    "auth": {"type": "bearer", "secret": "MOCK_TOKEN"},
}


# ---------- formato ----------

def test_llm_sees_only_what_it_fills():
    tool = S.parse("http", http_tool("https://api.acme.com/sucursales/{sucursal}/turnos", **TURNOS))
    params = S.llm_parameters(tool)
    assert set(params["properties"]) == {"sucursal", "fecha"}
    assert params["required"] == ["sucursal", "fecha"]
    assert S.required_secrets(tool) == {"MOCK_TOKEN"}
    assert S.openai_tool("consultar_turnos", tool)["function"]["name"] == "consultar_turnos"


@pytest.mark.parametrize("bad, message", [
    ({"url": "https://a.com/x/{id}"}, "path"),
    ({"url": "https://a.com/x", "path": {"id": {"description": "x"}}}, "path"),
    ({"url": "https://a.com/x", "query": {"q": {}}}, "description"),
    ({"url": "https://a.com/x", "headers": {"Host": "x"}}, "plataforma"),
    ({"url": "https://a.com/x", "headers": {"X-K": "{{secret.X}}"}}, "variable desconocida"),
    ({"url": "https://a.com/x", "headers": {"X-K": "{{call.nombre}}"}}, "call.nombre"),
    ({"url": "https://a.com/x", "method": "GET", "body": {"type": "object", "properties": {}}}, "sin body"),
    ({"url": "https://usr:pw@a.com/x"}, "usuario"),
    ({"url": "https://{{call.id}}.com/x"}, "host"),
    ({"url": "https://a.com/x", "auth": {"type": "bearer"}}, "auth.secret"),
    ({"url": "https://a.com/x", "auth": {"type": "bearer", "secret": "TK"}, "headers": {"Authorization": "x"}},
     "ya lo pone auth"),
    ({"url": "https://a.com/x", "method": "POST", "query": {"n": {"description": "n"}},
      "body": {"type": "object", "properties": {"n": {"type": "string", "description": "n"}}}}, "repetidos"),
])
def test_invalid_definitions(bad, message):
    with pytest.raises(ValidationError, match=message):
        S.parse("http", {"description": "x", "http": bad})


def test_slug_rules():
    assert S.check_slug("consultar_turnos")
    for bad in ("Consultar", "end_call", "a", "con-guion"):
        with pytest.raises(ValueError):
            S.check_slug(bad)


def test_validate_args_against_the_schema():
    tool = S.parse("http", http_tool("https://a.com/s/{sucursal}", **TURNOS))
    assert S.validate_args(tool, {"sucursal": "centro", "fecha": "2026-11-05"}) is None
    assert "enum" in S.validate_args(tool, {"sucursal": "sur", "fecha": "x"}) or \
        "is not one of" in S.validate_args(tool, {"sucursal": "sur", "fecha": "x"})
    assert "fecha" in S.validate_args(tool, {"sucursal": "centro"})


# ---------- pedido real contra la API falsa ----------

async def test_get_with_path_query_headers_and_bearer(mock_api_url):
    s = spec(http_tool(mock_api_url + "/sucursales/{sucursal}/turnos", **TURNOS))
    result = await runtime.run(s, {"sucursal": "centro", "fecha": "2026-11-05"}, ctx(), "call-1")
    assert result.ok and result.status == 200
    assert result.data["turnos"] == ["10:00", "11:30", "16:00"]
    got = mock_api.RECEIVED[-1]
    assert got["query"] == {"fecha": "2026-11-05", "origen": "atentina", "tel": "+5491155551234"}
    assert got["headers"]["x-tenant"] == "acme" and got["headers"]["x-conversacion"] == "conv-1"
    assert got["headers"]["x-atentina-conversation-id"] == "conv-1" and got["headers"]["x-atentina-tool"] == "prueba"
    assert "idempotency-key" not in got["headers"]           # GET no la lleva
    # El token no aparece en lo que ve el modelo ni en el pedido guardado.
    assert mock_api.TOKEN not in result.llm and mock_api.TOKEN not in json.dumps(result.request)
    assert "[secreto:MOCK_TOKEN]" in result.request["headers"]["Authorization"]


async def test_post_json_with_fixed_values_signature_and_idempotency(mock_api_url):
    s = spec(http_tool(mock_api_url + "/reservas", method="POST", sign=True,
                       auth={"type": "bearer", "secret": "MOCK_TOKEN"},
                       body={"type": "object", "required": ["fecha", "hora", "nombre"], "properties": {
                           "sucursal": {"type": "string", "value": "centro"},
                           "fecha": {"type": "string", "description": "AAAA-MM-DD"},
                           "hora": {"type": "string", "description": "HH:MM"},
                           "nombre": {"type": "string", "description": "Nombre"},
                           "canal": {"type": "string", "value": "{{call.channel}}"}}}))
    result = await runtime.run(s, {"fecha": "2026-11-05", "hora": "11:30", "nombre": "Ana"}, ctx(), "call-7")
    assert result.ok, result
    got = mock_api.RECEIVED[-1]
    assert got["signature_ok"] is True
    assert got["headers"]["idempotency-key"] == "conv-1:call-7"
    assert json.loads(got["body"]) == {"sucursal": "centro", "fecha": "2026-11-05", "hora": "11:30",
                                       "nombre": "Ana", "canal": "voice"}
    assert result.data["estado"] == "confirmada"


async def test_the_llm_cannot_override_a_fixed_value(mock_api_url):
    s = spec(http_tool(mock_api_url + "/reservas", method="POST", auth={"type": "bearer", "secret": "MOCK_TOKEN"},
                       body={"type": "object", "properties": {
                           "sucursal": {"type": "string", "value": "centro"},
                           "fecha": {"type": "string", "description": "f"}, "hora": {"type": "string", "description": "h"},
                           "nombre": {"type": "string", "description": "n"}}}))
    # sucursal no esta en el esquema del modelo: si la manda igual, no se usa (y el esquema no la rechaza).
    await runtime.run(s, {"sucursal": "norte", "fecha": "2026-11-05", "hora": "10:00", "nombre": "x"}, ctx())
    assert json.loads(mock_api.RECEIVED[-1]["body"])["sucursal"] == "centro"


async def test_form_body(mock_api_url):
    s = spec(http_tool(mock_api_url + "/form", method="POST", content_type="application/x-www-form-urlencoded",
                       auth={"type": "bearer", "secret": "MOCK_TOKEN"},
                       body={"type": "object", "properties": {"nombre": {"type": "string", "description": "n"},
                                                              "fijo": {"value": "si"}}}))
    result = await runtime.run(s, {"nombre": "Ana Gómez"}, ctx())
    assert result.ok and result.data == {"recibido": {"nombre": "Ana Gómez", "fijo": "si"}}


@pytest.mark.parametrize("auth", [{"type": "api_key", "secret": "MOCK_KEY", "name": "X-API-Key"},
                                  {"type": "api_key", "secret": "MOCK_KEY", "name": "key", "in": "query"}])
async def test_api_key_in_header_or_query(mock_api_url, auth):
    s = spec(http_tool(mock_api_url + "/deudores", auth=auth,
                       query={"dni": {"type": "string", "description": "DNI", "required": True}}))
    result = await runtime.run(s, {"dni": "30111222"}, ctx())
    assert result.ok and result.data["cliente"]["nombre"] == "Ana Gómez"
    assert mock_api.API_KEY not in json.dumps(result.request)


async def test_basic_auth(mock_api_url):
    s = spec(http_tool(mock_api_url + "/basic", auth={"type": "basic", "username": "atentina", "secret": "MOCK_PASSWORD"}))
    result = await runtime.run(s, {}, ctx())
    assert result.ok
    encoded = base64.b64encode(f"atentina:{mock_api.PASSWORD}".encode()).decode()
    assert encoded not in json.dumps(result.request)          # tachado tambien en base64


@pytest.mark.parametrize("client_auth", ["body", "basic"])
async def test_oauth2_client_credentials_caches_the_token(mock_api_url, client_auth):
    runtime._TOKENS.clear()
    s = spec(http_tool(mock_api_url + "/oauth/recurso", auth={
        "type": "oauth2_client_credentials", "token_url": mock_api_url + "/oauth/token",
        "client_id": "mock-client", "secret": "MOCK_CLIENT_SECRET", "client_auth": client_auth}))
    assert (await runtime.run(s, {}, ctx())).ok
    assert (await runtime.run(s, {}, ctx())).ok
    paths = [r["path"] for r in mock_api.RECEIVED]
    assert paths.count("/oauth/token") == 1 and paths.count("/oauth/recurso") == 2


async def test_oauth2_retries_once_with_a_new_token_on_401(mock_api_url):
    runtime._TOKENS.clear()
    s = spec(http_tool(mock_api_url + "/oauth/recurso", auth={
        "type": "oauth2_client_credentials", "token_url": mock_api_url + "/oauth/token",
        "client_id": "mock-client", "secret": "MOCK_CLIENT_SECRET"}))
    assert (await runtime.run(s, {}, ctx())).ok
    mock_api._oauth_tokens.clear()                            # el servidor invalido el token
    assert (await runtime.run(s, {}, ctx())).ok


async def test_error_status_goes_to_the_llm_clipped(mock_api_url):
    s = spec(http_tool(mock_api_url + "/sucursales/{sucursal}/turnos", **{**TURNOS, "path": {
        "sucursal": {"type": "string", "description": "s"}}}))
    result = await runtime.run(s, {"sucursal": "sur", "fecha": "2026-11-05"}, ctx())
    assert not result.ok and result.status == 404
    assert json.loads(result.llm) == {"ok": False, "status": 404, "error": '{"detail": "No existe la sucursal sur"}'}


async def test_pick_and_assign(mock_api_url):
    definition = http_tool(mock_api_url + "/sucursales/{sucursal}/turnos", **TURNOS)
    definition |= {"response": {"pick": ["turnos[0]", "sucursal.nombre"]},
                   "assign": [{"var": "sucursal_id", "path": "sucursal.id"}]}
    c = ctx()
    result = await runtime.run(spec(definition), {"sucursal": "norte", "fecha": "2026-11-05"}, c)
    assert json.loads(result.llm)["data"] == {"turnos[0]": "15:00", "sucursal.nombre": "Sucursal Norte"}
    assert c.vars == {"sucursal_id": "norte"} and result.assigned == {"sucursal_id": "norte"}


async def test_secret_echoed_by_the_api_is_redacted(mock_api_url):
    s = spec(http_tool(mock_api_url + "/eco", auth={"type": "bearer", "secret": "MOCK_TOKEN"},
                       headers={"X-Otra": "{{secrets.MOCK_KEY}}"}))
    result = await runtime.run(s, {}, ctx())
    assert result.ok
    assert mock_api.TOKEN not in result.llm and mock_api.API_KEY not in result.llm
    assert "[secreto:MOCK_KEY]" in result.llm


async def test_missing_secret_does_not_call(mock_api_url):
    s = spec(http_tool(mock_api_url + "/eco", auth={"type": "bearer", "secret": "NO_ESTA"}))
    result = await runtime.run(s, {}, ctx())
    assert not result.ok and "NO_ESTA" in result.error and mock_api.RECEIVED == []


async def test_invalid_args_do_not_call(mock_api_url):
    s = spec(http_tool(mock_api_url + "/sucursales/{sucursal}/turnos", **TURNOS))
    result = await runtime.run(s, {"sucursal": "sur"}, ctx())
    assert not result.ok and "argumentos inválidos" in result.error and mock_api.RECEIVED == []


async def test_timeout(mock_api_url):
    s = spec(http_tool(mock_api_url + "/lento", timeout_ms=500, query={"segundos": {"value": 2}}))
    result = await runtime.run(s, {}, ctx())
    assert not result.ok and result.error == "timeout" and result.ms < 1500


async def test_retries_only_when_configured(mock_api_url):
    once = spec(http_tool(mock_api_url + "/falla", query={"clave": {"value": "a"}, "veces": {"value": 1}}))
    assert (await runtime.run(once, {}, ctx())).status == 503
    twice = spec(http_tool(mock_api_url + "/falla", retries=1, query={"clave": {"value": "b"}, "veces": {"value": 1}}))
    result = await runtime.run(twice, {}, ctx())
    assert result.ok and result.data["intentos"] == 2


async def test_redirects_are_not_followed(mock_api_url):
    result = await runtime.run(spec(http_tool(mock_api_url + "/redirige")), {}, ctx())
    assert not result.ok and result.status == 302


# ---------- SSRF ----------

@pytest.mark.parametrize("url", ["https://127.0.0.1/x", "https://localhost/x", "https://169.254.169.254/latest",
                                 "https://10.0.0.5/x", "https://[::1]/x"])
async def test_private_addresses_are_blocked(url, monkeypatch):
    monkeypatch.setattr(runtime, "PRIVATE_HOSTS", set())
    result = await runtime.run(spec(http_tool(url)), {}, ctx())
    assert not result.ok and "privada" in result.error


async def test_http_is_only_for_private_hosts(monkeypatch):
    monkeypatch.setattr(runtime, "PRIVATE_HOSTS", set())
    result = await runtime.run(spec(http_tool("http://example.com/x")), {}, ctx())
    assert not result.ok and "https" in result.error


def test_sign_format():
    header = runtime.sign("s3cr3t", b'{"a":1}', now=1700000000)
    assert header == "t=1700000000,v1=" + __import__("hmac").new(
        b"s3cr3t", b'1700000000.{"a":1}', "sha256").hexdigest()
