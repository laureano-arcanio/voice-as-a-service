"""Cliente de la Graph API de WhatsApp, con httpx.MockTransport (sin red)."""

import json

import httpx
import pytest

from app.whatsapp.graph import GraphClient, GraphError

TOKEN = "EAAB-token-secreto-123"
PID = "1234567890"


def make(handler):
    seen = []

    def wrapper(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(wrapper))
    return GraphClient(TOKEN, "v25.0", http=http), seen


def ok(_):
    return httpx.Response(200, json={"success": True})


async def test_send_text():
    c, seen = make(ok)
    await c.send_text(PID, "5493515550000", "hola")
    r = seen[0]
    assert r.method == "POST"
    assert str(r.url) == f"https://graph.facebook.com/v25.0/{PID}/messages"
    assert r.headers["authorization"] == f"Bearer {TOKEN}"
    assert json.loads(r.content) == {
        "messaging_product": "whatsapp", "to": "5493515550000",
        "type": "text", "text": {"body": "hola"},
    }


async def test_send_template_con_y_sin_params():
    c, seen = make(ok)
    await c.send_template(PID, "54351", "recordatorio", "es_AR", ["Ana", "10:00"])
    assert json.loads(seen[0].content)["template"] == {
        "name": "recordatorio", "language": {"code": "es_AR"},
        "components": [{"type": "body", "parameters": [
            {"type": "text", "text": "Ana"}, {"type": "text", "text": "10:00"}]}],
    }
    await c.send_template(PID, "54351", "hola", "es")
    body = json.loads(seen[1].content)
    assert body["type"] == "template"
    assert "components" not in body["template"]


async def test_mark_read():
    c, seen = make(ok)
    await c.mark_read(PID, "wamid.XYZ")
    assert json.loads(seen[0].content) == {
        "messaging_product": "whatsapp", "status": "read", "message_id": "wamid.XYZ"}


async def test_request_code_y_verify_code():
    c, seen = make(ok)
    await c.request_code(PID, "voice")
    assert seen[0].url.path == f"/v25.0/{PID}/request_code"
    assert json.loads(seen[0].content) == {"code_method": "VOICE", "language": "es"}
    await c.request_code(PID, "SMS", "en_US")
    assert json.loads(seen[1].content) == {"code_method": "SMS", "language": "en_US"}
    await c.verify_code(PID, "123456")
    assert seen[2].url.path == f"/v25.0/{PID}/verify_code"
    assert json.loads(seen[2].content) == {"code": "123456"}
    with pytest.raises(ValueError):
        await c.request_code(PID, "EMAIL")


async def test_register_valida_pin():
    c, seen = make(ok)
    await c.register(PID, "123456")
    assert seen[0].url.path == f"/v25.0/{PID}/register"
    assert json.loads(seen[0].content) == {"messaging_product": "whatsapp", "pin": "123456"}
    for bad in ("12345", "1234567", "12345a", ""):
        with pytest.raises(ValueError):
            await c.register(PID, bad)
    assert len(seen) == 1


async def test_error_de_meta():
    def err(_):
        return httpx.Response(400, json={"error": {
            "message": f"Invalid OAuth {TOKEN}", "code": 190, "error_subcode": 463}})

    c, _ = make(err)
    with pytest.raises(GraphError) as ei:
        await c.send_text(PID, "54351", "x")
    e = ei.value
    assert (e.code, e.subcode, e.status) == (190, 463, 400)
    assert "Invalid OAuth" in e.message


async def test_respuesta_no_json_y_error_de_red_sin_token():
    c, _ = make(lambda _: httpx.Response(502, text="bad gateway"))
    with pytest.raises(GraphError) as ei:
        await c.send_text(PID, "54351", "x")
    assert ei.value.status == 502
    assert TOKEN not in str(ei.value)

    def boom(request):
        raise httpx.ConnectError("fallo", request=request)

    c, _ = make(boom)
    with pytest.raises(GraphError) as ei:
        await c.send_text(PID, "54351", "x")
    assert TOKEN not in str(ei.value) and TOKEN not in repr(ei.value)
    assert TOKEN not in repr(c)
