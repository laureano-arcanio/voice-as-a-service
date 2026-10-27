"""WhatsApp con la app de Meta propia del cliente (app/whatsapp/own_app.py, docs/ADMIN_SOPORTE_PLAN.md
seccion 4): alta por la API, secretos cifrados, webhook por cuenta (/wa/webhook/<clave>) y Embedded Signup
apagado por defecto. Meta simulado (FakeMeta de test_whatsapp_signup): sin red."""
import json

import pytest
from cryptography.fernet import Fernet

from app.api import deps
from app.config import settings
from app.main import app
from app.models import WaAccount
from app.whatsapp import own_app, signup

from .test_api import V1
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_signup import (  # noqa: F401  (fixture)
    DISPLAY,
    PNID,
    WABA,
    FakeMeta,
    acme,
)
from .test_whatsapp_webhook import sign

TOKEN = "EAAG-token-de-sistema-del-cliente-123"
SECRET = "secret-de-la-app-del-cliente-456"


@pytest.fixture
def meta(monkeypatch):
    m = FakeMeta()
    monkeypatch.setattr(signup, "graph_for", m.client)
    monkeypatch.setattr(own_app, "graph_for", m.client)
    monkeypatch.setattr(settings, "wa_public_url", "https://wa.example.com")
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    deps.api_limiter.reset()
    yield m
    deps.api_limiter.reset()


@pytest.fixture
def recorded():
    from app.whatsapp.service import get_service

    class Rec:
        def __init__(self):
            self.payloads = []

        def handle_payload(self, payload):
            self.payloads.append(payload)

    rec = Rec()
    app.dependency_overrides[get_service] = lambda: rec
    yield rec
    app.dependency_overrides.pop(get_service, None)


def connect(user, agent, **extra):
    return user.post(f"{V1}/whatsapp/accounts/own-app", json={
        "agent_id": agent["id"], "phone_number_id": PNID, "waba_id": WABA, "access_token": TOKEN,
        "app_secret": SECRET, **extra})


def test_alta_cifra_y_devuelve_webhook(api, meta, acme):  # noqa: F811
    c, agent, user = acme
    r = connect(user, agent)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["source"] == "own_app" and out["status"] == "connected" and out["display_phone_number"] == DISPLAY
    assert out["webhook_url"].startswith("https://wa.example.com/wa/webhook/")
    assert out["verify_token"] and out["has_app_secret"] and out["has_token"]
    assert TOKEN not in r.text and SECRET not in r.text
    assert meta.names() == ["list_phone_numbers", "subscribe_app"]
    assert all(call[1] == TOKEN for call in meta.calls)       # con el token del cliente, no el nuestro
    with api.sessions() as s:
        row = s.query(WaAccount).filter_by(phone_number_id=PNID).one()
        assert row.app_secret.startswith("fernet:") and row.verify_token.startswith("fernet:")
        assert row.client_id == c["id"]


def test_numero_de_otra_waba_y_reconexion(api, meta, acme):  # noqa: F811
    _, agent, user = acme
    meta.numbers = [{"id": "999", "display_phone_number": "+1"}]
    r = connect(user, agent)
    assert r.status_code == 400 and r.json()["code"] == "signup_mismatch"
    meta.numbers = FakeMeta().numbers
    first = connect(user, agent).json()
    again = connect(user, agent, access_token=TOKEN + "-nuevo")
    assert again.status_code == 201
    # La URL y el verify token no cambian: lo configurado en Meta sigue andando.
    assert again.json()["webhook_url"] == first["webhook_url"]
    assert again.json()["verify_token"] == first["verify_token"]


def test_numero_de_otro_cliente_es_409(api, admin, meta, acme):  # noqa: F811
    from .test_api import client_user, make_agent, make_client
    _, agent, user = acme
    assert connect(user, agent).status_code == 201
    other = make_client(admin, "otro")
    other_agent = make_agent(admin, other, template="demo_booking")
    r = connect(client_user(api, admin, other, "beto@otro.com"), other_agent)
    assert r.status_code == 409


def test_webhook_por_cuenta(api, meta, acme, recorded):  # noqa: F811
    _, agent, user = acme
    out = connect(user, agent).json()
    path = "/wa/webhook/" + out["webhook_url"].rsplit("/", 1)[1]
    ok = api.client.get(path, params={"hub.mode": "subscribe", "hub.verify_token": out["verify_token"], "hub.challenge": "7"})
    assert ok.status_code == 200 and ok.text == "7"
    bad = api.client.get(path, params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "7"})
    assert bad.status_code == 403
    assert api.client.get("/wa/webhook/no-existe", params={"hub.mode": "subscribe", "hub.verify_token": "x"}).status_code == 403

    def change(pnid):
        return {"field": "messages", "value": {"metadata": {"phone_number_id": pnid},
                                               "messages": [{"id": "wamid.1", "from": "54911", "type": "text"}]}}

    payload = {"object": "whatsapp_business_account", "entry": [
        {"id": WABA, "changes": [change(PNID), change("888")]},           # otro numero: se descarta
        {"id": "otra-waba", "changes": [change(PNID)]},                   # otra WABA: se descarta
    ]}
    raw = json.dumps(payload).encode()
    assert api.client.post(path, content=raw, headers=sign(raw, "secret-equivocado")).status_code == 403
    assert api.client.post(path, content=raw, headers=sign(raw, settings.wa_app_secret or "x")).status_code == 403
    assert api.client.post(path, content=raw, headers=sign(raw, SECRET)).status_code == 200
    [got] = recorded.payloads
    assert [e["id"] for e in got["entry"]] == [WABA]
    assert [c["value"]["metadata"]["phone_number_id"] for c in got["entry"][0]["changes"]] == [PNID]


def test_embedded_signup_apagado_por_defecto(api, acme, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "wa_embedded_signup", False)
    _, _, user = acme
    r = user.get(f"{V1}/whatsapp/config")
    assert r.status_code == 200 and r.json()["enabled"] is False and "app de Meta" in r.json()["reason"]


def test_reintento_solo_suscribe(api, meta, acme):  # noqa: F811
    _, agent, user = acme
    out = connect(user, agent).json()
    meta.calls.clear()
    r = user.post(f"{V1}/whatsapp/accounts/{out['id']}/register", json={})
    assert r.status_code == 200, r.text
    assert meta.names() == ["subscribe_app"] and r.json()["has_pin"] is False
