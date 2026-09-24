"""El motor: el LLM de conversacion decide la respuesta, el objetivo y el fin; la
extraccion saca los datos en segundo plano; la app valida y guarda."""
import asyncio

from fastapi.testclient import TestClient

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.deps import get_engine
from app.main import app

from .helpers import BASE, FakeLLM, start_with, turn_and_extract


async def test_start_conversation(store, workflow):
    engine = ConversationEngine(FakeLLM(), store)
    state, opening = engine.start_conversation("sales_discovery")
    assert opening == workflow.conversation.opening
    assert set(state.fields) == set(workflow.fields)
    assert all(v is None for v in state.fields.values())
    assert store.get(state.conversation_id).messages[0].text == opening
    assert state.progress.asked == "contact_name"   # la apertura pregunta el primer dato


async def test_data_comes_from_the_extraction(store):
    llm = FakeLLM(AgentTurn(next_objective="workforce_location", assistant_message="¿Dónde trabaja el personal?"),
                  extractions=[{"contact_name": "Juan", "company_name": "Acme", "company_activity": "Logística",
                                "employee_count": 80}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await turn_and_extract(engine, cid, "Soy Juan de Acme, hacemos logística y somos unas 80 personas.")
    assert turn.next_objective == "workforce_location"
    assert state.fields["employee_count"] == 80
    assert [m.role for m in state.messages] == ["assistant", "user", "assistant"]


async def test_the_turn_returns_before_the_extraction(store):
    """La respuesta sale sin esperar los datos; el turno siguiente si los espera."""
    gate = asyncio.Event()

    class SlowExtraction(FakeLLM):
        async def extract(self, workflow, state, only=None):
            await gate.wait()
            return await super().extract(workflow, state, only)

    llm = SlowExtraction(AgentTurn(next_objective="company_name", assistant_message="¿Empresa?"),
                         AgentTurn(next_objective="company_activity", assistant_message="¿Rubro?"),
                         extractions=[{"contact_name": "Juan"}, {"company_name": "Acme"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, _ = await engine.process_turn(cid, "Juan.")
    assert state.fields["contact_name"] is None
    gate.set()
    state, _ = await turn_and_extract(engine, cid, "Acme.")
    assert state.fields["contact_name"] == "Juan" and state.fields["company_name"] == "Acme"


async def test_the_llm_message_is_said_as_is(store):
    message = "Entendido, Juan. ¿Dónde trabaja el personal?"
    engine = ConversationEngine(FakeLLM(AgentTurn(next_objective="workforce_location", assistant_message=message)), store)
    cid = start_with(engine)
    _, turn = await engine.process_turn(cid, "Hola.")
    assert turn.assistant_message == message


async def test_invented_and_invalid_fields_are_dropped_and_reported(store):
    llm = FakeLLM(
        AgentTurn(next_objective="employee_count", assistant_message="¿Tenés una cantidad aproximada?"),
        AgentTurn(next_objective="employee_count", assistant_message="¿Cuántos son?"),
        extractions=[{"random_field": "foo", "employee_count": "bastantes"}],
    )
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan", company_name="Acme", company_activity="Logística")
    state, _ = await turn_and_extract(engine, cid, "Somos bastantes.")
    assert "random_field" not in state.fields and state.fields["employee_count"] is None
    assert state.progress.rejected == {"employee_count": "bastantes"}
    await engine.process_turn(cid, "No sé.")
    assert llm.calls[-1][1] == {"employee_count": "bastantes"}  # el LLM se entera


async def test_answered_without_data_is_retried_then_not_asked_again(store):
    """4a89e965: dijo "sí, pasame el link", la extraccion no lo guardo y el agente lo volvio a preguntar."""
    llm = FakeLLM(AgentTurn(answered=True, next_objective="company_activity", assistant_message="¿A qué se dedican?"),
                  extractions=[{}, {}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    state = store.get(cid)
    state.progress.asked = "company_name"
    store.save(state)
    state, _ = await turn_and_extract(engine, cid, "Acme.")
    assert llm.extract_calls == [None, ["company_name"]]    # extraccion completa y reintento del campo
    assert state.progress.answered_empty == ["company_name"]


async def test_answered_field_found_on_retry(store):
    llm = FakeLLM(AgentTurn(answered=True, next_objective="company_activity", assistant_message="¿A qué se dedican?"),
                  extractions=[{}, {"company_name": "Acme"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    state = store.get(cid)
    state.progress.asked = "company_name"
    store.save(state)
    state, _ = await turn_and_extract(engine, cid, "Acme.")
    assert state.fields["company_name"] == "Acme" and state.progress.answered_empty == []


async def test_the_llm_decides_when_it_ends(store):
    """Aunque falten datos: la app no pisa la decision (el dashboard muestra lo que falta)."""
    llm = FakeLLM(AgentTurn(next_objective=None, assistant_message="Chau.", status="completed"),
                  extractions=[{"contact_name": "Juan"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, turn = await turn_and_extract(engine, cid, "Juan, no me interesa, chau.")
    assert turn.status == "completed" and state.status == "completed"
    assert turn.assistant_message == "Chau."
    assert state.progress.outcome == "no_demo"


async def test_outcome_is_recorded_after_the_extraction(store):
    llm = FakeLLM(AgentTurn(next_objective=None, assistant_message="Listo.", status="completed"),
                  extractions=[{"wants_demo": True, "email": "juan@acme.com"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    state, _ = await turn_and_extract(engine, cid, "Sí, a juan arroba acme punto com.")
    assert state.fields["email"] == "juan@acme.com" and state.progress.outcome == "demo"


async def test_goal_with_missing_data_is_incomplete(store):
    """80ac0e22: pidio el link y corto sin dar el resto; contaba como objetivo cumplido."""
    llm = FakeLLM(AgentTurn(next_objective=None, assistant_message="Chau.", status="completed"),
                  extractions=[{"wants_demo": True}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    state, _ = await turn_and_extract(engine, cid, "Sí, pero ahora tengo que cortar.")
    assert state.progress.outcome == "incompleta"


async def test_email_the_user_did_not_say_is_rejected(store):
    llm = FakeLLM(AgentTurn(next_objective="email", assistant_message="¿Tu correo?"),
                  extractions=[{"email": "info@browix.com"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE, wants_demo=True)
    state, _ = await turn_and_extract(engine, cid, "Escribime a")
    assert state.fields["email"] is None and state.progress.rejected == {"email": "info@browix.com"}


async def test_llm_output_is_stored_per_turn(store):
    llm = FakeLLM(AgentTurn(next_objective="company_name", assistant_message="¿Empresa?"),
                  extractions=[{"contact_name": "Juan"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    state, _ = await turn_and_extract(engine, cid, "Juan.")
    reply = state.messages[-1]
    assert [c["kind"] for c in reply.llm] == ["turno", "extraccion"]
    assert reply.llm[0]["input"] == "Juan." and '"contact_name": "Juan"' in reply.llm[1]["output"]


async def test_the_extraction_does_not_see_the_new_reply(store):
    """Si ve la pregunta nueva del agente, la extraccion la contesta sola (bf06c2d0)."""
    class Spy(FakeLLM):
        async def extract(self, workflow, state, only=None):
            self.seen = [m.text for m in state.messages]
            return await super().extract(workflow, state, only)

    llm = Spy(AgentTurn(next_objective="company_name", assistant_message="¿Querés una demo?"))
    engine = ConversationEngine(llm, store)
    cid = start_with(engine)
    await turn_and_extract(engine, cid, "Juan.")
    assert llm.seen[-1] == "Juan."


async def test_retract_last_turn(store):
    llm = FakeLLM(AgentTurn(next_objective="main_problem", assistant_message="¿Qué te gustaría mejorar?"),
                  extractions=[{"attendance_process": "sin control"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    before = store.get(cid)
    await turn_and_extract(engine, cid, "no tenemos un control claro")
    assert engine.retract_last_turn(cid)
    after = store.get(cid)
    assert after.fields == before.fields and after.messages == before.messages
    assert not engine.retract_last_turn(cid)


async def test_retract_cancels_the_pending_extraction(store):
    gate = asyncio.Event()

    class SlowExtraction(FakeLLM):
        async def extract(self, workflow, state, only=None):
            await gate.wait()
            return await super().extract(workflow, state, only)

    llm = SlowExtraction(AgentTurn(next_objective="main_problem", assistant_message="¿Qué te gustaría mejorar?"),
                         extractions=[{"attendance_process": "sin control"}])
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, contact_name="Juan")
    await engine.process_turn(cid, "no tenemos")
    assert engine.retract_last_turn(cid)
    gate.set()
    await engine.wait_extraction(cid)
    await asyncio.sleep(0)
    assert store.get(cid).fields["attendance_process"] is None


def test_api_flow(store):
    llm = FakeLLM(AgentTurn(next_objective="company_name", assistant_message="¿En qué empresa trabajás?"),
                  extractions=[{"contact_name": "Juan"}])
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
