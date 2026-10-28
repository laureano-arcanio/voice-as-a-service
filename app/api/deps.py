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
import secrets
from collections.abc import Callable, Iterator
from dataclasses import dataclass
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
from ..models import ApiKey, Client, Role, User
from ..runtime import get_conversation_engine
from ..services import api_requests, api_usage, limits, oauth
from ..services.errors import Forbidden, NotFound, QuotaExceeded, ServiceError
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


def _api_key(db: Session, token: str) -> ApiKey:
    key = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(token), ApiKey.revoked_at.is_(None)))
    if key is None:
        raise _unauthorized("API key invalida o revocada")
    now = utcnow()
    # last_used_at con resolucion de un minuto: no escribir en cada pedido.
    if key.last_used_at is None or now - key.last_used_at > datetime.timedelta(minutes=1):
        key.last_used_at = now
        db.commit()
    return key


# Pedidos internos del servidor MCP (app/mcp/server.py): el secreto vive solo en memoria de este proceso.
MCP_INTERNAL_HEADER = "x-atentina-mcp"
MCP_INTERNAL_SECRET = secrets.token_urlsafe(32)
# Con un permiso de toda la plataforma, el cliente en el que actúa una herramienta de cliente del MCP.
MCP_CLIENT_HEADER = "x-atentina-mcp-client"
# Panel: el cliente en el que entró un admin ("ver como cliente", docs/ARQUITECTURA.md).
SUPPORT_CLIENT_HEADER = "x-atentina-client"


def get_principal(request: Request, db: DB,
                  creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> Principal:
    token = creds.credentials if creds else request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorized()
    if token.startswith(API_KEY_PREFIX):
        key = _api_key(db, token)
        scopes = api_usage.parse_scopes(key.scopes)
        # Una key `mcp` usa esta API por dentro (las herramientas de app/mcp/ son pedidos a /api/v1).
        if not scopes & {api_usage.SCOPE_CALLS, api_usage.SCOPE_MCP, api_usage.SCOPE_MCP_READ}:
            # Una key de inferencia (llm/stt/tts) no administra agentes, llamadas ni numeros.
            raise Forbidden("Esta API key es de la API de inferencia: no tiene acceso a esta API", "scope_missing")
        # Solo `mcp_read`: por fuera del MCP, solo lectura. Por dentro, el MCP ya filtró las de escritura (las
        # de lectura que van por POST, como validar o probar un agente, pasan con el secreto interno).
        internal = secrets.compare_digest(request.headers.get(MCP_INTERNAL_HEADER, ""), MCP_INTERNAL_SECRET)
        if (not scopes & {api_usage.SCOPE_CALLS, api_usage.SCOPE_MCP} and request.method not in ("GET", "HEAD")
                and not internal):
            raise Forbidden("Esta API key es de solo lectura (mcp_read)", "scope_missing")
        return Principal("api_key", key.id, Role.client, key.client_id, scopes)
    if token.startswith(oauth.ACCESS_PREFIX):
        # Un token OAuth vale para el MCP (su `resource`), no para la API: solo lo aceptan los pedidos que
        # hace el MCP por dentro, que llevan un secreto que no sale del proceso.
        if not secrets.compare_digest(request.headers.get(MCP_INTERNAL_HEADER, ""), MCP_INTERNAL_SECRET):
            raise _unauthorized("Este token es solo para el servidor MCP (/mcp)")
        access = oauth.authenticate(db, token)
        if access is None:
            raise _unauthorized("Token OAuth inválido, vencido o revocado")
        if access.grant.client_id is None:     # un admin que autorizó toda la plataforma
            acting = request.headers.get(MCP_CLIENT_HEADER)
            if acting:   # una herramienta de cliente: actúa como usuario del cliente que eligió en la llamada
                if db.get(Client, acting) is None:
                    raise NotFound("No existe ese cliente", "client_not_found")
                return Principal("user", access.user.id, Role.client, acting, oauth=True)
            return Principal("user", access.user.id, Role.admin, None, oauth=True)
        # Actúa como usuario del cliente del permiso, aunque sea un admin (que lo eligió al autorizar).
        return Principal("user", access.user.id, Role.client, access.grant.client_id, oauth=True)
    payload = decode_session_token(token)
    user = db.get(User, payload["sub"]) if payload else None
    if user is None or not user.active or payload.get("sv", 0) != user.session_version:
        raise _unauthorized("Sesion invalida o vencida")
    acting = request.headers.get(SUPPORT_CLIENT_HEADER)
    if acting and user.role == Role.admin:
        # Solo la sesión de un admin: una API key o un token OAuth no entran a otro cliente así.
        if db.get(Client, acting) is None:
            raise NotFound("No existe ese cliente", "client_not_found")
        return Principal("user", user.id, Role.client, acting, support=True)
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


def require_session(p: CurrentPrincipal) -> Principal:
    """Sesión del panel: ni API key ni token OAuth (autorizar agentes, por ejemplo)."""
    if p.kind != "user" or p.oauth:
        raise Forbidden("Requiere iniciar sesión en el panel")
    return p


def require_not_support(p: CurrentPrincipal) -> Principal:
    """La cuenta y los cobros del cliente: un admin que entró como el cliente solo los ve."""
    if p.support:
        raise Forbidden("Entrando como el cliente, su cuenta y su plan son de solo lectura", "support_read_only")
    return p


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
UserPrincipal = Annotated[Principal, Depends(require_user)]
SessionPrincipal = Annotated[Principal, Depends(require_session)]
NotSupportPrincipal = Annotated[Principal, Depends(require_not_support)]


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


# ---------- API de inferencia (LLM, STT, TTS con API key) ----------

@dataclass(frozen=True)
class InferenceAccess:
    """Una API key de inferencia ya autenticada, con permiso para el motor pedido y dentro de los
    limites del tier del cliente."""
    client: Client
    key: ApiKey
    remaining: api_usage.Remaining


def inference_key(db: Session, creds: HTTPAuthorizationCredentials | None, scope: str | None) -> tuple[ApiKey, Client]:
    """Key valida (solo por `Authorization: Bearer vaas_...`; la cookie de sesion no sirve), con el
    `scope` pedido (None: cualquiera de inferencia) y de un cliente activo."""
    if creds is None or not creds.credentials.startswith(API_KEY_PREFIX):
        raise _unauthorized("Esta API se usa con una API key: Authorization: Bearer vaas_...")
    key = _api_key(db, creds.credentials)
    scopes = api_usage.parse_scopes(key.scopes)
    allowed = {scope} if scope else set(api_usage.INFERENCE_SCOPES)
    if not scopes & allowed:
        what = f"el motor {scope}" if scope else "la API de inferencia"
        raise Forbidden(f"Esta API key no tiene acceso a {what}", "scope_missing")
    client = db.get(Client, key.client_id)
    if client is None or not client.active:
        raise QuotaExceeded("El cliente esta inactivo", "client_inactive")
    return key, client


def inference_access(scope: Literal["llm", "stt", "tts"]):
    """Dependencia de cada motor: autentica la key y aplica los limites del tier (pedidos por
    minuto y cupo del mes). 401 sin key valida, 403 sin ese alcance o sin el motor en el plan,
    429 al pasar el tope de pedidos o al agotar el cupo."""
    def dependency(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> InferenceAccess:
        key, client = inference_key(db, creds, scope)
        effective = limits.effective_limits(db, client)
        rate = effective.api_rate_limit
        if rate == 0:
            raise Forbidden("Tu plan no incluye la API de inferencia.", "not_in_plan")
        if rate is not None:
            # Por cliente (todas sus keys y los tres motores): los pedidos rechazados tambien cuentan.
            api_limiter.consume(f"inference:{client.id}", [Limit(rate, 60)],
                                f"Superaste los {rate} pedidos por minuto de tu plan. Probá de nuevo en unos segundos.")
        try:
            remaining = api_usage.check(db, client, scope, effective)
        except ServiceError as e:   # cupo del mes agotado o motor fuera del plan: queda en la lista de pedidos
            api_requests.log(db, client.id, key.id, scope, "rejected", http_status=e.status_code, error_code=e.code)
            raise
        return InferenceAccess(client, key, remaining)
    return dependency


LlmAccess = Annotated[InferenceAccess, Depends(inference_access("llm"))]
SttAccess = Annotated[InferenceAccess, Depends(inference_access("stt"))]
TtsAccess = Annotated[InferenceAccess, Depends(inference_access("tts"))]


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

