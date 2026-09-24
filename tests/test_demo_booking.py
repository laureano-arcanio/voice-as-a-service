"""Workflow demo_booking: tipos y clasificacion del resultado (el flujo lo decide el LLM)."""
import pytest

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.conversation.workflow import load_workflow, validate_updates

from .helpers import FakeLLM, start_with


@pytest.fixture
def wf():
    return load_workflow("demo_booking")


def test_types(wf):
    assert validate_updates(wf, {"demo_answer": "Sí"}) == {"demo_answer": "si"}
    assert validate_updates(wf, {"demo_answer": "tal vez"}) == {}
    assert validate_updates(wf, {"contact": "+54 9 351 555-1234"}) == {"contact": "+5493515551234"}
    assert validate_updates(wf, {"contact": "juan arroba acme punto com"}) == {"contact": "juan@acme.com"}
    assert validate_updates(wf, {"contact": "no sé"}) == {}


@pytest.mark.parametrize("fields, outcome", [
    ({"wants_pitch": False}, "no_pitch"),
    ({"wants_pitch": True, "demo_answer": "si", "contact_name": "Ana", "contact": "ana@x.com"}, "demo"),
    ({"wants_pitch": True, "demo_answer": "dudas", "callback_wanted": True}, "callback"),
    ({"wants_pitch": True, "demo_answer": "no"}, "no_interest"),
])
async def test_outcomes(store, fields, outcome):
    engine = ConversationEngine(FakeLLM(AgentTurn(field_updates={}, assistant_message="Chau.", status="completed")), store)
    cid = start_with(engine, workflow_id="demo_booking", **fields)
    state, _ = await engine.process_turn(cid, "Chau.")
    assert state.progress.outcome == outcome
