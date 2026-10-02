"""Dependencias de la API: sesion de base, motor conversacional y autenticacion.

Autenticacion (en este orden):
- `Authorization: Bearer vaas_...`: API key de un cliente (sus sistemas).
- `Authorization: Bearer <jwt>` o la cookie de sesion: usuario (UI).
El usuario se relee de la base en cada pedido: desactivarlo, cambiarle el rol o
subirle session_version (logout, cambio de clave) corta el acceso sin esperar a que
venza el token.

IP real: detras del tunel de Cloudflare viene en CF-Connecting-IP; solo se cree si el
par TCP es un proxy de confianza (settings.trusted_proxy_cidrs).
"""
import datetime
import ipaddress
from collections.abc import Callable, Iterator
from functools import cache
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.definitions import DefinitionSource
from ..config import settings
from ..conversation.engine import ConversationEngine
from ..db import get_sessionmaker, utcnow
from ..models import ApiKey, Role, User
from ..runtime import get_conversation_engine
from ..services.errors import Forbidden
from ..services.ratelimit import Limit, RateLimiter, client_key
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
    if user is None or not user.active or payload.get("sv", 0) != user.session_version:
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


# ---------- IP real y esquema ----------

def default_gateway(route_file: str = "/proc/net/route") -> str | None:
    """Gateway por defecto (IPv4). En el contenedor es el de la red de compose: el par que
    ve la app cuando cloudflared (host) entra por localhost:8011 via docker-proxy."""
    try:
        with open(route_file) as f:
            for line in f.readlines()[1:]:
                parts = line.split()
                if len(parts) > 2 and parts[1] == "00000000":
                    return str(ipaddress.IPv4Address(int(parts[2], 16).to_bytes(4, "little")))
    except (OSError, ValueError):
        pass
    return None


@cache
def _trusted_networks(cidrs: str) -> tuple:
    """CIDRs separados por coma; `gateway` es el gateway por defecto (ver default_gateway)."""
    nets = []
    for c in (c.strip() for c in cidrs.split(",")):
        if c.lower() == "gateway":
            c = default_gateway() or ""
        if c:
            nets.append(ipaddress.ip_network(c, strict=False))
    return tuple(nets)


def _peer_is_trusted(request: Request) -> bool:
    peer = request.client.host if request.client else ""
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(addr in net for net in _trusted_networks(settings.trusted_proxy_cidrs))


def client_ip(request: Request) -> str:
    """CF-Connecting-IP si el par es un proxy de confianza; si no, el par."""
    peer = request.client.host if request.client else ""
    if _peer_is_trusted(request):
        forwarded = request.headers.get("cf-connecting-ip", "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return peer


def request_is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    return _peer_is_trusted(request) and request.headers.get("x-forwarded-proto", "").lower() == "https"


# ---------- limites de uso ----------

# En memoria y por proceso (un worker de uvicorn), como el de la demo.
api_limiter = RateLimiter()
DEFAULT_LIMIT_MESSAGE = "Demasiados pedidos. Probá más tarde."


def rate_limit(name: str, *limits: Limit | Callable[[], Limit],
               per: Literal["principal", "client", "ip"] = "principal",
               message: str = DEFAULT_LIMIT_MESSAGE):
    """Dependencia para `dependencies=[Depends(rate_limit(...))]`: cuenta el pedido y da
    429 (Retry-After) al pasar el tope. Un limite puede ser una funcion que lo arme en
    cada pedido (lee settings en vivo). per=client: un admin cuenta por si mismo."""
    def resolve() -> list[Limit]:
        return [lim() if callable(lim) else lim for lim in limits]

    if per == "ip":
        def by_ip(request: Request) -> None:
            api_limiter.consume(f"{name}:ip:{client_key(client_ip(request))}", resolve(), message)
        return by_ip

    def by_principal(p: CurrentPrincipal) -> None:
        key = f"client:{p.client_id}" if per == "client" and p.client_id else f"{p.kind}:{p.id}"
        api_limiter.consume(f"{name}:{key}", resolve(), message)
    return by_principal

