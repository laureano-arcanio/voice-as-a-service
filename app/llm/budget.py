"""Presupuesto de tokens de cada pedido al LLM (H11): prompt de sistema + definicion +
historial + mensaje nuevo + max_tokens + margen <= LLM_CONTEXT_TOKENS (16384 con Gemma).
Pasado eso vLLM responde 400 y el turno se pierde: se sacan los mensajes mas viejos.

Sin el tokenizer del modelo (la app no lo tiene y no descarga nada): se estima por
caracteres, y LLM_CONTEXT_MARGIN_TOKENS cubre el error de la estimacion."""
import math

from app.config import settings

from .errors import LLMContextError

# Texto en castellano con Qwen y Gemma: ~3,5-4 caracteres por token; 3,5 sobreestima.
CHARS_PER_TOKEN = 3.5
# Tokens de plantilla de chat por mensaje (rol y separadores).
MESSAGE_OVERHEAD = 4
# Los mensajes viejos salen de a bloques: el corte se mueve cada varios turnos y no en
# cada uno, asi vLLM sigue reusando el prefijo (prefix caching) entre cortes. Par, para
# no cambiar la alternancia agente/usuario del historial.
DROP_CHUNK = 8
# Lo minimo que la definicion de un agente tiene que dejar libre para la conversacion
# (~100 mensajes de voz o ~7 de WhatsApp de 2000 caracteres).
MIN_CONVERSATION_TOKENS = 4096


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def message_tokens(text: str) -> int:
    return estimate_tokens(text) + MESSAGE_OVERHEAD


def thinking_tokens(thinking: bool | None = None, thinking_budget: int | None = None) -> int:
    """Con pensamiento, vLLM cuenta el razonamiento dentro de max_tokens."""
    thinking = settings.llm_thinking if thinking is None else thinking
    return (settings.llm_thinking_budget if thinking_budget is None else thinking_budget) if thinking else 0


def max_tokens_reply(reasoning: int | None = None) -> int:
    """max_tokens de un turno; reasoning: tokens de pensamiento (default: los de settings)."""
    return settings.llm_max_tokens_reply + (thinking_tokens() if reasoning is None else reasoning)


def max_tokens_extract(reasoning: int | None = None) -> int:
    return settings.llm_max_tokens_extract + (thinking_tokens() if reasoning is None else reasoning)


def prompt_limit(max_tokens: int) -> int:
    """Tokens de entrada disponibles con esa salida."""
    return settings.llm_context_tokens - max_tokens - settings.llm_context_margin_tokens


def definition_limit() -> int:
    """Tope de la parte fija del prompt (sistema + definicion del agente): deja lugar a la
    salida mas larga y a MIN_CONVERSATION_TOKENS de conversacion."""
    return prompt_limit(max(max_tokens_reply(), max_tokens_extract())) - MIN_CONVERSATION_TOKENS


def drop_count(fixed: int, history: list[int], limit: int) -> int:
    """Cuantos mensajes viejos del historial sacar (de a DROP_CHUNK) para que
    fixed + sum(historia restante) <= limit. fixed: sistema, definicion y mensaje nuevo;
    history: tokens de cada mensaje, del mas viejo al mas nuevo.
    LLMContextError si ni sin historial entra."""
    if fixed > limit:
        raise LLMContextError(f"el prompt sin historial ocupa ~{fixed} tokens y el limite es {limit}")
    total, drop = fixed + sum(history), 0
    while total > limit and drop < len(history):
        step = history[drop:drop + DROP_CHUNK]
        total -= sum(step)
        drop += len(step)
    return drop


def omitted_note(n: int) -> str:
    return f"[Se omitieron los {n} mensajes más viejos de la conversación por longitud.]"
