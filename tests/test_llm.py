import httpx
import pytest

from app import config
from app.conversation.engine import ConversationEngine
from app.llm.client import LLMClient

from .helpers import start_with, turn_and_extract


def llm_available() -> bool:
    try:
        r = httpx.get(f"{config.VLLM_LLM_BASE_URL}/models", headers={"Authorization": f"Bearer {config.VLLM_API_KEY}"}, timeout=2)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not llm_available(), reason="LLM no disponible en VLLM_LLM_BASE_URL")


@pytest.fixture
def engine(store):
    return ConversationEngine(LLMClient(config.VLLM_LLM_BASE_URL, config.VLLM_API_KEY, config.VLLM_LLM_MODEL), store)


async def test_normal_answer(engine):
    cid = start_with(engine)
    state, turn = await turn_and_extract(engine, cid, "Juan.")
    assert state.fields["contact_name"] == "Juan"
    assert turn.next_objective == "company_name"


async def test_multiple_fields_together(engine):
    cid = start_with(engine)
    state, turn = await turn_and_extract(engine, cid, "Soy Juan de Acme, hacemos logística y somos unas 80 personas.")
    assert state.fields["contact_name"] == "Juan"
    assert state.fields["company_name"] == "Acme"
    assert "log" in state.fields["company_activity"].lower()
    assert state.fields["employee_count"] == 80
    assert turn.next_objective == "workforce_location"


async def test_ambiguous_answer(engine):
    cid = start_with(engine, "¿Cuántos empleados tienen, aproximadamente?",
                     contact_name="Juan", company_name="Acme", company_activity="Logística")
    state, turn = await turn_and_extract(engine, cid, "Somos bastantes.")
    assert state.fields["employee_count"] is None
    assert turn.next_objective == "employee_count"


async def test_user_gets_ahead(engine):
    cid = start_with(engine, "¿A qué se dedica la empresa?", contact_name="Juan", company_name="Acme")
    state, turn = await turn_and_extract(
        engine, cid, "Hacemos limpieza. Hoy fichan en planillas de papel y lo que más quiero es controlar bien los horarios."
    )
    assert state.fields["company_activity"]
    assert state.fields["attendance_process"]
    assert state.fields["main_problem"]
    assert state.fields["employee_count"] is None and state.fields["workforce_location"] is None
    assert turn.next_objective in ("employee_count", "workforce_location")


async def test_question_is_answered_and_data_extracted(engine):
    cid = start_with(engine, "¿Cómo controlan hoy la asistencia y los horarios del personal?",
                     contact_name="Juan", company_name="Acme", company_activity="Logística",
                     employee_count=80, workforce_location="En la calle")
    state, turn = await turn_and_extract(engine, cid, "Usamos planillas. ¿El sistema permite fichar desde el celular?")
    assert state.fields["attendance_process"]
    assert turn.next_objective == "main_problem"
    assert "celular" in turn.assistant_message.lower()
