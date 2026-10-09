"""Conversacion por texto con un agente (sin llamada): para probar el motor por API."""
import logging

from fastapi import APIRouter, Depends

from ...config import settings
from ...conversation.store import ConversationConflict
from ...llm.errors import LLMContextError
from ...models import Agent, CallRow
from ...services.errors import Conflict, Invalid, NotFound, ServiceError, Upstream
from ...services.ratelimit import Limit
from ..deps import (
    DB,
    ActiveClientPrincipal,
    CurrentPrincipal,
    Engine,
    ensure_client_active,
    rate_limit,
)
from ..schemas import (
    ConversationIn,
    ConversationStartOut,
    ConversationStateOut,
    TurnIn,
    TurnOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])

# Turnos en curso en este proceso (la app corre en uno): dos turnos a la vez sobre la
# misma conversacion se cruzarian (el segundo no ve la respuesta del primero).
_in_progress: set[str] = set()


class LlmBusy(ServiceError):
    status_code = 503
    default_code = "llm_busy"
    retry_after = 5


class _TurnSlots:
    """Turnos de texto por la API en curso en este proceso, de todos los clientes. El LLM es
    el de las llamadas: el limite por hora de cada cliente no frena muchos turnos a la vez
    (60 conversaciones con un turno cada una superan las 32 secuencias de Gemma, H04)."""
    in_use = 0


def _state(engine, p, conversation_id: str):
    state = engine.store.get(conversation_id)
    if state is None or not p.can_access(state.client_id):
        raise NotFound("Conversación inexistente")
    return state


# Cada turno es un pedido al LLM: tope por cliente (todas sus API keys y usuarios juntos,
# H12); el admin cuenta por si mismo.
_new_limit = rate_limit("conversations", lambda: Limit(settings.rate_conversations_per_hour, 3600), per="client")
_turn_limit = rate_limit("turns", lambda: Limit(settings.rate_turns_per_hour, 3600), per="client")


@router.post("", status_code=201, response_model=ConversationStartOut, dependencies=[Depends(_new_limit)])
def start_conversation(body: ConversationIn, p: ActiveClientPrincipal, db: DB, engine: Engine):
    agent = db.get(Agent, body.agent_id)
    if agent is None or not p.can_access(agent.client_id):
        raise NotFound("Agente inexistente")
    # Tambien para un admin: el cliente del agente esta inactivo (solo lectura, H12).
    ensure_client_active(db, agent.client_id)
    try:
        state, message = engine.start_conversation(agent.id, client_id=agent.client_id)
    except KeyError:
        raise NotFound("Agente inexistente o archivado") from None
    return {"conversation_id": state.conversation_id, "message": message, "state": state}


@router.get("/{conversation_id}", response_model=ConversationStateOut)
def get_conversation(conversation_id: str, p: CurrentPrincipal, engine: Engine):
    return _state(engine, p, conversation_id)


@router.post("/{conversation_id}/turns", response_model=TurnOut, dependencies=[Depends(_turn_limit)],
             responses={502: {"description": "El LLM no respondio"},
                        422: {"description": "La conversacion no entra en el contexto del modelo (context_too_long)"},
                        503: {"description": "Demasiados turnos de texto a la vez (llm_busy, Retry-After)"},
                        409: {"description": "Conversacion de WhatsApp, de una llamada, terminada o con un turno "
                                            "en curso"}})
async def turn(conversation_id: str, body: TurnIn, p: ActiveClientPrincipal, db: DB, engine: Engine):
    state = _state(engine, p, conversation_id)
    if state.channel == "whatsapp":
        # La respuesta no le llegaria al contacto, y el turno se cruzaria con el de WhatsApp (su lock).
        raise Conflict("La conversación es de WhatsApp: los turnos llegan por WhatsApp", "whatsapp_conversation")
    # Una llamada (en curso o terminada) la escribe el worker de voz: un turno por la API
    # pisaria su estado o reescribiria una llamada ya facturada (H08).
    has_call = db.get(CallRow, conversation_id) is not None
    # Tambien para un admin que prueba el agente de un cliente inactivo (H12).
    ensure_client_active(db, state.client_id)
    db.close()      # no retener la conexion mientras responde el LLM (H07)
    if has_call:
        raise Conflict("La conversación es de una llamada: no admite turnos por texto", "call_conversation")
    if state.status == "completed":
        raise Conflict("La conversación ya terminó", "conversation_completed")
    if conversation_id in _in_progress:
        raise Conflict("Hay un turno en curso en esta conversación", "turn_in_progress")
    if _TurnSlots.in_use >= settings.api_max_concurrent_turns:
        raise LlmBusy("Hay muchas conversaciones de texto en curso. Probá en unos segundos.")
    _in_progress.add(conversation_id)
    _TurnSlots.in_use += 1      # cubre el turno y la extraccion que se espera abajo
    try:
        _, result = await engine.process_turn(conversation_id, body.message)
        # Por la API no hay audio que tape la extraccion: se espera y se devuelve el estado con los datos.
        await engine.wait_extraction(conversation_id)
    except ConversationConflict:
        raise Conflict("La conversación cambió mientras se procesaba el turno", "conversation_conflict") from None
    except LLMContextError:
        # No es una falla del LLM: la conversacion ya no entra en el contexto (H11).
        raise Invalid("La conversación es demasiado larga para el modelo: empezá otra", "context_too_long") from None
    except Exception as e:
        logger.exception("turno por texto %s", conversation_id)
        raise Upstream(f"El LLM no respondió: {type(e).__name__}") from e
    finally:
        _in_progress.discard(conversation_id)
        _TurnSlots.in_use -= 1
    return {"message": result.assistant_message, "state": engine.store.get(conversation_id),
            "next_objective": result.next_objective, "status": result.status}
