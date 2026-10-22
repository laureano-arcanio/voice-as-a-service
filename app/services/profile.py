"""Perfil del usuario de la sesion: nombre, y cambio de clave o de email con un codigo por mail.

El codigo (6 digitos) va siempre al email actual. No hay tabla: la API devuelve un desafio firmado
(security.create_account_code_token) y el usuario lo manda de vuelta con el codigo. Deja de valer al
cambiar la clave o el email (un solo uso) o a los ACCOUNT_CODE_MINUTES. Topes por usuario: mails por
hora e intentos fallidos cada 15 min (sin ellos, 6 digitos se adivinan).
"""
import datetime
import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..mail import messages, notify
from ..models import User
from .errors import Conflict, Invalid, Upstream
from .ratelimit import Limit, RateLimiter
from .security import (
    check_account_code,
    create_account_code_token,
    hash_password,
    new_account_code,
)

logger = logging.getLogger(__name__)

limiter = RateLimiter()
WINDOW, HOUR = 900, 3600
CODE_INVALID = "El código no es correcto o venció. Revisalo o pedí uno nuevo."


@dataclass(frozen=True)
class CodeSent:
    challenge: str
    sent_to: str
    expires_at: datetime.datetime


def update_name(s: Session, user: User, name: str) -> User:
    user.name = name.strip()
    s.commit()
    return user


def _email_taken(s: Session, email: str, user: User) -> bool:
    return s.scalar(select(func.count()).select_from(User).where(User.email == email, User.id != user.id)) > 0


def _send_code(user: User, purpose: str, new_email: str | None = None) -> CodeSent:
    limiter.consume(f"account_code:send:{user.id}", [Limit(settings.account_code_sends_per_hour, HOUR)],
                    "Pediste muchos códigos. Probá de nuevo en un rato.")
    code = new_account_code()
    challenge, expires = create_account_code_token(user, purpose, code, new_email)
    mail = messages.account_code(email=user.email, name=user.name, code=code, expires_at=expires,
                                 new_email=new_email)
    result = notify.send(mail)
    if result.status != "sent":
        raise Upstream("No pudimos mandar el mail con el código. Probá de nuevo en un rato.", "mail_failed")
    logger.info("perfil de %s: codigo para %s enviado", user.email, purpose)
    return CodeSent(challenge, user.email, expires)


def _check_code(user: User, purpose: str, challenge: str, code: str) -> dict:
    """Cuenta el intento antes de verificar: pedidos en paralelo no pasan todos."""
    key = f"account_code:try:{user.id}"
    limiter.consume(key, [Limit(settings.account_code_attempts_15m, WINDOW)],
                    "Demasiados intentos. Pedí un código nuevo en unos minutos.")
    payload = check_account_code(challenge, user, purpose, code)
    if payload is None:
        raise Invalid(CODE_INVALID, "invalid_code")
    limiter.reset(key)
    return payload


def request_password_code(user: User) -> CodeSent:
    return _send_code(user, "password")


def change_password(s: Session, user: User, challenge: str, code: str, password: str) -> User:
    """Cambia la clave y cierra las demas sesiones (sube session_version; la API reabre la de este pedido)."""
    _check_code(user, "password", challenge, code)
    user.password_hash = hash_password(password)
    user.session_version += 1
    s.commit()
    return user


def request_email_code(s: Session, user: User, new_email: str) -> CodeSent:
    new_email = new_email.strip().lower()
    if new_email == user.email:
        raise Invalid("Ese ya es tu email.", "same_email")
    if _email_taken(s, new_email, user):
        raise Conflict("Ya hay una cuenta con ese email.", "email_taken")
    return _send_code(user, "email", new_email)


def change_email(s: Session, user: User, challenge: str, code: str) -> User:
    """Pasa al email nuevo del desafio y cierra las demas sesiones."""
    payload = _check_code(user, "email", challenge, code)
    new_email = payload.get("new")
    if not new_email:
        raise Invalid(CODE_INVALID, "invalid_code")
    if _email_taken(s, new_email, user):
        raise Conflict("Ya hay una cuenta con ese email.", "email_taken")
    old = user.email
    user.email = new_email
    user.session_version += 1
    s.commit()
    logger.info("perfil: email %s cambiado a %s", old, new_email)
    return user
