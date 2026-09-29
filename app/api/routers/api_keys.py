from fastapi import APIRouter
from sqlalchemy import select

from ...db import utcnow
from ...models import ApiKey
from ...services.errors import NotFound
from ...services.security import generate_api_key
from ..deps import DB, UserPrincipal
from ..schemas import ApiKeyCreated, ApiKeyIn, ApiKeyOut
from .clients import get_client

router = APIRouter(prefix="/clients/{client_id}/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
def list_keys(client_id: str, p: UserPrincipal, db: DB):
    client = get_client(db, p, client_id)
    return list(db.scalars(select(ApiKey).where(ApiKey.client_id == client.id).order_by(ApiKey.created_at.desc())))


@router.post("", response_model=ApiKeyCreated, status_code=201)
def create_key(client_id: str, body: ApiKeyIn, p: UserPrincipal, db: DB):
    """La clave va en `Authorization: Bearer <key>`. Se muestra solo en esta respuesta."""
    client = get_client(db, p, client_id)
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
