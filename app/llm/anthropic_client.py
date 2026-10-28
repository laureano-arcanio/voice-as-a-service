"""LLM de Anthropic con el SDK nativo (conexion BYOK kind="anthropic", docs/features/LLM_CONEXIONES.md).

Mismos metodos que LLMClient (converse, extract, structured), sobre la Messages API: el system va aparte, las
herramientas como tool_use/tool_result, la salida JSON de `output_config.format` y el streaming de
`messages.stream`. Reusa los prompts y esquemas de app/llm/client.py.

Compatibilidad entre modelos (docs de la API, oct-2026; es del proveedor, no del comportamiento del modelo):
- Los 4.6+ y 5.x aceptan `output_config.effort`; los anteriores lo rechazan. Va en "low" salvo que la
  generacion del agente diga otra cosa.
- Los 4.7+ y 5.x rechazan temperature/top_p distintos del default: solo se manda en los anteriores.
- No se manda `thinking`: algunos modelos no admiten apagarlo (400); el default de cada uno sirve.
"""
import json
import logging
import re
from collections.abc import Callable

import anthropic

from app.conversation.models import (
    AgentTurn,
    ConversationState,
    Extraction,
    Generation,
    Workflow,
)

from . import platform_tools
from .client import extraction_schema
from .prompt import build_turn_messages, build_extraction_prompt, extraction_prompt

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com"
MIN_OUTPUT_TOKENS = 2048        # el razonamiento adaptativo cuenta contra max_tokens
DEFAULT_OUTPUT_TOKENS = 4096
OPENING = "(La conversación recién empieza.)"
_EFFORT_MODELS = re.compile(r"^claude-(opus|sonnet|haiku|fable|mythos)-(4-[6-9]|[5-9](-\d+)?)$")
_NO_SAMPLING_MODELS = re.compile(r"^claude-(opus|sonnet|haiku|fable|mythos)-(4-[7-9]|[5-9](-\d+)?)$")
_BAD_REQUEST = (anthropic.BadRequestError, anthropic.UnprocessableEntityError)


def supports_effort(model: str) -> bool:
    return bool(_EFFORT_MODELS.match(model))


def accepts_sampling(model: str) -> bool:
    return not _NO_SAMPLING_MODELS.match(model)


def to_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Mensajes estilo OpenAI -> (system, messages) de Anthropic: la conversacion tiene que empezar con el usuario
    (la apertura del agente va despues de una linea de arranque) y los roles alternan (los seguidos se juntan).
    Un mensaje con `name` (una persona del equipo en una derivacion) lleva el nombre adelante."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest: list[dict] = []
    for m in messages:
        if m["role"] == "system":
            continue
        content = f"{m['name']}: {m['content']}" if m.get("name") else m["content"]
        if rest and rest[-1]["role"] == m["role"]:
            rest[-1]["content"] += "\n" + content
        else:
            rest.append({"role": m["role"], "content": content})
    if not rest or rest[0]["role"] != "user":
        rest.insert(0, {"role": "user", "content": OPENING})
    return system, rest


def usage_of(message) -> tuple[int, int]:
    """(entrada, salida) del usage del mensaje final (en streaming, el de message_start y message_delta, que
    junta el SDK). La entrada cuenta tambien la cache."""
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    tokens_in = sum(int(getattr(usage, k, 0) or 0)
                    for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return tokens_in, int(getattr(usage, "output_tokens", 0) or 0)


def _anthropic_tool(t: dict) -> dict:
    f = t["function"]
    return {"name": f["name"], "description": f["description"], "input_schema": f["parameters"]}


class AnthropicClient:
    def __init__(self, api_key: str, model: str, temperature: float | None = None, *,
                 timeout: float = 30, base_url: str = ANTHROPIC_URL,
                 generation: Generation | None = None, max_tokens: int | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        self.model = model
        self.profile = "anthropic"
        self.label = f"anthropic:{model}"
        # Parametros del agente/etapa (app/llm/params.py); pisan a los de la plataforma.
        self.generation = generation.params if generation else {}
        self.max_tokens = max_tokens
        temp = self.generation.get("temperature", temperature)
        self.temperature = temp if temp is not None and accepts_sampling(model) else None

    def _params(self, messages: list[dict], max_tokens: int | None, effort: str = "low") -> dict:
        system, rest = to_messages(messages)
        cap = self.generation.get("max_tokens", max_tokens if max_tokens is not None else self.max_tokens)
        params: dict = {"model": self.model, "messages": rest,
                        "max_tokens": max(cap or DEFAULT_OUTPUT_TOKENS, MIN_OUTPUT_TOKENS)}
        if system:
            params["system"] = system
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if "top_p" in self.generation and accepts_sampling(self.model):
            params["top_p"] = self.generation["top_p"]
        if supports_effort(self.model):
            params["output_config"] = {"effort": self.generation.get("effort", effort)}
        return params

    async def _message(self, params: dict, on_text: Callable[[str], None] | None):
        """El texto y el mensaje entero (para los bloques tool_use)."""
        if on_text is None:
            message = await self.client.messages.create(**params)
            self._check(message)
            return "".join(b.text for b in message.content if b.type == "text"), message
        parts = []
        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                parts.append(text)
                on_text(text)
            message = await stream.get_final_message()
        self._check(message)
        return "".join(parts), message

    @staticmethod
    def _check(message) -> None:
        if message.stop_reason == "refusal":
            raise RuntimeError("Anthropic rechazo el pedido (refusal)")

    async def _json(self, messages: list[dict], schema: dict, *, max_tokens: int | None = None,
                    effort: str = "low") -> str:
        """El JSON de una respuesta guiada por `schema` (salida estructurada; si el modelo no la soporta, el
        error del proveedor llega tal cual)."""
        return (await self._json_message(messages, schema, max_tokens=max_tokens, effort=effort))[0]

    async def _json_message(self, messages: list[dict], schema: dict, *, max_tokens: int | None = None,
                            effort: str = "low"):
        params = self._params(messages, max_tokens, effort)
        params["output_config"] = {**params.get("output_config", {}), "format": {"type": "json_schema", "schema": schema}}
        return await self._message(params, None)

    async def converse(self, workflow: Workflow, state: ConversationState, user_message: str,
                       on_message: Callable[[str], None] | None = None, tools=None) -> AgentTurn:
        """Como LLMClient.converse: herramientas de la plataforma y del cliente con tool_use nativo."""
        params = self._params(build_turn_messages(workflow, state, user_message), None)
        params["tools"] = [_anthropic_tool(t) for t in
                           platform_tools.tools_for(state) + (tools.openai_tools() if tools else [])]
        params["tool_choice"] = {"type": "auto"}
        turn = AgentTurn(assistant_message="")
        said, raw = [], []
        rounds = 0
        while True:
            content, message = await self._message(params, on_message)
            tokens_in, tokens_out = usage_of(message)
            turn.input_tokens += tokens_in
            turn.output_tokens += tokens_out
            said.append(content)
            raw.append(content)
            uses = [b for b in message.content if b.type == "tool_use"]
            calls = [{"id": b.id, "name": b.name, "arguments": json.dumps(b.input, ensure_ascii=False)} for b in uses]
            customer = [c for c in calls if c["name"] not in platform_tools.NAMES]
            if calls:
                raw.append(json.dumps([{"tool": c["name"], "arguments": c["arguments"]} for c in calls],
                                      ensure_ascii=False))
            if customer and tools is not None and rounds >= tools.max_rounds:
                limit = tools.settings.limit_message
                tools.trace.append({"kind": "control", "input": ", ".join(c["name"] for c in customer), "ms": 0,
                                    "output": f"tope de {tools.max_rounds} vueltas con herramientas"})
                if on_message is not None:
                    on_message(limit)
                said.append(limit)
                break
            if customer and tools is not None:
                rounds += 1
                results = dict(await tools.execute(customer, on_message, spoke=bool(content.strip())))
                params["messages"] = params["messages"] + [
                    {"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in message.content
                                                      if b.type in ("text", "tool_use")]},
                    {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": c["id"],
                         "content": results.get(c["id"], '{"ok": true}')} for c in calls]}]
            platform_tools.apply(turn, calls, state)
            if not customer or turn.status == "completed" or turn.handoff:
                break
        turn.assistant_message = " ".join(t.strip() for t in said if t.strip())
        turn.raw = "\n".join(r for r in raw if r)
        return turn

    async def extract(self, workflow: Workflow, state: ConversationState) -> Extraction:
        content, message = await self._json_message(
            [{"role": "system", "content": extraction_prompt(state.channel)},
             {"role": "user", "content": build_extraction_prompt(workflow, state)}], extraction_schema(workflow))
        tokens_in, tokens_out = usage_of(message)
        return Extraction(fields=json.loads(content), raw=content, input_tokens=tokens_in, output_tokens=tokens_out)

    async def structured(self, messages: list[dict], schema: dict, name: str = "step",
                         thinking: bool | None = None, budget: int | None = None,
                         max_tokens: int | None = None) -> tuple[str, str | None]:
        """Un pedido con salida JSON guiada. thinking solo sube el effort."""
        return await self._json(messages, schema, max_tokens=max_tokens, effort="medium" if thinking else "low"), None
