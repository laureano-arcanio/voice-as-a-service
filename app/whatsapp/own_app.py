"""Alta de un numero con la app de Meta propia del cliente (docs/ARQUITECTURA.md).

Sin Tech Provider no hay Embedded Signup: el cliente crea su app de Meta con WhatsApp, un token permanente de un
usuario de sistema sobre su WABA, y nos pasa el token y el app secret. Validamos con Graph que el numero sea de
esa WABA, suscribimos su app a la WABA y le damos una URL de webhook propia (/wa/webhook/<clave>) con su verify
token, que pega en su app. Sus webhooks llegan firmados con su app secret (webhook.py los valida por cuenta).
"""
import logging
import secrets
from collections.abc import Callable

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Client, WaAccount
from ..services import limits
from ..services.errors import Conflict, NotFound, ServiceError
from . import crypto, store
from .graph import GraphClient, GraphError
from .signup import MetaError, _close, _reason, graph_for

logger = logging.getLogger(__name__)
SOURCE = "own_app"


def webhook_url(account: WaAccount) -> str | None:
    """La URL de webhook que el cliente pega en su app de Meta (None si la cuenta no es own_app)."""
    if not account.webhook_key:
        return None
    return f"{settings.wa_public_url.rstrip('/')}/wa/webhook/{account.webhook_key}"


def verify_token_for(account: WaAccount) -> str | None:
    return crypto.decrypt(account.verify_token)


def app_secret_for(account: WaAccount) -> str | None:
    return crypto.decrypt(account.app_secret)


async def connect(s: Session, *, client_id: str, agent_id: str, phone_number_id: str, waba_id: str,
                  access_token: str, app_secret: str, user_id: str | None = None,
                  graph_factory: Callable[[str], GraphClient] | None = None) -> WaAccount:
    """Alta, o cambio de token y secret de una cuenta own_app del mismo cliente (la URL de webhook y el verify
    token no cambian: lo configurado en Meta sigue andando). Hace commit."""
    factory = graph_factory or graph_for
    access_token, app_secret = access_token.strip(), app_secret.strip()
    if not crypto.enabled():
        raise crypto.TokenKeyMissing("Falta configurar WA_TOKEN_KEY en el servidor")
    client = s.get(Client, client_id)
    if client is None or not client.active:
        raise NotFound("Cliente inexistente o inactivo")
    existing = store.account_by_pnid(s, phone_number_id)
    if existing is not None and (existing.client_id != client_id or existing.source != SOURCE):
        raise Conflict("Ese número de WhatsApp ya está conectado a otra cuenta")
    if existing is None:
        limits.check_whatsapp(s, client_id)
    store.check_agent(s, client_id, agent_id)

    graph = factory(access_token)
    try:
        try:
            numbers = await graph.list_phone_numbers(waba_id)
        except GraphError as e:
            raise MetaError(e, "Meta rechazó el token o la cuenta de WhatsApp Business: ") from None
        number = next((n for n in numbers if str(n.get("id")) == phone_number_id), None)
        if number is None:
            raise ServiceError("El número no pertenece a esa cuenta de WhatsApp Business (revisá los dos IDs)",
                               code="signup_mismatch")
        status, reason = "connected", None
        try:
            await graph.subscribe_app(waba_id)     # suscribe SU app (la del token) a su WABA
        except GraphError as e:
            logger.warning("wa own_app: subscribed_apps fallo waba=%s code=%s", waba_id, e.code)
            status, reason = "pending", _reason("subscribed_apps", e)
    finally:
        await _close(graph)

    display = str(number.get("display_phone_number") or phone_number_id)[:32]
    name = str(number.get("verified_name") or "")[:128]
    quality = str(number.get("quality_rating") or "") or None
    if existing is None:
        account = store.create_account(
            s, client_id=client_id, agent_id=agent_id, phone_number_id=phone_number_id, waba_id=waba_id,
            display_phone_number=display, name=name, access_token=access_token, source=SOURCE,
            quality_rating=quality, connected_by=user_id, app_secret=crypto.encrypt(app_secret),
            verify_token=crypto.encrypt(secrets.token_urlsafe(24)), webhook_key=secrets.token_urlsafe(24))
    else:
        account = existing
        store.update_account(s, account, agent_id=agent_id, waba_id=waba_id, display_phone_number=display,
                             name=name or account.name, access_token=access_token, active=True)
        account.app_secret = crypto.encrypt(app_secret)
        account.quality_rating = quality
    store.mark_status(s, account, status, reason)
    s.commit()
    logger.info("wa own_app: cuenta %s pnid=%s waba=%s client=%s status=%s", account.id, phone_number_id,
                waba_id, client_id, status)
    return account


def scoped_payload(payload: dict, account: WaAccount) -> dict:
    """Solo lo de esa cuenta: los cambios de su WABA y, en los de mensajes, de su numero. Un webhook firmado
    con el secret de un cliente no puede hacer pasar mensajes de otro numero."""
    entries = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict) or str(entry.get("id") or "") != account.waba_id:
            continue
        changes = []
        for change in entry.get("changes") or []:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            meta = value.get("metadata")
            pnid = str(meta.get("phone_number_id") or "") if isinstance(meta, dict) else ""
            if change.get("field") == "messages" and pnid != account.phone_number_id:
                continue
            changes.append(change)
        if changes:
            entries.append({**entry, "changes": changes})
    return {**payload, "entry": entries}
