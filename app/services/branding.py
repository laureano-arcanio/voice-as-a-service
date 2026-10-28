"""Marca blanca del panel (docs/ARQUITECTURA.md): el logo y los tres colores con los que los usuarios de un
cliente ven el dashboard.

- Un admin la configura (`update`, `set_logo`, `remove_logo`); se aplica si `enabled` y el tier del cliente
  incluye `white_label` (`resolved`). El cliente la ve por `GET /auth/me` y la pagina de login por
  `GET /public/branding/{slug}` (`public_view`, 404 si no esta activa: no revela si el cliente existe).
- Colores `#rrggbb`. El primario va con texto blanco (botones) y como texto sobre blanco (links): tiene que dar
  4,5:1 (WCAG AA); si no, `color_contrast` con el mismo matiz oscurecido hasta que pase (`suggest_primary`).
  El encabezado es libre: el texto de la barra sale de `text_on`. El acento es decorativo (graficos).
- Logo: PNG, JPG o WebP (Pillow: se achica para entrar en LOGO_BOX, nunca se agranda, se recodifica) o SVG
  (se guarda tal cual si pasa `_check_svg`: sin scripts, eventos, foreignObject, entidades, @import, url() ni
  href fuera del documento). Archivo en BRANDING_DIR/<client_id>/<sha256[:16]>.<ext>; la URL publica lleva
  `v=<sha[:8]>` y se cachea un año.
"""
import hashlib
import io
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from ..config import settings
from ..models import Client, ClientBranding
from .errors import Invalid, NotFound

HEX = re.compile(r"^#[0-9a-f]{6}$")
MIN_CONTRAST = 4.5
INK = "#0b1220"
WHITE = "#ffffff"
DEFAULT_COLORS = {"color_primary": "#2456e6", "color_header": "#ffffff", "color_accent": "#b45309"}

LOGO_MAX_BYTES = 2 * 1024 * 1024
SVG_MAX_BYTES = 200 * 1024
LOGO_MAX_PIXELS = 24_000_000
LOGO_BOX = (480, 120)        # el logo entra aca manteniendo la proporcion (28 px de alto en el header)
LOGO_MIN_HEIGHT = 24
LOGO_FORMATS = {"PNG", "JPEG", "WEBP"}
LOGO_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}
# Un SVG abierto en una pestaña no ejecuta nada ni carga nada de afuera; el <style> inline si (los logotipos lo usan).
SVG_CSP = "default-src 'none'; style-src 'unsafe-inline'"
_SVG_UNSAFE = (re.compile(r"<\s*(script|foreignobject|iframe|embed|object|use)\b", re.I),
               re.compile(r"\son[a-z]+\s*=", re.I),
               re.compile(r"javascript:|@import|url\s*\(", re.I),
               re.compile(r"<!\s*(doctype|entity)", re.I))
_SVG_HREF = re.compile(r"(?:xlink:)?href\s*=\s*[\"']([^\"']*)", re.I)


# ---------- color ----------

def _linear(channel: int) -> float:
    v = channel / 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def _rgb(color: str) -> tuple[int, int, int]:
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def luminance(color: str) -> float:
    r, g, b = (_linear(c) for c in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """Relacion de contraste WCAG 2.1 (1 a 21)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def text_on(background: str) -> str:
    """Blanco si contrasta 4,5:1 con el fondo; si no, la tinta de la app."""
    return WHITE if contrast(WHITE, background) >= MIN_CONTRAST else INK


def suggest_primary(color: str) -> str:
    """El mismo matiz, oscurecido de a 5 % hacia negro hasta que el blanco contraste 4,5:1."""
    r, g, b = _rgb(color)
    for step in range(1, 20):
        k = 1 - 0.05 * step
        candidate = "#%02x%02x%02x" % (round(r * k), round(g * k), round(b * k))
        if contrast(WHITE, candidate) >= MIN_CONTRAST:
            return candidate
    return INK


def normalize_color(value: str, field: str) -> str:
    color = value.strip().lower()
    if not HEX.match(color):
        raise Invalid(f"El color tiene que ser #rrggbb ({field})", "color_format", [{"field": field}])
    return color


def check_primary(color: str) -> None:
    ratio = contrast(WHITE, color)
    if ratio < MIN_CONTRAST:
        raise Invalid(f"El primario {color} da {ratio:.2f}:1 con blanco; hace falta 4,5:1. Probá con "
                      f"{suggest_primary(color)}.", "color_contrast",
                      [{"field": "color_primary", "contrast": round(ratio, 2), "suggested": suggest_primary(color)}])


# ---------- logo ----------

def _ratio_from_svg(root: ET.Element) -> float | None:
    box = (root.get("viewBox") or "").replace(",", " ").split()
    try:
        if len(box) == 4 and float(box[2]) > 0 and float(box[3]) > 0:
            return round(float(box[2]) / float(box[3]), 4)
        w, h = root.get("width", ""), root.get("height", "")
        num = re.compile(r"^([0-9.]+)(px)?$")
        if num.match(w) and num.match(h) and float(num.match(h).group(1)) > 0:
            return round(float(num.match(w).group(1)) / float(num.match(h).group(1)), 4)
    except ValueError:
        pass
    return None


def _check_svg(data: bytes) -> tuple[bytes, str, float | None]:
    if len(data) > SVG_MAX_BYTES:
        raise Invalid("Un logo SVG pasa de 200 KB", "logo_too_large")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Invalid("No pudimos leer el SVG", "logo_invalid") from None
    for pattern in _SVG_UNSAFE:
        if pattern.search(text):
            raise Invalid("El SVG tiene scripts, eventos o referencias externas: exportalo plano", "logo_unsafe")
    for href in _SVG_HREF.findall(text):
        if not href.startswith("#"):
            raise Invalid("El SVG referencia algo de afuera del archivo: exportalo plano", "logo_unsafe")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise Invalid("No pudimos leer el SVG", "logo_invalid") from None
    if not root.tag.endswith("svg"):
        raise Invalid("No pudimos leer el SVG", "logo_invalid")
    return data, ".svg", _ratio_from_svg(root)


def _encode_raster(data: bytes) -> tuple[bytes, str, float]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in LOGO_FORMATS:
                raise Invalid("El logo tiene que ser PNG, JPG, WebP o SVG", "logo_format")
            if img.width * img.height > LOGO_MAX_PIXELS:
                raise Invalid("La imagen es demasiado grande", "logo_too_large")
            img = ImageOps.exif_transpose(img)
            if img.height < LOGO_MIN_HEIGHT:
                raise Invalid(f"El logo tiene que medir al menos {LOGO_MIN_HEIGHT} px de alto", "logo_invalid")
            alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
            img = img.convert("RGBA" if alpha else "RGB")
            img.thumbnail(LOGO_BOX, Image.Resampling.LANCZOS)      # solo achica
            out = io.BytesIO()
            if alpha:
                img.save(out, "PNG", optimize=True)
                return out.getvalue(), ".png", round(img.width / img.height, 4)
            img.save(out, "JPEG", quality=90, progressive=True)
            return out.getvalue(), ".jpg", round(img.width / img.height, 4)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise Invalid("No pudimos leer la imagen. Probá con un PNG, JPG o SVG.", "logo_invalid") from None


def encode_logo(data: bytes) -> tuple[bytes, str, float | None]:
    """(contenido a guardar, extension, ancho/alto)."""
    if len(data) > LOGO_MAX_BYTES:
        raise Invalid("El logo pasa de 2 MB", "logo_too_large")
    head = data[:2048].lstrip().lower()
    if head.startswith(b"<") and b"<svg" in head:
        return _check_svg(data)
    return _encode_raster(data)


def logo_path(b: ClientBranding) -> Path | None:
    if not b.logo:
        return None
    path = settings.branding_dir / b.logo
    return path if path.is_file() else None


def _drop_file(name: str | None) -> None:
    if name:
        (settings.branding_dir / name).unlink(missing_ok=True)


def drop_files(client_id: str) -> None:
    """Al borrar el cliente: su carpeta de logos."""
    shutil.rmtree(settings.branding_dir / client_id, ignore_errors=True)


# ---------- estado ----------

def get(s: Session, client: Client) -> ClientBranding | None:
    return s.get(ClientBranding, client.id)


def _get_or_new(s: Session, client: Client) -> ClientBranding:
    b = s.get(ClientBranding, client.id)
    if b is None:
        b = ClientBranding(client_id=client.id, **DEFAULT_COLORS)
        s.add(b)
        s.flush()
    return b


def available(client: Client) -> bool:
    """Si el plan del cliente la incluye (no se ajusta por cliente: sale del tier)."""
    return bool(client.tier.white_label)


def resolved(client: Client, b: ClientBranding | None) -> ClientBranding | None:
    """La marca que ven los usuarios del cliente, o None (panel de Atentina)."""
    return b if b is not None and b.enabled and available(client) else None


def update(s: Session, client: Client, *, enabled: bool, color_primary: str, color_header: str,
           color_accent: str, powered_by: bool, user_id: str | None) -> ClientBranding:
    colors = {k: normalize_color(v, k) for k, v in (("color_primary", color_primary),
                                                     ("color_header", color_header), ("color_accent", color_accent))}
    check_primary(colors["color_primary"])
    b = _get_or_new(s, client)
    b.enabled = enabled
    b.powered_by = powered_by
    b.updated_by = user_id
    for k, v in colors.items():
        setattr(b, k, v)
    s.flush()
    return b


def set_logo(s: Session, client: Client, data: bytes, user_id: str | None) -> ClientBranding:
    content, ext, ratio = encode_logo(data)
    name = f"{client.id}/{hashlib.sha256(content).hexdigest()[:16]}{ext}"
    path = settings.branding_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    b = _get_or_new(s, client)
    old, b.logo, b.logo_ratio, b.updated_by = b.logo, name, ratio, user_id
    s.flush()
    if old != name:
        _drop_file(old)
    return b


def remove_logo(s: Session, client: Client, user_id: str | None) -> ClientBranding:
    b = _get_or_new(s, client)
    old, b.logo, b.logo_ratio, b.updated_by = b.logo, None, None, user_id
    s.flush()
    _drop_file(old)
    return b


# ---------- lo que ve el panel ----------

@dataclass
class PublicBranding:
    slug: str
    name: str
    logo_url: str | None
    logo_ratio: float | None
    color_primary: str
    color_header: str
    color_accent: str
    header_fg: str
    powered_by: bool


def logo_url(client: Client, b: ClientBranding) -> str | None:
    if not b.logo:
        return None
    return f"/api/v1/public/branding/{client.slug}/logo?v={Path(b.logo).stem[:8]}"


def public_of(client: Client, b: ClientBranding) -> PublicBranding:
    return PublicBranding(slug=client.slug, name=client.name, logo_url=logo_url(client, b), logo_ratio=b.logo_ratio,
                          color_primary=b.color_primary, color_header=b.color_header, color_accent=b.color_accent,
                          header_fg=text_on(b.color_header), powered_by=b.powered_by)


def for_client(s: Session, client: Client) -> PublicBranding | None:
    """La marca resuelta del cliente (para `/auth/me`), o None."""
    b = resolved(client, get(s, client))
    return public_of(client, b) if b else None


def login_slug(client: Client, s: Session | None = None) -> str | None:
    """El `c=` de los links al login en los mails: el slug si el cliente tiene la marca activa."""
    s = s or object_session(client)
    return client.slug if s is not None and resolved(client, get(s, client)) else None


def _public(s: Session, slug: str) -> tuple[Client, ClientBranding]:
    client = s.scalar(select(Client).where(Client.slug == slug, Client.active.is_(True)))
    b = resolved(client, get(s, client)) if client else None
    if client is None or b is None:
        raise NotFound("No hay una marca para ese cliente", "branding_not_found")
    return client, b


def public_view(s: Session, slug: str) -> PublicBranding:
    client, b = _public(s, slug)
    return public_of(client, b)


def public_logo(s: Session, slug: str) -> Path:
    _, b = _public(s, slug)
    path = logo_path(b)
    if path is None:
        raise NotFound("El cliente no tiene logo", "logo_not_found")
    return path
