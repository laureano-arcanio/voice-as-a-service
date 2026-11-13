"""Variables dinámicas de una conversación: `{{nombre}}` en el prompt, el primer mensaje, el análisis, los mensajes
de derivación y las herramientas (docs/ARQUITECTURA.md, "Definición de un agente").

Un espacio por conversación en `progress.variables` (plano: texto, número o booleano), con `hidden_variables`
(van a herramientas, nunca al LLM) y `variable_sources` (quién escribió cada una). Fuentes, de menor a mayor:
`default` de la definición < `contact` (agenda o columnas de la campaña) < `request` (pedido de la API o del
panel) < `pre_call:<slug>` < `tool:<slug>`. Una de menor prioridad no pisa a una de mayor; una herramienta en la
conversación siempre pisa. Las del sistema (`call.*`, `channel`, `agent.*`, `today`, `now`) no se guardan ni se
pisan: se calculan de `progress.call` y la hora de inicio."""
import datetime
import json
import re
import unicodedata
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from ..config import settings

if TYPE_CHECKING:
    from .models import ConversationState, Workflow

NAME_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"
NAME_RE = re.compile(NAME_PATTERN)
RESERVED = ("channel", "today", "now")
RESERVED_PREFIXES = ("call.", "agent.", "secrets.", "fields.")
MAX_VARIABLES = 30
MAX_VALUE_CHARS = 2000
MAX_DESCRIPTION_CHARS = 300
# Las de la derivación las pone services/handoff.py en sus mensajes: no son variables de la conversación.
HANDOFF_VARIABLES = ("area", "persona", "cliente", "resumen", "horario")

WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
VAR_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
# Nunca van al LLM: se rechazan al guardar en prompt, first_message y analysis.
LLM_FORBIDDEN_RE = re.compile(r"\{\{\s*(secrets\.[^{}]*|fields\.[^{}]*|call\.summary)\s*\}\}")

_ALL = ["prompt", "first_message", "analysis", "handoff", "tool"]
# Catálogo (GET /variables/catalog): fuente única para la UI, el MCP y los docs.
SYSTEM_VARIABLES: list[dict] = [
    {"name": "call.from", "description": "Número que llama (entrante) o el nuestro (saliente)",
     "example": "+5491155550000", "applies_to": _ALL},
    {"name": "call.to", "description": "Número llamado: el nuestro (entrante) o el de la persona (saliente)",
     "example": "+541152630000", "applies_to": _ALL},
    {"name": "call.phone", "description": "Número de la otra punta", "example": "+5491155550000", "applies_to": _ALL},
    {"name": "call.direction", "description": "inbound (entrante) u outbound (saliente)", "example": "inbound",
     "applies_to": _ALL},
    {"name": "call.mode", "description": "Tipo de conversación: entrante, saliente, web, whatsapp…",
     "example": "saliente", "applies_to": _ALL},
    {"name": "call.id", "description": "Id de la conversación", "example": "6f1c…", "applies_to": _ALL},
    {"name": "channel", "description": "Canal: voice o whatsapp", "example": "voice", "applies_to": _ALL},
    {"name": "today", "description": "Fecha de inicio de la conversación (AGENT_TIMEZONE)",
     "example": "jueves 2026-11-12", "applies_to": _ALL},
    {"name": "now", "description": "Fecha y hora de inicio de la conversación (AGENT_TIMEZONE)",
     "example": "jueves 2026-11-12 14:03", "applies_to": _ALL},
    {"name": "agent.slug", "description": "Slug del agente", "example": "sofia_atencion", "applies_to": _ALL},
    {"name": "agent.version", "description": "Versión del agente", "example": "7", "applies_to": _ALL},
    {"name": "call.summary", "description": "Resumen del análisis (post-call)", "example": "Pidió una demo…",
     "applies_to": ["tool"]},
    {"name": "fields.<campo>", "description": "Dato del análisis", "example": "true", "applies_to": ["tool"]},
    {"name": "secrets.<NOMBRE>", "description": "Secreto de la cuenta o del agente", "example": "•••",
     "applies_to": ["tool"]},
    {"name": "area", "description": "Área a la que se deriva", "example": "Ventas", "applies_to": ["handoff"]},
    {"name": "persona", "description": "Persona del equipo que atiende", "example": "Ana", "applies_to": ["handoff"]},
    {"name": "cliente", "description": "Número de quien llama o escribe", "example": "+5491155550000",
     "applies_to": ["handoff"]},
    {"name": "resumen", "description": "Resumen de lo hablado antes de derivar", "example": "Quiere cambiar el plan",
     "applies_to": ["handoff"]},
    {"name": "horario", "description": "Horario de atención del área", "example": "de lunes a viernes de 9 a 18",
     "applies_to": ["handoff"]},
]


def catalog() -> dict:
    return {"name_pattern": NAME_PATTERN, "reserved": list(RESERVED), "reserved_prefixes": list(RESERVED_PREFIXES),
            "limits": {"max_variables": MAX_VARIABLES, "max_value_chars": MAX_VALUE_CHARS},
            "system": SYSTEM_VARIABLES}


def key(name: str) -> str:
    """Nombre comparable de un dato del contacto: sin acentos ni mayusculas, con _ ("Fecha Vence" -> fecha_vence)."""
    text = unicodedata.normalize("NFD", str(name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")[:64]


def fmt(value: Any) -> str:
    """El valor como texto, en una linea. Vacio para None."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "sí" if value else "no"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\s+", " ", str(value)).strip()


# ---------- validación ----------

def name_error(name: str) -> str | None:
    """Por qué `name` no sirve como variable de usuario, o None."""
    if isinstance(name, str) and (name in RESERVED or name.startswith(RESERVED_PREFIXES)):
        return f"{name} es una variable del sistema"
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        return "usar minúsculas, números y _ y empezar con una letra (hasta 64)"
    return None


def value_error(value: Any) -> str | None:
    if isinstance(value, (dict, list, tuple, set)):
        return "el valor tiene que ser texto, número o booleano"
    if isinstance(value, str) and len(value) > MAX_VALUE_CHARS:
        return f"el valor pasa de {MAX_VALUE_CHARS} caracteres"
    return None


def check_request(values: Any, path: str = "variables") -> tuple[dict, list[dict]]:
    """Las `variables` de un pedido (POST /calls, POST /conversations): (limpias, errores [{path, message}]).
    Un `null` se ignora."""
    if values is None:
        return {}, []
    if not isinstance(values, dict):
        return {}, [{"path": path, "message": "tiene que ser un objeto plano {nombre: valor}"}]
    clean, errors = {}, []
    for name, value in values.items():
        if value is None:
            continue
        if (msg := name_error(name)) or (msg := value_error(value)):
            errors.append({"path": f"{path}.{name}", "message": msg})
            continue
        clean[name] = value
    if len(clean) > MAX_VARIABLES:
        errors.append({"path": path, "message": f"hasta {MAX_VARIABLES} variables"})
    return clean, errors


def forbidden_in_llm_text(text: str) -> str | None:
    """La primera `{{secrets.X}}`, `{{fields.x}}` o `{{call.summary}}` del texto: nunca van al LLM."""
    m = LLM_FORBIDDEN_RE.search(text or "")
    return m.group(0) if m else None


def used(text: str) -> list[str]:
    """Los nombres de `{{x}}` del texto, en orden y sin repetir."""
    return list(dict.fromkeys(m.strip() for m in VAR_RE.findall(text or "")))


# ---------- el espacio de la conversación ----------

_RANK = {"default": 0, "system": 0, "contact": 1, "request": 2, "pre_call": 3, "tool": 4}


def _rank(source: str) -> int:
    return _RANK.get(source.split(":", 1)[0], 0)


def _scalar(value: Any) -> Any:
    """El valor plano: los objetos de una herramienta quedan como JSON; el texto, recortado al tope."""
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        value = value[:MAX_VALUE_CHARS]
    return value


def merge(state: "ConversationState", values: dict | None, source: str, hidden: set[str] | None = None) -> None:
    """Suma `values` al espacio con su fuente. Ignora las del sistema, los nombres inválidos y los `null`; una
    fuente de menor prioridad no pisa a una mayor (`tool:` siempre pisa). Con `contact` el nombre se normaliza
    como los datos del contacto (sin acentos ni mayúsculas, `params` afuera)."""
    p = state.progress
    hidden = hidden or set()
    for raw, value in (values or {}).items():
        if value is None:
            continue
        if source == "contact":
            if raw == "params":         # valores posicionales de una plantilla de WhatsApp
                continue
            name = key(raw)
        else:
            name = raw
        if name_error(name):
            continue
        current = p.variable_sources.get(name)
        if current is not None and not source.startswith("tool:") and _rank(source) < _rank(current):
            continue
        if name not in p.variables and len(p.variables) >= MAX_VARIABLES:
            continue
        p.variables[name] = _scalar(value)
        p.variable_sources[name] = source
        if raw in hidden or name in hidden:
            if name not in p.hidden_variables:
                p.hidden_variables.append(name)
        elif name in p.hidden_variables:
            p.hidden_variables.remove(name)


# Los datos de la llamada que se guardan en progress.call (los de {{call.*}}, salvo summary).
CALL_KEYS = ("id", "from", "to", "phone", "direction", "mode")
# Las fuentes que trae quien crea la conversacion, en orden de prioridad.
START_SOURCES = ("contact", "request")


def start(state: "ConversationState", workflow: "Workflow", values: dict[str, dict] | None = None,
          call: dict | None = None) -> None:
    """El espacio al crear la conversacion: los `default` de la definicion y los valores por fuente (`contact`,
    `request`; ValueError con otra). `call`: from, to, phone, direction y mode de la llamada; el id es el de la
    conversacion."""
    p = state.progress
    p.started_at = datetime.datetime.now(ZoneInfo(settings.agent_timezone)).isoformat(timespec="seconds")
    from .workflow import normalize_phone
    call = {k: v for k, v in (call or {}).items() if k in CALL_KEYS and k != "id" and v not in (None, "")}
    for k in ("from", "to", "phone"):     # sin separadores; un numero que no es numero (anonymous) no va
        if isinstance(call.get(k), str):
            if not (number := normalize_phone(call[k])):
                del call[k]
            else:
                call[k] = number
    p.call = {"id": state.conversation_id, **call}
    merge(state, {n: v.default for n, v in workflow.variable_specs.items()}, "default")
    if unknown := set(values or {}) - set(START_SOURCES):
        raise ValueError(f"fuentes desconocidas: {', '.join(sorted(unknown))}")
    for source in START_SOURCES:
        if (values or {}).get(source):
            merge(state, values[source], source)


def visible(state: "ConversationState") -> dict[str, Any]:
    """Las variables de usuario sin las ocultas: lo que puede ver el LLM."""
    hidden = set(state.progress.hidden_variables)
    return {k: v for k, v in state.progress.variables.items() if k not in hidden}


def message_values(state: "ConversationState | None", workflow: "Workflow | None" = None) -> dict[str, Any]:
    """Para los mensajes de la derivacion y las plantillas al equipo: todas (las ocultas tambien, como la ficha
    para el operador: no pasan por el LLM) y las del sistema."""
    if state is None:
        return {}
    return {**state.progress.variables, **system_values(state, workflow)}


def _started(state: "ConversationState") -> datetime.datetime:
    tz = ZoneInfo(settings.agent_timezone)
    if state.progress.started_at:
        try:
            return datetime.datetime.fromisoformat(state.progress.started_at).astimezone(tz)
        except ValueError:
            pass
    return datetime.datetime.now(tz)


def system_values(state: "ConversationState", workflow: "Workflow | None" = None) -> dict[str, Any]:
    """Las del sistema: de `progress.call`, el canal, el agente y la hora de inicio."""
    call = state.progress.call or {}
    caller = state.progress.caller_phone     # prueba por texto con número simulado
    started = _started(state)
    day = WEEKDAYS[started.weekday()]
    out = {"call.id": call.get("id") or state.conversation_id,
           "call.from": call.get("from") or caller, "call.to": call.get("to"),
           "call.phone": call.get("phone") or caller, "call.direction": call.get("direction"),
           "call.mode": call.get("mode"), "channel": state.channel,
           "agent.slug": workflow.id if workflow is not None else None, "agent.version": state.agent_version,
           "today": f"{day} {started:%Y-%m-%d}", "now": f"{day} {started:%Y-%m-%d %H:%M}"}
    return {k: v for k, v in out.items() if v not in (None, "")}


def render(text: str, state: "ConversationState | None", workflow: "Workflow | None" = None) -> str:
    """Cambia cada `{{x}}` por su valor, en una pasada (un valor que trae `{{y}}` no se vuelve a renderizar):
    primero las del sistema, después las visibles (sin acentos ni mayúsculas, como los datos del contacto). Las
    ocultas, `secrets.*`, `fields.*` y las que no tienen valor quedan vacías y el texto se acomoda. Sin estado,
    el texto como está."""
    if state is None or "{{" not in (text or ""):
        return text
    system = system_values(state, workflow)
    user = visible(state)
    by_key = {key(k): v for k, v in user.items()}
    missing = False

    def swap(m: re.Match) -> str:
        nonlocal missing
        name = m.group(1).strip()
        if name in system:
            value = fmt(system[name])
        elif name in user:
            value = fmt(user[name])
        elif "." not in name and key(name) in by_key:
            value = fmt(by_key[key(name)])
        else:
            value = ""
        missing = missing or not value
        return value

    out = VAR_RE.sub(swap, text)
    if missing:
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"[ \t]+([,.;:!?)])", r"\1", out).strip()
    return out


def detail(state: "ConversationState", workflow: "Workflow | None" = None) -> list[dict]:
    """Para el detalle de la conversación: las de usuario con su fuente (las ocultas enmascaradas), primero las
    declaradas en su orden y después las demás por nombre (progress.variables es jsonb: su orden no vale), y al
    final las del sistema en el orden del catálogo."""
    p = state.progress
    hidden = set(p.hidden_variables)
    declared = list(workflow.variable_specs) if workflow is not None else []
    names = [n for n in declared if n in p.variables] + sorted(n for n in p.variables if n not in declared)
    out = [{"name": n, "value": "•••" if n in hidden else p.variables[n],
            "source": p.variable_sources.get(n, "default"), **({"hidden": True} if n in hidden else {})}
           for n in names]
    system = system_values(state, workflow)
    order = [v["name"] for v in SYSTEM_VARIABLES if v["name"] in system]
    return out + [{"name": n, "value": system[n], "source": "system"} for n in order]
