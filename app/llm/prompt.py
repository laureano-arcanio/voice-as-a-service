"""Prompts del motor: la definicion del agente y el protocolo de la plataforma, nada mas.

Sin reglas de comportamiento (como preguntar, cuando cortar, como decir los numeros): esas son reglas del agente,
en su definicion, a la vista y editables (AGENTS.md, "Reglas de desarrollo"). El texto para la voz lo
normaliza la plataforma antes del TTS (app/voice/speech_text.py); terminar y derivar son herramientas
(app/llm/platform_tools.py)."""
import json

import yaml

from app.conversation import variables
from app.conversation.models import ConversationState, Message, Workflow

EXTRACTION_PROMPT = """Sos el extractor de datos de {where}. No hablás con nadie: leés la conversación entre el agente y el usuario y devolvés, para cada campo, el valor que dio el usuario, o null si no lo dio. Cada campo con su tipo y su descripción. KNOWN FIELDS son los datos ya guardados."""
# Se suma si el agente pide resumen (analysis.summary).
SUMMARY_PROMPT = " En summary, un resumen breve de la conversación: qué quería la persona y cómo terminó."

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

def extraction_prompt(channel: str = "voice", summary: bool = False) -> str:
    return EXTRACTION_PROMPT.format(where="una conversación por WhatsApp" if channel == "whatsapp"
                                    else "una llamada telefónica") + (SUMMARY_PROMPT if summary else "")


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


def render_fields(workflow: Workflow, state: ConversationState | None = None) -> str:
    """Los campos del analisis tal como los define el agente, en su orden (las descripciones, con sus variables)."""
    fields = {}
    for name, spec in workflow.analysis_fields.items():
        data = spec.model_dump(include={"type", "options", "description"}, exclude_none=True)
        data["description"] = variables.render(data["description"], state, workflow)
        fields[name] = data
    return yaml.safe_dump(fields, allow_unicode=True, sort_keys=False, width=1000)


def build_extraction_prompt(workflow: Workflow, state: ConversationState) -> str:
    """El analisis: el agente, sus instrucciones, los campos, las variables visibles como contexto y la
    conversacion."""
    known = {k: v for k, v in state.fields.items() if v is not None}
    instructions = workflow.analysis.instructions.strip() if workflow.analysis else ""
    instructions = f"INSTRUCCIONES:\n{variables.render(instructions, state, workflow)}\n\n" if instructions else ""
    context = variables.visible(state)
    context = f"VARIABLES:\n{json.dumps(context, ensure_ascii=False)}\n\n" if context else ""
    return (
        f"AGENTE: {workflow.agent.name}.\n\n"
        f"{instructions}"
        f"CAMPOS:\n{render_fields(workflow, state)}\n"
        f"{context}"
        f"CONVERSATION:\n{render_conversation(state)}\n\n"
        f"KNOWN FIELDS:\n{json.dumps(known, ensure_ascii=False)}"
    )


# ---------- conversacion ----------

def handoff_enabled(state: ConversationState | None) -> bool:
    """Si en esta conversacion el agente puede derivar: una llamada con areas (las fija el worker)."""
    return bool(state and state.channel == "voice" and state.progress.handoff_areas)


def build_system_prompt(workflow: Workflow, channel: str = "voice", state: ConversationState | None = None) -> str:
    """El canal y el prompt del agente tal cual, con sus {{variables}} sustituidas (app/conversation/variables.py).
    Sin estado (la vista previa del editor), el prompt sin renderizar."""
    return f"{CHANNEL[channel]}\n\n{variables.render(workflow.prompt.strip(), state, workflow)}"


def build_turn_messages(workflow: Workflow, state: ConversationState, user_message: str) -> list[dict]:
    """Por WhatsApp, los mensajes del usuario que llegaron como audio llevan VOICE_NOTE_TAG."""
    whatsapp = state.channel == "whatsapp"
    media = state.media if whatsapp else None
    content = _turn_text(user_message, bool(media and media.user_voice_note))
    # El del primer turno (progress.system_prompt): igual en toda la conversacion, para el prefix cache.
    system = state.progress.system_prompt or build_system_prompt(workflow, state.channel, state)
    return [{"role": "system", "content": system},
            *classic_history(state.messages, whatsapp), {"role": "user", "content": content}]


def classic_history(messages: list[Message], whatsapp: bool) -> list[dict]:
    """La conversacion como mensajes del chat. En una llamada derivada, lo que dijo la persona del equipo va como
    assistant con su nombre (`name`), y lo que dijo quien llama, como user.
    La respuesta que derivo (Message.handoff) va con su llamada a transfer_call y el resultado: sin eso el modelo
    ve que "te paso con X" solo alcanza y en la siguiente derivacion no llama a la herramienta."""
    out: list[dict] = []
    for i, m in enumerate(messages):
        item = {"role": m.role, "content": _turn_text(m.text, whatsapp and m.role == "user" and m.voice_note)}
        if m.person:
            item["name"] = "".join(c if c.isalnum() else "_" for c in m.person)[:64]
        if m.role == "assistant" and m.handoff:
            call_id = f"call_handoff_{i}"
            item["content"] = item["content"] or None
            item["tool_calls"] = [{"id": call_id, "type": "function", "function": {
                "name": "transfer_call", "arguments": json.dumps({"area": m.handoff}, ensure_ascii=False)}}]
            out += [item, {"role": "tool", "tool_call_id": call_id,
                           "content": f"Derivacion a {m.handoff} ejecutada; lo que paso despues sigue en la conversacion."}]
            continue
        out.append(item)
    return out


def _turn_text(text: str, voice_note: bool) -> str:
    return f"{VOICE_NOTE_TAG} {text}" if voice_note else text
