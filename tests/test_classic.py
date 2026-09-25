"""Motor clasico: prompt armado del YAML, conversacion multiturno en texto, sin
estado por turno y una sola extraccion al final."""
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, ConversationState, Message
from app.conversation.workflow import load_workflow
from app.llm.client import MarkerFilter
from app.llm.prompt import END_MARKER, build_classic_messages, build_classic_system

from .helpers import FakeLLM, turn_and_extract


def test_extends_keeps_the_agent_and_changes_the_engine():
    base, classic = load_workflow("berlin_signup"), load_workflow("berlin_signup_classic")
    assert (base.engine, classic.engine) == ("structured", "classic")
    assert classic.knowledge == base.knowledge and classic.fields == base.fields


def test_the_system_prompt_comes_from_the_yaml():
    wf = load_workflow("berlin_signup_classic")
    system = build_classic_system(wf)
    assert wf.conversation.rules[0] in system
    assert "Live Running Team" in system                                  # base de conocimiento
    assert "¿Qué actividad te gustaría hacer, o qué estás buscando?" in system
    assert "contact (obligatorio si same_number = false)" in system
    assert END_MARKER in system


def test_the_conversation_goes_as_messages():
    wf = load_workflow("berlin_signup_classic")
    state = ConversationState(conversation_id="c", workflow_id=wf.id, fields={},
                              messages=[Message(role="assistant", text="Hola."), Message(role="user", text="Hola."),
                                        Message(role="assistant", text="¿Qué actividad?")])
    messages = build_classic_messages(wf, state, "Yoga.")
    assert [m["role"] for m in messages] == ["system", "assistant", "user", "assistant", "user"]
    assert messages[-1]["content"] == "Yoga."


def test_the_end_marker_is_not_said_even_split_in_chunks():
    marker = MarkerFilter(END_MARKER)
    said = "".join(marker.feed(c) for c in ["¡Chau", ", que tengas", " un lindo día! [F", "IN", "]"]) + marker.flush()
    assert said == "¡Chau, que tengas un lindo día! " and marker.found
    other = MarkerFilter(END_MARKER)
    assert "".join(other.feed(c) for c in ["El [", "precio] varía."]) + other.flush() == "El [precio] varía."
    assert not other.found


async def test_no_extraction_until_the_end(store):
    llm = FakeLLM(AgentTurn(assistant_message="¿Por qué zona?"),
                  AgentTurn(assistant_message="Listo, te mando el link.", status="completed"),
                  extractions=[{"wants_pitch": True, "activity": "yoga", "zone": "Centro", "wants_link": True,
                                "same_number": True, "contact_name": "Ana"}])
    engine = ConversationEngine(llm, store)
    state, _ = engine.start_conversation("berlin_signup_classic")
    cid = state.conversation_id
    state, _ = await turn_and_extract(engine, cid, "Sí, quiero hacer yoga.")
    assert llm.extract_calls == [] and all(v is None for v in state.fields.values())
    state, _ = await turn_and_extract(engine, cid, "En el centro. Soy Ana, mandalo a este número.")
    assert llm.extract_calls == [None]
    assert state.status == "completed" and state.progress.outcome == "link"
    assert [c["kind"] for c in state.messages[-1].llm] == ["turno", "extraccion"]


async def test_hangup_extracts_without_outcome(store):
    llm = FakeLLM(AgentTurn(assistant_message="¿Por qué zona?"), extractions=[{"activity": "yoga"}])
    engine = ConversationEngine(llm, store)
    state, _ = engine.start_conversation("berlin_signup_classic")
    cid = state.conversation_id
    await turn_and_extract(engine, cid, "Yoga.")
    await engine.finish(cid)
    state = store.get(cid)
    assert state.fields["activity"] == "yoga" and state.progress.outcome is None


async def test_structured_finish_does_not_extract_again(store):
    llm = FakeLLM(AgentTurn(next_objective="zone", assistant_message="¿Por qué zona?"), extractions=[{"activity": "yoga"}])
    engine = ConversationEngine(llm, store)
    state, _ = engine.start_conversation("berlin_signup")
    await turn_and_extract(engine, state.conversation_id, "Yoga.")
    await engine.finish(state.conversation_id)
    assert llm.extract_calls == [None]
