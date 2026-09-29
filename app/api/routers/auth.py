import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from ...config import settings
from ...db import utcnow
from ...models import Client, User
from ...services.errors import ServiceError
from ...services.security import create_session_token, verify_password
from ..deps import DB, SESSION_COOKIE, CurrentPrincipal
from ..schemas import LoginIn, MeOut

router = APIRouter(prefix="/auth", tags=["auth"])


class TooManyAttempts(ServiceError):
    status_code = 429


class InvalidCredentials(ServiceError):
    status_code = 401


class _LoginLimiter:
    """Intentos fallidos por IP + email en una ventana (en memoria, por proceso)."""

    def __init__(self, attempts: int = 10, window: float = 300):
        self.attempts, self.window = attempts, window
        self.failures: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def _recent(self, key: str) -> deque[float]:
        q = self.failures[key]
        while q and time.monotonic() - q[0] > self.window:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        with self.lock:
            if len(self._recent(key)) >= self.attempts:
                raise TooManyAttempts("Demasiados intentos. Probá de nuevo en unos minutos.", "too_many_attempts")

    def fail(self, key: str) -> None:
        with self.lock:
            self._recent(key).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self.lock:
            self.failures.pop(key, None)


limiter = _LoginLimiter()


def _me(db, user: User) -> MeOut:
    client = db.get(Client, user.client_id) if user.client_id else None
    return MeOut(id=user.id, email=user.email, name=user.name, role=user.role, client_id=user.client_id,
                 client_name=client.name if client else None)


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, db: DB):
    email = body.email.lower()
    key = f"{request.client.host if request.client else '-'}|{email}"
    limiter.check(key)
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(user.password_hash if user else None, body.password) or not user.active:
        limiter.fail(key)
        raise InvalidCredentials("Email o clave incorrectos", "invalid_credentials")
    limiter.reset(key)
    user.last_login_at = utcnow()
    db.commit()
    token, expires = create_session_token(user.id, user.role, user.client_id)
    # httpOnly: el JS de la UI no ve el token (XSS). SameSite=Strict: no viaja en
    # pedidos de otros sitios (CSRF).
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", secure=settings.auth_cookie_secure,
                        expires=expires, path="/api")
    return _me(db, user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/api")


@router.get("/me", response_model=MeOut)
def me(p: CurrentPrincipal, db: DB):
    if p.kind != "user":
        client = db.get(Client, p.client_id)
        return MeOut(id=p.id, email="", name="API key", role=p.role, client_id=p.client_id,
                     client_name=client.name if client else None)
    return _me(db, db.get(User, p.id))
