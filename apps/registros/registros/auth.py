"""Login del panel (sesión en cookie), CSRF por Origin y claves de la API.

- La sesión se guarda por hash; sin la cookie no se puede reconstruir, y rotar REGISTROS_SESSION_SECRET
  las invalida todas.
- SameSite=Lax y no Strict: con Strict, el link a una ficha abierto desde WhatsApp no llevaría la sesión.
  Por eso los pedidos no seguros se validan además por Origin (CsrfMiddleware).
"""
import datetime
import hashlib
import hmac
import secrets
import threading
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from . import audit
from .config import settings
from .db import get_session, utcnow
from .models import SCOPE_CHARGE, ApiKey, AuditLog, Tenant, User, UserSession

SESSION_COOKIE = "registros_session"
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW = datetime.timedelta(minutes=15)
# Los intentos fallidos se pueden crear sin sesión: la tabla no crece sin límite.
LOGIN_FAILED_RETENTION = datetime.timedelta(days=30)
ACTION_LOGIN_FAILED = "login_failed"
ACTION_LOGIN = "login"
ACTION_LOGOUT = "logout"

_hasher = PasswordHasher()
# argon2 usa 64 MiB por verificación y el login no pide sesión: tope de verificaciones simultáneas.
_verify_slots = threading.BoundedSemaphore(4)
# Mismo costo con usuario inexistente: la demora no delata qué correos existen.
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))

DbSession = Annotated[Session, Depends(get_session)]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _password_ok(stored: str, password: str) -> bool:
    with _verify_slots:
        try:
            return _hasher.verify(stored, password)
        except (VerificationError, InvalidHashError):
            return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _session_hash(token: str) -> str:
    return hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def create_session(s: Session, user: User) -> str:
    """Abre una sesión y devuelve el token de la cookie. Sin commit."""
    token = secrets.token_urlsafe(32)
    s.add(UserSession(token_hash=_session_hash(token), user_id=user.id,
                      expires_at=utcnow() + datetime.timedelta(hours=settings.session_hours)))
    return token


def session_user(s: Session, token: str | None) -> User | None:
    """El usuario de una sesión vigente. Sirve también para las páginas que redirigen al login."""
    if not token or not settings.session_secret:
        return None
    row = s.get(UserSession, _session_hash(token))
    if row is None:
        return None
    if row.expires_at <= utcnow():
        s.delete(row)
        s.commit()
        return None
    user = s.get(User, row.user_id)
    return user if user is not None and user.active else None


def current_user(request: Request, s: DbSession) -> User:
    user = session_user(s, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(401, "Sin sesión")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


# --- Límite de intentos ---


def _reserve_attempt(s: Session, tenant_id: str | None, email: str) -> AuditLog | None:
    """Anota el intento antes de verificar la clave, con commit: con pedidos en paralelo, el último en
    anotarse ve a todos los anteriores, así que no se verifican más de LOGIN_MAX_FAILURES claves.
    Devuelve None si el correo ya llegó al límite."""
    now = utcnow()
    s.execute(delete(AuditLog).where(AuditLog.action == ACTION_LOGIN_FAILED,
                                     AuditLog.at < now - LOGIN_FAILED_RETENTION))
    attempt = audit.record(s, tenant_id, ACTION_LOGIN_FAILED, detail={"email": email})
    s.commit()
    count = s.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.action == ACTION_LOGIN_FAILED,
        AuditLog.at >= now - LOGIN_WINDOW,
        AuditLog.detail["email"].astext == email,
    ))
    if count > LOGIN_MAX_FAILURES:
        # El rechazado no suma: el límite vence 15 minutos después de los fallidos reales.
        s.delete(attempt)
        s.commit()
        return None
    s.commit()
    return attempt


def verify_login(s: Session, tenant_slug: str, email: str, password: str) -> tuple[User | None, bool]:
    """(usuario si la clave es correcta, bloqueado). El límite es por correo, en todos los tenants."""
    email = normalize_email(email)
    tenant = s.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
    attempt = _reserve_attempt(s, tenant.id if tenant else None, email)
    if attempt is None:
        return None, True
    user = None
    if tenant is not None:
        user = s.scalar(select(User).where(User.tenant_id == tenant.id, User.email == email))
    s.commit()  # no retiene una conexión del pool mientras argon2 trabaja
    ok = _password_ok(user.password_hash if user else _DUMMY_HASH, password)
    if user is None or not user.active or not ok:
        return None, False
    attempt.action = ACTION_LOGIN
    attempt.user_id = user.id
    s.commit()
    return user, False


# --- Rutas de sesión ---

router = APIRouter(prefix="/auth", include_in_schema=False)


class LoginIn(BaseModel):
    tenant: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=1, max_length=254)
    # Tope: argon2 no tiene que trabajar sobre un cuerpo enorme de alguien sin sesión.
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("tenant", "email")
    @classmethod
    def _sin_nul(cls, value: str) -> str:
        # Van a la base y a audit_log, y Postgres no guarda un NUL en text ni en jsonb. La clave solo va a argon2.
        if "\x00" in value:
            raise ValueError("caracteres inválidos")
        return value


def _me(s: Session, user: User) -> dict:
    tenant = s.get(Tenant, user.tenant_id)
    return {"email": user.email, "tenant": {"slug": tenant.slug, "name": tenant.name}}


@router.post("/login")
def login(body: LoginIn, response: Response, s: DbSession) -> dict:
    if not settings.session_secret:
        raise HTTPException(503, "Sesión sin configurar")
    user, blocked = verify_login(s, body.tenant, body.email, body.password)
    if blocked:
        raise HTTPException(429, "Demasiados intentos. Probá de nuevo en 15 minutos.",
                            headers={"Retry-After": str(int(LOGIN_WINDOW.total_seconds()))})
    if user is None:
        raise HTTPException(401, "Correo o clave incorrectos")
    s.execute(delete(UserSession).where(UserSession.expires_at <= utcnow()))
    token = create_session(s, user)
    s.commit()
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_hours * 3600, path="/", httponly=True,
                        samesite="lax", secure=settings.public_url.lower().startswith("https://"))
    return _me(s, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, s: DbSession) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    user = session_user(s, token)
    if user is not None:
        s.execute(delete(UserSession).where(UserSession.token_hash == _session_hash(token)))
        audit.record(s, user.tenant_id, ACTION_LOGOUT, user_id=user.id)
        s.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(user: CurrentUser, s: DbSession) -> dict:
    return _me(s, user)


# --- CSRF ---

_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def origin_allowed(origin: str, host: str) -> bool:
    origin = origin.rstrip("/").lower()
    public = urlsplit(settings.public_url.lower())
    if origin == f"{public.scheme}://{public.netloc}":
        return True
    parts = urlsplit(origin)
    return parts.scheme in ("http", "https") and bool(host) and parts.netloc == host.lower()


class CsrfMiddleware:
    """Un pedido no seguro sin Authorization tiene que venir de esta misma app. También cubre el login
    (sin cookie todavía). Con Authorization no hay CSRF: el navegador no la manda solo."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in _SAFE_METHODS:
            return await self.app(scope, receive, send)
        request = Request(scope)
        if "authorization" not in request.headers:
            origin = request.headers.get("origin")
            if origin is not None:
                allowed = origin_allowed(origin, request.headers.get("host", ""))
            else:
                # Sin Origin: curl, scripts o un navegador viejo; ahí manda Sec-Fetch-Site.
                allowed = request.headers.get("sec-fetch-site", "").lower() not in ("cross-site", "same-site")
            if not allowed:
                return await JSONResponse({"detail": "Origen no permitido"}, status_code=403)(scope, receive, send)
        await self.app(scope, receive, send)


# --- Claves de la API ---


def new_api_key() -> tuple[str, str]:
    """(clave, hash). La clave se muestra una vez; en la base queda el SHA-256."""
    key = "reg_" + secrets.token_urlsafe(32)
    return key, api_key_hash(key)


def api_key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass(frozen=True)
class ApiCaller:
    tenant_id: str
    scope: str
    key_id: str


def api_caller(s: DbSession, authorization: Annotated[str | None, Header()] = None) -> ApiCaller:
    scheme, _, token = (authorization or "").partition(" ")
    key = None
    if scheme.lower() == "bearer" and token.strip():
        key = s.scalar(select(ApiKey).where(ApiKey.key_hash == api_key_hash(token.strip()),
                                            ApiKey.revoked_at.is_(None)))
    if key is None:
        raise HTTPException(401, "Clave inválida", headers={"WWW-Authenticate": "Bearer"})
    return ApiCaller(tenant_id=key.tenant_id, scope=key.scope, key_id=key.id)


Reader = Annotated[ApiCaller, Depends(api_caller)]  # read y charge


def charge_caller(caller: Reader) -> ApiCaller:
    if caller.scope != SCOPE_CHARGE:
        raise HTTPException(403, "La clave no tiene el alcance charge")
    return caller


Charger = Annotated[ApiCaller, Depends(charge_caller)]
