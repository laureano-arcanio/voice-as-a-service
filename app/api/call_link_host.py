"""Pagina publica del link para llamar a un agente (docs/LINK_LLAMADA_PLAN.md).

- `GET /llamar/{token}`: web/dist/llamar.html (entrada aparte del build de web/) con el titulo, las
  metas de la vista previa (og:*) y los datos del link completados en el server. Tiene su propia CSP
  (Turnstile y el LiveKit para navegadores) y es la unica pagina que permite el microfono.
- CallLinkHostMiddleware: con el Host de CALL_LINK_BASE_URL (llamar.atentina.com.ar), `/<token>` va a
  esa pagina y solo pasan sus assets y la API publica de links; el panel y el resto de la API no existen
  en ese host.
"""
import html
import json
import re
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import settings
from ..services import call_links as service
from ..services.errors import NotFound
from .deps import DB

router = APIRouter(include_in_schema=False)

TOKEN_PATH = re.compile(r"^/([A-Za-z0-9_-]{8,32})/?$")
# Lo unico que se sirve en el host del link, ademas de la pagina.
ALLOWED_PREFIXES = ("/assets/", "/api/v1/public/call-links/")
ALLOWED_FILES = ("/favicon.svg", "/atentina-mark.svg", "/robots.txt")
PAGE = "llamar.html"
HEAD_MARK = "<!--LINK_HEAD-->"
DATA_MARK = "<!--LINK_DATA-->"
TURNSTILE = "https://challenges.cloudflare.com"


def link_host() -> str:
    return (urlparse(settings.call_link_base_url).hostname or "").lower() if settings.call_link_base_url else ""


def _livekit_origins() -> str:
    """wss:// y https:// del LiveKit que usan los navegadores (el cliente prueba los dos)."""
    parsed = urlparse(settings.demo_livekit_url or settings.livekit_url)
    if not parsed.hostname:
        return ""
    host = parsed.netloc
    secure = parsed.scheme in ("wss", "https")
    return f"{'wss' if secure else 'ws'}://{host} {'https' if secure else 'http'}://{host}"


def content_security_policy() -> str:
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' {TURNSTILE}",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        f"connect-src 'self' {_livekit_origins()}".rstrip(),
        f"frame-src {TURNSTILE}",
        "media-src 'self' blob: mediastream:",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex",
    "Permissions-Policy": "microphone=(self), camera=(), geolocation=(), payment=()",
}


def _json_for_html(data: dict) -> str:
    # Dentro de <script type="application/json">: que un texto del cliente no pueda cerrar la etiqueta.
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render(template: str, view: service.PublicView | None) -> str:
    """La pagina con las metas y los datos del link. Sin `view`: la del link inexistente o revocado."""
    if view is None:
        title, description = "Link no disponible", "Este link ya no está activo."
        data = {"found": False}
    else:
        title = f"Hablá con {view.display_name} · {view.company_name}"
        description = view.subtitle or f"Llamá a {view.company_name} desde el navegador."
        data = {"found": True, "token": view.token, "display_name": view.display_name,
                "company_name": view.company_name, "subtitle": view.subtitle,
                "max_call_seconds": view.max_call_seconds, "records_audio": view.records_audio,
                "available": view.available, "turnstile_site_key": settings.turnstile_site_key,
                "home_url": settings.site_url}
    e = html.escape
    head = "\n    ".join([
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(description)}" />',
        '<meta name="robots" content="noindex, nofollow" />',
        f'<meta property="og:title" content="{e(title)}" />',
        f'<meta property="og:description" content="{e(description)}" />',
        '<meta property="og:type" content="website" />',
        f'<meta property="og:url" content="{e(service.url_for_token(view.token)) if view else ""}" />',
        '<meta name="twitter:card" content="summary" />',
    ])
    body = f'<script type="application/json" id="link-data">{_json_for_html(data)}</script>'
    return template.replace(HEAD_MARK, head, 1).replace(DATA_MARK, body, 1)


@router.get("/llamar/{token}")
def link_page(token: str, db: DB):
    page = settings.web_dist_dir / PAGE
    if not page.exists():
        return HTMLResponse("Sin build de la UI (cd web && npm run build)", status_code=503)
    try:
        view, status = service.public_view(db, token), 200
    except NotFound:
        view, status = None, 404
    headers = {**HEADERS, "Content-Security-Policy": content_security_policy()}
    return HTMLResponse(render(page.read_text(encoding="utf-8"), view), status_code=status, headers=headers)


class CallLinkHostMiddleware:
    """Con Host == el de CALL_LINK_BASE_URL: `/<token>` -> `/llamar/<token>`, `/` -> la landing,
    pasan los assets y la API publica de links, y el resto es 404."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        host = link_host()
        if scope["type"] != "http" or not host:
            return await self.app(scope, receive, send)
        request_host = dict(scope["headers"]).get(b"host", b"").decode("latin-1").split(":")[0].lower()
        if request_host != host:
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path == "/":
            return await RedirectResponse(settings.site_url, status_code=302)(scope, receive, send)
        if match := TOKEN_PATH.match(path):
            new = f"/llamar/{match.group(1)}"
            scope = {**scope, "path": new, "raw_path": new.encode()}
            return await self.app(scope, receive, send)
        if path.startswith(ALLOWED_PREFIXES) or path in ALLOWED_FILES:
            return await self.app(scope, receive, send)
        await HTMLResponse("No encontrado", status_code=404)(scope, receive, send)
