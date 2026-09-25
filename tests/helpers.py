import json

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, Extraction, Message

BASE = {
    "contact_name": "Juan", "company_name": "Acme", "company_activity": "Logística",
    "employee_count": 80, "workforce_location": "Calle", "attendance_process": "Planillas",
    "main_problem": "Control horario", "desired_timeline": "Este mes", "decision_maker": "Él mismo",
}


class FakeLLM:
    """turns: salidas del LLM de conversacion; extractions: datos que devuelve
    cada extraccion, en orden (sin mas, no encuentra nada)."""

    def __init__(self, *turns: AgentTurn, extractions: list[dict] = ()):
        self.turns = list(turns)
        self.extractions = list(extractions)
        self.calls = []
        self.extract_calls = []

    async def process_turn(self, workflow, state, user_message, on_message=None):
        self.calls.append((user_message, dict(state.progress.rejected)))
        turn = self.turns.pop(0)
        turn.raw = json.dumps(turn.model_dump(), ensure_ascii=False)
        return turn

    async def converse(self, workflow, state, user_message, on_message=None):
        return await self.process_turn(workflow, state, user_message, on_message)

    async def extract(self, workflow, state, only=None):
        self.extract_calls.append(only)
        fields = self.extractions.pop(0) if self.extractions else {}
        return Extraction(fields=fields, raw=json.dumps(fields, ensure_ascii=False))


def start_with(engine: ConversationEngine, last_question: str | None = None, workflow_id="sales_discovery", **fields):
    state, _ = engine.start_conversation(workflow_id)
    state.fields.update(fields)
    if last_question:
        state.messages += [Message(role="user", text="..."), Message(role="assistant", text=last_question)]
    engine.store.save(state)
    return state.conversation_id


async def turn_and_extract(engine: ConversationEngine, cid: str, message: str):
    """Un turno y su extraccion: el estado como queda para el turno siguiente."""
    _, turn = await engine.process_turn(cid, message)
    await engine.wait_extraction(cid)
    return engine.store.get(cid), turn
