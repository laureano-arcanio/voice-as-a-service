"""Las herramientas del cliente en una conversacion (docs/TOOLS_PLAN.md, 7): que herramientas tiene el
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
from . import schema as S
from .runtime import ToolContext, ToolResult, ToolSpec, run

logger = logging.getLogger(__name__)

SECRETS_TTL = 30.0          # segundos: rotar un secreto rige en el proximo turno pasado este tiempo
CONTEXTS_MAX = 512


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
        out = {"mode": "whatsapp" if state.channel == "whatsapp" else "", "from": None, "to": None}
        if state.channel == "whatsapp" and actor and actor.startswith("wa:"):
            out["from"] = "+" + actor[3:].lstrip("+")
        elif state.channel == "voice":
            from ..models import CallRow, PhoneNumber
            with self.sessions() as s:
                call = s.get(CallRow, state.conversation_id)
                if call is not None:
                    ours = (s.scalar(select(PhoneNumber.e164).where(PhoneNumber.id == call.phone_number_id))
                            if call.phone_number_id else None)
                    out["mode"] = str(call.mode.value if hasattr(call.mode, "value") else call.mode)
                    out["from"], out["to"] = ((ours, call.phone) if out["mode"] == "saliente" else (call.phone, ours))
        with self._lock:
            self._calls[state.conversation_id] = out
            while len(self._calls) > CONTEXTS_MAX:
                self._calls.popitem(last=False)
        return out

    def context(self, workflow: Workflow, state: ConversationState, actor: str | None) -> ToolContext:
        call = self._call(state, actor)
        return ToolContext(conversation_id=state.conversation_id, channel=state.channel, mode=call["mode"],
                           from_=call["from"], to=call["to"], agent_slug=workflow.id, agent_version=workflow.version,
                           fields={k: v for k, v in state.fields.items() if v is not None},
                           contact=dict(state.progress.contact), vars=dict(state.progress.tool_vars),
                           secrets=self._secret_values(state.agent_id), timezone=settings.agent_timezone)

    def turn(self, workflow: Workflow, state: ConversationState, actor: str | None) -> "TurnTools | None":
        specs = self.specs(workflow, state)
        if not specs:
            return None
        return TurnTools(specs=specs, ctx=self.context(workflow, state, actor),
                         settings=workflow.tool_settings or ToolSettings(), voice=state.channel == "voice")


@dataclass
class TurnTools:
    """Las herramientas de un turno: las define para el LLM y ejecuta lo que pide."""
    specs: list[ToolSpec]
    ctx: ToolContext
    settings: ToolSettings
    voice: bool = True
    trace: list[dict] = field(default_factory=list)
    calls: int = 0              # herramientas ejecutadas en el turno (el respaldo de BYOK no repite el turno)

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
        if not result.ok and spec.messages.failed and on_message is not None and self.voice:
            on_message(spec.messages.failed)
        self.trace.append({"kind": "herramienta", "input": f"{spec.slug} {json.dumps(args, ensure_ascii=False)}",
                           "ms": round((time.perf_counter() - started) * 1000), "output": result.llm,
                           "tool": {"slug": spec.slug, "type": spec.type, "revision": spec.revision,
                                    **result.trace()}})
        return result.llm

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
