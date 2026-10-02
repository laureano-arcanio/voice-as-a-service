"""Embedded Signup v4 (docs/WHATSAPP_PLAN.md 3.3): el cliente conecta su numero desde
el dashboard, y despues administra la cuenta (registro, datos del numero, plantillas).

connect(), en orden:
1. cambia el codigo del popup (vence a los 30 s) por el business token del cliente;
2. comprueba que el phone_number_id sea de esa WABA (en coexistencia el popup no lo
   manda: se toma el unico numero de la WABA);
3. suscribe nuestra app a la WABA (sin esto no llega ningun mensaje);
4. registra el numero con un PIN de 6 digitos (el pedido, el guardado si el numero se
   reconecta, o uno nuevo); en coexistencia (numero de la app de WhatsApp Business) no se
   registra: se pide la sincronizacion de contactos e historial (Meta da 24 h);
5. guarda la cuenta (wa_accounts) con el token y el PIN cifrados.
Si falla la suscripcion o el registro, la cuenta queda `pending` con el motivo y se
reintenta con retry_register(). Un token rechazado (190) la deja `disconnected`.

El token, el secret, el codigo y el PIN no van a los logs ni a las respuestas.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Client, WaAccount
from ..services.errors import Conflict, Invalid, NotFound, ServiceError
from . import crypto, store
from .graph import GraphClient, GraphError

logger = logging.getLogger(__name__)

EVENT_SOURCE = {"FINISH": "embedded_signup", "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING": "coexistence"}
# Codigo de Meta del intercambio con un codigo vencido o ya usado (OAuthException).
CODE_EXPIRED = 100
PLACEHOLDER_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")
# Coexistencia: sincronizaciones que hay que pedir dentro de las 24 h del alta.
SMB_SYNC_TYPES = ("smb_app_state_sync", "history")


class MetaError(ServiceError):
    """Meta rechazo el pedido: el mensaje es el de Meta (sin tokens)."""
    status_code = 502
    default_code = "meta_error"

    def __init__(self, e: GraphError, prefix: str = ""):
        super().__init__(f"{prefix}{e.message}" if prefix else e.message,
                         details=[{"meta_code": e.code, "meta_subcode": e.subcode}])
        self.graph_error = e


class SignupDisabled(ServiceError):
    status_code = 503
    default_code = "wa_signup_disabled"


def graph_for(token: str) -> GraphClient:
    """Cliente de Graph por pedido (los tests lo reemplazan)."""
    return GraphClient(token, version=settings.wa_graph_version)


def config_problem() -> str | None:
    """Por que el alta no esta disponible (None si lo esta). La UI lo muestra."""
    missing = [name for name, value in (("WA_APP_ID", settings.wa_app_id), ("WA_APP_SECRET", settings.wa_app_secret),
                                        ("WA_CONFIG_ID", settings.wa_config_id)) if not value]
    if not settings.wa_token_key.strip():
        missing.append("WA_TOKEN_KEY")
    if missing:
        return f"Falta configurar {', '.join(missing)} en el servidor"
    if not crypto.enabled():
        return "WA_TOKEN_KEY invalida"
    return None


def _reason(step: str, e: GraphError) -> str:
    return f"{step}: code={e.code} {e.message}"[:255]


async def _close(graph) -> None:
    close = getattr(graph, "aclose", None)
    if close is not None:
        await close()


async def connect(s: Session, *, client_id: str, agent_id: str, code: str, waba_id: str, phone_number_id: str,
                  event: str, business_id: str | None = None, pin: str | None = None,
                  user_id: str | None = None,
                  graph_factory: Callable[[str], GraphClient] | None = None) -> WaAccount:
    """Alta o reconexion de un numero del cliente. Hace commit."""
    factory = graph_factory or graph_for
    if event == "FINISH_ONLY_WABA":
        raise ServiceError("Falta el número: el alta terminó sin un número de WhatsApp. Volvé a "
                           "conectar y cargá el número", code="signup_no_phone")
    if event not in EVENT_SOURCE:
        raise Invalid(f"Evento de alta no soportado: {event}")
    source = EVENT_SOURCE[event]
    phone_number_id = phone_number_id or ""
    # Coexistencia: FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING solo trae waba_id.
    if not re.fullmatch(r"\d{1,32}", phone_number_id) and not (source == "coexistence" and not phone_number_id):
        raise Invalid("Falta el phone_number_id del alta")
    problem = config_problem()
    if problem:
        raise crypto.TokenKeyMissing(problem) if "WA_TOKEN_KEY" in problem else SignupDisabled(problem)
    client = s.get(Client, client_id)
    if client is None or not client.active:
        raise NotFound("Cliente inexistente o inactivo")
    store.check_agent(s, client_id, agent_id)
    existing = store.account_by_pnid(s, phone_number_id) if phone_number_id else None
    if existing is not None and existing.client_id != client_id:
        raise Conflict("Ese número de WhatsApp ya está conectado a otra cuenta")

    # 1. Codigo -> business token (sin Bearer: va con el secret de la app).
    exchanger = factory("")
    try:
        token = await exchanger.exchange_code(settings.wa_app_id, settings.wa_app_secret, code)
    except GraphError as e:
        logger.warning("wa signup: intercambio fallido client=%s waba=%s code=%s", client_id, waba_id, e.code)
        if e.code == CODE_EXPIRED:
            raise ServiceError("El código de Meta venció o ya se usó: volvé a conectar",
                               code="signup_code_expired") from None
        raise MetaError(e, "Meta rechazó el alta: ") from None
    finally:
        await _close(exchanger)

    graph = factory(token)
    try:
        # 2. El numero tiene que ser de esa WABA (el token solo ve las del cliente).
        try:
            numbers = await graph.list_phone_numbers(waba_id)
        except GraphError as e:
            raise MetaError(e, "No se pudieron leer los números de la cuenta: ") from None
        if not phone_number_id:
            if len(numbers) != 1:
                raise ServiceError("No se pudo saber qué número conectar: la cuenta de WhatsApp Business tiene "
                                   f"{len(numbers)}", code="signup_no_phone")
            phone_number_id = str(numbers[0].get("id") or "")
            if not re.fullmatch(r"\d{1,32}", phone_number_id):
                raise ServiceError("Meta no devolvió el número de la cuenta", code="signup_no_phone")
            existing = store.account_by_pnid(s, phone_number_id)
            if existing is not None and existing.client_id != client_id:
                raise Conflict("Ese número de WhatsApp ya está conectado a otra cuenta")
        number = next((n for n in numbers if str(n.get("id")) == phone_number_id), None)
        if number is None:
            raise ServiceError("El número no pertenece a esa cuenta de WhatsApp Business", code="signup_mismatch")

        status, reason = "connected", None
        # 3. Suscripcion de la app a la WABA.
        try:
            await graph.subscribe_app(waba_id)
        except GraphError as e:
            logger.warning("wa signup: subscribed_apps fallo waba=%s code=%s", waba_id, e.code)
            status, reason = "pending", _reason("subscribed_apps", e)

        # 4. Registro (no en coexistencia: el numero sigue en la app). Al reconectar se usa
        # el PIN guardado: el numero ya tiene la verificacion en dos pasos con ese.
        previous_pin = store.pin_for(existing) if existing is not None else None
        pin = pin or previous_pin or crypto.new_pin()
        registered = False
        if source != "coexistence" and status == "connected":
            try:
                await graph.register(phone_number_id, pin)
                registered = True
            except GraphError as e:
                logger.warning("wa signup: register fallo pnid=%s code=%s", phone_number_id, e.code)
                status, reason = "pending", _reason("register", e)
        elif source == "coexistence" and status == "connected":
            status, reason = await _smb_sync(graph, phone_number_id)
    finally:
        await _close(graph)

    # 5. Alta o actualizacion de la cuenta.
    display = str(number.get("display_phone_number") or phone_number_id)[:32]
    name = str(number.get("verified_name") or "")[:128]
    fields = {"waba_id": waba_id, "business_id": business_id or None, "source": source,
              "quality_rating": str(number.get("quality_rating") or "") or None, "connected_by": user_id}
    account = store.account_by_pnid(s, phone_number_id)
    if account is not None and account.client_id != client_id:
        raise Conflict("Ese número de WhatsApp ya está conectado a otra cuenta")
    if account is None:
        account = store.create_account(s, client_id=client_id, agent_id=agent_id, phone_number_id=phone_number_id,
                                       display_phone_number=display, name=name, access_token=token, **fields)
    else:
        store.update_account(s, account, agent_id=agent_id, display_phone_number=display, active=True,
                             access_token=token, name=name or account.name)
        for key, value in fields.items():
            setattr(account, key, value)
    # Un PIN que fallo no pisa el que ya habia (si no, se pierde el bueno).
    if registered or (previous_pin is None and source != "coexistence"):
        account.pin_enc = crypto.encrypt(pin)
    store.mark_status(s, account, status, reason)
    s.commit()
    logger.info("wa signup: cuenta %s pnid=%s waba=%s client=%s source=%s status=%s", account.id,
                phone_number_id, waba_id, client_id, source, status)
    return account


async def _smb_sync(graph, phone_number_id: str) -> tuple[str, str | None]:
    """Coexistencia: pide las dos sincronizaciones. ("connected", None) o ("pending", motivo)."""
    for sync_type in SMB_SYNC_TYPES:
        try:
            await graph.smb_app_data(phone_number_id, sync_type)
        except GraphError as e:
            logger.warning("wa signup: smb_app_data %s fallo pnid=%s code=%s", sync_type, phone_number_id, e.code)
            return "pending", _reason(f"smb_app_data {sync_type}", e)
    return "connected", None


def _disconnect_if_auth(s: Session, account: WaAccount, e: GraphError) -> None:
    """Token del cliente rechazado: la cuenta queda desconectada (commit). Con el token
    global solo se loguea: es nuestro, no del cliente."""
    if not e.is_auth_error:
        return
    if store.has_own_token(account):
        store.mark_status(s, account, "disconnected", f"token_invalid code={e.code}")
        s.commit()
        logger.warning("wa: cuenta %s desconectada (token rechazado, code=%s)", account.id, e.code)
    else:
        logger.error("wa: el token global (WA_ACCESS_TOKEN) fue rechazado, code=%s", e.code)


async def retry_register(s: Session, account: WaAccount, pin: str | None = None,
                         graph_factory: Callable[[str], GraphClient] | None = None) -> WaAccount:
    """Reintenta la suscripcion y el registro de una cuenta pending (o los repite); en
    coexistencia, la suscripcion y la sincronizacion. PIN: el pedido, el guardado o uno
    nuevo. Sin token propio (numero de nuestro portafolio): el pedido o WA_REGISTRATION_PIN,
    nunca uno al azar. Hace commit."""
    own = store.has_own_token(account)
    pin = pin or store.pin_for(account) or (crypto.new_pin() if own else settings.wa_registration_pin)
    if account.source != "coexistence" and not re.fullmatch(r"\d{6}", pin or ""):
        raise Invalid("Falta el PIN de 6 dígitos del número (WA_REGISTRATION_PIN o el del pedido)")
    graph = (graph_factory or graph_for)(store.token_for(account))
    step = "subscribed_apps"
    try:
        await graph.subscribe_app(account.waba_id)
        if account.source == "coexistence":
            status, reason = await _smb_sync(graph, account.phone_number_id)
            if status != "connected":
                store.mark_status(s, account, status, reason)
                s.commit()
                raise ServiceError(f"Meta rechazó la sincronización: {reason}", code="meta_error")
        else:
            step = "register"
            await graph.register(account.phone_number_id, pin)
    except GraphError as e:
        _disconnect_if_auth(s, account, e)
        if not e.is_auth_error:
            store.mark_status(s, account, "pending", _reason(step, e))
            s.commit()
        raise MetaError(e) from None
    finally:
        await _close(graph)
    if own and account.source != "coexistence":
        account.pin_enc = crypto.encrypt(pin)
    store.mark_status(s, account, "connected")
    s.commit()
    return account


async def refresh(s: Session, account: WaAccount,
                  graph_factory: Callable[[str], GraphClient] | None = None) -> WaAccount:
    """Relee el numero en Meta (numero visible y calidad). Un 190 la desconecta."""
    graph = (graph_factory or graph_for)(store.token_for(account))
    try:
        data = await graph.get_phone_number(account.phone_number_id)
    except GraphError as e:
        _disconnect_if_auth(s, account, e)
        raise MetaError(e) from None
    finally:
        await _close(graph)
    if data.get("display_phone_number"):
        account.display_phone_number = str(data["display_phone_number"])[:32]
    account.quality_rating = str(data.get("quality_rating") or "") or None
    s.commit()
    return account


# --- Plantillas (se listan en vivo de Meta: no hay tabla) ---

async def list_templates(s: Session, account: WaAccount,
                         graph_factory: Callable[[str], GraphClient] | None = None) -> list[dict]:
    graph = (graph_factory or graph_for)(store.token_for(account))
    try:
        return await graph.list_templates(account.waba_id)
    except GraphError as e:
        _disconnect_if_auth(s, account, e)
        raise MetaError(e) from None
    finally:
        await _close(graph)


def template_payload(*, name: str, language: str, category: str, body: str, examples: list[str],
                     header_text: str | None = None, footer_text: str | None = None) -> dict:
    """Cuerpo de POST /{waba_id}/message_templates. Variables posicionales {{1}}..{{n}} en el
    cuerpo, con un ejemplo por variable (Meta los exige para revisarla). El encabezado y el
    pie van sin variables."""
    numbers = sorted({int(n) for n in PLACEHOLDER_RE.findall(body)})
    if numbers != list(range(1, len(numbers) + 1)):
        raise Invalid("Las variables del cuerpo tienen que ser {{1}}, {{2}}... seguidas")
    if len(examples) != len(numbers):
        raise Invalid(f"El cuerpo tiene {len(numbers)} variables: hace falta un ejemplo para cada una")
    if any(not e.strip() for e in examples):
        raise Invalid("Los ejemplos no pueden estar vacíos")
    for label, text in (("encabezado", header_text), ("pie", footer_text)):
        if text and "{{" in text:
            raise Invalid(f"El {label} no admite variables")
    components: list[dict] = []
    if header_text:
        components.append({"type": "HEADER", "format": "TEXT", "text": header_text})
    body_component: dict = {"type": "BODY", "text": body}
    if examples:
        body_component["example"] = {"body_text": [list(examples)]}
    components.append(body_component)
    if footer_text:
        components.append({"type": "FOOTER", "text": footer_text})
    return {"name": name, "language": language, "category": category, "components": components}


async def create_template(s: Session, account: WaAccount, payload: dict,
                          graph_factory: Callable[[str], GraphClient] | None = None) -> dict:
    graph = (graph_factory or graph_for)(store.token_for(account))
    try:
        result = await graph.create_template(account.waba_id, payload)
    except GraphError as e:
        _disconnect_if_auth(s, account, e)
        raise MetaError(e) from None
    finally:
        await _close(graph)
    logger.info("wa: plantilla creada account=%s id=%s status=%s", account.id, result.get("id"), result.get("status"))
    return result
