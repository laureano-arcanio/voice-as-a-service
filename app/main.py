"""App HTTP: API en /api/v1 y la UI (SPA de web/, ya compilada) en el resto.

Publicada a internet por el tunel (app.atentina.com.ar, sin Cloudflare Access): tope de
cuerpo, chequeo de Origin (CSRF) y headers de seguridad con CSP en api/http.py.
"""
import asyncio
import contextlib
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from .api import errors
from .api.deps import _bearer, get_db, get_principal, require_admin
from .api.http import (
    BodyLimitMiddleware,
    CsrfMiddleware,
    HttpsRedirectMiddleware,
    SecurityHeadersMiddleware,
)
from .api.routers import (
    agents,
    api_keys,
    auth,
    calls,
    clients,
    conversations,
    demo,
    phone_numbers,
    tiers,
    users,
    voices,
    whatsapp,
)
from .config import settings
from .services.demo import allowed_origins
from .whatsapp import webhook as wa_webhook
from .whatsapp.service import sweep_loop

logger = logging.getLogger(__name__)
API_PREFIX = "/api/v1"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Fin de los chats de WhatsApp vencidos, como el corte de una llamada (app/whatsapp/service.py).
    sweep = asyncio.create_task(sweep_loop())
    yield
    sweep.cancel()


def create_app() -> FastAPI:
    if not settings.auth_secret:
        raise RuntimeError("Falta AUTH_SECRET en .env (firma de las sesiones): `openssl rand -hex 32`")
    # Docs y OpenAPI propios (abajo), no los publicos de FastAPI. `make openapi` usa app.openapi().
    app = FastAPI(title="Voice as a Service", version="1.0.0", docs_url=None, openapi_url=None, redoc_url=None,
                  lifespan=lifespan)
    errors.install(app)
    wa_webhook.install_logging()
    # Middlewares: el ultimo agregado es el de afuera. Orden de afuera hacia adentro:
    # http -> https por el tunel, headers (tambien en los 403/413), CORS (la demo de la
    # landing, sin credenciales), tope de cuerpo y CSRF.
    app.add_middleware(CsrfMiddleware)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(), allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"], expose_headers=["Retry-After"], max_age=600)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HttpsRedirectMiddleware)

    api = APIRouter(prefix=API_PREFIX)
    for module in (auth, tiers, clients, phone_numbers, agents, users, api_keys, calls, conversations, voices,
                   whatsapp, demo):
        api.include_router(module.router)
    app.include_router(api)
    _mount_docs(app)
    # Fuera de /api/v1 y antes de _mount_spa (su catch-all es GET y tragaria /wa/webhook).
    app.include_router(wa_webhook.router)

    @app.get("/health", include_in_schema=False)
    def health():
        return {"ok": True}

    _mount_spa(app)
    return app


SWAGGER_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
               "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
               "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'")


def _docs_access(request: Request, db: Annotated[object, Depends(get_db)],
                 creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> None:
    """API_DOCS: off -> 404; admin -> sesion o token de admin; public -> sin auth."""
    if settings.api_docs == "off":
        raise HTTPException(404)
    if settings.api_docs == "admin":
        require_admin(get_principal(request, db, creds))


def _mount_docs(app: FastAPI) -> None:
    """Swagger y OpenAPI en /api/v1, solo para admins por defecto (settings.api_docs)."""
    @app.get(f"{API_PREFIX}/openapi.json", include_in_schema=False, dependencies=[Depends(_docs_access)])
    def openapi_json():
        return JSONResponse(app.openapi())

    @app.get(f"{API_PREFIX}/docs", include_in_schema=False, dependencies=[Depends(_docs_access)])
    def swagger():
        html = get_swagger_ui_html(openapi_url=f"{API_PREFIX}/openapi.json", title=f"{app.title} - API")
        html.headers["Content-Security-Policy"] = SWAGGER_CSP
        return html


def _mount_spa(app: FastAPI) -> None:
    """Sirve el build de la SPA; cualquier ruta que no sea de la API devuelve
    index.html y la resuelve React Router."""
    dist = settings.web_dist_dir
    index = dist / "index.html"
    if not index.exists():
        logger.warning("Sin build de la UI en %s (cd web && npm run build): solo API", dist)
        return
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        file = (dist / path).resolve()
        if path and file.is_file() and dist.resolve() in file.parents:
            return FileResponse(file)
        # index.html sin cache: apunta a los assets con hash de cada build.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
