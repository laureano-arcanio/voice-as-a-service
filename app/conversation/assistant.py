"""Motor assistant (docs/APPS_PLAN.md): un asistente con las herramientas de las apps del cliente.

Cada paso es un pedido al LLM con salida JSON guiada: una de reply (responder y terminar el turno),
call (una herramienta, con sus argumentos segun su esquema), confirm o cancel (la accion pendiente
del turno anterior). Hasta ASSISTANT_MAX_STEPS pasos por turno. Sin tool calling nativo de vLLM:
anda con el LLM tal como esta.

Confirmacion: una herramienta destructive o send no se ejecuta cuando el LLM la pide; queda
pendiente (progress.pending) y el LLM le pregunta al usuario. En el turno siguiente, confirm
ejecuta exactamente lo pendiente (el LLM no puede cambiar los argumentos) y cancel lo descarta.
Lo pendiente vale un solo turno.

Controles de la plataforma (no dependen del prompt; vistos en las pruebas con Gemma, 12-oct-2026):
- Un *_id en los argumentos de una herramienta que escribe tiene que haber salido de un resultado
  (el LLM mandaba alumno_id 3 para dar de baja a otra persona).
- Despues de una consulta que devuelve "ambiguo": true (contrato v1.1), nada escribe en ese turno: hay
  que preguntar ("vino Juan" registraba a Juan Perez, o a los dos Juanes).
- Un link en la respuesta tiene que haber salido de una herramienta (inventaba uno), y el de una vista
  (abrir_vista, o una herramienta de la app que devuelve "view", contrato v1.3) lo pone el sistema: el
  LLM ve [[linkN]] (copiaba mal el token).
"""
import datetime
import json
import logging
import re
import time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, sessionmaker

from ..apps import tools as app_tools
from ..config import settings
from ..llm.prompt import VOICE_NOTE_TAG
from .models import AgentTurn, ConversationState, TurnMedia, Workflow

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
MAX_RESULT_CHARS = 5000
MAX_HISTORY_CHARS = 1500
MAX_PREVIOUS_RESULTS = 4000
FALLBACK = "Perdón, no pude completar eso. ¿Me lo decís de otra forma?"
DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
KIND_LABEL = {"read": "consulta", "write": "registra", "destructive": "CONFIRMAR: cambia o borra datos",
              "send": "CONFIRMAR: envía a terceros"}

# Protocolo del motor: como responder y como funcionan las herramientas, las confirmaciones y los controles
# de la plataforma. Sin nada de un negocio: quien es el asistente, su tono, sus reglas y lo que sabe vienen
# de la definicion del agente (agent, objective, conversation.rules, knowledge), que se edita en la UI.
SYSTEM = """Sos un asistente que trabaja por {canal} y resuelve los pedidos del usuario con herramientas.

En cada paso respondés un JSON con una acción:
- call: usar una herramienta (tool y arguments según su esquema). Recibís el resultado y seguís.
- reply: responderle al usuario (message). Termina tu turno.
- confirm o cancel: solo cuando hay una ACCIÓN PENDIENTE.

Cómo funcionan las herramientas:
- Los datos salen de las herramientas: no los inventes ni hagas cuentas que una herramienta ya da. Contá solo lo que muestran los resultados; si algo no se pudo hacer o no cambió, decilo.
- Los *_id salen de los resultados: nunca los adivines; si no tenés uno, buscalo primero.
- Si un resultado trae "ambiguo": true, preguntale al usuario cuál es, mostrando las opciones, antes de registrar nada. Con "ambiguo": false, seguí con el primero.
- Las herramientas marcadas CONFIRMAR no se ejecutan al pedirlas: quedan pendientes y vos preguntás si confirma, diciendo exactamente qué se va a hacer. Las que envían a terceros se llaman directamente, con los textos ya redactados: el sistema pide la confirmación y vos mostrás los textos.
- Si el resultado de un envío dice "simulado", aclaralo: quedó registrado en modo de prueba y no se envió.
- Si falta un dato que la herramienta permite omitir, omitilo en vez de inventarlo.
- No repitas una herramienta con los mismos argumentos.
- abrir_vista devuelve una marca como [[link1]]: ponela tal cual en tu respuesta y el sistema la cambia por el link. Nunca escribas un link vos.
- Si el mensaje trae "[archivo recibido · sha256 ...]", es una imagen o PDF leído por OCR (puede tener errores). Si una herramienta tiene un campo para el hash del archivo, pasale ese sha256.
- La fecha y hora actuales vienen al principio del mensaje del usuario (AHORA). Fechas en AAAA-MM-DD y horas en HH:MM en los argumentos.
- Un mensaje que empieza con SISTEMA es de la plataforma: seguí su indicación.
- No menciones JSON, herramientas ni detalles técnicos."""

WHATSAPP = """CANAL (WhatsApp): respondés siempre por escrito, aunque el usuario mande audios. Los audios llegan transcriptos y pueden tener errores, sobre todo en los nombres: si uno no es claro, preguntá. Números, fechas y horas en cifras; un listado, con una línea por ítem que empiece con "- "; sin encabezados; *negrita* con un asterisco. Si la respuesta sería muy larga (más de unos 1500 caracteres), resumí y, si hay una vista que lo muestre, mandá su link."""


def _now() -> datetime.datetime:
    return datetime.datetime.now(ZoneInfo(settings.assistant_timezone))


def build_system(workflow: Workflow, state: ConversationState, tools: list[app_tools.Tool]) -> str:
    whatsapp = state.channel == "whatsapp"
    parts = [SYSTEM.format(canal="WhatsApp" if whatsapp else "teléfono")]
    if whatsapp:
        parts.append(WHATSAPP)
    a = workflow.agent
    agent = [f"QUIÉN SOS: {a.name}, {a.role}. Idioma: {a.language}.", f"OBJETIVO: {workflow.objective.description}"]
    if workflow.conversation.rules:
        agent.append("REGLAS:\n" + "\n".join(f"- {r}" for r in workflow.conversation.rules))
    if workflow.knowledge.strip():
        agent.append("INFORMACIÓN:\n" + workflow.knowledge.strip())
    parts.append("\n".join(agent))
    # La fecha y hora van en el mensaje del usuario (now_line), no acá: el prompt de sistema queda igual
    # entre pasos y turnos, y vLLM reusa su procesamiento (prefix caching).
    if tools:
        lines = []
        for t in tools:
            args = json.dumps(t.schema.get("properties", {}), ensure_ascii=False, separators=(",", ":"))
            lines.append(f"- {t.name} [{KIND_LABEL[t.kind]}]: {t.description}\n  argumentos: {args}")
        parts.append("HERRAMIENTAS:\n" + "\n".join(lines))
    else:
        parts.append("HERRAMIENTAS: ninguna disponible ahora. Decile al usuario que no podés acceder a sus datos.")
    return "\n\n".join(parts)


def now_line() -> str:
    now = _now()
    return f"AHORA: {DAYS[now.weekday()]} {now:%Y-%m-%d %H:%M} ({settings.assistant_timezone})."


def step_schema(tools: list[app_tools.Tool], can_confirm: bool, reply_only: bool = False) -> dict:
    """reply_only: el paso solo puede responder (el ultimo, o despues de repetir una herramienta)."""
    options = [{"type": "object", "properties": {"action": {"enum": ["reply"]}, "message": {"type": "string"}},
                "required": ["action", "message"], "additionalProperties": False}]
    if reply_only:
        return {"anyOf": options}
    for t in tools:
        options.append({"type": "object", "properties": {
            "action": {"enum": ["call"]}, "tool": {"enum": [t.name]}, "arguments": t.schema},
            "required": ["action", "tool", "arguments"], "additionalProperties": False})
    if can_confirm:
        for action in ("confirm", "cancel"):
            options.append({"type": "object", "properties": {"action": {"enum": [action]}},
                            "required": ["action"], "additionalProperties": False})
    return {"anyOf": options}


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + " […]"


def _dump(value) -> str:
    return _clip(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str),
                 MAX_RESULT_CHARS)


def _ids(arguments, path: str = "") -> list[tuple[str, str]]:
    """Los (clave, valor) de las claves *_id, a cualquier nivel."""
    out = []
    if isinstance(arguments, dict):
        for k, v in arguments.items():
            if k.endswith("_id") and isinstance(v, (int, str)) and not isinstance(v, bool):
                out.append((k, str(v)))
            else:
                out += _ids(v, f"{path}.{k}")
    elif isinstance(arguments, list):
        for v in arguments:
            out += _ids(v, path)
    return out


def unseen_ids(arguments: dict, seen: str) -> list[str]:
    """Los *_id que no aparecen en ningun resultado (como "clave": valor, numero o texto)."""
    return [f"{k}={v}" for k, v in _ids(arguments)
            if f'"{k}": {v}' not in seen and f'"{k}": "{v}"' not in seen]


PLACEHOLDER_RE = re.compile(r"[a-z]+(_[a-z]+)*_id")


def placeholders(arguments, names: set[str]) -> list[str]:
    """Valores que son el nombre de un campo en vez del dato ("alumno": "alumno_id"; con Gemma a temperatura
    1.0, casos de uso del 12-oct-2026)."""
    out = []
    if isinstance(arguments, dict):
        for v in arguments.values():
            out += placeholders(v, names)
    elif isinstance(arguments, list):
        for v in arguments:
            out += placeholders(v, names)
    elif isinstance(arguments, str) and (arguments in names or PLACEHOLDER_RE.fullmatch(arguments)):
        out.append(arguments)
    return out


def _field_names(schema) -> set[str]:
    names: set[str] = set()
    if isinstance(schema, dict):
        names |= set((schema.get("properties") or {}).keys())
        for v in schema.values():
            names |= _field_names(v)
    elif isinstance(schema, list):
        for v in schema:
            names |= _field_names(v)
    return names


def unseen_urls(message: str, seen: str) -> list[str]:
    return [u for u in (m.rstrip(".,;:!?") for m in URL_RE.findall(message)) if u not in seen]


def _seen_before(state: ConversationState) -> str:
    """Resultados de herramientas y respuestas de los turnos anteriores (los del prompt)."""
    parts = []
    for m in state.messages[-max(settings.assistant_history_messages, 2):]:
        if m.role == "assistant":
            parts.append(m.text)
            parts += [t.get("output") or "" for t in m.llm or [] if t.get("kind") == "herramienta"]
    return "\n".join(parts)


AMBIGUOUS = '"ambiguo": true'
# Cualquier marca [[...]] que quede después de poner los links (12-oct-2026: "[[link_planes]]", inventada
# para una vista que la app no tenía).
MARK_RE = re.compile(r"\[\[[^\[\]\n]{1,60}\]\]")
# Respuesta clara a una accion pendiente: la resuelve la plataforma, no el LLM (12-oct-2026: con "Sí"
# volvia a pedir la misma herramienta en vez de confirm, y quedaba preguntando en cada turno).
YES_START = {"si", "sí", "sip", "dale", "ok", "okey", "okay", "confirmo", "confirmado", "confirmá", "hacelo",
             "mandalo", "mandala", "mandalos", "mandalas", "mandá", "envialo", "enviá", "correcto", "perfecto",
             "listo", "exacto", "adelante", "claro", "obvio", "de", "bueno", "joya", "genial"}
YES_WORDS = YES_START | {"una", "por", "supuesto", "gracias", "ya", "porfa", "eso", "es", "así", "todo", "todos",
                         "lo", "los", "nomás", "noma", "también", "registralo", "corregilo", "borralo", "dalo"}


def is_yes(text: str) -> bool:
    """Una respuesta hecha solo de palabras de aceptacion ("sí", "dale, mandalo", "confirmo, gracias")."""
    words = re.findall(r"[a-záéíóúñ]+", text.lower())
    return bool(words) and len(words) <= 8 and words[0] in YES_START and all(w in YES_WORDS for w in words)


NO = re.compile(r"^\W*(no|nop|nah|cancel[aá](lo)?|mejor no|par[aá]|dejalo|olvidalo)\b", re.IGNORECASE)


def _mark_link(result: str, url: str | None, links: dict[str, str]) -> str:
    """El link a una vista (de abrir_vista, o de una herramienta que devuelve "view"): el LLM ve una marca
    [[linkN]] y el sistema la cambia en la respuesta (12-oct-2026: copiaba mal el token)."""
    if not url:
        return result
    mark = f"[[link{len(links) + 1}]]"
    links[mark] = url
    return result.replace(f'"link": "{url}"', f'"link": "{mark}", "nota": "Poné {mark} tal cual en tu respuesta."', 1)


def _put_links(message: str, links: dict[str, str]) -> str:
    """Cambia las marcas por los links; si el LLM no puso ninguna, los agrega al final."""
    used = False
    for mark, url in links.items():
        if mark in message:
            message, used = message.replace(mark, url), True
    if links and not used and not any(url in message for url in links.values()):
        message += "\n\n" + "\n".join(links.values())
    return message


def _pending_note(pending: dict) -> str:
    return ("ACCIÓN PENDIENTE (la pediste en el turno anterior y está esperando el sí del usuario): "
            f"{pending['tool']} con {json.dumps(pending['arguments'], ensure_ascii=False)}. "
            "Si el mensaje nuevo la confirma, respondé action=confirm. Si dice que no, la cambia o habla de "
            "otra cosa, action=cancel (y después hacé lo que pide).")


class Assistant:
    def __init__(self, llm, sessions: sessionmaker[Session]):
        self.llm = llm
        self.sessions = sessions

    def tools_for(self, workflow: Workflow, state: ConversationState) -> list[app_tools.Tool]:
        with self.sessions() as s:
            return app_tools.catalog(s, state.client_id, workflow.tools)

    def history(self, state: ConversationState) -> list[dict]:
        """Los mensajes previos en texto, y en la ultima respuesta, los resultados de sus herramientas:
        sin ellos el LLM inventaba los alumno_id al seguir el pedido ("dale, mandalos"; casos de uso,
        12-oct-2026)."""
        messages = state.messages[-settings.assistant_history_messages:] if settings.assistant_history_messages else []
        whatsapp = state.channel == "whatsapp"
        out = []
        last_assistant = max((i for i, m in enumerate(messages) if m.role == "assistant"), default=None)
        for i, m in enumerate(messages):
            text = _clip(m.text, MAX_HISTORY_CHARS)
            if whatsapp and m.role == "user" and m.voice_note:
                text = f"{VOICE_NOTE_TAG} {text}"
            if i == last_assistant and (results := [t.get("input", "") + " -> " + (t.get("output") or "")
                                                    for t in m.llm or [] if t.get("kind") == "herramienta"]):
                text += "\n\n[Resultados de herramientas de este turno: " + _clip(" | ".join(results),
                                                                                   MAX_PREVIOUS_RESULTS) + "]"
            out.append({"role": m.role, "content": text})
        return out

    async def run(self, workflow: Workflow, state: ConversationState, user_message: str,
                  media: TurnMedia, actor: str) -> tuple[AgentTurn, list[dict], dict | None]:
        """Devuelve la respuesta, la traza del turno (para el dashboard) y lo que queda pendiente."""
        tools = self.tools_for(workflow, state)
        by_name = {t.name: t for t in tools}
        prior = state.progress.pending if state.progress.pending and state.progress.pending.get("tool") in by_name else None
        new_pending: dict | None = None
        trace: list[dict] = []
        whatsapp = state.channel == "whatsapp"

        content = f"{VOICE_NOTE_TAG} {user_message}" if whatsapp and media.user_voice_note else user_message
        content = f"{now_line()}\n\n{content}"
        decided = None
        links: dict[str, str] = {}      # [[linkN]] -> URL de una vista pedida en este turno
        confirmed = ""                  # resultado de lo pendiente que confirmo el usuario
        if prior and is_yes(user_message):
            confirmed, url = await self._execute(by_name[prior["tool"]], prior["arguments"], actor, trace,
                                                 state.conversation_id)
            result = _mark_link(confirmed, url, links)
            decided = f"SISTEMA: el usuario confirmó y se ejecutó {prior['tool']}. RESULTADO: {result}"
            prior = None
        elif prior and NO.match(user_message.strip()):
            trace.append({"kind": "control", "input": prior["tool"], "ms": 0, "output": "cancelada por el usuario"})
            decided = f"SISTEMA: el usuario no confirmó; {prior['tool']} quedó cancelada y no se ejecutó."
            prior = None
        if prior:
            content += "\n\n" + _pending_note(prior)
        elif decided:
            content += "\n\n" + decided
        messages = [{"role": "system", "content": build_system(workflow, state, tools)},
                    *self.history(state), {"role": "user", "content": content}]
        done_calls: set[str] = set()
        seen = _seen_before(state) + "\n" + confirmed
        url_retries = 1
        json_retries = 1
        ambiguous = False               # una consulta del turno devolvio "ambiguo": true

        steps = max(settings.assistant_max_steps, 1)
        reply_only = False
        for step in range(steps):
            started = time.perf_counter()
            # El ultimo paso, o despues de repetir una herramienta, solo puede responder (12-oct-2026: con
            # razonamiento repetia ficha_alumno hasta agotar los pasos y el usuario recibia el FALLBACK).
            schema = step_schema(tools, prior is not None, reply_only or step == steps - 1)
            raw, reasoning = await self.llm.structured(messages, schema, "paso",
                                                       thinking=settings.assistant_thinking,
                                                       budget=settings.assistant_thinking_budget,
                                                       max_tokens=settings.assistant_max_step_tokens)
            trace.append({"kind": "paso", "input": "", "ms": round((time.perf_counter() - started) * 1000),
                          "reasoning": reasoning, "output": raw})
            try:
                action = json.loads(raw)
            except ValueError:
                # Cortada por el tope de tokens (o rara): se reintenta una vez, sin sumarla al historial.
                logger.warning("assistant: salida no JSON en %s", state.conversation_id)
                trace.append({"kind": "control", "input": raw[-200:], "ms": 0, "output": "salida no JSON"})
                if json_retries > 0:
                    json_retries -= 1
                    continue
                break
            messages.append({"role": "assistant", "content": raw})
            kind = action.get("action")
            if kind == "reply":
                message = _put_links((action.get("message") or "").strip() or FALLBACK, links)
                if marks := MARK_RE.findall(message):
                    # Una marca sin vista pedida en este turno (12-oct-2026: le llegó "[[link1]]" al usuario).
                    trace.append({"kind": "control", "input": " ".join(marks), "ms": 0, "output": "marca sin link"})
                    if url_retries > 0:
                        url_retries -= 1
                        messages.append({"role": "user", "content": (
                            "SISTEMA: escribiste una marca de link sin pedir la vista. Para mandar un link, primero "
                            "pedilo con abrir_vista y después poné la marca que devuelve. Si la vista no está en "
                            "abrir_vista, no hay link: respondé con lo que sepas o decí que no está disponible.")})
                        continue
                    message = MARK_RE.sub("", message).strip() or FALLBACK
                if bad := unseen_urls(message, seen):
                    trace.append({"kind": "control", "input": " ".join(bad), "ms": 0, "output": "link inventado"})
                    if url_retries > 0:
                        url_retries -= 1
                        messages.append({"role": "user", "content": (
                            "SISTEMA: ese link no salió de ninguna herramienta. No inventes links: para mostrar una "
                            "vista, pedila con abrir_vista; si no está, decí que no está disponible.")})
                        continue
                    for url in bad:
                        message = message.replace(url, "(link no disponible)")
                return AgentTurn(assistant_message=message, raw=raw, reasoning=reasoning), trace, new_pending
            if kind in ("confirm", "cancel") and prior:
                pending, prior = prior, None
                if kind == "cancel":
                    messages.append({"role": "user", "content": "SISTEMA: acción pendiente cancelada, no se ejecutó."})
                    continue
                result, url = await self._execute(by_name[pending["tool"]], pending["arguments"], actor, trace,
                                                  state.conversation_id)
                seen += "\n" + result
                result = _mark_link(result, url, links)
                messages.append({"role": "user", "content": f"RESULTADO de {pending['tool']} (confirmada): {result}"})
                continue
            tool = by_name.get(action.get("tool") or "")
            if kind != "call" or tool is None:
                messages.append({"role": "user", "content": "SISTEMA: acción inválida. Respondé al usuario."})
                continue
            arguments = action.get("arguments") or {}
            key = f"{tool.name}:{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}"
            if key in done_calls:
                messages.append({"role": "user", "content": "SISTEMA: ya usaste esa herramienta con esos argumentos. "
                                 "Respondé al usuario con lo que tenés."})
                reply_only = True
                continue
            done_calls.add(key)
            if bad := placeholders(arguments, _field_names(tool.schema)):
                trace.append({"kind": "control", "input": json.dumps(arguments, ensure_ascii=False), "ms": 0,
                              "output": "nombre de campo como valor: " + ", ".join(bad)})
                messages.append({"role": "user", "content": (
                    f"SISTEMA: {tool.name} NO se ejecutó: pusiste {', '.join(repr(b) for b in bad)} como valor; "
                    "va el dato (por ejemplo el número de alumno_id que salió del resultado, o el nombre).")})
                continue
            if tool.kind != "read" and ambiguous:
                trace.append({"kind": "control", "input": json.dumps(arguments, ensure_ascii=False), "ms": 0,
                              "output": f"{tool.name} despues de una consulta ambigua"})
                messages.append({"role": "user", "content": (
                    f"SISTEMA: {tool.name} NO se ejecutó: la búsqueda fue ambigua. Preguntale al usuario cuál es, "
                    "mostrando las opciones, y esperá su respuesta. Respondé ahora con reply.")})
                continue
            if tool.kind != "read" and (missing := unseen_ids(arguments, seen)):
                trace.append({"kind": "control", "input": json.dumps(arguments, ensure_ascii=False), "ms": 0,
                              "output": "id sin consultar: " + ", ".join(missing)})
                messages.append({"role": "user", "content": (
                    f"SISTEMA: {tool.name} NO se ejecutó: {', '.join(missing)} no salió de ningún resultado. "
                    "Nunca adivines un id: buscalo primero con una herramienta de consulta.")})
                continue
            if tool.needs_confirmation:
                new_pending = {"tool": tool.name, "arguments": arguments}
                trace.append({"kind": "pendiente", "input": json.dumps(arguments, ensure_ascii=False), "ms": 0,
                              "output": tool.name})
                messages.append({"role": "user", "content": (
                    f"SISTEMA: {tool.name} NO se ejecutó: queda pendiente. Preguntale al usuario si confirma, "
                    "diciendo exactamente qué se va a hacer. Respondé ahora con reply.")})
                continue
            result, url = await self._execute(tool, arguments, actor, trace, state.conversation_id)
            seen += "\n" + result
            if tool.kind == "read" and AMBIGUOUS in result:
                ambiguous = True
            result = _mark_link(result, url, links)
            messages.append({"role": "user", "content": f"RESULTADO de {tool.name}: {result}"})

        return AgentTurn(assistant_message=FALLBACK), trace, new_pending

    async def _execute(self, tool: app_tools.Tool, arguments: dict, actor: str, trace: list[dict],
                       conversation_id: str) -> str:
        started = time.perf_counter()
        try:
            out = await app_tools.execute(self.sessions, tool, arguments, actor, conversation_id)
        except Exception:
            logger.exception("assistant: fallo la herramienta %s", tool.name)
            out = {"ok": False, "result": "Error interno al usar la herramienta."}
        result = _dump(out["result"]) if out["ok"] else "ERROR: " + _dump(out["result"])
        trace.append({"kind": "herramienta", "input": f"{tool.name} {json.dumps(arguments, ensure_ascii=False)}",
                      "ms": round((time.perf_counter() - started) * 1000), "output": result})
        return result, out.get("link")
