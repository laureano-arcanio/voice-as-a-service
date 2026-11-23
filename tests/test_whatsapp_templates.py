"""WhatsApp fase 2: plantillas de la WABA del cliente (listar, crear, editar y borrar, en
vivo desde Meta)."""
import pytest

from app.config import settings
from app.models import Campaign, HandoffArea, WaAccount
from app.services.errors import Invalid
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


def edit(**extra):
    return {"body": "Hola {{1}}, tu turno es el {{2}}.", "examples": ["Juan", "lunes 6"], **extra}


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
    assert r.json() == {"id": "333", "status": "PENDING", "category": "UTILITY"}
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
    # Editar y borrar son de la cuenta que las maneja: otro cliente, 404 sin tocar Meta.
    calls = len(meta.calls)
    assert other.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111", json=edit()).status_code == 404
    assert other.delete(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111").status_code == 404
    assert len(meta.calls) == calls
    assert admin.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").status_code == 200
    assert api.client.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").status_code == 401

    monkeypatch.setattr(settings, "wa_templates_per_hour", 1)
    assert user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl()).status_code == 201
    r = user.post(f"{V1}/whatsapp/accounts/{acc['id']}/templates", json=tpl(name="otra"))
    assert r.status_code == 429
    # Mismo bucket WA_TEMPLATES_PER_HOUR para todas las operaciones con plantillas.
    assert user.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111", json=edit()).status_code == 429
    assert user.delete(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111").status_code == 429


def test_support_admin_edits_and_deletes(admin, meta, account):  # noqa: F811
    """Decisión 3: un admin en soporte (X-Atentina-Client) edita y borra, con el mismo
    permiso que crear (_get_managed)."""
    user, acc = account
    hdr = {"X-Atentina-Client": acc["client_id"]}
    base = f"{V1}/whatsapp/accounts/{acc['id']}/templates/111"
    assert admin.put(base, json=edit(), headers=hdr).status_code == 204
    assert admin.delete(base + "?force=true", headers=hdr).status_code == 204
    names = [t["name"] for t in user.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").json()]
    assert names == ["promo"]


# ---------- editar ----------

def test_edit_template(meta, account):  # noqa: F811
    user, acc = account
    r = user.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111",
                 json=edit(header_text="Turno", footer_text="Atentina"))
    assert r.status_code == 204, r.text
    name, token, template_id, payload = meta.calls[-1]
    assert (name, token, template_id) == ("edit_template", BIZ_TOKEN, "111")
    # En el lugar: ni name ni language (inmutables), y category solo si se pide.
    assert payload == {"components": [
        {"type": "HEADER", "format": "TEXT", "text": "Turno"},
        {"type": "BODY", "text": "Hola {{1}}, tu turno es el {{2}}.",
         "example": {"body_text": [["Juan", "lunes 6"]]}},
        {"type": "FOOTER", "text": "Atentina"}]}
    r = user.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111", json=edit(category="MARKETING"))
    assert r.status_code == 204, r.text
    assert meta.calls[-1][3]["category"] == "MARKETING"


@pytest.mark.parametrize("bad", [
    {"body": "Hola {{1}} y {{3}}", "examples": ["a", "b"]},
    {"examples": ["solo uno"]},
    {"examples": ["Juan", " "]},
    {"header_text": "Hola {{1}}"},
    {"category": "OTRA"},
])
def test_edit_template_validation(meta, account, bad):  # noqa: F811
    user, acc = account
    calls = len(meta.calls)
    r = user.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111", json=edit(**bad))
    assert r.status_code == 422, r.text
    assert len(meta.calls) == calls


def test_edit_template_190_disconnects(api, meta, account):  # noqa: F811
    user, acc = account
    meta.fail["edit_template"] = GraphError("Error validating access token", code=190, status=401)
    r = user.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111", json=edit())
    assert r.status_code == 502 and r.json()["errors"] == [{"meta_code": 190, "meta_subcode": None}]
    (after,) = user.get(f"{V1}/whatsapp/accounts").json()
    assert after["status"] == "disconnected"


def test_meta_error_with_empty_message_falls_back(meta, account):  # noqa: F811
    user, acc = account
    # Bug visto de Meta (100/2388293): error sin message. El 502 nunca lleva detail vacío.
    meta.fail["edit_template"] = GraphError("", code=100, subcode=2388293, status=400)
    r = user.put(f"{V1}/whatsapp/accounts/{acc['id']}/templates/111", json=edit())
    assert r.status_code == 502, r.text
    assert r.json()["detail"] == "Meta rechazó el pedido (código 100/2388293)"
    assert r.json()["errors"] == [{"meta_code": 100, "meta_subcode": 2388293}]


# ---------- borrar ----------

def test_delete_template(meta, account):  # noqa: F811
    user, acc = account
    r = user.delete(f"{V1}/whatsapp/accounts/{acc['id']}/templates/222")
    assert r.status_code == 204, r.text
    # Sin uso: solo lee la plantilla y borra por id, con el token de la cuenta.
    assert meta.calls[-2] == ("get_template", BIZ_TOKEN, "222")
    assert meta.calls[-1] == ("delete_template", BIZ_TOKEN, WABA, "222")
    names = [t["name"] for t in user.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").json()]
    assert names == ["recordatorio"]     # FakeMeta la saca de sus templates


def test_delete_template_in_use(api, meta, account):  # noqa: F811
    user, acc = account
    with api.sessions() as s:
        c = Campaign(client_id=acc["client_id"], channel="whatsapp", account_id=acc["id"], name="Campaña turno",
                     template_name="recordatorio", template_language="es_AR", status="running")
        done = Campaign(client_id=acc["client_id"], channel="whatsapp", account_id=acc["id"], name="Vieja",
                        template_name="recordatorio", template_language="es_AR", status="done")
        area = HandoffArea(client_id=acc["client_id"], name="Consultas", delivery="whatsapp",
                           whatsapp={"account_id": acc["id"], "wait_seconds": 60,
                                     "template": {"name": "recordatorio", "language": "es_AR", "params": []}})
        s.add_all([c, done, area])
        s.commit()
        campaign_id, area_id = c.id, area.id

    base = f"{V1}/whatsapp/accounts/{acc['id']}/templates/111"
    r = user.delete(base)
    assert r.status_code == 409, r.text
    # done/cancelled no cuentan: la campaña viva y el área, con sus nombres.
    assert r.json()["code"] == "template_in_use"
    assert r.json()["detail"] == "La usa: campaña Campaña turno, área Consultas"
    assert r.json()["errors"] == [{"kind": "campaign", "id": campaign_id, "name": "Campaña turno"},
                                 {"kind": "area", "id": area_id, "name": "Consultas"}]
    assert "delete_template" not in meta.names()
    # force borra igual.
    assert user.delete(base + "?force=true").status_code == 204
    assert meta.calls[-1] == ("delete_template", BIZ_TOKEN, WABA, "111")
    names = [t["name"] for t in user.get(f"{V1}/whatsapp/accounts/{acc['id']}/templates").json()]
    assert names == ["promo"]


def test_delete_template_missing(meta, account):  # noqa: F811
    user, acc = account
    r = user.delete(f"{V1}/whatsapp/accounts/{acc['id']}/templates/999")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "not_found"
    assert meta.calls[-1] == ("get_template", BIZ_TOKEN, "999")
    assert "delete_template" not in meta.names()     # no se borró nada en Meta


def test_delete_template_190_disconnects(api, meta, account):  # noqa: F811
    user, acc = account
    meta.fail["delete_template"] = GraphError("Error validating access token", code=190, status=401)
    r = user.delete(f"{V1}/whatsapp/accounts/{acc['id']}/templates/222")
    assert r.status_code == 502 and r.json()["errors"][0]["meta_code"] == 190
    (after,) = user.get(f"{V1}/whatsapp/accounts").json()
    assert after["status"] == "disconnected" and after["status_reason"] == "token_invalid code=190"


async def test_delete_template_rejects_non_numeric_id(api, meta, account):  # noqa: F811
    """Por id (hsm_ids): sin número no se llama a Meta. (Por la API, get_template ya lo
    responde con el 404 de Meta.)"""
    _, acc = account
    calls = len(meta.calls)
    with api.sessions() as s, pytest.raises(Invalid):
        await signup.delete_template(s, s.get(WaAccount, acc["id"]), "no-numero")
    assert len(meta.calls) == calls


def test_template_payload_helper():
    p = signup.template_payload(name="a", language="es_AR", category="MARKETING", body="Hola {{1}} {{1}}",
                                examples=["Ana"])
    assert p["components"] == [{"type": "BODY", "text": "Hola {{1}} {{1}}", "example": {"body_text": [["Ana"]]}}]
    e = signup.template_edit_payload(body="Hola {{1}}", examples=["Ana"])
    assert e == {"components": [{"type": "BODY", "text": "Hola {{1}}", "example": {"body_text": [["Ana"]]}}]}
    e = signup.template_edit_payload(category="UTILITY", body="Chau", examples=[])
    assert e == {"category": "UTILITY", "components": [{"type": "BODY", "text": "Chau"}]}
