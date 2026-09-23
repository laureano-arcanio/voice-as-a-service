import uuid

from .models import AgentTurn, ConversationState, Message
from .store import ConversationStore
from .workflow import completion_message, load_workflow, pending_fields, validate_updates


class ConversationEngine:
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

        result = await self.llm.process_turn(workflow, state, user_message)
        updates = validate_updates(workflow, result.field_updates)
        state.fields.update(updates)

        pending = pending_fields(workflow, state)
        if pending:
            next_objective = result.next_objective if result.next_objective in pending else pending[0]
            message = result.assistant_message if result.status == "active" else workflow.fields[pending[0]].question.strip()
            turn = AgentTurn(field_updates=updates, next_objective=next_objective, assistant_message=message, status="active")
        else:
            turn = AgentTurn(field_updates=updates, next_objective=None, assistant_message=completion_message(workflow, state), status="completed")

        state.status = turn.status
        state.messages += [Message(role="user", text=user_message), Message(role="assistant", text=turn.assistant_message)]
        self.store.save(state)
        return state, turn
