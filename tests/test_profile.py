"""Perfil del usuario: nombre, y cambio de clave o de email con un codigo al email actual."""
import re

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import profile

from .test_api import (  # noqa: F401  (admin: fixture)
    ADMIN,
    V1,
    admin,
    client_user,
    make_client,
)
from .test_mail import outbox  # noqa: F401  (outbox: fixture)


@pytest.fixture
def ana(api, admin, outbox):  # noqa: F811
    profile.limiter.reset()
    api.outbox = outbox
    api.ana = client_user(api, admin, make_client(admin))
    return api


def code_of(mail) -> str:
    return re.search(r"\b(\d{6})\b", mail.subject).group(1)


def ask_password_code(api):
    r = api.ana.post(f"{V1}/auth/me/password/code")
    assert r.status_code == 200, r.text
    return r.json()["challenge"], code_of(api.outbox[-1])


def test_update_name(ana):
    r = ana.ana.patch(f"{V1}/auth/me", json={"name": "  Ana Pérez "})
    assert r.status_code == 200 and r.json()["name"] == "Ana Pérez"


def test_change_password(ana):
    other = ana.login("ana@acme.com", "cliente-password-1")
    challenge, code = ask_password_code(ana)
    [mail] = ana.outbox
    assert mail.to == "ana@acme.com" and code in mail.text
    assert code not in challenge
    r = ana.ana.post(f"{V1}/auth/me/password", json={"challenge": challenge, "code": code,
                                                     "password": "nueva-password-1"})
    assert r.status_code == 200, r.text
    # Esta sesion sigue (cookie nueva); las demas se cierran.
    assert ana.ana.get(f"{V1}/auth/me").status_code == 200
    assert other.get(f"{V1}/auth/me").status_code == 401
    ana.login("ana@acme.com", "nueva-password-1")
    assert TestClient(ana.app).post(f"{V1}/auth/login", json={"email": "ana@acme.com",
                                                             "password": "cliente-password-1"}).status_code == 401
    # Un solo uso: la clave cambio.
    r = ana.ana.post(f"{V1}/auth/me/password", json={"challenge": challenge, "code": code,
                                                     "password": "otra-password-12"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_code"


def test_wrong_code_and_attempts(ana, monkeypatch):
    monkeypatch.setattr(settings, "account_code_attempts_15m", 2)
    challenge, code = ask_password_code(ana)
    wrong = f"{(int(code) + 1) % 10**6:06d}"
    body = {"challenge": challenge, "code": wrong, "password": "nueva-password-1"}
    assert ana.ana.post(f"{V1}/auth/me/password", json=body).status_code == 422
    assert ana.ana.post(f"{V1}/auth/me/password", json=body).status_code == 422
    # Agotados los intentos, ni el codigo bueno pasa.
    assert ana.ana.post(f"{V1}/auth/me/password", json={**body, "code": code}).status_code == 429


def test_code_is_per_user_and_purpose(ana, admin):  # noqa: F811
    challenge, code = ask_password_code(ana)
    # El desafio de clave no sirve para el email ni para otro usuario.
    r = ana.ana.post(f"{V1}/auth/me/email", json={"challenge": challenge, "code": code})
    assert r.status_code == 422
    r = admin.post(f"{V1}/auth/me/password", json={"challenge": challenge, "code": code,
                                                   "password": "nueva-password-1"})
    assert r.status_code == 422


def test_code_send_limit(ana, monkeypatch):
    monkeypatch.setattr(settings, "account_code_sends_per_hour", 1)
    ask_password_code(ana)
    assert ana.ana.post(f"{V1}/auth/me/password/code").status_code == 429


def test_mail_failure_is_reported(ana):
    from app.mail.sender import SendResult
    ana.outbox.result = SendResult("failed", error="500")
    r = ana.ana.post(f"{V1}/auth/me/password/code")
    assert r.status_code == 502 and r.json()["code"] == "mail_failed"


def test_change_email(ana):
    r = ana.ana.post(f"{V1}/auth/me/email/code", json={"email": "Ana.Nueva@Acme.com"})
    assert r.status_code == 200, r.text
    challenge = r.json()["challenge"]
    [mail] = ana.outbox
    assert mail.to == "ana@acme.com"            # al email actual
    assert "ana.nueva@acme.com" in mail.text
    r = ana.ana.post(f"{V1}/auth/me/email", json={"challenge": challenge, "code": code_of(mail)})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "ana.nueva@acme.com"
    assert ana.ana.get(f"{V1}/auth/me").json()["email"] == "ana.nueva@acme.com"
    ana.login("ana.nueva@acme.com", "cliente-password-1")
    r = ana.ana.post(f"{V1}/auth/me/email", json={"challenge": challenge, "code": code_of(mail)})
    assert r.status_code == 422                  # un solo uso: el email cambio


def test_change_email_rejects_taken_and_same(ana):
    r = ana.ana.post(f"{V1}/auth/me/email/code", json={"email": ADMIN[0].upper()})
    assert r.status_code == 409 and r.json()["code"] == "email_taken"
    r = ana.ana.post(f"{V1}/auth/me/email/code", json={"email": "ana@acme.com"})
    assert r.status_code == 422 and r.json()["code"] == "same_email"
    assert ana.ana.post(f"{V1}/auth/me/email/code", json={"email": "no-es-email"}).status_code == 422
    assert ana.outbox == []


def test_change_email_taken_meanwhile(ana, admin):  # noqa: F811
    r = ana.ana.post(f"{V1}/auth/me/email/code", json={"email": "luis@acme.com"})
    challenge, code = r.json()["challenge"], code_of(ana.outbox[-1])
    client_user(ana, admin, {"id": ana.ana.get(f"{V1}/auth/me").json()["client_id"]}, email="luis@acme.com")
    r = ana.ana.post(f"{V1}/auth/me/email", json={"challenge": challenge, "code": code})
    assert r.status_code == 409


def test_requires_session(ana):
    r = ana.client.post(f"{V1}/auth/me/password/code")
    assert r.status_code == 401


def test_welcome_popup_once(ana):
    assert ana.ana.get(f"{V1}/auth/me").json()["welcome_pending"] is True
    r = ana.ana.post(f"{V1}/auth/me/welcome")
    assert r.status_code == 200 and r.json()["welcome_pending"] is False
    # Vale para todas las sesiones del usuario, no solo esta.
    assert ana.login("ana@acme.com", "cliente-password-1").get(f"{V1}/auth/me").json()["welcome_pending"] is False
    # El admin no lo ve.
    assert ana.login(*ADMIN).get(f"{V1}/auth/me").json()["welcome_pending"] is False
