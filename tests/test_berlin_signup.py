"""Workflow berlin_signup: tipos (el flujo lo decide el LLM)."""
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


async def test_completing_leaves_no_outcome(store):
    """El resultado de agente ya no existe: cualquier cierre normal queda sin outcome."""
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message="Chau.", status="completed")), store)
    cid = start_with(engine, agent_id="berlin_signup", wants_pitch=False)
    state, _ = await turn_and_extract(engine, cid, "Chau.")
    assert state.status == "completed" and state.progress.outcome is None
