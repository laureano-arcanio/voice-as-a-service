"""Roles dentro del cliente en la API y el MCP (docs/features/EQUIPO_TELEFONIA.md): el Usuario no escribe lo
que es solo de Admin; la sesión, la API key, el admin en soporte y el MCP de cada uno."""
import pytest

from .test_api import V1, admin, client_user, make_client  # noqa: F401  (admin: fixture)
from .test_oauth import connect, mcp, setup  # noqa: F401  (setup: fixture)

CID = "{cid}"
AGENT = "{aid}"

# (método, ruta, cuerpo). Las rutas con ids falsos alcanzan para el permiso: lo que se prueba es el 403.
ROUTES = [
    # Plan y cobros: Admin con sesión del panel (la API key no crea keys ni cobra).
    ("GET", "/clients/{cid}/billing", None, True, True),
    ("POST", "/clients/{cid}/billing/subscribe", {"tier_id": "x", "method": "transfer"}, True, False),
    ("POST", "/clients/{cid}/billing/cancel", None, True, False),
    ("PUT", "/clients/{cid}/billing/fiscal", {"legal_name": "A", "tax_id": "20123456789", "tax_condition": "ri"},
     True, False),
    # API keys.
    ("GET", "/clients/{cid}/api-keys", None, True, True),
    ("POST", "/clients/{cid}/api-keys", {"name": "x"}, True, True),
    ("DELETE", "/clients/{cid}/api-keys/nope", None, True, True),
    # Conexiones de LLM (la escritura).
    ("POST", "/clients/{cid}/llm-connections", {"name": "x", "kind": "openai_compatible", "api_key": "k"}, False, True),
    ("PATCH", "/clients/{cid}/llm-connections/nope", {"name": "y"}, False, True),
    ("DELETE", "/clients/{cid}/llm-connections/nope", None, False, True),
    # Herramientas, secretos y credenciales.
    ("POST", "/clients/{cid}/tools", {"name": "x", "type": "http", "definition": {}}, False, True),
    ("PUT", "/clients/{cid}/tools/x", {"definition": {}}, False, True),
    ("DELETE", "/clients/{cid}/tools/x", None, False, True),
    ("POST", "/clients/{cid}/tools/test", {"type": "http", "definition": {}, "args": {}}, False, True),
    ("POST", "/clients/{cid}/secrets", {"name": "x", "value": "v"}, False, True),
    ("PATCH", "/clients/{cid}/secrets/x", {"value": "v"}, False, True),
    ("DELETE", "/clients/{cid}/secrets/x", None, False, True),
    ("POST", "/clients/{cid}/credentials", {"slug": "x", "name": "X", "auth": {"type": "bearer", "secret": "s"}},
     False, True),
    ("PUT", "/clients/{cid}/credentials/x", {"name": "Y"}, False, True),
    ("DELETE", "/clients/{cid}/credentials/x", None, False, True),
    ("POST", "/agents/{aid}/secrets", {"name": "x", "value": "v"}, False, True),
    ("PATCH", "/agents/{aid}/secrets/x", {"value": "v"}, False, True),
    ("POST", "/agents/{aid}/secrets/x/promote", None, False, True),
    ("DELETE", "/agents/{aid}/secrets/x", None, False, True),
    # Agentes.
    ("POST", "/agents", {"name": "X"}, False, True),
    ("PATCH", "/agents/{aid}", {"name": "Y"}, False, True),
    ("PUT", "/agents/{aid}/definition", {"definition": {}}, False, True),
    ("DELETE", "/agents/{aid}", None, False, True),
    # Números, aviso de grabación y retención del contenido.
    ("PATCH", "/phone-numbers/nope", {"label": "x"}, False, True),
    ("PUT", "/clients/{cid}/direct-call-settings", {"recording_notice": True}, False, True),
    ("PUT", "/clients/{cid}/api-content", {"enabled": True, "retention_days": 30}, True, True),
    # Campañas de voz.
    ("POST", "/campaigns", {"name": "x", "channel": "voice"}, False, True),
    ("PATCH", "/campaigns/nope", {"name": "y"}, False, True),
    ("DELETE", "/campaigns/nope", None, False, True),
    ("POST", "/campaigns/nope/contacts", {"contacts": []}, False, True),
    ("POST", "/campaigns/nope/start", None, False, True),
    ("POST", "/campaigns/nope/resume", None, False, True),
    ("POST", "/campaigns/nope/pause", None, False, True),
    ("POST", "/campaigns/nope/cancel", None, False, True),
    # Campañas de WhatsApp y sus bajas.
    ("POST", "/whatsapp/campaigns", {"name": "x", "account_id": "a", "template": {}}, False, True),
    ("PATCH", "/whatsapp/campaigns/nope", {"name": "y"}, False, True),
    ("DELETE", "/whatsapp/campaigns/nope", None, False, True),
    ("POST", "/whatsapp/campaigns/nope/recipients", {"recipients": []}, False, True),
    ("POST", "/whatsapp/campaigns/nope/start", None, False, True),
    ("POST", "/whatsapp/campaigns/nope/pause", None, False, True),
    ("POST", "/whatsapp/campaigns/nope/cancel", None, False, True),
    ("POST", "/whatsapp/optouts", {"wa_id": "5493516775617"}, False, True),
    ("DELETE", "/whatsapp/optouts/5493516775617", None, False, True),
    # Contactos: importar, archivar en lote y bajas.
    ("POST", "/contacts/import", {"csv": "telefono,nombre\n"}, False, True),
    ("POST", "/contacts/archive", {"contact_ids": ["nope"]}, False, True),
    ("POST", "/contacts/optouts", {"phone": "+5493516775617"}, False, True),
    ("DELETE", "/contacts/optouts/+5493516775617", None, False, True),
    # La cuenta de WhatsApp.
    ("POST", "/whatsapp/accounts", {"waba_id": "w", "name": "x", "access_token": "t"}, False, True),
    ("PATCH", "/whatsapp/accounts/nope", {"name": "y"}, False, True),
    ("POST", "/whatsapp/accounts/nope/deactivate", None, False, True),
    ("PUT", "/whatsapp/accounts/nope/routes", [], False, True),
    ("POST", "/whatsapp/accounts/own-app", {"waba_id": "w", "phone_number_id": "p", "access_token": "t"},
     False, True),
    ("POST", "/whatsapp/signup", {"waba_id": "w", "phone_number_id": "p", "access_token": "t"}, False, True),
    ("POST", "/whatsapp/accounts/nope/register", {"pin": "123456"}, False, True),
    ("POST", "/whatsapp/accounts/nope/refresh", None, False, True),
]


@pytest.fixture
def roles(api, admin):
    c = make_client(admin, outbound_minutes=300, campaign_channels=["voice"], max_tools=5, max_team_members=5)
    admin_user = client_user(api, admin, c)
    user = client_user(api, admin, c, email="operador@acme.com", client_role="user")
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "crm"}).json()["key"]
    return {"client": c, "admin": admin_user, "user": user, "key": key, "platform": admin,
            "support": {"X-Atentina-Client": c["id"]}}


def url(path, roles):
    return f"{V1}{path.format(cid=roles['client']['id'], aid='nope')}"


def call(client, method, path, body, **kw):
    return client.request(method, url(path, roles=kw["roles"]), json=body, headers=kw.get("headers"))


def test_every_admin_only_route_by_principal(roles):
    for method, path, body, session_only, support_ok in ROUTES:
        r = call(roles["user"], method, path, body, roles=roles)
        assert (r.status_code, r.json().get("code")) == (403, "client_admin_required"), (method, path, r.text)
        r = call(roles["admin"], method, path, body, roles=roles)
        assert r.status_code not in (401, 403), (method, path, r.text)
        r = call(roles["platform"], method, path, body, roles=roles, headers=roles["support"])
        if support_ok:
            assert r.status_code not in (401, 403), (method, path, r.text)
        else:
            assert (r.status_code, r.json().get("code")) == (403, "support_read_only"), (method, path, r.text)


def test_api_key_is_admin_but_not_for_keys_or_billing(api, roles):
    headers = {"Authorization": f"Bearer {roles['key']}"}
    for method, path, body, session_only, _ in ROUTES:
        r = call(roles["admin"], method, path, body, roles=roles, headers=headers)
        if session_only:
            assert r.status_code == 403, (method, path, r.text)
        else:
            assert r.status_code not in (401, 403), (method, path, r.text)


def test_a_user_still_does_the_daily_work(api, roles):
    user, c = roles["user"], roles["client"]
    ok = [("GET", "/team"), ("GET", "/handoff-areas"), ("GET", "/agents"), ("GET", "/phone-numbers"),
          ("GET", "/contacts"), ("GET", "/campaigns"), ("GET", "/whatsapp/campaigns"),
          ("GET", "/clients/{cid}/llm-connections"), ("GET", "/clients/{cid}/api-content"),
          ("GET", "/clients/{cid}/direct-call-settings"), ("GET", "/reports/calls"),
          ("GET", "/plan/features")]
    for method, path in ok:
        r = user.request(method, url(path, roles))
        assert r.status_code == 200, (path, r.text)
    # Validar y ver el prompt del agente son lecturas por POST: para todos.
    r = user.post(f"{V1}/agents/validate", json={"definition": {}})
    assert r.status_code not in (401, 403)
    # Un contacto de a uno sí; importar o archivar en lote y las bajas, no.
    assert user.post(f"{V1}/contacts", json={"phone": "+5493516775617", "name": "Juan"}).status_code == 201
    assert user.post(f"{V1}/contacts", json=[{"phone": "+5493516775617"}]).status_code in (200, 201)
    assert user.post(f"{V1}/contacts/import", json={"csv": "telefono\n+5493516775618\n"}).status_code == 403
    assert user.post(f"{V1}/contacts/archive", json={"contact_ids": ["x"]}).status_code == 403
    assert user.post(f"{V1}/contacts/optouts", json={"phone": "+5493516775619"}).status_code == 403


def test_mcp_hides_and_rejects_admin_only_tools_for_a_user(api, setup, monkeypatch):  # noqa: F811
    c, agent, user, _ = setup
    from app.models import User

    with api.sessions() as s:   # el usuario del permiso es un Usuario del cliente
        s.get(User, user.get(f"{V1}/auth/me").json()["id"]).client_role = "user"
        s.commit()
    access = connect(api, (c, agent, user, setup[3]))["access_token"]
    tools = {t["name"] for t in mcp(api, access, method="tools/list").json()["result"]["tools"]}
    assert "create_agent" not in tools and "start_campaign" not in tools and "create_llm_connection" not in tools
    assert {"list_agents", "list_team", "list_campaigns"} <= tools
    out = mcp(api, access, params={"name": "create_agent", "arguments": {}}).json()
    assert "desconocida" in out["error"]["message"]

    # El mismo usuario como Admin del cliente (el rol se relee en cada pedido) sí las ve.
    with api.sessions() as s:
        s.get(User, user.get(f"{V1}/auth/me").json()["id"]).client_role = "admin"
        s.commit()
    tools = {t["name"] for t in mcp(api, access, method="tools/list").json()["result"]["tools"]}
    assert {"create_agent", "create_llm_connection"} <= tools
