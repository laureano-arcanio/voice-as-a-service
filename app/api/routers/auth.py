from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from ...config import settings
from ...db import utcnow
from ...models import Client, User
from ...services.errors import ServiceError
from ...services.ratelimit import Limit, RateLimited, client_key
from ...services.security import (
    API_KEY_PREFIX,
    create_session_token,
    decode_session_token,
    verify_password,
)
from ..deps import (
    DB,
    SESSION_COOKIE,
    CurrentPrincipal,
    api_limiter,
    client_ip,
    request_is_https,
)
from ..schemas import LoginIn, MeOut

router = APIRouter(prefix="/auth", tags=["auth"])
WINDOW, DAY = 900, 86_400
TOO_MANY = "Demasiados intentos. Probá de nuevo en unos minutos."


class InvalidCredentials(ServiceError):
    status_code = 401


def _me(db, user: User) -> MeOut:
    client = db.get(Client, user.client_id) if user.client_id else None
    return MeOut(id=user.id, email=user.email, name=user.name, role=user.role, client_id=user.client_id,
                 client_name=client.name if client else None)


def _login_limits(ip: str, email: str) -> tuple[list[tuple[str, list[Limit]]], str, list[Limit]]:
    """Intentos por IP + email (adivinar una clave) y por IP (probar muchos emails), y la
    clave y el limite por email (adivinar desde muchas IP)."""
    return [
        (f"login:ip_email:{ip}|{email}", [Limit(settings.login_fail_ip_email_15m, WINDOW)]),
        (f"login:ip:{ip}", [Limit(settings.login_fail_ip_15m, WINDOW), Limit(settings.login_fail_ip_day, DAY)]),
    ], f"login:email:{email}", [Limit(settings.login_fail_email_15m, WINDOW)]


@router.post("/login", response_model=MeOut, responses={429: {"description": "Demasiados intentos fallidos"}})
def login(body: LoginIn, request: Request, response: Response, db: DB):
    email = body.email.lower()
    ip = client_key(client_ip(request))
    limits, email_key, email_limits = _login_limits(ip, email)
    # El tope por email solo frena a una IP que ya fallo en la ventana: si no, un tercero
    # que conoce el email (el del admin) lo deja afuera aunque tenga la clave correcta.
    if api_limiter.count(f"login:ip:{ip}", WINDOW) > 0:
        limits.append((email_key, email_limits))
    try:
        # Se cuenta antes de verificar (atomico): pedidos en paralelo no pasan todos.
        api_limiter.consume_all(limits, TOO_MANY)
    except RateLimited as e:
        e.code = "too_many_attempts"
        raise
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(user.password_hash if user else None, body.password) or not user.active:
        if all(key != email_key for key, _ in limits):
            api_limiter.hit(email_key)
        raise InvalidCredentials("Email o clave incorrectos", "invalid_credentials")
    for key, _ in limits:
        api_limiter.unhit(key)
    api_limiter.reset(limits[0][0])
    user.last_login_at = utcnow()
    db.commit()
    token, _ = create_session_token(user.id, user.role, user.client_id, user.session_version)
    # httpOnly: el JS de la UI no ve el token (XSS). SameSite=Strict: no viaja desde otros
    # sitios (entre subdominios de atentina.com.ar si: eso lo cubre el chequeo de Origin, main.py).
    # Secure siempre que el pedido llegue por HTTPS (tunel), aunque AUTH_COOKIE_SECURE=false.
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict",
                        secure=settings.auth_cookie_secure or request_is_https(request),
                        max_age=settings.auth_token_hours * 3600, path="/api")
    return _me(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    """Cierra todas las sesiones del usuario (sube session_version) y borra la cookie.
    Sin sesion valida, 204 igual."""
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else request.cookies.get(SESSION_COOKIE)
    payload = decode_session_token(token) if token and not token.startswith(API_KEY_PREFIX) else None
    user = db.get(User, payload["sub"]) if payload else None
    if user is not None and payload.get("sv", 0) == user.session_version:
        user.session_version += 1
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/api", httponly=True, samesite="strict",
                           secure=settings.auth_cookie_secure or request_is_https(request))


@router.get("/me", response_model=MeOut)
def me(p: CurrentPrincipal, db: DB):
    if p.kind != "user":
        client = db.get(Client, p.client_id)
        return MeOut(id=p.id, email="", name="API key", role=p.role, client_id=p.client_id,
                     client_name=client.name if client else None)
    return _me(db, db.get(User, p.id))
