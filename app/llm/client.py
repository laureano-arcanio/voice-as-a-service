import json
from collections.abc import Callable
from typing import TYPE_CHECKING

from openai import AsyncOpenAI, BadRequestError

from app.config import settings
from app.conversation.models import (
    AgentTurn,
    ConversationState,
    Extraction,
    Generation,
    Workflow,
)

from . import platform_tools
from .prompt import build_turn_messages, build_extraction_prompt, extraction_prompt

if TYPE_CHECKING:
    from app.tools.conversation import TurnTools

TYPE_SCHEMAS = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "boolean": {"type": "boolean"},
    "email": {"type": "string"},
    "email_or_phone": {"type": "string"},
    "digits": {"type": "string"},
    "phone": {"type": "string"},
}


def field_schema(spec) -> dict:
    base = {"type": "string", "enum": spec.options} if spec.type == "choice" else TYPE_SCHEMAS[spec.type]
    return {"anyOf": [base, {"type": "null"}]}


def extraction_schema(workflow: Workflow) -> dict:
    names = [n for n, _ in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)]
    return {
        "type": "object",
        "properties": {n: field_schema(workflow.fields[n]) for n in names},
        "required": names,
        "additionalProperties": False,
    }


# Servidores (base_url) que rechazaron stream_options: se les pide sin usage (los tokens quedan en 0).
_NO_STREAM_USAGE: set[str] = set()


def usage_of(usage) -> tuple[int, int]:
    """(entrada, salida) del `usage` de una respuesta; (0, 0) si el proveedor no lo da."""
    if usage is None:
        return 0, 0
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0)


def local_sampling() -> dict:
    """El muestreo del LLM propio: el de la configuracion del modelo (LLM_TEMPERATURE, LLM_TOP_P, LLM_TOP_K,
    LLM_MIN_P en el .env o el override del modelo). Lo que no esta definido no se manda: rige el del servidor
    (vLLM toma el generation_config del modelo)."""
    out = {k: v for k, v in (("temperature", settings.llm_temperature), ("top_p", settings.llm_top_p),
                             ("top_k", settings.llm_top_k), ("min_p", settings.llm_min_p)) if v is not None}
    return out


class LLMClient:
    """Cliente de chat completions (API OpenAI). profile "vllm": el servidor propio, con el muestreo y el
    razonamiento de la configuracion. Otro profile: un proveedor externo (conexion BYOK, app/llm/resolver.py),
    solo con lo que pide la generacion del agente. La salida JSON es siempre guiada (json_schema): un proveedor
    que no la soporta no sirve (se rechaza al probar la conexion)."""

    def __init__(self, base_url: str, api_key: str, model: str, thinking: bool = settings.llm_thinking,
                 thinking_budget: int = settings.llm_thinking_budget, *, profile: str = "vllm",
                 default_headers: dict | None = None, timeout: float = 30, label: str | None = None,
                 generation: Generation | None = None, max_tokens: int | None = None):
        self._base_url, self._api_key = base_url, api_key
        self._default_headers, self._timeout = default_headers, timeout
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout,
                                  default_headers=default_headers, max_retries=0 if profile != "vllm" else 2)
        self.model = model
        self.profile = profile
        self.label = label or ("local" if profile == "vllm" else f"{profile}:{model}")
        self.thinking = thinking
        self.thinking_budget = thinking_budget
        self.max_tokens = max_tokens
        # Parametros del agente/etapa (app/llm/params.py); pisan a los de la plataforma.
        self.generation = generation.params if generation else {}
        self.options = self._options()
        # OpenAI pide max_completion_tokens (los modelos con razonamiento rechazan max_tokens).
        self._tokens_param = "max_completion_tokens" if "api.openai.com" in base_url else "max_tokens"

    def _options(self, thinking: bool | None = None, budget: int | None = None) -> dict:
        """Los parametros del pedido: la generacion del agente/etapa pisa los de la plataforma. En el perfil vllm,
        top_k, min_p y el razonamiento van en extra_body (chat_template_kwargs.enable_thinking)."""
        gen = self.generation
        if self.profile != "vllm":
            return {k: gen[k] for k in ("temperature", "top_p", "reasoning_effort") if k in gen}
        sampling = {**local_sampling(), **{k: gen[k] for k in ("temperature", "top_p", "top_k", "min_p") if k in gen}}
        extra = {k: sampling.pop(k) for k in ("top_k", "min_p") if k in sampling}
        thinking = bool(gen.get("enable_thinking", self.thinking if thinking is None else thinking))
        extra["chat_template_kwargs"] = {"enable_thinking": thinking}
        if thinking:
            extra["thinking_token_budget"] = gen.get("thinking_token_budget",
                                                     self.thinking_budget if budget is None else budget)
        return {**sampling, "extra_body": extra}

    def _limit(self, max_tokens: int | None = None) -> dict:
        """Tope de tokens de salida: la generacion pisa el de la llamada y el de la plataforma."""
        cap = self.generation.get("max_tokens", self.max_tokens if max_tokens is None else max_tokens)
        return {} if cap is None else {self._tokens_param: cap}

    def derive(self, *, generation=None, thinking: bool | None = None,
               thinking_budget: int | None = None, max_tokens: int | None = None) -> "LLMClient":
        """Otro cliente sobre la misma conexion, con los parametros del agente/etapa (app/llm/resolver.py)."""
        return LLMClient(
            self._base_url, self._api_key, self.model,
            thinking=self.thinking if thinking is None else thinking,
            thinking_budget=self.thinking_budget if thinking_budget is None else thinking_budget,
            profile=self.profile, default_headers=self._default_headers,
            timeout=self._timeout, label=self.label, generation=generation, max_tokens=max_tokens)

    @staticmethod
    def _guided(name: str, schema: dict) -> dict:
        return {"response_format": {"type": "json_schema",
                                    "json_schema": {"name": name, "schema": schema, "strict": True}}}

    async def converse(self, workflow: Workflow, state: ConversationState, user_message: str,
                       on_message: Callable[[str], None] | None = None, tools: "TurnTools | None" = None) -> AgentTurn:
        """Un turno: texto libre con la conversacion como mensajes, y function calling con las herramientas de la
        plataforma (end_call, transfer_call; app/llm/platform_tools.py) y las del cliente (tools). Las del cliente
        se ejecutan y se le vuelve a preguntar con el resultado, hasta tools.max_rounds vueltas; al llegar, el
        turno termina con tool_settings.limit_message."""
        messages = build_turn_messages(workflow, state, user_message)
        definitions = platform_tools.tools_for(state) + (tools.openai_tools() if tools else [])
        turn = AgentTurn(assistant_message="")
        said, raw, reasoning = [], [], []
        rounds = 0
        while True:
            request = dict(model=self.model, messages=messages, tools=definitions, tool_choice="auto",
                           **self._limit(), **self.options)
            content, thought, calls, (tokens_in, tokens_out) = await self._converse_once(request, on_message)
            turn.input_tokens += tokens_in
            turn.output_tokens += tokens_out
            said.append(content)
            raw.append(content)
            if thought:
                reasoning.append(thought)
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
                messages.append({"role": "assistant", "content": content or None, "tool_calls": [
                    {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in customer]})
                for call_id, result in await tools.execute(customer, on_message, spoke=bool(content.strip())):
                    messages.append({"role": "tool", "tool_call_id": call_id, "content": result})
            platform_tools.apply(turn, calls, state)
            if not customer or turn.status == "completed" or turn.handoff:
                break
        turn.assistant_message = " ".join(t.strip() for t in said if t.strip())
        turn.raw = "\n".join(r for r in raw if r)
        turn.reasoning = "".join(reasoning) or None
        return turn

    async def _stream(self, request: dict):
        """El pedido en streaming, con el usage en el ultimo chunk (stream_options) si el servidor lo acepta."""
        if self._base_url in _NO_STREAM_USAGE:
            return await self.client.chat.completions.create(**request, stream=True)
        try:
            return await self.client.chat.completions.create(**request, stream=True,
                                                             stream_options={"include_usage": True})
        except BadRequestError as e:
            if "stream_options" not in str(e):
                raise
            _NO_STREAM_USAGE.add(self._base_url)
            return await self.client.chat.completions.create(**request, stream=True)

    async def _converse_once(self, request: dict, on_message: Callable[[str], None] | None
                             ) -> tuple[str, str | None, list[dict], tuple[int, int]]:
        """Un pedido: el texto (ya pasado al TTS en streaming), el razonamiento, las herramientas que pidio el
        modelo [{id, name, arguments}] y los tokens (entrada, salida)."""
        if on_message is None:
            response = await self.client.chat.completions.create(**request)
            message = response.choices[0].message
            reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
            calls = [{"id": c.id or f"call_{i}", "name": c.function.name, "arguments": c.function.arguments or "{}"}
                     for i, c in enumerate(getattr(message, "tool_calls", None) or [])]
            return message.content or "", reasoning, calls, usage_of(getattr(response, "usage", None))
        parts, reasoning_parts = [], []
        pending: dict[int, dict] = {}
        usage = (0, 0)
        async for chunk in await self._stream(request):
            if getattr(chunk, "usage", None) is not None:
                usage = usage_of(chunk.usage)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if text := getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None):
                reasoning_parts.append(text)
            if delta.content:
                parts.append(delta.content)
                on_message(delta.content)
            for tc in getattr(delta, "tool_calls", None) or []:
                slot = pending.setdefault(tc.index if tc.index is not None else len(pending),
                                          {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function is not None:
                    slot["name"] += tc.function.name or ""
                    slot["arguments"] += tc.function.arguments or ""
        calls = [{**c, "id": c["id"] or f"call_{i}", "arguments": c["arguments"] or "{}"}
                 for i, c in sorted(pending.items()) if c["name"]]
        return "".join(parts), "".join(reasoning_parts) or None, calls, usage

    async def extract(self, workflow: Workflow, state: ConversationState) -> Extraction:
        """Los datos del usuario segun toda la conversacion."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": extraction_prompt(state.channel)},
                      {"role": "user", "content": build_extraction_prompt(workflow, state)}],
            **self._guided("extraction", extraction_schema(workflow)), **self._limit(), **self.options)
        message = response.choices[0].message
        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        content = message.content or ""
        tokens_in, tokens_out = usage_of(getattr(response, "usage", None))
        return Extraction(fields=json.loads(content), raw=content, reasoning=reasoning,
                          input_tokens=tokens_in, output_tokens=tokens_out)

    async def structured(self, messages: list[dict], schema: dict, name: str = "step",
                         thinking: bool | None = None, budget: int | None = None,
                         max_tokens: int | None = None) -> tuple[str, str | None]:
        """Un pedido con salida JSON guiada (resumen de una derivacion, prueba de una conexion). Devuelve el JSON
        y el razonamiento. thinking: pisa el del cliente para este pedido."""
        message = (await self.client.chat.completions.create(
            model=self.model, messages=messages, **self._guided(name, schema), **self._limit(max_tokens),
            **self._options(thinking=thinking, budget=budget))).choices[0].message
        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        return message.content or "", reasoning
