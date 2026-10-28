"""Link publico para llamar a un agente (docs/features/LINK_LLAMADA.md): alta por agente con el tope del
plan, pausa, regenerar y revocar; la API publica (Turnstile, topes por IP y por link, errores sin
hablar del plan); minutos entrantes del tier; la pagina con sus metas y el host propio."""
import io
import json
import re

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.models import CallLink, CallMode, CallRow, CallStatus
from app.services import call_links, demo, quota

from .test_api import V1, client_user, make_agent, make_client
from .test_whatsapp_api import admin  # noqa: F401  (fixture)

HOST = "llamar.example.com"
TEMPLATE = "<html><head><!--LINK_HEAD--></head><body><!--LINK_DATA--></body></html>"


@pytest.fixture
def links(api, admin, monkeypatch, tmp_path):  # noqa: F811  (fixture)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key")
    monkeypatch.setattr(settings, "demo_livekit_url", "wss://rtc.example")
    monkeypatch.setattr(settings, "call_link_base_url", f"https://{HOST}")
    (tmp_path / "llamar.html").write_text(TEMPLATE)
    monkeypatch.setattr(settings, "web_dist_dir", tmp_path)
    monkeypatch.setattr(settings, "call_link_images_dir", tmp_path / "images")
    api.turnstile_ok = True

    async def fake_verify(token, ip):
        return api.turnstile_ok

    monkeypatch.setattr(demo, "verify_turnstile", fake_verify)
    call_links.limiter.reset()
    api.acme = make_client(admin, inbound_minutes=10, max_call_links=1)
    api.agent = make_agent(admin, api.acme, template="demo_booking")
    api.user = client_user(api, admin, api.acme)
    return api


def create(api, **body):
    return api.user.post(f"{V1}/agents/{api.agent['id']}/call-link", json=body)


def start(api, token, client=None):
    return (client or api.client).post(f"{V1}/public/call-links/{token}/calls", json={"turnstile_token": "ok"})


def finish_all(api):
    with api.sessions() as s:
        s.query(CallRow).update({"status": CallStatus.finalizada})
        s.commit()


# ---------- del cliente ----------

def test_agent_list_has_link_url_and_objective(links):
    def row():
        return next(a for a in links.user.get(f"{V1}/agents").json() if a["id"] == links.agent["id"])

    assert row()["call_link_url"] is None and isinstance(row()["objective"], str)
    link = create(links).json()
    assert row()["call_link_url"] == link["url"]
    links.user.delete(f"{V1}/agents/{links.agent['id']}/call-link")
    assert row()["call_link_url"] is None


def test_create_read_update_rotate_revoke(links):
    url = f"{V1}/agents/{links.agent['id']}/call-link"
    state = links.user.get(url).json()
    assert state["link"] is None and state["plan_max"] == 1 and state["plan_used"] == 0 and state["enabled"]
    assert state["default_company_name"] == "Acme"

    r = create(links, subtitle="Turnos y consultas")
    assert r.status_code == 201, r.text
    link = r.json()
    assert re.fullmatch(r"[A-Za-z0-9_-]{12}", link["token"])
    assert link["url"] == f"https://{HOST}/{link['token']}"
    assert link["max_call_seconds"] == settings.call_link_default_seconds and not link["paused"]
    assert link["usage"] == {"calls_today": 0, "seconds_today": 0, "seconds_month": 0}
    assert create(links).status_code == 409

    r = links.user.patch(url, json={"display_name": " Sofi ", "daily_minutes": 30, "paused": True})
    assert r.status_code == 200 and (r.json()["display_name"], r.json()["daily_minutes"], r.json()["paused"]) == (
        "Sofi", 30, True)
    assert links.user.patch(url, json={"daily_minutes": None}).json()["daily_minutes"] is None
    too_long = links.user.patch(url, json={"max_call_seconds": settings.call_max_duration_seconds + 1})
    assert too_long.status_code == 409

    rotated = links.user.post(f"{url}/rotate").json()
    assert rotated["token"] != link["token"] and rotated["display_name"] == "Sofi" and rotated["paused"]
    assert links.client.get(f"{V1}/public/call-links/{link['token']}").status_code == 404
    assert links.client.get(f"{V1}/public/call-links/{rotated['token']}").status_code == 200

    assert links.user.delete(url).status_code == 204
    assert links.user.get(url).json()["link"] is None
    assert links.client.get(f"{V1}/public/call-links/{rotated['token']}").status_code == 404
    assert create(links).status_code == 201      # revocado: no cuenta para el tope


def test_plan_limit(links, admin):  # noqa: F811  (fixture)
    other = make_agent(admin, links.acme, template="demo_booking", name="Otro")
    assert create(links).status_code == 201
    r = links.user.post(f"{V1}/agents/{other['id']}/call-link", json={})
    assert r.status_code == 429 and r.json()["code"] == "call_links_limit"

    none = make_client(admin, slug="free", max_call_links=0)
    agent = make_agent(admin, none, template="demo_booking")
    r = admin.post(f"{V1}/agents/{agent['id']}/call-link", json={})
    assert r.status_code == 429 and "no incluye" in r.json()["detail"]


def test_other_client_cannot_see_the_link(links, admin, api):  # noqa: F811  (fixture)
    create(links)
    other = make_client(admin, slug="otro")
    user = client_user(api, admin, other, email="otro@otro.com")
    assert user.get(f"{V1}/agents/{links.agent['id']}/call-link").status_code == 404


# ---------- publico ----------

def test_public_view(links):
    token = create(links, subtitle="Turnos").json()["token"]
    view = links.client.get(f"{V1}/public/call-links/{token}").json()
    assert view == {"display_name": "Sofía", "company_name": "Acme", "subtitle": "Turnos",
                    "image_url": None, "max_call_seconds": settings.call_link_default_seconds,
                    "records_audio": False, "available": True}
    assert links.client.get(f"{V1}/public/call-links/nope12345678").status_code == 404


def test_start_call_is_web_and_uses_inbound_minutes(links):
    token = create(links, max_call_seconds=120).json()["token"]
    r = start(links, token)
    assert r.status_code == 201, r.text
    assert r.json()["livekit_url"] == "wss://rtc.example" and r.json()["max_call_seconds"] == 120
    meta = links.dispatched[-1]
    assert meta["max_duration_seconds"] == 120 and meta["phone"] is None and meta["call_link_id"]
    assert meta["join_timeout_seconds"] == settings.call_link_join_timeout_seconds
    with links.sessions() as s:
        row = s.query(CallRow).one()
        assert row.mode == CallMode.web and row.call_link_id == meta["call_link_id"]
    assert quota.MINUTE_MODES[CallMode.web] == "inbound"
    assert quota.same_minutes(CallMode.entrante) == [CallMode.entrante, CallMode.web]


def test_turnstile_and_paused(links):
    token = create(links).json()["token"]
    links.turnstile_ok = False
    r = start(links, token)
    assert r.status_code == 403 and r.json()["code"] == "captcha_failed"
    links.turnstile_ok = True
    links.user.patch(f"{V1}/agents/{links.agent['id']}/call-link", json={"paused": True})
    r = start(links, token)
    assert r.status_code == 503 and r.json()["code"] == "unavailable"
    assert links.client.get(f"{V1}/public/call-links/{token}").json()["available"] is False


def test_busy_and_unavailable_do_not_mention_the_plan(links, admin):  # noqa: F811  (fixture)
    token = create(links, max_concurrent=1).json()["token"]
    assert start(links, token).status_code == 201
    r = start(links, token)
    assert r.status_code == 429 and r.json()["code"] == "busy" and "plan" not in r.json()["detail"]

    finish_all(links)
    with links.sessions() as s:     # gasto todos los minutos entrantes del mes
        s.query(CallRow).update({"duration_seconds": 10 * 60, "started_at": CallRow.created_at})
        s.commit()
    r = start(links, token)
    assert r.status_code == 503 and r.json()["code"] == "unavailable"
    assert "minutos" not in r.json()["detail"]


def test_link_daily_minutes(links):
    token = create(links, daily_minutes=1).json()["token"]
    assert start(links, token).status_code == 201
    finish_all(links)
    with links.sessions() as s:
        s.query(CallRow).update({"duration_seconds": 60, "started_at": CallRow.created_at})
        s.commit()
    assert start(links, token).json()["code"] == "unavailable"


def test_ip_limit(links, monkeypatch):
    monkeypatch.setattr(settings, "call_link_ip_calls_per_hour", 1)
    token = create(links).json()["token"]
    assert start(links, token).status_code == 201
    finish_all(links)
    r = start(links, token)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited"


def test_global_cap(links, monkeypatch):
    monkeypatch.setattr(settings, "call_link_max_concurrent", 1)
    token = create(links).json()["token"]
    assert start(links, token).status_code == 201
    assert start(links, token).json()["code"] == "busy"


def test_disabled_without_turnstile(links, monkeypatch):
    token = create(links).json()["token"]
    monkeypatch.setattr(settings, "turnstile_site_key", "")
    assert start(links, token).status_code == 503
    assert links.user.get(f"{V1}/agents/{links.agent['id']}/call-link").json()["enabled"] is False


# ---------- pagina y host ----------

def _data(html: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="link-data">(.*?)</script>', html).group(1))


def test_page_with_metas_and_its_own_headers(links):
    token = create(links, company_name="Clínica <del> Sur").json()["token"]
    r = links.client.get(f"/llamar/{token}")
    assert r.status_code == 200
    assert "<title>Hablá con Sofía · Clínica &lt;del&gt; Sur</title>" in r.text
    assert 'property="og:title"' in r.text and "<del>" not in r.text
    data = _data(r.text)
    assert data["found"] and data["token"] == token and data["company_name"] == "Clínica <del> Sur"
    assert data["turnstile_site_key"] == "site-key"
    assert "microphone=(self)" in r.headers["permissions-policy"]
    csp = r.headers["content-security-policy"]
    assert "wss://rtc.example" in csp and "https://challenges.cloudflare.com" in csp and "frame-ancestors 'none'" in csp

    gone = links.client.get("/llamar/nope12345678")
    assert gone.status_code == 404 and _data(gone.text) == {"found": False}


def test_link_host_only_serves_the_page_and_its_api(links):
    token = create(links).json()["token"]
    host = TestClient(links.app, base_url=f"https://{HOST}")
    page = host.get(f"/{token}")
    assert page.status_code == 200 and _data(page.text)["token"] == token
    assert host.get(f"{V1}/public/call-links/{token}").status_code == 200
    assert start(links, token, client=host).status_code == 201
    assert host.get("/", follow_redirects=False).headers["location"] == settings.site_url
    for path in (f"{V1}/auth/me", f"{V1}/agents", "/login", "/llamar/x/y"):
        assert host.get(path).status_code == 404, path


def test_agent_archived_link_is_gone(links):
    token = create(links).json()["token"]
    with links.sessions() as s:
        assert s.query(CallLink).count() == 1
    assert links.user.delete(f"{V1}/agents/{links.agent['id']}").status_code in (200, 204)
    assert links.client.get(f"{V1}/public/call-links/{token}").status_code == 404


# ---------- imagen ----------

def _image(fmt: str, size=(900, 600), mode="RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, (200, 30, 30, 128) if mode == "RGBA" else (200, 30, 30)).save(out, fmt)
    return out.getvalue()


def put_image(api, data: bytes, name="logo.png", user=None):
    return (user or api.user).put(f"{V1}/agents/{api.agent['id']}/call-link/image",
                                  files={"file": (name, data, "application/octet-stream")})


def test_image_upload_crop_serve_and_remove(links):
    token = create(links).json()["token"]
    images = settings.call_link_images_dir

    r = put_image(links, _image("JPEG"))
    assert r.status_code == 200, r.text
    url = r.json()["image_url"]
    assert url.startswith(f"{V1}/public/call-links/{token}/image?v=")
    got = links.client.get(url)
    assert got.status_code == 200 and got.headers["content-type"] == "image/jpeg"
    assert Image.open(io.BytesIO(got.content)).size == (512, 512)   # recorte cuadrado y achicada
    assert links.client.get(f"{V1}/public/call-links/{token}").json()["image_url"] == url

    # Con transparencia queda PNG; la anterior se borra.
    png = put_image(links, _image("PNG", (300, 200), "RGBA")).json()["image_url"]
    assert png != url and len(list(images.iterdir())) == 1
    got = links.client.get(png)
    assert got.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(got.content)).size == (200, 200)   # no se agranda

    # La pagina la muestra y la usa para la vista previa al compartir (absoluta, por el host del link).
    page = links.client.get(f"/llamar/{token}").text
    assert _data(page)["image_url"] == png and f'property="og:image" content="https://{HOST}{png}' in page
    host = TestClient(links.app, base_url=f"https://{HOST}")
    assert host.get(png).status_code == 200

    # Regenerar el link la conserva; quitarla vuelve a la inicial y borra el archivo.
    url = f"{V1}/agents/{links.agent['id']}/call-link"
    rotated = links.user.post(f"{url}/rotate").json()
    assert rotated["image_url"].startswith(f"{V1}/public/call-links/{rotated['token']}/image")
    assert links.client.get(png).status_code == 404     # el token viejo ya no existe
    r = links.user.delete(f"{url}/image")
    assert r.status_code == 200 and r.json()["image_url"] is None
    assert list(images.iterdir()) == []
    assert links.client.get(rotated["image_url"]).status_code == 404


def test_image_rejects_other_formats_and_other_clients(links, admin, api):  # noqa: F811  (fixture)
    assert put_image(links, _image("PNG")).status_code == 404       # sin link todavia
    create(links)
    gif = put_image(links, _image("GIF"), "a.gif")
    assert gif.status_code == 422 and gif.json()["code"] == "image_format"
    assert put_image(links, b"<svg xmlns='http://www.w3.org/2000/svg'/>", "a.svg").json()["code"] == "image_invalid"
    big = put_image(links, b"0" * (call_links.IMAGE_MAX_BYTES + 1))
    assert big.json()["code"] == "image_too_large"

    other = make_client(admin, slug="otro")
    user = client_user(api, admin, other, email="otro@otro.com")
    assert put_image(links, _image("PNG"), user=user).status_code == 404
