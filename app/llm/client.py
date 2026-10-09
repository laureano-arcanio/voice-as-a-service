import asyncio
import json
import logging
import re
from collections.abc import Callable

from openai import APIError, APITimeoutError, AsyncOpenAI, BadRequestError
from pydantic import ValidationError

from app.config import settings
from app.conversation.models import AgentTurn, ConversationState, Extraction, Workflow

from . import budget
from .errors import LLMContextError, LLMError, LLMTimeoutError
from .prompt import (
    END_MARKER,
    build_classic_messages,
    build_extraction_prompt,
    build_user_prompt,
    conversation_line,
    extraction_prompt,
    system_prompt,
)

logger = logging.getLogger(__name__)

TYPE_SCHEMAS = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "email": {"type": "string"},
    "email_or_phone": {"type": "string"},
}


def field_schema(spec) -> dict:
    base = {"type": "string", "enum": spec.options} if spec.type == "choice" else TYPE_SCHEMAS[spec.type]
    return {"anyOf": [base, {"type": "null"}]}


def turn_schema(workflow: Workflow) -> dict:
    return {
        "type": "object",
        # assistant_message primero: el decoding guiado respeta este orden y el
        # agente de voz manda el mensaje al TTS mientras se genera el resto.
        "properties": {
            "assistant_message": {"type": "string"},
            "answered": {"type": "boolean"},
            "next_objective": {"anyOf": [{"type": "string", "enum": list(workflow.fields)}, {"type": "null"}]},
            "status": {"type": "string", "enum": ["active", "completed"]},
        },
        "required": ["assistant_message", "answered", "next_objective", "status"],
        "additionalProperties": False,
    }


def extraction_schema(workflow: Workflow, only: list[str] | None = None) -> dict:
    names = [n for n, _ in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority) if only is None or n in only]
    return {
        "type": "object",
        "properties": {n: field_schema(workflow.fields[n]) for n in names},
        "required": names,
        "additionalProperties": False,
    }


# Recomendados por Qwen: con pensamiento, 0.6 / 0.95 / 20; sin pensamiento, 0.7 / 0.8 / 20.
# Qwen desaconseja temperaturas bajas o greedy con pensamiento (se repite).
SAMPLING = {
    True: {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0},
    False: {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0},
}


def request_options(thinking: bool, budget: int, temperature: float | None = None) -> dict:
    sampling = dict(SAMPLING[thinking])
    if temperature is not None:
        sampling["temperature"] = temperature
    extra = {"top_k": sampling.pop("top_k"), "min_p": sampling.pop("min_p"),
             "chat_template_kwargs": {"enable_thinking": thinking}}
    if thinking:
        extra["thinking_token_budget"] = budget
    return {**sampling, "extra_body": extra}


class LLMClient:
    """Cada pedido lleva max_tokens y entra en LLM_CONTEXT_TOKENS: si la conversacion no
    entra, salen los mensajes mas viejos (app/llm/budget.py). Los errores salen como
    LLMError (o LLMContextError / LLMTimeoutError), con un deadline por pedido entero."""

    def __init__(self, base_url: str, api_key: str, model: str, thinking: bool = settings.llm_thinking,
                 thinking_budget: int = settings.llm_thinking_budget, temperature: float | None = settings.llm_temperature):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30)
        self.model = model
        self.options = request_options(thinking, thinking_budget, temperature)
        self.reasoning_tokens = budget.thinking_tokens(thinking, thinking_budget)

    async def process_turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                           on_message: Callable[[str], None] | None = None) -> AgentTurn:
        """Con on_message, pide el JSON en streaming y le pasa assistant_message
        a medida que llega, antes de que termine el resto del JSON."""
        max_tokens = budget.max_tokens_reply(self.reasoning_tokens)
        request = dict(
            model=self.model,
            messages=fit_structured(workflow, state, user_message, max_tokens),
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "agent_turn", "schema": turn_schema(workflow), "strict": True},
            },
            max_tokens=max_tokens,
            **self.options,
        )
        spoken = Spoken(on_message)

        async def run() -> AgentTurn:
            if on_message is None:
                message = (await self.client.chat.completions.create(**request)).choices[0].message
                content = message.content or ""
                # vLLM separa el razonamiento (--reasoning-parser qwen3).
                reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
            else:
                content, reasoning = await self._stream(request, spoken)
            turn = parse_turn(content, state)
            turn.raw = content
            turn.reasoning = reasoning
            return turn

        return await guarded(run(), settings.llm_turn_deadline_seconds, spoken)

    async def converse(self, workflow: Workflow, state: ConversationState, user_message: str,
                       on_message: Callable[[str], None] | None = None) -> AgentTurn:
        """Motor clasico: texto libre con la conversacion como mensajes. El fin
        lo marca END_MARKER, que se saca antes de decirlo."""
        max_tokens = budget.max_tokens_reply(self.reasoning_tokens)
        request = dict(model=self.model, messages=fit_classic(workflow, state, user_message, max_tokens),
                       max_tokens=max_tokens, **self.options)
        marker = MarkerFilter(END_MARKER)
        spoken = Spoken(on_message)

        async def run() -> AgentTurn:
            if on_message is None:
                choice = (await self.client.chat.completions.create(**request)).choices[0]
                message = choice.message
                content = message.content or ""
                reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
                finish = getattr(choice, "finish_reason", None)
                marker.feed(content)
                marker.flush()
            else:
                parts, reasoning_parts, finish = [], [], None
                async for chunk in await self.client.chat.completions.create(**request, stream=True):
                    if not chunk.choices:
                        continue
                    finish = getattr(chunk.choices[0], "finish_reason", None) or finish
                    delta = chunk.choices[0].delta
                    if text := getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None):
                        reasoning_parts.append(text)
                    if delta.content:
                        parts.append(delta.content)
                        if text := marker.feed(delta.content):
                            spoken(text)
                if text := marker.flush():
                    spoken(text)
                content, reasoning = "".join(parts), "".join(reasoning_parts) or None
            if finish == "length":
                logger.warning("llm: respuesta cortada por max_tokens=%s %s", max_tokens, state.conversation_id)
            return AgentTurn(assistant_message=marker.text.strip(), status="completed" if marker.found else "active",
                             raw=content, reasoning=reasoning)

        return await guarded(run(), settings.llm_turn_deadline_seconds, spoken)

    async def extract(self, workflow: Workflow, state: ConversationState, only: list[str] | None = None) -> Extraction:
        """Los datos del usuario segun toda la conversacion (only: solo esos campos). Si no
        entra en el contexto, sin los mensajes mas viejos: en structured known_fields ya trae
        lo extraido antes; en classic (una extraccion al final) se pierde lo de esos mensajes."""
        max_tokens = budget.max_tokens_extract(self.reasoning_tokens)
        request = dict(
            model=self.model,
            messages=fit_extraction(workflow, state, only, max_tokens),
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": extraction_schema(workflow, only), "strict": True},
            },
            max_tokens=max_tokens,
            **self.options,
        )

        async def run() -> Extraction:
            message = (await self.client.chat.completions.create(**request)).choices[0].message
            reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
            return Extraction(fields=json.loads(message.content), raw=message.content, reasoning=reasoning)

        return await guarded(run(), settings.llm_extract_deadline_seconds)

    async def _stream(self, request: dict, on_message: Callable[[str], None]) -> tuple[str, str | None]:
        content, reasoning = [], []
        message = MessageExtractor()
        async for chunk in await self.client.chat.completions.create(**request, stream=True):
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if text := getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None):
                reasoning.append(text)
            if delta.content:
                content.append(delta.content)
                if text := message.feed(delta.content):
                    on_message(text)
        return "".join(content), "".join(reasoning) or None


# ---------- presupuesto de contexto ----------

def fit_structured(workflow: Workflow, state: ConversationState, user_message: str, max_tokens: int) -> list[dict]:
    """Sistema fijo + un mensaje con definicion, conversacion, estado y mensaje nuevo; si no
    entra, la conversacion sin sus lineas mas viejas."""
    system = system_prompt(state.channel)
    empty = state.model_copy(update={"messages": []})
    fixed = budget.message_tokens(system) + budget.message_tokens(build_user_prompt(workflow, empty, user_message))
    whatsapp = state.channel == "whatsapp"
    history = [budget.estimate_tokens(conversation_line(m, whatsapp)) + 1 for m in state.messages]
    drop = budget.drop_count(fixed, history, budget.prompt_limit(max_tokens))
    if drop:
        logger.info("llm: %s mensajes viejos fuera del contexto %s", drop, state.conversation_id)
        state = state.model_copy(update={"messages": state.messages[drop:]})
    return [{"role": "system", "content": system},
            {"role": "user", "content": build_user_prompt(workflow, state, user_message, drop)}]


def fit_classic(workflow: Workflow, state: ConversationState, user_message: str, max_tokens: int) -> list[dict]:
    """Sistema (el agente entero) + historial como mensajes + mensaje nuevo; si no entra,
    sin los mensajes mas viejos (de a pares: la alternancia no cambia)."""
    messages = build_classic_messages(workflow, state, user_message)
    fixed = budget.message_tokens(messages[0]["content"]) + budget.message_tokens(messages[-1]["content"])
    history = [budget.message_tokens(m["content"]) for m in messages[1:-1]]
    drop = budget.drop_count(fixed, history, budget.prompt_limit(max_tokens))
    if not drop:
        return messages
    logger.info("llm: %s mensajes viejos fuera del contexto %s", drop, state.conversation_id)
    return build_classic_messages(workflow, state.model_copy(update={"messages": state.messages[drop:]}),
                                  user_message, drop)


def fit_extraction(workflow: Workflow, state: ConversationState, only: list[str] | None,
                   max_tokens: int) -> list[dict]:
    system = extraction_prompt(state.channel)
    empty = state.model_copy(update={"messages": []})
    fixed = budget.message_tokens(system) + budget.message_tokens(build_extraction_prompt(workflow, empty, only))
    whatsapp = state.channel == "whatsapp"
    history = [budget.estimate_tokens(conversation_line(m, whatsapp)) + 1 for m in state.messages]
    drop = budget.drop_count(fixed, history, budget.prompt_limit(max_tokens))
    if drop:
        logger.info("llm: extraccion sin %s mensajes viejos %s", drop, state.conversation_id)
        state = state.model_copy(update={"messages": state.messages[drop:]})
    return [{"role": "system", "content": system},
            {"role": "user", "content": build_extraction_prompt(workflow, state, only, drop)}]


# ---------- errores ----------

# 400 de vLLM por longitud: "maximum context length is ...", "longer than the maximum
# model length", "max_tokens ... is too large".
CONTEXT_ERROR_RE = re.compile(r"context length|maximum model length|max_model_len|too large|longer than|too long", re.IGNORECASE)


class Spoken:
    """on_message que recuerda lo que ya salio, para LLMError.spoken."""

    def __init__(self, on_message: Callable[[str], None] | None):
        self.on_message = on_message
        self.parts: list[str] = []

    def __call__(self, text: str) -> None:
        self.parts.append(text)
        if self.on_message is not None:
            self.on_message(text)

    @property
    def text(self) -> str:
        return "".join(self.parts)


async def guarded(coro, deadline: float, spoken: Spoken | None = None):
    """Corre el pedido con un deadline total y traduce los errores a LLMError."""
    def said() -> str:
        return spoken.text if spoken else ""

    try:
        async with asyncio.timeout(deadline):
            return await coro
    except LLMError as e:
        e.spoken = e.spoken or said()
        raise
    except (TimeoutError, APITimeoutError) as e:
        raise LLMTimeoutError(f"el LLM no termino en {deadline:g} s", spoken=said()) from e
    except BadRequestError as e:
        cls = LLMContextError if CONTEXT_ERROR_RE.search(str(e)) else LLMError
        raise cls(f"vLLM rechazo el pedido: {e}", spoken=said()) from e
    except (APIError, ValidationError, ValueError, TypeError) as e:
        # ValueError: JSON invalido (json.JSONDecodeError); TypeError: content None.
        raise LLMError(f"{type(e).__name__}: {e}", spoken=said()) from e


def parse_turn(content: str, state: ConversationState) -> AgentTurn:
    """El JSON del turno. Si vino cortado (max_tokens) pero assistant_message esta completo,
    se usa ese mensaje como turno activo sin avance: ya se dijo por voz."""
    try:
        return AgentTurn.model_validate_json(content)
    except ValidationError:
        message = MessageExtractor()
        text = message.feed(content)
        if not message.done or not text.strip():
            raise
        logger.warning("llm: JSON del turno incompleto, se usa assistant_message %s", state.conversation_id)
        return AgentTurn(assistant_message=text, answered=False, next_objective=state.progress.asked, status="active")


class MessageExtractor:
    """Decodifica el valor de assistant_message de un JSON que llega por partes.
    feed() devuelve el texto nuevo; un escape cortado entre chunks espera al siguiente."""

    START = re.compile(r'"assistant_message"\s*:\s*"')
    ESCAPE = re.compile(r'\\(u[0-9a-fA-F]{4}|["\\/bfnrt])')

    def __init__(self):
        self.raw = ""
        self.pos: int | None = None     # proximo caracter del valor a decodificar
        self.done = False

    def feed(self, chunk: str) -> str:
        self.raw += chunk
        if self.done:
            return ""
        if self.pos is None:
            start = self.START.search(self.raw)
            if not start:
                return ""
            self.pos = start.end()
        out = []
        while self.pos < len(self.raw):
            c = self.raw[self.pos]
            if c == '"':
                self.done = True
                break
            if c == "\\":
                escape = self.ESCAPE.match(self.raw, self.pos)
                if not escape:
                    break               # escape incompleto: falta el resto
                out.append(json.loads(f'"{escape.group(0)}"'))
                self.pos = escape.end()
                continue
            out.append(c)
            self.pos += 1
        return "".join(out)


class MarkerFilter:
    """Saca una marca de un texto que llega por partes. feed() devuelve lo que
    ya se puede decir: retiene el final si puede ser el principio de la marca."""

    def __init__(self, marker: str):
        self.marker = marker
        self.pending = ""
        self.text = ""          # todo lo dicho, sin la marca
        self.found = False

    def feed(self, chunk: str) -> str:
        self.pending += chunk
        if self.marker in self.pending:
            self.found = True
            self.pending = self.pending.replace(self.marker, "")
        keep = next((n for n in range(len(self.marker) - 1, 0, -1)
                     if self.pending.endswith(self.marker[:n])), 0)
        out, self.pending = self.pending[:len(self.pending) - keep], self.pending[len(self.pending) - keep:]
        self.text += out
        return out

    def flush(self) -> str:
        out, self.pending = self.pending, ""
        self.text += out
        return out
