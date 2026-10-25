"""Servidor MCP de Atentina (docs/MCP_PLAN.md): POST /mcp, Streamable HTTP sin estado y con
respuestas JSON (sin SSE), sin el SDK, como el cliente de app/apps/client.py.

Auth: API key con el scope `mcp` (`Authorization: Bearer vaas_...`) o token OAuth (app/api/oauth.py). Cada
herramienta es un pedido a `/api/v1` en el mismo proceso (ASGI, sin red) con esa credencial: los permisos, los límites del plan y la
quota los aplica la API, no este módulo. Acá solo se adelanta el chequeo del plan para devolver el
motivo claro (`feature_not_in_plan`) antes de pedir.
"""
import base64
import binascii
import json
import logging
import time
from dataclasses import dataclass
from typing import Annotated, Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials

from ..api import oauth as oauth_routes
from ..api.deps import DB, MCP_INTERNAL_HEADER, MCP_INTERNAL_SECRET, _api_key, _bearer
from ..config import settings
from ..services import api_usage, mcp_usage, oauth
from ..services.security import API_KEY_PREFIX
from . import catalog, guides
from .catalog import Tool

logger = logging.getLogger(__name__)
router = APIRouter()

# La primera es la que se ofrece si el cliente pide una que no conocemos.
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2025-11-25")
SERVER_INFO = {"name": "atentina", "title": "Atentina", "version": "1.0.0"}
INSTRUCTIONS = ("Atentina: agentes de voz por teléfono, WhatsApp y web para empresas. Con estas herramientas "
                "se consultan los agentes, las llamadas y sus transcripciones, los contactos, las campañas y el "
                "equipo de derivación del cliente. Empezá por get_plan_tools: dice qué incluye el plan.")
API = "/api/v1"
MAX_AUDIO_BYTES = 5 * 1024 * 1024
UPGRADE_PATH = "/plan"


@dataclass(frozen=True)
class Identity:
    """Quien usa el MCP: una API key `mcp` (o `mcp_read`) o un token OAuth (un usuario en un cliente, o un
    admin en toda la plataforma: client_id None y `admin`)."""
    kind: str               # api_key | oauth
    id: str                 # la key o el permiso (OAuthGrant)
    client_id: str | None
    token: str
    admin: bool = False     # toolset `admin` y nada de cliente
    read_only: bool = False  # key `mcp_read`: solo las herramientas de lectura


def _unauthorized_mcp(request: Request, detail: str) -> HTTPException:
    # resource_metadata: por ahí descubre el cliente MCP el servidor de autorización (RFC 9728).
    metadata = f"{oauth_routes.issuer(request)}/.well-known/oauth-protected-resource/mcp"
    return HTTPException(401, detail, headers={"WWW-Authenticate": f'Bearer resource_metadata="{metadata}"'})


def mcp_identity(request: Request, db: DB,
                 creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> Identity:
    """API key con el scope `mcp` o token OAuth para este recurso: ni la cookie del panel ni una key `calls`."""
    token = creds.credentials if creds else ""
    if token.startswith(oauth.ACCESS_PREFIX):
        access = oauth.authenticate(db, token)
        if access is None:
            raise _unauthorized_mcp(request, "Token OAuth inválido, vencido o revocado")
        if access.grant.resource.rstrip("/") != oauth_routes.resource(request):
            raise _unauthorized_mcp(request, "Este token es para otro servidor MCP")
        return Identity("oauth", access.grant.id, access.grant.client_id, token,
                        admin=access.grant.client_id is None)
    if not token.startswith(API_KEY_PREFIX):
        raise _unauthorized_mcp(request, "Iniciá sesión (OAuth) o usá una API key con el alcance mcp "
                                         "(Authorization: Bearer vaas_...)")
    try:
        key = _api_key(db, token)
    except HTTPException:
        raise _unauthorized_mcp(request, "API key inválida o revocada") from None
    scopes = api_usage.parse_scopes(key.scopes)
    if not scopes & {api_usage.SCOPE_MCP, api_usage.SCOPE_MCP_READ}:
        raise _unauthorized_mcp(request, "Esta API key no tiene el alcance mcp: creá una con ese alcance en el panel")
    return Identity("api_key", key.id, key.client_id, token, read_only=api_usage.SCOPE_MCP not in scopes)


class Ctx:
    """Un pedido MCP: quién lo hace y un cliente HTTP en proceso contra la misma app."""

    def __init__(self, request: Request, who: Identity):
        self.who = who
        self.client_id = who.client_id
        # El header interno deja pasar el token OAuth a /api/v1 (deps.get_principal); desde afuera no se acepta.
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=request.app), base_url="http://mcp.internal",
                                      headers={"Authorization": f"Bearer {who.token}",
                                               MCP_INTERNAL_HEADER: MCP_INTERNAL_SECRET}, timeout=60)

    async def api(self, method: str, path: str, **kwargs) -> httpx.Response:
        # Las de admin traen client_id como argumento (ya reemplazado); acá queda solo el del token.
        return await self.http.request(method, API + path.replace("{client_id}", self.client_id or ""), **kwargs)


# ---------- JSON-RPC ----------

def _result(msg_id, result: dict) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _error(msg_id, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}},
                        status_code=status)


def _origin_ok(request: Request) -> bool:
    """La especificación pide validar Origin (DNS rebinding). Los clientes MCP no son navegadores y no
    lo mandan; si viene, tiene que ser uno de los nuestros."""
    origin = request.headers.get("origin")
    if origin is None:
        return True
    allowed = {o.strip().rstrip("/").lower() for o in settings.app_origins.split(",") if o.strip()}
    return origin.rstrip("/").lower() in allowed


@router.post("/mcp", include_in_schema=False)
async def mcp(request: Request, db: DB, who: Annotated[Identity, Depends(mcp_identity)]):
    if not _origin_ok(request):
        return _error(None, -32600, "Origin no permitido", status=403)
    try:
        msg = await request.json()
    except ValueError:
        return _error(None, -32700, "JSON inválido", status=400)
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Pedido JSON-RPC inválido",
                      status=400)
    method, msg_id, params = msg["method"], msg.get("id"), msg.get("params") or {}
    if "id" not in msg:   # notificación (notifications/initialized, cancelled...): sin respuesta
        return Response(status_code=202)
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _result(msg_id, {"protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                                "capabilities": {"tools": {"listChanged": False}, "resources": {},
                                                 "prompts": {"listChanged": False}},
                                "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS})
    if method == "ping":
        return _result(msg_id, {})
    toolsets = request.query_params.get("toolsets")
    if method == "tools/list":
        openapi = request.app.openapi()
        return _result(msg_id, {"tools": [_describe(t, openapi) for t in _visible(toolsets, who)]})
    if method == "tools/call":
        tool = catalog.BY_NAME.get(params.get("name"))
        if tool is None or tool not in _visible(toolsets, who):
            return _error(msg_id, -32602, f"Herramienta desconocida: {params.get('name')}")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return _error(msg_id, -32602, "`arguments` tiene que ser un objeto")
        ctx = Ctx(request, who)
        started = time.monotonic()
        try:
            result = await _call(ctx, tool, args, request.app.openapi())
        finally:
            await ctx.http.aclose()
        error = bool(result.get("isError", False))
        logger.info("mcp %s cliente=%s %s=%s error=%s", tool.name, ctx.client_id, who.kind, who.id, error)
        try:
            mcp_usage.record(db, who.client_id, tool.name, error, round((time.monotonic() - started) * 1000))
        except Exception:   # la métrica no corta la respuesta
            db.rollback()
            logger.exception("mcp: no se pudo anotar el uso de %s", tool.name)
        return _result(msg_id, result)
    if method == "resources/list":
        return _result(msg_id, {"resources": guides.list_resources()})
    if method == "resources/read":
        uri = params.get("uri")
        if uri == guides.SCHEMA_URI:
            ctx = Ctx(request, who)
            try:
                r = await ctx.api("GET", "/agents/schema")
            finally:
                await ctx.http.aclose()
            return _result(msg_id, {"contents": [{"uri": uri, "mimeType": "application/json", "text": r.text}]})
        text = guides.read_resource(uri)
        if text is None:
            return _error(msg_id, -32002, f"Recurso desconocido: {uri}")
        return _result(msg_id, {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]})
    if method == "prompts/list":
        return _result(msg_id, {"prompts": guides.list_prompts()})
    if method == "prompts/get":
        prompt = guides.get_prompt(params.get("name"), params.get("arguments") or {})
        if prompt is None:
            return _error(msg_id, -32602, f"Prompt desconocido: {params.get('name')}")
        return _result(msg_id, prompt)
    return _error(msg_id, -32601, f"Método no soportado: {method}")


@router.get("/mcp", include_in_schema=False)
def mcp_get():
    # Sin stream de avisos del servidor: la especificación pide 405.
    return Response(status_code=405, headers={"Allow": "POST"})


# ---------- herramientas ----------

def _visible(toolsets: str | None, who: Identity) -> list[Tool]:
    tools = catalog.select(toolsets, admin=who.admin)
    if who.admin:
        return tools
    plan_tools = catalog.BY_NAME["get_plan_tools"]
    tools = tools if plan_tools in tools else [plan_tools, *tools]
    return [t for t in tools if t.reads] if who.read_only else tools


def _describe(t: Tool, openapi: dict) -> dict:
    description = t.description
    if t.features:
        description += f" Requiere en el plan: {' o '.join(t.features)} (ver get_plan_tools)."
    annotations = {"title": t.title, "readOnlyHint": t.reads, "openWorldHint": False}
    if not t.reads:
        annotations["destructiveHint"] = t.destructive
        annotations["idempotentHint"] = t.method in ("PUT", "DELETE")
    return {"name": t.name, "title": t.title, "description": description, "inputSchema": t.input_schema(openapi),
            "annotations": annotations}


def _ok(data: Any) -> dict:
    structured = data if isinstance(data, dict) else {"items": data}
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
            "structuredContent": structured}


def _fail(code: str, message: str, **extra) -> dict:
    body = {"code": code, "message": message, **extra}
    return {"content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}],
            "structuredContent": body, "isError": True}


def _upgrade_url() -> str:
    origin = settings.app_origins.split(",")[0].strip().rstrip("/")
    return origin + UPGRADE_PATH


def _api_fail(r: httpx.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    detail = body.get("detail") if isinstance(body, dict) else None
    code = (body.get("code") if isinstance(body, dict) else None) or f"http_{r.status_code}"
    if isinstance(detail, list):   # 422 de validación: "campo: motivo"
        detail = "; ".join(f"{e.get('loc', ['?'])[-1]}: {e.get('msg', '')}" for e in detail if isinstance(e, dict))
    message = detail if isinstance(detail, str) and detail else f"La API respondió {r.status_code}"
    extra = {"http_status": r.status_code}
    if code.endswith("_not_in_plan"):
        extra["upgrade_url"] = _upgrade_url()
    return _fail(code, message, **extra)


async def _plan(ctx: Ctx) -> dict:
    r = await ctx.api("GET", "/plan/features")
    r.raise_for_status()
    return r.json()


def _blocked(tool: Tool, plan: dict) -> str | None:
    """El motivo por el que el plan no deja usar la herramienta, o None."""
    if not tool.features:
        return None
    features = plan["features"]
    if any(features.get(f, {}).get("enabled") for f in tool.features):
        return None
    return features.get(tool.features[0], {}).get("reason") or "Tu plan no incluye esta función."


async def _call(ctx: Ctx, tool: Tool, args: dict, openapi: dict) -> dict:
    allowed = tool.arg_names(openapi)
    unknown = set(args) - allowed
    missing = [p for p in tool.required if args.get(p) in (None, "")]
    if unknown or missing:
        what = "; ".join(filter(None, [unknown and f"desconocidos: {', '.join(sorted(unknown))}",
                                       missing and f"faltan: {', '.join(missing)}"]))
        return _fail("invalid_arguments", f"Argumentos inválidos ({what})")
    if tool.name == "get_plan_tools":
        return await _plan_tools(ctx)
    if tool.session and ctx.who.kind == "api_key":
        return _fail("needs_oauth", "Esta herramienta necesita conectar el agente iniciando sesión (OAuth), no con "
                                    "una API key.")
    if tool.api_key_only and ctx.who.kind != "api_key":
        return _fail("needs_api_key", "Esta herramienta usa la API de inferencia, que funciona con una API key: "
                                      "conectá el agente con una key que tenga los alcances mcp y stt o tts.")
    if tool.features:
        plan = await _plan(ctx)
        reason = _blocked(tool, plan)
        if reason:
            return _fail("feature_not_in_plan", f"Tu plan {plan['tier_name']} no incluye esta función.",
                         feature=tool.features[0], reason=reason, upgrade_url=_upgrade_url())
    path, rest = tool.path, dict(args)
    for name in list(rest):
        if "{" + name + "}" in path:
            path = path.replace("{" + name + "}", quote(str(rest.pop(name)), safe=""))
    if tool.upload:
        try:
            data = base64.b64decode(rest.pop(tool.upload), validate=True)
        except (binascii.Error, ValueError):
            return _fail("invalid_arguments", f"`{tool.upload}` no es base64 válido")
        kwargs = {"files": {"file": (rest.pop("filename", "audio"), data)},
                  "data": {k: v for k, v in rest.items() if v is not None}}
    elif tool.query_args:
        kwargs = {"params": rest}
    elif tool.body_arg:
        kwargs = {"json": rest.get(tool.body_arg)}
    else:
        kwargs = {"json": rest} if tool.body else {}
    r = await ctx.api(tool.method, path, **kwargs)
    if r.status_code >= 400:
        return _api_fail(r)
    if tool.audio:
        if len(r.content) > MAX_AUDIO_BYTES:
            return _fail("audio_too_large", f"El audio pesa más de {MAX_AUDIO_BYTES // 1024 // 1024} MB")
        return {"content": [{"type": "audio", "data": base64.b64encode(r.content).decode(),
                             "mimeType": r.headers.get("content-type", "audio/wav")}]}
    if tool.text:
        return {"content": [{"type": "text", "text": r.content.decode("utf-8-sig")}]}
    return _ok(r.json() if r.content else {})


async def _plan_tools(ctx: Ctx) -> dict:
    """Qué herramientas puede usar el agente con el plan del cliente (docs/MCP_PLAN.md, 6.1)."""
    plan = await _plan(ctx)
    available, unavailable, needs_oauth, needs_api_key = [], [], [], []
    for t in catalog.select("all"):
        if ctx.who.read_only and not t.reads:
            continue
        reason = _blocked(t, plan)
        if t.session and ctx.who.kind == "api_key":
            needs_oauth.append(t.name)
        elif t.api_key_only and ctx.who.kind != "api_key":
            needs_api_key.append(t.name)
        elif reason is None:
            available.append(t.name)
        else:
            unavailable.append({"name": t.name, "toolset": t.toolset, "feature": t.features[0], "reason": reason})
    r = await ctx.api("GET", "/clients/{client_id}/usage")
    return _ok({"plan": plan["tier_name"], "free": plan["free"],
                "tools": {"available": available, "unavailable": unavailable, "needs_oauth": needs_oauth,
                          "needs_api_key": needs_api_key},
                "toolsets": {k: v for k, v in catalog.TOOLSETS.items() if k != "admin"}, "usage": r.json() if r.status_code == 200 else None,
                "upgrade_url": _upgrade_url()})
