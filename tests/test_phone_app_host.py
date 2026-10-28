"""Teléfono del equipo en su host (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 16): `/` es la página, pasan la API
(con su propia sesión: la cookie es de cada host) y los assets, y nada más del panel."""
import pytest
from fastapi.testclient import TestClient

from app.config import settings

from .test_api import V1, client_user, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)

HOST = "telefono.example.com"
PAGE = "<html><body>telefono</body></html>"


@pytest.fixture
def phone(api, admin, monkeypatch, tmp_path):  # noqa: F811  (fixture)
    monkeypatch.setattr(settings, "phone_app_base_url", f"https://{HOST}")
    (tmp_path / "telefono.html").write_text(PAGE)
    monkeypatch.setattr(settings, "web_dist_dir", tmp_path)
    api.acme = make_client(admin)
    client_user(api, admin, api.acme)
    return api


def test_page_on_panel_host(phone):
    r = phone.client.get("/movil")
    assert r.status_code == 200 and r.text == PAGE
    assert r.headers["cache-control"] == "no-cache"
    assert "microphone=(self)" in r.headers["permissions-policy"]


def test_phone_host_serves_page_and_api_only(phone):
    host = TestClient(phone.app, base_url=f"https://{HOST}")
    page = host.get("/")
    assert page.status_code == 200 and page.text == PAGE
    assert "content-security-policy" in page.headers
    assert host.get(f"{V1}/auth/me").status_code == 401
    login = host.post(f"{V1}/auth/login", json={"email": "ana@acme.com", "password": "cliente-password-1"},
                      headers={"Origin": f"https://{HOST}"})
    assert login.status_code == 200, login.text
    assert host.get(f"{V1}/auth/me").json()["email"] == "ana@acme.com"
    assert host.get(f"{V1}/contacts").status_code == 200
    for path in ("/login", "/telefono", "/admin", "/llamar/abcdefgh12", "/mcp", "/wa/webhook", f"{V1}/docs",
                 f"{V1}/openapi.json"):
        assert host.get(path).status_code == 404, path


def test_phone_host_lets_logo_and_manifest_through(phone):
    # Los sirve el build de la SPA (fuera de los tests puede no estar): basta con que el middleware no los corte.
    host = TestClient(phone.app, base_url=f"https://{HOST}")
    for path in ("/atentina-logo.svg", "/atentina-mark.svg", "/telefono.webmanifest"):
        assert host.get(path).text != "No encontrado", path
    assert host.get("/otro.svg").text == "No encontrado"


def test_without_setting_other_hosts_unchanged(phone, monkeypatch):
    monkeypatch.setattr(settings, "phone_app_base_url", "")
    host = TestClient(phone.app, base_url=f"https://{HOST}")
    assert host.get("/movil").status_code == 200


# ---------- una sola sesión para el panel y el teléfono (services/session_switch.py) ----------

PANEL = "panel.example.com"


@pytest.fixture
def both(phone, monkeypatch):
    monkeypatch.setattr(settings, "app_origins", f"https://{PANEL}")
    panel = TestClient(phone.app, base_url=f"https://{PANEL}")
    r = panel.post(f"{V1}/auth/login", json={"email": "ana@acme.com", "password": "cliente-password-1"},
                   headers={"Origin": f"https://{PANEL}"})
    assert r.status_code == 200, r.text
    phone.panel = panel
    phone.phone = TestClient(phone.app, base_url=f"https://{HOST}")
    return phone


def _token(url: str) -> str:
    return url.split("#sesion=", 1)[1]


def test_switch_panel_to_phone_and_back(both):
    url = both.panel.post(f"{V1}/auth/switch", json={"target": "phone"},
                          headers={"Origin": f"https://{PANEL}"}).json()["url"]
    assert url.startswith(f"https://{HOST}/#sesion=")
    r = both.phone.post(f"{V1}/auth/switch/redeem", json={"token": _token(url)})
    assert r.status_code == 200 and r.json()["email"] == "ana@acme.com"
    assert both.phone.get(f"{V1}/auth/me").status_code == 200
    # De un solo uso, y la sesión del panel sigue abierta.
    assert both.phone.post(f"{V1}/auth/switch/redeem", json={"token": _token(url)}).json()["code"] == "invalid_switch"
    assert both.panel.get(f"{V1}/auth/me").status_code == 200

    back = both.phone.post(f"{V1}/auth/switch", json={"target": "panel"},
                           headers={"Origin": f"https://{HOST}"}).json()["url"]
    assert back.startswith(f"https://{PANEL}/telefono#sesion=")
    # El pase es para el host del panel: en el del teléfono no vale.
    assert both.phone.post(f"{V1}/auth/switch/redeem", json={"token": _token(back)}).status_code == 422
    assert both.panel.post(f"{V1}/auth/switch/redeem", json={"token": _token(back)}).status_code == 200


def test_switch_needs_session_and_dies_with_logout(both):
    assert both.client.post(f"{V1}/auth/switch", json={"target": "phone"}).status_code == 401
    url = both.panel.post(f"{V1}/auth/switch", json={"target": "phone"},
                          headers={"Origin": f"https://{PANEL}"}).json()["url"]
    # Cerrar todas las sesiones (sube session_version) invalida el pase.
    with both.sessions() as s:
        from app.models import User
        s.query(User).filter(User.email == "ana@acme.com").update({"session_version": User.session_version + 1})
        s.commit()
    assert both.phone.post(f"{V1}/auth/switch/redeem", json={"token": _token(url)}).status_code == 422


def test_start_signs_in_the_phone_with_the_panel_session(both):
    hop = both.phone.get(f"{V1}/auth/switch/start", follow_redirects=False)
    assert hop.status_code == 302 and hop.headers["location"] == f"https://{PANEL}{V1}/auth/switch/start?target=phone"
    landed = both.panel.get(f"{V1}/auth/switch/start", follow_redirects=False).headers["location"]
    assert landed.startswith(f"https://{HOST}/#sesion=")
    assert both.phone.post(f"{V1}/auth/switch/redeem", json={"token": _token(landed)}).status_code == 200
    # Sin sesión en el panel: vuelve a pedir la clave.
    fresh = TestClient(both.app, base_url=f"https://{PANEL}")
    assert fresh.get(f"{V1}/auth/switch/start", follow_redirects=False).headers["location"] == f"https://{HOST}/#sin_sesion"


def test_switch_same_host_is_a_path(phone, monkeypatch):
    monkeypatch.setattr(settings, "phone_app_base_url", "")
    user = phone.login("ana@acme.com", "cliente-password-1")
    assert user.post(f"{V1}/auth/switch", json={"target": "phone"}).json()["url"] == "/movil"
