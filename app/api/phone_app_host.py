"""Teléfono del equipo en su host (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 16).

- `GET /movil`: web/dist/telefono.html, entrada aparte del build de web/ (React, la misma API y el mismo
  CallProvider que el teléfono del panel, con una UI tipo app de teléfono de Android). Con la sesión del panel.
- PhoneAppHostMiddleware: con el Host de PHONE_APP_BASE_URL (telefono.atentina.com.ar), `/` es esa página y solo
  pasan la API, los assets y los íconos; el panel, el MCP, OAuth y los webhooks no existen en ese host. La cookie
  de sesión es de cada host (sin Domain): se ingresa ahí con el mismo usuario y clave.
"""
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import settings

router = APIRouter(include_in_schema=False)

PAGE = "telefono.html"
PAGE_PATH = "/movil"
ALLOWED_PREFIXES = ("/api/v1/", "/assets/")
ALLOWED_FILES = ("/favicon.svg", "/atentina-mark.svg", "/robots.txt", "/telefono.webmanifest")
# Los docs de la API son del panel (solo admin): tampoco acá.
BLOCKED_PREFIXES = ("/api/v1/docs", "/api/v1/openapi.json")


def phone_host() -> str:
    return (urlparse(settings.phone_app_base_url).hostname or "").lower() if settings.phone_app_base_url else ""


@router.get(PAGE_PATH)
def phone_page():
    page = settings.web_dist_dir / PAGE
    if not page.exists():
        return HTMLResponse("Sin build de la UI (cd web && npm run build)", status_code=503)
    # Sin cache: apunta a los assets con hash de cada build. La CSP es la del panel (http.py).
    return FileResponse(page, headers={"Cache-Control": "no-cache", "X-Robots-Tag": "noindex"})


class PhoneAppHostMiddleware:
    """Con Host == el de PHONE_APP_BASE_URL: `/` -> `/movil`, pasan la API, los assets y los íconos, y el resto
    es 404."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        host = phone_host()
        if scope["type"] != "http" or not host:
            return await self.app(scope, receive, send)
        request_host = dict(scope["headers"]).get(b"host", b"").decode("latin-1").split(":")[0].lower()
        if request_host != host:
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path == "/":
            scope = {**scope, "path": PAGE_PATH, "raw_path": PAGE_PATH.encode()}
            return await self.app(scope, receive, send)
        if (path.startswith(ALLOWED_PREFIXES) and not path.startswith(BLOCKED_PREFIXES)) or path in ALLOWED_FILES:
            return await self.app(scope, receive, send)
        await HTMLResponse("No encontrado", status_code=404)(scope, receive, send)
