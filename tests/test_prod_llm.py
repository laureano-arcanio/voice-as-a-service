"""Presupuesto del LLM (H11): max_tokens en cada pedido, recorte del historial al
contexto, tope de la definicion del agente, deadline por pedido y errores con tipo."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.agents.templates import load_reference, reference_data
from app.config import settings
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, Message
from app.llm import budget
from app.llm.client import LLMClient
from app.llm.errors import LLMContextError, LLMError, LLMTimeoutError

from .helpers import FakeLLM
from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)
from .test_workflow import state_with

TURN = '{"assistant_message": "Dale, ¿algo más?", "answered": false, "next_objective": null, "status": "active"}'


class FakeCompletions:
    """chat.completions de openai: guarda cada pedido y responde content (o lanza error)."""

    def __init__(self, content: str = TURN, error: Exception | None = None, chunks: list[str] | None = None,
                 delay: float = 0):
        self.content, self.error, self.chunks, self.delay = content, error, chunks, delay
        self.requests = []

    async def create(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if request.get("stream"):
            return self._stream()
        message = SimpleNamespace(content=self.content, reasoning_content=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])

    async def _stream(self):
        for text in self.chunks or [self.content]:
            delta = SimpleNamespace(content=text, reasoning_content=None)
            yield SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)])
            await asyncio.sleep(self.delay)


def fake_client(**kw) -> tuple[LLMClient, FakeCompletions]:
    llm = LLMClient("http://localhost:1/v1", "x", "m")
    completions = FakeCompletions(**kw)
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return llm, completions


def long_history(state, n: int, size: int = 600):
    """n mensajes alternados (agente primero, como con apertura), cada uno numerado."""
    roles = ["assistant", "user"]
    state.messages = [Message(role=roles[i % 2], text=f"m{i:03d} " + "x" * size) for i in range(n)]
    return state


def request_tokens(messages: list[dict]) -> int:
    return sum(budget.message_tokens(m["content"]) for m in messages)


@pytest.fixture
def small_context(monkeypatch):
    """Contexto chico para que unas decenas de mensajes no entren."""
    monkeypatch.setattr(settings, "llm_context_tokens", 6000)
    monkeypatch.setattr(settings, "llm_context_margin_tokens", 256)


# ---------- max_tokens ----------

async def test_every_request_has_max_tokens():
    wf, classic = load_reference("berlin_signup"), load_reference("berlin_signup_classic")
    llm, calls = fake_client()
    await llm.process_turn(wf, state_with(wf), "Hola")
    await llm.process_turn(wf, state_with(wf), "Hola", on_message=lambda t: None)
    llm.client.chat.completions.content = "Hola, ¿qué clase te interesa?"
    await llm.converse(classic, state_with(classic), "Hola")
    await llm.converse(classic, state_with(classic), "Hola", on_message=lambda t: None)
    llm.client.chat.completions.content = "{}"
    await llm.extract(wf, state_with(wf))
    assert [r["max_tokens"] for r in calls.requests] == [settings.llm_max_tokens_reply] * 4 + [settings.llm_max_tokens_extract]


async def test_thinking_budget_counts_in_max_tokens():
    wf = load_reference("berlin_signup")
    llm, calls = fake_client()
    llm.reasoning_tokens = LLMClient("http://localhost:1/v1", "x", "m", thinking=True, thinking_budget=128).reasoning_tokens
    await llm.process_turn(wf, state_with(wf), "Hola")
    assert calls.requests[0]["max_tokens"] == settings.llm_max_tokens_reply + 128


# ---------- recorte del historial ----------

async def test_classic_drops_the_oldest_messages_and_keeps_alternation(small_context):
    wf = load_reference("berlin_signup_classic")
    state = long_history(state_with(wf), 41)
    llm, calls = fake_client(content="Dale.")
    await llm.converse(wf, state, "el mensaje nuevo")
    messages = calls.requests[0]["messages"]
    history = messages[1:-1]
    dropped = 41 - len(history)
    assert dropped > 0 and dropped % budget.DROP_CHUNK == 0
    # Sistema y mensaje nuevo intactos; salen los mas viejos y queda el mas reciente.
    assert messages[0]["role"] == "system" and f"Se omitieron los {dropped} mensajes" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "el mensaje nuevo"}
    assert history[0]["content"].startswith(f"m{dropped:03d}") and history[-1]["content"].startswith("m040")
    assert [m["role"] for m in history] == ["assistant", "user"] * (len(history) // 2) + ["assistant"]
    limit = budget.prompt_limit(settings.llm_max_tokens_reply)
    assert request_tokens(messages) <= limit
    # El estado guardado no cambia: el recorte es solo del pedido.
    assert len(state.messages) == 41


async def test_classic_short_history_is_untouched(small_context):
    wf = load_reference("berlin_signup_classic")
    state = long_history(state_with(wf), 4, size=20)
    llm, calls = fake_client(content="Dale.")
    await llm.converse(wf, state, "Hola")
    messages = calls.requests[0]["messages"]
    assert len(messages) == 6 and "Se omitieron" not in messages[0]["content"]


async def test_structured_and_extraction_drop_the_oldest_lines(small_context):
    wf = load_reference("berlin_signup")
    state = long_history(state_with(wf), 41)
    llm, calls = fake_client()
    await llm.process_turn(wf, state, "el mensaje nuevo")
    prompt = calls.requests[0]["messages"][1]["content"]
    assert "Se omitieron los" in prompt and "m000" not in prompt and "m040" in prompt
    assert prompt.endswith("el mensaje nuevo") and "WORKFLOW:" in prompt
    assert request_tokens(calls.requests[0]["messages"]) <= budget.prompt_limit(settings.llm_max_tokens_reply)

    llm, calls = fake_client(content="{}")
    await llm.extract(wf, state)
    prompt = calls.requests[0]["messages"][1]["content"]
    assert "Se omitieron los" in prompt and "m000" not in prompt and "m040" in prompt
    assert request_tokens(calls.requests[0]["messages"]) <= budget.prompt_limit(settings.llm_max_tokens_extract)


def test_drop_count_moves_in_chunks():
    """El corte avanza de a DROP_CHUNK: entre cortes el prefijo del pedido no cambia."""
    history = [10] * 30
    assert budget.drop_count(100, history, 400) == 0
    assert budget.drop_count(100, history, 399) == budget.DROP_CHUNK
    assert budget.drop_count(100, history, 100) == 30
    with pytest.raises(LLMContextError):
        budget.drop_count(500, history, 400)


# ---------- errores con tipo ----------

async def test_prompt_that_does_not_fit_is_a_context_error_without_calling_vllm(small_context):
    wf = load_reference("berlin_signup_classic")
    llm, calls = fake_client(content="Dale.")
    with pytest.raises(LLMContextError):
        await llm.converse(wf, state_with(wf), "x" * 30_000)
    assert calls.requests == []


def bad_request(message: str) -> openai.BadRequestError:
    response = httpx.Response(400, request=httpx.Request("POST", "http://localhost:1/v1/chat/completions"))
    return openai.BadRequestError(message, response=response, body=None)


async def test_vllm_errors_become_typed_errors():
    wf = load_reference("berlin_signup")
    llm, _ = fake_client(error=bad_request(
        "This model's maximum context length is 16384 tokens. However, you requested 17000 tokens."))
    with pytest.raises(LLMContextError):
        await llm.process_turn(wf, state_with(wf), "Hola")
    llm, _ = fake_client(error=bad_request("invalid sampling parameter"))
    with pytest.raises(LLMError) as ei:
        await llm.process_turn(wf, state_with(wf), "Hola")
    assert not isinstance(ei.value, LLMContextError)
    llm, _ = fake_client(error=openai.APIConnectionError(request=httpx.Request("POST", "http://localhost:1")))
    with pytest.raises(LLMError):
        await llm.extract(wf, state_with(wf))
    llm, _ = fake_client(content="no es json")
    with pytest.raises(LLMError):
        await llm.extract(wf, state_with(wf))


async def test_stream_deadline_covers_the_whole_turn(monkeypatch):
    """Cada chunk llega a tiempo, pero el turno entero se pasa: LLMTimeoutError con lo ya dicho."""
    monkeypatch.setattr(settings, "llm_turn_deadline_seconds", 0.15)
    wf = load_reference("berlin_signup_classic")
    llm, _ = fake_client(chunks=["Hola, ", "¿cómo ", "estás?"] * 10, delay=0.05)
    said = []
    with pytest.raises(LLMTimeoutError) as ei:
        await llm.converse(wf, state_with(wf), "Hola", on_message=said.append)
    assert ei.value.spoken == "".join(said) and ei.value.spoken.startswith("Hola, ")


async def test_truncated_turn_json_keeps_the_complete_message():
    """max_tokens corto el JSON despues de assistant_message: el mensaje vale, sin avance."""
    wf = load_reference("berlin_signup")
    state = state_with(wf)
    state.progress.asked = "contact_name"
    llm, _ = fake_client(content='{"assistant_message": "¿Cómo te llamás?", "answered": tr')
    turn = await llm.process_turn(wf, state, "Hola")
    assert (turn.assistant_message, turn.status, turn.answered, turn.next_objective) == (
        "¿Cómo te llamás?", "active", False, "contact_name")
    llm, _ = fake_client(content='{"assistant_message": "¿Cómo te ll')
    with pytest.raises(LLMError):
        await llm.process_turn(wf, state, "Hola")


class FailingLLM(FakeLLM):
    def __init__(self, error: Exception):
        super().__init__()
        self.error = error

    async def process_turn(self, workflow, state, user_message, on_message=None):
        raise self.error


async def test_engine_propagates_llm_errors_without_saving_the_turn(store):
    engine = ConversationEngine(FailingLLM(LLMContextError("no entra")), store)
    state, _ = engine.start_conversation("sales_discovery")
    with pytest.raises(LLMContextError):
        await engine.process_turn(state.conversation_id, "Hola")
    assert len(store.get(state.conversation_id).messages) == 1     # solo la apertura

    # Cualquier otro error del LLM sale como LLMError (un solo tipo para voz y WhatsApp).
    engine = ConversationEngine(FailingLLM(RuntimeError("boom")), store)
    with pytest.raises(LLMError):
        await engine.process_turn(state.conversation_id, "Hola")
    assert len(store.get(state.conversation_id).messages) == 1


# ---------- tamano de la definicion ----------

def test_huge_knowledge_is_rejected_with_its_path(api, admin):  # noqa: F811
    c = make_client(admin)
    huge = {**reference_data("sales_discovery"), "knowledge": "Dato. " * (settings.knowledge_max_chars // 6 + 10)}
    r = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "Grande", "definition": huge})
    assert r.status_code == 422 and r.json()["code"] == "invalid_definition"
    errors = r.json()["errors"]
    assert errors[0]["path"] == "knowledge" and str(settings.knowledge_max_chars) in errors[0]["message"]

    agent = make_agent(admin, c)
    r = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": {**agent["definition"], "knowledge": huge["knowledge"]}})
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "knowledge"
    check = admin.post(f"{V1}/agents/validate", json={"definition": huge}).json()
    assert check["valid"] is False and check["errors"][0]["path"] == "knowledge"


def test_definition_that_leaves_no_room_for_the_conversation_is_rejected(api, admin):  # noqa: F811
    """Con el conocimiento dentro del tope, igual tiene que dejar lugar a la conversacion."""
    c = make_client(admin)
    rules = [f"Regla {i}: " + "texto largo de la regla " * 20 for i in range(120)]
    big = reference_data("sales_discovery")
    big["conversation"] = {**big["conversation"], "rules": rules}
    r = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "Reglas", "definition": big})
    assert r.status_code == 422, r.text
    assert any("tokens" in e["message"] and str(settings.llm_context_tokens) in e["message"] for e in r.json()["errors"])


def test_reference_agents_fit():
    from app.agents.limits import definition_errors
    from app.agents.templates import reference_ids

    for agent_id in reference_ids():
        assert definition_errors(load_reference(agent_id)) == [], agent_id


def test_turn_payload_is_valid_json():
    # Sanity del fake: el TURN de estos tests es un AgentTurn valido.
    assert AgentTurn.model_validate(json.loads(TURN)).status == "active"
