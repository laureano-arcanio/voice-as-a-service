"""Catalogo de parametros de generacion del LLM (docs/BYOK_LLM_PLAN.md, "Parametros de generacion").

Cada agente define un `generation` (Workflow.generation) con un mapa `parametro -> valor`, y cada
etapa de `Workflow.llm` lo puede pisar (`LlmStage.generation`). Los parametros son los del
proveedor: se agregan y quitan desde la UI, que arma la lista segun el proveedor elegido
(`for_provider`). En runtime, el proveedor activo solo manda los que soporta; los demas se
descartan (asi una misma definicion sirve para local, OpenAI, OpenRouter o Anthropic).

Un valor `None` no se manda (equivale a "el default del proveedor").
"""
from dataclasses import dataclass

VLLM = "vllm"
OPENAI = "openai_compatible"
OPENROUTER = "openrouter"
ANTHROPIC = "anthropic"

PROVIDER_LABELS = {
    VLLM: "Servidor propio (local)",
    OPENAI: "OpenAI compatible",
    OPENROUTER: "OpenRouter",
    ANTHROPIC: "Anthropic",
}


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    # number | int | bool | choice
    type: str
    providers: tuple[str, ...]
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    # Ayuda para la UI (que significa y donde aplica).
    hint: str = ""


# El orden define el que ve la UI al agregar un parametro.
CATALOG: dict[str, Param] = {
    p.name: p for p in (
        Param("temperature", "Temperatura", "number", (VLLM, OPENAI, OPENROUTER, ANTHROPIC),
              minimum=0, maximum=2,
              hint="Más alta, respuestas más variadas; más baja, más previsibles."),
        Param("top_p", "Top P (núcleo)", "number", (VLLM, OPENAI, OPENROUTER, ANTHROPIC),
              minimum=0, maximum=1,
              hint="Elige solo entre las palabras más probables que suman P."),
        Param("top_k", "Top K", "int", (VLLM,), minimum=0,
              hint="Cuántas palabras candidatas mira en cada paso."),
        Param("min_p", "Min P", "number", (VLLM,), minimum=0, maximum=1,
              hint="Descarta las palabras con probabilidad menor a esta."),
        Param("max_tokens", "Máximo de tokens de salida", "int",
              (VLLM, OPENAI, OPENROUTER, ANTHROPIC), minimum=1,
              hint="Tope de lo que genera cada respuesta. Anthropic usa un piso de 2048."),
        Param("enable_thinking", "Razonamiento", "bool", (VLLM,),
              hint="Piensa antes de contestar: mejor en tareas complejas, más lento. En voz viene apagado."),
        Param("thinking_token_budget", "Tope de razonamiento (tokens)", "int", (VLLM,), minimum=0,
              hint="Al llegar a este tope corta el razonamiento y contesta."),
        Param("reasoning_effort", "Esfuerzo de razonamiento", "choice", (OPENAI, OPENROUTER),
              choices=("low", "medium", "high"),
              hint="Para modelos con razonamiento (gpt-5/o-series y equivalentes)."),
        Param("effort", "Esfuerzo", "choice", (ANTHROPIC,), choices=("low", "medium", "high"),
              hint="Anthropic no permite apagarlo: low, medium o high."),
    )
}


def for_provider(kind: str) -> list[Param]:
    """Los parametros que ofrece ese proveedor, en el orden del catalogo."""
    return [p for p in CATALOG.values() if kind in p.providers]


def _coerce(spec: Param, value):
    if value is None:
        return None
    if spec.type == "bool":
        if isinstance(value, bool):
            return value
        raise ValueError(f"{spec.name}: tiene que ser si o no")
    if spec.type == "choice":
        if not isinstance(value, str) or value not in spec.choices:
            raise ValueError(f"{spec.name}: tiene que ser uno de {', '.join(spec.choices)}")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{spec.name}: tiene que ser un numero")
    number = float(value) if spec.type == "number" else int(value)
    if spec.type == "int" and number != value:
        raise ValueError(f"{spec.name}: tiene que ser un entero")
    if spec.minimum is not None and number < spec.minimum:
        raise ValueError(f"{spec.name}: no puede ser menor que {spec.minimum:g}")
    if spec.maximum is not None and number > spec.maximum:
        raise ValueError(f"{spec.name}: no puede ser mayor que {spec.maximum:g}")
    return number


def validate_params(params: dict) -> dict:
    """Valida nombres, tipos y rangos. Devuelve el mapa normalizado. ValueError con el detalle."""
    if not isinstance(params, dict):
        raise ValueError("generation: tiene que ser un objeto de parametro -> valor")
    out: dict = {}
    for name, value in params.items():
        spec = CATALOG.get(name)
        if spec is None:
            raise ValueError(f"generation.{name}: parametro desconocido")
        coerced = _coerce(spec, value)
        if coerced is not None:
            out[name] = coerced
    return out


def merge(*layers: dict | None) -> dict:
    """Junta capas de parametros (base -> agente -> etapa); la ultima gana. Sin valores None."""
    out: dict = {}
    for layer in layers:
        for name, value in (layer or {}).items():
            if value is not None:
                out[name] = value
    return out
