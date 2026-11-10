"""Las herramientas del cliente en una conversacion (docs/features/HERRAMIENTAS.md): que herramientas tiene el
agente, el contexto de la llamada (numeros, modo, secretos del agente, vars) y la ejecucion de lo que pide el
modelo en un turno, con las frases de voz de cada herramienta. El modelo decide que llamar y cuando; la
plataforma ejecuta y le devuelve el resultado, sin interpretar lo que dijo la persona."""
import asyncio
import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select

from ..config import settings
from ..conversation.models import ConversationState, ToolSettings, Workflow
from ..db import utcnow
from . import schema as S
from .runtime import ToolContext, ToolResult, ToolSpec, run

logger = logging.getLogger(__name__)

SECRETS_TTL = 30.0          # segundos: rotar un secreto rige en el proximo turno pasado este tiempo
CONTEXTS_MAX = 512


NOT_EXECUTABLE = "not_executable"


def workflow_event_data(slug: str, result: ToolResult) -> dict:
    """Lo que sale de un workflow en events. Nunca la respuesta ni su error, que pueden traer datos de la persona."""
    return {"ok": bool(result.ok), "status": result.status, "ms": result.ms, "slug": slug,
            **({"reason": NOT_EXECUTABLE} if result.error == NOT_EXECUTABLE else {})}


def is_transport(result: ToolResult) -> bool:
    """Sin respuesta, o una que pide volver a intentar. Una falla sin pedido hecho no entra: no hay nada que repetir."""
    return result.transport or result.status == 429 or (result.status is not None and result.status >= 500)


def workflow_error(result: ToolResult) -> str:
    """El diagnostico de un workflow que fallo: tipo, HTTP y si fue de transporte. Sin texto: un no-2xx o una funcion
    que falla traen lo que dijo la API del cliente, que puede tener datos de la persona."""
    http = f" | HTTP {result.status}" if result.status is not None else ""
    return (f"herramienta automática: {result.code or 'error'}{http} | falla de conexión: "
            f"{'sí' if is_transport(result) else 'no'}")


def record_run(sessions, spec: ToolSpec, result: ToolResult, ms: int, *, client_id: str | None,
               agent_id: str | None, conversation_id: str | None) -> None:
    """Una fila en tool_runs. Si falla (la base, una FK), se loguea y la llamada sigue."""
    if sessions is None or not client_id:
        return
    from ..models import ToolRun
    try:
        with sessions() as s:
            s.add(ToolRun(client_id=client_id, tool_id=spec.tool_id, conversation_id=conversation_id or None,
                          agent_id=agent_id, slug=spec.slug[:64], type=spec.type[:8], ok=bool(result.ok),
                          status_code=result.status if spec.type == "http" else None, ms=result.ms or ms,
                          error=("" if result.ok else str(result.error or ""))[:255], created_at=utcnow()))
            s.commit()
    except Exception:
        logger.exception("tools: no se pudo registrar la ejecucion de %s", spec.slug)


class ConversationTools:
    """Una por motor. Lee la base en cada turno (las herramientas cambian sin version del agente)."""

    def __init__(self, sessions):
        self.sessions = sessions
        self._lock = threading.Lock()
        self._secrets: dict[str, tuple[float, dict[str, str]]] = {}
        self._calls: OrderedDict[str, dict] = OrderedDict()

    def specs(self, workflow: Workflow, state: ConversationState) -> list[ToolSpec]:
        if not workflow.tools or self.sessions is None:
            return []
        from ..services import tools as tools_service
        with self.sessions() as s:
            return tools_service.agent_tool_specs(s, state.client_id, workflow)

    def _secret_values(self, agent_id: str) -> dict[str, str]:
        now = time.monotonic()
        with self._lock:
            cached = self._secrets.get(agent_id)
            if cached and now - cached[0] < SECRETS_TTL:
                return cached[1]
        from ..services import tools as tools_service
        with self.sessions() as s:
            values = tools_service.secret_values(s, agent_id)
        with self._lock:
            self._secrets[agent_id] = (now, values)
        return values

    def _call(self, state: ConversationState, actor: str | None) -> dict:
        """Modo y numeros de la llamada (o el WhatsApp del que escribe), una vez por conversacion."""
        with self._lock:
            if (cached := self._calls.get(state.conversation_id)) is not None:
                return cached
        out = {"mode": "whatsapp" if state.channel == "whatsapp" else "", "from": None, "to": None, "phone": None}
        if state.channel == "whatsapp" and actor and actor.startswith("wa:"):
            out["from"] = out["phone"] = "+" + actor[3:].lstrip("+")
        elif state.channel == "voice":
            from ..models import CallRow, PhoneNumber
            with self.sessions() as s:
                call = s.get(CallRow, state.conversation_id)
                if call is not None:
                    ours = (s.scalar(select(PhoneNumber.e164).where(PhoneNumber.id == call.phone_number_id))
                            if call.phone_number_id else None)
                    out["mode"] = str(call.mode.value if hasattr(call.mode, "value") else call.mode)
                    out["from"], out["to"] = ((ours, call.phone) if out["mode"] in ("saliente", "celular") else (call.phone, ours))
                    out["phone"] = call.phone
                elif state.progress.caller_phone:   # prueba por texto con numero simulado (POST /conversations)
                    out["from"] = out["phone"] = state.progress.caller_phone
        with self._lock:
            self._calls[state.conversation_id] = out
            while len(self._calls) > CONTEXTS_MAX:
                self._calls.popitem(last=False)
        return out

    def context(self, workflow: Workflow, state: ConversationState, actor: str | None) -> ToolContext:
        call = self._call(state, actor)
        return ToolContext(conversation_id=state.conversation_id, channel=state.channel, mode=call["mode"],
                           from_=call["from"], to=call["to"], phone=call["phone"], agent_slug=workflow.id,
                           agent_version=workflow.version,
                           fields={k: v for k, v in state.fields.items() if v is not None},
                           contact=dict(state.progress.contact), vars=dict(state.progress.tool_vars),
                           secrets=self._secret_values(state.agent_id), timezone=settings.agent_timezone)

    def turn(self, workflow: Workflow, state: ConversationState, actor: str | None) -> "TurnTools | None":
        specs = self.specs(workflow, state)
        if not specs:
            return None
        return TurnTools(specs=specs, ctx=self.context(workflow, state, actor),
                         settings=workflow.tool_settings or ToolSettings(), voice=state.channel == "voice",
                         sessions=self.sessions, client_id=state.client_id, agent_id=state.agent_id)

    def workflow_spec(self, state: ConversationState, slug: str, key: str) -> ToolSpec | None:
        """La herramienta de un workflow, siempre del cliente de la conversacion. None si no se puede ejecutar:
        borrada, invalida o, en el post-call, editada despues a algo sin Idempotency-Key (code o GET)."""
        if self.sessions is None or not state.client_id:
            return None
        from ..models import ClientTool
        from ..services import tools as tools_service
        with self.sessions() as s:
            row = s.scalar(select(ClientTool).where(ClientTool.client_id == state.client_id, ClientTool.slug == slug))
            if row is None:
                return None
            try:
                spec = tools_service.spec_of(row, tools_service.credentials_map(s, state.client_id))
            except ValueError:      # ValidationError de pydantic es un ValueError
                logger.warning("tools: definicion invalida de %s (cliente %s)", slug, state.client_id)
                return None
        if key == "post_call" and (spec.type != "http" or spec.tool.http.method == "GET"):
            return None
        return spec

    async def run_workflow(self, workflow: Workflow, state: ConversationState, slug: str, actor: str | None,
                           key: str, *, emit: bool = True) -> ToolResult:
        """Una herramienta de workflow (`key`: pre_call o post_call), sin parametros del modelo. Idempotency-Key
        fija: <conversacion>:<key>. Deja la fila en tool_runs y el evento workflow.<key> (`emit`), con metadatos:
        la respuesta no va a mensajes, traza ni eventos, y su error se reemplaza por workflow_error. error
        "not_executable": no se llamo a nada."""
        spec = self.workflow_spec(state, slug, key)
        if spec is None:
            result = ToolResult(ok=False, error=NOT_EXECUTABLE)
        else:
            result = await run(spec, {}, self.context(workflow, state, actor), key)
            if not result.ok:
                result.error = workflow_error(result)
            record_run(self.sessions, spec, result, result.ms, client_id=state.client_id,
                       agent_id=state.agent_id, conversation_id=state.conversation_id)
        if emit:
            self._workflow_event(state, slug, key, result)
        return result

    def _workflow_event(self, state: ConversationState, slug: str, key: str, result: ToolResult) -> None:
        if self.sessions is None or not state.client_id:
            return
        from ..services import events
        try:
            with self.sessions() as s:
                events.record(s, state.client_id, f"workflow.{key}", conversation_id=state.conversation_id,
                              **workflow_event_data(slug, result))
                s.commit()
        except Exception:
            logger.exception("tools: no se pudo registrar el evento de %s", slug)


@dataclass
class TurnTools:
    """Las herramientas de un turno: las define para el LLM y ejecuta lo que pide."""
    specs: list[ToolSpec]
    ctx: ToolContext
    settings: ToolSettings
    voice: bool = True
    trace: list[dict] = field(default_factory=list)
    calls: int = 0              # herramientas ejecutadas en el turno (el respaldo de BYOK no repite el turno)
    # Para registrar cada ejecucion en tool_runs (reportes del admin, docs/features/REPORTES.md).
    sessions: object = None
    client_id: str | None = None
    agent_id: str | None = None

    @property
    def by_name(self) -> dict[str, ToolSpec]:
        return {s.slug: s for s in self.specs}

    def openai_tools(self) -> list[dict]:
        return [S.openai_tool(s.slug, s.tool) for s in self.specs]

    @property
    def max_rounds(self) -> int:
        return self.settings.max_calls_per_turn

    async def _one(self, call_id: str, name: str, raw_args: str, on_message: Callable[[str], None] | None) -> str:
        spec = self.by_name.get(name)
        started = time.perf_counter()
        if spec is None:
            out = json.dumps({"ok": False, "error": f"No existe la herramienta {name}"}, ensure_ascii=False)
            self.trace.append({"kind": "herramienta", "input": f"{name} {raw_args}", "ms": 0, "output": out})
            return out
        try:
            args = json.loads(raw_args or "{}")
        except ValueError:
            args = raw_args
        result: ToolResult = await run(spec, args, self.ctx, call_id)
        ms = round((time.perf_counter() - started) * 1000)
        if not result.ok and spec.messages.failed and on_message is not None and self.voice:
            on_message(spec.messages.failed)
        self.trace.append({"kind": "herramienta", "input": f"{spec.slug} {json.dumps(args, ensure_ascii=False)}",
                           "ms": ms, "output": result.llm,
                           "tool": {"slug": spec.slug, "type": spec.type, "revision": spec.revision,
                                    **result.trace()}})
        self._record(spec, result, ms)
        return result.llm

    def _record(self, spec: ToolSpec, result: ToolResult, ms: int) -> None:
        record_run(self.sessions, spec, result, ms, client_id=self.client_id, agent_id=self.agent_id,
                   conversation_id=self.ctx.conversation_id)

    async def execute(self, calls: list[dict], on_message: Callable[[str], None] | None,
                      spoke: bool) -> list[tuple[str, str]]:
        """calls: [{id, name, arguments}]. Corre en paralelo; dice la frase de inicio de la primera que la tenga
        (si el modelo no hablo en esta vuelta) y la de demora. Devuelve [(id, resultado para el modelo)]."""
        self.calls += len(calls)
        specs = [self.by_name.get(c["name"]) for c in calls]
        if on_message is not None and self.voice and not spoke:
            if starts := [s.messages.start for s in specs if s is not None and s.messages.start]:
                on_message(starts[0])
        tasks = [asyncio.ensure_future(self._one(c["id"], c["name"], c["arguments"], on_message)) for c in calls]
        delays = [s.messages.delayed for s in specs if s is not None and s.messages.delayed]
        if delays and on_message is not None and self.voice:
            delayed = min(delays, key=lambda d: d.after_ms)
            done, _ = await asyncio.wait(tasks, timeout=delayed.after_ms / 1000)
            if len(done) < len(tasks):
                on_message(delayed.text)
        results = await asyncio.gather(*tasks)
        return [(c["id"], r) for c, r in zip(calls, results)]
