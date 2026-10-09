"""Mails por Resend: alta de cliente con link para crear la clave, numero asignado y el sender."""
import re
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.config import settings
from app.mail import sender
from app.mail.sender import Mail, SendResult
from app.models import Role, User
from app.services.security import (
    create_password_setup_token,
    create_session_token,
    decode_password_setup_token,
    decode_session_token,
    hash_password,
)

from .test_api import ADMIN, V1, admin, make_agent, make_tier  # noqa: F401  (admin: fixture)

CLIENT_BODY = {"owner_email": "Ana@Acme.com", "owner_name": "Ana Pérez"}


class Outbox(list):
    """Los mails que la API manda; `result` es lo que contesta el "Resend" simulado."""
    result = SendResult("sent", id="re_123")


@pytest.fixture
def outbox(monkeypatch):
    sent = Outbox()

    def fake_send(mail, idempotency_key=None):
        sent.append(mail)
        return sent.result

    monkeypatch.setattr("app.mail.notify.send", fake_send)
    return sent


def create_client_with_owner(admin, slug="acme", **extra):
    tier = make_tier(admin, name=f"plan-{slug}", description="Para pymes que arrancan.", max_concurrent_calls=3,
                     inbound_minutes=1500, outbound_minutes=None, max_phone_numbers=2)
    r = admin.post(f"{V1}/clients", json={"name": "Acme SA", "slug": slug, "tier_id": tier["id"], **CLIENT_BODY,
                                          **extra})
    assert r.status_code == 201, r.text
    return r.json(), tier


def setup_token(mail: Mail) -> str:
    url = re.search(r'https://\S+/set-password\?token=[^\s"<]+', mail.text).group(0)
    return parse_qs(urlsplit(url).query)["token"][0]


# ---------- alta de cliente ----------

def test_create_client_with_owner_sends_welcome(api, admin, outbox):
    client, _ = create_client_with_owner(admin)
    assert client["invite"] == {"email": "ana@acme.com", "status": "sent", "error": None}
    assert len(outbox) == 1
    mail = outbox[0]
    assert mail.to == "ana@acme.com"
    assert mail.subject == "Activá tu cuenta de Atentina"
    # El plan contratado, con "Sin límite" donde el tier no tiene tope.
    for text in ("plan-acme", "Para pymes que arrancan.", "1.500", "Sin límite"):
        assert text in mail.html and text in mail.text
    assert "Hola Ana," in mail.text and "Acme SA" in mail.text
    # Link al dashboard con el email prellenado, y el de la clave.
    assert f"{settings.app_url}/login?email=ana%40acme.com" in mail.text
    assert "/set-password?token=" in mail.html
    with api.sessions() as s:
        user = s.query(User).filter_by(email="ana@acme.com").one()
        assert user.role == Role.client and user.client_id == client["id"] and user.name == "Ana Pérez"


def test_create_client_without_owner_sends_nothing(api, admin, outbox):
    r = admin.post(f"{V1}/clients", json={"name": "Sola", "slug": "sola", "tier_id": make_tier(admin)["id"]})
    assert r.status_code == 201 and r.json()["invite"] is None
    assert outbox == []


def test_owner_cannot_log_in_until_password_is_set(api, admin, outbox):
    create_client_with_owner(admin)
    r = api.client.post(f"{V1}/auth/login", json={"email": "ana@acme.com", "password": "cualquiera-123"})
    assert r.status_code == 401


def test_duplicate_owner_email_creates_nothing(api, admin, outbox):
    create_client_with_owner(admin)
    tier = make_tier(admin, name="otro")
    r = admin.post(f"{V1}/clients", json={"name": "Otra", "slug": "otra", "tier_id": tier["id"], **CLIENT_BODY})
    assert r.status_code == 409 and r.json()["code"] == "user_exists"
    assert [c["slug"] for c in admin.get(f"{V1}/clients").json()] == ["acme"]   # sin cliente huerfano
    assert len(outbox) == 1


def test_mail_failure_does_not_fail_creation(api, admin, outbox):
    outbox.result = SendResult("failed", error="500 boom")
    client, _ = create_client_with_owner(admin)
    assert client["invite"]["status"] == "failed" and client["invite"]["error"] == "500 boom"


# ---------- crear la clave ----------

def test_password_setup_flow_logs_in_and_is_single_use(api, admin, outbox):
    create_client_with_owner(admin)
    token = setup_token(outbox[0])
    info = api.client.post(f"{V1}/auth/password-setup/check", json={"token": token})
    assert info.status_code == 200
    assert info.json() == {"email": "ana@acme.com", "name": "Ana Pérez", "client_name": "Acme SA"}

    r = api.client.post(f"{V1}/auth/password-setup", json={"token": token, "password": "mi-clave-nueva-1"})
    assert r.status_code == 200 and r.json()["email"] == "ana@acme.com"
    assert api.client.get(f"{V1}/auth/me").json()["role"] == "client"   # quedo con sesion abierta
    assert api.login("ana@acme.com", "mi-clave-nueva-1")

    # Un solo uso: el mismo link ya no sirve, ni para ver ni para cambiar la clave.
    for path, body in (("check", {}), ("", {"password": "otra-clave-nueva-2"})):
        r = api.client.post(f"{V1}/auth/password-setup" + (f"/{path}" if path else ""), json={"token": token, **body})
        assert r.status_code == 422 and r.json()["code"] == "invalid_setup_token"


def test_password_setup_rejects_weak_expired_and_foreign_tokens(api, admin, outbox, monkeypatch):
    create_client_with_owner(admin)
    token = setup_token(outbox[0])
    r = api.client.post(f"{V1}/auth/password-setup", json={"token": token, "password": "corta"})
    assert r.status_code == 422                       # min 10: no gasta el link
    assert api.client.post(f"{V1}/auth/password-setup/check", json={"token": token}).status_code == 200

    assert api.client.post(f"{V1}/auth/password-setup/check", json={"token": "basura" * 5}).status_code == 422
    with api.sessions() as s:
        user = s.query(User).filter_by(email="ana@acme.com").one()
        user_id, pw = user.id, user.password_hash
    monkeypatch.setattr(settings, "password_setup_hours", -1)
    expired, _ = create_password_setup_token(user_id, pw)
    assert api.client.post(f"{V1}/auth/password-setup/check", json={"token": expired}).status_code == 422
    # Un token de sesion (misma AUTH_SECRET) no sirve como link de alta.
    session, _ = create_session_token(user_id, "client", None)
    assert api.client.post(f"{V1}/auth/password-setup/check", json={"token": session}).status_code == 422


def test_setup_token_is_not_a_session_token(api, admin, outbox):
    create_client_with_owner(admin)
    token = setup_token(outbox[0])
    assert decode_password_setup_token(token) is not None
    assert decode_session_token(token) is None
    r = api.client.get(f"{V1}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_deactivated_user_cannot_use_setup_link(api, admin, outbox):
    create_client_with_owner(admin)
    token = setup_token(outbox[0])
    with api.sessions() as s:
        s.query(User).filter_by(email="ana@acme.com").one().active = False
        s.commit()
    assert api.client.post(f"{V1}/auth/password-setup/check", json={"token": token}).status_code == 422


def test_resend_invite(api, admin, outbox):
    create_client_with_owner(admin)
    with api.sessions() as s:
        user_id = s.query(User).filter_by(email="ana@acme.com").one().id
    r = admin.post(f"{V1}/users/{user_id}/invite")
    assert r.status_code == 200 and r.json()["status"] == "sent" and len(outbox) == 2
    # El link nuevo anda.
    assert api.client.post(f"{V1}/auth/password-setup/check", json={"token": setup_token(outbox[1])}).status_code == 200
    # Un admin no es de ningun cliente: no se invita.
    with api.sessions() as s:
        admin_id = s.query(User).filter_by(email=ADMIN[0]).one().id
    assert admin.post(f"{V1}/users/{admin_id}/invite").status_code == 422


def test_invite_requires_admin(api, admin, outbox):
    create_client_with_owner(admin)
    with api.sessions() as s:
        user_id = s.query(User).filter_by(email="ana@acme.com").one().id
        s.query(User).filter_by(email="ana@acme.com").one().password_hash = hash_password("clave-de-ana-123")
        s.commit()
    ana = api.login("ana@acme.com", "clave-de-ana-123")
    assert ana.post(f"{V1}/users/{user_id}/invite").status_code == 403


# ---------- numero asignado ----------

def test_assigning_number_mails_every_active_user_of_the_client(api, admin, outbox):
    client, _ = create_client_with_owner(admin)
    for email, active in (("beto@acme.com", True), ("inactivo@acme.com", False)):
        r = admin.post(f"{V1}/users", json={"email": email, "password": "cliente-password-1", "role": "client",
                                             "client_id": client["id"]})
        if not active:
            admin.patch(f"{V1}/users/{r.json()['id']}", json={"active": False})
    outbox.clear()
    n = admin.post(f"{V1}/phone-numbers", json={"e164": "+5491155550001", "label": "Ventas"}).json()
    assert outbox == []                                 # cargado, sin asignar: sin mail

    assert admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": client["id"]}).status_code == 200
    assert sorted(m.to for m in outbox) == ["ana@acme.com", "beto@acme.com"]
    mail = next(m for m in outbox if m.to == "beto@acme.com")
    assert mail.subject == "Te asignamos el número +5491155550001"
    assert "Ventas" in mail.html and "1 de 2" in mail.html and "Todavía sin agente" in mail.html
    assert f"{settings.app_url}/login?email=beto%40acme.com" in mail.html.replace("&amp;", "&")

    # Asignar de nuevo al mismo cliente no repite el aviso.
    outbox.clear()
    assert admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": client["id"]}).status_code == 200
    assert outbox == []


def test_creating_number_already_assigned_mentions_agent(api, admin, outbox):
    client, _ = create_client_with_owner(admin)
    agent = make_agent(admin, client)
    outbox.clear()
    r = admin.post(f"{V1}/phone-numbers", json={"e164": "+5491155550002", "client_id": client["id"],
                                                 "agent_id": agent["id"]})
    assert r.status_code == 201
    assert len(outbox) == 1 and "Ventas" in outbox[0].text and "Todavía sin agente" not in outbox[0].text


def test_number_over_tier_limit_sends_nothing(api, admin, outbox):
    client, _ = create_client_with_owner(admin)    # tope: 2 numeros
    ids = [admin.post(f"{V1}/phone-numbers", json={"e164": f"+549115555000{i}"}).json()["id"] for i in range(3, 6)]
    outbox.clear()
    codes = [admin.post(f"{V1}/phone-numbers/{i}/assign", json={"client_id": client["id"]}).status_code for i in ids]
    assert codes == [200, 200, 409]
    assert len(outbox) == 2                          # un mail (a Ana) por asignación lograda


# ---------- mails: contenido y sender ----------

def test_dynamic_text_is_escaped(api, admin, outbox):
    tier = make_tier(admin, name="<b>x</b>")
    r = admin.post(f"{V1}/clients", json={"name": "<script>alert(1)</script>", "slug": "xss", "tier_id": tier["id"],
                                          "owner_email": "a@b.com", "owner_name": "<i>Ana</i>"})
    assert r.status_code == 201
    html = outbox[0].html
    assert "<script>" not in html and "<b>x</b>" not in html and "<i>Ana</i>" not in html
    assert "&lt;script&gt;" in html


def test_sender_without_key_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "")
    assert sender.send(Mail("a@b.com", "x", "<p>x</p>", "x")).status == "disabled"


def test_sender_posts_to_resend(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return httpx.Response(200, json={"id": "re_abc"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(sender.httpx, "post", fake_post)
    result = sender.send(Mail("a@b.com", "Hola", "<p>x</p>", "x"), idempotency_key="k1")
    assert result == SendResult("sent", id="re_abc")
    url, body, headers = calls[0]
    assert url == sender.RESEND_URL and headers["Authorization"] == "Bearer re_test"
    assert headers["Idempotency-Key"] == "k1"
    assert body["from"] == settings.mail_from and body["to"] == ["a@b.com"] and body["text"] == "x"


def test_sender_reports_errors_without_raising(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(sender.httpx, "post", lambda *a, **k: httpx.Response(
        403, text="domain not verified", request=httpx.Request("POST", sender.RESEND_URL)))
    result = sender.send(Mail("a@b.com", "x", "<p>x</p>", "x"))
    assert result.status == "failed" and "403" in result.error

    def boom(*a, **k):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(sender.httpx, "post", boom)
    assert sender.send(Mail("a@b.com", "x", "<p>x</p>", "x")).status == "failed"
