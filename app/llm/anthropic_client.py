"""LLM de Anthropic con el SDK nativo (conexion BYOK kind="anthropic", docs/BYOK_LLM_PLAN.md).

Mismos cuatro metodos que LLMClient (process_turn, converse, extract, structured), sobre la Messages
API: el system va aparte, la salida JSON sale de `output_config.format` y el streaming de
`messages.stream`. Reusa los prompts y esquemas de app/llm/client.py.

Compatibilidad entre modelos (docs de la API, oct-2026):
- Los 4.6+ y 5.x aceptan `output_config.effort`; los anteriores lo rechazan. Para voz va en "low"
  (en "medium" si el motor assistant pide razonar).
- Los 4.7+ y 5.x rechazan temperature/top_p distintos del default: solo se manda en los anteriores.
- No se manda `thinking`: algunos modelos no admiten apagarlo (400); el default de cada uno sirve.
- Si el proveedor rechaza el esquema (limites de structured outputs), se pide en el prompt y se
  valida igual (json_mode "prompt"); el motor ya reintenta una vez los JSON invalidos.
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

from .client import (
    MessageExtractor,
    classic_marker,
    classic_turn,
    clean_json,
    extraction_schema,
    turn_schema,
)
from .prompt import (
    build_classic_messages,
    build_extraction_prompt,
    build_user_prompt,
    extraction_prompt,
    system_prompt,
)

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
    """Mensajes estilo OpenAI -> (system, messages) de Anthropic: la conversacion tiene que empezar
    con el usuario (la apertura del agente va despues de una linea de arranque)."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
    if not rest or rest[0]["role"] != "user":
        rest.insert(0, {"role": "user", "content": OPENING})
    return system, rest


class AnthropicClient:
    def __init__(self, api_key: str, model: str, temperature: float | None = None, *,
                 json_mode: str = "json_schema", timeout: float = 30, base_url: str = ANTHROPIC_URL,
                 generation: Generation | None = None, max_tokens: int | None = None):
        self.client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        self.model = model
        self.profile = "anthropic"
        self.json_mode = json_mode
        self.label = f"anthropic:{model}"
        # Parametros del agente/etapa (app/llm/params.py); pisan a los de la plataforma.
        self.generation = generation.params if generation else {}
        self.max_tokens = max_tokens
        temp = self.generation.get("temperature", temperature)
        self.temperature = temp if temp is not None and accepts_sampling(model) else None
        self._schema_rejected = False

    # --- pedido ----------------------------------------------------------------------------

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
        effort = self.generation.get("effort", effort)
        if supports_effort(self.model):
            params["output_config"] = {"effort": effort}
        return params

    def _guided(self, params: dict, name: str, schema: dict) -> tuple[dict, bool]:
        """Agrega la salida estructurada (o el esquema en el prompt). Devuelve (params, envuelto): un
        esquema sin `type: object` en la raiz (anyOf del motor assistant) se envuelve en {result: ...}."""
        wrapped = schema.get("type") != "object"
        body = {"type": "object", "properties": {"result": schema}, "required": ["result"],
                "additionalProperties": False} if wrapped else schema
        if self.json_mode == "json_schema" and not self._schema_rejected:
            config = {**params.get("output_config", {}), "format": {"type": "json_schema", "schema": body}}
            return {**params, "output_config": config}, wrapped
        note = ("Respondé únicamente con un objeto JSON válido, sin texto antes ni después y sin ```, "
                "que cumpla este JSON Schema:\n" + json.dumps(body, ensure_ascii=False))
        system = f"{params['system']}\n\n{note}" if params.get("system") else note
        return {**params, "system": system}, wrapped

    async def _text(self, params: dict, on_text: Callable[[str], None] | None) -> str:
        """El texto de la respuesta; con on_text, en streaming (a medida que llega)."""
        if on_text is None:
            message = await self.client.messages.create(**params)
            return self._content(message)
        parts = []
        async with self.client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                parts.append(text)
                on_text(text)
            message = await stream.get_final_message()
        self._check(message)
        return "".join(parts)

    @staticmethod
    def _check(message) -> None:
        if message.stop_reason == "refusal":
            raise RuntimeError("Anthropic rechazo el pedido (refusal)")

    def _content(self, message) -> str:
        self._check(message)
        return "".join(b.text for b in message.content if b.type == "text")

    async def _json(self, messages: list[dict], name: str, schema: dict, *, max_tokens: int | None = None,
                    effort: str = "low", on_text: Callable[[str], None] | None = None) -> str:
        """El JSON (texto) de una respuesta guiada por `schema`."""
        params, wrapped = self._guided(self._params(messages, max_tokens, effort), name, schema)
        try:
            raw = await self._text(params, on_text)
        except _BAD_REQUEST as e:
            if "output_config" not in params or "format" not in params["output_config"] or self._schema_rejected:
                raise
            # El esquema no entra en structured outputs: se pide en el prompt (y queda asi).
            logger.warning("anthropic %s rechazo el esquema %s (%s): paso a esquema en el prompt",
                           self.model, name, str(e)[:160])
            self._schema_rejected = True
            params, wrapped = self._guided(self._params(messages, max_tokens, effort), name, schema)
            raw = await self._text(params, on_text)
        raw = clean_json(raw)
        if wrapped:
            raw = json.dumps(json.loads(raw)["result"], ensure_ascii=False)
        return raw

    # --- la interfaz de LLMClient -----------------------------------------------------------

    async def process_turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                           on_message: Callable[[str], None] | None = None) -> AgentTurn:
        extractor = MessageExtractor()

        def feed(text: str) -> None:
            if said := extractor.feed(text):
                on_message(said)

        content = await self._json(
            [{"role": "system", "content": system_prompt(state.channel)},
             {"role": "user", "content": build_user_prompt(workflow, state, user_message)}],
            "agent_turn", turn_schema(workflow), on_text=feed if on_message else None)
        turn = AgentTurn.model_validate_json(content)
        turn.raw = content
        return turn

    async def converse(self, workflow: Workflow, state: ConversationState, user_message: str,
                       on_message: Callable[[str], None] | None = None) -> AgentTurn:
        marker = classic_marker(state)

        def feed(text: str) -> None:
            if said := marker.feed(text):
                on_message(said)

        params = self._params(build_classic_messages(workflow, state, user_message), None)
        content = await self._text(params, feed if on_message else None)
        if on_message is None:
            marker.feed(content)
        if (said := marker.flush()) and on_message:
            on_message(said)
        return classic_turn(marker, raw=content)

    async def extract(self, workflow: Workflow, state: ConversationState, only: list[str] | None = None) -> Extraction:
        content = await self._json(
            [{"role": "system", "content": extraction_prompt(state.channel)},
             {"role": "user", "content": build_extraction_prompt(workflow, state, only)}],
            "extraction", extraction_schema(workflow, only))
        return Extraction(fields=json.loads(content), raw=content)

    async def structured(self, messages: list[dict], schema: dict, name: str = "step",
                         thinking: bool | None = None, budget: int | None = None,
                         max_tokens: int | None = None) -> tuple[str, str | None]:
        """Un pedido con salida JSON guiada (motor assistant). thinking solo sube el effort."""
        content = await self._json(messages, name, schema, max_tokens=max_tokens,
                                   effort="medium" if thinking else "low")
        return content, None
