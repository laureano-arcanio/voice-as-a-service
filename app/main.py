"""App HTTP: API en /api/v1 y la UI (SPA de web/, ya compilada) en el resto."""
import logging

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import errors
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

logger = logging.getLogger(__name__)
API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    if not settings.auth_secret:
        raise RuntimeError("Falta AUTH_SECRET en .env (firma de las sesiones): `openssl rand -hex 32`")
    app = FastAPI(title="Voice as a Service", version="1.0.0", docs_url=f"{API_PREFIX}/docs",
                  openapi_url=f"{API_PREFIX}/openapi.json", redoc_url=None)
    errors.install(app)
    wa_webhook.install_logging()
    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(), allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"], expose_headers=["Retry-After"], max_age=600)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    api = APIRouter(prefix=API_PREFIX)
    for module in (auth, tiers, clients, phone_numbers, agents, users, api_keys, calls, conversations, voices,
                   whatsapp, demo):
        api.include_router(module.router)
    app.include_router(api)
    # Fuera de /api/v1 y antes de _mount_spa (su catch-all es GET y tragaria /wa/webhook).
    app.include_router(wa_webhook.router)

    @app.get("/health", include_in_schema=False)
    def health():
        return {"ok": True}

    _mount_spa(app)
    return app


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
