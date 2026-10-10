from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from ...config import settings
from ...db import utcnow
from ...models import Client, User
from ...services import signup
from ...services.errors import Invalid, ServiceError
from ...services.ratelimit import Limit, RateLimited, client_key
from ...services.security import (
    API_KEY_PREFIX,
    create_session_token,
    decode_password_setup_token,
    decode_session_token,
    hash_password,
    password_setup_token_matches,
    verify_password,
)
from ..deps import (
    DB,
    SESSION_COOKIE,
    CurrentPrincipal,
    api_limiter,
    client_ip,
    rate_limit,
    request_is_https,
)
from ..schemas import (
    LoginIn,
    MeOut,
    PasswordSetupCheckIn,
    PasswordSetupIn,
    PasswordResetIn,
    PasswordSetupInfo,
)

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


def _open_session(request: Request, response: Response, user: User) -> None:
    token, _ = create_session_token(user.id, user.role, user.client_id, user.session_version)
    # httpOnly: el JS de la UI no ve el token (XSS). SameSite=Strict: no viaja desde otros
    # sitios (entre subdominios de atentina.com.ar si: eso lo cubre el chequeo de Origin, main.py).
    # Secure siempre que el pedido llegue por HTTPS (tunel), aunque AUTH_COOKIE_SECURE=false.
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict",
                        secure=settings.auth_cookie_secure or request_is_https(request),
                        max_age=settings.auth_token_hours * 3600, path="/api")


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
    _open_session(request, response, user)
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


# ---------- crear la clave desde el link del mail de alta ----------

SETUP_LINK_INVALID = "El link venció o ya se usó. Pedí uno nuevo con «Olvidé mi clave» en el ingreso."


def _setup_user(db, token: str) -> User:
    """El usuario del link, si sigue valiendo: firma, vencimiento, usuario activo y clave sin cambiar
    desde que se emitio (un solo uso)."""
    payload = decode_password_setup_token(token)
    user = db.get(User, payload["sub"]) if payload else None
    if user is None or not user.active or not password_setup_token_matches(payload, user.password_hash):
        raise Invalid(SETUP_LINK_INVALID, "invalid_setup_token")
    return user


# Publicos (el usuario todavia no tiene clave). El token es una firma imposible de adivinar; el tope
# por IP frena el barrido igual y el uso de la API como oraculo.
_setup_limit = Depends(rate_limit("password_setup", Limit(30, 3600), per="ip"))


@router.post("/password-setup/check", response_model=PasswordSetupInfo, dependencies=[_setup_limit],
             responses={422: {"description": "Link vencido o ya usado (code invalid_setup_token)"}})
def password_setup_check(body: PasswordSetupCheckIn, db: DB):
    """Datos del usuario de un link de alta, para mostrar la pantalla de crear la clave."""
    user = _setup_user(db, body.token)
    client = db.get(Client, user.client_id) if user.client_id else None
    return PasswordSetupInfo(email=user.email, name=user.name, client_name=client.name if client else None)


@router.post("/password-setup", response_model=MeOut, dependencies=[_setup_limit],
             responses={422: {"description": "Link vencido o ya usado (code invalid_setup_token)"}})
def password_setup(body: PasswordSetupIn, request: Request, response: Response, db: DB):
    """Guarda la clave y abre la sesion. El link no sirve de nuevo (la huella de la clave cambio) y
    las sesiones que hubiera abiertas se cierran."""
    user = _setup_user(db, body.token)
    user.password_hash = hash_password(body.password)
    user.session_version += 1
    user.last_login_at = utcnow()
    db.commit()
    _open_session(request, response, user)
    return _me(db, user)


@router.post("/password-reset", status_code=202, response_class=Response,
             responses={429: {"description": "Demasiados pedidos"}})
def password_reset(body: PasswordResetIn, request: Request, db: DB):
    """Olvidé mi clave: si el email es de un usuario activo, le manda el link para crear una nueva
    (el mismo de /password-setup). Responde 202 siempre."""
    signup.password_reset(db, body.email, client_ip(request))
    return Response(status_code=202)
