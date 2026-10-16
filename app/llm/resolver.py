"""Que LLM atiende cada turno (docs/BYOK_LLM_PLAN.md).

`Workflow.llm` (LlmPlan) define etapas por turno del usuario; cada una usa el servidor propio o
una conexion del cliente (llm_connections: proveedor externo, su key cifrada y el modelo). El
resolver devuelve, por turno, un objeto con los cuatro metodos de LLMClient:

- sin plan, o etapa local: el LLMClient propio, tal cual;
- etapa externa: `TurnLLM`, que ante un error del proveedor contesta con el propio
  (fallback_local) salvo que ya haya empezado a hablar (en voz, repetir la frase sonaria doble).
  Despues de BREAKER_FAILS errores seguidos de una conexion, la saltea BREAKER_SECONDS.
"""
import asyncio
import logging
import threading
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..conversation.models import Generation, LlmStage, Workflow
from ..models import LlmConnection
from ..whatsapp import crypto
from . import params as llm_params
from .anthropic_client import AnthropicClient
from .client import LLMClient

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENROUTER_HEADERS = {"HTTP-Referer": "https://atentina.com.ar", "X-Title": "Atentina"}
CACHE_SECONDS = 30          # una conexion revocada o editada deja de usarse en a lo sumo esto
BREAKER_FAILS = 3
BREAKER_SECONDS = 30
EXTERNAL_TIMEOUT = 20       # un turno de voz no espera mas a un proveedor


class LlmUnavailable(Exception):
    """La conexion del turno no se puede usar y el agente no tiene fallback al servidor propio."""


@dataclass(frozen=True)
class ConnectionData:
    id: str
    client_id: str
    kind: str
    base_url: str
    api_key: str
    json_mode: str
    stamp: float            # updated_at: invalida el cliente cacheado al editar la conexion


class Breaker:
    def __init__(self) -> None:
        self._fails: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def is_open(self, key: str) -> bool:
        until = self._open_until.get(key)
        if until is None:
            return False
        if time.monotonic() >= until:
            self._open_until.pop(key, None)
            self._fails.pop(key, None)
            return False
        return True

    def failed(self, key: str) -> None:
        self._fails[key] = self._fails.get(key, 0) + 1
        if self._fails[key] >= BREAKER_FAILS:
            self._open_until[key] = time.monotonic() + BREAKER_SECONDS

    def ok(self, key: str) -> None:
        self._fails.pop(key, None)


class TurnLLM:
    """El LLM externo de un turno, con el propio de respaldo. Uno por turno: fell_back es de este turno."""

    def __init__(self, primary: LLMClient | None, local, fallback: bool, breaker: Breaker, key: str,
                 provider: str, model: str, reason: str = ""):
        self.primary, self.local, self.fallback, self.breaker, self.key = primary, local, fallback, breaker, key
        self.provider, self.model = provider, model
        self.label = f"{provider}:{model}"
        self.reason = reason
        self.fell_back = primary is None

    def info(self) -> dict:
        """Para la traza del turno (Message.llm): quien contesto de verdad."""
        if self.fell_back:
            return {"provider": "local", "model": getattr(self.local, "model", None),
                    "fallback_from": self.label, "fallback_reason": self.reason or None}
        return {"provider": self.provider, "model": self.model}

    async def _run(self, method: str, *args, **kwargs):
        fallback = getattr(self.local, method)
        if self.primary is None or (self.fallback and self.breaker.is_open(self.key)):
            self.fell_back = True
            self.reason = self.reason or "circuito abierto"
            return await fallback(*args, **kwargs)
        spoke = False
        primary_kwargs = dict(kwargs)
        if (on_message := kwargs.get("on_message")) is not None:
            def spoken(text: str) -> None:
                nonlocal spoke
                spoke = True
                on_message(text)
            primary_kwargs["on_message"] = spoken
        try:
            result = await getattr(self.primary, method)(*args, **primary_kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.breaker.failed(self.key)
            logger.warning("llm %s fallo (%s): %s", self.label, method, e)
            if not self.fallback or spoke:
                raise
            self.fell_back = True
            self.reason = type(e).__name__
            return await fallback(*args, **kwargs)
        self.breaker.ok(self.key)
        return result

    async def process_turn(self, *args, **kwargs):
        return await self._run("process_turn", *args, **kwargs)

    async def converse(self, *args, **kwargs):
        return await self._run("converse", *args, **kwargs)

    async def extract(self, *args, **kwargs):
        return await self._run("extract", *args, **kwargs)

    async def structured(self, *args, **kwargs):
        return await self._run("structured", *args, **kwargs)


def engine_defaults(engine: str) -> dict:
    """Los parametros de plataforma por motor, cuando el agente no los pisa. Voz: sin razonamiento.
    Assistant: con razonamiento y tope por paso (app/config.py)."""
    if engine == "assistant":
        return {"thinking": settings.assistant_thinking, "thinking_budget": settings.assistant_thinking_budget,
                "max_tokens": settings.assistant_max_step_tokens}
    return {"thinking": settings.llm_thinking, "thinking_budget": settings.llm_thinking_budget, "max_tokens": None}


def effective_generation(workflow: Workflow, stage: LlmStage | None) -> dict:
    """Los parametros del turno: agente (Workflow.generation) y etapa (LlmStage.generation)."""
    agent = workflow.generation.params if workflow.generation else {}
    over = stage.generation.params if stage and stage.generation else {}
    return llm_params.merge(agent, over)


class LLMResolver:
    def __init__(self, local, sessions: sessionmaker[Session]):
        self.local = local
        self.sessions = sessions
        self.breaker = Breaker()
        self._lock = threading.Lock()
        self._connections: dict[str, tuple[float, ConnectionData | None]] = {}
        self._clients: dict[tuple, LLMClient | AnthropicClient] = {}
        self._locals: dict[tuple, LLMClient] = {}

    def for_turn(self, workflow: Workflow, turn: int, client_id: str | None):
        """El LLM del turno `turn` (1 = el primer mensaje del usuario) del agente."""
        defaults = engine_defaults(workflow.engine)
        plan = workflow.llm
        if plan is None:
            return self._local(effective_generation(workflow, None), defaults)
        stage = plan.stage_for(turn)
        generation = effective_generation(workflow, stage)
        if stage.connection is None:
            return self._local(generation, defaults)
        data = self._connection(stage.connection)
        # El agente solo usa conexiones de su cliente: una definicion con el id de otro no sirve.
        if data is None or data.client_id != client_id:
            return self._unavailable(plan.fallback_local, stage, generation, defaults,
                                     "conexion inexistente, revocada o de otro cliente")
        try:
            primary = self._client(data, stage, generation, defaults)
        except crypto.TokenKeyMissing as e:
            return self._unavailable(plan.fallback_local, stage, generation, defaults, e.message)
        return TurnLLM(primary, self._local(generation, defaults), plan.fallback_local, self.breaker,
                       data.id, data.kind, stage.model or "")

    def _local(self, generation: dict, defaults: dict) -> LLMClient:
        """El cliente propio con los parametros del agente/etapa, cacheado (el LLMClient hornea sus
        options al construirse: derive y cachear es lo unico seguro con varias conversaciones a la vez)."""
        if not hasattr(self.local, "derive"):    # local de prueba (FakeLLM): no aplica parametros
            return self.local
        key = (tuple(sorted(generation.items())), defaults["thinking"], defaults["thinking_budget"],
               defaults["max_tokens"], settings.llm_temperature)
        with self._lock:
            client = self._locals.get(key)
            if client is not None:
                return client
        client = self.local.derive(generation=Generation(params=generation), **defaults)
        with self._lock:
            if len(self._locals) >= 64:
                self._locals.clear()
            self._locals[key] = client
        return client

    def _unavailable(self, fallback: bool, stage: LlmStage, generation: dict, defaults: dict, reason: str):
        logger.error("conexion %s no disponible: %s", stage.connection, reason)
        if not fallback:
            raise LlmUnavailable(reason)
        return TurnLLM(None, self._local(generation, defaults), True, self.breaker, stage.connection or "",
                       "external", stage.model or "", reason=reason)

    def _connection(self, connection_id: str) -> ConnectionData | None:
        now = time.monotonic()
        with self._lock:
            cached = self._connections.get(connection_id)
            if cached and now - cached[0] < CACHE_SECONDS:
                return cached[1]
        with self.sessions() as s:
            row = s.get(LlmConnection, connection_id)
            data = None
            if row is not None and row.revoked_at is None:
                try:
                    key = crypto.decrypt(row.api_key_enc) or ""
                except crypto.TokenKeyMissing:
                    key = ""
                data = ConnectionData(row.id, row.client_id, row.kind, row.base_url, key, row.json_mode,
                                      row.updated_at.timestamp() if row.updated_at else 0.0)
        with self._lock:
            self._connections[connection_id] = (now, data)
        return data

    def _client(self, data: ConnectionData, stage: LlmStage, generation: dict,
                defaults: dict) -> LLMClient | AnthropicClient:
        if not data.api_key:
            raise crypto.TokenKeyMissing("No se puede descifrar la API key de la conexion (WA_TOKEN_KEY)")
        cache_key = (data.id, data.stamp, stage.model, tuple(sorted(generation.items())), defaults["max_tokens"])
        with self._lock:
            client = self._clients.get(cache_key)
            if client is None:
                if len(self._clients) >= 64:
                    self._clients.clear()
                gen = Generation(params=generation)
                if data.kind == "anthropic":
                    client = AnthropicClient(data.api_key, stage.model or "", json_mode=data.json_mode,
                                             timeout=EXTERNAL_TIMEOUT, base_url=data.base_url, generation=gen,
                                             max_tokens=defaults["max_tokens"])
                else:
                    headers = OPENROUTER_HEADERS if data.kind == "openrouter" else None
                    # temperature=None: un externo solo usa la de generation (LLM_TEMPERATURE es del propio).
                    client = LLMClient(data.base_url, data.api_key, stage.model or "", temperature=None,
                                       profile=data.kind, json_mode=data.json_mode, default_headers=headers,
                                       timeout=EXTERNAL_TIMEOUT, generation=gen, max_tokens=defaults["max_tokens"])
                self._clients[cache_key] = client
        return client
