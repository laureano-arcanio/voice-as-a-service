"""Dependencias de la API: sesion de base, motor conversacional y autenticacion.

Autenticacion (en este orden):
- `Authorization: Bearer vaas_...`: API key de un cliente (sus sistemas).
- `Authorization: Bearer <jwt>` o la cookie de sesion: usuario (UI).
El usuario se relee de la base en cada pedido: desactivarlo o cambiarle el rol
corta el acceso sin esperar a que venza el token.
"""
import datetime
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.definitions import DefinitionSource
from ..conversation.engine import ConversationEngine
from ..db import get_sessionmaker, utcnow
from ..models import ApiKey, Role, User
from ..runtime import get_conversation_engine
from ..services.errors import Forbidden
from ..services.security import (
    API_KEY_PREFIX,
    Principal,
    decode_session_token,
    hash_api_key,
)

SESSION_COOKIE = "vaas_session"
_bearer = HTTPBearer(auto_error=False, description="API key del cliente (vaas_...) o token de sesion")


def get_db() -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


def get_definitions(engine: Annotated[ConversationEngine, Depends(get_conversation_engine)]) -> DefinitionSource:
    return engine.definitions


DB = Annotated[Session, Depends(get_db)]
Engine = Annotated[ConversationEngine, Depends(get_conversation_engine)]
Definitions = Annotated[DefinitionSource, Depends(get_definitions)]


def _unauthorized(detail: str = "No autenticado") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_principal(request: Request, db: DB,
                  creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> Principal:
    token = creds.credentials if creds else request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorized()
    if token.startswith(API_KEY_PREFIX):
        key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(token), ApiKey.revoked_at.is_(None)))
        if key is None:
            raise _unauthorized("API key invalida o revocada")
        now = utcnow()
        # last_used_at con resolucion de un minuto: no escribir en cada pedido.
        if key.last_used_at is None or now - key.last_used_at > datetime.timedelta(minutes=1):
            key.last_used_at = now
            db.commit()
        return Principal("api_key", key.id, Role.client, key.client_id)
    payload = decode_session_token(token)
    user = db.get(User, payload["sub"]) if payload else None
    if user is None or not user.active:
        raise _unauthorized("Sesion invalida o vencida")
    return Principal("user", user.id, Role(user.role), user.client_id)


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require_admin(p: CurrentPrincipal) -> Principal:
    if not p.is_admin:
        raise Forbidden("Requiere rol admin")
    return p


def require_user(p: CurrentPrincipal) -> Principal:
    if p.kind != "user":
        raise Forbidden("Requiere sesion de usuario (no API key)")
    return p


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
UserPrincipal = Annotated[Principal, Depends(require_user)]


def scoped_client_id(p: Principal, client_id: str | None) -> str | None:
    """El cliente que puede ver quien pide: el suyo, o el que pida un admin (None = todos)."""
    if p.is_admin:
        return client_id
    if client_id and client_id != p.client_id:
        raise Forbidden("Sin acceso a ese cliente")
    return p.client_id


def ensure_access(p: Principal, client_id: str | None) -> None:
    if not p.can_access(client_id):
        raise Forbidden("Sin acceso a ese cliente")
