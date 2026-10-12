"""Links firmados a las vistas de una app (docs/APPS_PLAN.md, seccion 5).

El link lleva un token aleatorio de 32 bytes; la base guarda su SHA-256. Vence a los
APPS_LINK_TTL_DAYS y se puede revocar. URL: https://<APPS_PUBLIC_HOST>/{cliente}/{app}/{vista}/?k=<token>.
"""
import datetime
import hashlib
import secrets
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import App, AppLink, Client
from ..services.errors import Invalid, NotFound
from .registry import manifest_of


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def public_base() -> str:
    if not settings.apps_public_host:
        raise Invalid("Las vistas no estan publicadas (falta APPS_PUBLIC_HOST)")
    return f"{settings.apps_public_scheme}://{settings.apps_public_host}"


def view_path(client_slug: str, app_slug: str, view: str) -> str:
    return f"/{client_slug}/{app_slug}/{view}/"


def create_link(s: Session, app: App, view: str, params: dict, created_by: str,
                ttl_days: int | None = None) -> tuple[str, AppLink]:
    """Devuelve la URL (con el token, que no se guarda) y el link."""
    if app.client_id is None:
        raise Invalid("La app no esta asignada a un cliente")
    if view not in {v.name for v in manifest_of(app).views}:
        raise NotFound(f"La app no tiene la vista {view!r}")
    client = s.get(Client, app.client_id)
    token = secrets.token_urlsafe(32)
    link = AppLink(token_hash=hash_token(token), app_id=app.id, view=view,
                   params={k: v for k, v in params.items() if v not in (None, "")},
                   expires_at=utcnow() + datetime.timedelta(days=ttl_days or settings.apps_link_ttl_days),
                   created_by=created_by[:64])
    s.add(link)
    s.flush()
    query = urlencode({**{k: str(v) for k, v in link.params.items()}, "k": token})
    return f"{public_base()}{view_path(client.slug, app.slug, view)}?{query}", link


def resolve(s: Session, token: str) -> AppLink | None:
    """El link vigente de ese token, o None (inexistente, vencido o revocado)."""
    link = s.scalar(select(AppLink).where(AppLink.token_hash == hash_token(token)))
    if link is None or link.revoked_at is not None or link.expires_at <= utcnow():
        return None
    return link


def revoke(link: AppLink) -> None:
    link.revoked_at = link.revoked_at or utcnow()
