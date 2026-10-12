"""Pedidos de Atentina a una app (contrato v1, docs/APPS_PLAN.md seccion 9).

MCP minimo, sin el SDK: JSON-RPC por POST a /mcp (Streamable HTTP). Las apps de la plantilla
corren sin estado y responden JSON; igual se manda initialize y se acepta una respuesta SSE, para
hablar con cualquier servidor MCP. Todo pedido lleva el APP_TOKEN y quien actua (X-Atentina-Actor).
"""
import itertools
import json
from typing import Any

import httpx

from ..config import settings

PROTOCOL_VERSION = "2025-06-18"
_ids = itertools.count(1)


class AppError(Exception):
    """La app no responde, responde mal o no cumple el contrato. El mensaje no lleva datos."""


def _headers(token: str, actor: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if actor:
        headers["X-Atentina-Actor"] = actor
    return headers


def _check(response: httpx.Response, what: str) -> httpx.Response:
    if response.status_code == 401:
        raise AppError(f"{what}: la app rechazo el token (401)")
    if response.status_code >= 400:
        raise AppError(f"{what}: HTTP {response.status_code}")
    return response


def get_json(base_url: str, token: str, path: str, timeout: float | None = None) -> dict:
    """GET sincronico (registro y salud, desde la API)."""
    try:
        r = httpx.get(base_url.rstrip("/") + path, headers=_headers(token, "admin"),
                      timeout=timeout or settings.apps_http_timeout)
    except httpx.HTTPError as e:
        raise AppError(f"{path}: no responde ({type(e).__name__})") from None
    _check(r, path)
    try:
        return r.json()
    except ValueError:
        raise AppError(f"{path}: la respuesta no es JSON") from None


def _rpc_result(response: httpx.Response, request_id: int) -> dict:
    """Respuesta JSON o SSE (text/event-stream: la primera respuesta con ese id)."""
    kind = response.headers.get("content-type", "")
    if kind.startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                try:
                    message = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if message.get("id") == request_id:
                    return message
        raise AppError("mcp: la respuesta SSE no trae el resultado")
    try:
        return response.json()
    except ValueError:
        raise AppError("mcp: la respuesta no es JSON") from None


class McpSession:
    """Una sesion MCP corta (initialize + pedidos) contra una app."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, token: str, actor: str | None):
        self.client = client
        self.url = base_url.rstrip("/") + "/mcp"
        self.headers = {**_headers(token, actor), "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json"}

    async def _post(self, payload: dict) -> httpx.Response:
        try:
            r = await self.client.post(self.url, json=payload, headers=self.headers)
        except httpx.HTTPError as e:
            raise AppError(f"mcp: no responde ({type(e).__name__})") from None
        return _check(r, "mcp")

    async def request(self, method: str, params: dict | None = None) -> dict:
        request_id = next(_ids)
        r = await self._post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        message = _rpc_result(r, request_id)
        if "error" in message:
            raise AppError(f"mcp {method}: {message['error'].get('message', 'error')}")
        return message.get("result") or {}

    async def initialize(self) -> None:
        r = await self._post({"jsonrpc": "2.0", "id": next(_ids), "method": "initialize", "params": {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "atentina", "version": "1"}}})
        if session_id := r.headers.get("mcp-session-id"):
            self.headers["Mcp-Session-Id"] = session_id
        await self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})


async def call_tool(base_url: str, token: str, name: str, arguments: dict, actor: str) -> dict:
    """Llama una herramienta. Devuelve {"ok": bool, "result": <JSON o texto>}: un error de
    negocio (isError) vuelve con ok=False y el texto de la app; una falla de la app, AppError."""
    async with httpx.AsyncClient(timeout=settings.apps_http_timeout) as client:
        session = McpSession(client, base_url, token, actor)
        await session.initialize()
        result = await session.request("tools/call", {"name": name, "arguments": arguments})
    return {"ok": not result.get("isError", False), "result": tool_content(result)}


def tool_content(result: dict) -> Any:
    """structuredContent si viene; si no, el texto (JSON si se puede parsear)."""
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    text = "\n".join(c.get("text", "") for c in result.get("content") or [] if c.get("type") == "text")
    try:
        return json.loads(text)
    except ValueError:
        return text


async def post_json(base_url: str, token: str, path: str, payload: dict, actor: str = "atentina") -> dict:
    """POST a la app (outbox y jobs, contrato v1.1)."""
    async with httpx.AsyncClient(timeout=settings.apps_http_timeout) as client:
        try:
            r = await client.post(base_url.rstrip("/") + path, json=payload, headers=_headers(token, actor))
        except httpx.HTTPError as e:
            raise AppError(f"{path}: no responde ({type(e).__name__})") from None
    _check(r, path)
    try:
        return r.json()
    except ValueError:
        return {}


async def get_view(base_url: str, token: str, path: str, query: str, actor: str, prefix: str) -> httpx.Response:
    """GET de una vista o un estatico, para el gateway (respuesta entera: son paginas chicas)."""
    url = base_url.rstrip("/") + path + (f"?{query}" if query else "")
    async with httpx.AsyncClient(timeout=settings.apps_http_timeout) as client:
        try:
            return await client.get(url, headers={**_headers(token, actor), "X-Forwarded-Prefix": prefix})
        except httpx.HTTPError as e:
            raise AppError(f"vista: no responde ({type(e).__name__})") from None
