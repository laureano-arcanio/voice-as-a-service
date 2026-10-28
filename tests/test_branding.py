"""Marca blanca del panel (docs/ARQUITECTURA.md): colores con contraste, logo (imagen recodificada, SVG filtrado),
quien la ve (`/auth/me`), la API publica del login, el flag del tier y los links de los mails."""
import io

import pytest
from PIL import Image

from app.config import settings
from app.mail import messages
from app.services import branding

from .test_api import V1, admin, client_user, make_client, make_tier  # noqa: F401  (admin: fixture)

COLORS = dict(color_primary="#0068fd", color_header="#272a35", color_accent="#4d39c3")
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 904 243"><defs><style>.a{fill:#272a35}</style></defs>'
       '<path class="a" d="M0 0h10v10H0z"/></svg>')


@pytest.fixture
def brand(api, admin, monkeypatch, tmp_path):  # noqa: F811  (fixture)
    monkeypatch.setattr(settings, "branding_dir", tmp_path / "branding")
    api.yoizen = make_client(admin, slug="yoizen", white_label=True)
    api.user = client_user(api, admin, api.yoizen, email="ana@yoizen.com")
    return api


def put(api, client, **body):
    return api.post if False else api.put(f"{V1}/clients/{client['id']}/branding",
                                          json={"enabled": True, "powered_by": True, **COLORS, **body})


def png(width=600, height=150, alpha=True):
    img = Image.new("RGBA" if alpha else "RGB", (width, height), (0, 104, 253, 255) if alpha else (0, 104, 253))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def upload(api, client, data, name="logo.png", mime="image/png"):
    return api.put(f"{V1}/clients/{client['id']}/branding/logo", files={"file": (name, data, mime)})


# ---------- colores ----------

def test_contrast_table():
    # La misma tabla que web/src/branding/color.test.ts (docs/ARQUITECTURA.md).
    table = {"#2456e6": (5.92, 3.16), "#0068fd": (4.77, 3.92), "#272a35": (14.30, 1.31), "#4d39c3": (7.81, 2.40),
             "#fd6421": (2.99, 6.26)}
    for color, (on_white, on_ink) in table.items():
        assert round(branding.contrast("#ffffff", color), 2) == on_white
        assert round(branding.contrast("#0b1220", color), 2) == on_ink
    assert branding.text_on("#272a35") == "#ffffff" and branding.text_on("#ffffff") == "#0b1220"
    assert branding.text_on("#fd6421") == "#0b1220"


def test_primary_needs_contrast_and_gets_a_suggestion(brand, admin):
    r = put(admin, brand.yoizen, color_primary="#fd6421")
    assert r.status_code == 422 and r.json()["code"] == "color_contrast", r.text
    suggested = r.json()["errors"][0]["suggested"]
    assert branding.contrast("#ffffff", suggested) >= 4.5 and suggested != "#fd6421"
    assert put(admin, brand.yoizen, color_primary=suggested).status_code == 200
    # Formato: #rrggbb (mayusculas se normalizan).
    assert put(admin, brand.yoizen, color_primary="blue").status_code == 422
    out = put(admin, brand.yoizen, color_primary="#0068FD").json()
    assert out["color_primary"] == "#0068fd" and out["header_fg"] == "#ffffff"


# ---------- quien la ve ----------

def test_me_has_branding_only_when_enabled_and_in_plan(brand, admin):
    assert brand.user.get(f"{V1}/auth/me").json()["branding"] is None
    out = put(admin, brand.yoizen).json()
    assert out["active"] and out["available"]
    me = brand.user.get(f"{V1}/auth/me").json()["branding"]
    assert me == {"slug": "yoizen", "name": "Yoizen", "logo_url": None, "logo_ratio": None, "color_primary": "#0068fd",
                  "color_header": "#272a35", "color_accent": "#4d39c3", "header_fg": "#ffffff", "powered_by": True}
    # El admin nunca la ve.
    assert admin.get(f"{V1}/auth/me").json()["branding"] is None
    # Apagada: nada.
    put(admin, brand.yoizen, enabled=False)
    assert brand.user.get(f"{V1}/auth/me").json()["branding"] is None
    # Prendida pero el plan ya no la incluye: queda guardada, no se aplica.
    put(admin, brand.yoizen, enabled=True)
    admin.patch(f"{V1}/tiers/{brand.yoizen['tier']['id']}", json={"white_label": False})
    assert brand.user.get(f"{V1}/auth/me").json()["branding"] is None
    out = admin.get(f"{V1}/clients/{brand.yoizen['id']}/branding").json()
    assert out["enabled"] and not out["available"] and not out["active"]
    assert brand.user.get(f"{V1}/plan/features").json()["features"]["white_label"]["enabled"] is False


def test_public_branding_404_unless_active(brand, admin):
    assert brand.client.get(f"{V1}/public/branding/yoizen").status_code == 404
    assert brand.client.get(f"{V1}/public/branding/nadie").status_code == 404
    put(admin, brand.yoizen)
    r = brand.client.get(f"{V1}/public/branding/yoizen")
    assert r.status_code == 200 and r.json()["name"] == "Yoizen" and r.json()["color_primary"] == "#0068fd"
    assert brand.client.get(f"{V1}/public/branding/yoizen/logo").status_code == 404
    # Sin fila de marca: tampoco.
    other = make_client(admin, slug="otro", white_label=True)
    assert brand.client.get(f"{V1}/public/branding/{other['slug']}").status_code == 404


def test_client_cannot_edit(brand):
    assert brand.user.put(f"{V1}/clients/{brand.yoizen['id']}/branding",
                          json={"enabled": True, **COLORS}).status_code == 403
    assert brand.user.get(f"{V1}/clients/{brand.yoizen['id']}/branding").status_code == 403


# ---------- logo ----------

def test_raster_logo_is_shrunk_and_served_with_cache(brand, admin):
    put(admin, brand.yoizen)
    r = upload(admin, brand.yoizen, png(1200, 300))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["logo_ratio"] == 4.0 and out["logo_url"].startswith("/api/v1/public/branding/yoizen/logo?v=")
    path = next((settings.branding_dir / brand.yoizen["id"]).iterdir())
    with Image.open(path) as img:
        assert img.size == (480, 120) and img.format == "PNG"
    logo = brand.client.get(out["logo_url"])
    assert logo.status_code == 200 and logo.headers["content-type"] == "image/png"
    assert "immutable" in logo.headers["cache-control"]
    assert brand.user.get(f"{V1}/auth/me").json()["branding"]["logo_url"] == out["logo_url"]
    # Un logo chico no se agranda; el JPG sin alfa sale como JPEG.
    small = Image.new("RGB", (120, 30), (200, 10, 10))
    buf = io.BytesIO()
    small.save(buf, "JPEG")
    out = upload(admin, brand.yoizen, buf.getvalue(), "logo.jpg", "image/jpeg").json()
    files = list((settings.branding_dir / brand.yoizen["id"]).iterdir())
    assert len(files) == 1 and files[0].suffix == ".jpg" and out["logo_ratio"] == 4.0
    with Image.open(files[0]) as img:
        assert img.size == (120, 30)
    # Quitar: sin archivo y sin URL.
    out = admin.delete(f"{V1}/clients/{brand.yoizen['id']}/branding/logo").json()
    assert out["logo_url"] is None and list((settings.branding_dir / brand.yoizen["id"]).iterdir()) == []


def test_svg_logo_kept_as_is_with_csp(brand, admin):
    put(admin, brand.yoizen)
    r = upload(admin, brand.yoizen, SVG.encode(), "logo.svg", "image/svg+xml")
    assert r.status_code == 200, r.text
    assert r.json()["logo_ratio"] == round(904 / 243, 4)
    logo = brand.client.get(r.json()["logo_url"])
    assert logo.status_code == 200 and logo.headers["content-type"].startswith("image/svg+xml")
    assert logo.headers["content-security-policy"] == "default-src 'none'; style-src 'unsafe-inline'"
    assert logo.headers["x-content-type-options"] == "nosniff"
    assert logo.text == SVG


@pytest.mark.parametrize("bad", [
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil/x.png"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://evil/a.css)</style></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div/></foreignObject></svg>',
    '<!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>',
])
def test_unsafe_svg_rejected(brand, admin, bad):
    r = upload(admin, brand.yoizen, bad.encode(), "logo.svg", "image/svg+xml")
    assert r.status_code == 422 and r.json()["code"] == "logo_unsafe", r.text


def test_logo_limits(brand, admin):
    assert upload(admin, brand.yoizen, b"\x89PNG not really").json()["code"] == "logo_invalid"
    assert upload(admin, brand.yoizen, b"a" * (branding.LOGO_MAX_BYTES + 1)).json()["code"] == "logo_too_large"
    assert upload(admin, brand.yoizen, ("<svg " + "a" * branding.SVG_MAX_BYTES).encode()).json()["code"] == "logo_too_large"
    assert upload(admin, brand.yoizen, png(100, 10)).json()["code"] == "logo_invalid"      # menos de 24 px de alto
    gif = io.BytesIO()
    Image.new("RGB", (100, 40)).save(gif, "GIF")
    assert upload(admin, brand.yoizen, gif.getvalue(), "logo.gif", "image/gif").json()["code"] == "logo_format"


def test_delete_client_drops_logo_files(brand, admin):
    put(admin, brand.yoizen)
    upload(admin, brand.yoizen, png())
    assert (settings.branding_dir / brand.yoizen["id"]).is_dir()
    assert admin.delete(f"{V1}/clients/{brand.yoizen['id']}").status_code == 204
    assert not (settings.branding_dir / brand.yoizen["id"]).exists()


# ---------- tier y mails ----------

def test_tier_flag_in_api(admin):
    tier = make_tier(admin, name="Marca")
    assert tier["white_label"] is False
    assert admin.patch(f"{V1}/tiers/{tier['id']}", json={"white_label": True}).json()["white_label"] is True
    assert admin.patch(f"{V1}/tiers/{tier['id']}", json={"white_label": None}).json()["white_label"] is True


def test_login_links_carry_the_client_slug(brand, admin):
    assert messages.dashboard_url("ana@yoizen.com") == f"{settings.app_url.rstrip('/')}/login?email=ana%40yoizen.com"
    assert messages.dashboard_url("ana@yoizen.com", "yoizen").endswith("/login?email=ana%40yoizen.com&c=yoizen")
    assert messages.password_setup_url("tok", None, "yoizen").endswith("/set-password?token=tok&c=yoizen")
    with brand.sessions() as s:
        from app.models import Client
        client = s.scalar(__import__("sqlalchemy").select(Client).where(Client.slug == "yoizen"))
        assert branding.login_slug(client) is None
    put(admin, brand.yoizen)
    with brand.sessions() as s:
        client = s.scalar(__import__("sqlalchemy").select(Client).where(Client.slug == "yoizen"))
        assert branding.login_slug(client) == "yoizen"
