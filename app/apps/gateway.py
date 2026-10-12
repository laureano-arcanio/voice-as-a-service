"""Gateway de las vistas de las apps (docs/APPS_PLAN.md, seccion 5): https://<APPS_PUBLIC_HOST>/...

Con ese Host, app atiende solo esto (AppsHostMiddleware): ni el panel ni la API. Solo GET y HEAD.
- /{cliente}/{app}/{vista}/?k=<token>: valida el link, pone la cookie `ak` (HttpOnly, con path de
  la app y la vida que le queda al link) y redirige a la misma URL sin el token.
- Despues, la cookie: la vista del link (con cualquier parametro) y los estaticos de la app.
La pagina la arma la app (red interna); los headers de seguridad los pone el gateway, no la app.
"""
import html
import re
from urllib.parse import parse_qsl, urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import settings
from ..db import get_sessionmaker, utcnow
from ..models import App, AppLink, Client
from . import client as app_client
from . import links
from .registry import token_of

COOKIE = "ak"
CSP = ("default-src 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; "
       "font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
HEADERS = {
    "Content-Security-Policy": CSP,
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "private, no-store",
}
# Lo unico que se reenvia de la respuesta de la app.
STATIC_TYPES = ("text/css", "image/", "font/", "application/javascript", "text/javascript")

gateway = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _page(status: int, title: str, text: str) -> HTMLResponse:
    body = (f"<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content='width=device-width'>"
            f"<title>{html.escape(title)}</title><body style='font-family:system-ui;max-width:32rem;margin:3rem auto;"
            f"padding:0 1rem;color:#1f2937'><h1 style='font-size:1.25rem'>{html.escape(title)}</h1>"
            f"<p>{html.escape(text)}</p></body></html>")
    return HTMLResponse(body, status, headers=HEADERS)


def _expired() -> HTMLResponse:
    return _page(401, "Link vencido", "Este link ya no sirve. Pedile uno nuevo a tu asistente por WhatsApp.")


def _not_found() -> HTMLResponse:
    return _page(404, "No encontrado", "Esta página no existe.")


def _find_app(s, client_slug: str, app_slug: str) -> App | None:
    app = s.scalar(select(App).where(App.slug == app_slug))
    if app is None or app.client_id is None:
        return None
    client = s.get(Client, app.client_id)
    return app if client is not None and client.slug == client_slug and client.active else None


def _link_from_cookie(s, request: Request, app: App) -> AppLink | None:
    token = request.cookies.get(COOKIE)
    link = links.resolve(s, token) if token else None
    return link if link is not None and link.app_id == app.id else None


async def _proxy(app: App, link: AppLink, path: str, query: str, prefix: str, static: bool) -> Response:
    try:
        r = await app_client.get_view(app.base_url, token_of(app), path, query, f"link:{link.id}", prefix)
    except app_client.AppError:
        return _page(502, "No disponible", "La aplicación no responde. Probá de nuevo en unos minutos.")
    kind = r.headers.get("content-type", "application/octet-stream")
    if r.status_code == 404:
        return _not_found()
    if r.status_code >= 400:
        return _page(502, "No disponible", "La aplicación no pudo mostrar esta página.")
    if static and not kind.startswith(STATIC_TYPES):
        return _not_found()
    if not static and not kind.startswith(("text/html", "text/csv")):
        return _page(502, "No disponible", "La aplicación no devolvió una página.")
    headers = dict(HEADERS)
    # Exportar a Excel (contrato v1.1): la vista con ?formato=csv baja un archivo.
    if kind.startswith("text/csv"):
        name = re.sub(r"[^\w.-]", "", r.headers.get("content-disposition", "").partition("filename=")[2]) or "datos.csv"
        headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return Response(r.content, r.status_code, media_type=kind, headers=headers)


@gateway.api_route("/{client_slug}/{app_slug}/static/{path:path}", methods=["GET", "HEAD"])
async def static(client_slug: str, app_slug: str, path: str, request: Request):
    with get_sessionmaker()() as s:
        app = _find_app(s, client_slug, app_slug)
        link = _link_from_cookie(s, request, app) if app else None
    if app is None or link is None or ".." in path.split("/"):
        return _not_found()
    return await _proxy(app, link, f"/static/{path}", "", f"/{client_slug}/{app_slug}", static=True)


@gateway.api_route("/{client_slug}/{app_slug}/{view}/", methods=["GET", "HEAD"])
async def view(client_slug: str, app_slug: str, view: str, request: Request):
    params = [(k, v) for k, v in parse_qsl(request.url.query, keep_blank_values=True) if k != "k"]
    token = request.query_params.get("k")
    with get_sessionmaker()() as s:
        app = _find_app(s, client_slug, app_slug)
        if app is None:
            return _not_found()
        if token:
            link = links.resolve(s, token)
            if link is None or link.app_id != app.id or link.view != view:
                return _expired()
            link.opens += 1
            link.last_opened_at = utcnow()
            s.commit()
            clean = request.url.path + (f"?{urlencode(params)}" if params else "")
            response = RedirectResponse(clean, 303, headers=HEADERS)
            response.set_cookie(COOKIE, token, max_age=max(int((link.expires_at - utcnow()).total_seconds()), 1),
                                path=f"/{client_slug}/{app_slug}/", httponly=True, samesite="lax",
                                secure=settings.apps_public_scheme == "https")
            return response
        link = _link_from_cookie(s, request, app)
        if link is None or link.view != view:
            return _expired()
    return await _proxy(app, link, f"/views/{view}", urlencode(params), f"/{client_slug}/{app_slug}", static=False)


@gateway.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def other(path: str):
    return _not_found()


class AppsHostMiddleware:
    """Con Host == APPS_PUBLIC_HOST, el pedido va al gateway y no llega al panel ni a la API."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and settings.apps_public_host:
            host = dict(scope["headers"]).get(b"host", b"").decode("latin-1").split(":")[0].lower()
            if host == settings.apps_public_host.lower():
                await gateway(scope, receive, send)
                return
        await self.app(scope, receive, send)
