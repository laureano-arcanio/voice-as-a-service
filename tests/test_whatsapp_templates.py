"""WhatsApp fase 2: plantillas de la WABA del cliente (listar y crear, en vivo desde Meta)."""
import pytest

from app.config import settings
from app.whatsapp import signup
from app.whatsapp.graph import GraphError

from .test_api import V1, client_user, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_signup import (  # noqa: F401  (fixtures)
    BIZ_TOKEN,
    WABA,
    acme,
    meta,
    signup_ok,
)


@pytest.fixture
def account(meta, acme):  # noqa: F811
    _, agent, user = acme
    return user, signup_ok(user, agent)


def tpl(**extra):
    return {"name": "recordatorio_turno", "language": "es_AR", "category": "UTILITY",
            "body": "Hola {{1}}, te esperamos el {{2}}.", "examples": ["Juan", "lunes 6"], **extra}


def test_list_templates(meta, account):  # noqa: F811
    user, acc = account
    r = user.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates")
    assert r.status_code == 200, r.text
    assert [(t["name"], t["status"], t["rejected_reason"]) for t in r.json()] == [
        ("recordatorio", "APPROVED", None), ("promo", "REJECTED", "PROMOTIONAL")]
    assert meta.calls[-1] == ("list_templates", BIZ_TOKEN, WABA)


def test_create_template_payload(meta, account):  # noqa: F811
    user, acc = account
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates",
                  json=tpl(header_text="Turno", footer_text="Atentina"))
    assert r.status_code == 201, r.text
    assert r.json() == {"id": "t3", "status": "PENDING", "category": "UTILITY"}
    name, token, waba, payload = meta.calls[-1]
    assert (name, token, waba) == ("create_template", BIZ_TOKEN, WABA)
    assert payload == {
        "name": "recordatorio_turno", "language": "es_AR", "category": "UTILITY",
        "components": [
            {"type": "HEADER", "format": "TEXT", "text": "Turno"},
            {"type": "BODY", "text": "Hola {{1}}, te esperamos el {{2}}.",
             "example": {"body_text": [["Juan", "lunes 6"]]}},
            {"type": "FOOTER", "text": "Atentina"},
        ]}
    # Sin variables: sin example.
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl(body="Gracias", examples=[]))
    assert r.status_code == 201
    assert "example" not in meta.calls[-1][3]["components"][0]


@pytest.mark.parametrize("bad", [
    {"name": "Con Mayusculas"},
    {"category": "OTRA"},
    {"examples": ["solo uno"]},
    {"body": "Hola {{1}} y {{3}}", "examples": ["a", "b"]},
    {"examples": ["Juan", " "]},
    {"header_text": "Hola {{1}}"},
    {"body": "x" * 1025},
])
def test_create_template_validation(meta, account, bad):  # noqa: F811
    user, acc = account
    calls = len(meta.calls)
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl(**bad))
    assert r.status_code == 422, r.text
    assert len(meta.calls) == calls


def test_templates_meta_error_and_190(meta, account):  # noqa: F811
    user, acc = account
    meta.fail["create_template"] = GraphError("Template name already exists", code=100, subcode=2388023, status=400)
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl())
    assert r.status_code == 502 and r.json()["errors"] == [{"meta_code": 100, "meta_subcode": 2388023}]
    assert "already exists" in r.json()["detail"]
    meta.fail["list_templates"] = GraphError("Error validating access token", code=190, status=401)
    assert user.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").status_code == 502
    (after,) = user.get(f"{V1}/whatsapp/accounts").json()
    assert after["status"] == "disconnected"


def test_templates_tenant_and_rate_limit(api, admin, meta, account, monkeypatch):  # noqa: F811
    user, acc = account
    other = client_user(api, admin, make_client(admin, slug="otro"), email="b@otro.com")
    assert other.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").status_code == 404
    assert other.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl()).status_code == 404
    assert admin.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").status_code == 200
    assert api.client.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").status_code == 401

    monkeypatch.setattr(settings, "wa_templates_per_hour", 1)
    assert user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl()).status_code == 201
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl(name="otra"))
    assert r.status_code == 429


def test_template_payload_helper():
    p = signup.template_payload(name="a", language="es_AR", category="MARKETING", body="Hola {{1}} {{1}}",
                                examples=["Ana"])
    assert p["components"] == [{"type": "BODY", "text": "Hola {{1}} {{1}}", "example": {"body_text": [["Ana"]]}}]
