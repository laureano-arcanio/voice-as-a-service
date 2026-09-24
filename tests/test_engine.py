"""El motor: el LLM decide la respuesta, el objetivo y el fin; la app valida y guarda."""
from fastapi.testclient import TestClient

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.deps import get_engine
from app.main import app

from .helpers import BASE, FakeLLM, start_with


async def test_start_conversation(store, workflow):
    engine = ConversationEngine(FakeLLM(), store)
    state, opening = engine.start_conversation("sales_discovery")
    assert opening == workflow.conversation.opening
    assert set(state.fields) == set(workflow.fields)
    assert all(v is None for v in state.fields.values())
    assert store.get(state.conversation_id).messages[0].text == opening


async def test_multiple_updates_in_one_turn(store):
    llm = FakeLLM(AgentTurn(
        field_updates={"contact_name": "Juan", "company_name": "Acme", "company_activity": "Logística", "employee_count": 80},
        next_objective="workforce_location", assistant_message="¿Dónde trabaja el personal?",
    ))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await engine.process_turn(cid, "Soy Juan de Acme, hacemos logística y somos unas 80 personas.")
    assert turn.next_objective == "workforce_location"
    assert store.get(cid).fields["employee_count"] == 80
    assert [m.role for m in state.messages] == ["assistant", "user", "assistant"]


async def test_the_llm_message_is_said_as_is(store):
    message = "Entendido, Juan. ¿Dónde trabaja el personal?"
    engine = ConversationEngine(FakeLLM(AgentTurn(field_updates={}, next_objective="workforce_location", assistant_message=message)), store)
    cid = start_with(engine)
    _, turn = await engine.process_turn(cid, "Hola.")
    assert turn.assistant_message == message


async def test_invented_and_invalid_fields_are_dropped_and_reported(store):
    llm = FakeLLM(
        AgentTurn(field_updates={"random_field": "foo", "employee_count": "bastantes"},
                  next_objective="employee_count", assistant_message="¿Tenés una cantidad aproximada?"),
        AgentTurn(field_updates={}, next_objective="employee_count", assistant_message="¿Cuántos son?"),
    )
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan", company_name="Acme", company_activity="Logística")
    state, turn = await engine.process_turn(cid, "Somos bastantes.")
    assert turn.field_updates == {}
    assert "random_field" not in state.fields and state.fields["employee_count"] is None
    assert state.progress.rejected == {"employee_count": "bastantes"}
    await engine.process_turn(cid, "No sé.")
    assert llm.calls[-1][1] == {"employee_count": "bastantes"}  # el LLM se entera


async def test_the_llm_decides_when_it_ends(store):
    """Aunque falten datos: la app no pisa la decision (el dashboard muestra lo que falta)."""
    llm = FakeLLM(AgentTurn(field_updates={"contact_name": "Juan"}, next_objective=None, assistant_message="Chau.", status="completed"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await engine.process_turn(cid, "Juan, no me interesa, chau.")
    assert turn.status == "completed" and state.status == "completed"
    assert turn.assistant_message == "Chau."
    assert state.progress.outcome == "no_demo"


async def test_outcome_is_recorded_on_completion(store):
    llm = FakeLLM(AgentTurn(field_updates={"wants_demo": True, "email": "juan@acme.com"}, next_objective=None,
                            assistant_message="Listo.", status="completed"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    state, _ = await engine.process_turn(cid, "Sí, a juan arroba acme punto com.")
    assert state.fields["email"] == "juan@acme.com" and state.progress.outcome == "demo"


async def test_email_the_user_did_not_say_is_rejected(store):
    llm = FakeLLM(AgentTurn(field_updates={"email": "info@browix.com"}, next_objective="email", assistant_message="¿Tu correo?"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE, wants_demo=True)
    state, _ = await engine.process_turn(cid, "Escribime a")
    assert state.fields["email"] is None and state.progress.rejected == {"email": "info@browix.com"}


async def test_llm_output_is_stored_per_turn(store):
    llm = FakeLLM(AgentTurn(field_updates={"contact_name": "Juan"}, next_objective="company_name", assistant_message="¿Empresa?"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, _ = await engine.process_turn(cid, "Juan.")
    reply = store.get(cid).messages[-1]
    assert [c["kind"] for c in reply.llm] == ["turno"]
    assert '"contact_name": "Juan"' in reply.llm[0]["output"] and reply.llm[0]["input"] == "Juan."


async def test_retract_last_turn(store):
    llm = FakeLLM(AgentTurn(field_updates={"attendance_process": "sin control"}, next_objective="main_problem",
                            assistant_message="¿Qué te gustaría mejorar?"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    before = store.get(cid)
    await engine.process_turn(cid, "no tenemos un control claro")
    assert engine.retract_last_turn(cid)
    after = store.get(cid)
    assert after.fields == before.fields and after.messages == before.messages
    assert not engine.retract_last_turn(cid)


def test_api_flow(store):
    llm = FakeLLM(AgentTurn(field_updates={"contact_name": "Juan"}, next_objective="company_name", assistant_message="¿En qué empresa trabajás?"))
    app.dependency_overrides[get_engine] = lambda: ConversationEngine(llm, store)
    client = TestClient(app)
    started = client.post("/conversations", json={"workflow_id": "sales_discovery"}).json()
    body = client.post(f"/conversations/{started['conversation_id']}/turn", json={"message": "Juan."}).json()
    missing = client.post("/conversations", json={"workflow_id": "nope"})
    app.dependency_overrides.clear()
    assert body["state"]["fields"]["contact_name"] == "Juan"
    assert body["next_objective"] == "company_name"
    assert body["status"] == "active"
    assert missing.status_code == 404
