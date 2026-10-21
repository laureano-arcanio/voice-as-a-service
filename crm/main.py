"""CRM de ventas (docs/CRM_PLAN.md): API en /api, UI en / (web/crm.html), loops de envio, eventos y GA.

Local: el puerto se publica solo en 127.0.0.1 (docker-compose.yml, servicio crm).
"""
import asyncio
import contextlib
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import DataError, IntegrityError

from .config import settings
from .routes import leads, outreach
from .services import ga, sending
from .services.errors import CrmError

logger = logging.getLogger("crm")
PROBLEM = "application/problem+json"


def problem(status: int, title: str, detail: str, **extra) -> JSONResponse:
    return JSONResponse({"type": "about:blank", "title": title, "status": status, "detail": detail, **extra},
                        status_code=status, media_type=PROBLEM)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    tasks = []
    if settings.loops:
        tasks = [asyncio.create_task(f()) for f in (sending.send_loop, sending.events_loop, ga.ga_loop)]
    yield
    for t in tasks:
        t.cancel()


def create_app() -> FastAPI:
    if not settings.api_key:
        raise RuntimeError("falta CRM_API_KEY en .env")
    app = FastAPI(title="Atentina CRM", version="1", lifespan=lifespan, docs_url="/api/docs",
                  openapi_url="/api/openapi.json", redoc_url=None,
                  description="CRM de ventas de Atentina. Contrato y ejemplos en docs/CRM_API.md. "
                              "Auth: `Authorization: Bearer <key>`. Errores en application/problem+json.")

    @app.exception_handler(CrmError)
    async def _crm_error(_: Request, e: CrmError):
        extra = {"field": e.field} if e.field else {}
        return problem(e.status, e.title, e.detail, **extra)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        errors = [{"field": ".".join(str(x) for x in err["loc"][1:]), "msg": err["msg"]} for err in e.errors()]
        return problem(422, "Datos invalidos", "; ".join(f"{x['field']}: {x['msg']}" for x in errors),
                       errors=errors)

    @app.exception_handler(DataError)
    async def _data_error(_: Request, e: DataError):
        detail = str(e.orig).split("\n")[0] if e.orig else "dato invalido"
        return problem(422, "Datos invalidos", detail)

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, e: IntegrityError):
        detail = str(e.orig).split("\n")[0] if e.orig else "conflicto"
        return problem(409, "Conflicto", detail)

    app.include_router(leads.router)
    app.include_router(outreach.router)

    @app.get("/health", include_in_schema=False)
    def health():
        return {"ok": True}

    dist = settings.web_dist_dir
    page = dist / "crm.html"
    if page.is_file():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def ui(path: str):
            # La SPA: cualquier ruta que no sea /api devuelve la pagina.
            if path.startswith("api/"):
                return problem(404, "No existe", f"/{path}")
            file = (dist / path).resolve()
            if path and file.is_file() and dist.resolve() in file.parents and file.suffix != ".html":
                return FileResponse(file)  # logo, favicon y demas archivos del build
            return FileResponse(page)
    else:
        logger.warning("Sin build de la UI en %s (cd web && npm run build): solo API", page)
    return app


app = create_app() if settings.api_key else FastAPI(title="Atentina CRM (sin CRM_API_KEY)")
