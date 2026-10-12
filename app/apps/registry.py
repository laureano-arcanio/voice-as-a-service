"""Registro de apps (docs/APPS_PLAN.md, seccion 9): el deploy de atentina-apps llama a
POST /apps con slug, base_url y APP_TOKEN; Atentina pide /health y /manifest, valida el contrato y
guarda. El token va cifrado con WA_TOKEN_KEY (app/whatsapp/crypto.py)."""
import asyncio
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import App
from ..services.errors import Invalid
from ..whatsapp import crypto
from . import client as app_client

logger = logging.getLogger(__name__)

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")
MAX_TOOLS = 20
MAX_DESCRIPTION = 400
Kind = Literal["read", "write", "destructive", "send"]
CONFIRM_KINDS = {"destructive", "send"}


class ViewParam(BaseModel):
    type: str = "string"
    default: Any = None
    description: str = ""


class ViewSpec(BaseModel):
    name: str
    title: str
    description: str = ""
    params: dict[str, ViewParam] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    name: str
    description: str
    kind: Kind
    input_schema: dict = Field(default_factory=lambda: {"type": "object", "properties": {}})


class JobSpec(BaseModel):
    """Aviso programado (contrato v1.1): a la hora, en los dias ISO (1 = lunes; vacio = todos)."""
    name: str
    title: str = ""
    hora: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    dias: list[int] = Field(default_factory=list)


class Manifest(BaseModel):
    spec: int
    slug: str
    client: str = ""
    name: str
    version: str
    core: str = ""
    description: str = ""
    views: list[ViewSpec] = Field(default_factory=list)
    tools: list[ToolSpec] = Field(default_factory=list)
    jobs: list[JobSpec] = Field(default_factory=list)


def validate_manifest(data: dict, slug: str) -> Manifest:
    """Invalid con el motivo si no cumple el contrato v1."""
    try:
        m = Manifest.model_validate(data)
    except ValidationError as e:
        raise Invalid(f"Manifest invalido: {e.errors()[0]['loc']}: {e.errors()[0]['msg']}") from None
    problems = []
    if m.spec != 1:
        problems.append(f"spec {m.spec} (se espera 1)")
    if m.slug != slug:
        problems.append(f"el slug del manifest es {m.slug!r}, no {slug!r}")
    if len(m.tools) > MAX_TOOLS:
        problems.append(f"{len(m.tools)} herramientas (tope {MAX_TOOLS})")
    names = [t.name for t in m.tools] + [v.name for v in m.views] + [j.name for j in m.jobs]
    problems += [f"nombre invalido {n!r}" for n in names if not NAME_RE.fullmatch(n)]
    if len({t.name for t in m.tools}) != len(m.tools) or len({v.name for v in m.views}) != len(m.views):
        problems.append("nombres repetidos")
    problems += [f"{j.name}: dias fuera de 1..7" for j in m.jobs if any(d not in range(1, 8) for d in j.dias)]
    problems += [f"{t.name}: descripcion de mas de {MAX_DESCRIPTION} caracteres"
                 for t in m.tools if len(t.description) > MAX_DESCRIPTION]
    if problems:
        raise Invalid("Manifest invalido: " + "; ".join(problems))
    return m


def token_of(app: App) -> str:
    return crypto.decrypt(app.token_enc)


def manifest_of(app: App) -> Manifest:
    return Manifest.model_validate(app.manifest)


def register(s: Session, slug: str, base_url: str, token: str) -> App:
    """Alta o actualizacion (misma app, version nueva). No cambia el cliente asignado."""
    if not SLUG_RE.fullmatch(slug):
        raise Invalid("slug: minusculas, numeros y - (hasta 64)")
    if not re.fullmatch(r"https?://[^\s/]+(:\d+)?/?", base_url):
        raise Invalid("base_url: http://host:puerto, sin path")
    try:
        app_client.get_json(base_url, token, "/health")
        manifest = validate_manifest(app_client.get_json(base_url, token, "/manifest"), slug)
    except app_client.AppError as e:
        raise Invalid(f"La app no responde bien: {e}") from None
    app = s.scalar(select(App).where(App.slug == slug))
    if app is None:
        app = App(slug=slug)
        s.add(app)
    app.name = manifest.name
    app.base_url = base_url.rstrip("/")
    app.token_enc = crypto.encrypt(token)
    app.version = manifest.version
    app.manifest = manifest.model_dump(mode="json")
    app.status, app.last_error, app.last_health_at = "ok", None, utcnow()
    s.flush()
    return app


def refresh(s: Session, app: App) -> App:
    """Relee /health y /manifest con el token guardado."""
    try:
        token = token_of(app)
        app_client.get_json(app.base_url, token, "/health")
        manifest = validate_manifest(app_client.get_json(app.base_url, token, "/manifest"), app.slug)
    except app_client.AppError as e:
        app.status, app.last_error = "down", str(e)[:255]
        return app
    except Invalid as e:
        app.status, app.last_error = "invalid", e.message[:255]
        return app
    app.name, app.version, app.manifest = manifest.name, manifest.version, manifest.model_dump(mode="json")
    app.status, app.last_error, app.last_health_at = "ok", None, utcnow()
    return app


def check_health(sessions: sessionmaker[Session]) -> int:
    """Pide /health a cada app; devuelve cuantas no responden."""
    down = 0
    with sessions() as s:
        for app in s.scalars(select(App)):
            try:
                app_client.get_json(app.base_url, token_of(app), "/health", timeout=5)
            except Exception as e:  # noqa: BLE001 - una app rota no corta el barrido
                down += 1
                if app.status != "down":
                    logger.warning("apps: %s no responde: %s", app.slug, e)
                app.status, app.last_error = "down", str(e)[:255]
                continue
            if app.status == "down":
                app.status, app.last_error = "ok", None
            app.last_health_at = utcnow()
        s.commit()
    return down


async def health_loop(interval: float | None = None) -> None:
    from ..db import get_sessionmaker

    interval = interval or settings.apps_health_seconds
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(check_health, get_sessionmaker())
        except Exception:
            logger.exception("apps: fallo el chequeo de salud")
