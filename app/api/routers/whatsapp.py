"""Numeros de WhatsApp conectados (wa_accounts): cada uno lo atiende un agente del cliente.

- Admin: ve y administra todas; alta manual (numeros de nuestro portafolio) y token.
- Usuario del cliente: conecta los suyos por Embedded Signup (/signup), elige el agente,
  los activa o desactiva, reintenta el registro, maneja sus plantillas y el ruteo por
  contacto (PUT /routes: los contactos de cada regla los atiende ese agente, en mensajes
  y llamadas de WhatsApp, en vez del agente por defecto de la cuenta). Una cuenta de
  otro cliente da 404; registro, /refresh y plantillas en una cuenta sin token propio
  (alta manual, token de nuestro portafolio), 403.
No hay DELETE (las conversaciones le hacen RESTRICT): se desactiva.
El token y el PIN nunca salen en una respuesta (solo has_token y has_pin).
Flujo de mensajes: app/whatsapp/service.py; alta: app/whatsapp/signup.py; plan en
docs/WHATSAPP_PLAN.md.
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from ...config import settings
from ...models import Agent, Client, WaAccount, WaRoute, WaThread
from ...services import wa_routing
from ...services.errors import Forbidden, Invalid, NotFound
from ...services.ratelimit import Limit
from ...services.security import Principal
from ...whatsapp import own_app, signup, store
from ...whatsapp.service import WhatsAppService, get_service
from ..deps import (
    DB,
    CurrentPrincipal,
    UserPrincipal,
    rate_limit,
    scoped_client_id,
)
from ..schemas import (
    WaAccountIn,
    WaAccountOut,
    WaAccountPatch,
    WaConfigOut,
    WaOwnAppIn,
    WaRegisterIn,
    WaRouteIn,
    WaRouteOut,
    WaSignupIn,
    WaTemplateCreated,
    WaTemplateIn,
    WaTemplateOut,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Lo que puede cambiar un usuario del cliente en su cuenta (el resto es de admin).
CLIENT_PATCH_FIELDS = {"agent_id", "name", "active"}

signup_limit = rate_limit("wa_signup", lambda: Limit(settings.wa_signup_per_hour, 3600), per="client",
                          message="Demasiados intentos de conectar WhatsApp. Probá en una hora.")
# Meta corta el registro tras varios PIN incorrectos (133016): el reintento tambien tiene tope.
register_limit = rate_limit("wa_register", lambda: Limit(settings.wa_signup_per_hour, 3600), per="client",
                            message="Demasiados reintentos de registro. Probá en una hora.")
templates_limit = rate_limit("wa_templates", lambda: Limit(settings.wa_templates_per_hour, 3600), per="client",
                             message="Demasiadas plantillas creadas. Probá en una hora.")


def _route_out(db, r: WaRoute) -> WaRouteOut:
    agent = db.get(Agent, r.agent_id)
    return WaRouteOut(agent_id=r.agent_id, agent_name=agent.name if agent else None,
                      contacts=list(r.contacts or []))


def _out(db, a: WaAccount) -> WaAccountOut:
    agent = db.get(Agent, a.agent_id)
    client = db.get(Client, a.client_id)
    return WaAccountOut(
        id=a.id, client_id=a.client_id, client_name=client.name if client else None, agent_id=a.agent_id,
        agent_name=agent.name if agent else None, phone_number_id=a.phone_number_id, waba_id=a.waba_id,
        business_id=a.business_id, display_phone_number=a.display_phone_number, name=a.name,
        has_token=bool(a.access_token), has_pin=bool(a.pin_enc), active=a.active, status=a.status,
        status_reason=a.status_reason, status_changed_at=a.status_changed_at, quality_rating=a.quality_rating,
        messaging_limit=a.messaging_limit, source=a.source, webhook_url=own_app.webhook_url(a),
        verify_token=own_app.verify_token_for(a) if a.webhook_key else None, has_app_secret=bool(a.app_secret),
        routes=[_route_out(db, r) for r in wa_routing.routes_for(db, a.id)],
        created_at=a.created_at, updated_at=a.updated_at)


def _get(db, account_id: str, p: Principal) -> WaAccount:
    """La cuenta, si quien pide puede verla. La de otro cliente da 404 (no se revela)."""
    a = store.get_account(db, account_id)
    if a is None or not p.can_access(a.client_id):
        raise NotFound("Cuenta de WhatsApp inexistente")
    return a


def _get_managed(db, account_id: str, p: Principal) -> WaAccount:
    """Para registro, datos de Meta y plantillas. Sin token propio la cuenta usa
    WA_ACCESS_TOKEN, el de nuestro portafolio (WABA compartida, PIN de .env): solo admin (o un admin
    que entró como el cliente)."""
    a = _get(db, account_id, p)
    if not (p.is_admin or p.support) and not store.has_own_token(a):
        raise Forbidden("Este número usa la cuenta de WhatsApp de la plataforma: lo administra un admin")
    return a


@router.get("/config", response_model=WaConfigOut)
def get_config(_: UserPrincipal):
    """Datos publicos para lanzar Embedded Signup (app_id y config_id no son secretos)."""
    problem = signup.config_problem()
    return WaConfigOut(enabled=problem is None, reason=problem, app_id=settings.wa_app_id or None,
                       config_id=settings.wa_config_id or None, graph_version=settings.wa_graph_version,
                       sdk_locale=settings.wa_sdk_locale)


@router.get("/accounts", response_model=list[WaAccountOut])
def list_accounts(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    return [_out(db, a) for a in store.list_accounts(db, scoped_client_id(p, client_id))]


@router.post("/accounts", response_model=WaAccountOut, status_code=201)
def create_account(body: WaAccountIn, p: CurrentPrincipal, db: DB):
    """Alta manual (un numero de nuestra WABA): admin, o un admin que entró como el cliente (va a ese cliente).
    409 si el phone_number_id ya esta, 404 si el agente no es del cliente. El token se guarda cifrado (503 sin
    WA_TOKEN_KEY)."""
    if not (p.is_admin or p.support):
        raise Forbidden("Requiere rol admin")
    data = body.model_dump()
    if p.support:
        data["client_id"] = p.client_id
    a = store.create_account(db, **data)
    db.commit()
    return _out(db, a)


@router.patch("/accounts/{account_id}", response_model=WaAccountOut)
def update_account(account_id: str, body: WaAccountPatch, p: CurrentPrincipal, db: DB):
    """access_token "" o null lo borra (vuelve a WA_ACCESS_TOKEN). Usuario del cliente:
    solo agent_id, name y active."""
    a = _get(db, account_id, p)
    changes = body.model_dump(exclude_unset=True)
    if not (p.is_admin or p.support) and set(changes) - CLIENT_PATCH_FIELDS:
        raise Forbidden("Solo un admin puede cambiar " + ", ".join(sorted(set(changes) - CLIENT_PATCH_FIELDS)))
    # Columnas NOT NULL: null es "sin cambio". El token si se puede borrar.
    changes = {k: v for k, v in changes.items() if v is not None or k == "access_token"}
    store.update_account(db, a, **changes)
    db.commit()
    return _out(db, a)


@router.post("/accounts/{account_id}/deactivate", response_model=WaAccountOut)
def deactivate_account(account_id: str, p: CurrentPrincipal, db: DB):
    """Deja de responder los mensajes que lleguen a ese numero (quedan ignored)."""
    a = _get(db, account_id, p)
    store.update_account(db, a, active=False)
    db.commit()
    return _out(db, a)


@router.put("/accounts/{account_id}/routes", response_model=list[WaRouteOut])
def set_account_routes(account_id: str, body: list[WaRouteIn], p: CurrentPrincipal, db: DB):
    """Reemplaza el ruteo por contacto de la cuenta: los contactos de cada regla los atiende
    ese agente, en los mensajes y las llamadas de WhatsApp, en vez del agente por defecto.
    409 si un contacto esta en dos reglas; 422 con agente ajeno, archivado o regla vacia."""
    a = _get(db, account_id, p)
    routes = wa_routing.set_routes(db, a, [(r.agent_id, r.contacts) for r in body])
    db.commit()
    return [_route_out(db, r) for r in routes]


@router.post("/accounts/own-app", response_model=WaAccountOut, status_code=201,
             dependencies=[Depends(signup_limit)])
async def connect_own_app(body: WaOwnAppIn, p: UserPrincipal, db: DB):
    """Conecta un número con la app de Meta propia del cliente (docs/ADMIN_SOPORTE_PLAN.md, sección 4): valida
    con Meta que el número sea de la WABA, suscribe su app a la WABA y devuelve la URL de webhook y el verify
    token para pegar en su app. 201 también si quedó `pending` (falló la suscripción: ver status_reason).
    409 si el número es de otra cuenta; 400 signup_mismatch si no es de esa WABA."""
    client_id = scoped_client_id(p, body.client_id)
    if not client_id:
        raise Invalid("Falta client_id")
    a = await own_app.connect(db, client_id=client_id, agent_id=body.agent_id, phone_number_id=body.phone_number_id,
                              waba_id=body.waba_id, access_token=body.access_token, app_secret=body.app_secret,
                              user_id=p.id)
    return _out(db, a)


@router.post("/signup", response_model=WaAccountOut, status_code=201, dependencies=[Depends(signup_limit)])
async def signup_account(body: WaSignupIn, p: UserPrincipal, db: DB):
    """Embedded Signup: cambia el codigo por el token del cliente, suscribe la app a su
    WABA, registra el numero y guarda la cuenta. 201 tambien si quedo `pending` (fallo
    la suscripcion o el registro: ver status_reason y reintentar con /register).
    409 si el numero es de otro cliente; 400 signup_code_expired si el codigo vencio."""
    client_id = body.client_id if p.is_admin else p.client_id
    if not client_id:
        raise NotFound("Falta client_id")
    a = await signup.connect(db, client_id=client_id, agent_id=body.agent_id, code=body.code,
                             waba_id=body.waba_id, phone_number_id=body.phone_number_id, event=body.event,
                             business_id=body.business_id, pin=body.pin, user_id=p.id)
    return _out(db, a)


@router.post("/accounts/{account_id}/register", response_model=WaAccountOut,
             dependencies=[Depends(register_limit)])
async def register_account(account_id: str, body: WaRegisterIn, p: CurrentPrincipal, db: DB):
    """Reintenta la suscripcion y el registro (cuenta pending). PIN: el pedido, el
    guardado o uno nuevo."""
    a = _get_managed(db, account_id, p)
    await signup.retry_register(db, a, body.pin)
    return _out(db, a)


@router.post("/accounts/{account_id}/refresh", response_model=WaAccountOut)
async def refresh_account(account_id: str, p: CurrentPrincipal, db: DB):
    """Relee el numero visible y la calidad en Meta. Un token rechazado la desconecta."""
    a = _get_managed(db, account_id, p)
    await signup.refresh(db, a)
    return _out(db, a)


@router.get("/accounts/{account_id}/templates", response_model=list[WaTemplateOut])
async def list_templates(account_id: str, p: CurrentPrincipal, db: DB):
    """Plantillas de la WABA de la cuenta, en vivo desde Meta (con estado de aprobacion)."""
    a = _get_managed(db, account_id, p)
    out = []
    for t in await signup.list_templates(db, a):
        if not t.get("id") or not t.get("name"):
            continue
        out.append(WaTemplateOut(
            id=str(t["id"]), name=str(t["name"]), language=str(t.get("language") or ""),
            category=str(t.get("category") or ""), status=str(t.get("status") or ""),
            rejected_reason=(str(t["rejected_reason"]) if t.get("rejected_reason") not in (None, "NONE") else None),
            components=[c for c in t.get("components") or [] if isinstance(c, dict)]))
    return out


@router.post("/accounts/{account_id}/templates", response_model=WaTemplateCreated, status_code=201,
             dependencies=[Depends(templates_limit)])
async def create_template(account_id: str, body: WaTemplateIn, p: CurrentPrincipal, db: DB):
    """Crea una plantilla en la WABA de la cuenta. Meta la revisa: queda PENDING."""
    a = _get_managed(db, account_id, p)
    payload = signup.template_payload(**body.model_dump())
    result = await signup.create_template(db, a, payload)
    return WaTemplateCreated(id=str(result.get("id") or ""), status=result.get("status"),
                             category=result.get("category"))


@router.post("/threads/{conversation_id}/close", status_code=204)
async def close_thread(conversation_id: str, p: CurrentPrincipal, db: DB,
                       service: Annotated[WhatsAppService, Depends(get_service)]):
    """Cierra una conversacion de WhatsApp: el proximo mensaje del contacto empieza otra, con la
    version vigente del agente. Esta queda en el historial. Es su fin, como el corte de una
    llamada (extraccion final del clasico). Cerrar una ya cerrada no hace nada."""
    thread = db.get(WaThread, conversation_id)
    if thread is None or not p.can_access(thread.client_id):
        raise NotFound("Conversación de WhatsApp inexistente")
    if thread.closed_at is not None:
        return
    store.close_thread(db, thread)
    db.commit()
    service.end(conversation_id)
