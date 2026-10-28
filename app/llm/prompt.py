"""Prompts del motor: la definicion del agente y el protocolo de la plataforma, nada mas.

Sin reglas de comportamiento (como preguntar, cuando cortar, como decir los numeros): esas son reglas del agente,
en su definicion, a la vista y editables (AGENTS.md, "Reglas de desarrollo"). El texto para la voz lo
normaliza la plataforma antes del TTS (app/voice/speech_text.py); terminar y derivar son herramientas
(app/llm/platform_tools.py)."""
import datetime
import json
from zoneinfo import ZoneInfo

import yaml

from app.config import settings
from app.conversation.contact import prompt_block
from app.conversation.models import ConversationState, Message, Workflow

EXTRACTION_PROMPT = """Sos el extractor de datos de {where}. No hablás con nadie: leés la conversación entre el agente y el usuario y devolvés, para cada campo, el valor que dio el usuario, o null si no lo dio. Cada campo con su tipo y su descripción. KNOWN FIELDS son los datos ya guardados."""

# Marca de los mensajes del usuario que llegaron como audio (WhatsApp): son una transcripcion.
VOICE_NOTE_TAG = "[nota de voz transcripta]"

# El canal sale de la conversacion (state.channel), no del agente: la misma definicion atiende llamadas y
# WhatsApp. Lo que cambia es el formato del medio.
CHANNEL = {
    "voice": "Estás en una llamada telefónica. Tu respuesta se dice en voz alta.",
    "whatsapp": ("Estás conversando por WhatsApp. Tu respuesta se manda como mensaje de texto (formato de "
                 "WhatsApp: *negrita* con un asterisco, sin otro markdown) o, si la persona mandó un audio, "
                 "como nota de voz. Los audios de la persona te llegan transcriptos y marcados "
                 f"{VOICE_NOTE_TAG}. No recibís imágenes."),
}

WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def extraction_prompt(channel: str = "voice") -> str:
    return EXTRACTION_PROMPT.format(where="una conversación por WhatsApp" if channel == "whatsapp"
                                    else "una llamada telefónica")


def render_workflow(workflow: Workflow) -> str:
    return yaml.safe_dump(workflow.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False, width=1000)


def render_conversation(state: ConversationState) -> str:
    """Toda la conversacion, un mensaje por linea (los saltos de linea de un texto escrito se aplanan con " / ":
    si no, "\\nagente: ..." pareceria otro turno). Para la extraccion y el resumen de una derivacion."""
    whatsapp = state.channel == "whatsapp"
    return "\n".join(f"{_speaker(m, whatsapp)}: {_one_line(m.text)}" for m in state.messages)


def _speaker(message: Message, whatsapp: bool) -> str:
    if message.person:
        return f"{message.person} (persona del equipo)"
    if message.role == "assistant":
        return "agente"
    return "usuario (nota de voz)" if whatsapp and message.voice_note else "usuario"


def _one_line(text: str) -> str:
    if "\n" not in text and "\r" not in text:
        return text
    return " / ".join(line.strip() for line in text.splitlines() if line.strip())


def render_fields(workflow: Workflow) -> str:
    """Los campos tal como los define el agente."""
    fields = {name: spec.model_dump(include={"type", "options", "description"}, exclude_none=True)
              for name, spec in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)}
    return yaml.safe_dump(fields, allow_unicode=True, sort_keys=False, width=1000)


def build_extraction_prompt(workflow: Workflow, state: ConversationState) -> str:
    known = {k: v for k, v in state.fields.items() if v is not None}
    # Llamada suelta: lo que el contacto escribio antes de la llamada.
    motive = f"MOTIVO DEL LLAMADO (escrito antes de la llamada):\n{state.progress.context}\n\n" \
        if state.progress.context else ""
    return (
        f"AGENTE: {workflow.agent.name}, {workflow.agent.role}.\n"
        f"OBJETIVO: {workflow.objective.description.strip()}\n\n"
        f"CAMPOS:\n{render_fields(workflow)}\n"
        f"{motive}"
        f"CONVERSATION:\n{render_conversation(state)}\n\n"
        f"KNOWN FIELDS:\n{json.dumps(known, ensure_ascii=False)}"
    )


# ---------- conversacion ----------

def handoff_enabled(state: ConversationState | None) -> bool:
    """Si en esta conversacion el agente puede derivar: una llamada con areas (las fija el worker)."""
    return bool(state and state.channel == "voice" and state.progress.handoff_areas)


def describe_condition(when: dict) -> str:
    return " y ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in when.items())


def render_variables(text: str) -> str:
    """{{today}} y {{now}} en las reglas, el objetivo y la base de conocimiento del agente (zona AGENT_TIMEZONE)."""
    if "{{" not in text:
        return text
    now = datetime.datetime.now(ZoneInfo(settings.agent_timezone))
    return (text.replace("{{today}}", f"{WEEKDAYS[now.weekday()]} {now:%Y-%m-%d}")
            .replace("{{now}}", f"{WEEKDAYS[now.weekday()]} {now:%Y-%m-%d %H:%M}"))


def build_system_prompt(workflow: Workflow, channel: str = "voice", state: ConversationState | None = None) -> str:
    """El agente en un prompt de sistema, sacado de su definicion: quien es, el canal, el objetivo, los datos,
    sus reglas, la base de conocimiento y los cierres. Con el estado de una llamada de campaña suma los datos del
    contacto y los campos que ya vienen cargados."""
    whatsapp = channel == "whatsapp"
    fields = []
    for name, spec in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority):
        need = ("obligatorio" if spec.required else
                f"obligatorio si {describe_condition(spec.required_if)}" if spec.required_if else "opcional")
        description = " ".join(spec.description.split()).rstrip(".") + "."
        options = f" Opciones: {', '.join(spec.options)}." if spec.options else ""
        question = f" Pregunta sugerida: {spec.question.strip()}" if spec.question and spec.question.strip() else ""
        fields.append(f"- {name} ({need}): {description}{options}{question}")
    outcomes = [f"- {o.label}{' (si ' + describe_condition(o.when) + ')' if o.when else ' (en cualquier otro caso)'}: "
                f"{' '.join(o.message.split())}" for o in workflow.completion.outcomes]
    rules = "\n".join(f"- {render_variables(r)}" for r in workflow.conversation.rules)
    campaign = f"\n\n{block}" if (block := prompt_block(state)) else ""
    greeting = (f"\n\nAPERTURA (la persona escribe primero; guía para tu primer mensaje):\n"
                f"{workflow.conversation.opening.strip()}" if whatsapp else "")
    data = f"\n\nDATOS A OBTENER (los nombres son internos):\n{chr(10).join(fields)}" if fields else ""
    return f"""Sos {workflow.agent.name}, {workflow.agent.role}. Idioma: {workflow.agent.language}. {CHANNEL[channel]}

OBJETIVO:
{render_variables(workflow.objective.description.strip())}{campaign}{data}

REGLAS:
{rules}

BASE DE CONOCIMIENTO:
{render_variables(workflow.knowledge.strip())}

CIERRES (mensaje de despedida según el resultado):
{chr(10).join(outcomes)}{greeting}"""


def build_turn_messages(workflow: Workflow, state: ConversationState, user_message: str) -> list[dict]:
    """Por WhatsApp, los mensajes del usuario que llegaron como audio llevan VOICE_NOTE_TAG."""
    whatsapp = state.channel == "whatsapp"
    media = state.media if whatsapp else None
    content = _turn_text(user_message, bool(media and media.user_voice_note))
    return [{"role": "system", "content": build_system_prompt(workflow, state.channel, state)},
            *classic_history(state.messages, whatsapp), {"role": "user", "content": content}]


def classic_history(messages: list[Message], whatsapp: bool) -> list[dict]:
    """La conversacion como mensajes del chat. En una llamada derivada, lo que dijo la persona del equipo va como
    assistant con su nombre (`name`), y lo que dijo quien llama, como user."""
    out: list[dict] = []
    for m in messages:
        item = {"role": m.role, "content": _turn_text(m.text, whatsapp and m.role == "user" and m.voice_note)}
        if m.person:
            item["name"] = "".join(c if c.isalnum() else "_" for c in m.person)[:64]
        out.append(item)
    return out


def _turn_text(text: str, voice_note: bool) -> str:
    return f"{VOICE_NOTE_TAG} {text}" if voice_note else text
