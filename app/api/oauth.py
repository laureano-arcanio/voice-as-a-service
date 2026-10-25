"""OAuth 2.1 del servidor MCP (docs/MCP_PLAN.md, 4.2; lógica en services/oauth.py).

- Metadata: /.well-known/oauth-protected-resource[/mcp] (RFC 9728) y
  /.well-known/oauth-authorization-server (RFC 8414). El emisor es el mismo host que sirve /mcp
  (app.atentina.com.ar o mcp.atentina.com.ar): el login y la pantalla de consentimiento son del panel.
- /oauth/authorize: redirige a la pantalla de consentimiento del panel (/oauth/consent, con sesión);
  esa pantalla usa /api/v1/oauth/authorize para validar el pedido y aprobarlo.
- /oauth/register (RFC 7591), /oauth/token y /oauth/revoke (RFC 7009): sin cookies ni sesión.
- /api/v1/oauth/grants: los agentes conectados de un cliente, para verlos y revocarlos.
"""
import base64
from typing import Annotated
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..models import Client, OAuthGrant, User
from ..services import oauth
from ..services.errors import Forbidden, NotFound
from ..services.ratelimit import Limit
from .deps import DB, SessionPrincipal, rate_limit, request_is_https, scoped_client_id
from .schemas import OAuthApproveIn, OAuthAuthorizeOut, OAuthGrantOut, OAuthRedirectOut

router = APIRouter(include_in_schema=False)
api_router = APIRouter(prefix="/oauth", tags=["oauth"])

NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
_register_limit = Depends(rate_limit("oauth_register", Limit(20, 3600), per="ip"))
_token_limit = Depends(rate_limit("oauth_token", Limit(120, 60), per="ip"))


def issuer(request: Request) -> str:
    host = request.headers.get("host", "localhost")
    return f"{'https' if request_is_https(request) else 'http'}://{host}"


def resource(request: Request) -> str:
    return issuer(request) + "/mcp"


def _error(e: oauth.OAuthError) -> JSONResponse:
    return JSONResponse(e.body(), status_code=e.status, headers=NO_STORE)


# ---------- metadata ----------

@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp")
def protected_resource(request: Request):
    return {"resource": resource(request), "authorization_servers": [issuer(request)],
            "scopes_supported": list(oauth.SCOPES), "bearer_methods_supported": ["header"],
            "resource_name": "Atentina", "resource_documentation": "https://atentina.com.ar/desarrolladores/docs/mcp"}


@router.get("/.well-known/oauth-authorization-server")
def authorization_server(request: Request):
    base = issuer(request)
    return {"issuer": base, "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token", "registration_endpoint": f"{base}/oauth/register",
            "revocation_endpoint": f"{base}/oauth/revoke", "scopes_supported": list(oauth.SCOPES),
            "response_types_supported": ["code"], "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
            "revocation_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
            "authorization_response_iss_parameter_supported": True,
            "client_id_metadata_document_supported": True}


# ---------- autorización ----------

@router.get("/oauth/authorize")
def authorize(request: Request):
    """La pantalla de consentimiento del panel, con el mismo pedido (la valida al abrirse)."""
    query = request.url.query
    return RedirectResponse("/oauth/consent" + (f"?{query}" if query else ""), status_code=302)


def _params(raw: dict) -> dict:
    return {k: v for k, v in raw.items() if isinstance(v, str)}


@api_router.get("/authorize", response_model=OAuthAuthorizeOut)
async def authorize_info(request: Request, p: SessionPrincipal, db: DB):
    """Qué agente pide acceso, para la pantalla de consentimiento. 400 si el pedido no es válido."""
    try:
        req = await oauth.parse_authorize(db, dict(request.query_params), resource(request))
    except oauth.RedirectError as e:
        return OAuthAuthorizeOut(valid=False, error=e.error, error_description=e.description,
                                 redirect_to=oauth.redirect_url(e.req, issuer(request), error=e.error,
                                                                error_description=e.description))
    except oauth.OAuthError as e:
        return OAuthAuthorizeOut(valid=False, error=e.error, error_description=e.description)
    user = db.get(User, p.id)
    tenant = db.get(Client, user.client_id) if user.client_id else None
    return OAuthAuthorizeOut(valid=True, client_name=req.client.name or req.client.id,
                             client_uri=req.client.client_uri, verified=req.client.kind == "cimd",
                             redirect_host=_host(req.redirect_uri), scope=req.scope, resource=req.resource,
                             needs_client=p.is_admin, client_id=tenant.id if tenant else None,
                             client_name_tenant=tenant.name if tenant else None)


def _host(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.hostname or parsed.scheme


@api_router.post("/authorize", response_model=OAuthRedirectOut)
async def authorize_decide(body: OAuthApproveIn, request: Request, p: SessionPrincipal, db: DB):
    """Aprueba o rechaza: devuelve la URL a la que vuelve el navegador (con `code` o con `error`)."""
    try:
        req = await oauth.parse_authorize(db, _params(body.params), resource(request))
    except oauth.RedirectError as e:
        return OAuthRedirectOut(redirect_to=oauth.redirect_url(e.req, issuer(request), error=e.error,
                                                               error_description=e.description))
    except oauth.OAuthError as e:
        raise Forbidden(e.description, e.error) from None
    if not body.approve:
        return OAuthRedirectOut(redirect_to=oauth.redirect_url(req, issuer(request), error="access_denied",
                                                               error_description="El usuario no dio acceso"))
    user = db.get(User, p.id)
    try:
        tenant = oauth.tenant_for(db, user, body.client_id)
    except oauth.OAuthError as e:
        raise Forbidden(e.description, e.error) from None
    return OAuthRedirectOut(redirect_to=oauth.approve(db, req, user, tenant, issuer(request)))


# ---------- registro, token y revocación ----------

@router.post("/oauth/register", dependencies=[_register_limit])
async def register(request: Request, db: DB):
    try:
        meta = await request.json()
    except ValueError:
        meta = None
    if not isinstance(meta, dict):
        return _error(oauth.OAuthError("invalid_client_metadata", "El cuerpo tiene que ser un objeto JSON"))
    try:
        client, secret = oauth.register_client(db, meta)
    except oauth.OAuthError as e:
        return _error(e)
    out = {"client_id": client.id, "client_id_issued_at": int(client.created_at.timestamp()),
           "client_name": client.name, "redirect_uris": client.redirect_uris,
           "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
           "token_endpoint_auth_method": meta.get("token_endpoint_auth_method") or "none", "scope": "mcp"}
    if secret:
        out |= {"client_secret": secret, "client_secret_expires_at": 0}
    return JSONResponse(out, status_code=201, headers=NO_STORE)


def _basic(request: Request) -> tuple[str | None, str | None]:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        return None, None
    try:
        user, _, password = base64.b64decode(header[6:]).decode().partition(":")
    except ValueError:
        return None, None
    return unquote(user), unquote(password)


async def _form_and_client(request: Request, db) -> tuple[dict, object]:
    form = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
    basic_id, basic_secret = _basic(request)
    client = await oauth.resolve_client(db, basic_id or form.get("client_id") or "")
    oauth.authenticate_client(client, basic_secret or form.get("client_secret"))
    return form, client


@router.post("/oauth/token", dependencies=[_token_limit])
async def token(request: Request, db: DB):
    try:
        form, client = await _form_and_client(request, db)
        grant_type = form.get("grant_type")
        if grant_type == "authorization_code":
            out = oauth.exchange_code(db, client, form, resource(request))
        elif grant_type == "refresh_token":
            out = oauth.refresh(db, client, form)
        else:
            raise oauth.OAuthError("unsupported_grant_type", "grant_type: authorization_code o refresh_token")
    except oauth.OAuthError as e:
        return _error(e)
    return JSONResponse(out, headers=NO_STORE)


@router.post("/oauth/revoke", dependencies=[_token_limit])
async def revoke(request: Request, db: DB):
    try:
        form, client = await _form_and_client(request, db)
    except oauth.OAuthError as e:
        return _error(e)
    oauth.revoke_token(db, client, form.get("token") or "")
    return JSONResponse({}, headers=NO_STORE)


# ---------- agentes conectados ----------

@api_router.get("/grants", response_model=list[OAuthGrantOut])
def list_grants(p: SessionPrincipal, db: DB, client_id: str | None = None):
    """Los agentes de IA conectados por OAuth al cliente. Un admin, todos o los de `client_id`."""
    rows = oauth.list_grants(db, scoped_client_id(p, client_id))
    return [OAuthGrantOut(id=g.id, client_id=g.client_id, app_name=c.name or c.id, app_uri=c.client_uri,
                          verified=c.kind == "cimd", user_email=u.email, created_at=g.created_at,
                          last_used_at=g.last_used_at) for g, c, u in rows]


@api_router.delete("/grants/{grant_id}", status_code=204)
def revoke_grant(grant_id: str, p: SessionPrincipal, db: DB):
    grant = db.get(OAuthGrant, grant_id)
    if grant is None or not p.can_access(grant.client_id):
        raise NotFound("Agente conectado inexistente")
    oauth.revoke_grant(db, grant)
