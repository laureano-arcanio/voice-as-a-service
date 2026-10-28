"""Una sola sesión para el panel y el teléfono del equipo (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 16).

La cookie de sesión es de cada host (sin Domain, para no mandarla a los demás subdominios de atentina.com.ar). Para
pasar de uno al otro sin volver a ingresar, el host de origen da un pase de un solo uso (60 s, para el host destino)
que viaja en el fragmento de la URL (`#sesion=`, no llega a los logs ni al Referer) y el destino lo cambia por su
propia cookie (POST /auth/switch/redeem). Sin PHONE_APP_BASE_URL, o si ya está en el mismo host, no hace falta pase.
"""
import threading
import time
from typing import Literal
from urllib.parse import urlparse

from ..config import settings
from ..models import User
from .security import create_switch_token, decode_switch_token

Target = Literal["phone", "panel"]
PANEL_PATH = "/telefono"     # el Teléfono del equipo en el panel
PHONE_LOCAL_PATH = "/movil"  # la app del teléfono en el host del panel

_used: dict[str, float] = {}
_lock = threading.Lock()


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def phone_base() -> str:
    return settings.phone_app_base_url.rstrip("/")


def panel_base() -> str:
    first = next((o.strip() for o in settings.app_origins.split(",") if o.strip()), "")
    return first.rstrip("/")


def target_url(user: User, target: Target, request_host: str) -> str:
    """A dónde ir: la URL con el pase, o una ruta relativa si el destino es este mismo host."""
    base = phone_base() if target == "phone" else panel_base()
    path = "/" if target == "phone" else PANEL_PATH
    if not base or _host(base) == request_host:
        return PHONE_LOCAL_PATH if target == "phone" and not base else path
    token = create_switch_token(user.id, user.session_version, _host(base))
    return f"{base}{path}#sesion={token}"


def redeem(token: str, request_host: str, get_user) -> User | None:
    """El usuario del pase, si es para este host, no venció, no se usó y la sesión del usuario sigue vigente."""
    payload = decode_switch_token(token, request_host)
    if payload is None:
        return None
    now = time.time()
    with _lock:
        for jti, exp in list(_used.items()):
            if exp < now:
                del _used[jti]
        if payload["jti"] in _used:
            return None
        _used[payload["jti"]] = float(payload["exp"])
    user = get_user(payload["sub"])
    if user is None or not user.active or payload["sv"] != user.session_version:
        return None
    return user
