"""Marca blanca del panel (docs/ARQUITECTURA.md).

- `/clients/{client_id}/branding`: la configura un admin (colores, logo, prendida o no).
- `/public/branding/{slug}`: lo que necesita la pagina de login (`/login?c=<slug>`), sin auth; 404 si la
  marca no esta activa o el plan no la incluye. El logo se sirve con cache de un año (la URL cambia con el archivo).
"""
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from ...models import Client
from ...services import branding as service
from ...services.errors import NotFound
from ..deps import DB, AdminPrincipal
from ..schemas import BrandingIn, BrandingOut, BrandingPublicOut

router = APIRouter(tags=["branding"])

PUBLIC_404 = {404: {"description": "El cliente no existe, no tiene la marca activa o su plan no la incluye"}}
COLOR_422 = {422: {"description": "color_format, o color_contrast (el primario no da 4,5:1 con blanco; "
                                  "`errors[0].suggested` trae uno que si)"}}
LOGO_422 = {422: {"description": "logo_format, logo_too_large, logo_invalid o logo_unsafe (SVG con scripts o "
                                 "referencias externas)"}}
LOGO_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"}


def _client(db, client_id: str) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise NotFound("Cliente inexistente", "client_not_found")
    return client


def _out(db, client: Client) -> BrandingOut:
    b = service.get(db, client)
    if b is None:
        return BrandingOut(enabled=False, logo_url=None, logo_ratio=None, powered_by=True,
                           available=service.available(client), active=False, header_fg=service.text_on("#ffffff"),
                           **service.DEFAULT_COLORS)
    return BrandingOut(enabled=b.enabled, logo_url=service.logo_url(client, b), logo_ratio=b.logo_ratio,
                       color_primary=b.color_primary, color_header=b.color_header, color_accent=b.color_accent,
                       powered_by=b.powered_by, available=service.available(client),
                       active=service.resolved(client, b) is not None, header_fg=service.text_on(b.color_header))


@router.get("/clients/{client_id}/branding", response_model=BrandingOut)
def read_branding(client_id: str, _: AdminPrincipal, db: DB):
    """La marca del cliente: lo guardado, si su plan la incluye (`available`) y si se esta mostrando (`active`)."""
    return _out(db, _client(db, client_id))


@router.put("/clients/{client_id}/branding", response_model=BrandingOut, responses=COLOR_422)
def update_branding(client_id: str, body: BrandingIn, p: AdminPrincipal, db: DB):
    """Colores, si se muestra y la linea "Con tecnologia de Atentina". El logo va aparte (`PUT .../logo`)."""
    client = _client(db, client_id)
    service.update(db, client, enabled=body.enabled, color_primary=body.color_primary,
                   color_header=body.color_header, color_accent=body.color_accent, powered_by=body.powered_by,
                   user_id=p.id if p.kind == "user" else None)
    db.commit()
    return _out(db, client)


@router.put("/clients/{client_id}/branding/logo", response_model=BrandingOut, responses=LOGO_422)
def put_logo(client_id: str,
             file: Annotated[UploadFile, File(description="PNG, JPG, WebP (hasta 2 MB) o SVG (hasta 200 KB)")],
             p: AdminPrincipal, db: DB):
    """El logo del header y del login. Las imagenes se achican a 480 × 120 y se recodifican; el SVG se guarda
    tal cual si no tiene scripts ni referencias externas."""
    client = _client(db, client_id)
    service.set_logo(db, client, file.file.read(service.LOGO_MAX_BYTES + 1), p.id if p.kind == "user" else None)
    db.commit()
    return _out(db, client)


@router.delete("/clients/{client_id}/branding/logo", response_model=BrandingOut)
def delete_logo(client_id: str, p: AdminPrincipal, db: DB):
    """Sin logo, el panel muestra el nombre del cliente en texto."""
    client = _client(db, client_id)
    service.remove_logo(db, client, p.id if p.kind == "user" else None)
    db.commit()
    return _out(db, client)


@router.get("/public/branding/{slug}", response_model=BrandingPublicOut, responses=PUBLIC_404)
def public_branding(slug: str, db: DB):
    """Lo que muestra la pagina de login con `?c=<slug>`."""
    return BrandingPublicOut(**service.public_view(db, slug).__dict__)


@router.get("/public/branding/{slug}/logo", response_class=FileResponse, responses=PUBLIC_404)
def public_logo(slug: str, db: DB):
    path = service.public_logo(db, slug)
    headers = dict(LOGO_HEADERS)
    if path.suffix == ".svg":
        headers["Content-Security-Policy"] = service.SVG_CSP
    return FileResponse(path, media_type=service.LOGO_TYPES.get(path.suffix, "application/octet-stream"),
                        headers=headers)
