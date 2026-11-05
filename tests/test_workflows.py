"""Workflows del agente (app/conversation/workflows.py, engine.run_pre_call): que se hace con la respuesta del pre-call,
que ve el modelo, y el post-call durable: clasificacion de fallas, reintentos con la misma clave, retomas, nota para el
operador y resumen de respaldo. Sin red: el HTTP de las herramientas es un guion."""
import asyncio
import datetime
import json

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.agents.templates import reference_data
from app.config import settings
from app.conversation import workflows
from app.conversation.models import ToolSettings, Workflow
from app.db import utcnow
from app.llm.prompt import build_system_prompt
from app.models import CallMode, CallRow, ClientTool, ConversationRow, Event, ToolRun, WaAccount, WaThread
from app.services import handoff as handoff_service
from app.tools import runtime
from app.tools.conversation import TurnTools
from app.voice import handoff as voice_handoff

from .test_api import V1, admin  # noqa: F401  (fixture)
from .voice_harness import OPENING, add_agent, add_tool, charge_tool, http_tool, identify_tool, new_client, seed_call

BASE = "https://fichas.test"
PHONE = "+5493514440000"
REPLY = {"status": "single", "name": "María Gómez", "al_dia": True, "record": "Ficha: https://fichas.test/c/1",
         "operator_note": "María Gómez, al día", "dato_clinico": "no se asigna"}
PRE_CALL = {"pre_call": {"tool": "buscar_ficha", "timeout_ms": 1500}}


class Script:
    """El HTTP de las herramientas: cada pedido toma lo siguiente. Un status, un JSON (200) o una excepcion."""

    def __init__(self):
        self.replies: list = []
        self.requests: list[dict] = []

    async def request(self, method, url, headers, body):
        self.requests.append({"method": method, "url": url, "headers": headers, "body": body})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, runtime.Response):
            return reply
        if isinstance(reply, int):
            return runtime.Response(reply, {"error": "x"}, False)
        return runtime.Response(200, reply, False)


@pytest.fixture
def http(monkeypatch):
    script = Script()

    async def request(self, method, url, headers, body):
        return await script.request(method, url, headers, body)

    monkeypatch.setattr(runtime.SafeHttp, "request", request)
    return script


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


@pytest.fixture
def client(admin):  # noqa: F811
    return new_client(admin)


def post_call_agent(admin, client, when="always", tool=None):  # noqa: F811
    add_tool(admin, client, tool or charge_tool(BASE))
    return add_agent(admin, client, workflows={"post_call": {"tool": "registrar_cobro", "when": when}})


def pre_call_agent(admin, client, tool=None, opening=OPENING, **extra):  # noqa: F811
    add_tool(admin, client, tool or identify_tool(BASE))
    return add_agent(admin, client, workflows=PRE_CALL, opening=opening, **extra)


def pending_conversation(api, agent, client, *, channel="voice", status="pending", **values) -> str:
    """Conversacion lista para el loop."""
    if channel == "voice":
        conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    else:
        state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
        conversation_id = state.conversation_id
    update(api, conversation_id, post_call_status=status, post_call_next_at=utcnow(), **values)
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


def post_call_events(api, conversation_id) -> list[dict]:
    with api.sessions() as s:
        return [e.data for e in s.scalars(select(Event).where(Event.conversation_id == conversation_id,
                                                              Event.type == "workflow.post_call").order_by(Event.id))]


def run_post_call(api, conversation_id, **kw):
    return asyncio.run(workflows.run_post_call(api.sessions, api.engine, conversation_id, **kw))


# --- Pre-call: que se hace con la respuesta -------------------------------------------------------

def test_pre_call_splits_visible_and_hidden(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    http.replies = [REPLY]
    assert asyncio.run(api.engine.run_pre_call(conversation_id)) == "Hola María Gómez, soy Ana."
    state = api.engine.store.get(conversation_id)
    # Todas, para herramientas, whisper y plantillas; al prompt, solo las visibles.
    assert state.progress.tool_vars == {"situacion": "single", "nombre": "María Gómez", "al_dia": True,
                                        "ficha": REPLY["record"], "nota_operador": REPLY["operator_note"]}
    assert state.progress.contact == {"situacion": "single", "nombre": "María Gómez"}
    prompt = build_system_prompt(api.engine.workflow(state), "voice", state)
    assert "María Gómez" in prompt and "single" in prompt
    for hidden in ("Ficha:", "al día", "fichas.test", "no se asigna"):
        assert hidden not in prompt
    # La respuesta no va a mensajes ni traza.
    assert "fichas.test" not in state.model_dump_json(include={"messages"})
    assert "dato_clinico" not in state.model_dump_json()


def test_pre_call_precarga_un_campo_y_no_pisa_lo_que_estaba(api, admin, client, http):  # noqa: F811
    tool = identify_tool(BASE)
    tool["definition"]["assign"] = [{"var": "contact_name", "path": "name"}, {"var": "company_name", "path": "status"}]
    agent = pre_call_agent(admin, client, tool=tool)
    with api.sessions() as s:
        state, _ = api.engine.new_conversation(agent["id"], client["id"], session=s, phone=PHONE,
                                               contact={"company_name": "De la campaña", "deuda": 5})
        api.engine.store.add(s, state)
        s.flush()
        s.add(CallRow(conversation_id=state.conversation_id, client_id=client["id"], mode=CallMode.saliente, phone=PHONE))
        s.commit()
    http.replies = [REPLY]
    asyncio.run(api.engine.run_pre_call(state.conversation_id))
    state = api.engine.store.get(state.conversation_id)
    assert state.fields["contact_name"] == "María Gómez" and state.fields["company_name"] == "De la campaña"
    assert set(state.progress.preloaded) == {"company_name", "contact_name"}
    assert state.progress.contact == {"deuda": 5}


def test_pre_call_failure_leaves_a_run_and_no_data(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    http.replies = [503]
    assert asyncio.run(api.engine.run_pre_call(conversation_id)) == "Hola, soy Ana."
    state = api.engine.store.get(conversation_id)
    assert state.progress.tool_vars == {} and state.progress.contact == {}
    with api.sessions() as s:
        run = s.scalars(select(ToolRun).where(ToolRun.conversation_id == conversation_id)).one()
        event = s.scalars(select(Event).where(Event.type == "workflow.pre_call")).one()
    assert (run.ok, run.status_code) == (False, 503)
    assert event.data == {"ok": False, "status": 503, "ms": event.data["ms"], "slug": "buscar_ficha"}


def test_pre_call_of_a_deleted_tool_continues(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    with api.sessions() as s:
        s.delete(s.scalars(select(ClientTool)).one())
        s.commit()
    assert asyncio.run(api.engine.run_pre_call(conversation_id)) == "Hola, soy Ana."
    assert http.requests == []


def test_pre_call_only_finds_tools_of_its_client(api, admin, client, http):  # noqa: F811
    # Misma herramienta en otro cliente: nunca se ejecuta la ajena, aunque la definicion quede apuntando a ese nombre.
    agent = pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    other = new_client(admin, "otro")
    add_tool(admin, other, http_tool("buscar_ficha", "https://otro.test/x", assign=[{"var": "nombre", "path": "name"}]))
    with api.sessions() as s:
        s.delete(s.scalars(select(ClientTool).where(ClientTool.client_id == client["id"])).one())
        s.commit()
    asyncio.run(api.engine.run_pre_call(conversation_id))
    assert http.requests == []


def test_without_pre_call_nothing_happens(api, admin, client, http):  # noqa: F811
    agent = add_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    before = api.engine.store.get(conversation_id).model_dump()
    assert asyncio.run(api.engine.run_pre_call(conversation_id)) is None
    assert api.engine.store.get(conversation_id).model_dump() == before and http.requests == []


def test_phone_is_the_other_end_on_whatsapp_and_outbound(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
    http.replies = [REPLY, REPLY]
    asyncio.run(api.engine.run_pre_call(state.conversation_id, actor="wa:5493515551234"))
    assert json.loads(http.requests[-1]["body"])["from"] == "+5493515551234"
    outbound = seed_call(api, agent["id"], client["id"], CallMode.saliente, PHONE)
    asyncio.run(api.engine.run_pre_call(outbound))
    assert json.loads(http.requests[-1]["body"])["from"] == PHONE
    assert http.requests[-1]["headers"]["Idempotency-Key"] == f"{outbound}:pre_call"


def test_whatsapp_pre_call_goes_to_the_prompt_guide(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
    assert state.messages == []
    http.replies = [REPLY]
    assert asyncio.run(api.engine.run_pre_call(state.conversation_id, actor="wa:549351")) is None     # sin IndexError
    state = api.engine.store.get(state.conversation_id)
    assert state.messages == [] and state.progress.opening_guide == "Hola María Gómez, soy Ana."
    prompt = build_system_prompt(api.engine.workflow(state), "whatsapp", state)
    assert "Hola María Gómez, soy Ana." in prompt and "{{nombre}}" not in prompt


def test_whatsapp_failed_pre_call_does_not_read_the_variable(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
    http.replies = [runtime.HttpTimeout()]
    asyncio.run(api.engine.run_pre_call(state.conversation_id))
    state = api.engine.store.get(state.conversation_id)
    assert "{{nombre}}" not in build_system_prompt(api.engine.workflow(state), "whatsapp", state)


# --- Post-call: arme ------------------------------------------------------------------------------

def test_arm_never_raises(admin, client):  # noqa: F811
    workflow = Workflow.model_validate({**reference_data("sales_discovery"), "id": "x", "version": 1,
                                        "workflows": {"post_call": {"tool": "t"}}})

    def broken():
        raise RuntimeError("sin base")

    workflows.arm(broken, "conv", CallMode.entrante, workflow)
    workflows.mark_ended(broken, "conv")


def test_arm_is_idempotent_and_respects_when(api, admin, client):  # noqa: F811
    agent = post_call_agent(admin, client, when="handoff_accepted")
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    workflow = api.engine.workflow(api.engine.store.get(conversation_id))
    workflows.arm(api.sessions, conversation_id, CallMode.entrante, workflow, only_when="always")
    assert read(api, conversation_id).post_call_status is None
    workflows.arm(api.sessions, conversation_id, CallMode.entrante, workflow)
    first = read(api, conversation_id)
    expected = utcnow() + datetime.timedelta(seconds=settings.call_max_duration_seconds + 600)
    assert first.post_call_status == "armed" and abs(first.post_call_next_at - expected).total_seconds() < 5
    update(api, conversation_id, post_call_status="done")
    workflows.arm(api.sessions, conversation_id, CallMode.entrante, workflow)
    workflows.mark_ended(api.sessions, conversation_id)
    assert read(api, conversation_id).post_call_status == "done"       # una vez por conversacion


def test_text_end_arms_for_always_and_the_loop_recovers_it(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client, when="always")
    state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
    workflow = api.engine.workflow(state)
    with api.sessions() as s:
        workflows.arm_text_end(s, state.conversation_id, workflow)
        s.commit()
    row = read(api, state.conversation_id)
    assert row.post_call_status == "armed"
    assert abs((row.post_call_next_at - utcnow()).total_seconds() - 60) < 5
    # Todavia no vencio: el loop no lo toma. Al vencer (se recreo `app` antes de terminar finish), si.
    http.replies = [{"charged": True}]
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert http.requests == []
    later = utcnow() + datetime.timedelta(seconds=61)
    asyncio.run(workflows.run_once(api.sessions, api.engine, now=lambda: later))
    assert read(api, state.conversation_id).post_call_status == "done"


def test_text_end_ignores_handoff_accepted(api, admin, client):  # noqa: F811
    agent = post_call_agent(admin, client, when="handoff_accepted")
    state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
    with api.sessions() as s:
        workflows.arm_text_end(s, state.conversation_id, api.engine.workflow(state))
        s.commit()
    assert read(api, state.conversation_id).post_call_status is None


# --- Post-call: clasificacion ---------------------------------------------------------------------

TRANSPORT = {"timeout": runtime.HttpTimeout(), "conexion": runtime.HttpError("ConnectError"),
             "dns": runtime.HttpError("El host no resuelve"), "429": 429, "501": 501, "503": 503}


@pytest.mark.parametrize("failure", list(TRANSPORT.values()), ids=list(TRANSPORT))
def test_transport_retries_with_the_same_key_and_ends_failed(api, admin, client, http, failure):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [failure] * 4
    clock = [utcnow()]
    waits = []

    def tick():
        asyncio.run(workflows.run_once(api.sessions, api.engine, now=lambda: clock[0]))

    for attempt in range(1, 4):
        tick()
        row = read(api, conversation_id)
        assert (row.post_call_status, row.post_call_attempts) == ("pending", attempt)
        waits.append(row.post_call_next_at - clock[0])
        # No se adelanta: un instante antes de su hora, el loop no lo toma.
        before = row.post_call_next_at - datetime.timedelta(seconds=1)
        asyncio.run(workflows.run_once(api.sessions, api.engine, now=lambda: before))
        assert len(http.requests) == attempt
        clock[0] = row.post_call_next_at
    tick()
    row = read(api, conversation_id)
    assert (row.post_call_status, row.post_call_attempts, row.post_call_next_at) == ("failed", 4, None)
    assert waits == [datetime.timedelta(0), datetime.timedelta(minutes=1), datetime.timedelta(minutes=10)]
    keys = {r["headers"]["Idempotency-Key"] for r in http.requests}
    assert keys == {f"{conversation_id}:post_call"} and len(http.requests) == 4
    assert [e["ok"] for e in post_call_events(api, conversation_id)] == [False] * 4


def test_transport_then_success_is_done(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [503, {"charged": True}]
    assert run_post_call(api, conversation_id) == "pending"
    assert run_post_call(api, conversation_id) == "done"
    assert read(api, conversation_id).post_call_attempts == 2


OAUTH_DEF = {"type": "oauth2_client_credentials", "secret": "CLAVE", "client_id": "c",
             "token_url": BASE + "/token"}


@pytest.mark.parametrize("token_reply,expected", [
    (runtime.HttpTimeout(), "pending"), (runtime.HttpError("ConnectError"), "pending"), (503, "pending"),
    (429, "pending"), (400, "failed")], ids=["timeout", "conexion", "503", "429", "400"])
def test_oauth_token_server_is_classified_the_same(api, admin, client, http, token_reply, expected):  # noqa: F811
    tool = charge_tool(BASE)
    tool["definition"]["http"]["auth"] = OAUTH_DEF
    r = admin.post(f"{V1}/clients/{client['id']}/secrets", json={"name": "CLAVE", "value": "s3creto"})
    assert r.status_code == 201, r.text
    agent = post_call_agent(admin, client, tool=tool)
    conversation_id = pending_conversation(api, agent, client)
    runtime._TOKENS.clear()
    http.replies = [token_reply]
    assert run_post_call(api, conversation_id) == expected
    assert len(http.requests) == 1


@pytest.mark.parametrize("reply", [301, 400, 404, 422], ids=str)
def test_app_answer_is_failed_at_once(api, admin, client, http, reply):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [reply]
    assert run_post_call(api, conversation_id) == "failed"
    assert len(http.requests) == 1 and read(api, conversation_id).post_call_attempts == 1


def test_blocked_url_is_failed_at_once(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [runtime.BlockedAddress("red privada")]
    assert run_post_call(api, conversation_id) == "failed"


def test_missing_secret_is_failed_without_a_request(api, admin, client, http):  # noqa: F811
    tool = charge_tool(BASE)
    tool["definition"]["http"]["auth"] = {"type": "bearer", "secret": "CLAVE"}
    assert admin.post(f"{V1}/clients/{client['id']}/secrets", json={"name": "CLAVE", "value": "x"}).status_code == 201
    agent = post_call_agent(admin, client, tool=tool)
    conversation_id = pending_conversation(api, agent, client)
    from app.models import ClientSecret
    with api.sessions() as s:
        s.delete(s.scalars(select(ClientSecret)).one())
        s.commit()
    api.engine.tools._secrets.clear()
    assert run_post_call(api, conversation_id) == "failed"
    assert http.requests == []


def test_charged_false_is_done_without_retry(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [{"charged": False, "operator_message": "Sin ficha: no se cobró."}]
    assert run_post_call(api, conversation_id) == "done"
    assert run_post_call(api, conversation_id) is None      # done no se repite
    assert len(http.requests) == 1


def test_run_timeout_counts_as_transport(api, admin, client, http, monkeypatch):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    monkeypatch.setattr(workflows, "RUN_TIMEOUT", 0.01)

    async def slow(*a, **kw):
        await asyncio.sleep(5)

    monkeypatch.setattr(api.engine.tools, "run_workflow", slow)
    assert run_post_call(api, conversation_id) == "pending"


# --- Post-call: durabilidad -----------------------------------------------------------------------

def test_expired_armed_is_taken_by_the_loop(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client, status="armed")
    update(api, conversation_id, post_call_next_at=utcnow() + datetime.timedelta(minutes=5))
    http.replies = [{"charged": True}]
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert read(api, conversation_id).post_call_status == "armed" and http.requests == []      # llamada en curso
    update(api, conversation_id, post_call_next_at=utcnow() - datetime.timedelta(seconds=1))
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert read(api, conversation_id).post_call_status == "done"


def test_expired_running_resumes_with_the_same_key(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client, status="running", post_call_attempts=1)
    update(api, conversation_id, post_call_next_at=utcnow() + datetime.timedelta(seconds=100))
    http.replies = [{"charged": True}]
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert http.requests == []                              # un `running` vigente es de otro proceso
    update(api, conversation_id, post_call_next_at=utcnow() - datetime.timedelta(seconds=1))
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    row = read(api, conversation_id)
    assert (row.post_call_status, row.post_call_attempts) == ("done", 2)
    assert http.requests[0]["headers"]["Idempotency-Key"] == f"{conversation_id}:post_call"


@pytest.mark.parametrize("status", ["running", "pending", "armed"])
def test_exhausted_attempts_fail_without_running(api, admin, client, http, status):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client, status=status, post_call_attempts=4)
    assert run_post_call(api, conversation_id) == "failed"
    assert http.requests == [] and read(api, conversation_id).post_call_attempts == 4
    assert post_call_events(api, conversation_id)[-1]["reason"] == "max_attempts"


def test_result_of_a_stale_claim_is_discarded(api, admin, client, http):  # noqa: F811
    # Mientras corria, otro proceso lo retomo: este resultado ya no vale y no deja evento.
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    real = http.request

    async def retaken(method, url, headers, body):
        update(api, conversation_id, post_call_attempts=2)
        return await real(method, url, headers, body)

    http.replies = [{"charged": True, "operator_message": "viejo"}]
    http.request = retaken
    assert run_post_call(api, conversation_id) is None
    row = read(api, conversation_id)
    assert (row.post_call_status, row.post_call_attempts, row.post_call_note) == ("running", 2, None)
    assert post_call_events(api, conversation_id) == []


def test_two_claims_run_once(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [{"charged": True}, {"charged": True}]

    async def both():
        return await asyncio.gather(*[workflows.run_post_call(api.sessions, api.engine, conversation_id)
                                      for _ in range(2)])

    assert sorted(asyncio.run(both()), key=str) == [None, "done"]
    assert len(http.requests) == 1


def test_claim_loses_against_a_snapshot_already_taken(api, admin, client):  # noqa: F811
    # Dos procesos que leyeron la misma fila, tambien sobre `running` vencido: gana uno solo.
    agent = post_call_agent(admin, client)
    for status in ("pending", "running"):
        conversation_id = pending_conversation(api, agent, client, status=status)
        now = utcnow()
        with api.sessions() as a, api.sessions() as b:
            first, second = a.get(ConversationRow, conversation_id), b.get(ConversationRow, conversation_id)
            won = workflows._claim(a, first, now)
            a.commit()
            lost = workflows._claim(b, second, now)
            b.commit()
        assert (won, lost) == (1, None)


def test_exception_stays_running_until_it_expires(api, admin, client, http, monkeypatch):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)

    async def boom(*a, **kw):
        raise RuntimeError("base caida")

    monkeypatch.setattr(api.engine.tools, "run_workflow", boom)
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    row = read(api, conversation_id)
    assert (row.post_call_status, row.post_call_attempts) == ("running", 1)
    assert abs((row.post_call_next_at - utcnow()).total_seconds() - 180) < 5


# --- Post-call: no ejecutable ---------------------------------------------------------------------

def edit_tool(api, **http):
    with api.sessions() as s:
        row = s.scalars(select(ClientTool)).one()
        row.definition = {**row.definition, "http": {**row.definition["http"], **http}}
        s.commit()


def to_code(api):
    with api.sessions() as s:
        row = s.scalars(select(ClientTool)).one()
        row.type = "code"
        row.definition = {"description": "x", "code": "export default async function () { return {}; }"}
        s.commit()


def delete_tool(api):
    with api.sessions() as s:
        s.delete(s.scalars(select(ClientTool)).one())
        s.commit()


def invalid_tool(api):
    with api.sessions() as s:
        s.scalars(select(ClientTool)).one().definition = {"description": "x"}
        s.commit()


@pytest.mark.parametrize("break_tool", [delete_tool, to_code, invalid_tool,
                                        lambda api: edit_tool(api, method="GET", body=None)],
                         ids=["borrada", "code", "invalida", "GET"])
def test_not_executable_fails_without_calling(api, admin, client, http, break_tool):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    break_tool(api)
    assert run_post_call(api, conversation_id) == "failed"
    assert http.requests == []
    assert post_call_events(api, conversation_id)[-1]["reason"] == "not_executable"


def test_missing_version_fails_and_does_not_break_the_batch(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    bad = pending_conversation(api, agent, client)
    good = pending_conversation(api, agent, client)
    update(api, bad, agent_version=999)
    http.replies = [{"charged": True}]
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert read(api, bad).post_call_status == "failed" and read(api, good).post_call_status == "done"
    assert len(http.requests) == 1


# --- Nota para el operador ------------------------------------------------------------------------

@pytest.mark.parametrize("reply,note", [
    ({"operator_message": "  Cobro registrado.  "}, "Cobro registrado."),
    ({"operator_message": "x" * 1500}, "x" * 1000),
    ({"operator_message": ["lista"]}, None), ({"operator_message": 5}, None), ({"operator_message": None}, None),
    ({"operator_message": "   "}, None), ({"otra": "cosa"}, None), ("texto plano", None), (None, None),
], ids=["texto", "largo", "lista", "numero", "null", "blanco", "sin_clave", "plano", "vacio"])
def test_note_on_whatsapp(api, admin, client, http, reply, note):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client, channel="whatsapp")
    http.replies = [reply]
    assert run_post_call(api, conversation_id, actor="wa:549351") == "done"
    assert read(api, conversation_id).post_call_note == note


def test_no_note_on_voice(api, admin, client, http):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client)
    http.replies = [{"operator_message": "Cobro registrado."}]
    assert run_post_call(api, conversation_id) == "done"
    assert read(api, conversation_id).post_call_note is None


def test_post_call_actor_comes_from_the_thread(api, admin, client, http):  # noqa: F811
    # Lo corre el loop, que no sabe quien escribe: la persona sale del hilo.
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client, channel="whatsapp")
    with api.sessions() as s:
        account = WaAccount(client_id=client["id"], agent_id=agent["id"], phone_number_id="111", waba_id="222",
                            display_phone_number="+54 351")
        s.add(account)
        s.flush()
        s.add(WaThread(conversation_id=conversation_id, account_id=account.id, client_id=client["id"],
                       wa_id="5493515551234"))
        s.commit()
    http.replies = [{"charged": True}]
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert json.loads(http.requests[0]["body"])["from"] == "+5493515551234"


# --- Sin exposicion -------------------------------------------------------------------------------

def test_responses_are_not_exposed(api, admin, client, http):  # noqa: F811
    add_tool(admin, client, identify_tool(BASE))
    add_tool(admin, client, charge_tool(BASE))
    agent = add_agent(admin, client, workflows={**PRE_CALL, "post_call": {"tool": "registrar_cobro", "when": "always"}})
    state, _ = api.engine.start_conversation(agent["id"], client["id"], channel="whatsapp", opening=False)
    conversation_id = state.conversation_id
    voice = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    note = "Cobro registrado al titular Juan Pérez."
    http.replies = [REPLY, {"charged": True, "operator_message": note}] * 2
    for cid in (conversation_id, voice):
        asyncio.run(api.engine.run_pre_call(cid, actor="wa:549351"))
        update(api, cid, post_call_status="pending", post_call_next_at=utcnow())
        assert run_post_call(api, cid, actor="wa:549351") == "done"
    assert read(api, conversation_id).post_call_note == note

    key = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "mcp", "scopes": ["mcp"]}).json()["key"]
    for cid in (conversation_id, voice):
        bodies = [admin.get(f"{V1}/conversations/{cid}").text, admin.get(f"{V1}/calls/{cid}").text,
                  admin.get(f"{V1}/events", params={"conversation_id": cid, "client_id": client["id"]}).text,
                  api.client.post("/mcp", headers={"Authorization": f"Bearer {key}"}, json={
                      "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                      "params": {"name": "get_call", "arguments": {"conversation_id": cid}}}).text]
        assert all(b for b in bodies)
        assert '"workflow.post_call"' in bodies[2] and '"workflow.pre_call"' in bodies[2]
        for body in bodies:
            for secret in ("Cobro registrado", "operator_message", "al día", "Ficha:", "fichas.test/c", "post_call_note",
                           "tool_vars", "nota_operador", "no se asigna"):
                assert secret not in body, (secret, body)
        stored = api.engine.store.get(cid).model_dump_json(include={"messages"})
        assert "Cobro registrado" not in stored and "Ficha:" not in stored


# --- Diagnostico de un workflow que falla: sin texto de la respuesta -------------------------------

PERSONAL = "QA-RESP-WORKFLOW persona Maria"
FAILURES = {
    "422": (runtime.Response(422, {"error": PERSONAL}, False), "failed", "herramienta automática: http_error | HTTP 422 | falla de conexión: no"),
    "503": (runtime.Response(503, PERSONAL, False), "pending", "herramienta automática: http_error | HTTP 503 | falla de conexión: sí"),
    "429": (runtime.Response(429, PERSONAL, False), "pending", "herramienta automática: http_error | HTTP 429 | falla de conexión: sí"),
    "301": (runtime.Response(301, PERSONAL, False), "failed", "herramienta automática: redirect | HTTP 301 | falla de conexión: no"),
    "timeout": (runtime.HttpTimeout(), "pending", "herramienta automática: timeout | falla de conexión: sí"),
    "conexion": (runtime.HttpError(PERSONAL), "pending", "herramienta automática: connection | falla de conexión: sí"),
    "bloqueada": (runtime.BlockedAddress(PERSONAL), "failed", "herramienta automática: blocked_address | falla de conexión: no"),
}


def run_of(api, conversation_id) -> ToolRun:
    with api.sessions() as s:
        return s.scalars(select(ToolRun).where(ToolRun.conversation_id == conversation_id)).one()


def technical_tool(admin, client) -> dict:  # noqa: F811
    r = admin.get(f"{V1}/reports/technical", params={"client_id": client["id"]})
    assert r.status_code == 200, r.text
    assert PERSONAL not in r.text
    [tool] = r.json()["tools"]
    return tool


def assert_clean_events(admin, client, conversation_id) -> None:  # noqa: F811
    r = admin.get(f"{V1}/events", params={"conversation_id": conversation_id, "client_id": client["id"]})
    assert r.status_code == 200, r.text
    assert "workflow." in r.text and PERSONAL not in r.text


@pytest.mark.parametrize("reply,_state,expected", list(FAILURES.values()), ids=list(FAILURES))
def test_failed_pre_call_keeps_only_the_diagnosis(api, admin, client, http, reply, _state, expected):  # noqa: F811
    agent = pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    http.replies = [reply]
    asyncio.run(api.engine.run_pre_call(conversation_id))
    assert run_of(api, conversation_id).error == expected
    assert technical_tool(admin, client)["last_error"] == expected
    assert_clean_events(admin, client, conversation_id)


@pytest.mark.parametrize("reply,state,expected", list(FAILURES.values()), ids=list(FAILURES))
def test_failed_post_call_keeps_only_the_diagnosis(api, admin, client, http, reply, state, expected):  # noqa: F811
    agent = post_call_agent(admin, client)
    conversation_id = pending_conversation(api, agent, client, channel="whatsapp")
    http.replies = [reply]
    assert run_post_call(api, conversation_id) == state
    assert run_of(api, conversation_id).error == expected
    assert technical_tool(admin, client)["last_error"] == expected
    assert read(api, conversation_id).post_call_note is None
    assert_clean_events(admin, client, conversation_id)


def test_token_server_failure_keeps_only_the_diagnosis(api, admin, client, http):  # noqa: F811
    tool = charge_tool(BASE)
    tool["definition"]["http"]["auth"] = OAUTH_DEF
    assert admin.post(f"{V1}/clients/{client['id']}/secrets", json={"name": "CLAVE", "value": "s3creto"}).status_code == 201
    agent = post_call_agent(admin, client, tool=tool)
    conversation_id = pending_conversation(api, agent, client)
    runtime._TOKENS.clear()
    http.replies = [503]
    assert run_post_call(api, conversation_id) == "pending"
    assert run_of(api, conversation_id).error == "herramienta automática: auth_failed | HTTP 503 | falla de conexión: sí"


@pytest.fixture
def code_runner(monkeypatch):
    """El sandbox de codigo: contesta lo que diga `reply`."""
    monkeypatch.setattr(settings, "tools_runner_url", "http://runner.test")
    monkeypatch.setattr(settings, "tools_runner_token", "tok")
    runner = type("Runner", (), {"reply": {}})()
    real = httpx.AsyncClient

    def async_client(**kw):
        return real(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=runner.reply)), **kw)

    monkeypatch.setattr(runtime.httpx, "AsyncClient", async_client)
    return runner


def code_pre_call_agent(admin, client):  # noqa: F811
    tool = {"slug": "buscar_ficha", "type": "code", "definition": {
        "description": "Herramienta de un workflow.", "code": "export default async function () { return 1; }"}}
    return pre_call_agent(admin, client, tool=tool)


@pytest.mark.parametrize("reply", [
    {"ok": False, "error": PERSONAL, "logs": [PERSONAL]},
    {"ok": True, "result": {"ok": False, "error": PERSONAL}, "logs": []}], ids=["lanza", "ok_false"])
def test_failed_code_pre_call_keeps_only_the_type(api, admin, client, code_runner, reply):  # noqa: F811
    agent = code_pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    code_runner.reply = reply
    asyncio.run(api.engine.run_pre_call(conversation_id))
    expected = "herramienta automática: function_error | falla de conexión: no"
    assert run_of(api, conversation_id).error == expected
    assert technical_tool(admin, client)["last_error"] == expected
    assert_clean_events(admin, client, conversation_id)


def test_response_cannot_pose_as_not_executable(api, admin, client, code_runner):  # noqa: F811
    agent = code_pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    code_runner.reply = {"ok": True, "result": {"ok": False, "error": workflows.NOT_EXECUTABLE}, "logs": []}
    asyncio.run(api.engine.run_pre_call(conversation_id))
    with api.sessions() as s:
        event = s.scalars(select(Event).where(Event.type == "workflow.pre_call")).one()
    assert "reason" not in event.data


def test_tool_called_by_the_model_keeps_its_error_text(api, admin, client, http):  # noqa: F811
    agent = pre_call_agent(admin, client)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.entrante, PHONE)
    state = api.engine.store.get(conversation_id)
    tools = api.engine.tools
    spec = tools.workflow_spec(state, "buscar_ficha", "pre_call")
    turn = TurnTools(specs=[spec], ctx=tools.context(api.engine.workflow(state), state, None), settings=ToolSettings(),
                     sessions=api.sessions, client_id=state.client_id, agent_id=state.agent_id)
    http.replies = [runtime.Response(422, {"error": PERSONAL}, False)]
    [(_, seen)] = asyncio.run(turn.execute([{"id": "c1", "name": "buscar_ficha", "arguments": "{}"}], None, True))
    assert PERSONAL in seen and PERSONAL in run_of(api, conversation_id).error


# --- Resumen compartido ---------------------------------------------------------------------------

class SummaryLLM:
    def __init__(self, content=None, error=None, delay=0.0):
        self.content, self.error, self.delay = content, error, delay

    async def structured(self, messages, schema, name, **kw):
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.content, None


@pytest.mark.parametrize("llm,expected", [
    (SummaryLLM('{"resumen": " Juan pide un turno. "}'), "Juan pide un turno."),
    (SummaryLLM('{"resumen": ""}'), handoff_service.FALLBACK_SUMMARY),
    (SummaryLLM("no es json"), handoff_service.FALLBACK_SUMMARY),
    (SummaryLLM(error=RuntimeError("LLM caido")), handoff_service.FALLBACK_SUMMARY),
    (SummaryLLM('{"resumen": "tarde"}', delay=1), handoff_service.FALLBACK_SUMMARY),
], ids=["ok", "vacio", "invalido", "falla", "lento"])
def test_safe_summary(llm, expected):
    assert asyncio.run(handoff_service.safe_summary(llm, "conversación", timeout=0.05)) == expected


def test_summary_is_reexported_from_voice_handoff():
    assert voice_handoff.summarize is handoff_service.summarize
    assert voice_handoff.summary_messages is handoff_service.summary_messages
    assert voice_handoff.SUMMARY_SCHEMA is handoff_service.SUMMARY_SCHEMA
    assert voice_handoff.FALLBACK_SUMMARY == handoff_service.FALLBACK_SUMMARY
    assert voice_handoff.SUMMARY_TIMEOUT == handoff_service.SUMMARY_TIMEOUT
