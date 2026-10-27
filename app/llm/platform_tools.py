"""Herramientas de la plataforma: terminar la conversacion y pasar la llamada a una persona. Las ve el modelo
junto con las del cliente (function calling); no se ejecutan: cambian el estado del turno y el worker corta o
deriva despues de decir lo que el modelo escribio en ese mensaje. Las usa el motor con el LLM de Atentina (o
BYOK) y con tu propio agente (app/llm/external.py)."""
import json

from ..conversation.models import AgentTurn, ConversationState
from ..conversation.workflow import OFF_TOPIC

END_CALL = "end_call"
TRANSFER_CALL = "transfer_call"
NAMES = (END_CALL, TRANSFER_CALL)
# Motivo de end_call con el LLM de Atentina: el resultado sale de los datos (extraccion); fuera de tema, no.
FINISHED, OFF_TOPIC_REASON = "terminada", OFF_TOPIC.id


def end_call_tool(outcomes: list[str] | None = None) -> dict:
    """outcomes: con tu propio agente, los ids de completion.outcomes (el resultado lo elige el agente). Sin
    outcomes, el motivo: terminada (el resultado sale de los datos) o fuera de tema."""
    if outcomes is not None:
        param = {"outcome": {"type": "string", "enum": outcomes,
                             "description": "Resultado de la conversacion; sin el, el resultado por defecto."}}
    else:
        param = {"motivo": {"type": "string", "enum": [FINISHED, OFF_TOPIC_REASON],
                            "description": f"{OFF_TOPIC_REASON}: la conversacion no tiene que ver con el objetivo "
                                           f"del agente. {FINISHED}: cualquier otro cierre."}}
    return {"type": "function", "function": {
        "name": END_CALL,
        "description": "Termina la conversacion despues de decir lo que escribiste en este mensaje (la despedida).",
        "parameters": {"type": "object", "properties": param, "required": []},
    }}


def transfer_call_tool(areas: list[dict]) -> dict:
    """Las areas de la llamada (state.progress.handoff_areas): nombre, cuando pasarla, horario y si atiende ahora."""
    from ..services.handoff import is_open     # services importa conversation: aca, para no hacer un ciclo
    lines = []
    for a in areas:
        when = " ".join((a.get("when") or "").split()).rstrip(".")
        hours = a.get("schedule_text") or ""
        now = "atiende ahora" if is_open(a.get("schedule")) else "cerrada ahora"
        lines.append(f"{a['name']}{' (' + when + ')' if when else ''}: {hours + ', ' if hours else ''}{now}")
    return {"type": "function", "function": {
        "name": TRANSFER_CALL,
        "description": ("Pasa la llamada a una persona del equipo del area, despues de decir lo que escribiste en "
                        "este mensaje. Areas: " + "; ".join(lines)),
        "parameters": {"type": "object", "properties": {"area": {"type": "string", "enum": [a["name"] for a in areas]}},
                       "required": ["area"]},
    }}


def tools_for(state: ConversationState, outcomes: list[str] | None = None) -> list[dict]:
    """end_call siempre; transfer_call en una llamada con areas."""
    tools = [end_call_tool(outcomes)]
    if state.channel == "voice" and state.progress.handoff_areas:
        tools.append(transfer_call_tool(state.progress.handoff_areas))
    return tools


def _args(raw: str) -> dict:
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


def apply(turn: AgentTurn, calls: list[dict], state: ConversationState) -> str | None:
    """Las llamadas a end_call y transfer_call ({name, arguments}) en el turno. Devuelve el outcome de end_call
    si vino (tu propio agente). Cortar gana: no se deriva una conversacion terminada."""
    outcome = None
    for call in calls:
        args = _args(call.get("arguments") or "")
        if call["name"] == END_CALL:
            turn.status = "completed"
            if args.get("motivo") == OFF_TOPIC_REASON:
                turn.end_reason = "off_topic"
            if isinstance(args.get("outcome"), str):
                outcome = args["outcome"]
        elif call["name"] == TRANSFER_CALL and isinstance(args.get("area"), str) and state.progress.handoff_areas:
            turn.handoff = args["area"]
    if turn.status == "completed":
        turn.handoff = None
    return outcome
