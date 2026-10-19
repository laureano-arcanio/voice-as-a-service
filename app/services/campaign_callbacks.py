"""Webhook de las campañas (docs/LLAMADAS_SALIENTES_PLAN.md, seccion 8): configuracion, firma y cola.

- `callback_url`: https y un host publico (sin eso, un cliente podria apuntar a la red interna del
  server: la base, los demas servicios). Con CAMPAIGN_CALLBACK_ALLOW_PRIVATE=true (desarrollo) se
  permite http y cualquier host. La entrega resuelve el host, chequea la IP y se conecta a esa IP
  (con el SNI y el Host originales), asi un DNS que cambia entre el chequeo y la conexion no sirve.
- `callback_secret`: firma cada POST (HMAC-SHA256 del cuerpo, header `X-Atentina-Signature: sha256=<hex>`).
  Va cifrado con WA_TOKEN_KEY y no se devuelve nunca; si el cliente no manda uno, se genera y se
  muestra una sola vez.
- Cola (`campaign_callbacks`): un evento por contacto que termina (`contact.finished`), por el
  seguimiento por WhatsApp de uno de voz (`contact.followup`) y por la campaña que termina
  (`campaign.finished`). Encolar es una fila en la transaccion de quien termina el contacto; la entrega,
  con reintentos y fuera del loop de las campañas, es app/campaigns/callbacks.py.

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama.
"""
from __future__ import annotations

import asyncio
import datetime
import hashlib
import hmac
import ipaddress
import secrets
import socket
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import Campaign, CampaignCallback, CampaignContact
from ..whatsapp import crypto
from .errors import Invalid

SIGNATURE_HEADER = "X-Atentina-Signature"
MIN_SECRET, MAX_SECRET = 16, 128


def resolve_public(host: str, port: int | None = None) -> str:
    """La IP publica a la que apunta el host. ValueError si no resuelve o si alguna de sus direcciones es
    privada, loopback o interna."""
    try:
        infos = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError("el host no resuelve") from None
    addresses = [info[4][0] for info in infos]
    if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError("apunta a una red privada o interna")
    return addresses[0]


def check_url(url: str, *, resolve: bool = True) -> str:
    """La URL del webhook, validada. Invalid si no es https (o http en desarrollo) o apunta a una red interna.
    `resolve=False` saltea el DNS (que bloquea): lo hace antes `check_url_async`."""
    url = url.strip()
    parsed = urlparse(url)
    allow = settings.campaign_callback_allow_private
    if parsed.scheme not in (("http", "https") if allow else ("https",)) or not parsed.hostname:
        raise Invalid("callback_url: tiene que ser una URL https completa", "invalid_callback_url")
    if parsed.username or parsed.password:
        raise Invalid("callback_url: sin usuario ni clave en la URL", "invalid_callback_url")
    if len(url) > 512:
        raise Invalid("callback_url: hasta 512 caracteres", "invalid_callback_url")
    if not allow and resolve:
        try:
            resolve_public(parsed.hostname, parsed.port)
        except ValueError as e:
            raise Invalid(f"callback_url: {e}", "invalid_callback_url") from None
    return url


async def check_url_async(url: str) -> str:
    """`check_url` sin bloquear el event loop: la resolucion DNS corre en un thread."""
    return await asyncio.to_thread(check_url, url)


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def set_webhook(c: Campaign, changes: dict, *, resolve: bool = True) -> str | None:
    """Aplica `callback_url` y/o `callback_secret` (los que vinieron en `changes`). Sin URL no hay
    secreto; con URL y sin secreto, se genera uno. Devuelve el secreto generado (se muestra una vez).
    Desde un handler async, la URL se valida antes con `check_url_async` y aca `resolve=False`."""
    if "callback_url" in changes:
        url = changes["callback_url"]
        c.callback_url = check_url(url, resolve=resolve) if url else None
        if c.callback_url is None:
            c.callback_secret = None
    secret = changes.get("callback_secret")
    if secret:
        if c.callback_url is None:
            raise Invalid("callback_secret necesita callback_url")
        if not MIN_SECRET <= len(secret) <= MAX_SECRET:
            raise Invalid(f"callback_secret: entre {MIN_SECRET} y {MAX_SECRET} caracteres")
        c.callback_secret = _encrypt(secret)
    if c.callback_url and not c.callback_secret:
        secret = new_secret()
        c.callback_secret = _encrypt(secret)
        return secret
    return None


def _encrypt(secret: str) -> str:
    if not crypto.enabled():
        raise crypto.TokenKeyMissing("Falta configurar WA_TOKEN_KEY para guardar el secreto del webhook")
    return crypto.encrypt(secret)


def secret_of(c: Campaign) -> str | None:
    return crypto.decrypt(c.callback_secret)


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def enqueue(s: Session, c: Campaign, event: str, r: CampaignContact | None = None,
            now: datetime.datetime | None = None) -> None:
    """Encola el evento si la campaña tiene webhook. `r`: el contacto, en los eventos por contacto."""
    if not c.callback_url:
        return
    now = now or utcnow()
    if r is None:
        now += datetime.timedelta(microseconds=1)     # el de la campaña va despues de los de contacto del mismo instante
    s.add(CampaignCallback(campaign_id=c.id, campaign_contact_id=r.id if r is not None else None, event=event,
                           next_attempt_at=now, created_at=now))
