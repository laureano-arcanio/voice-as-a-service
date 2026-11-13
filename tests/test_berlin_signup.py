"""Workflow berlin_signup: tipos y clasificacion del resultado (el flujo lo decide el LLM)."""
import pytest

from app.agents.templates import load_reference
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.conversation.workflow import validate_updates

from .helpers import FakeLLM, start_with, turn_and_extract


@pytest.fixture
def wf():
    return load_reference("berlin_signup")


def test_types(wf):
    assert validate_updates(wf, {"wants_link": "true"}) == {"wants_link": True}
    assert validate_updates(wf, {"contact": "+54 9 351 555-1234"}) == {"contact": "+5493515551234"}
    assert validate_updates(wf, {"contact": "ana@gmail.com"}) == {"contact": "ana@gmail.com"}
    # El email dictado no se convierte: lo que no es un email ni un telefono no se guarda.
    assert validate_updates(wf, {"contact": "ana arroba gmail punto com"}) == {}


@pytest.mark.parametrize("fields, outcome", [
    ({"wants_pitch": False}, "no_pitch"),
    ({"wants_pitch": True, "activity": "yoga", "zone": "centro", "wants_link": True,
      "same_number": True, "contact_name": "Ana"}, "link"),
    ({"wants_pitch": True, "activity": "boxeo", "zone": "Urca", "wants_link": False}, "no_interest"),
    # Sin datos obligatorios: el resultado sale de las condiciones (incompleta ya no se asigna).
    ({"wants_pitch": True, "zone": "centro", "wants_link": True}, "link"),
])
async def test_outcomes(store, fields, outcome):
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message="Chau.", status="completed")), store)
    cid = start_with(engine, agent_id="berlin_signup", **fields)
    state, _ = await turn_and_extract(engine, cid, "Chau.")
    assert state.progress.outcome == outcome
