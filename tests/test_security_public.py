"""Superficie publica (app.atentina.com.ar por el tunel, sin Cloudflare Access): limites de
login por IP real, cookie, logout, CSRF, docs, CORS, headers y CSP, 401 sin auth,
aislamiento entre clientes, y que la demo, el webhook y las API keys sigan andando."""
import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.api import http as http_mw
from app.config import settings
from app.models import Role, User
from app.services import tts
from app.services.security import hash_password

from .test_api import ADMIN, V1, client_user, make_agent, make_client

CF_PEER = ("172.24.0.1", 40000)        # cloudflared por el gateway de compose
LAN_PEER = ("192.168.1.50", 40000)     # LAN por el DNAT del router: no es proxy
LANDING = "https://atentina.com.ar"
APP = "https://app.atentina.com.ar"


@pytest.fixture
def admin(api):
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    return api.login(*ADMIN)


def peer_client(api, peer=CF_PEER, **kw) -> TestClient:
    return TestClient(api.app, client=peer, **kw)


def bad_login(c: TestClient, email: str, ip: str | None = None):
    headers = {"CF-Connecting-IP": ip} if ip else {}
    return c.post(f"{V1}/auth/login", json={"email": email, "password": "mala-clave"}, headers=headers)


def session_cookie(resp) -> str:
    return next(h for h in resp.headers.get_list("set-cookie") if h.startswith("vaas_session="))


# ---------- login: limites por IP real ----------

@pytest.fixture
def low_limits(monkeypatch):
    monkeypatch.setattr(settings, "login_fail_ip_email_15m", 3)
    monkeypatch.setattr(settings, "login_fail_ip_15m", 5)
    monkeypatch.setattr(settings, "login_fail_email_15m", 4)


def test_login_limit_per_ip_email_uses_cf_ip(api, admin, low_limits):
    c = peer_client(api)
    for _ in range(3):
        assert bad_login(c, ADMIN[0], "203.0.113.1").status_code == 401
    r = bad_login(c, ADMIN[0], "203.0.113.1")
    assert r.status_code == 429 and r.json()["code"] == "too_many_attempts" and int(r.headers["Retry-After"]) > 0
    # Bloqueado tambien con la clave correcta, pero desde otra IP real sigue pudiendo entrar.
    ok = {"email": ADMIN[0], "password": ADMIN[1]}
    assert c.post(f"{V1}/auth/login", json=ok, headers={"CF-Connecting-IP": "203.0.113.1"}).status_code == 429
    assert c.post(f"{V1}/auth/login", json=ok, headers={"CF-Connecting-IP": "203.0.113.2"}).status_code == 200


def test_login_limit_per_ip_across_emails(api, low_limits):
    c = peer_client(api)
    for i in range(5):
        assert bad_login(c, f"u{i}@example.com", "203.0.113.7").status_code == 401
    assert bad_login(c, "otro@example.com", "203.0.113.7").status_code == 429
    assert bad_login(c, "otro@example.com", "203.0.113.8").status_code == 401


def test_login_limit_per_email_across_ips(api, admin, low_limits):
    c = peer_client(api)
    for i in range(4):
        assert bad_login(c, ADMIN[0], f"203.0.113.{10 + i}").status_code == 401
    # Con el email al tope, una IP que ya fallo queda frenada...
    assert bad_login(c, ADMIN[0], "203.0.113.10").status_code == 429
    # ...una nueva prueba una vez y queda frenada...
    assert bad_login(c, ADMIN[0], "203.0.113.99").status_code == 401
    assert bad_login(c, ADMIN[0], "203.0.113.99").status_code == 429
    # ...y el dueno, desde una IP sin fallos, entra igual (un tercero no lo deja afuera).
    ok = {"email": ADMIN[0], "password": ADMIN[1]}
    assert c.post(f"{V1}/auth/login", json=ok, headers={"CF-Connecting-IP": "203.0.113.200"}).status_code == 200


def test_login_parallel_attempts_are_counted_before_verifying(api, low_limits):
    from concurrent.futures import ThreadPoolExecutor
    c = peer_client(api)
    with ThreadPoolExecutor(12) as pool:
        codes = list(pool.map(lambda _: bad_login(c, "x@example.com", "203.0.113.70").status_code, range(12)))
    assert codes.count(401) == 3 and codes.count(429) == 9


def test_rejected_login_does_not_grow_limiter(api, low_limits):
    from app.api.deps import api_limiter
    c = peer_client(api)
    for i in range(5):
        bad_login(c, f"u{i}@example.com", "203.0.113.80")
    before = len(api_limiter.hits)
    for i in range(50):
        assert bad_login(c, f"nuevo{i}@example.com", "203.0.113.80").status_code == 429
    assert len(api_limiter.hits) == before


def test_trusted_gateway_resolves_default_route(tmp_path):
    from app.api.deps import _trusted_networks, default_gateway
    route = tmp_path / "route"
    route.write_text("Iface\tDestination\tGateway\tFlags\n"
                     "eth0\t00000000\t010018AC\t0003\n"
                     "eth0\t000018AC\t00000000\t0001\n")
    assert default_gateway(str(route)) == "172.24.0.1"
    assert default_gateway(str(tmp_path / "no-existe")) is None
    assert _trusted_networks("127.0.0.1/32, 10.0.0.0/8") and type(settings).model_fields[
        "trusted_proxy_cidrs"].default == "127.0.0.1/32,::1/128,gateway"


def test_http_through_tunnel_redirects_to_https(api):
    c = peer_client(api, follow_redirects=False)
    r = c.get(f"{V1}/auth/me?x=1", headers={"X-Forwarded-Proto": "http", "Host": "app.atentina.com.ar"})
    assert r.status_code == 308 and r.headers["location"] == "https://app.atentina.com.ar/api/v1/auth/me?x=1"
    # Directo (localhost, LAN) o ya por HTTPS: sin redireccion.
    assert c.get(f"{V1}/auth/me", headers={"X-Forwarded-Proto": "https"}).status_code == 401
    assert peer_client(api, LAN_PEER, follow_redirects=False).get(
        f"{V1}/auth/me", headers={"X-Forwarded-Proto": "http"}).status_code == 401
    assert api.client.get(f"{V1}/auth/me").status_code == 401


def test_login_success_resets_ip_email(api, admin, low_limits):
    c = peer_client(api)
    for _ in range(2):
        bad_login(c, ADMIN[0], "203.0.113.20")
    ok = {"email": ADMIN[0], "password": ADMIN[1]}
    assert c.post(f"{V1}/auth/login", json=ok, headers={"CF-Connecting-IP": "203.0.113.20"}).status_code == 200
    for _ in range(2):
        assert bad_login(c, ADMIN[0], "203.0.113.20").status_code == 401


def test_cf_header_ignored_from_untrusted_peer(api, low_limits):
    c = peer_client(api, LAN_PEER)
    for i in range(5):
        assert bad_login(c, f"u{i}@example.com", f"198.51.100.{i}").status_code == 401
    # Rotar CF-Connecting-IP desde la LAN no da IPs nuevas: cuenta el par.
    assert bad_login(c, "x@example.com", "198.51.100.200").status_code == 429


# ---------- cookie y logout ----------

def test_cookie_flags_over_http_dev(api, admin):
    r = api.client.post(f"{V1}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    cookie = session_cookie(r).lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    assert f"max-age={settings.auth_token_hours * 3600}" in cookie
    assert "secure" not in cookie   # AUTH_COOKIE_SECURE=false y http://: anda en localhost


def test_cookie_secure_behind_tunnel(api, admin):
    body = {"email": ADMIN[0], "password": ADMIN[1]}
    r = peer_client(api).post(f"{V1}/auth/login", json=body, headers={"X-Forwarded-Proto": "https"})
    assert "secure" in session_cookie(r).lower()
    # X-Forwarded-Proto desde un par no confiable no cuenta.
    r = peer_client(api, LAN_PEER).post(f"{V1}/auth/login", json=body, headers={"X-Forwarded-Proto": "https"})
    assert "secure" not in session_cookie(r).lower()


def test_cookie_secure_by_setting(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "auth_cookie_secure", True)
    r = TestClient(api.app).post(f"{V1}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert "secure" in session_cookie(r).lower()


def test_logout_invalidates_stolen_token(api, admin):
    token = admin.cookies.get("vaas_session")
    bearer = {"Authorization": f"Bearer {token}"}
    assert api.client.get(f"{V1}/auth/me", headers=bearer).status_code == 200
    other = api.login(*ADMIN)  # otra sesion del mismo usuario
    assert admin.post(f"{V1}/auth/logout").status_code == 204
    assert api.client.get(f"{V1}/auth/me", headers=bearer).status_code == 401
    assert other.get(f"{V1}/auth/me").status_code == 401   # cierra todas
    assert api.client.post(f"{V1}/auth/logout").status_code == 204   # sin sesion, 204 igual
    assert api.login(*ADMIN).get(f"{V1}/auth/me").status_code == 200


def test_password_change_and_deactivation_close_sessions(api, admin):
    c = make_client(admin)
    user = client_user(api, admin, c)
    uid = user.get(f"{V1}/auth/me").json()["id"]
    assert admin.patch(f"{V1}/users/{uid}", json={"password": "otra-clave-larga-1"}).status_code == 200
    assert user.get(f"{V1}/auth/me").status_code == 401
    user = api.login("ana@acme.com", "otra-clave-larga-1")
    admin.patch(f"{V1}/users/{uid}", json={"active": False})
    admin.patch(f"{V1}/users/{uid}", json={"active": True})
    assert user.get(f"{V1}/auth/me").status_code == 401


# ---------- CSRF ----------

def test_csrf_origin_checks(api, admin):
    c = make_client(admin)
    path = f"{V1}/clients/{c['id']}"
    body = {"name": "Acme 2"}
    assert admin.patch(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    r = admin.patch(path, json=body, headers={"Origin": LANDING})   # otro subdominio, same-site
    assert r.status_code == 403 and r.json()["code"] == "csrf"
    assert admin.patch(path, json=body, headers={"Origin": "null"}).status_code == 403
    assert admin.patch(path, json=body, headers={"Sec-Fetch-Site": "same-site"}).status_code == 403
    assert admin.patch(path, json=body, headers={"Origin": "http://testserver"}).status_code == 200
    assert admin.patch(path, json=body, headers={"Origin": APP}).status_code == 200
    assert admin.patch(path, json=body, headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200
    assert admin.patch(path, json=body).status_code == 200   # sin Origin: no es un navegador
    # El logout tambien: un POST sin cuerpo desde otro sitio no cierra la sesion.
    assert admin.post(f"{V1}/auth/logout", headers={"Origin": LANDING}).status_code == 403
    assert admin.get(f"{V1}/auth/me").status_code == 200


def test_csrf_does_not_apply_to_bearer(api, admin):
    c = make_client(admin)
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "crm"}).json()["key"]
    agent = make_agent(admin, c)
    r = api.client.post(f"{V1}/calls", json={"agent_id": agent["id"]},
                        headers={"Authorization": f"Bearer {key}", "Origin": "https://evil.example"})
    assert r.status_code == 201, r.text


# ---------- docs ----------

@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_docs_admin_only(api, admin, path):
    assert api.client.get(f"{V1}{path}").status_code == 401
    user = client_user(api, admin, make_client(admin))
    assert user.get(f"{V1}{path}").status_code == 403
    r = admin.get(f"{V1}{path}")
    assert r.status_code == 200
    if path == "/docs":
        assert "cdn.jsdelivr.net" in r.headers["content-security-policy"]
    else:
        assert "/api/v1/auth/login" in r.json()["paths"]


def test_docs_off_and_public(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "api_docs", "off")
    assert admin.get(f"{V1}/openapi.json").status_code == 404
    monkeypatch.setattr(settings, "api_docs", "public")
    assert api.client.get(f"{V1}/openapi.json").status_code == 200


def test_openapi_still_generated_for_make_openapi(api):
    assert "/api/v1/auth/login" in api.app.openapi()["paths"]


# ---------- CORS ----------

def test_cors_landing_only_and_without_credentials(api):
    pre = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    ok = api.client.options(f"{V1}/demo/sessions", headers={"Origin": LANDING, **pre})
    assert ok.headers["access-control-allow-origin"] == LANDING
    assert "access-control-allow-credentials" not in ok.headers
    other = api.client.options(f"{V1}/auth/login", headers={"Origin": "https://evil.example", **pre})
    assert "access-control-allow-origin" not in other.headers


# ---------- headers y CSP ----------

def test_security_headers_and_csp(api, tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html><script>var tema = 1;</script>"
                                         "<script type=\"module\" src=\"/assets/x.js\"></script></html>")
    monkeypatch.setattr(settings, "web_dist_dir", tmp_path)
    http_mw._csp_cache.clear()
    digest = base64.b64encode(hashlib.sha256(b"var tema = 1;").digest()).decode()
    r = api.client.get("/health")
    h = r.headers
    csp = h["content-security-policy"]
    assert f"'sha256-{digest}'" in csp and "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert "https://connect.facebook.net" in csp and "frame-src https://*.facebook.com" in csp
    assert "connect-src 'self' https://*.facebook.com" in csp and "frame-ancestors 'none'" in csp
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff"
    assert h["cross-origin-opener-policy"] == "same-origin-allow-popups"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "microphone=()" in h["permissions-policy"]
    assert "strict-transport-security" not in h   # http://localhost
    https = peer_client(api).get("/health", headers={"X-Forwarded-Proto": "https"})
    assert https.headers["strict-transport-security"].startswith("max-age=31536000")
    monkeypatch.setattr(settings, "csp_report_only", True)
    r = api.client.get("/health")
    assert "content-security-policy" not in r.headers and "content-security-policy-report-only" in r.headers


def test_body_limit(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "api_max_body_bytes", 1000)
    r = api.client.post(f"{V1}/auth/login", content=b"x" * 2000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413

    def chunks():
        for _ in range(4):
            yield b"x" * 500
    r = admin.post(f"{V1}/agents/validate", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_validation_error_hides_input(api):
    # Falta `password`: el error de pydantic trae todo el body (con la clave mal nombrada) como input.
    r = api.client.post(f"{V1}/auth/login", json={"email": "a@b.com", "clave": "clave-secreta-123"})
    assert r.status_code == 422
    assert "clave-secreta-123" not in r.text and all("input" not in e for e in r.json()["detail"])


# ---------- sin auth: 401 ----------

@pytest.mark.parametrize("method,path", [
    ("GET", "/auth/me"), ("GET", "/tiers"), ("GET", "/clients"), ("GET", "/phone-numbers"),
    ("GET", "/agents"), ("GET", "/agents/schema"), ("GET", "/agent-templates"), ("GET", "/users"),
    ("GET", "/calls"), ("GET", "/stats"), ("GET", "/voices"), ("GET", "/whatsapp/accounts"),
    ("POST", "/calls"), ("POST", "/conversations"), ("POST", "/tts/preview"), ("POST", "/agents/validate"),
])
def test_endpoints_require_auth(api, method, path):
    assert api.client.request(method, f"{V1}{path}", json={}).status_code == 401


# ---------- aislamiento entre clientes ----------

def test_client_isolation_sample(api, admin):
    acme, beta = make_client(admin, "acme"), make_client(admin, "beta")
    agent_b = make_agent(admin, beta)
    conv_b = admin.post(f"{V1}/conversations", json={"agent_id": agent_b["id"]}).json()["conversation_id"]
    ana = client_user(api, admin, acme)
    for path in (f"/agents/{agent_b['id']}", f"/agents/{agent_b['id']}/versions", f"/clients/{beta['id']}",
                 f"/clients/{beta['id']}/usage", f"/conversations/{conv_b}", f"/calls/{conv_b}"):
        assert ana.get(f"{V1}{path}").status_code in (403, 404), path
    assert ana.get(f"{V1}/clients/{beta['id']}/api-keys").status_code in (403, 404)
    assert ana.get(f"{V1}/calls", params={"client_id": beta["id"]}).status_code == 403
    assert ana.post(f"{V1}/calls", json={"agent_id": agent_b["id"]}).status_code == 404
    assert ana.post(f"{V1}/conversations", json={"agent_id": agent_b["id"]}).status_code == 404
    # Lo de admin, 403.
    assert ana.get(f"{V1}/users").status_code == 403
    assert ana.post(f"{V1}/tiers", json={"name": "x"}).status_code == 403
    assert ana.get(f"{V1}/whatsapp/accounts", params={"client_id": beta["id"]}).status_code == 403


def test_loadtest_only_admin_or_internal_client(api, admin):
    acme = make_client(admin, "acme")
    agent = make_agent(admin, acme)
    ana = client_user(api, admin, acme)
    r = ana.post(f"{V1}/calls", json={"agent_id": agent["id"], "loadtest": True})
    assert r.status_code == 403 and r.json()["code"] == "loadtest_forbidden"
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "loadtest": True}).status_code == 201
    interno = make_client(admin, settings.loadtest_client)
    agent_i = make_agent(admin, interno)
    key = admin.post(f"{V1}/clients/{interno['id']}/api-keys", json={"name": "loadtest"}).json()["key"]
    r = api.client.post(f"{V1}/calls", json={"agent_id": agent_i["id"], "loadtest": True},
                        headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 201 and api.dispatched[-1]["loadtest"] is True


def test_dispatch_error_is_not_leaked(api, admin, monkeypatch):
    from app.services import livekit

    async def boom(room, metadata):
        raise RuntimeError("twirp error: secreto-interno http://livekit:7880")

    monkeypatch.setattr(livekit, "dispatch_call", boom)
    agent = make_agent(admin, make_client(admin))
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]})
    assert r.status_code == 502 and "secreto-interno" not in r.text


# ---------- limites de uso con auth ----------

def test_tts_preview_rate_limited(api, admin, monkeypatch):
    async def fake_preview(voice, text):
        async def stream():
            yield b"RIFF"
        return stream()

    monkeypatch.setattr(tts, "preview", fake_preview)
    monkeypatch.setattr(settings, "rate_tts_preview_per_hour", 2)
    body = {"voice": "sofia", "text": "Hola"}
    for _ in range(2):
        assert admin.post(f"{V1}/tts/preview", json=body).status_code == 200
    r = admin.post(f"{V1}/tts/preview", json=body)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0


def test_conversations_rate_limited(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "rate_conversations_per_hour", 1)
    agent = make_agent(admin, make_client(admin))
    assert admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).status_code == 201
    assert admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).status_code == 429


# ---------- lo publico sigue andando ----------

def test_demo_still_works_through_tunnel(api, monkeypatch):
    from app.cli import seed_demo
    from app.services import demo

    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    monkeypatch.setattr(settings, "demo_livekit_url", "wss://rtc.example")
    seen_ips = []

    async def fake_verify(token, ip):
        seen_ips.append(ip)
        return True

    monkeypatch.setattr(demo, "verify_turnstile", fake_verify)
    demo.limiter.reset()
    with api.sessions() as s:
        seed_demo(s)
        s.commit()
    c = peer_client(api)
    hdr = {"Origin": LANDING, "CF-Connecting-IP": "203.0.113.50", "X-Forwarded-Proto": "https"}
    r = c.post(f"{V1}/demo/sessions", json={"turnstile_token": "ok"}, headers=hdr)
    assert r.status_code == 201 and r.headers["access-control-allow-origin"] == LANDING
    assert seen_ips == ["203.0.113.50"]
    auth = {**hdr, "Authorization": f"Bearer {r.json()['token']}"}
    assert c.post(f"{V1}/demo/calls", json={"agent": "turnos"}, headers=auth).status_code == 201


def test_whatsapp_webhook_still_works(api, monkeypatch):
    from app.whatsapp.service import get_service

    class Recording:
        def __init__(self):
            self.payloads = []

        def handle_payload(self, payload):
            self.payloads.append(payload)

    rec = Recording()
    api.app.dependency_overrides[get_service] = lambda: rec
    monkeypatch.setattr(settings, "wa_app_secret", "secreto")
    monkeypatch.setattr(settings, "wa_verify_token", "verif")
    c = peer_client(api)
    r = c.get("/wa/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verif", "hub.challenge": "42"})
    assert r.status_code == 200 and r.text == "42"
    raw = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
    sig = "sha256=" + hmac.new(b"secreto", raw, hashlib.sha256).hexdigest()
    r = c.post("/wa/webhook", content=raw, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
    assert r.status_code == 200


def test_admin_seeded_user_keeps_working(api):
    # Usuarios previos a session_version (sv ausente en el token = 0).
    import datetime

    import jwt
    with api.sessions() as s:
        u = User(email="viejo@example.com", password_hash=hash_password("x" * 12), role=Role.admin)
        s.add(u)
        s.commit()
        uid = u.id
    now = datetime.datetime.now(datetime.UTC)
    legacy = jwt.encode({"sub": uid, "role": "admin", "exp": now + datetime.timedelta(hours=1)},
                        settings.auth_secret, algorithm="HS256")
    assert api.client.get(f"{V1}/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 200
