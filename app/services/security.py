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


def _setup_key() -> bytes:
    # Clave propia, derivada de la de sesion: un token de alta de clave no vale como sesion
    # (ambos llevan `sub` y `exp`) ni al reves.
    return hashlib.sha256(f"{settings.auth_secret}|password-setup".encode()).digest()


def _fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_password_setup_token(user_id: str, password_hash: str) -> tuple[str, datetime.datetime]:
    """Link de un solo uso para crear la clave: lleva la huella de la clave actual (`ph`) y deja
    de valer cuando esta cambia, o a las `password_setup_hours`."""
    now = datetime.datetime.now(datetime.UTC)
    expires = now + datetime.timedelta(hours=settings.password_setup_hours)
    payload = {"sub": user_id, "ph": _fingerprint(password_hash), "exp": expires, "iat": now}
    return jwt.encode(payload, _setup_key(), algorithm="HS256"), expires


def decode_password_setup_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _setup_key(), algorithms=["HS256"], options={"require": ["sub", "exp", "ph"]})
    except jwt.PyJWTError:
        return None


def password_setup_token_matches(payload: dict, password_hash: str) -> bool:
    """False si la clave ya cambio desde que se emitio el token (ya se usó)."""
    return secrets.compare_digest(payload["ph"], _fingerprint(password_hash))


def unusable_password_hash() -> str:
    """Hash de una clave al azar que nadie conoce: el usuario existe pero no puede ingresar hasta crear la suya."""
    return hash_password(secrets.token_urlsafe(32))


def generate_api_key() -> tuple[str, str, str]:
    """(clave, prefijo visible, hash)."""
    key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return key, key[:12], hash_api_key(key)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
