"""OAuth 2.1 del servidor MCP (docs/MCP_PLAN.md, 4.2): registro de clientes, autorización con PKCE,
tokens con rotación y su validación. Las rutas HTTP están en app/api/oauth.py.

El token actúa como un usuario del cliente del permiso (`OAuthGrant.client_id`): un admin elige el
cliente al autorizar y queda con rol de cliente. Vale solo para el MCP (`resource`), y la API lo acepta
solo en los pedidos internos del MCP (app/mcp/server.py).
"""
import asyncio
import base64
import datetime
import hashlib
import ipaddress
import json
import re
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Client, OAuthClient, OAuthCode, OAuthGrant, OAuthToken, Role, User
from .campaign_callbacks import resolve_public

ACCESS_PREFIX = "vaat_"
REFRESH_PREFIX = "vaar_"
ACCESS_TTL = datetime.timedelta(hours=1)
REFRESH_TTL = datetime.timedelta(days=30)
CODE_TTL = datetime.timedelta(minutes=10)
CIMD_TTL = datetime.timedelta(days=1)
SCOPES = ("mcp",)
MAX_REDIRECT_URIS = 10
MAX_METADATA_BYTES = 16 * 1024
# Esquemas que nunca son un redirect (los custom como cursor:// o vscode:// sí).
_BAD_SCHEMES = {"javascript", "data", "file", "vbscript", "about", "blob"}


class OAuthError(Exception):
    """Error con el formato de RFC 6749 (`error`, `error_description`)."""

    def __init__(self, error: str, description: str, status: int = 400):
        super().__init__(description)
        self.error, self.description, self.status = error, description, status

    def body(self) -> dict:
        return {"error": self.error, "error_description": self.description}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _is_loopback(host: str | None) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address((host or "").strip("[]")).is_loopback
    except ValueError:
        return False


def check_redirect_uri(uri: str) -> str:
    """https, http solo a loopback (apps de escritorio, RFC 8252) o un esquema propio (cursor://)."""
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if not scheme or scheme in _BAD_SCHEMES or parsed.fragment or len(uri) > 512:
        raise OAuthError("invalid_redirect_uri", f"redirect_uri inválido: {uri}")
    if scheme == "http" and not _is_loopback(parsed.hostname):
        raise OAuthError("invalid_redirect_uri", "redirect_uri http solo a localhost; si no, https")
    if scheme == "https" and not parsed.hostname:
        raise OAuthError("invalid_redirect_uri", f"redirect_uri inválido: {uri}")
    return uri


def redirect_allowed(client: OAuthClient, uri: str) -> bool:
    """Igual a uno registrado; a loopback, con cualquier puerto (RFC 8252, 7.3)."""
    if uri in client.redirect_uris:
        return True
    asked = urlparse(uri)
    if asked.scheme != "http" or not _is_loopback(asked.hostname):
        return False
    for registered in map(urlparse, client.redirect_uris):
        if (registered.scheme, registered.hostname, registered.path) == (asked.scheme, asked.hostname, asked.path):
            return True
    return False


# ---------- clientes ----------

def register_client(s: Session, meta: dict) -> tuple[OAuthClient, str | None]:
    """Registro dinámico (RFC 7591). Devuelve el cliente y su secreto si lo pidió confidencial."""
    uris = meta.get("redirect_uris")
    if not isinstance(uris, list) or not uris or len(uris) > MAX_REDIRECT_URIS or not all(
            isinstance(u, str) for u in uris):
        raise OAuthError("invalid_redirect_uri", f"redirect_uris: entre 1 y {MAX_REDIRECT_URIS} URLs")
    uris = [check_redirect_uri(u) for u in uris]
    method = meta.get("token_endpoint_auth_method") or "none"
    if method not in ("none", "client_secret_post", "client_secret_basic"):
        raise OAuthError("invalid_client_metadata", f"token_endpoint_auth_method no soportado: {method}")
    grants = meta.get("grant_types") or ["authorization_code"]
    if not set(grants) <= {"authorization_code", "refresh_token"}:
        raise OAuthError("invalid_client_metadata", "grant_types: authorization_code y refresh_token")
    secret = None if method == "none" else secrets.token_urlsafe(32)
    client = OAuthClient(id="mcp_" + secrets.token_urlsafe(16), kind="dcr",
                         name=str(meta.get("client_name") or "")[:128], client_uri=_uri(meta.get("client_uri")),
                         redirect_uris=uris, secret_hash=_hash(secret) if secret else None)
    s.add(client)
    s.commit()
    return client, secret


def _uri(value) -> str | None:
    return value[:512] if isinstance(value, str) and value.startswith("https://") else None


async def _fetch_metadata(url: str) -> dict:
    """El Client ID Metadata Document: https, host público, sin redirecciones y chico."""
    parsed = urlparse(url)
    try:
        await asyncio.to_thread(resolve_public, parsed.hostname, parsed.port)
    except ValueError as e:
        raise OAuthError("invalid_client", f"client_id: {e}") from None
    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as http:
        try:
            r = await http.get(url, headers={"Accept": "application/json"})
        except httpx.HTTPError:
            raise OAuthError("invalid_client", "No se pudo leer el documento del client_id") from None
    if r.status_code != 200 or len(r.content) > MAX_METADATA_BYTES:
        raise OAuthError("invalid_client", "El documento del client_id no responde 200 o es muy grande")
    try:
        doc = r.json()
    except json.JSONDecodeError:
        raise OAuthError("invalid_client", "El documento del client_id no es JSON") from None
    if not isinstance(doc, dict):
        raise OAuthError("invalid_client", "El documento del client_id no es un objeto JSON")
    return doc


# Reemplazable en los tests.
fetch_metadata = _fetch_metadata


def _is_cimd(client_id: str) -> bool:
    parsed = urlparse(client_id)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.path not in ("", "/")


async def resolve_client(s: Session, client_id: str) -> OAuthClient:
    """El cliente registrado, o el del metadata document (leído y guardado por un día)."""
    if not client_id:
        raise OAuthError("invalid_request", "Falta client_id")
    client = s.get(OAuthClient, client_id)
    fresh = client is not None and (client.kind == "dcr" or (
        client.fetched_at and utcnow() - client.fetched_at < CIMD_TTL))
    if fresh:
        return client
    if not _is_cimd(client_id):
        raise OAuthError("invalid_client", "client_id desconocido: registrá el cliente o usá un metadata document")
    doc = await fetch_metadata(client_id)
    if doc.get("client_id") != client_id:
        raise OAuthError("invalid_client", "El documento no declara este client_id")
    uris = doc.get("redirect_uris")
    if not isinstance(uris, list) or not uris or len(uris) > MAX_REDIRECT_URIS:
        raise OAuthError("invalid_client", "El documento no tiene redirect_uris válidos")
    uris = [check_redirect_uri(u) for u in uris if isinstance(u, str)]
    if client is None:
        client = OAuthClient(id=client_id, kind="cimd")
        s.add(client)
    client.name = str(doc.get("client_name") or urlparse(client_id).hostname)[:128]
    client.client_uri = _uri(doc.get("client_uri"))
    client.redirect_uris = uris
    client.fetched_at = utcnow()
    s.commit()
    return client


def authenticate_client(client: OAuthClient, secret: str | None) -> None:
    """Los confidenciales mandan su secreto al endpoint de token; los públicos, nada (PKCE)."""
    if client.secret_hash is None:
        return
    if not secret or not secrets.compare_digest(_hash(secret), client.secret_hash):
        raise OAuthError("invalid_client", "Secreto del cliente inválido", status=401)


# ---------- autorización ----------

@dataclass
class AuthorizeRequest:
    client: OAuthClient
    redirect_uri: str
    code_challenge: str
    state: str | None
    scope: str
    resource: str


def same_resource(given: str, expected: str) -> bool:
    """El `resource` que manda el cliente es la URL del servidor MCP: con `?toolsets=...` sigue siendo el mismo."""
    return given.split("#")[0].split("?")[0].rstrip("/") == expected


async def parse_authorize(s: Session, params: dict, expected_resource: str) -> AuthorizeRequest:
    """Valida el pedido de /authorize. Un error de cliente o de redirect_uri no se redirige (OAuthError con
    status 400); el resto también es OAuthError, pero se puede devolver al redirect_uri (`redirect_error`)."""
    client = await resolve_client(s, params.get("client_id") or "")
    redirect_uri = params.get("redirect_uri") or ""
    if not redirect_uri and len(client.redirect_uris) == 1:
        redirect_uri = client.redirect_uris[0]
    if not redirect_allowed(client, redirect_uri):
        raise OAuthError("invalid_request", "redirect_uri no registrado para este cliente")
    req = AuthorizeRequest(client=client, redirect_uri=redirect_uri, code_challenge="", state=params.get("state"),
                           scope="mcp", resource=expected_resource)
    if params.get("response_type") != "code":
        raise RedirectError(req, "unsupported_response_type", "Solo response_type=code")
    challenge = params.get("code_challenge") or ""
    if params.get("code_challenge_method") != "S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", challenge):
        raise RedirectError(req, "invalid_request", "Hace falta PKCE con code_challenge_method=S256")
    req.code_challenge = challenge
    scopes = set((params.get("scope") or "mcp").split())
    if not scopes <= set(SCOPES):
        raise RedirectError(req, "invalid_scope", f"Alcances soportados: {' '.join(SCOPES)}")
    resource = params.get("resource")
    if resource and not same_resource(resource, expected_resource):
        raise RedirectError(req, "invalid_target", f"resource tiene que ser {expected_resource}")
    return req


class RedirectError(OAuthError):
    """Error que se devuelve al redirect_uri del cliente (ya validado)."""

    def __init__(self, req: AuthorizeRequest, error: str, description: str):
        super().__init__(error, description)
        self.req = req


def redirect_url(req: AuthorizeRequest, issuer: str, **params) -> str:
    query = {**params, "iss": issuer}
    if req.state is not None:
        query["state"] = req.state
    sep = "&" if "?" in req.redirect_uri else "?"
    return req.redirect_uri + sep + urlencode(query)


def tenant_for(s: Session, user: User, client_id: str | None) -> Client:
    """El cliente en el que va a actuar el agente: el del usuario, o el que elige un admin."""
    if user.role == Role.client:
        if client_id and client_id != user.client_id:
            raise OAuthError("access_denied", "Tu usuario no tiene acceso a ese cliente", status=403)
        client_id = user.client_id
    if not client_id:
        raise OAuthError("invalid_request", "Elegí el cliente con el que va a trabajar el agente")
    client = s.get(Client, client_id)
    if client is None or not client.active:
        raise OAuthError("invalid_request", "Cliente inexistente o inactivo")
    return client


def approve(s: Session, req: AuthorizeRequest, user: User, tenant: Client, issuer: str) -> str:
    """Crea el permiso y el código; devuelve la URL a la que vuelve el navegador."""
    grant = OAuthGrant(oauth_client_id=req.client.id, user_id=user.id, client_id=tenant.id, scope=req.scope,
                       resource=req.resource, session_version=user.session_version)
    s.add(grant)
    s.flush()
    code = secrets.token_urlsafe(32)
    s.add(OAuthCode(code_hash=_hash(code), grant_id=grant.id, redirect_uri=req.redirect_uri,
                    code_challenge=req.code_challenge, expires_at=utcnow() + CODE_TTL))
    s.commit()
    return redirect_url(req, issuer, code=code)


# ---------- tokens ----------

def _issue(s: Session, grant: OAuthGrant) -> dict:
    access = ACCESS_PREFIX + secrets.token_urlsafe(32)
    refresh = REFRESH_PREFIX + secrets.token_urlsafe(32)
    now = utcnow()
    s.add_all([OAuthToken(grant_id=grant.id, kind="access", token_hash=_hash(access), expires_at=now + ACCESS_TTL),
               OAuthToken(grant_id=grant.id, kind="refresh", token_hash=_hash(refresh),
                          expires_at=now + REFRESH_TTL)])
    s.commit()
    return {"access_token": access, "token_type": "Bearer", "expires_in": int(ACCESS_TTL.total_seconds()),
            "refresh_token": refresh, "scope": grant.scope}


def _pkce_ok(verifier: str, challenge: str) -> bool:
    if not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier or ""):
        return False
    digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return secrets.compare_digest(digest, challenge)


def _grant_alive(s: Session, grant: OAuthGrant | None) -> User | None:
    """El usuario del permiso si sigue valiendo: sin revocar, activo y sin cambio de clave."""
    if grant is None or grant.revoked_at is not None:
        return None
    user = s.get(User, grant.user_id)
    client = s.get(Client, grant.client_id)
    if user is None or not user.active or user.session_version != grant.session_version:
        return None
    if client is None or not client.active:
        return None
    return user


def exchange_code(s: Session, client: OAuthClient, form: dict, expected_resource: str) -> dict:
    row = s.get(OAuthCode, _hash(form.get("code") or ""))
    grant = s.get(OAuthGrant, row.grant_id) if row else None
    if row is None or grant is None or grant.oauth_client_id != client.id:
        raise OAuthError("invalid_grant", "Código inválido")
    if row.used_at is not None:
        # Un código usado dos veces: alguien lo robó. Se corta el permiso entero (RFC 6749, 4.1.2).
        grant.revoked_at = utcnow()
        s.commit()
        raise OAuthError("invalid_grant", "Código ya usado")
    if row.expires_at < utcnow():
        raise OAuthError("invalid_grant", "Código vencido")
    if (form.get("redirect_uri") or row.redirect_uri) != row.redirect_uri:
        raise OAuthError("invalid_grant", "redirect_uri distinto al de la autorización")
    if not _pkce_ok(form.get("code_verifier") or "", row.code_challenge):
        raise OAuthError("invalid_grant", "code_verifier inválido")
    resource = form.get("resource")
    if resource and not same_resource(resource, expected_resource):
        raise OAuthError("invalid_target", f"resource tiene que ser {expected_resource}")
    row.used_at = utcnow()
    if _grant_alive(s, grant) is None:
        s.commit()
        raise OAuthError("invalid_grant", "El permiso ya no vale")
    return _issue(s, grant)


def refresh(s: Session, client: OAuthClient, form: dict) -> dict:
    """Rotación: el refresh usado se revoca y sale un par nuevo."""
    token = s.scalar(select(OAuthToken).where(OAuthToken.token_hash == _hash(form.get("refresh_token") or ""),
                                              OAuthToken.kind == "refresh"))
    grant = s.get(OAuthGrant, token.grant_id) if token else None
    if token is None or grant is None or grant.oauth_client_id != client.id:
        raise OAuthError("invalid_grant", "refresh_token inválido")
    if token.revoked_at is not None:
        # Reuso de un refresh ya rotado: se corta el permiso (OAuth 2.1, 4.3.1).
        grant.revoked_at = utcnow()
        s.commit()
        raise OAuthError("invalid_grant", "refresh_token ya usado")
    if token.expires_at < utcnow() or _grant_alive(s, grant) is None:
        raise OAuthError("invalid_grant", "refresh_token vencido o permiso revocado")
    token.revoked_at = utcnow()
    return _issue(s, grant)


def revoke_token(s: Session, client: OAuthClient, value: str) -> None:
    """RFC 7009: revoca el token y, si es un refresh, el permiso entero. Un token desconocido no es error."""
    token = s.scalar(select(OAuthToken).where(OAuthToken.token_hash == _hash(value or "")))
    grant = s.get(OAuthGrant, token.grant_id) if token else None
    if token is None or grant is None or grant.oauth_client_id != client.id:
        return
    token.revoked_at = token.revoked_at or utcnow()
    if token.kind == "refresh":
        grant.revoked_at = grant.revoked_at or utcnow()
    s.commit()


@dataclass(frozen=True)
class Access:
    grant: OAuthGrant
    user: User


def authenticate(s: Session, value: str) -> Access | None:
    """Un access token vigente, con su permiso y su usuario; None si no vale."""
    if not value.startswith(ACCESS_PREFIX):
        return None
    token = s.scalar(select(OAuthToken).where(OAuthToken.token_hash == _hash(value), OAuthToken.kind == "access"))
    if token is None or token.revoked_at is not None or token.expires_at < utcnow():
        return None
    grant = s.get(OAuthGrant, token.grant_id)
    user = _grant_alive(s, grant)
    if user is None:
        return None
    now = utcnow()
    if grant.last_used_at is None or now - grant.last_used_at > datetime.timedelta(minutes=1):
        grant.last_used_at = now
        s.commit()
    return Access(grant, user)


# ---------- agentes conectados (UI) ----------

def list_grants(s: Session, client_id: str | None) -> list[tuple[OAuthGrant, OAuthClient, User]]:
    """Los permisos vigentes de un cliente (None: todos, para un admin), los más nuevos primero. Solo los
    que llegaron a emitir tokens: una autorización abandonada antes del canje no es un agente conectado."""
    q = (select(OAuthGrant, OAuthClient, User).join(OAuthClient, OAuthClient.id == OAuthGrant.oauth_client_id)
         .join(User, User.id == OAuthGrant.user_id).where(OAuthGrant.revoked_at.is_(None))
         .where(exists().where(OAuthToken.grant_id == OAuthGrant.id))
         .order_by(OAuthGrant.created_at.desc()))
    if client_id:
        q = q.where(OAuthGrant.client_id == client_id)
    return [tuple(r) for r in s.execute(q).all()]


def revoke_grant(s: Session, grant: OAuthGrant) -> None:
    grant.revoked_at = grant.revoked_at or utcnow()
    s.commit()
