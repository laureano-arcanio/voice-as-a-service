import json

import yaml

from app.conversation.models import ConversationState, Message, Workflow
from app.conversation.workflow import pending_fields

from .budget import omitted_note

SYSTEM_PROMPT = """Sos un agente conversacional telefónico que ejecuta un workflow.

Los datos del usuario no los guardás vos: otro proceso los extrae de la conversación mientras hablás. Por eso known_fields puede no tener todavía lo que el usuario dijo en el mensaje nuevo o en el anterior: guiate por la conversación.

En cada turno:

1. Leé la definición del workflow.
2. Leé la conversación hasta ahora y el estado actual.
3. Interpretá el nuevo mensaje del usuario, en el contexto de la conversación.
4. Determiná qué objetivos siguen pendientes: los de pending_objectives, menos los que el usuario ya respondió en la conversación o en el mensaje nuevo.
5. Elegí el siguiente objetivo conversacional apropiado.
6. Generá una respuesta natural para continuar.

Reglas:

- Las preguntas de cada campo son sugerencias, no un guion rígido: reformulalas para que la conversación sea natural.
- No vuelvas a preguntar lo que ya está en known_fields, en answered_without_data o lo que el usuario ya respondió en la conversación.
- El usuario puede proporcionar varios datos espontáneamente.
- Si una respuesta es ambigua, pedí aclaración.
- Si el usuario hace una pregunta, respondela con la base de conocimiento y luego continuá naturalmente.
- Nunca inventes datos del usuario ni información del producto.
- Hacé normalmente una pregunta por turno.
- Respetá el idioma y las reglas definidas en el workflow.
- Las respuestas deben ser breves, naturales y apropiadas para una conversación de voz.
- No menciones JSON, campos, workflow ni estados internos.
- Si CURRENT STATE trae rejected_values, esos valores no se pudieron guardar (por ejemplo un email incompleto): pedí ese dato de nuevo.
- La conversación termina cuando no quedan objetivos pendientes o cuando el usuario no quiere seguir. En ese turno despedite, usando como guía el mensaje del resultado que corresponda (completion.outcomes), y marcá completed.

Respondé con:
- assistant_message: lo que le decís al usuario.
- answered: true si el nuevo mensaje del usuario responde lo que le preguntaste en tu último mensaje (last_asked_objective), aunque haya que interpretarlo; false si no lo responde, pide aclaración o habla de otra cosa.
- next_objective: el campo que vas a intentar obtener con tu respuesta (puede ser el mismo si pedís aclaración), o null si no queda ninguno.
- status: active o completed."""


EXTRACTION_PROMPT = """Sos el extractor de datos de una llamada telefónica. No hablás con nadie: leés la conversación entre el agente y el usuario y devolvés, para cada campo, el valor que dio el usuario.

Reglas:

- Un campo lleva valor si el usuario lo dijo o lo confirmó en cualquier momento de la conversación; si no, null.
- Si el usuario corrigió un dato o cambió de opinión, vale lo último que dijo.
- Si el usuario acepta una opción concreta que le propuso el agente ("sí, esa", "dale"), el valor es esa opción. Las sugerencias del agente que el usuario no eligió no son datos.
- Un campo sí o no (boolean) lleva valor solo si el usuario respondió esa pregunta o lo expresó claramente. Una negativa, un "ahora no" o un "lo pienso" es false.
- No deduzcas datos de lo que dijo el agente, ni completes con valores de relleno como 0 o texto vacío.
- El texto viene de un reconocimiento de voz y puede tener errores. Si una palabra mal transcripta corresponde claramente a algo que encaja en el campo, usá la forma correcta; si no está claro, null.
- Respetá el tipo y la descripción de cada campo. Un email va escrito como dirección (juan@gmail.com) y un teléfono, en cifras.
- known_fields son los datos ya guardados: repetilos si siguen valiendo, o corregilos si el usuario los cambió."""


# ---------- canal ----------
# El canal sale de la conversacion (state.channel), no del agente: la misma
# definicion atiende llamadas y WhatsApp. Voz es el prompt de siempre; los
# otros canales cambian frases puntuales y suman su bloque de reglas.

CHANNEL_RULES: dict[str, str] = {
    "voice": "",
    "whatsapp": """CANAL: conversación escrita por WhatsApp. Estas reglas pisan las del workflow y la forma de la base de conocimiento pensadas para una llamada hablada (números o correos en palabras, escribir solo lo que se dice, cantidad de frases):
- Números, montos, fechas, horarios y teléfonos en cifras (por ejemplo 23.500, 10/10 o 9:30), aunque la base de conocimiento los tenga en palabras.
- Emails como dirección (hola@empresa.com) y links como se escriben.
- Mensajes breves, de hasta unos 300 caracteres, con normalmente una sola pregunta.
- Sin markdown salvo *negrita* con un asterisco; sin encabezados ni listas largas.
- No podés ver imágenes. Los audios del usuario te llegan transcriptos automáticamente, marcados como nota de voz, y pueden tener errores de reconocimiento: si un dato clave no se entiende, pedí que lo repita.
- Si en la conversación todavía no hay mensajes tuyos, saludá y presentate usando como guía la apertura del workflow (opening) y respondé lo que escribió el usuario.""",
}

# Respuesta en nota de voz (WhatsApp, app/whatsapp/audio.py): el texto va al
# TTS, asi que valen las reglas de una llamada. Va en el prompt de sistema
# (estatico, para el prefix caching) y el turno avisa cuando aplica; when dice
# como lo avisa cada motor.
VOICE_NOTE_RULES = """NOTA DE VOZ: {when}, tu respuesta se envía como nota de voz: una voz sintética lee tu texto. En ese turno no valen las reglas de texto de WhatsApp de arriba sino las de una llamada:
- Números, montos, fechas, horarios y teléfonos en palabras (por ejemplo veintitrés mil quinientos pesos, el diez de octubre, a las nueve y media).
- Emails y links como se dicen (hola arroba empresa punto com).
- Sin emojis, asteriscos, listas ni símbolos: solo lo que se dice.
- Frases cortas, de unas tres oraciones, con normalmente una sola pregunta.
- No menciones que es un audio ni que lo estás grabando."""

# Marca de los mensajes del usuario que llegaron como audio (motor clasico).
VOICE_NOTE_TAG = "[nota de voz transcripta]"
VOICE_NOTE_REPLY = "\n\n[Tu respuesta se envía como nota de voz: seguí las reglas de NOTA DE VOZ.]"


def _swap(text: str, *pairs: tuple[str, str]) -> str:
    """Reemplazos del texto de voz; falla si una frase ya no esta (para que un
    cambio en el prompt de voz no deje al canal con la frase vieja)."""
    for old, new in pairs:
        if old not in text:
            raise ValueError(f"frase no encontrada en el prompt: {old!r}")
        text = text.replace(old, new)
    return text


_WHATSAPP_SYSTEM = _swap(
    SYSTEM_PROMPT,
    ("Sos un agente conversacional telefónico", "Sos un agente conversacional por WhatsApp"),
    ("apropiadas para una conversación de voz.", "apropiadas para un chat de WhatsApp."),
    ("\n\nRespondé con:", (f"\n\n{CHANNEL_RULES['whatsapp']}\n\n"
                          f"{VOICE_NOTE_RULES.format(when='Si CURRENT STATE trae \"reply_format\": \"nota de voz\"')}"
                          "\n\nRespondé con:")),
    ("- assistant_message: lo que le decís al usuario.", "- assistant_message: el texto del mensaje que le mandás al usuario."),
)

_WHATSAPP_EXTRACTION = _swap(
    EXTRACTION_PROMPT,
    ("de una llamada telefónica.", "de una conversación escrita por WhatsApp."),
    ("- El texto viene de un reconocimiento de voz y puede tener errores. Si una palabra mal transcripta",
     ("- El texto lo escribió el usuario: puede tener errores de tipeo o abreviaturas. Los mensajes marcados "
      "(nota de voz) no: vienen de un reconocimiento de voz y pueden tener errores de transcripción. "
      "Si una palabra mal escrita o mal transcripta")),
)


def system_prompt(channel: str = "voice") -> str:
    return _WHATSAPP_SYSTEM if channel == "whatsapp" else SYSTEM_PROMPT


def extraction_prompt(channel: str = "voice") -> str:
    return _WHATSAPP_EXTRACTION if channel == "whatsapp" else EXTRACTION_PROMPT


def render_workflow(workflow: Workflow) -> str:
    return yaml.safe_dump(workflow.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False, width=1000)


def render_conversation(state: ConversationState, omitted: int = 0) -> str:
    """Toda la conversacion: con solo el ultimo intercambio, el LLM no veia un
    dato que no habia guardado y lo volvia a preguntar ("ya te dije antes").

    Un mensaje por linea: los saltos de linea de un texto escrito (WhatsApp) se
    aplanan con " / ", si no "\nagente: ..." inventaria turnos del agente.

    Por WhatsApp, los mensajes del usuario que llegaron como audio van marcados
    (es una transcripcion); los del agente no, para que el modelo no imite la marca.

    omitted: mensajes viejos que se sacaron por el contexto (app/llm/budget.py); state ya
    viene sin ellos y una linea avisa que faltan."""
    whatsapp = state.channel == "whatsapp"
    lines = [conversation_line(m, whatsapp) for m in state.messages]
    return "\n".join([omitted_note(omitted), *lines] if omitted else lines)


def conversation_line(message: Message, whatsapp: bool) -> str:
    return f"{_speaker(message, whatsapp)}: {_one_line(message.text)}"


def _speaker(message: Message, whatsapp: bool) -> str:
    if message.role == "assistant":
        return "agente"
    return "usuario (nota de voz)" if whatsapp and message.voice_note else "usuario"


def _one_line(text: str) -> str:
    if "\n" not in text and "\r" not in text:
        return text
    return " / ".join(line.strip() for line in text.splitlines() if line.strip())


def build_user_prompt(workflow: Workflow, state: ConversationState, user_message: str, omitted: int = 0) -> str:
    answered_empty = state.progress.answered_empty
    current = {
        "status": state.status,
        "known_fields": {k: v for k, v in state.fields.items() if v is not None},
        "pending_objectives": [f for f in pending_fields(workflow, state) if f not in answered_empty],
        "last_asked_objective": state.progress.asked,
    }
    if answered_empty:
        current["answered_without_data"] = answered_empty
    if state.progress.rejected:
        current["rejected_values"] = state.progress.rejected
    # Marcas del turno (solo WhatsApp): el mensaje es una transcripcion y/o la
    # respuesta sale como nota de voz (reglas NOTA DE VOZ del prompt de sistema).
    media = state.media if state.channel == "whatsapp" else None
    if media and media.reply_voice_note:
        current["reply_format"] = "nota de voz"
    header = "NEW USER MESSAGE (nota de voz transcripta):" if media and media.user_voice_note else "NEW USER MESSAGE:"
    # La conversacion va antes del estado: crece al final y el resto no cambia,
    # asi vLLM reusa el prefijo (prefix caching) del turno anterior.
    return (
        f"WORKFLOW:\n{render_workflow(workflow)}\n"
        f"CONVERSATION:\n{render_conversation(state, omitted)}\n\n"
        f"CURRENT STATE:\n{json.dumps(current, ensure_ascii=False, indent=2)}\n\n"
        f"{header}\n{user_message}"
    )


def render_fields(workflow: Workflow, only: list[str] | None = None) -> str:
    """Los campos tal como los define el workflow: la extraccion sale de la
    configuracion del agente, no de un prompt por cliente."""
    fields = {name: spec.model_dump(include={"type", "options", "description", "question"}, exclude_none=True)
              for name, spec in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)
              if only is None or name in only}
    return yaml.safe_dump(fields, allow_unicode=True, sort_keys=False, width=1000)


def build_extraction_prompt(workflow: Workflow, state: ConversationState, only: list[str] | None = None,
                            omitted: int = 0) -> str:
    focus = f"Devolvé solo el campo {', '.join(only)}: el agente lo preguntó y el usuario lo respondió.\n\n" if only else ""
    known = {k: v for k, v in state.fields.items() if v is not None and (only is None or k in only)}
    objective = "OBJETIVO" if state.channel == "whatsapp" else "OBJETIVO DE LA LLAMADA"
    return (
        f"AGENTE: {workflow.agent.name}, {workflow.agent.role}.\n"
        f"{objective}: {workflow.objective.description.strip()}\n\n"
        f"CAMPOS:\n{render_fields(workflow, only)}\n"
        f"CONVERSATION:\n{render_conversation(state, omitted)}\n\n"
        f"KNOWN FIELDS:\n{json.dumps(known, ensure_ascii=False)}\n\n"
        f"{focus}Devolvé el valor de cada campo según la conversación."
    )


# ---------- motor clasico ----------

# Marca de fin: el modelo la agrega al despedirse y no se dice (el texto va
# directo al TTS, sin JSON donde poner un status).
END_MARKER = "[FIN]"


def describe_condition(when: dict) -> str:
    return " y ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in when.items())


def build_classic_system(workflow: Workflow, channel: str = "voice") -> str:
    """Todo el agente en un prompt de sistema, sacado del YAML. Con whatsapp
    cambia el medio, suma las reglas del canal y el saludo: el usuario escribe
    primero y no hay apertura en la conversacion."""
    whatsapp = channel == "whatsapp"
    where = "Estás conversando por WhatsApp (texto)" if whatsapp else "Estás en una llamada telefónica"
    reply = "Respondé solo con el texto del mensaje." if whatsapp else "Respondé solo con lo que decís en voz alta."
    extra = ""
    if whatsapp:
        when = f"Si el mensaje del usuario termina con el aviso \"{VOICE_NOTE_REPLY.strip()}\""
        extra = (f"\n\nSALUDO (apertura del workflow: guía para tu primer mensaje):\n"
                 f"{workflow.conversation.opening.strip()}\n\n{CHANNEL_RULES['whatsapp']}"
                 f"\n\n{VOICE_NOTE_RULES.format(when=when)}")
    fields = []
    for name, spec in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority):
        need = ("obligatorio" if spec.required else
                f"obligatorio si {describe_condition(spec.required_if)}" if spec.required_if else "opcional")
        description = " ".join(spec.description.split()).rstrip(".") + "."
        options = f" Opciones: {', '.join(spec.options)}." if spec.options else ""
        question = "" if "No se pregunta" in description else f" Pregunta sugerida: {spec.question.strip()}"
        fields.append(f"- {name} ({need}): {description}{options}{question}")
    outcomes = [f"- {o.label}{' (si ' + describe_condition(o.when) + ')' if o.when else ' (en cualquier otro caso)'}: "
                f"{' '.join(o.message.split())}" for o in workflow.completion.outcomes]
    rules = "\n".join(f"- {r}" for r in workflow.conversation.rules)
    return f"""Sos {workflow.agent.name}, {workflow.agent.role}. {where}; idioma: {workflow.agent.language}.

OBJETIVO:
{workflow.objective.description.strip()}

DATOS A OBTENER, en este orden salvo que el usuario los dé antes. Los nombres son internos: nunca los digas. Las preguntas son sugerencias, reformulalas para que la conversación sea natural. No vuelvas a preguntar lo que el usuario ya respondió.
{chr(10).join(fields)}

REGLAS:
{rules}
- Hacé normalmente una pregunta por turno.
- Nunca inventes datos del usuario ni información del producto.

BASE DE CONOCIMIENTO:
{workflow.knowledge.strip()}

CIERRE:
La conversación termina cuando obtuviste los datos obligatorios o cuando el usuario no quiere seguir. En ese turno despedite usando como guía el mensaje que corresponda:
{chr(10).join(outcomes)}
Al final de ese último mensaje, y solo en ese, escribí {END_MARKER}.{extra}

{reply}"""


def build_classic_messages(workflow: Workflow, state: ConversationState, user_message: str,
                           omitted: int = 0) -> list[dict]:
    """Por WhatsApp, los mensajes del usuario que llegaron como audio llevan
    VOICE_NOTE_TAG (los del agente no) y, si la respuesta sale como nota de voz,
    el mensaje nuevo termina con VOICE_NOTE_REPLY.

    omitted: mensajes viejos sacados por el contexto (state ya viene sin ellos); el aviso
    va al final del prompt de sistema, no como mensaje, para no romper la alternancia."""
    whatsapp = state.channel == "whatsapp"
    history = [{"role": m.role, "content": _classic_text(m.text, whatsapp and m.role == "user" and m.voice_note)}
               for m in state.messages]
    media = state.media if whatsapp else None
    content = _classic_text(user_message, bool(media and media.user_voice_note))
    if media and media.reply_voice_note:
        content += VOICE_NOTE_REPLY
    system = build_classic_system(workflow, state.channel)
    if omitted:
        system += f"\n\n{omitted_note(omitted)}"
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": content}]


def _classic_text(text: str, voice_note: bool) -> str:
    return f"{VOICE_NOTE_TAG} {text}" if voice_note else text
