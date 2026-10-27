"""Ejecucion de una herramienta del cliente (docs/TOOLS_PLAN.md, 4 y 5): arma el pedido HTTP o le pasa
la funcion al sandbox (tools-runner), y devuelve lo que ve el modelo, con los secretos tachados.

Seguridad de red (SSRF): el host se resuelve y se conecta a una IP ya validada (publica), en el mismo
paso, asi un DNS que cambia entre el chequeo y la conexion no burla el filtro (backend de red propio en un pool
de httpcore, su API publica). No se siguen redirects ni se usan proxies del entorno. PRIVATE_HOSTS deja pasar
hosts internos: solo lo setean los tests y el e2e, en codigo (no hay configuracion para habilitarlo).
"""
import asyncio
import base64
import datetime
import hashlib
import hmac
import ipaddress
import json
import logging
import re
import socket
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlencode, urlparse, urlunparse

import httpcore
import httpx

from ..config import settings
from . import schema as S

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 1_000_000
ERROR_BODY_CHARS = 500
USER_AGENT = "Atentina-Tools/1"


@dataclass
class ToolContext:
    """Lo que la herramienta puede leer de la conversacion (templates y `call` del codigo)."""
    conversation_id: str = ""
    channel: str = "voice"
    mode: str = ""
    from_: str | None = None
    to: str | None = None
    agent_slug: str = ""
    agent_version: int | None = None
    fields: dict[str, Any] = field(default_factory=dict)
    contact: dict[str, Any] = field(default_factory=dict)
    vars: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)
    timezone: str = "America/Argentina/Buenos_Aires"

    def call(self) -> dict:
        return {"id": self.conversation_id, "channel": self.channel, "mode": self.mode, "from": self.from_,
                "to": self.to, "agent": self.agent_slug}


@dataclass
class ToolSpec:
    """Una herramienta lista para correr: la definicion validada y lo que va en la traza."""
    slug: str
    type: str
    revision: int
    tool: S.HttpTool | S.CodeTool
    tool_id: str | None = None          # tools.id (para tool_runs); None en la prueba sin guardar

    @property
    def messages(self) -> S.Messages:
        return self.tool.messages


@dataclass
class ToolResult:
    ok: bool
    status: int | None = None
    data: Any = None
    error: str | None = None
    ms: int = 0
    request: dict | None = None          # lo que se mando (http), con los secretos tachados
    logs: list[str] = field(default_factory=list)
    llm: str = ""                         # lo que recibe el modelo
    assigned: dict[str, Any] = field(default_factory=dict)

    def trace(self) -> dict:
        out = {"ok": self.ok, "status": self.status, "ms": self.ms}
        if self.request:
            out["request"] = self.request
        if self.logs:
            out["logs"] = self.logs
        return out


class ToolFailure(Exception):
    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ---------- templates ----------

def _lookup(ctx: ToolContext, ns: str, key: str | None) -> Any:
    if ns == "secrets":
        if key not in ctx.secrets:
            raise ToolFailure("missing_secret", f"Falta el secreto {key} (cargalo en Secretos del cliente o del agente)")
        return ctx.secrets[key]
    if ns == "call":
        return ctx.call().get(key)
    if ns == "agent":
        return ctx.agent_slug if key == "slug" else ctx.agent_version
    if ns in ("fields", "contact", "vars"):
        return getattr(ctx, ns).get(key)
    now = datetime.datetime.now(datetime.UTC)
    try:
        from zoneinfo import ZoneInfo
        now = now.astimezone(ZoneInfo(ctx.timezone))
    except Exception:
        pass
    return now.date().isoformat() if ns == "today" else now.isoformat(timespec="seconds")


def render(text: str, ctx: ToolContext) -> str:
    def one(m: re.Match) -> str:
        value = _lookup(ctx, m.group(1), m.group(2))
        if value is None:
            return ""
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return S.TEMPLATE_RE.sub(one, text)


def _fixed(value: Any, ctx: ToolContext) -> Any:
    if isinstance(value, list):
        return [_fixed(v, ctx) for v in value]
    return render(value, ctx) if isinstance(value, str) else value


# ---------- redaccion ----------

def secret_forms(values: list[str]) -> list[str]:
    """Las formas en que un secreto puede aparecer en el pedido o en la respuesta."""
    out = set()
    for v in values:
        if len(v) < 4:
            continue
        out |= {v, quote(v, safe=""), base64.b64encode(v.encode()).decode()}
    return sorted(out, key=len, reverse=True)


def redact(value: Any, forms: list[str], names: dict[str, str]) -> Any:
    if isinstance(value, str):
        for f in forms:
            if f in value:
                value = value.replace(f, f"[secreto:{names.get(f, '?')}]")
        return value
    if isinstance(value, list):
        return [redact(v, forms, names) for v in value]
    if isinstance(value, dict):
        return {k: redact(v, forms, names) for k, v in value.items()}
    return value


class Redactor:
    def __init__(self, secrets: dict[str, str], extra: dict[str, str] | None = None):
        self.names: dict[str, str] = {}
        for name, value in {**secrets, **(extra or {})}.items():
            for f in secret_forms([value]):
                self.names[f] = name
        self.forms = sorted(self.names, key=len, reverse=True)

    def add(self, name: str, value: str) -> None:
        for f in secret_forms([value]):
            self.names[f] = name
        self.forms = sorted(self.names, key=len, reverse=True)

    def __call__(self, value: Any) -> Any:
        return redact(value, self.forms, self.names) if self.forms else value


# ---------- respuesta ----------

_STEP_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def get_path(data: Any, path: str) -> Any:
    node = data
    for key, index in _STEP_RE.findall(path):
        if index:
            if not isinstance(node, list) or int(index) >= len(node):
                return None
            node = node[int(index)]
        else:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
    return node


def _drop_path(data: Any, path: str) -> None:
    steps = _STEP_RE.findall(path)
    node = data
    for key, index in steps[:-1]:
        node = (node[int(index)] if index and isinstance(node, list) and int(index) < len(node)
                else node.get(key) if not index and isinstance(node, dict) else None)
        if node is None:
            return
    key, index = steps[-1]
    if index and isinstance(node, list) and int(index) < len(node):
        node[int(index)] = None
    elif not index and isinstance(node, dict):
        node.pop(key, None)


def pick(data: Any, paths: list[str]) -> Any:
    if not paths:
        return data
    return {p: get_path(data, p) for p in paths}


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + " […]"


def finish(spec: ToolSpec, result: ToolResult, ctx: ToolContext, redactor: Redactor) -> ToolResult:
    """Asignaciones, pick, recorte y redaccion: lo que ve el modelo."""
    tool = spec.tool
    data = result.data
    if result.ok:
        for a in tool.assign:
            value = get_path(data, a.path)
            if value is not None:
                result.assigned[a.var] = value
                ctx.vars[a.var] = value
        if any(a.hide for a in tool.assign):
            data = json.loads(json.dumps(data))
            for a in tool.assign:
                if a.hide:
                    _drop_path(data, a.path)
        data = pick(data, tool.response.pick)
        out = {"ok": True, "status": result.status, "data": data} if result.status else {"ok": True, "data": data}
    else:
        out = {"ok": False, **({"status": result.status} if result.status else {}), "error": result.error}
    result.data = redactor(result.data)
    result.error = redactor(result.error)
    result.logs = [redactor(line) for line in result.logs]
    result.llm = clip(redactor(json.dumps(out, ensure_ascii=False, default=str)), tool.response.max_chars)
    return result


# ---------- red ----------

# Hosts internos permitidos (http y cualquier puerto): vacio en la app; los tests y el e2e lo cargan.
PRIVATE_HOSTS: set[str] = set()


def private_hosts() -> set[str]:
    return PRIVATE_HOSTS


def _public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


class SafeBackend(httpcore.AsyncNetworkBackend):
    """Resuelve y conecta a una IP publica (o a un host de PRIVATE_HOSTS)."""

    def __init__(self):
        self.inner = httpcore.AnyIOBackend()

    async def connect_tcp(self, host: str, port: int, timeout: float | None = None,
                          local_address: str | None = None, socket_options=None):
        allowed = host.lower() in private_hosts()
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError:
            raise httpcore.ConnectError(f"El host {host} no resuelve") from None
        ips = [info[4][0] for info in infos]
        if not allowed and (not ips or not all(_public(ip) for ip in ips)):
            raise BlockedAddress(f"{host} apunta a una red privada o interna")
        return await self.inner.connect_tcp(ips[0], port, timeout=timeout, local_address=local_address,
                                            socket_options=socket_options)

    async def connect_unix_socket(self, *args, **kwargs):
        raise BlockedAddress("sin sockets unix")

    async def sleep(self, seconds: float) -> None:
        await self.inner.sleep(seconds)


class BlockedAddress(Exception):
    """No es de httpcore: llega tal cual."""


class HttpTimeout(Exception):
    pass


class HttpError(Exception):
    pass


@dataclass
class Response:
    status: int
    data: Any           # JSON si se pudo leer, si no texto
    cut: bool           # se corto en MAX_BODY_BYTES


class SafeHttp:
    """Cliente HTTP de las herramientas: pool de httpcore con SafeBackend, sin redirects ni proxies, con tope de
    tiempo total y de tamaño de la respuesta."""

    def __init__(self, timeout_s: float):
        self.timeout_s = timeout_s
        self.pool = httpcore.AsyncConnectionPool(network_backend=SafeBackend(), retries=0)

    async def __aenter__(self) -> "SafeHttp":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.pool.aclose()

    async def request(self, method: str, url: str, headers: dict[str, str], body: bytes | None) -> Response:
        t = self.timeout_s
        try:
            async with asyncio.timeout(t):
                async with self.pool.stream(method, url, headers=list(headers.items()), content=body,
                                            extensions={"timeout": {"connect": t, "read": t, "write": t,
                                                                    "pool": t}}) as resp:
                    data, cut = await _read(resp)
                    return Response(resp.status, data, cut)
        except (TimeoutError, httpcore.TimeoutException):
            raise HttpTimeout() from None
        except (httpcore.NetworkError, httpcore.ProtocolError, httpcore.UnsupportedProtocol) as e:
            raise HttpError(type(e).__name__) from None


def check_destination(url: str) -> None:
    """https, o http solo para un host de PRIVATE_HOSTS; puerto 443/8443 (o el de esos hosts)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    internal = host in private_hosts()
    if parsed.scheme != "https" and not internal:
        raise ToolFailure("invalid_url", "La URL tiene que ser https")
    if not internal and parsed.port not in (None, 443, 8443):
        raise ToolFailure("invalid_url", "Puerto no permitido (443 u 8443)")


# ---------- OAuth2 client credentials ----------

_TOKENS: dict[str, tuple[str, float]] = {}


async def oauth_token(auth: S.Auth, ctx: ToolContext, client: SafeHttp, refresh: bool = False) -> str:
    secret = _lookup(ctx, "secrets", auth.secret)
    client_id = render(auth.client_id or "", ctx)
    key = hashlib.sha256(json.dumps([auth.token_url, client_id, secret, auth.scope, auth.audience]).encode()).hexdigest()
    cached = _TOKENS.get(key)
    if cached and not refresh and cached[1] > time.time():
        return cached[0]
    check_destination(auth.token_url)
    data = {"grant_type": "client_credentials"}
    if auth.scope:
        data["scope"] = auth.scope
    if auth.audience:
        data["audience"] = auth.audience
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json",
               "Content-Type": "application/x-www-form-urlencoded"}
    if auth.client_auth == "basic":
        headers["Authorization"] = "Basic " + base64.b64encode(f"{quote(client_id)}:{quote(secret)}".encode()).decode()
    else:
        data |= {"client_id": client_id, "client_secret": secret}
    try:
        resp = await client.request("POST", auth.token_url, headers, urlencode(data).encode())
    except HttpTimeout:
        raise ToolFailure("auth_failed", "El servidor de tokens no respondió a tiempo") from None
    except BlockedAddress as e:
        raise ToolFailure("blocked_address", str(e)) from None
    except HttpError as e:
        raise ToolFailure("auth_failed", f"No se pudo pedir el token: {e}") from None
    if resp.status != 200:
        raise ToolFailure("auth_failed", f"El servidor de tokens respondió {resp.status}", resp.status)
    try:
        body = resp.data
        token = body["access_token"]
    except (KeyError, TypeError):
        raise ToolFailure("auth_failed", "El servidor de tokens no devolvió access_token") from None
    ttl = float(body.get("expires_in") or 3600)
    _TOKENS[key] = (token, time.time() + max(ttl - 60, 30))
    return token


# ---------- pedido HTTP ----------

def sign(secret: str, body: bytes, now: int | None = None) -> str:
    """X-Atentina-Signature: t=<unix>,v1=<hex de HMAC-SHA256("<t>.<cuerpo>")> (formato de Stripe)."""
    t = int(time.time()) if now is None else now
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v1={mac}"


@dataclass
class Built:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


async def build_request(tool: S.HttpTool, args: dict, ctx: ToolContext, client: SafeHttp,
                        call_id: str, refresh_token: bool = False) -> Built:
    h = tool.http
    url = render(h.url, ctx)
    for name, p in h.path.items():
        value = args.get(name) if p.by_llm else _fixed(p.value, ctx)
        if value in (None, ""):
            raise ToolFailure("missing_variable", f"Falta el parámetro {name} de la ruta")
        url = url.replace("{" + name + "}", quote(str(value), safe=""))
    parsed = urlparse(url)
    query: list[tuple[str, str]] = []
    for name, p in h.query.items():
        value = args.get(name) if p.by_llm else _fixed(p.value, ctx)
        if value is None or value == "":
            if p.required and p.by_llm is False:
                raise ToolFailure("missing_variable", f"Falta el valor de {name}")
            continue
        for v in value if isinstance(value, list) else [value]:
            query.append((name, json.dumps(v) if isinstance(v, bool) else str(v)))
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/plain;q=0.9, */*;q=0.5",
               "X-Atentina-Conversation-Id": ctx.conversation_id, "X-Atentina-Tool": ""}
    for name, value in h.headers.items():
        headers[name] = render(value, ctx)
    auth = h.auth
    if auth.type == "credential":
        raise ToolFailure("missing_credential", f"No existe la credencial {auth.credential}")
    if auth.type == "bearer":
        prefix = "Bearer " if auth.prefix is None else auth.prefix
        headers[auth.header or "Authorization"] = prefix + _lookup(ctx, "secrets", auth.secret)
    elif auth.type == "api_key":
        key = _lookup(ctx, "secrets", auth.secret)
        if (auth.in_ or "header") == "query":
            query.append((auth.name, key))
        else:
            headers[auth.name] = key
    elif auth.type == "basic":
        user = render(auth.username or "", ctx)
        password = _lookup(ctx, "secrets", auth.secret)
        headers["Authorization"] = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
    elif auth.type == "oauth2_client_credentials":
        headers["Authorization"] = "Bearer " + await oauth_token(auth, ctx, client, refresh_token)
    if query:
        existing = parsed.query + "&" if parsed.query else ""
        parsed = parsed._replace(query=existing + urlencode(query))
    url = urlunparse(parsed)
    body: bytes | None = None
    if h.body is not None and h.method not in ("GET", "DELETE"):
        payload: dict[str, Any] = {}
        for name, prop in (h.body.get("properties") or {}).items():
            if "value" in prop:
                payload[name] = _fixed(prop["value"], ctx)
            elif name in args:
                payload[name] = args[name]
        if h.content_type == "application/json":
            body = json.dumps(payload, ensure_ascii=False).encode()
        else:
            body = urlencode({k: json.dumps(v) if isinstance(v, bool) else v for k, v in payload.items()
                              if v is not None}).encode()
        headers["Content-Type"] = h.content_type
    if h.method != "GET":
        headers["Idempotency-Key"] = f"{ctx.conversation_id or 'prueba'}:{call_id}"
    if h.sign:
        headers["X-Atentina-Signature"] = sign(_lookup(ctx, "secrets", S.SIGNING_SECRET), body or b"")
    return Built(h.method, url, headers, body)


def _header(resp: httpcore.Response, name: str) -> str:
    wanted = name.lower().encode()
    return next((v.decode("latin-1") for k, v in resp.headers if k.lower() == wanted), "")


async def _read(resp: httpcore.Response) -> tuple[Any, bool]:
    """El cuerpo (JSON si se puede) y si se corto por el tope."""
    chunks, size, cut = [], 0, False
    async for chunk in resp.aiter_stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            chunks.append(chunk[: len(chunk) - (size - MAX_BODY_BYTES)])
            cut = True
            break
        chunks.append(chunk)
    content_type = _header(resp, "content-type")
    charset = re.search(r"charset=([\w-]+)", content_type)
    raw = b"".join(chunks).decode(charset.group(1) if charset else "utf-8", errors="replace")
    if "json" in content_type and not cut:
        try:
            return json.loads(raw) if raw.strip() else None, cut
        except ValueError:
            pass
    return raw, cut


RETRY_STATUS = {429, 500, 502, 503, 504}


async def run_http(spec: ToolSpec, args: dict, ctx: ToolContext, call_id: str, redactor: Redactor) -> ToolResult:
    tool: S.HttpTool = spec.tool
    h = tool.http
    # Todo lo que no es GET lleva Idempotency-Key: se puede reintentar.
    attempts = 1 + h.retries
    async with SafeHttp(h.timeout_ms / 1000) as client:
        refreshed = False
        attempt = 0
        while True:
            attempt += 1
            built = await build_request(tool, args, ctx, client, call_id, refresh_token=refreshed)
            built.headers["X-Atentina-Tool"] = spec.slug
            check_destination(built.url)
            if built.headers.get("Authorization", "").startswith("Bearer ") and h.auth.type == "oauth2_client_credentials":
                redactor.add("oauth_token", built.headers["Authorization"][7:])
            request_log = redactor({"method": built.method, "url": built.url, "headers": built.headers,
                                    "body": built.body.decode(errors="replace") if built.body else None})
            try:
                resp = await client.request(built.method, built.url, built.headers, built.body)
                data, cut, status = resp.data, resp.cut, resp.status
            except BlockedAddress as e:
                raise ToolFailure("blocked_address", str(e)) from None
            except HttpTimeout:
                if attempt < attempts:
                    await asyncio.sleep(0.3 * 2 ** (attempt - 1))
                    continue
                return ToolResult(ok=False, error="timeout", request=request_log)
            except HttpError as e:
                if attempt < attempts:
                    await asyncio.sleep(0.3 * 2 ** (attempt - 1))
                    continue
                return ToolResult(ok=False, error=f"error de conexión: {e}", request=request_log)
            if status == 401 and h.auth.type == "oauth2_client_credentials" and not refreshed:
                refreshed = True
                continue
            if status in RETRY_STATUS and attempt < attempts:
                await asyncio.sleep(0.3 * 2 ** (attempt - 1))
                continue
            break
    if 300 <= status < 400:
        return ToolResult(ok=False, status=status, error="la API respondió con una redirección (no se siguen)",
                          request=request_log)
    if status >= 400:
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        return ToolResult(ok=False, status=status, error=clip(text or f"HTTP {status}", ERROR_BODY_CHARS),
                          request=request_log)
    if cut:
        data = clip(data, tool.response.max_chars)
    return ToolResult(ok=True, status=status, data=data, request=request_log)


# ---------- codigo ----------

async def run_code(spec: ToolSpec, args: dict, ctx: ToolContext, redactor: Redactor) -> ToolResult:
    tool: S.CodeTool = spec.tool
    if not settings.tools_runner_url:
        raise ToolFailure("runner_unavailable", "Las herramientas de código no están disponibles en este servidor")
    secrets = {name: _lookup(ctx, "secrets", name) for name in tool.secrets}
    payload = {"code": tool.code, "args": args, "secrets": secrets, "call": ctx.call(), "vars": ctx.vars,
               "allowed_hosts": tool.allowed_hosts, "timeout_ms": tool.timeout_ms}
    headers = {"Authorization": f"Bearer {settings.tools_runner_token}"}
    try:
        async with httpx.AsyncClient(timeout=tool.timeout_ms / 1000 + 5, trust_env=False) as client:
            resp = await client.post(settings.tools_runner_url.rstrip("/") + "/run", json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise ToolFailure("runner_unavailable", f"El sandbox de código no responde ({type(e).__name__})") from None
    if resp.status_code != 200:
        raise ToolFailure("runner_unavailable", f"El sandbox de código respondió {resp.status_code}")
    out = resp.json()
    logs = [str(line) for line in out.get("logs") or []][:200]
    if not out.get("ok"):
        return ToolResult(ok=False, error=str(out.get("error") or "error en la función"), logs=logs)
    value = out.get("result")
    if isinstance(value, dict) and value.get("ok") is False:
        return ToolResult(ok=False, error=str(value.get("error") or "la función devolvió ok: false"), logs=logs,
                          data=value)
    return ToolResult(ok=True, data=value, logs=logs)


# ---------- entrada ----------

async def run(spec: ToolSpec, args: Any, ctx: ToolContext, call_id: str | None = None) -> ToolResult:
    """Valida los argumentos, ejecuta y arma lo que ve el modelo. No lanza: un error vuelve como ok=False."""
    started = time.perf_counter()
    redactor = Redactor(ctx.secrets)
    call_id = call_id or uuid.uuid4().hex[:12]
    if (problem := S.validate_args(spec.tool, args)) is not None:
        result = ToolResult(ok=False, error=f"argumentos inválidos: {problem}")
    else:
        try:
            if spec.type == "http":
                result = await run_http(spec, args, ctx, call_id, redactor)
            else:
                result = await run_code(spec, args, ctx, redactor)
        except ToolFailure as e:
            result = ToolResult(ok=False, status=e.status, error=e.message)
        except Exception:
            logger.exception("tools: fallo %s", spec.slug)
            result = ToolResult(ok=False, error="error interno al ejecutar la herramienta")
    result.ms = round((time.perf_counter() - started) * 1000)
    return finish(spec, result, ctx, redactor)
