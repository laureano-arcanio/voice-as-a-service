"""Cola de la extraccion final de las llamadas de voz (app/conversation/analysis.py): armado y fin, estados,
reintentos solo de transporte, tope, retomas, concurrencia y la espera del post-call. Sin red: el LLM es FakeLLM."""
import asyncio
import datetime
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from app.agents.templates import reference_data
from app.config import settings
from app.conversation import analysis
from app.conversation.models import Message
from app.db import utcnow
from app.models import CallMode, ConversationRow

from .test_api import V1, admin  # noqa: F401  (fixture)
from .voice_harness import add_agent, new_client, seed_call

PHONE = "+5493514440000"


class Unavailable(Exception):
    """Un 503 del proveedor del LLM."""
    status_code = 503


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


@pytest.fixture
def client(admin):  # noqa: F811
    return new_client(admin)


def agent_without_analysis(admin, client):  # noqa: F811
    definition = reference_data("sales_discovery")
    definition.pop("analysis")
    r = admin.post(f"{V1}/agents", json={"client_id": client["id"], "name": "Ana", "slug": "ana",
                                         "definition": definition})
    assert r.status_code == 201, r.text
    return r.json()


def seeded(api, agent, client, *, analysis_status=None, post_call_status=None, **values) -> str:
    """Una llamada con dos mensajes, lista para la cola."""
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    state = api.engine.store.get(conversation_id)
    state.messages.append(Message(role="user", text="Hola, quería consultar."))
    api.engine.store.save(state)
    update(api, conversation_id, analysis_status=analysis_status, post_call_status=post_call_status,
           analysis_next_at=values.pop("analysis_next_at", utcnow() if analysis_status else None),
           post_call_next_at=values.pop("post_call_next_at", utcnow() if post_call_status else None), **values)
    return conversation_id


def update(api, conversation_id, **values) -> None:
    with api.sessions() as s:
        row = s.get(ConversationRow, conversation_id)
        for key, value in values.items():
            setattr(row, key, value)
        s.commit()


def read(api, conversation_id) -> ConversationRow:
    with api.sessions() as s:
        return s.get(ConversationRow, conversation_id)


def run(api, conversation_id, *, now=utcnow):
    return asyncio.run(analysis.run_analysis(api.sessions, api.engine, conversation_id, now=now))


def later(seconds: int):
    return lambda: utcnow() + datetime.timedelta(seconds=seconds)


# --- Armado y fin -------------------------------------------------------------------------------


def test_arm_respects_analysis_and_is_idempotent(api, admin, client):  # noqa: F811
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client)
    workflow = api.engine.workflow(api.engine.store.get(conversation_id))
    analysis.arm(api.sessions, conversation_id, workflow)
    row = read(api, conversation_id)
    assert row.analysis_status == "armed"
    assert row.analysis_next_at > utcnow() + datetime.timedelta(seconds=settings.call_max_duration_seconds)
    expires = row.analysis_next_at
    analysis.arm(api.sessions, conversation_id, workflow)     # ya armada: no la pisa
    assert read(api, conversation_id).analysis_next_at == expires


def test_arm_skips_without_analysis_or_with_own_agent(api, admin, client):  # noqa: F811
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client)
    analysis.arm(api.sessions, conversation_id, SimpleNamespace(analysis=None, external=None))
    analysis.arm(api.sessions, conversation_id, SimpleNamespace(analysis=object(), external=object()))
    assert read(api, conversation_id).analysis_status is None


def test_end_without_analysis_ends_the_post_call(api, admin, client):  # noqa: F811
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, post_call_status="armed")
    analysis.end(api.sessions, conversation_id)
    row = read(api, conversation_id)
    assert row.analysis_status is None and row.post_call_status == "pending"


def test_end_moves_armed_to_pending(api, admin, client):  # noqa: F811
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="armed", post_call_status="armed")
    analysis.end(api.sessions, conversation_id)
    row = read(api, conversation_id)
    assert row.analysis_status == "pending" and row.analysis_next_at <= utcnow()
    assert row.post_call_status == "armed"     # el post-call espera a que la extraccion termine


# --- La cola ------------------------------------------------------------------------------------


def test_run_once_saves_the_fields_and_then_the_post_call(api, admin, client):  # noqa: F811
    api.llm.extractions = [{"contact_name": "Juan"}]
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending", post_call_status="armed")
    asyncio.run(analysis.run_once(api.sessions, api.engine))
    row = read(api, conversation_id)
    assert row.analysis_status == "done" and row.fields["contact_name"] == "Juan"
    assert row.analysis_attempts == 1 and row.post_call_status == "pending"
    assert api.llm.extract_calls == [2]
    assert [c["kind"] for c in row.messages[-1]["llm"]] == ["extraccion"]


def test_transient_failures_back_off_and_then_fail(api, admin, client):  # noqa: F811
    async def unavailable(workflow, state):
        raise Unavailable("sin servicio")

    api.llm.extract = unavailable
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending", post_call_status="armed")
    assert run(api, conversation_id) == "pending"
    row = read(api, conversation_id)
    assert row.analysis_attempts == 1
    assert row.analysis_next_at >= utcnow() + datetime.timedelta(seconds=29)
    assert row.post_call_status == "armed"     # todavia no
    assert run(api, conversation_id, now=later(60)) == "pending"
    assert read(api, conversation_id).analysis_next_at >= utcnow() + datetime.timedelta(minutes=4)
    assert run(api, conversation_id, now=later(600)) == "failed"
    row = read(api, conversation_id)
    assert row.analysis_attempts == 3 and row.analysis_next_at is None
    assert row.post_call_status == "pending"   # con el analisis terminado, corre


def test_model_output_is_not_retried(api, admin, client):  # noqa: F811
    calls = []

    async def invalid_json(workflow, state):
        calls.append(1)
        raise ValueError("json invalido")

    api.llm.extract = invalid_json
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending", post_call_status="armed")
    assert run(api, conversation_id) == "failed"
    row = read(api, conversation_id)
    assert calls == [1] and row.analysis_status == "failed" and row.post_call_status == "pending"


def test_timeout_ends_pending_without_saving(api, admin, client, monkeypatch):  # noqa: F811
    gate = asyncio.Event()

    async def slow(workflow, state):
        await gate.wait()

    api.llm.extract = slow
    monkeypatch.setattr(analysis, "RUN_TIMEOUT", 0.05)
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending", post_call_status="armed")
    assert run(api, conversation_id) == "pending"
    row = read(api, conversation_id)
    assert row.analysis_status == "pending" and row.fields["contact_name"] is None
    gate.set()


def test_two_runs_at_once_extract_once(api, admin, client):  # noqa: F811
    gate = asyncio.Event()
    calls = []
    real = api.llm.extract

    async def slow(workflow, state):
        calls.append(1)
        await gate.wait()
        return await real(workflow, state)

    api.llm.extractions = [{"contact_name": "Juan"}]
    api.llm.extract = slow
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending")

    async def twice():
        first = asyncio.create_task(analysis.run_analysis(api.sessions, api.engine, conversation_id))
        await asyncio.sleep(0)      # el primero reclama y queda esperando al LLM
        second = await analysis.run_analysis(api.sessions, api.engine, conversation_id)
        gate.set()
        return second, await first

    second, first = asyncio.run(twice())
    assert second is None and first == "done" and calls == [1]


@pytest.mark.parametrize("status", ["armed", "running"])
def test_expired_states_are_resumed(api, admin, client, status):  # noqa: F811
    api.llm.extractions = [{"contact_name": "Juan"}]
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status=status,
                             analysis_next_at=utcnow() - datetime.timedelta(seconds=1))
    asyncio.run(analysis.run_once(api.sessions, api.engine))
    row = read(api, conversation_id)
    assert row.analysis_status == "done" and row.fields["contact_name"] == "Juan"


def test_exhausted_attempts_fail_without_the_llm(api, admin, client):  # noqa: F811
    agent = add_agent(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending", analysis_attempts=3,
                             post_call_status="armed")
    asyncio.run(analysis.run_once(api.sessions, api.engine))
    row = read(api, conversation_id)
    assert row.analysis_status == "failed" and row.analysis_attempts == 3
    assert api.llm.extract_calls == [] and row.post_call_status == "pending"


def test_no_analysis_agent_is_left_out(api, admin, client):  # noqa: F811
    agent = agent_without_analysis(admin, client)
    conversation_id = seeded(api, agent, client, analysis_status="pending")
    workflow = api.engine.workflow(api.engine.store.get(conversation_id))
    assert workflow.analysis is None
    analysis.arm(api.sessions, conversation_id, workflow)
    asyncio.run(analysis.run_once(api.sessions, api.engine))
    row = read(api, conversation_id)
    assert row.analysis_status == "done" and api.llm.extract_calls == []


def test_due_ids_includes_only_what_is_due(api, admin, client):  # noqa: F811
    agent = add_agent(admin, client)
    due = seeded(api, agent, client, analysis_status="pending")
    waiting = seeded(api, agent, client, analysis_status="pending",
                     analysis_next_at=utcnow() + datetime.timedelta(minutes=5))
    with api.sessions() as s:
        ids = analysis.due_ids(s, utcnow())
    assert due in ids and waiting not in ids
