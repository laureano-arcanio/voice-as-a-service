from fastapi import APIRouter
from sqlalchemy import func, select

from ...config import settings
from ...db import utcnow
from ...models import ApiKey, Client
from ...services.errors import Conflict, Forbidden, NotFound
from ...services.security import generate_api_key
from ..deps import DB, ActiveClientPrincipal, UserPrincipal, require_user
from ..schemas import ApiKeyCreated, ApiKeyIn, ApiKeyOut
from .clients import get_client

router = APIRouter(prefix="/clients/{client_id}/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
def list_keys(client_id: str, p: UserPrincipal, db: DB):
    client = get_client(db, p, client_id)
    return list(db.scalars(select(ApiKey).where(ApiKey.client_id == client.id).order_by(ApiKey.created_at.desc())))


@router.post("", response_model=ApiKeyCreated, status_code=201,
             responses={409: {"description": "El cliente ya tiene MAX_API_KEYS_PER_CLIENT claves activas"}})
def create_key(client_id: str, body: ApiKeyIn, p: ActiveClientPrincipal, db: DB):
    """La clave va en `Authorization: Bearer <key>`. Se muestra solo en esta respuesta.
    Cliente inactivo: 403 client_inactive (solo lectura)."""
    require_user(p)
    client = get_client(db, p, client_id)
    if not client.active:
        raise Forbidden("El cliente está inactivo: no se crean API keys", "client_inactive")
    # Lock del cliente: dos altas a la vez no pasan el tope. Los limites de uso son por
    # cliente, pero cada clave suelta es una credencial mas que cuidar (H12).
    db.scalar(select(Client.id).where(Client.id == client.id).with_for_update(key_share=True, of=Client))
    active = db.scalar(select(func.count()).select_from(ApiKey)
                       .where(ApiKey.client_id == client.id, ApiKey.revoked_at.is_(None))) or 0
    if active >= settings.max_api_keys_per_client:
        raise Conflict(f"{client.name} ya tiene {active} API keys activas (tope {settings.max_api_keys_per_client}): "
                       "revocá alguna antes de crear otra", "api_keys_limit")
    key, prefix, key_hash = generate_api_key()
    row = ApiKey(client_id=client.id, name=body.name, prefix=prefix, key_hash=key_hash)
    db.add(row)
    db.commit()
    return ApiKeyCreated(**ApiKeyOut.model_validate(row).model_dump(), key=key)


@router.delete("/{key_id}", status_code=204)
def revoke_key(client_id: str, key_id: str, p: UserPrincipal, db: DB):
    client = get_client(db, p, client_id)
    row = db.get(ApiKey, key_id)
    if row is None or row.client_id != client.id:
        raise NotFound("API key inexistente")
    row.revoked_at = row.revoked_at or utcnow()
    db.commit()
