"""El motor: prompt armado de la definicion, conversacion multiturno en texto, sin
estado por turno y una sola extraccion al final."""
from app.agents.templates import load_reference
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, ConversationState, Message
from app.llm.prompt import build_classic_messages, build_classic_system

from .helpers import FakeLLM, turn_and_extract


def test_the_classic_suffix_is_the_same_agent():
    base, classic = load_reference("berlin_signup"), load_reference("berlin_signup_classic")
    assert not hasattr(base, "engine") and base.external is None
    assert classic.knowledge == base.knowledge and classic.fields == base.fields


def test_the_system_prompt_comes_from_the_yaml():
    wf = load_reference("berlin_signup_classic")
    system = build_classic_system(wf)
    assert wf.conversation.rules[0] in system
    assert "Live Running Team" in system                                  # base de conocimiento
    assert "¿Qué actividad te gustaría hacer, o qué estás buscando?" in system
    assert "contact (obligatorio si same_number = false)" in system
    # Terminar es una herramienta (end_call), no una marca en el texto.
    assert "[FIN]" not in system


def test_the_conversation_goes_as_messages():
    wf = load_reference("berlin_signup_classic")
    state = ConversationState(conversation_id="c", agent_id=wf.id, fields={},
                              messages=[Message(role="assistant", text="Hola."), Message(role="user", text="Hola."),
                                        Message(role="assistant", text="¿Qué actividad?")])
    messages = build_classic_messages(wf, state, "Yoga.")
    assert [m["role"] for m in messages] == ["system", "assistant", "user", "assistant", "user"]
    assert messages[-1]["content"] == "Yoga."


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
    assert llm.extract_calls == [5]         # toda la conversacion: la apertura y los dos turnos
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


async def test_finish_after_completed_does_not_extract_again(store):
    llm = FakeLLM(AgentTurn(assistant_message="Listo, chau.", status="completed"), extractions=[{"activity": "yoga"}])
    engine = ConversationEngine(llm, store)
    state, _ = engine.start_conversation("berlin_signup")
    await turn_and_extract(engine, state.conversation_id, "Yoga.")
    await engine.finish(state.conversation_id)
    assert llm.extract_calls == [3]


# ---------- telefono (dato tipo phone): sin numero de la llamada, hay que pedirlo ----------

def _with_phone():
    wf = load_reference("berlin_signup_classic").model_copy(deep=True)   # la de referencia esta en cache
    from app.conversation.models import FieldSpec
    wf.fields["telefono"] = FieldSpec(priority=1, description="Teléfono de contacto", type="phone", required=True,
                                      question="¿A qué número te llamamos?")
    return wf


def _state(wf, **fields):
    return ConversationState(conversation_id="c", agent_id=wf.id, fields={n: None for n in wf.fields} | fields,
                             messages=[Message(role="assistant", text="Hola.")])


def test_phone_is_one_more_field():
    """El telefono es un dato mas: sin recordatorio oculto en el turno del usuario ni reglas propias."""
    wf = _with_phone()
    messages = build_classic_messages(wf, _state(wf), "Quiero anotarme.")
    assert messages[-1]["content"] == "Quiero anotarme."
    assert "- telefono (obligatorio): Teléfono de contacto. Pregunta sugerida: ¿A qué número te llamamos?" \
        in messages[0]["content"]
    assert "Antes de despedirte" not in messages[0]["content"]
