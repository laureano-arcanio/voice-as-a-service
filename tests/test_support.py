"""Ver como cliente: un admin con X-Atentina-Client actua como ese cliente (docs/ADMIN_SOPORTE_PLAN.md)."""
from app.agents.templates import reference_data

from .test_api import (  # noqa: F401 (admin: fixture)
    ADMIN,
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
)

HDR = "X-Atentina-Client"


def as_client(client):
    return {HDR: client["id"]}


def two_clients(admin):  # noqa: F811
    a, b = make_client(admin, "acme"), make_client(admin, "otro")
    return a, b


# ---------- el principal de soporte ----------

def test_admin_with_header_acts_as_that_client(api, admin):  # noqa: F811
    a, b = two_clients(admin)
    agent_a, agent_b = make_agent(admin, a), make_agent(admin, b)
    h = as_client(a)
    me = admin.get(f"{V1}/auth/me", headers=h).json()
    assert me["role"] == "client" and me["client_id"] == a["id"] and me["support"] is True
    assert me["email"] == ADMIN[0] and me["client_name"] == a["name"]
    # Sin el header sigue siendo el admin.
    plain = admin.get(f"{V1}/auth/me").json()
    assert plain["role"] == "admin" and plain["client_id"] is None and not plain.get("support")

    listed = admin.get(f"{V1}/agents", headers=h).json()
    assert [x["id"] for x in listed] == [agent_a["id"]]
    assert admin.get(f"{V1}/agents/{agent_a['id']}", headers=h).status_code == 200
    # El agente de otro cliente: 404, como para el cliente.
    assert admin.get(f"{V1}/agents/{agent_b['id']}", headers=h).status_code == 404


def test_admin_in_support_creates_agent_in_that_client(api, admin):  # noqa: F811
    a, _ = two_clients(admin)
    r = admin.post(f"{V1}/agents", json={"name": "Recepción", "template_id": "asistente"}, headers=as_client(a))
    assert r.status_code == 201, r.text
    assert r.json()["client_id"] == a["id"]
    # Sin el header, el admin necesita client_id.
    assert admin.post(f"{V1}/agents", json={"name": "Otro", "template_id": "asistente"}).status_code == 422


def test_unknown_client_in_header_is_404(api, admin):  # noqa: F811
    r = admin.get(f"{V1}/agents", headers={HDR: "no-existe"})
    assert r.status_code == 404 and r.json()["code"] == "client_not_found"
    assert admin.get(f"{V1}/auth/me", headers={HDR: "no-existe"}).status_code == 404


def test_header_is_ignored_by_client_users_and_api_keys(api, admin):  # noqa: F811
    a, b = two_clients(admin)
    agent_a, agent_b = make_agent(admin, a), make_agent(admin, b)
    user = client_user(api, admin, a)
    me = user.get(f"{V1}/auth/me", headers=as_client(b)).json()
    assert me["client_id"] == a["id"] and not me.get("support")
    assert [x["id"] for x in user.get(f"{V1}/agents", headers=as_client(b)).json()] == [agent_a["id"]]
    assert user.get(f"{V1}/agents/{agent_b['id']}", headers=as_client(b)).status_code == 404

    key = admin.post(f"{V1}/clients/{a['id']}/api-keys", json={"name": "crm"}).json()["key"]
    auth = {"Authorization": f"Bearer {key}", **as_client(b)}
    r = api.client.get(f"{V1}/agents", headers=auth)
    assert r.status_code == 200 and [x["id"] for x in r.json()] == [agent_a["id"]]
    assert api.client.get(f"{V1}/agents/{agent_b['id']}", headers=auth).status_code == 404
    # Ni siquiera un cliente inexistente en el header los afecta.
    assert api.client.get(f"{V1}/agents", headers={"Authorization": f"Bearer {key}", HDR: "no-existe"}).status_code == 200


# ---------- solo lectura: cuenta y cobros ----------

def test_account_and_billing_are_read_only_in_support(api, admin):  # noqa: F811
    a, _ = two_clients(admin)
    h = as_client(a)
    cid = a["id"]
    checks = [
        admin.patch(f"{V1}/auth/me", json={"name": "Otro"}, headers=h),
        admin.post(f"{V1}/auth/me/legal", json={}, headers=h),
        admin.post(f"{V1}/clients/{cid}/billing/subscribe", json={"tier_id": a["tier"]["id"]}, headers=h),
        admin.post(f"{V1}/clients/{cid}/billing/cancel", headers=h),
        admin.put(f"{V1}/clients/{cid}/billing/fiscal", headers=h,
                  json={"legal_name": "Acme SA", "tax_id": "30123456789", "tax_condition": "ri"}),
    ]
    for r in checks:
        assert r.status_code == 403 and r.json()["code"] == "support_read_only", (r.request.url, r.text)
    # El nombre del admin no cambió.
    assert admin.get(f"{V1}/auth/me").json()["name"] != "Otro"


def test_call_emails_still_editable_in_support(api, admin):  # noqa: F811
    a, _ = two_clients(admin)
    r = admin.put(f"{V1}/clients/{a['id']}/call-emails", json={"enabled": False, "recipients": ["ana@acme.com"]},
                  headers=as_client(a))
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is False and r.json()["recipients"] == ["ana@acme.com"]


# ---------- en soporte no es admin ----------

def test_support_is_not_admin(api, admin):  # noqa: F811
    a, _ = two_clients(admin)
    h = as_client(a)
    assert [c["slug"] for c in admin.get(f"{V1}/clients", headers=h).json()] == ["acme"]
    assert admin.post(f"{V1}/tiers", json={"name": "Nuevo"}, headers=h).status_code == 403
    assert admin.get(f"{V1}/tiers", headers=h).status_code == 403
    assert admin.post(f"{V1}/clients", json={"name": "X", "slug": "x", "tier_id": a["tier"]["id"]},
                      headers=h).status_code == 403
    # Sin el header, sigue administrando.
    assert len(admin.get(f"{V1}/clients").json()) == 2


# ---------- lo que se abrió al cliente ----------

def test_client_user_can_preview_prompt(api, admin):  # noqa: F811
    a = make_client(admin)
    user = client_user(api, admin, a)
    definition = reference_data("sales_discovery")
    r = user.post(f"{V1}/agents/prompt", json={"definition": definition})
    assert r.status_code == 200, r.text
    assert r.json()["system"]


def test_llm_connection_urls_must_be_public_https_even_for_admin(api, admin):  # noqa: F811
    a = make_client(admin)
    url = f"{V1}/clients/{a['id']}/llm-connections"
    body = {"name": "propio", "kind": "openai_compatible", "api_key": "k", "default_model": "m"}
    for bad in ("http://vllm-llm:8000/v1", "http://api.example.com/v1", "https://10.0.0.5/v1",
                "https://127.0.0.1:8000/v1"):
        r = admin.post(url, json={**body, "base_url": bad})
        assert r.status_code == 422 and r.json()["code"] == "invalid_base_url", bad
        # También como admin en soporte.
        r = admin.post(url, json={**body, "base_url": bad}, headers=as_client(a))
        assert r.status_code == 422 and r.json()["code"] == "invalid_base_url", bad
    assert admin.post(url, json={**body, "base_url": "https://8.8.8.8/v1"}).status_code == 201
