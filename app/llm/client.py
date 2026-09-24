import json
import re
from collections.abc import Callable

from openai import AsyncOpenAI

from app import config

from app.conversation.models import AgentTurn, ConversationState, Extraction, Workflow

from .prompt import EXTRACTION_PROMPT, SYSTEM_PROMPT, build_extraction_prompt, build_user_prompt

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
    def __init__(self, base_url: str, api_key: str, model: str, thinking: bool = config.LLM_THINKING,
                 thinking_budget: int = config.LLM_THINKING_BUDGET, temperature: float | None = config.LLM_TEMPERATURE):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=30)
        self.model = model
        self.options = request_options(thinking, thinking_budget, temperature)

    async def process_turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                           on_message: Callable[[str], None] | None = None) -> AgentTurn:
        """Con on_message, pide el JSON en streaming y le pasa assistant_message
        a medida que llega, antes de que termine el resto del JSON."""
        request = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(workflow, state, user_message)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "agent_turn", "schema": turn_schema(workflow), "strict": True},
            },
            **self.options,
        )
        if on_message is None:
            message = (await self.client.chat.completions.create(**request)).choices[0].message
            content = message.content
            # vLLM separa el razonamiento (--reasoning-parser qwen3).
            reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        else:
            content, reasoning = await self._stream(request, on_message)
        turn = AgentTurn.model_validate_json(content)
        turn.raw = content
        turn.reasoning = reasoning
        return turn

    async def extract(self, workflow: Workflow, state: ConversationState, only: list[str] | None = None) -> Extraction:
        """Los datos del usuario segun toda la conversacion (only: solo esos campos)."""
        message = (await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": build_extraction_prompt(workflow, state, only)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": extraction_schema(workflow, only), "strict": True},
            },
            **self.options,
        )).choices[0].message
        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        return Extraction(fields=json.loads(message.content), raw=message.content, reasoning=reasoning)

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
