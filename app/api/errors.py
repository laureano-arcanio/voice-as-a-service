import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..services.errors import ServiceError

logger = logging.getLogger(__name__)


def install(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error(_: Request, exc: ServiceError) -> JSONResponse:
        # Mismo formato que HTTPException ({"detail": ...}) mas un codigo estable y
        # errores puntuales para la UI (ej. por campo de la definicion de un agente).
        retry_after = getattr(exc, "retry_after", None)
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": exc.message, "code": exc.code, "errors": exc.details},
                            headers={"Retry-After": str(retry_after)} if retry_after else None)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # El 422 de FastAPI sin `input` (en el login seria la clave mandada), `ctx` ni `url`.
        detail = [{k: v for k, v in e.items() if k not in ("input", "ctx", "url")} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(detail)})

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Mismo formato para lo inesperado; el detalle queda en el log, no en la respuesta.
        logger.exception("error no manejado en %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Error interno", "code": "internal_error", "errors": []})
