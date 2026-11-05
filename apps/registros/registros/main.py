"""App de fichas Registros: API /v1 para la plataforma y panel propio. Sin código de la plataforma."""
import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import api, auth, panel
from .config import settings
from .db import get_sessionmaker
from .models import Tenant

logger = logging.getLogger("registros")

DB_RETRY_MIN_SECONDS = 2
DB_RETRY_MAX_SECONDS = 30
PANEL_STATIC = Path(panel.__file__).parent / "static"

# Una ruta del panel puede poner los suyos: estos son los valores por defecto.
DEFAULT_HEADERS = {
    "Referrer-Policy": "no-referrer",  # el link /c/<token> no sale por Referer
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",  # datos de salud
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'",
}


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in DEFAULT_HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, with_headers)


def db_ready() -> bool:
    """Lee una tabla y no SELECT 1: una restauración con otro dueño o sin migrar también da falla."""
    try:
        with get_sessionmaker()() as s:
            s.execute(select(Tenant.id).limit(1))
        return True
    except SQLAlchemyError:
        return False


async def _wait_for_db() -> None:
    """Si la app arranca antes que db no se cae: sigue intentando y lo deja en el log. Cada pedido
    conecta por su cuenta, así que al volver la base no hace falta reiniciar."""
    delay = DB_RETRY_MIN_SECONDS
    warned = False
    while not await asyncio.to_thread(db_ready):
        if not warned:
            logger.warning("Sin base al iniciar: reintentando hasta %s s entre intentos", DB_RETRY_MAX_SECONDS)
            warned = True
        await asyncio.sleep(delay)
        delay = min(delay * 2, DB_RETRY_MAX_SECONDS)
    if warned:
        logger.warning("Base conectada")


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_wait_for_db())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def create_app() -> FastAPI:
    app = FastAPI(title="Registros", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(auth.CsrfMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        # Sin `input`: el detalle por defecto repite lo recibido, y un error no lleva datos personales.
        errors = [{"loc": [str(x) for x in err["loc"]], "msg": err["msg"]} for err in e.errors()]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.exception_handler(OperationalError)
    async def _db_down(_: Request, e: OperationalError):
        # 503: quien llama reintenta por transporte. El mensaje del driver no sale del log.
        logger.warning("Base no disponible: %s", type(e.orig).__name__)
        return JSONResponse({"detail": "Base no disponible"}, status_code=503)

    @app.get("/health", include_in_schema=False)
    def health():
        if settings.session_secret and db_ready():
            return {"status": "ok"}
        return JSONResponse({"status": "unavailable"}, status_code=503)

    app.include_router(auth.router)
    app.include_router(api.router)
    # Antes que el panel, por si sus rutas capturan cualquier camino.
    app.mount("/static", StaticFiles(directory=PANEL_STATIC), name="static")
    app.include_router(panel.router)
    return app


app = create_app()
