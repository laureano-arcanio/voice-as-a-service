import json
import re
from collections.abc import Callable

from openai import AsyncOpenAI

from app.config import settings
from app.conversation.models import AgentTurn, ConversationState, Extraction, Workflow

from .prompt import (
    END_MARKER,
    build_classic_messages,
    build_extraction_prompt,
    build_user_prompt,
    extraction_prompt,
    system_prompt,
)

TYPE_SCHEMAS = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "email": {"type": "string"},
    "email_or_phone": {"type": "string"},
    "digits": {"type": "string"},
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


# Muestreo recomendado por familia de modelo, con y sin pensamiento.
# - Qwen3.5: con pensamiento, 0.6 / 0.95 / 20; sin, 0.7 / 0.8 / 20 (desaconseja temperaturas bajas o
#   greedy con pensamiento: se repite).
# - Gemma 4: 1.0 / 0.95 / 64 en todos los casos (model card de Google, "Best practices"; 12-oct-2026).
SAMPLING = {
    "qwen": {True: {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0},
             False: {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0}},
    "gemma": {True: {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "min_p": 0.0},
              False: {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "min_p": 0.0}},
}


def sampling_family(model: str, setting: str = settings.llm_sampling) -> str:
    if setting != "auto":
        return setting
    return "gemma" if "gemma" in model.lower() else "qwen"


def request_options(thinking: bool, budget: int, temperature: float | None = None, family: str = "qwen") -> dict:
    sampling = dict(SAMPLING[family][thinking])
    if temperature is not None:
        sampling["temperature"] = temperature
    extra = {"top_k": sampling.pop("top_k"), "min_p": sampling.pop("min_p"),
             "chat_template_kwargs": {"enable_thinking": thinking}}
    if thinking:
        extra["thinking_token_budget"] = budget
    return {**sampling, "extra_body": extra}


JSON_MODES = ("json_schema", "json_object", "prompt")


def clean_json(content: str) -> str:
    """El JSON de una respuesta que lo trae entre ``` (proveedores sin salida guiada)."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


class LLMClient:
    """Cliente de chat completions (API OpenAI). profile "vllm": el servidor propio, con los
    parametros de vLLM (muestreo por familia, pensamiento, salida guiada). profile "generic": un
    proveedor externo (conexion BYOK, app/llm/resolver.py): solo temperatura, sin extras que
    rechazaria, y json_mode segun lo que soporte (json_schema | json_object | prompt)."""

    def __init__(self, base_url: str, api_key: str, model: str, thinking: bool = settings.llm_thinking,
                 thinking_budget: int = settings.llm_thinking_budget, temperature: float | None = settings.llm_temperature,
                 *, profile: str = "vllm", json_mode: str = "json_schema", default_headers: dict | None = None,
                 timeout: float = 30, label: str | None = None):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout,
                                  default_headers=default_headers, max_retries=0 if profile != "vllm" else 2)
        self.model = model
        self.profile = profile
        self.json_mode = json_mode if json_mode in JSON_MODES else "json_schema"
        self.label = label or ("local" if profile == "vllm" else f"{profile}:{model}")
        self.family = sampling_family(model) if profile == "vllm" else "generic"
        self.temperature = temperature
        if profile == "vllm":
            self.options = request_options(thinking, thinking_budget, temperature, self.family)
        else:
            self.options = {} if temperature is None else {"temperature": temperature}
        # OpenAI pide max_completion_tokens (los modelos con razonamiento rechazan max_tokens).
        self._tokens_param = "max_completion_tokens" if "api.openai.com" in base_url else "max_tokens"

    def _guided(self, messages: list[dict], name: str, schema: dict) -> tuple[list[dict], dict]:
        """Mensajes y parametros para pedir `schema` segun json_mode."""
        if self.json_mode == "json_schema":
            return messages, {"response_format": {"type": "json_schema",
                                                  "json_schema": {"name": name, "schema": schema, "strict": True}}}
        note = ("Respondé únicamente con un objeto JSON válido, sin texto antes ni después y sin ```, "
                "que cumpla este JSON Schema:\n" + json.dumps(schema, ensure_ascii=False))
        if messages and messages[0]["role"] == "system":
            messages = [{**messages[0], "content": f"{messages[0]['content']}\n\n{note}"}, *messages[1:]]
        else:
            messages = [{"role": "system", "content": note}, *messages]
        return messages, ({"response_format": {"type": "json_object"}} if self.json_mode == "json_object" else {})

    async def process_turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                           on_message: Callable[[str], None] | None = None) -> AgentTurn:
        """Con on_message, pide el JSON en streaming y le pasa assistant_message
        a medida que llega, antes de que termine el resto del JSON."""
        messages, guided = self._guided(
            [{"role": "system", "content": system_prompt(state.channel)},
             {"role": "user", "content": build_user_prompt(workflow, state, user_message)}],
            "agent_turn", turn_schema(workflow))
        request = dict(model=self.model, messages=messages, **guided, **self.options)
        if on_message is None:
            message = (await self.client.chat.completions.create(**request)).choices[0].message
            content = message.content
            # vLLM separa el razonamiento (--reasoning-parser qwen3).
            reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        else:
            content, reasoning = await self._stream(request, on_message)
        turn = AgentTurn.model_validate_json(clean_json(content))
        turn.raw = content
        turn.reasoning = reasoning
        return turn

    async def converse(self, workflow: Workflow, state: ConversationState, user_message: str,
                       on_message: Callable[[str], None] | None = None) -> AgentTurn:
        """Motor clasico: texto libre con la conversacion como mensajes. El fin
        lo marca END_MARKER, que se saca antes de decirlo."""
        request = dict(model=self.model, messages=build_classic_messages(workflow, state, user_message), **self.options)
        marker = MarkerFilter(END_MARKER)
        if on_message is None:
            message = (await self.client.chat.completions.create(**request)).choices[0].message
            content = message.content or ""
            reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
            marker.feed(content)
            marker.flush()
        else:
            parts, reasoning_parts = [], []
            async for chunk in await self.client.chat.completions.create(**request, stream=True):
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if text := getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None):
                    reasoning_parts.append(text)
                if delta.content:
                    parts.append(delta.content)
                    if text := marker.feed(delta.content):
                        on_message(text)
            if text := marker.flush():
                on_message(text)
            content, reasoning = "".join(parts), "".join(reasoning_parts) or None
        return AgentTurn(assistant_message=marker.text.strip(), status="completed" if marker.found else "active",
                         raw=content, reasoning=reasoning)

    async def extract(self, workflow: Workflow, state: ConversationState, only: list[str] | None = None) -> Extraction:
        """Los datos del usuario segun toda la conversacion (only: solo esos campos)."""
        messages, guided = self._guided(
            [{"role": "system", "content": extraction_prompt(state.channel)},
             {"role": "user", "content": build_extraction_prompt(workflow, state, only)}],
            "extraction", extraction_schema(workflow, only))
        message = (await self.client.chat.completions.create(
            model=self.model, messages=messages, **guided, **self.options)).choices[0].message
        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        content = clean_json(message.content or "")
        return Extraction(fields=json.loads(content), raw=content, reasoning=reasoning)

    async def structured(self, messages: list[dict], schema: dict, name: str = "step",
                         thinking: bool | None = None, budget: int | None = None,
                         max_tokens: int | None = None) -> tuple[str, str | None]:
        """Un pedido con salida JSON guiada (motor assistant, app/conversation/assistant.py).
        Devuelve el JSON tal cual y el razonamiento. thinking: pisa el del cliente (LLM_THINKING) para
        este pedido; vLLM aplica el esquema despues del razonamiento (probado con Gemma 4)."""
        if self.profile != "vllm" or thinking is None:
            options = self.options
        else:
            options = request_options(thinking, budget or settings.llm_thinking_budget, self.temperature, self.family)
        messages, guided = self._guided(messages, name, schema)
        limit = {} if max_tokens is None else {self._tokens_param: max_tokens}
        message = (await self.client.chat.completions.create(
            model=self.model, messages=messages, **guided, **limit,
            timeout=90 if thinking and self.profile == "vllm" else None,
            **options,
        )).choices[0].message
        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        content = message.content or ""
        return (content if self.json_mode == "json_schema" else clean_json(content)), reasoning

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
