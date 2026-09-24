"""Workflow berlin_signup: tipos y clasificacion del resultado (el flujo lo decide el LLM)."""
import pytest

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.conversation.workflow import load_workflow, pending_fields, validate_updates

from .helpers import FakeLLM, start_with, turn_and_extract
from .test_workflow import state_with


@pytest.fixture
def wf():
    return load_workflow("berlin_signup")


def test_types(wf):
    assert validate_updates(wf, {"wants_link": "true"}) == {"wants_link": True}
    assert validate_updates(wf, {"contact": "+54 9 351 555-1234"}) == {"contact": "+5493515551234"}
    assert validate_updates(wf, {"contact": "ana arroba gmail punto com"}) == {"contact": "ana@gmail.com"}


def test_contact_only_if_other_number(wf):
    base = {"wants_pitch": True, "activity": "pilates", "zone": "Nueva Córdoba", "wants_link": True}
    assert pending_fields(wf, state_with(wf, **base)) == ["same_number", "contact_name"]
    assert pending_fields(wf, state_with(wf, **base, same_number=False)) == ["contact", "contact_name"]


@pytest.mark.parametrize("fields, outcome", [
    ({"wants_pitch": False}, "no_pitch"),
    ({"wants_pitch": True, "activity": "yoga", "zone": "centro", "wants_link": True,
      "same_number": True, "contact_name": "Ana"}, "link"),
    ({"wants_pitch": True, "activity": "boxeo", "zone": "Urca", "wants_link": False}, "no_interest"),
    ({"wants_pitch": True, "zone": "centro", "wants_link": True}, "incompleta"),   # 80ac0e22
])
async def test_outcomes(store, fields, outcome):
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message="Chau.", status="completed")), store)
    cid = start_with(engine, workflow_id="berlin_signup", **fields)
    state, _ = await turn_and_extract(engine, cid, "Chau.")
    assert state.progress.outcome == outcome
