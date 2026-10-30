"""Motor external (docs/features/LLM_CONEXIONES.md): cada turno lo contesta el agente del cliente.

El endpoint es compatible con OpenAI (`POST /chat/completions`, `stream: true`) y sale de una conexion del
cliente (llm_connections, `openai_compatible`). Se le manda la conversacion entera en cada turno (el historial
es la fuente de verdad: un turno deshecho no vuelve) y dos herramientas de la plataforma, `end_call` y, en una
llamada con areas, `transfer_call`. Los datos de la llamada van en headers `X-Atentina-*`: el cuerpo lleva solo
campos estandar, porque un endpoint que reenvia a OpenAI rechazaria los desconocidos.

No hay respaldo con el LLM propio: no tiene el prompt del cliente. Un error lo maneja el motor
(app/conversation/engine.py) con el mensaje y la accion de ExternalConfig.
"""
import asyncio
import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..conversation.models import AgentTurn, ConversationState, Workflow
from ..models import CallRow, Client, LlmConnection, PhoneNumber
from ..services import limits as limits_service
from ..whatsapp import crypto
from . import platform_tools

logger = logging.getLogger(__name__)

CACHE_SECONDS = 30          # una conexion revocada o un plan que ya no la incluye dejan de usarse en a lo sumo esto
TURN_TIMEOUT = 30           # un turno entero (el primer token tiene su propio tope, ExternalConfig)
HEADER_MAX = 2000           # contacto y motivo en headers: recortados, para no pasar el limite del servidor
CONTEXTS_MAX = 1024         # datos de llamada cacheados por conversacion


class ExternalError(Exception):
    """El turno no tiene respuesta del agente del cliente. code: el motivo, para la traza y el corte."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail
        self.trace: dict = {}     # el turno fallido, para la traza (vacio si no llego a pedirse)


@dataclass(frozen=True)
class Target:
    connection_id: str
    model: str
    client: AsyncOpenAI


@dataclass
class ExternalResult:
    turn: AgentTurn
    outcome: str | None         # el de end_call, si vino
    trace: dict


def build_messages(workflow: Workflow, state: ConversationState, user_message: str) -> list[dict]:
    """La conversacion como mensajes de OpenAI. Lo que dijo una persona del equipo (derivacion) va como
    assistant con su nombre."""
    messages = [{"role": "system", "content": workflow.external.system}] if workflow.external.system else []
    for m in state.messages:
        message = {"role": m.role, "content": m.text}
        if m.person:
            message["name"] = "".join(c if c.isalnum() else "_" for c in m.person)[:64]
        messages.append(message)
    messages.append({"role": "user", "content": user_message})
    return messages


def _ascii(value: str, limit: int = 256) -> str:
    """Un header tiene que ser ASCII: JSON con escapes para lo que no lo es."""
    text = json.dumps(value, ensure_ascii=True)[1:-1] if not value.isascii() else value
    return text[:limit]


class ExternalAgents:
    """Resuelve el endpoint de cada agente (conexion + plan, cacheados) y corre los turnos."""

    def __init__(self, sessions: sessionmaker[Session]):
        self.sessions = sessions
        self._lock = threading.Lock()
        self._targets: dict[tuple[str, str], tuple[float, Target | None, str]] = {}
        self._clients: dict[tuple[str, float], AsyncOpenAI] = {}
        self._contexts: OrderedDict[str, dict] = OrderedDict()

    def target(self, workflow: Workflow, client_id: str | None) -> Target:
        """La conexion del agente, si es de su cliente, esta vigente y el plan incluye la funcion.
        ExternalError(external_agent_not_in_plan | connection_unavailable) si no."""
        key = (workflow.external.connection, client_id or "")
        now = time.monotonic()
        with self._lock:
            cached = self._targets.get(key)
        if cached is None or now - cached[0] >= CACHE_SECONDS:
            target, problem = self._load(workflow, client_id)
            cached = (now, target, problem)
            with self._lock:
                self._targets[key] = cached
        _, target, problem = cached
        if target is None:
            raise ExternalError(problem)
        if workflow.external.model and workflow.external.model != target.model:
            return Target(target.connection_id, workflow.external.model, target.client)
        return target

    def _load(self, workflow: Workflow, client_id: str | None) -> tuple[Target | None, str]:
        with self.sessions() as s:
            client = s.get(Client, client_id) if client_id else None
            if client is None or not limits_service.effective_limits(s, client).external_agent:
                return None, "external_agent_not_in_plan"
            row = s.get(LlmConnection, workflow.external.connection)
            if row is None or row.client_id != client_id or row.revoked_at is not None:
                return None, "connection_unavailable"
            try:
                key = crypto.decrypt(row.api_key_enc) or ""
            except crypto.TokenKeyMissing:
                key = ""
            if not key:
                return None, "connection_unavailable"
            stamp = row.updated_at.timestamp() if row.updated_at else 0.0
            with self._lock:
                http = self._clients.get((row.id, stamp))
                if http is None:
                    if len(self._clients) >= 64:
                        self._clients.clear()
                    http = self._clients[(row.id, stamp)] = AsyncOpenAI(
                        base_url=row.base_url, api_key=key, max_retries=0,
                        timeout=httpx.Timeout(TURN_TIMEOUT, connect=5))
            return Target(row.id, row.default_model or "agent", http), ""

    def context(self, state: ConversationState, actor: str | None) -> dict:
        """Los datos de la llamada para los headers, una vez por conversacion: modo, numeros y la campaña."""
        with self._lock:
            if (cached := self._contexts.get(state.conversation_id)) is not None:
                return cached
        ctx = {"mode": state.channel if state.channel == "whatsapp" else "", "from": "", "to": ""}
        if state.channel == "whatsapp" and actor and actor.startswith("wa:"):
            ctx["from"] = "+" + actor[3:].lstrip("+")
        elif state.channel == "voice":
            with self.sessions() as s:
                call = s.get(CallRow, state.conversation_id)
                if call is not None:
                    ours = (s.scalar(select(PhoneNumber.e164).where(PhoneNumber.id == call.phone_number_id))
                            if call.phone_number_id else None) or ""
                    ctx["mode"] = call.mode
                    # Entrante: llama `phone` a un numero nuestro; saliente: al reves.
                    ctx["from"], ctx["to"] = ((ours, call.phone or "") if call.mode in ("saliente", "celular")
                                              else (call.phone or "", ours))
        with self._lock:
            self._contexts[state.conversation_id] = ctx
            while len(self._contexts) > CONTEXTS_MAX:
                self._contexts.popitem(last=False)
        return ctx

    def headers(self, workflow: Workflow, state: ConversationState, actor: str | None) -> dict[str, str]:
        ctx = self.context(state, actor)
        turn = 1 + sum(m.role == "user" for m in state.messages)
        headers = {"X-Atentina-Conversation-Id": state.conversation_id, "X-Atentina-Channel": state.channel,
                   "X-Atentina-Mode": ctx["mode"], "X-Atentina-From": ctx["from"], "X-Atentina-To": ctx["to"],
                   "X-Atentina-Agent": _ascii(workflow.id), "X-Atentina-Turn": str(turn)}
        if state.progress.contact:
            headers["X-Atentina-Contact"] = json.dumps(state.progress.contact, ensure_ascii=True)[:HEADER_MAX]
        if state.progress.context:
            headers["X-Atentina-Context"] = _ascii(state.progress.context, HEADER_MAX)
        return {k: v for k, v in headers.items() if v}

    async def turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                   on_message: Callable[[str], None] | None, actor: str | None) -> ExternalResult:
        """El turno del agente del cliente. ExternalError si no contesta (nada se dijo todavia); si se corta
        despues de empezar a hablar, queda lo dicho y el error en la traza."""
        target = self.target(workflow, state.client_id)
        tools = platform_tools.tools_for(state, [o.id for o in workflow.completion.outcomes])
        request = dict(model=target.model, messages=build_messages(workflow, state, user_message), tools=tools,
                       stream=True, user=state.conversation_id,
                       extra_headers=self.headers(workflow, state, actor))
        started = time.perf_counter()
        first = asyncio.Event()
        parts: list[str] = []
        calls: dict[int, dict] = {}
        usage = [0, 0]      # si el endpoint manda usage (no se le pide: el cuerpo lleva solo lo estandar)

        async def consume() -> None:
            async for chunk in await target.client.chat.completions.create(**request):
                if (u := getattr(chunk, "usage", None)) is not None:
                    usage[:] = [int(getattr(u, "prompt_tokens", 0) or 0), int(getattr(u, "completion_tokens", 0) or 0)]
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    first.set()
                    parts.append(delta.content)
                    if on_message is not None:
                        on_message(delta.content)
                for call in delta.tool_calls or []:
                    first.set()
                    slot = calls.setdefault(call.index, {"name": "", "arguments": ""})
                    if call.function and call.function.name:
                        slot["name"] += call.function.name
                    if call.function and call.function.arguments:
                        slot["arguments"] += call.function.arguments

        task = asyncio.create_task(consume())
        error: ExternalError | None = None
        first_ms = None
        try:
            waiter = asyncio.create_task(first.wait())
            done, _ = await asyncio.wait({task, waiter}, timeout=workflow.external.first_token_timeout_ms / 1000,
                                         return_when=asyncio.FIRST_COMPLETED)
            waiter.cancel()
            if first.is_set():
                first_ms = round((time.perf_counter() - started) * 1000)
            if not done:
                raise ExternalError("timeout", f"sin respuesta en {workflow.external.first_token_timeout_ms} ms")
            await asyncio.wait_for(task, TURN_TIMEOUT)
        except asyncio.CancelledError:
            task.cancel()
            raise
        except ExternalError as e:
            error = e
        except asyncio.TimeoutError:
            error = ExternalError("timeout", f"el turno paso los {TURN_TIMEOUT} s")
        except Exception as e:      # HTTP, red, respuesta que no es SSE
            error = ExternalError("endpoint_error", f"{type(e).__name__}: {e}"[:300])
        finally:
            if not task.done():
                task.cancel()
        text = "".join(parts).strip()
        ms = round((time.perf_counter() - started) * 1000)
        tools_used = [c for _, c in sorted(calls.items())]
        trace = {"kind": "turno", "input": user_message, "ms": ms, "first_token_ms": first_ms,
                 "output": text + (f"\n{json.dumps(tools_used, ensure_ascii=False)}" if tools_used else ""),
                 "provider": "external", "model": target.model}
        if error is not None:
            trace["error"] = str(error)
            if not text:
                logger.warning("agente externo %s: %s", workflow.id, error)
                error.trace = trace
                raise error
            logger.warning("agente externo %s: se corto despues de hablar (%s)", workflow.id, error)
        if not text and not tools_used:
            error = ExternalError("empty_response", "el endpoint no devolvio texto ni herramientas")
            error.trace = {**trace, "error": str(error)}
            raise error
        result = self._result(text, tools_used, state, trace)
        result.turn.input_tokens, result.turn.output_tokens = usage
        return result

    @staticmethod
    def _result(text: str, tools_used: list[dict], state: ConversationState, trace: dict) -> ExternalResult:
        turn = AgentTurn(assistant_message=text)
        outcome = platform_tools.apply(turn, tools_used, state)
        return ExternalResult(turn=turn, outcome=outcome, trace=trace)
