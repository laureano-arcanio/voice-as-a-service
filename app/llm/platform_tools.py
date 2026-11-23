"""Herramientas de la plataforma: terminar la conversacion y pasar la llamada a una persona. Las ve el modelo
junto con las del cliente (function calling); no se ejecutan: cambian el estado del turno y el worker corta o
deriva despues de decir lo que el modelo escribio en ese mensaje. Las usa el motor con el LLM de Atentina (o
BYOK) y con tu propio agente (app/llm/external.py)."""
import json

from ..conversation.models import AgentTurn, ConversationState, Workflow
from ..conversation.workflow import OFF_TOPIC_ID

END_CALL = "end_call"
TRANSFER_CALL = "transfer_call"
REPEAT_LAST = "repeat_last_reply"
NAMES = (END_CALL, TRANSFER_CALL, REPEAT_LAST)
# Motivo de end_call: fuera de tema corta sin completar; cualquier otro cierre va con terminada.
FINISHED, OFF_TOPIC_REASON = "terminada", OFF_TOPIC_ID


def end_call_tool() -> dict:
    """motivo: terminada (cierre normal) o fuera de tema (la conversacion no tenia que ver con el objetivo)."""
    return {"type": "function", "function": {
        "name": END_CALL,
        "description": "Termina la conversacion despues de decir lo que escribiste en este mensaje (la despedida).",
        "parameters": {"type": "object", "properties": {
            "motivo": {"type": "string", "enum": [FINISHED, OFF_TOPIC_REASON],
                       "description": f"{OFF_TOPIC_REASON}: la conversacion no tiene que ver con el objetivo "
                                      f"del agente. {FINISHED}: cualquier otro cierre."}},
            "required": []},
    }}


def repeat_last_reply_tool() -> dict:
    """Repite la ultima respuesta tal cual (docs/features/ATENCION_TURNO.md): la sustitucion la hace el motor
    (app/conversation/engine.py), que ademas respeta el texto si el modelo escribio algo."""
    return {"type": "function", "function": {
        "name": REPEAT_LAST,
        "description": "Cuando la persona pide que repitas, dice que no escuchó o contesta con una duda, repetí "
                       "la última respuesta tal cual. No escribas texto en este turno: llamá a esta herramienta "
                       "y nada más.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }}


def transfer_call_tool(areas: list[dict], channel: str = "voice") -> dict:
    """Las areas de la conversacion (state.progress.handoff_areas): nombre, cuando pasarla, horario y si atiende ahora.
    Una cerrada que redirige fuera de horario atiende igual: sigue por el area siguiente."""
    from ..services.handoff import is_open     # services importa conversation: aca, para no hacer un ciclo
    lines = []
    for a in areas:
        when = " ".join((a.get("when") or "").split()).rstrip(".")
        hours = a.get("schedule_text") or ""
        now = "atiende ahora" if is_open(a.get("schedule")) or a.get("redirects") else "cerrada ahora"
        lines.append(f"{a['name']}{' (' + when + ')' if when else ''}: {hours + ', ' if hours else ''}{now}")
    return {"type": "function", "function": {
        "name": TRANSFER_CALL,
        "description": (f"Pasa la {'conversacion' if channel == 'whatsapp' else 'llamada'} a una persona del equipo del "
                        "area, despues de decir lo que escribiste en este mensaje. Areas: " + "; ".join(lines)),
        "parameters": {"type": "object", "properties": {"area": {"type": "string", "enum": [a["name"] for a in areas]}},
                       "required": ["area"]},
    }}


def tools_for(state: ConversationState, workflow: Workflow | None = None) -> list[dict]:
    """end_call siempre; transfer_call si la conversacion tiene areas. Por WhatsApp de texto las llena _turn, solo las
    que tienen plantilla (app/whatsapp/service.py). repeat_last_reply solo en voz y solo si el agente activo la
    atencion del turno con la repeticion (turn_attention; una definicion sin el bloque no cambia nada); el workflow
    lo tienen los tres callers (clientes LLM y agente propio), nunca la vista previa del editor."""
    tools = [end_call_tool()]
    if state.channel == "voice" and workflow is not None:
        attention = workflow.turn_attention
        if attention is not None and attention.enabled and attention.repeat_last_reply:
            tools.append(repeat_last_reply_tool())
    if state.progress.handoff_areas:
        tools.append(transfer_call_tool(state.progress.handoff_areas, state.channel))
    return tools


def _args(raw: str) -> dict:
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


def apply(turn: AgentTurn, calls: list[dict], state: ConversationState) -> None:
    """Las llamadas a end_call, transfer_call y repeat_last_reply ({name, arguments}) en el turno. Solo lee las
    claves que conoce: un argumento desconocido (ej. un `outcome` de un endpoint viejo) se ignora sin error.
    Cortar gana: no se deriva una conversacion terminada. repeat_last_reply no cambia status: un turno repetido
    no completa ni dispara la extraccion."""
    for call in calls:
        args = _args(call.get("arguments") or "")
        if call["name"] == END_CALL:
            turn.status = "completed"
            if args.get("motivo") == OFF_TOPIC_REASON:
                turn.end_reason = "off_topic"
        elif call["name"] == TRANSFER_CALL and isinstance(args.get("area"), str) and state.progress.handoff_areas:
            turn.handoff = args["area"]
        elif call["name"] == REPEAT_LAST:
            turn.repeat = True
    if turn.status == "completed":
        turn.handoff = None
