"""Apps por cliente (docs/APPS_PLAN.md): registro desde el deploy de atentina-apps, inventario,
asignacion a un cliente y links a sus vistas.

- Admin: registra, relee, asigna, libera y borra. El deploy (make register de atentina-apps)
  registra y relee con APPS_DEPLOY_TOKEN, sin usuario: las API keys son siempre de un cliente.
- Cliente (usuario o API key): ve sus apps y crea o revoca links a sus vistas.
"""
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from ...apps import client as app_client
from ...apps import jobs, links, registry
from ...config import settings
from ...db import get_sessionmaker
from ...models import App, AppLink, Client
from ...services.errors import Conflict, Invalid, NotFound
from ..deps import (
    DB,
    AdminPrincipal,
    CurrentPrincipal,
    _bearer,
    get_principal,
    require_admin,
    scoped_client_id,
)
from ..schemas import (
    AppJobOut,
    AppJobRunOut,
    AppLinkIn,
    AppLinkOut,
    AppOut,
    AppRegisterIn,
    AppToolOut,
    AppViewOut,
    AssignIn,
)
from .clients import get_client

router = APIRouter(prefix="/apps", tags=["apps"])


def deployer(request: Request, db: DB,
             creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> None:
    """APPS_DEPLOY_TOKEN, o un admin."""
    token = settings.apps_deploy_token
    if creds and token and secrets.compare_digest(creds.credentials.encode(), token.encode()):
        return
    require_admin(get_principal(request, db, creds))


def _out(db, app: App) -> AppOut:
    client = db.get(Client, app.client_id) if app.client_id else None
    manifest = app.manifest or {}
    return AppOut.model_validate(app).model_copy(update={
        "client_name": client.name if client else None,
        "views": [AppViewOut(name=v["name"], title=v["title"], description=v.get("description", ""))
                  for v in manifest.get("views", [])],
        "tools": [AppToolOut(name=t["name"], kind=t["kind"], description=t["description"])
                  for t in manifest.get("tools", [])],
        "jobs": [AppJobOut(**{k: j[k] for k in ("name", "title", "hora", "dias") if k in j})
                 for j in manifest.get("jobs", [])],
    })


def _get(db, p, app_id: str) -> App:
    app = db.get(App, app_id)
    # Una app del inventario solo la ve el admin.
    if app is None or not p.can_access(app.client_id):
        raise NotFound("App inexistente")
    return app


@router.post("", response_model=AppOut, dependencies=[Depends(deployer)])
def register_app(body: AppRegisterIn, db: DB):
    """Alta o version nueva (la llama `make register` de atentina-apps). Atentina pide /health y
    /manifest con el token; 422 si no responde o el manifest no cumple el contrato."""
    app = registry.register(db, body.slug, body.base_url, body.token)
    db.commit()
    return _out(db, app)


@router.get("", response_model=list[AppOut])
def list_apps(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Admin: todas (client_id: las de ese cliente). Cliente: las suyas."""
    q = select(App).order_by(App.slug)
    if cid := scoped_client_id(p, client_id):
        q = q.where(App.client_id == cid)
    return [_out(db, a) for a in db.scalars(q)]


@router.get("/{app_id}", response_model=AppOut)
def get_app(app_id: str, p: CurrentPrincipal, db: DB):
    return _out(db, _get(db, p, app_id))


@router.post("/{app_id}/refresh", response_model=AppOut, dependencies=[Depends(deployer)])
def refresh_app(app_id: str, db: DB):
    """Relee /health y /manifest (por ejemplo, despues de levantar una version nueva)."""
    app = db.get(App, app_id)
    if app is None:
        raise NotFound("App inexistente")
    app = registry.refresh(db, app)
    db.commit()
    return _out(db, app)


@router.post("/{app_id}/assign", response_model=AppOut)
def assign_app(app_id: str, body: AssignIn, p: AdminPrincipal, db: DB):
    app = _get(db, p, app_id)
    get_client(db, p, body.client_id)
    if app.client_id not in (None, body.client_id):
        raise Conflict("La app ya es de otro cliente: liberala antes", "app_assigned")
    app.client_id = body.client_id
    db.commit()
    return _out(db, app)


@router.post("/{app_id}/release", response_model=AppOut)
def release_app(app_id: str, p: AdminPrincipal, db: DB):
    """La devuelve al inventario. Sus links dejan de abrir y los agentes del cliente pierden
    sus herramientas (las definiciones no cambian: al guardarlas de nuevo, la validacion avisa)."""
    app = _get(db, p, app_id)
    app.client_id = None
    for link in db.scalars(select(AppLink).where(AppLink.app_id == app.id, AppLink.revoked_at.is_(None))):
        links.revoke(link)
    db.commit()
    return _out(db, app)


@router.delete("/{app_id}", status_code=204)
def delete_app(app_id: str, p: AdminPrincipal, db: DB):
    """Solo del inventario. No toca el contenedor (eso es `make down` en atentina-apps)."""
    app = _get(db, p, app_id)
    if app.client_id is not None:
        raise Conflict("La app está asignada a un cliente: liberala antes de borrarla", "app_assigned")
    db.delete(app)
    db.commit()


@router.post("/{app_id}/jobs/{job}/run", response_model=AppJobRunOut)
async def run_job(app_id: str, job: str, p: AdminPrincipal, db: DB):
    """Corre un aviso programado ahora (prueba): llama a la app y le manda el aviso a los
    operadores del cliente, en APPS_OUTBOX_MODE. No cuenta como la corrida del dia."""
    app = _get(db, p, app_id)
    if job not in {j["name"] for j in (app.manifest or {}).get("jobs", [])}:
        raise NotFound(f"La app no tiene el job {job!r}")
    try:
        return await jobs.run_job(get_sessionmaker(), app.id, job)
    except app_client.AppError as e:
        raise Invalid(f"La app no respondió el job: {e}") from None


@router.get("/{app_id}/links", response_model=list[AppLinkOut])
def list_links(app_id: str, p: CurrentPrincipal, db: DB):
    app = _get(db, p, app_id)
    q = select(AppLink).where(AppLink.app_id == app.id).order_by(AppLink.created_at.desc()).limit(200)
    return list(db.scalars(q))


@router.post("/{app_id}/links", response_model=AppLinkOut, status_code=201)
def create_link(app_id: str, body: AppLinkIn, p: CurrentPrincipal, db: DB):
    """Un link a una vista (el mismo que arma el asistente). La URL solo se ve en esta respuesta."""
    app = _get(db, p, app_id)
    url, link = links.create_link(db, app, body.view, body.params, f"{p.kind}:{p.id}")
    db.commit()
    return AppLinkOut.model_validate(link).model_copy(update={"url": url})


@router.delete("/{app_id}/links/{link_id}", status_code=204)
def revoke_link(app_id: str, link_id: str, p: CurrentPrincipal, db: DB):
    app = _get(db, p, app_id)
    link = db.get(AppLink, link_id)
    if link is None or link.app_id != app.id:
        raise NotFound("Link inexistente")
    links.revoke(link)
    db.commit()
