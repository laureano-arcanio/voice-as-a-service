"""Cifrado de los secretos de wa_accounts (token de acceso y PIN) con WA_TOKEN_KEY.

Fernet (AES-128-CBC + HMAC-SHA256, de `cryptography`). WA_TOKEN_KEY: una o mas claves
separadas por coma; la primera cifra y todas descifran (MultiFernet, para rotar).
Generar una: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

En la base va "fernet:<token>". Un texto sin prefijo es legado en claro (cuentas
cargadas antes de la fase 2): se lee igual, con un warning una sola vez.
"""
import logging
import secrets
from functools import cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from ..config import settings
from ..services.errors import ServiceError

logger = logging.getLogger(__name__)

PREFIX = "fernet:"
_warned_legacy = False


class TokenKeyMissing(ServiceError):
    """Falta WA_TOKEN_KEY (o es invalida, o no descifra lo guardado)."""
    status_code = 503
    default_code = "wa_token_key_missing"

    def __init__(self, message: str = "Falta configurar WA_TOKEN_KEY para guardar credenciales de WhatsApp"):
        super().__init__(message)


@cache
def _fernet(keys: str) -> MultiFernet:
    try:
        return MultiFernet([Fernet(k.strip().encode()) for k in keys.split(",") if k.strip()])
    except (ValueError, TypeError):
        # Sin el valor de la clave en el mensaje.
        raise TokenKeyMissing("WA_TOKEN_KEY invalida: tiene que ser una clave Fernet (base64 de 32 bytes)") from None


def enabled() -> bool:
    if not settings.wa_token_key.strip():
        return False
    try:
        _fernet(settings.wa_token_key)
    except TokenKeyMissing:
        return False
    return True


def _key() -> MultiFernet:
    if not settings.wa_token_key.strip():
        raise TokenKeyMissing()
    return _fernet(settings.wa_token_key)


def encrypt(value: str) -> str:
    return PREFIX + _key().encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    global _warned_legacy
    if not value:
        return None
    if not value.startswith(PREFIX):
        if not _warned_legacy:
            _warned_legacy = True
            logger.warning("wa: hay secretos en claro en wa_accounts (legado): se usan igual; "
                           "volver a cargarlos para cifrarlos")
        return value
    try:
        return _key().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        raise TokenKeyMissing("WA_TOKEN_KEY no descifra las credenciales guardadas") from None


def new_pin() -> str:
    """PIN de 6 digitos para el registro (verificacion en dos pasos del numero)."""
    return f"{secrets.randbelow(1_000_000):06d}"
