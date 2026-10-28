"""OAuth 2.1 del servidor MCP (docs/features/MCP.md): metadata, registro, consentimiento, PKCE,
tokens con rotación, revocación y el uso del token en /mcp (y solo ahí)."""
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import pytest

from app.services import oauth

from .test_api import ADMIN, V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)

REDIRECT = "http://127.0.0.1:33418/callback"
RESOURCE = "http://testserver/mcp"


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def register(api, **meta):
    r = api.client.post("/oauth/register", json={"redirect_uris": [REDIRECT], "client_name": "Claude Code", **meta})
    assert r.status_code == 201, r.text
    return r.json()


def auth_params(client_id, challenge, **extra):
    return {"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT, "code_challenge": challenge,
            "code_challenge_method": "S256", "state": "xyz", "scope": "mcp", "resource": RESOURCE, **extra}


def authorize(user, params, **body):
    r = user.post(f"{V1}/oauth/authorize", json={"params": params, "approve": True, **body})
    assert r.status_code == 200, r.text
    return r.json()["redirect_to"]


def code_of(url):
    q = parse_qs(urlparse(url).query)
    assert q["state"] == ["xyz"] and q["iss"] == ["http://testserver"], q
    return q["code"][0]


def token(api, **form):
    return api.client.post("/oauth/token", data=form)


def mcp(api, access, method="tools/call", params=None, toolsets="all"):
    return api.client.post(f"/mcp?toolsets={toolsets}", headers={"Authorization": f"Bearer {access}"},
                           json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})


def call(api, access, name, **arguments):
    r = mcp(api, access, params={"name": name, "arguments": arguments})
    assert r.status_code == 200, r.text
    return r.json()["result"]


@pytest.fixture
def setup(api, admin):
    """Cliente con un agente, un usuario con sesión y un cliente OAuth registrado."""
    c = make_client(admin)
    agent = make_agent(admin, c)
    user = client_user(api, admin, c)
    return c, agent, user, register(api)


def connect(api, setup):
    """El flujo completo: autorizar, canjear el código. Devuelve los tokens."""
    _, _, user, app_client = setup
    verifier, challenge = pkce()
    code = code_of(authorize(user, auth_params(app_client["client_id"], challenge)))
    r = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT, client_id=app_client["client_id"],
              code_verifier=verifier, resource=RESOURCE)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    return r.json()


# ---------- metadata y descubrimiento ----------

def test_metadata_and_discovery(api):
    pr = api.client.get("/.well-known/oauth-protected-resource/mcp").json()
    assert pr["resource"] == RESOURCE and pr["authorization_servers"] == ["http://testserver"]
    assert api.client.get("/.well-known/oauth-protected-resource").json() == pr
    meta = api.client.get("/.well-known/oauth-authorization-server").json()
    assert meta["token_endpoint"] == "http://testserver/oauth/token"
    assert meta["code_challenge_methods_supported"] == ["S256"] and meta["client_id_metadata_document_supported"]
    r = api.client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == ('Bearer resource_metadata='
                                             '"http://testserver/.well-known/oauth-protected-resource/mcp"')


def test_authorize_redirects_to_the_consent_page(api):
    r = api.client.get("/oauth/authorize?client_id=x&state=1", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/oauth/consent?client_id=x&state=1"


# ---------- flujo completo ----------

def test_full_flow_and_the_token_works_only_on_mcp(api, setup):
    c, agent, user, app_client = setup
    _, challenge = pkce()
    info = user.get(f"{V1}/oauth/authorize", params=auth_params(app_client["client_id"], challenge)).json()
    assert info["valid"] and info["client_name"] == "Claude Code" and info["redirect_host"] == "127.0.0.1"
    assert info["needs_client"] is False and info["client_id"] == c["id"] and not info["verified"]
    tokens = connect(api, setup)
    assert tokens["access_token"].startswith("vaat_") and tokens["refresh_token"].startswith("vaar_")
    assert tokens["token_type"] == "Bearer" and tokens["expires_in"] == 3600
    access = tokens["access_token"]
    agents = call(api, access, "list_agents")["structuredContent"]["items"]
    assert [a["id"] for a in agents] == [agent["id"]]
    # Con OAuth también andan las que exigen sesión de usuario.
    billing = call(api, access, "get_billing")
    assert not billing.get("isError"), billing
    plan = call(api, access, "get_plan_tools")["structuredContent"]
    assert plan["tools"]["needs_oauth"] == [] and "get_billing" in plan["tools"]["available"]
    # El token no abre la API desde afuera: solo vale para /mcp.
    r = api.client.get(f"{V1}/agents", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 401 and "MCP" in r.json()["detail"]
    # Ni para autorizar otros agentes.
    grants = user.get(f"{V1}/oauth/grants").json()
    assert len(grants) == 1 and grants[0]["app_name"] == "Claude Code" and grants[0]["user_email"] == "ana@acme.com"


def test_api_key_is_told_to_use_oauth_for_session_tools(api, admin, setup):
    c, _, _, _ = setup
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "k", "scopes": ["mcp"]}).json()["key"]
    out = call(api, key, "get_billing")
    assert out["isError"] and out["structuredContent"]["code"] == "needs_oauth"
    assert "get_billing" in call(api, key, "get_plan_tools")["structuredContent"]["tools"]["needs_oauth"]


def test_deny_returns_access_denied(api, setup):
    _, _, user, app_client = setup
    _, challenge = pkce()
    r = user.post(f"{V1}/oauth/authorize", json={"params": auth_params(app_client["client_id"], challenge),
                                                  "approve": False})
    q = parse_qs(urlparse(r.json()["redirect_to"]).query)
    assert q["error"] == ["access_denied"] and q["state"] == ["xyz"] and "code" not in q


# ---------- validaciones ----------

def test_bad_requests(api, setup):
    _, _, user, app_client = setup
    cid = app_client["client_id"]
    _, challenge = pkce()
    # redirect_uri ajeno: no se redirige (podría ser de un atacante).
    info = user.get(f"{V1}/oauth/authorize",
                    params=auth_params(cid, challenge, redirect_uri="https://evil.example/cb")).json()
    assert not info["valid"] and info["redirect_to"] is None
    # Loopback con otro puerto: vale (RFC 8252).
    assert user.get(f"{V1}/oauth/authorize", params=auth_params(
        cid, challenge, redirect_uri="http://127.0.0.1:5555/callback")).json()["valid"]
    # Sin PKCE, otro recurso u otro alcance: se devuelve el error al cliente.
    for extra, error in (({"code_challenge_method": "plain"}, "invalid_request"),
                         ({"resource": "https://otro.example/mcp"}, "invalid_target"),
                         ({"scope": "admin"}, "invalid_scope")):
        info = user.get(f"{V1}/oauth/authorize", params=auth_params(cid, challenge, **extra)).json()
        assert not info["valid"] and info["error"] == error
        assert parse_qs(urlparse(info["redirect_to"]).query)["error"] == [error]
    assert not user.get(f"{V1}/oauth/authorize", params=auth_params("desconocido", challenge)).json()["valid"]
    # Sin sesión no hay consentimiento.
    assert api.client.get(f"{V1}/oauth/authorize", params=auth_params(cid, challenge)).status_code == 401


def test_register_validates_redirect_uris(api):
    for uris in ([], ["http://evil.example/cb"], ["javascript:alert(1)"], ["https://x.example/cb#frag"]):
        r = api.client.post("/oauth/register", json={"redirect_uris": uris})
        assert r.status_code == 400 and r.json()["error"] == "invalid_redirect_uri", uris
    assert register(api, redirect_uris=["cursor://anysphere.cursor-retrieval/oauth/callback"])["client_id"]


def test_code_is_single_use_and_bound_to_pkce(api, setup):
    _, _, user, app_client = setup
    cid = app_client["client_id"]
    verifier, challenge = pkce()
    code = code_of(authorize(user, auth_params(cid, challenge)))
    r = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT, client_id=cid,
              code_verifier="x" * 50)
    assert r.json()["error"] == "invalid_grant"
    ok = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT, client_id=cid,
               code_verifier=verifier)
    assert ok.status_code == 200
    # Reusar el código corta el permiso entero, también el token ya emitido.
    again = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT, client_id=cid,
                  code_verifier=verifier)
    assert again.json()["error"] == "invalid_grant"
    assert mcp(api, ok.json()["access_token"]).status_code == 401


def test_refresh_rotates_and_reuse_revokes(api, setup):
    _, _, _, app_client = setup
    first = connect(api, setup)
    cid = app_client["client_id"]
    second = token(api, grant_type="refresh_token", refresh_token=first["refresh_token"], client_id=cid).json()
    assert second["access_token"] != first["access_token"]
    assert not call(api, second["access_token"], "whoami").get("isError")
    reuse = token(api, grant_type="refresh_token", refresh_token=first["refresh_token"], client_id=cid)
    assert reuse.json()["error"] == "invalid_grant"
    assert mcp(api, second["access_token"]).status_code == 401


def test_revocation_endpoint_and_ui(api, setup):
    _, _, user, app_client = setup
    tokens = connect(api, setup)
    r = api.client.post("/oauth/revoke", data={"token": tokens["refresh_token"], "client_id": app_client["client_id"]})
    assert r.status_code == 200
    assert mcp(api, tokens["access_token"]).status_code == 401
    assert user.get(f"{V1}/oauth/grants").json() == []
    tokens = connect(api, setup)
    grant = user.get(f"{V1}/oauth/grants").json()[0]
    assert user.delete(f"{V1}/oauth/grants/{grant['id']}").status_code == 204
    assert mcp(api, tokens["access_token"]).status_code == 401


def test_logout_everywhere_cuts_the_agent(api, setup):
    _, _, user, _ = setup
    tokens = connect(api, setup)
    assert user.post(f"{V1}/auth/logout").status_code == 204   # sube session_version
    assert mcp(api, tokens["access_token"]).status_code == 401


def test_token_is_bound_to_its_resource(api, setup):
    tokens = connect(api, setup)
    r = api.client.post("/mcp", headers={"Authorization": f"Bearer {tokens['access_token']}", "Host": "otro.example"},
                        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401


def test_resource_with_toolsets_is_the_same_server(api, setup):
    """El cliente puede mandar como resource la URL que le cargaron, con ?toolsets=; otro path no vale."""
    _, _, user, app_client = setup
    verifier, challenge = pkce()
    code = code_of(authorize(user, auth_params(app_client["client_id"], challenge, resource=RESOURCE + "?toolsets=all")))
    r = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT, client_id=app_client["client_id"],
              code_verifier=verifier, resource=RESOURCE + "?toolsets=all")
    assert r.status_code == 200, r.text
    assert mcp(api, r.json()["access_token"], "tools/list").status_code == 200
    _, challenge = pkce()
    bad = authorize(user, auth_params(app_client["client_id"], challenge, resource=RESOURCE + "/otro"))
    assert "invalid_target" in bad


def test_other_clients_user_cannot_pick_a_client(api, admin, setup):
    _, _, user, app_client = setup
    other = make_client(admin, slug="otra")
    _, challenge = pkce()
    r = user.post(f"{V1}/oauth/authorize", json={"params": auth_params(app_client["client_id"], challenge),
                                                  "approve": True, "client_id": other["id"]})
    assert r.status_code == 403


def test_admin_picks_the_client_and_acts_as_it(api, admin, setup):
    c, agent, _, app_client = setup
    other = make_client(admin, slug="otra")
    make_agent(admin, other)
    verifier, challenge = pkce()
    params = auth_params(app_client["client_id"], challenge)
    assert admin.get(f"{V1}/oauth/authorize", params=params).json()["needs_client"] is True
    assert admin.post(f"{V1}/oauth/authorize", json={"params": params, "approve": True}).status_code == 403
    code = code_of(authorize(admin, params, client_id=c["id"]))
    access = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT,
                   client_id=app_client["client_id"], code_verifier=verifier).json()["access_token"]
    # Solo ve los agentes del cliente elegido, aunque sea admin.
    assert [a["id"] for a in call(api, access, "list_agents")["structuredContent"]["items"]] == [agent["id"]]
    assert ADMIN[0] in [g["user_email"] for g in admin.get(f"{V1}/oauth/grants").json()]


def test_admin_platform_grant_sees_every_tool(api, admin, setup):
    """Fase 5: un admin que autoriza "Toda la plataforma" actúa como admin, con el toolset admin y todas las
    de cliente (elige el cliente en cada llamada); un usuario de cliente no puede pedirlo."""
    c, agent, user, app_client = setup
    _, challenge = pkce()
    denied = user.post(f"{V1}/oauth/authorize", json={"params": auth_params(app_client["client_id"], challenge),
                                                      "approve": True, "platform": True})
    assert denied.status_code == 403
    verifier, challenge = pkce()
    code = code_of(authorize(admin, auth_params(app_client["client_id"], challenge), platform=True))
    access = token(api, grant_type="authorization_code", code=code, redirect_uri=REDIRECT,
                   client_id=app_client["client_id"], code_verifier=verifier).json()["access_token"]
    tools = {t["name"]: t for t in mcp(api, access, "tools/list").json()["result"]["tools"]}
    assert {"admin_list_clients", "whoami", "list_agents", "get_plan_tools"} <= set(tools)
    # Las de cliente piden el cliente; whoami y las de admin, no (las de admin lo traen donde hace falta).
    assert tools["list_agents"]["inputSchema"]["required"][0] == "client_id"
    assert "client_id" not in tools["whoami"]["inputSchema"]["properties"]
    assert "client_id" not in tools["admin_list_clients"]["inputSchema"]["properties"]
    # Actúa en el cliente elegido: ve sus agentes y nada más.
    other = make_client(admin, slug="otra")
    make_agent(admin, other)
    items = call(api, access, "list_agents", client_id=c["id"])["structuredContent"]["items"]
    assert [a["id"] for a in items] == [agent["id"]]
    assert not call(api, access, "get_plan_tools", client_id=c["id"]).get("isError")
    missing = call(api, access, "list_agents")
    assert missing["isError"] and missing["structuredContent"]["code"] == "invalid_arguments"
    unknown = call(api, access, "list_agents", client_id="no-existe")
    assert unknown["isError"] and unknown["structuredContent"]["http_status"] == 404
    # Sin el secreto interno, el header del cliente no sirve desde afuera.
    outside = api.client.get(f"{V1}/agents", headers={"Authorization": f"Bearer {access}",
                                                      "x-atentina-mcp-client": c["id"]})
    assert outside.status_code == 401
    slugs = [x["slug"] for x in call(api, access, "admin_list_clients")["structuredContent"]["items"]]
    assert c["slug"] in slugs
    limits = call(api, access, "admin_get_client_limits", client_id=c["id"])
    assert not limits.get("isError"), limits
    # Reportes: técnico de un cliente (o de todos) y plataforma; los de cliente piden el cliente.
    assert {"get_report_technical", "get_report_platform", "get_report_summary"} <= set(tools)
    assert "client_id" in tools["get_report_technical"]["inputSchema"]["properties"]
    assert "client_id" not in tools["get_report_platform"]["inputSchema"]["properties"]
    assert "kpis" in call(api, access, "get_report_summary", client_id=c["id"])["structuredContent"]
    assert "latency_daily" in call(api, access, "get_report_technical", client_id=c["id"])["structuredContent"]
    assert "clients" in call(api, access, "get_report_platform")["structuredContent"]
    # El uso queda anotado sin cliente (toda la plataforma) y lo ve el admin.
    usage = call(api, access, "admin_get_mcp_usage")["structuredContent"]
    assert {"admin_list_clients", "admin_get_client_limits"} <= {t["tool"] for t in usage["tools"]}
    # Se ve en "Agentes conectados" sin cliente.
    assert None in [g["client_id"] for g in admin.get(f"{V1}/oauth/grants").json()]


def test_confidential_client_needs_its_secret(api, setup):
    _, _, user, _ = setup
    app_client = register(api, token_endpoint_auth_method="client_secret_basic")
    assert app_client["client_secret"]
    verifier, challenge = pkce()
    code = code_of(authorize(user, auth_params(app_client["client_id"], challenge)))
    form = dict(grant_type="authorization_code", code=code, redirect_uri=REDIRECT, code_verifier=verifier)
    bad = api.client.post("/oauth/token", data={**form, "client_id": app_client["client_id"]})
    assert bad.status_code == 401 and bad.json()["error"] == "invalid_client"
    basic = base64.b64encode(f"{app_client['client_id']}:{app_client['client_secret']}".encode()).decode()
    ok = api.client.post("/oauth/token", data=form, headers={"Authorization": f"Basic {basic}"})
    assert ok.status_code == 200, ok.text


def test_client_id_metadata_document(api, setup, monkeypatch):
    _, _, user, _ = setup
    url = "https://claude.ai/oauth/mcp-client-metadata"
    fetched = []

    async def fake_fetch(u):
        fetched.append(u)
        return {"client_id": url, "client_name": "Claude", "client_uri": "https://claude.ai",
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]}

    monkeypatch.setattr(oauth, "fetch_metadata", fake_fetch)
    verifier, challenge = pkce()
    params = auth_params(url, challenge, redirect_uri="https://claude.ai/api/mcp/auth_callback")
    info = user.get(f"{V1}/oauth/authorize", params=params).json()
    assert info["valid"] and info["client_name"] == "Claude" and info["verified"] is True
    code = parse_qs(urlparse(authorize(user, params)).query)["code"][0]
    r = token(api, grant_type="authorization_code", code=code, redirect_uri="https://claude.ai/api/mcp/auth_callback",
              client_id=url, code_verifier=verifier)
    assert r.status_code == 200, r.text
    assert fetched == [url]   # leído una vez y guardado

    async def wrong(u):
        return {"client_id": "https://otro.example/x", "redirect_uris": ["https://otro.example/cb"]}

    monkeypatch.setattr(oauth, "fetch_metadata", wrong)
    other = "https://otro.example/metadata.json"
    assert not user.get(f"{V1}/oauth/authorize", params=auth_params(other, challenge)).json()["valid"]


def test_redirect_url_keeps_existing_query():
    req = oauth.AuthorizeRequest(client=None, redirect_uri="https://x.example/cb?a=1", code_challenge="",
                                 state=None, scope="mcp", resource=RESOURCE)
    assert oauth.redirect_url(req, "https://i", code="c") == "https://x.example/cb?a=1&" + urlencode(
        {"code": "c", "iss": "https://i"})
