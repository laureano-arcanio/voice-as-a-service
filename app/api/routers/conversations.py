"""Conversacion por texto con un agente (sin llamada): para probar el motor por API."""
import logging

from fastapi import APIRouter

from ...models import Agent
from ...services.errors import Conflict, NotFound, Upstream
from ..deps import DB, CurrentPrincipal, Engine
from ..schemas import (
    ConversationIn,
    ConversationStartOut,
    ConversationStateOut,
    TurnIn,
    TurnOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


def _state(engine, p, conversation_id: str):
    state = engine.store.get(conversation_id)
    if state is None or not p.can_access(state.client_id):
        raise NotFound("Conversación inexistente")
    return state


@router.post("", status_code=201, response_model=ConversationStartOut)
def start_conversation(body: ConversationIn, p: CurrentPrincipal, db: DB, engine: Engine):
    agent = db.get(Agent, body.agent_id)
    if agent is None or not p.can_access(agent.client_id):
        raise NotFound("Agente inexistente")
    try:
        state, message = engine.start_conversation(agent.id, client_id=agent.client_id)
    except KeyError:
        raise NotFound("Agente inexistente o archivado") from None
    return {"conversation_id": state.conversation_id, "message": message, "state": state}


@router.get("/{conversation_id}", response_model=ConversationStateOut)
def get_conversation(conversation_id: str, p: CurrentPrincipal, engine: Engine):
    return _state(engine, p, conversation_id)


@router.post("/{conversation_id}/turns", response_model=TurnOut,
             responses={502: {"description": "El LLM no respondio"}})
async def turn(conversation_id: str, body: TurnIn, p: CurrentPrincipal, engine: Engine):
    if _state(engine, p, conversation_id).channel == "whatsapp":
        # La respuesta no le llegaria al contacto, y el turno se cruzaria con el de WhatsApp (su lock).
        raise Conflict("La conversación es de WhatsApp: los turnos llegan por WhatsApp", "whatsapp_conversation")
    try:
        _, result = await engine.process_turn(conversation_id, body.message)
    except Exception as e:
        logger.exception("turno por texto %s", conversation_id)
        raise Upstream(f"El LLM no respondió: {type(e).__name__}") from e
    # Por la API no hay audio que tape la extraccion: se espera y se devuelve el estado con los datos.
    await engine.wait_extraction(conversation_id)
    return {"message": result.assistant_message, "state": engine.store.get(conversation_id),
            "next_objective": result.next_objective, "status": result.status}
