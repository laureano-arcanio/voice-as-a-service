"""Conversacion por texto con un agente (sin llamada): para probar el motor por API."""
import asyncio
import logging

from fastapi import APIRouter, Depends

from ...config import settings
from ...conversation import workflows
from ...models import Agent
from ...services import calls
from ...services.errors import Conflict, NotFound, Upstream
from ...services.ratelimit import Limit
from ..deps import DB, CurrentPrincipal, Engine, rate_limit
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


# Cada turno es un pedido al LLM: tope por usuario o API key.
_new_limit = rate_limit("conversations", lambda: Limit(settings.rate_conversations_per_hour, 3600))
_turn_limit = rate_limit("turns", lambda: Limit(settings.rate_turns_per_hour, 3600))


@router.post("", status_code=201, response_model=ConversationStartOut, dependencies=[Depends(_new_limit)])
async def start_conversation(body: ConversationIn, p: CurrentPrincipal, db: DB, engine: Engine):
    """Con `caller_phone` o `workflows` (solo pruebas del panel; 403 panel_test_only con API key o el MCP): el
    numero simulado precarga los campos de telefono y llega a las herramientas; `workflows` corre el pre-call."""
    def create():
        agent = db.get(Agent, body.agent_id)
        if agent is None or not p.can_access(agent.client_id):
            raise NotFound("Agente inexistente")
        simulated = calls.panel_test(p, body.caller_phone, body.workflows)
        try:
            state, message = engine.new_conversation(agent.id, client_id=agent.client_id, phone=simulated)
        except KeyError:
            raise NotFound("Agente inexistente o archivado") from None
        state.progress.caller_phone = simulated
        state.progress.test_workflows = body.workflows
        engine.store.save(state)
        return state, message

    state, message = await asyncio.to_thread(create)
    if body.workflows:
        # La apertura queda renderizada con lo que trajo; si falla o vence, sigue sin datos (como en voz).
        message = await engine.run_pre_call(state.conversation_id) or message
        # Post-call `always`: corre al terminar el chat o tras TEXT_TEST_IDLE sin mensajes (docs/features/HERRAMIENTAS.md).
        await asyncio.to_thread(workflows.arm_text_test, engine.store.sessions, state.conversation_id,
                                engine.workflow(state))
    return {"conversation_id": state.conversation_id, "message": message,
            "state": engine.store.get(state.conversation_id)}


@router.get("/{conversation_id}", response_model=ConversationStateOut)
def get_conversation(conversation_id: str, p: CurrentPrincipal, engine: Engine):
    return _state(engine, p, conversation_id)


@router.post("/{conversation_id}/turns", response_model=TurnOut, dependencies=[Depends(_turn_limit)],
             responses={502: {"description": "El LLM no respondio"}})
async def turn(conversation_id: str, body: TurnIn, p: CurrentPrincipal, engine: Engine):
    state = _state(engine, p, conversation_id)
    if state.channel == "whatsapp":
        # La respuesta no le llegaria al contacto, y el turno se cruzaria con el de WhatsApp (su lock).
        raise Conflict("La conversación es de WhatsApp: los turnos llegan por WhatsApp", "whatsapp_conversation")
    testing = state.progress.test_workflows
    if testing:
        await asyncio.to_thread(workflows.touch_text_test, engine.store.sessions, conversation_id)
    try:
        _, result = await engine.process_turn(conversation_id, body.message)
    except Exception as e:
        logger.exception("turno por texto %s", conversation_id)
        raise Upstream(f"El LLM no respondió: {type(e).__name__}") from e
    # Por la API no hay audio que tape la extraccion: se espera y se devuelve el estado con los datos.
    await engine.wait_extraction(conversation_id)
    if testing and result.status == "completed":
        # Con lo extraido: de armed a pending; el loop lo corre. Si ya lo tomo al vencer, no cambia nada.
        await asyncio.to_thread(workflows.mark_ended, engine.store.sessions, conversation_id)
    return {"message": result.assistant_message, "state": engine.store.get(conversation_id),
            "status": result.status}
