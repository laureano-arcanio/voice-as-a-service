import json

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, Message

BASE = {
    "contact_name": "Juan", "company_name": "Acme", "company_activity": "Logística",
    "employee_count": 80, "workforce_location": "Calle", "attendance_process": "Planillas",
    "main_problem": "Control horario", "desired_timeline": "Este mes", "decision_maker": "Él mismo",
}


class FakeLLM:
    def __init__(self, *turns: AgentTurn):
        self.turns = list(turns)
        self.calls = []

    async def process_turn(self, workflow, state, user_message):
        self.calls.append((user_message, dict(state.progress.rejected)))
        turn = self.turns.pop(0)
        turn.raw = json.dumps(turn.model_dump(), ensure_ascii=False)
        return turn


def start_with(engine: ConversationEngine, last_question: str | None = None, workflow_id="sales_discovery", **fields):
    state, _ = engine.start_conversation(workflow_id)
    state.fields.update(fields)
    if last_question:
        state.messages += [Message(role="user", text="..."), Message(role="assistant", text=last_question)]
    engine.store.save(state)
    return state.conversation_id
