"""WhatsApp fase 2: Embedded Signup (app/whatsapp/signup.py) por la API, cifrado de los
secretos, cuentas desconectadas (token rechazado y account_update) y la migracion 0005.
Meta simulado (FakeMeta): sin red."""
import logging

import httpx
import pytest
from cryptography.fernet import Fernet

from app.api import deps
from app.config import settings
from app.models import WaAccount
from app.whatsapp import crypto, signup, store
from app.whatsapp.graph import GraphClient, GraphError

from .helpers import FakeLLM
from .test_api import V1, client_user, make_agent, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_service import PNID as SERVICE_PNID
from .test_whatsapp_service import make_wa, reply, send, text_payload

APP_SECRET = "app-secret-de-meta-123"
CODE = "AQD-codigo-del-popup-xyz"
BIZ_TOKEN = "EAAG-business-token-del-cliente-789"
WABA = "300000000000001"
PNID = "400000000000001"
DISPLAY = "+54 9 351 555-0000"


class FakeMeta:
    """Graph API simulada para el alta. fail: {metodo: GraphError}. Registra cada llamada
    con el token del cliente que la hizo."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.fail: dict[str, GraphError] = {}
        self.numbers = [{"id": PNID, "display_phone_number": DISPLAY, "verified_name": "Acme Turnos",
                         "quality_rating": "GREEN"}]
        self.templates = [
            {"id": "t1", "name": "recordatorio", "language": "es_AR", "category": "UTILITY", "status": "APPROVED",
             "components": [{"type": "BODY", "text": "Hola {{1}}"}]},
            {"id": "t2", "name": "promo", "language": "es_AR", "category": "MARKETING", "status": "REJECTED",
             "rejected_reason": "PROMOTIONAL", "components": []},
        ]

    def client(self, token: str):
        meta = self

        class Client:
            async def _call(self, name, *args):
                meta.calls.append((name, token, *args))
                if name in meta.fail:
                    raise meta.fail[name]

            async def exchange_code(self, app_id, app_secret, code):
                await self._call("exchange_code", app_id, app_secret, code)
                return BIZ_TOKEN

            async def list_phone_numbers(self, waba_id):
                await self._call("list_phone_numbers", waba_id)
                return meta.numbers

            async def subscribe_app(self, waba_id):
                await self._call("subscribe_app", waba_id)
                return {"success": True}

            async def register(self, pnid, pin):
                await self._call("register", pnid, pin)
                return {"success": True}

            async def smb_app_data(self, pnid, sync_type):
                await self._call("smb_app_data", pnid, sync_type)
                return {"success": True}

            async def get_phone_number(self, pnid, fields=""):
                await self._call("get_phone_number", pnid)
                return {"id": pnid, "display_phone_number": DISPLAY, "quality_rating": "YELLOW"}

            async def list_templates(self, waba_id, limit=100):
                await self._call("list_templates", waba_id)
                return meta.templates

            async def create_template(self, waba_id, payload):
                await self._call("create_template", waba_id, payload)
                return {"id": "t3", "status": "PENDING", "category": payload["category"]}

            async def aclose(self):
                pass

        return Client()

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


@pytest.fixture
def meta(monkeypatch):
    m = FakeMeta()
    monkeypatch.setattr(signup, "graph_for", m.client)
    monkeypatch.setattr(settings, "wa_app_id", "2192489028351511")
    monkeypatch.setattr(settings, "wa_app_secret", APP_SECRET)
    monkeypatch.setattr(settings, "wa_config_id", "cfg-123")
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    deps.api_limiter.reset()
    yield m
    deps.api_limiter.reset()


@pytest.fixture
def acme(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c, template="demo_booking")
    return c, agent, client_user(api, admin, c)


def body(agent, **extra):
    return {"code": CODE, "waba_id": WABA, "phone_number_id": PNID, "business_id": "500", "event": "FINISH",
            "agent_id": agent["id"], **extra}


def signup_ok(user, agent, **extra) -> dict:
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent, **extra))
    assert r.status_code == 201, r.text
    return r.json()


# ---------- alta ----------

def test_signup_happy_path_encrypts_secrets(api, meta, acme, caplog):
    c, agent, user = acme
    caplog.set_level(logging.DEBUG)
    acc = signup_ok(user, agent)

    assert acc["status"] == "connected" and acc["source"] == "embedded_signup"
    assert acc["client_id"] == c["id"] and acc["agent_id"] == agent["id"]
    assert (acc["display_phone_number"], acc["name"], acc["quality_rating"]) == (DISPLAY, "Acme Turnos", "GREEN")
    assert acc["has_token"] is True and acc["has_pin"] is True and acc["business_id"] == "500"
    # Orden de Meta: codigo -> numeros de la WABA -> suscripcion -> registro, con el token del cliente.
    assert meta.names() == ["exchange_code", "list_phone_numbers", "subscribe_app", "register"]
    assert meta.calls[0] == ("exchange_code", "", "2192489028351511", APP_SECRET, CODE)
    assert all(call[1] == BIZ_TOKEN for call in meta.calls[1:])
    pin = meta.calls[3][3]
    assert len(pin) == 6 and pin.isdigit()

    with api.sessions() as s:
        row = s.get(WaAccount, acc["id"])
        assert row.access_token.startswith("fernet:") and BIZ_TOKEN not in row.access_token
        assert row.pin_enc.startswith("fernet:") and pin not in row.pin_enc
        assert store.token_for(row) == BIZ_TOKEN and store.pin_for(row) == pin
        assert row.connected_by is not None and row.status_changed_at is not None

    # Nada secreto en la respuesta, el listado ni los logs.
    listed = user.get(f"{V1}/whatsapp/accounts").json()
    for secret in (BIZ_TOKEN, APP_SECRET, CODE, pin):
        assert secret not in str(acc) and secret not in str(listed) and secret not in caplog.text


def test_signup_register_failure_is_pending_then_retry(api, meta, acme):
    _, agent, user = acme
    meta.fail["register"] = GraphError("Two step verification PIN Mismatch", code=133005, status=400)
    acc = signup_ok(user, agent)
    assert acc["status"] == "pending" and "133005" in acc["status_reason"]

    del meta.fail["register"]
    retry = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/register", json={"pin": "123456"})
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "connected" and retry.json()["status_reason"] is None
    assert meta.calls[-2:] == [("subscribe_app", BIZ_TOKEN, WABA), ("register", BIZ_TOKEN, PNID, "123456")]
    with api.sessions() as s:
        assert store.pin_for(s.get(WaAccount, acc["id"])) == "123456"


def test_signup_subscribe_failure_is_pending(meta, acme):
    _, agent, user = acme
    meta.fail["subscribe_app"] = GraphError("Unsupported post request", code=100, status=400)
    acc = signup_ok(user, agent)
    assert acc["status"] == "pending" and acc["status_reason"].startswith("subscribed_apps")
    assert "register" not in meta.names()


def test_signup_coexistence_skips_register(meta, acme):
    _, agent, user = acme
    # El evento de coexistencia solo trae waba_id: el numero es el unico de la WABA.
    acc = signup_ok(user, agent, event="FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", phone_number_id="")
    assert acc["source"] == "coexistence" and acc["status"] == "connected"
    assert acc["phone_number_id"] == PNID and acc["has_pin"] is False
    assert "register" not in meta.names()
    # Sincronizacion de contactos e historial pedida en el alta (Meta da 24 h).
    assert [c for c in meta.calls if c[0] == "smb_app_data"] == [
        ("smb_app_data", BIZ_TOKEN, PNID, "smb_app_state_sync"), ("smb_app_data", BIZ_TOKEN, PNID, "history")]


def test_signup_coexistence_sync_failure_is_pending_and_ambiguous_waba(meta, acme):
    _, agent, user = acme
    meta.fail["smb_app_data"] = GraphError("Not allowed", code=100, status=400)
    acc = signup_ok(user, agent, event="FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", phone_number_id="")
    assert acc["status"] == "pending" and acc["status_reason"].startswith("smb_app_data smb_app_state_sync")
    # Con varios numeros en la WABA no se adivina cual.
    meta.numbers = meta.numbers + [{"id": "400000000000002", "display_phone_number": "+1"}]
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent, event="FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING",
                                                     phone_number_id=""))
    assert r.status_code == 400 and r.json()["code"] == "signup_no_phone"
    # Sin numero, un FINISH comun sigue rechazado.
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent, phone_number_id=""))
    assert r.status_code == 422


def test_signup_reconnect_reuses_pin_and_keeps_it_on_failure(api, meta, acme):
    _, agent, user = acme
    first = signup_ok(user, agent)
    pin_a = next(c for c in meta.calls if c[0] == "register")[3]
    with api.sessions() as s:
        store.mark_status(s, s.get(WaAccount, first["id"]), "disconnected", "token_invalid code=190")
        s.commit()
    # Reconexion sin PIN: se registra con el guardado, no con uno nuevo.
    meta.calls.clear()
    again = signup_ok(user, agent)
    assert again["status"] == "connected" and ("register", BIZ_TOKEN, PNID, pin_a) in meta.calls
    # Un PIN pedido que falla no pisa el guardado.
    meta.fail["register"] = GraphError("Two step verification PIN Mismatch", code=133005, status=400)
    third = signup_ok(user, agent, pin="999999")
    assert third["status"] == "pending"
    with api.sessions() as s:
        assert store.pin_for(s.get(WaAccount, first["id"])) == pin_a


def test_manual_account_actions_are_admin_only(api, admin, meta, acme, monkeypatch):  # noqa: F811
    c, agent, user = acme
    r = admin.post(f"{V1}/whatsapp/accounts", json={
        "client_id": c["id"], "agent_id": agent["id"], "phone_number_id": "400000000000009",
        "waba_id": WABA, "display_phone_number": "+1 555"})
    assert r.status_code == 201, r.text
    acc = r.json()
    base = f"{V1}/whatsapp/accounts/{acc['id']}"
    # El cliente no usa nuestro token (WABA de la plataforma) para registro, Meta ni plantillas.
    for method, path, payload in (("post", "/register", {"pin": "123456"}), ("post", "/refresh", None),
                                  ("get", "/templates", None),
                                  ("post", "/templates", {"name": "x", "language": "es_AR", "category": "UTILITY",
                                                          "body": "Hola", "examples": []})):
        r = getattr(user, method)(base + path, **({"json": payload} if payload is not None else {}))
        assert r.status_code == 403, (path, r.text)
    assert meta.calls == []
    # Sigue pudiendo elegir el agente y desactivarlo.
    assert user.patch(base, json={"name": "Piloto"}).status_code == 200
    # Admin: retry_register usa WA_REGISTRATION_PIN (nunca uno al azar); sin el, 422.
    monkeypatch.setattr(settings, "wa_access_token", "token-global")
    monkeypatch.setattr(settings, "wa_registration_pin", "")
    r = admin.post(base + "/register", json={})
    assert r.status_code == 422 and "register" not in meta.names()
    monkeypatch.setattr(settings, "wa_registration_pin", "246810")
    r = admin.post(base + "/register", json={})
    assert r.status_code == 200, r.text
    assert meta.calls[-1] == ("register", "token-global", "400000000000009", "246810")
    assert r.json()["has_pin"] is False


def test_retry_reason_names_the_failed_step(meta, acme):
    _, agent, user = acme
    meta.fail["register"] = GraphError("Two step verification PIN Mismatch", code=133005, status=400)
    acc = signup_ok(user, agent)
    meta.fail = {"subscribe_app": GraphError("(#200) Permissions error", code=200, status=403)}
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/register", json={})
    assert r.status_code == 502
    (after,) = user.get(f"{V1}/whatsapp/accounts").json()
    assert after["status_reason"].startswith("subscribed_apps:")


def test_signup_reconnect_same_client_updates(api, meta, acme):
    _, agent, user = acme
    first = signup_ok(user, agent)
    with api.sessions() as s:
        store.mark_status(s, s.get(WaAccount, first["id"]), "disconnected", "token_invalid code=190")
        s.commit()
    again = signup_ok(user, agent)
    assert again["id"] == first["id"] and again["status"] == "connected"


def test_signup_rejections(api, admin, meta, acme):  # noqa: F811
    _, agent, user = acme
    # Solo con WABA, sin numero.
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent, event="FINISH_ONLY_WABA", phone_number_id=""))
    assert r.status_code == 400 and r.json()["code"] == "signup_no_phone"
    # Agente de otro cliente.
    other = make_client(admin, slug="otro")
    other_agent = make_agent(admin, other, template="demo_booking")
    assert user.post(f"{V1}/whatsapp/signup", json=body(other_agent)).status_code == 404
    # El client_id del cuerpo no vale para un usuario de cliente: se le fuerza el suyo.
    r = user.post(f"{V1}/whatsapp/signup", json=body(other_agent, client_id=other["id"]))
    assert r.status_code == 404
    # El numero no es de esa WABA.
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent, phone_number_id="999"))
    assert r.status_code == 400 and r.json()["code"] == "signup_mismatch"
    # Codigo vencido (Meta da 100 en el intercambio).
    meta.fail["exchange_code"] = GraphError("This authorization code has expired.", code=100, status=400)
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent))
    assert r.status_code == 400 and r.json()["code"] == "signup_code_expired"
    # Otro error de Meta: 502 con el codigo de Meta, sin el secret.
    meta.fail["exchange_code"] = GraphError("Error validating client secret.", code=1, status=400)
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent))
    assert r.status_code == 502 and r.json()["code"] == "meta_error"
    assert r.json()["errors"] == [{"meta_code": 1, "meta_subcode": None}] and APP_SECRET not in r.text
    # Ninguna cuenta creada.
    assert user.get(f"{V1}/whatsapp/accounts").json() == []


def test_signup_number_of_other_client_is_409(api, admin, meta, acme):  # noqa: F811
    _, agent, user = acme
    signup_ok(user, agent)
    other = make_client(admin, slug="otro")
    other_agent = make_agent(admin, other, template="demo_booking")
    other_user = client_user(api, admin, other, email="b@otro.com")
    calls = len(meta.calls)
    r = other_user.post(f"{V1}/whatsapp/signup", json=body(other_agent))
    assert r.status_code == 409
    assert len(meta.calls) == calls     # sin gastar el codigo
    # Tampoco ve ni maneja la cuenta del otro.
    assert other_user.get(f"{V1}/whatsapp/accounts").json() == []
    acc_id = user.get(f"{V1}/whatsapp/accounts").json()[0]["id"]
    for path in ("register", "refresh"):
        assert other_user.post(f"{V1}/whatsapp/accounts/{acc_id}/{path}", json={}).status_code == 404


def test_signup_admin_for_a_client(api, admin, meta, acme):  # noqa: F811
    c, agent, _ = acme
    r = admin.post(f"{V1}/whatsapp/signup", json=body(agent, client_id=c["id"]))
    assert r.status_code == 201 and r.json()["client_id"] == c["id"]


def test_signup_requires_user_session(api, admin, meta, acme):  # noqa: F811
    c, agent, _ = acme
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "crm"}).json()["key"]
    r = api.client.post(f"{V1}/whatsapp/signup", json=body(agent), headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 403
    assert api.client.post(f"{V1}/whatsapp/signup", json=body(agent)).status_code == 401
    assert "exchange_code" not in meta.names()


def test_signup_rate_limit(meta, acme, monkeypatch):
    _, agent, user = acme
    monkeypatch.setattr(settings, "wa_signup_per_hour", 1)
    signup_ok(user, agent)
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent))
    assert r.status_code == 429 and r.headers.get("retry-after")


def test_config_endpoint(api, meta, acme, monkeypatch):
    _, agent, user = acme
    cfg = user.get(f"{V1}/whatsapp/config").json()
    assert cfg == {"enabled": True, "reason": None, "app_id": "2192489028351511", "config_id": "cfg-123",
                   "graph_version": settings.wa_graph_version, "sdk_locale": settings.wa_sdk_locale}
    monkeypatch.setattr(settings, "wa_config_id", "")
    cfg = user.get(f"{V1}/whatsapp/config").json()
    assert cfg["enabled"] is False and "WA_CONFIG_ID" in cfg["reason"]
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent))
    assert r.status_code == 503 and r.json()["code"] == "wa_signup_disabled"
    monkeypatch.setattr(settings, "wa_config_id", "cfg-123")
    monkeypatch.setattr(settings, "wa_token_key", "")
    cfg = user.get(f"{V1}/whatsapp/config").json()
    assert cfg["enabled"] is False and "WA_TOKEN_KEY" in cfg["reason"]
    r = user.post(f"{V1}/whatsapp/signup", json=body(agent))
    assert r.status_code == 503 and r.json()["code"] == "wa_token_key_missing"
    assert api.client.get(f"{V1}/whatsapp/config").status_code == 401


def test_refresh_updates_quality_and_190_disconnects(api, meta, acme):
    _, agent, user = acme
    acc = signup_ok(user, agent)
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/refresh")
    assert r.status_code == 200 and r.json()["quality_rating"] == "YELLOW"
    meta.fail["get_phone_number"] = GraphError("Error validating access token", code=190, status=401)
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/refresh")
    assert r.status_code == 502 and r.json()["errors"][0]["meta_code"] == 190
    (after,) = user.get(f"{V1}/whatsapp/accounts").json()
    assert after["status"] == "disconnected" and after["status_reason"] == "token_invalid code=190"


# ---------- cuenta desconectada en el servicio ----------

def own_token(w, monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    with w.sessions() as s:
        store.update_account(s, s.get(WaAccount, w.account_id), access_token="token-del-cliente")
        s.commit()


async def test_401_on_send_disconnects_and_stops_replying(sessions, monkeypatch):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola")))
    own_token(w, monkeypatch)
    w.graph.fail = GraphError("Error validating access token", code=190, status=401)
    await send(w, text_payload("hola", "wamid.in1"))
    with sessions() as s:
        account = s.get(WaAccount, w.account_id)
        assert account.status == "disconnected" and account.status_reason == "token_invalid code=190"
    # El siguiente no llega al LLM (no tiene mas turnos: fallaria) ni se intenta enviar.
    w.graph.fail = None
    await send(w, text_payload("sigo", "wamid.in2"))
    assert w.graph.sent == [] and w.llm.turns == [] and len(w.llm.calls) == 1


async def test_401_with_global_token_only_logs(sessions, monkeypatch, caplog):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola")))
    w.graph.fail = GraphError("Error validating access token", code=190, status=401)
    await send(w, text_payload("hola", "wamid.in1"))
    with sessions() as s:
        assert s.get(WaAccount, w.account_id).status == "connected"
    assert "token global" in caplog.text


async def test_account_update_and_quality_events(sessions, caplog):
    caplog.set_level(logging.INFO, logger="app.whatsapp")
    w = make_wa(sessions)
    with sessions() as s:
        account = s.get(WaAccount, w.account_id)
        waba, display = account.waba_id, account.display_phone_number

    def event(field, value):
        return {"object": "whatsapp_business_account",
                "entry": [{"id": waba, "time": 1, "changes": [{"field": field, "value": value}]}]}

    await send(w, event("phone_number_quality_update", {
        "display_phone_number": "15550000000", "event": "UPGRADE", "current_limit": "TIER_10K",
        "old_limit": "TIER_1K"}))
    await send(w, event("account_update", {"event": "PARTNER_APP_INSTALLED", "waba_info": {"waba_id": waba}}))
    with sessions() as s:
        account = s.get(WaAccount, w.account_id)
        assert account.messaging_limit == "TIER_10K" and account.status == "connected"
        assert display  # el numero visible con espacios coincide por digitos
    await send(w, event("account_update", {"event": "PARTNER_REMOVED", "waba_info": {"waba_id": waba},
                                           "disconnection_info": {"reason": "x"}}))
    with sessions() as s:
        account = s.get(WaAccount, w.account_id)
        assert account.status == "disconnected" and account.status_reason == "account_update PARTNER_REMOVED"
    # DISABLED_UPDATE: SCHEDULE_FOR_DISABLE solo avisa; DISABLE desconecta; REINSTATE reconecta
    # solo lo que desconecto un DISABLE (no el PARTNER_REMOVED de arriba).
    def disabled(state):
        return event("account_update", {"event": "DISABLED_UPDATE",
                                        "ban_info": {"waba_ban_state": state, "waba_ban_date": "April 17, 2025"}})

    await send(w, disabled("REINSTATE"))
    with sessions() as s:
        assert s.get(WaAccount, w.account_id).status_reason == "account_update PARTNER_REMOVED"
    with sessions() as s:
        store.mark_status(s, s.get(WaAccount, w.account_id), "connected")
        s.commit()
    await send(w, disabled("SCHEDULE_FOR_DISABLE"))
    with sessions() as s:
        assert s.get(WaAccount, w.account_id).status == "connected"
    await send(w, disabled(["DISABLE"]))
    with sessions() as s:
        account = s.get(WaAccount, w.account_id)
        assert account.status == "disconnected" and account.status_reason == "account_update DISABLED_UPDATE"
    await send(w, disabled("REINSTATE"))
    with sessions() as s:
        assert s.get(WaAccount, w.account_id).status == "connected"
    await send(w, event("account_update", {"event": "ACCOUNT_DELETED", "waba_info": {"waba_id": waba}}))
    await send(w, event("message_template_status_update", {
        "event": "APPROVED", "message_template_id": 123, "message_template_name": "recordatorio",
        "message_template_language": "es_AR", "reason": "NONE"}))
    assert "message_template_status_update event=APPROVED" in caplog.text
    # Desconectada: no responde.
    await send(w, text_payload("hola", "wamid.in9", pnid=SERVICE_PNID))
    assert w.graph.sent == []


# ---------- crypto ----------

def test_crypto_roundtrip_legacy_rotation_and_missing_key(monkeypatch, caplog):
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "wa_token_key", old)
    assert crypto.enabled()
    enc = crypto.encrypt("secreto")
    assert enc.startswith("fernet:") and "secreto" not in enc and crypto.decrypt(enc) == "secreto"
    # Rotacion: la nueva primero cifra; la vieja sigue descifrando.
    monkeypatch.setattr(settings, "wa_token_key", f"{new},{old}")
    assert crypto.decrypt(enc) == "secreto"
    assert crypto.decrypt(crypto.encrypt("otro")) == "otro"
    # Legado en claro: se lee igual, con warning.
    with caplog.at_level(logging.WARNING):
        monkeypatch.setattr(crypto, "_warned_legacy", False)
        assert crypto.decrypt("EAAG-en-claro") == "EAAG-en-claro"
    assert "en claro" in caplog.text and "EAAG-en-claro" not in caplog.text
    assert crypto.decrypt(None) is None and crypto.decrypt("") is None
    # Sin clave o con otra clave: TokenKeyMissing (503), sin el valor en el mensaje.
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    with pytest.raises(crypto.TokenKeyMissing):
        crypto.decrypt(enc)
    monkeypatch.setattr(settings, "wa_token_key", "")
    assert not crypto.enabled()
    with pytest.raises(crypto.TokenKeyMissing) as e:
        crypto.encrypt("x")
    assert e.value.status_code == 503
    monkeypatch.setattr(settings, "wa_token_key", "no-es-fernet")
    assert not crypto.enabled()
    pins = {crypto.new_pin() for _ in range(50)}
    assert all(len(p) == 6 and p.isdigit() for p in pins) and len(pins) > 1


def test_manual_account_without_key_is_503(api, admin, acme, monkeypatch):  # noqa: F811
    c, agent, _ = acme
    monkeypatch.setattr(settings, "wa_token_key", "")
    r = admin.post(f"{V1}/whatsapp/accounts", json={
        "client_id": c["id"], "agent_id": agent["id"], "phone_number_id": "77", "waba_id": "1",
        "display_phone_number": "+1", "access_token": "EAAG-x"})
    assert r.status_code == 503 and r.json()["code"] == "wa_token_key_missing"
    # Sin token propio (usa WA_ACCESS_TOKEN) no hace falta la clave.
    r = admin.post(f"{V1}/whatsapp/accounts", json={
        "client_id": c["id"], "agent_id": agent["id"], "phone_number_id": "77", "waba_id": "1",
        "display_phone_number": "+1"})
    assert r.status_code == 201 and r.json()["has_token"] is False


# ---------- Graph: llamadas nuevas ----------

async def test_graph_signup_calls(caplog):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path.endswith("/oauth/access_token"):
            return httpx.Response(200, json={"access_token": BIZ_TOKEN, "token_type": "bearer"})
        if path.endswith("/phone_numbers"):
            return httpx.Response(200, json={"data": [{"id": PNID}]})
        if path.endswith("/message_templates") and request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "t1", "name": "x"}], "paging": {}})
        if request.headers.get("authorization") == "Bearer vencido":
            return httpx.Response(401, json={"error": {"message": "Error validating access token", "code": 190}})
        return httpx.Response(200, json={"success": True, "id": "t9", "status": "PENDING"})

    caplog.set_level(logging.DEBUG)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert await GraphClient("", http=http).exchange_code("app1", APP_SECRET, CODE) == BIZ_TOKEN
    ex = seen[0]
    assert "authorization" not in ex.headers
    assert ex.url.params["client_secret"] == APP_SECRET and ex.url.params["code"] == CODE
    assert APP_SECRET not in caplog.text and CODE not in caplog.text

    g = GraphClient(BIZ_TOKEN, http=http)
    assert await g.list_phone_numbers(WABA) == [{"id": PNID}]
    assert "verified_name" in seen[-1].url.params["fields"]
    await g.subscribe_app(WABA)
    assert seen[-1].method == "POST" and seen[-1].url.path == f"/v25.0/{WABA}/subscribed_apps"
    assert await g.list_templates(WABA) == [{"id": "t1", "name": "x"}]
    assert (await g.create_template(WABA, {"name": "x"}))["id"] == "t9"

    with pytest.raises(GraphError) as e:
        await GraphClient("vencido", http=http).get_phone_number(PNID)
    assert e.value.is_auth_error and e.value.code == 190
    assert not GraphError("sin permiso", code=10, status=403).is_auth_error
