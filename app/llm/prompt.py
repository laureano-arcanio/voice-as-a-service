import json

import yaml

from app.conversation.models import ConversationState, Workflow
from app.conversation.workflow import pending_fields

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


def render_workflow(workflow: Workflow) -> str:
    return yaml.safe_dump(workflow.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False, width=1000)


def render_conversation(state: ConversationState) -> str:
    """Toda la conversacion: con solo el ultimo intercambio, el LLM no veia un
    dato que no habia guardado y lo volvia a preguntar ("ya te dije antes")."""
    return "\n".join(f"{'agente' if m.role == 'assistant' else 'usuario'}: {m.text}" for m in state.messages)


def build_user_prompt(workflow: Workflow, state: ConversationState, user_message: str) -> str:
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
    # La conversacion va antes del estado: crece al final y el resto no cambia,
    # asi vLLM reusa el prefijo (prefix caching) del turno anterior.
    return (
        f"WORKFLOW:\n{render_workflow(workflow)}\n"
        f"CONVERSATION:\n{render_conversation(state)}\n\n"
        f"CURRENT STATE:\n{json.dumps(current, ensure_ascii=False, indent=2)}\n\n"
        f"NEW USER MESSAGE:\n{user_message}"
    )


def render_fields(workflow: Workflow, only: list[str] | None = None) -> str:
    """Los campos tal como los define el workflow: la extraccion sale de la
    configuracion del agente, no de un prompt por cliente."""
    fields = {name: spec.model_dump(include={"type", "options", "description", "question"}, exclude_none=True)
              for name, spec in sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)
              if only is None or name in only}
    return yaml.safe_dump(fields, allow_unicode=True, sort_keys=False, width=1000)


def build_extraction_prompt(workflow: Workflow, state: ConversationState, only: list[str] | None = None) -> str:
    focus = f"Devolvé solo el campo {', '.join(only)}: el agente lo preguntó y el usuario lo respondió.\n\n" if only else ""
    known = {k: v for k, v in state.fields.items() if v is not None and (only is None or k in only)}
    return (
        f"AGENTE: {workflow.agent.name}, {workflow.agent.role}.\n"
        f"OBJETIVO DE LA LLAMADA: {workflow.objective.description.strip()}\n\n"
        f"CAMPOS:\n{render_fields(workflow, only)}\n"
        f"CONVERSATION:\n{render_conversation(state)}\n\n"
        f"KNOWN FIELDS:\n{json.dumps(known, ensure_ascii=False)}\n\n"
        f"{focus}Devolvé el valor de cada campo según la conversación."
    )


# ---------- motor clasico ----------

# Marca de fin: el modelo la agrega al despedirse y no se dice (el texto va
# directo al TTS, sin JSON donde poner un status).
END_MARKER = "[FIN]"


def describe_condition(when: dict) -> str:
    return " y ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in when.items())


def build_classic_system(workflow: Workflow) -> str:
    """Todo el agente en un prompt de sistema, sacado del YAML."""
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
    return f"""Sos {workflow.agent.name}, {workflow.agent.role}. Estás en una llamada telefónica; idioma: {workflow.agent.language}.

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
Al final de ese último mensaje, y solo en ese, escribí {END_MARKER}.

Respondé solo con lo que decís en voz alta."""


def build_classic_messages(workflow: Workflow, state: ConversationState, user_message: str) -> list[dict]:
    history = [{"role": m.role, "content": m.text} for m in state.messages]
    return [{"role": "system", "content": build_classic_system(workflow)}, *history,
            {"role": "user", "content": user_message}]
