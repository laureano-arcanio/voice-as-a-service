import hashlib
import hmac
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

SECRET = "app-secret-de-prueba"
TOKEN = "verify-de-prueba"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "wa_app_secret", SECRET)
    monkeypatch.setattr(settings, "wa_verify_token", TOKEN)
    return TestClient(app)


def sign(raw: bytes, secret: str = SECRET) -> dict:
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()}


def post(client, payload, headers=None):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return client.post("/wa/webhook", content=raw, headers=sign(raw) if headers is None else headers)


def change(**value):
    return {"object": "whatsapp_business_account",
            "entry": [{"id": "1", "changes": [{"field": "messages", "value": {
                "metadata": {"phone_number_id": "555"}, **value}}]}]}


def test_challenge_ok(client):
    r = client.get("/wa/webhook", params={"hub.mode": "subscribe", "hub.verify_token": TOKEN, "hub.challenge": "123"})
    assert r.status_code == 200 and r.text == "123"
    assert r.headers["content-type"].startswith("text/plain")


def test_challenge_token_incorrecto(client):
    r = client.get("/wa/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1"})
    assert r.status_code == 403


def test_challenge_con_token_vacio_configurado(client, monkeypatch):
    monkeypatch.setattr(settings, "wa_verify_token", "")
    r = client.get("/wa/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "1"})
    assert r.status_code == 403


def test_firma_valida(client):
    assert post(client, change()).status_code == 200


def test_firma_invalida(client):
    raw = b"{}"
    assert post(client, raw, sign(raw, "otro-secreto")).status_code == 403


def test_sin_firma(client):
    assert post(client, {}, headers={}).status_code == 403


def test_sin_secreto_configurado(client, monkeypatch):
    monkeypatch.setattr(settings, "wa_app_secret", "")
    raw = b"{}"
    assert post(client, raw, sign(raw, "")).status_code == 403


def test_json_invalido_con_firma_valida(client):
    assert post(client, b"{no es json").status_code == 200


def test_payload_raro(client):
    for p in ([], {"entry": "x"}, {"entry": [1, {"changes": [None, {"value": 5}]}]}):
        assert post(client, p).status_code == 200


def test_cuerpo_demasiado_grande(client):
    assert post(client, b" " * (1024 * 1024 + 1)).status_code == 413


def test_statuses(client, caplog):
    caplog.set_level(logging.INFO)
    r = post(client, change(statuses=[{"id": "wamid.ST", "status": "delivered", "recipient_id": "5491155551234"}]))
    assert r.status_code == 200
    assert "tipo=statuses" in caplog.text and "wamid.ST" in caplog.text and "555" in caplog.text
    assert "5491155551234" not in caplog.text


def test_messages_no_loguea_texto_ni_telefono(client, caplog):
    caplog.set_level(logging.INFO)
    r = post(client, change(messages=[{"id": "wamid.MS", "from": "5491155551234", "type": "text",
                                       "text": {"body": "hola secreto"}}]))
    assert r.status_code == 200
    assert "tipo=messages" in caplog.text and "wamid.MS" in caplog.text
    assert "hola secreto" not in caplog.text and "5491155551234" not in caplog.text


def test_access_log_tapa_verify_token():
    import logging

    from app.whatsapp.webhook import RedactVerifyToken

    path = "/wa/webhook?hub.mode=subscribe&hub.verify_token=secreto123&hub_verify_token=secreto123&hub.challenge=9"
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                               ("1.2.3.4:5", "GET", path, "1.1", 200), None)
    RedactVerifyToken().filter(record)
    msg = record.getMessage()
    assert "secreto123" not in msg
    assert "hub.verify_token=***" in msg and "hub.challenge=9" in msg
