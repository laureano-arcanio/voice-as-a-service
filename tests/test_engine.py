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


async def test_invented_and_invalid_fields_are_dropped(store):
    llm = FakeLLM(AgentTurn(
        field_updates={"random_field": "foo", "employee_count": "bastantes"},
        next_objective="random_field", assistant_message="¿Tenés una cantidad aproximada?",
    ))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan", company_name="Acme", company_activity="Logística")
    state, turn = await engine.process_turn(cid, "Somos bastantes.")
    assert turn.field_updates == {}
    assert "random_field" not in state.fields
    assert state.fields["employee_count"] is None
    assert turn.next_objective == "employee_count"


async def test_llm_cannot_complete_arbitrarily(store, workflow):
    llm = FakeLLM(AgentTurn(field_updates={"contact_name": "Juan"}, next_objective=None, assistant_message="Chau.", status="completed"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await engine.process_turn(cid, "Juan, chau.")
    assert turn.status == "active" and state.status == "active"
    assert turn.next_objective == "company_name"
    assert turn.assistant_message == workflow.fields["company_name"].question


async def test_completed_is_decided_by_app(store, workflow):
    llm = FakeLLM(AgentTurn(field_updates={"wants_demo": False}, next_objective="email", assistant_message="¿Tu correo?", status="active"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    state, turn = await engine.process_turn(cid, "No, por ahora no.")
    assert turn.status == "completed" and state.status == "completed"
    assert turn.next_objective is None
    assert turn.assistant_message == workflow.completion.message_if_no_demo.strip()


async def test_demo_requires_email_before_completing(store, workflow):
    llm = FakeLLM(
        AgentTurn(field_updates={"wants_demo": True}, next_objective="email", assistant_message="¿A qué correo te escribimos?", status="completed"),
        AgentTurn(field_updates={"email": "juan@acme.com"}, next_objective=None, assistant_message="Listo.", status="completed"),
    )
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    _, turn = await engine.process_turn(cid, "Sí, dale.")
    assert turn.status == "active" and turn.next_objective == "email"
    _, turn = await engine.process_turn(cid, "juan arroba acme punto com")
    assert turn.status == "completed"
    assert turn.assistant_message == workflow.completion.message_if_demo.strip()


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
