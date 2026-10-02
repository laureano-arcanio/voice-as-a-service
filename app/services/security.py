"""Claves (argon2), tokens de sesion (JWT HS256) y API keys (SHA-256)."""
import datetime
import hashlib
import secrets
from dataclasses import dataclass

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from ..config import settings
from ..models import Role

API_KEY_PREFIX = "vaas_"
_hasher = PasswordHasher()
# Hash de referencia para gastar el mismo tiempo cuando el email no existe (no se
# puede distinguir por tiempo un email registrado de uno que no).
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


@dataclass(frozen=True)
class Principal:
    """Quien hace el pedido: un usuario (sesion) o la API key de un cliente."""
    kind: str               # "user" | "api_key"
    id: str
    role: Role
    client_id: str | None   # None solo para admins

    @property
    def is_admin(self) -> bool:
        return self.role == Role.admin

    def can_access(self, client_id: str | None) -> bool:
        return self.is_admin or (client_id is not None and client_id == self.client_id)


def create_session_token(user_id: str, role: str, client_id: str | None,
                         session_version: int = 0) -> tuple[str, datetime.datetime]:
    """sv: User.session_version al emitirlo; si despues sube (logout, clave), el token deja de valer."""
    expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=settings.auth_token_hours)
    payload = {"sub": user_id, "role": role, "cid": client_id, "sv": session_version, "exp": expires,
               "iat": datetime.datetime.now(datetime.UTC)}
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256"), expires


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=["HS256"], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError:
        return None


def generate_api_key() -> tuple[str, str, str]:
    """(clave, prefijo visible, hash)."""
    key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return key, key[:12], hash_api_key(key)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
