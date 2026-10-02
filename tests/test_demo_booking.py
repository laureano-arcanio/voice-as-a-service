"""Workflow demo_booking: tipos y clasificacion del resultado (el flujo lo decide el LLM)."""
import pytest

from app.agents.templates import load_reference
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.conversation.workflow import validate_updates

from .helpers import FakeLLM, start_with, turn_and_extract


@pytest.fixture
def wf():
    return load_reference("demo_booking")


def test_types(wf):
    assert validate_updates(wf, {"demo_answer": "Sí"}) == {"demo_answer": "si"}
    assert validate_updates(wf, {"demo_answer": "tal vez"}) == {}
    assert validate_updates(wf, {"contact": "+54 9 351 555-1234"}) == {"contact": "+5493515551234"}
    assert validate_updates(wf, {"contact": "juan arroba acme punto com"}) == {"contact": "juan@acme.com"}
    assert validate_updates(wf, {"contact": "no sé"}) == {}


@pytest.mark.parametrize("fields, outcome", [
    ({"wants_pitch": False}, "no_pitch"),
    ({"wants_pitch": True, "company_context": "Logística", "demo_answer": "si", "contact_name": "Ana",
      "contact": "ana@x.com"}, "demo"),
    ({"wants_pitch": True, "demo_answer": "dudas", "callback_wanted": True}, "callback"),
    ({"wants_pitch": True, "demo_answer": "no"}, "no_interest"),
])
async def test_outcomes(store, fields, outcome):
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message="Chau.", status="completed")), store)
    cid = start_with(engine, agent_id="demo_booking", **fields)
    state, _ = await turn_and_extract(engine, cid, "Chau.")
    assert state.progress.outcome == outcome


def test_outcome_without_saved_outcome(wf):
    # Si termino antes de guardar el resultado, se calcula al vuelo. Antes daba
    # AttributeError (500 en GET /api/calls/{id} en el loadtest de 64).
    from app.models import ConversationRow
    from app.services.reports import Reports
    conv = ConversationRow(id="c1", agent_id="demo_booking", status="completed", fields={"wants_pitch": False})
    assert Reports(None, None).outcome(wf, conv).id == "no_pitch"
