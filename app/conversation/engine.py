import time
import uuid

from .models import AgentTurn, ConversationState, Message
from .store import ConversationStore
from .workflow import check_updates, load_workflow, outcome_for


class ConversationEngine:
    """El LLM decide la respuesta, el objetivo siguiente y si la conversacion
    termino. La app valida los datos que propone y guarda el estado."""

    def __init__(self, llm, store: ConversationStore):
        self.llm = llm
        self.store = store

    def start_conversation(self, workflow_id: str) -> tuple[ConversationState, str]:
        workflow = load_workflow(workflow_id)
        opening = workflow.conversation.opening
        state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            fields={name: None for name in workflow.fields},
            messages=[Message(role="assistant", text=opening)],
        )
        self.store.save(state)
        return state, opening

    async def process_turn(self, conversation_id: str, user_message: str) -> tuple[ConversationState, AgentTurn]:
        state = self.store.get(conversation_id)
        if state is None:
            raise KeyError(conversation_id)
        workflow = load_workflow(state.workflow_id)
        undo = state.model_dump(include={"status", "fields", "progress"}, exclude={"progress": {"undo"}})
        undo["n_messages"] = len(state.messages)

        started = time.perf_counter()
        result = await self.llm.process_turn(workflow, state, user_message)
        trace = [{"kind": "turno", "input": user_message, "ms": round((time.perf_counter() - started) * 1000),
                  "reasoning": result.reasoning, "output": result.raw or result.model_dump_json()}]

        # Solo validacion de datos: campos inexistentes o con tipo invalido no se
        # guardan, y los invalidos se le informan al LLM en el turno siguiente.
        updates, state.progress.rejected = check_updates(workflow, result.field_updates, user_message)
        state.fields.update(updates)
        state.status = result.status
        state.progress.outcome = outcome_for(workflow, state).id if result.status == "completed" else None
        state.progress.undo = undo

        turn = AgentTurn(field_updates=updates, next_objective=result.next_objective,
                         assistant_message=result.assistant_message, status=result.status)
        state.messages += [Message(role="user", text=user_message),
                           Message(role="assistant", text=turn.assistant_message, llm=trace)]
        self.store.save(state)
        return state, turn

    def retract_last_turn(self, conversation_id: str) -> bool:
        """Deshace el ultimo turno. Para cuando el cliente siguio hablando y la
        respuesta no llego a sonar: el turno siguiente trae el mensaje completo."""
        state = self.store.get(conversation_id)
        if state is None or state.progress.undo is None:
            return False
        undo = state.progress.undo
        state.messages = state.messages[:undo.pop("n_messages")]
        restored = ConversationState.model_validate({**state.model_dump(), **undo})
        self.store.save(restored)
        return True
