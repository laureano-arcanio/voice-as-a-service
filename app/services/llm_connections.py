"""Conexiones de LLM de un cliente (BYOK, docs/BYOK_LLM_PLAN.md): alta, rotacion de la key, prueba
y baja. La key se guarda cifrada (app/whatsapp/crypto.py) y no se devuelve nunca: solo los ultimos 4."""
import asyncio
import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

import anthropic
import openai
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..llm.anthropic_client import ANTHROPIC_URL, AnthropicClient
from ..llm.client import JSON_MODES, LLMClient
from ..llm.external import end_call_tool
from ..llm.resolver import OPENROUTER_HEADERS, OPENROUTER_URL
from ..models import Agent, LlmConnection
from ..whatsapp import crypto
from .errors import Conflict, Invalid, NotFound

KINDS = ("openai_compatible", "openrouter", "anthropic")

# Errores de cualquiera de los dos SDK, por lo que significan.
_AUTH = (openai.AuthenticationError, openai.PermissionDeniedError,
         anthropic.AuthenticationError, anthropic.PermissionDeniedError)
_NOT_FOUND = (openai.NotFoundError, anthropic.NotFoundError)
_RATE = (openai.RateLimitError, anthropic.RateLimitError)
_NETWORK = (openai.APIConnectionError, openai.APITimeoutError,
            anthropic.APIConnectionError, anthropic.APITimeoutError)
_BAD_REQUEST = (openai.BadRequestError, anthropic.BadRequestError, ValueError)
TEST_TIMEOUT = 20
_TEST_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
                "additionalProperties": False}


def check_base_url(url: str, allow_private: bool) -> str:
    """https y un host publico. Los admin pueden apuntar a un servidor propio (http o red interna)."""
    url = url.strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise Invalid("base_url: tiene que ser una URL http(s) completa", "invalid_base_url")
    if parsed.username or parsed.password:
        raise Invalid("base_url: sin usuario ni clave en la URL", "invalid_base_url")
    if allow_private:
        return url
    if parsed.scheme != "https":
        raise Invalid("base_url: tiene que ser https", "invalid_base_url")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise Invalid("base_url: el host no resuelve", "invalid_base_url") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise Invalid("base_url: apunta a una red privada o interna", "invalid_base_url")
    return url


def active(s: Session, client_id: str) -> list[LlmConnection]:
    return list(s.scalars(select(LlmConnection).where(
        LlmConnection.client_id == client_id, LlmConnection.revoked_at.is_(None))
        .order_by(LlmConnection.created_at)))


def get(s: Session, client_id: str, connection_id: str) -> LlmConnection:
    row = s.get(LlmConnection, connection_id)
    if row is None or row.client_id != client_id or row.revoked_at is not None:
        raise NotFound("Conexion inexistente")
    return row


def used_by(s: Session, client_id: str) -> dict[str, int]:
    """Agentes vigentes (no archivados) del cliente que usan cada conexion."""
    count: dict[str, int] = {}
    for definition in s.scalars(select(Agent.definition).where(
            Agent.client_id == client_id, Agent.archived_at.is_(None))):
        ids = {st.get("connection") for st in (definition.get("llm") or {}).get("stages") or []}
        for connection_id in ids - {None}:
            count[connection_id] = count.get(connection_id, 0) + 1
    return count


def _check_name(s: Session, client_id: str, name: str, ignore: str | None = None) -> str:
    name = name.strip()
    if not name:
        raise Invalid("name: no puede estar vacio")
    if any(c.name.lower() == name.lower() and c.id != ignore for c in active(s, client_id)):
        raise Conflict(f"Ya hay una conexion {name!r}", "connection_name_taken")
    return name


def _normalize(kind: str, base_url: str | None, allow_private: bool) -> str:
    if kind not in KINDS:
        raise Invalid(f"kind: {', '.join(KINDS)}", "invalid_kind")
    if kind == "openrouter":
        return OPENROUTER_URL
    if kind == "anthropic":
        return ANTHROPIC_URL
    if not base_url:
        raise Invalid("base_url: obligatoria en una conexion OpenAI compatible", "invalid_base_url")
    return check_base_url(base_url, allow_private)


def create(s: Session, client_id: str, *, name: str, kind: str, base_url: str | None, api_key: str,
           default_model: str, user_id: str | None, allow_private: bool) -> LlmConnection:
    api_key = api_key.strip()
    if not api_key:
        raise Invalid("api_key: obligatoria")
    row = LlmConnection(
        client_id=client_id, name=_check_name(s, client_id, name), kind=kind,
        base_url=_normalize(kind, base_url, allow_private), api_key_enc=crypto.encrypt(api_key),
        last4=api_key[-4:], default_model=default_model.strip(), created_by=user_id)
    s.add(row)
    s.flush()
    return row


def update(s: Session, row: LlmConnection, *, name: str | None, base_url: str | None, api_key: str | None,
           default_model: str | None, allow_private: bool) -> LlmConnection:
    if name is not None:
        row.name = _check_name(s, row.client_id, name, ignore=row.id)
    if base_url is not None and row.kind != "openrouter":
        row.base_url = _normalize(row.kind, base_url, allow_private)
    if default_model is not None:
        row.default_model = default_model.strip()
    if api_key is not None and api_key.strip():
        row.api_key_enc = crypto.encrypt(api_key.strip())
        row.last4 = api_key.strip()[-4:]
        row.last_test_at = row.last_test_ok = None
        row.last_test_detail = ""
    s.flush()
    return row


def revoke(s: Session, row: LlmConnection) -> int:
    """Da de baja la conexion. Devuelve cuantos agentes la usaban: pasan a contestar con el servidor
    propio si tienen fallback_local (si no, el turno falla: avisarle al cliente antes)."""
    n = used_by(s, row.client_id).get(row.id, 0)
    row.revoked_at = utcnow()
    return n


def _client(row: LlmConnection, model: str, json_mode: str) -> LLMClient | AnthropicClient:
    key = crypto.decrypt(row.api_key_enc) or ""
    if row.kind == "anthropic":
        return AnthropicClient(key, model, json_mode=json_mode, timeout=TEST_TIMEOUT, base_url=row.base_url)
    headers = OPENROUTER_HEADERS if row.kind == "openrouter" else None
    return LLMClient(row.base_url, key, model, profile=row.kind, json_mode=json_mode,
                     default_headers=headers, timeout=TEST_TIMEOUT)


def _model(row: LlmConnection, model: str | None) -> str:
    model = (model or row.default_model).strip()
    if not model:
        raise Invalid("model: la conexion no tiene modelo por defecto; indicalo", "model_required")
    return model


async def _probe(row: LlmConnection, model: str) -> tuple[bool, str, str]:
    """(ok, detalle, json_mode). Prueba de mejor a peor salida guiada y se queda con la primera que anda."""
    last = ""
    for mode in JSON_MODES:
        client = _client(row, model, mode)
        started = time.perf_counter()
        try:
            raw, _ = await client.structured(
                [{"role": "user", "content": "Devolvé un objeto JSON con la clave ok en true."}],
                _TEST_SCHEMA, "test", max_tokens=32)
            if json.loads(raw).get("ok") is True:
                ms = round((time.perf_counter() - started) * 1000)
                return True, f"{mode} · {ms} ms", mode
            last = "la respuesta no cumplio el esquema"
        except _AUTH:
            return False, "clave inválida o sin permiso", row.json_mode
        except _NOT_FOUND:
            return False, f"modelo {model!r} inexistente o URL incorrecta", row.json_mode
        except _RATE:
            return False, "límite de uso del proveedor (429)", row.json_mode
        except _NETWORK as e:
            return False, f"sin conexión con el proveedor: {type(e).__name__}", row.json_mode
        except _BAD_REQUEST as e:
            last = str(e)[:160]      # este modo no lo soporta (o no devolvio JSON): se prueba el siguiente
    return False, f"no devolvió JSON válido: {last}", row.json_mode


async def _probe_external(row: LlmConnection, model: str) -> tuple[bool, str, str]:
    """El endpoint de un agente propio (motor external): un turno en streaming con la herramienta end_call,
    como los que manda la plataforma. Mide el primer texto; no toca json_mode."""
    client = _client(row, model, row.json_mode).client
    started, first = time.perf_counter(), None
    text, tools = [], 0
    try:
        stream = await client.chat.completions.create(
            model=model, stream=True, tools=[end_call_tool(["fin"])], user="atentina-test",
            messages=[{"role": "assistant", "content": "Hola, ¿en qué te puedo ayudar?"},
                      {"role": "user", "content": "Hola, es una prueba de Atentina. Respondé con una frase corta."}],
            extra_headers={"X-Atentina-Conversation-Id": "test", "X-Atentina-Channel": "voice",
                           "X-Atentina-Mode": "prueba", "X-Atentina-Turn": "1"})
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and (delta.content or delta.tool_calls) and first is None:
                first = round((time.perf_counter() - started) * 1000)
            if delta and delta.content:
                text.append(delta.content)
            tools += len(delta.tool_calls or []) if delta else 0
    except _AUTH:
        return False, "clave inválida o sin permiso", row.json_mode
    except _NOT_FOUND:
        return False, "URL incorrecta: no hay /chat/completions", row.json_mode
    except _NETWORK as e:
        return False, f"sin conexión con el endpoint: {type(e).__name__}", row.json_mode
    except (openai.OpenAIError, ValueError) as e:
        return False, f"el endpoint no respondió en streaming (SSE): {type(e).__name__}"[:255], row.json_mode
    if first is None:
        return False, "el endpoint no devolvió texto ni herramientas", row.json_mode
    said = "".join(text).strip()
    return True, f"streaming · primer texto {first} ms" + (f" · «{said[:80]}»" if said else " · end_call"), row.json_mode


def test(s: Session, row: LlmConnection, model: str | None, mode: str = "llm") -> LlmConnection:
    """Prueba la conexion (sincrono: lo llama un handler de FastAPI en el threadpool) y guarda el
    resultado y el modo de JSON que soporta. mode external: como endpoint de un agente propio."""
    if mode == "external":
        ok, detail, _ = asyncio.run(_probe_external(row, (model or row.default_model or "agent").strip()))
        row.last_test_at, row.last_test_ok, row.last_test_detail = utcnow(), ok, detail[:255]
        s.flush()
        return row
    model = _model(row, model)
    ok, detail, mode = asyncio.run(_probe(row, model))
    row.last_test_at, row.last_test_ok, row.last_test_detail = utcnow(), ok, detail[:255]
    if ok:
        row.json_mode = mode
    s.flush()
    return row


def models(row: LlmConnection) -> list[str]:
    async def run() -> list[str]:
        client = _client(row, row.default_model or "-", row.json_mode).client
        if row.kind == "anthropic":
            return sorted([m.id async for m in client.models.list(limit=100)])
        page = await client.models.list()
        return sorted(m.id for m in page.data)
    try:
        return asyncio.run(run())
    except _AUTH:
        raise Invalid("El proveedor rechazo la clave", "provider_auth") from None
    except (openai.OpenAIError, anthropic.AnthropicError) as e:
        raise Invalid(f"No se pudo leer la lista de modelos: {type(e).__name__}", "provider_error") from None
