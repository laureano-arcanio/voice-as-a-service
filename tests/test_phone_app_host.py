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


def test_without_setting_other_hosts_unchanged(phone, monkeypatch):
    monkeypatch.setattr(settings, "phone_app_base_url", "")
    host = TestClient(phone.app, base_url=f"https://{HOST}")
    assert host.get("/movil").status_code == 200
