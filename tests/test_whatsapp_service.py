"""WhatsApp fase 1: del payload del webhook (forma real de Meta, tests/fixtures/wa) al
motor y la respuesta. El service se prueba directo con drain(): el TestClient no
espera las tareas de fondo."""
import asyncio
import copy
import datetime
import json
import logging
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.agents.definitions import DbDefinitions
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.conversation.store import ConversationStore
from app.models import Client, ConversationRow, Tier, WaAccount, WaMessage, WaThread
from app.services import agents as agent_service
from app.services.errors import Conflict, NotFound
from app.whatsapp import store
from app.whatsapp.graph import GraphClient, GraphError
from app.whatsapp.service import WhatsAppService

from .helpers import FakeLLM

FIXTURES = Path(__file__).parent / "fixtures" / "wa"
PNID = "100000000000002"
WA_ID = "5493510000000"
SEND_TO = "543510000000"  # el wa_id argentino sin el 9 (recipient)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def text_payload(body: str, wamid: str, pnid: str = PNID) -> dict:
    p = fixture("text.json")
    value = p["entry"][0]["changes"][0]["value"]
    value["metadata"]["phone_number_id"] = pnid
    value["messages"][0].update(id=wamid, text={"body": body})
    return p


def status_payload(name: str, wamid: str) -> dict:
    p = fixture(name)
    p["entry"][0]["changes"][0]["value"]["statuses"][0]["id"] = wamid
    return p


class FakeGraph:
    """send_text devuelve wamid.out1, wamid.out2...; fail: GraphError a levantar."""

    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []
        self.read: list[str] = []
        self.fail: GraphError | None = None

    async def send_text(self, pnid, to, body):
        if self.fail:
            raise self.fail
        self.sent.append((pnid, to, body))
        return {"messaging_product": "whatsapp", "contacts": [{"input": to, "wa_id": to}],
                "messages": [{"id": f"wamid.out{len(self.sent)}"}]}

    async def mark_read(self, pnid, wamid):
        self.read.append(wamid)
        return {"success": True}

    async def aclose(self):
        pass


class Wa:
    pass


def make_wa(sessions, template="demo_booking_classic", llm=None, graph=None) -> Wa:
    w = Wa()
    with sessions() as s:
        tier = Tier(name="T")
        s.add(tier)
        s.flush()
        client = Client(name="Acme", slug="acme", tier_id=tier.id)
        s.add(client)
        s.flush()
        agent = agent_service.create_agent(s, client, name="Turnos", slug="turnos", description="",
                                           definition=None, template_id=template, user_id=None)
        s.flush()
        account = store.create_account(s, client_id=client.id, agent_id=agent.id, phone_number_id=PNID,
                                       waba_id="100000000000001", display_phone_number="+1 555 000 0000")
        s.commit()
        w.client_id, w.agent_id, w.account_id = client.id, agent.id, account.id
    w.sessions = sessions
    w.llm = llm or FakeLLM()
    w.engine = ConversationEngine(w.llm, ConversationStore(sessions), DbDefinitions(sessions))
    w.graph = graph or FakeGraph()
    w.service = WhatsAppService(w.engine, sessions, graph_factory=lambda token: w.graph,
                                debounce_seconds=0.05, session_hours=24)
    return w


def reply(text="¡Hola! ¿En qué te ayudo?", **kw) -> AgentTurn:
    return AgentTurn(assistant_message=text, **kw)


def messages(sessions, **where) -> list[WaMessage]:
    with sessions() as s:
        q = select(WaMessage).order_by(WaMessage.created_at)
        for k, v in where.items():
            q = q.where(getattr(WaMessage, k) == v)
        return list(s.scalars(q))


def conversations(sessions) -> list[ConversationRow]:
    with sessions() as s:
        return list(s.scalars(select(ConversationRow).order_by(ConversationRow.created_at)))


async def send(w: Wa, *payloads) -> None:
    for p in payloads:
        w.service.handle_payload(p)
    await w.service.drain()


async def test_text_gets_a_reply(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola, soy Sofía. ¿Para qué día querés el turno?")))
    await send(w, text_payload("hola, quiero un turno", "wamid.in1"))

    assert w.graph.sent == [(PNID, SEND_TO, "Hola, soy Sofía. ¿Para qué día querés el turno?")]
    assert w.graph.read == ["wamid.in1"]
    (conv,) = conversations(sessions)
    assert conv.channel == "whatsapp" and conv.client_id == w.client_id
    # Sin apertura: el primer mensaje es el del cliente.
    assert [m["role"] for m in conv.messages] == ["user", "assistant"]
    assert conv.messages[0]["text"] == "hola, quiero un turno"
    assert w.engine.store.get(conv.id).channel == "whatsapp"
    (inb,) = messages(sessions, direction="in")
    assert (inb.wamid, inb.status, inb.type, inb.conversation_id) == ("wamid.in1", "answered", "text", conv.id)
    (out,) = messages(sessions, direction="out")
    assert (out.wamid, out.status, out.conversation_id, out.account_id) == ("wamid.out1", "sent", conv.id, w.account_id)
    with sessions() as s:
        thread = s.get(WaThread, conv.id)
        assert (thread.wa_id, thread.contact_name, thread.account_id) == (WA_ID, "Contacto Prueba", w.account_id)


async def test_repeated_wamid_is_one_turn(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply(), reply()))
    p = text_payload("hola", "wamid.dup")
    await send(w, p, copy.deepcopy(p))
    await send(w, copy.deepcopy(p))    # reenvio de Meta mas tarde
    assert len(w.llm.calls) == 1 and len(w.graph.sent) == 1
    assert len(messages(sessions, direction="in")) == 1


async def test_messages_in_the_window_are_one_turn(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()))
    for i, body in enumerate(["hola", "quería saber", "el precio"]):
        w.service.handle_payload(text_payload(body, f"wamid.m{i}"))
        await asyncio.sleep(0.01)
    await w.service.drain()
    assert [c[0] for c in w.llm.calls] == ["hola\nquería saber\nel precio"]
    assert len(w.graph.sent) == 1 and w.graph.read == ["wamid.m2"]
    assert {m.status for m in messages(sessions, direction="in")} == {"answered"}


async def test_text_arriving_while_the_llm_answers_redoes_the_turn(sessions):
    started, gate = asyncio.Event(), asyncio.Event()

    class SlowLLM(FakeLLM):
        async def converse(self, workflow, state, user_message, on_message=None):
            started.set()
            await gate.wait()
            return await super().converse(workflow, state, user_message, on_message)

    w = make_wa(sessions, llm=SlowLLM(reply("vieja"), reply("combinada")))
    w.service.handle_payload(text_payload("hola", "wamid.a"))
    await asyncio.wait_for(started.wait(), 1)
    w.service.handle_payload(text_payload("quiero un turno", "wamid.b"))
    gate.set()
    await w.service.drain()
    assert [c[0] for c in w.llm.calls] == ["hola", "hola\nquiero un turno"]
    assert [b for _, _, b in w.graph.sent] == ["combinada"]
    (conv,) = conversations(sessions)
    assert [m["text"] for m in conv.messages] == ["hola\nquiero un turno", "combinada"]


async def test_audio_gets_fixed_reply_without_llm(sessions, monkeypatch):
    from app.config import settings

    w = make_wa(sessions)
    audio = fixture("audio.json")
    second = copy.deepcopy(audio)
    second["entry"][0]["changes"][0]["value"]["messages"][0]["id"] = "wamid.audio2"
    await send(w, audio, second)       # dos audios juntos: una sola respuesta fija
    assert w.llm.calls == []
    assert [b for _, _, b in w.graph.sent] == [settings.wa_unsupported_reply]
    assert conversations(sessions) == []
    assert sorted(m.status for m in messages(sessions, direction="in")) == ["answered", "ignored"]
    assert {m.type for m in messages(sessions, direction="in")} == {"audio"}
    assert len(messages(sessions, direction="out")) == 1


async def test_status_before_send_and_failed(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()))
    # El read llega antes de que send_text devuelva el wamid (o es de otro envio).
    await send(w, status_payload("status_read.json", "wamid.out1"))
    (row,) = messages(sessions, direction="out")
    assert (row.status, row.conversation_id) == ("read", None)

    await send(w, text_payload("hola", "wamid.in1"))
    (row,) = messages(sessions, direction="out")
    assert row.status == "read" and row.conversation_id is not None   # no retrocede a sent

    await send(w, status_payload("status_failed.json", "wamid.out1"))
    (row,) = messages(sessions, direction="out")
    assert row.status == "failed" and row.error["code"] == 131047 and row.error["message"]


async def test_completed_conversation_then_new_one(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Listo, te esperamos. ¡Chau!", status="completed"), reply("¡Hola de nuevo!")))
    await send(w, text_payload("confirmo", "wamid.1"))
    await send(w, text_payload("otra cosa", "wamid.2"))
    first, second = conversations(sessions)
    assert first.status == "completed" and second.status == "active"
    assert second.agent_id == first.agent_id == w.agent_id
    assert second.messages[0]["text"] == "otra cosa"


async def test_session_expires_after_hours(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply(), reply(), reply()))
    await send(w, text_payload("hola", "wamid.1"))
    await send(w, text_payload("sigo", "wamid.2"))
    assert len(conversations(sessions)) == 1
    with sessions() as s:
        thread = s.scalar(select(WaThread))
        thread.last_user_at -= datetime.timedelta(hours=25)
        s.commit()
    await send(w, text_payload("volví", "wamid.3"))
    old, new = conversations(sessions)
    assert old.status == "active" and len(old.messages) == 4   # queda incompleta, como un corte
    assert new.messages[0]["text"] == "volví"


@pytest.mark.parametrize("what", ["client", "account", "unknown_pnid"])
async def test_ignored(sessions, caplog, what):
    caplog.set_level(logging.INFO, logger="app.whatsapp")
    w = make_wa(sessions, llm=FakeLLM(reply()))
    with sessions() as s:
        if what == "client":
            s.get(Client, w.client_id).active = False
        elif what == "account":
            s.get(WaAccount, w.account_id).active = False
        s.commit()
    pnid = "999" if what == "unknown_pnid" else PNID
    await send(w, text_payload("hola", "wamid.x", pnid=pnid))
    assert w.llm.calls == [] and w.graph.sent == [] and conversations(sessions) == []
    (inb,) = messages(sessions, direction="in")
    assert inb.status == "ignored"
    assert "ignorado" in caplog.text
    assert WA_ID not in caplog.text and "hola" not in caplog.text


async def test_send_error_is_saved_without_retry(sessions):
    graph = FakeGraph()
    graph.fail = GraphError("Re-engagement message", code=131047, status=400)
    w = make_wa(sessions, llm=FakeLLM(reply()), graph=graph)
    await send(w, text_payload("hola", "wamid.1"))
    (out,) = messages(sessions, direction="out")
    assert (out.wamid, out.status, out.error["code"]) == (None, "failed", 131047)
    assert out.conversation_id is not None
    (inb,) = messages(sessions, direction="in")
    assert inb.status == "error"
    assert len(w.llm.calls) == 1


async def test_llm_failure_marks_error_and_sends_nothing(sessions):
    w = make_wa(sessions, llm=FakeLLM())   # sin turnos: el LLM falla
    await send(w, text_payload("hola", "wamid.1"))
    assert w.graph.sent == []
    (inb,) = messages(sessions, direction="in")
    assert inb.status == "error"


async def test_classic_extracts_every_turn_on_whatsapp(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply(), reply(), extractions=[{}, {}]))
    await send(w, text_payload("hola, soy Ana", "wamid.1"))
    await w.engine.wait_extraction(conversations(sessions)[0].id)
    await send(w, text_payload("para el lunes", "wamid.2"))
    await w.engine.wait_extraction(conversations(sessions)[0].id)
    assert len(w.llm.extract_calls) == 2


async def test_paused_thread_is_not_answered(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply(), reply()))
    await send(w, text_payload("hola", "wamid.1"))
    with sessions() as s:
        s.scalar(select(WaThread)).paused = True
        s.commit()
    await send(w, text_payload("hola?", "wamid.2"))
    assert len(w.graph.sent) == 1 and len(conversations(sessions)) == 1


async def test_with_real_graph_client(sessions):
    """La request que sale a Meta, con GraphClient sobre httpx.MockTransport."""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.url.path, json.loads(request.content), request.headers["authorization"]))
        body = json.loads(request.content)
        if body.get("status") == "read":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(200, json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.real"}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    w = make_wa(sessions, llm=FakeLLM(reply("¡Hola!")))
    w.service = WhatsAppService(w.engine, sessions, debounce_seconds=0.01,
                                graph_factory=lambda token: GraphClient(token, http=http))
    await send(w, text_payload("hola", "wamid.1"))
    await http.aclose()
    paths = [p for p, _, _ in requests]
    assert paths == [f"/v25.0/{PNID}/messages"] * 2
    assert requests[0][1] == {"messaging_product": "whatsapp", "status": "read", "message_id": "wamid.1"}
    assert requests[1][1]["to"] == SEND_TO and requests[1][1]["text"] == {"body": "¡Hola!"}
    (out,) = messages(sessions, direction="out")
    assert out.wamid == "wamid.real"


def test_store_accounts(sessions, monkeypatch):
    from app.config import settings

    w = make_wa(sessions)
    monkeypatch.setattr(settings, "wa_access_token", "global")
    with sessions() as s:
        with pytest.raises(Conflict):
            store.create_account(s, client_id=w.client_id, agent_id=w.agent_id, phone_number_id=PNID,
                                 waba_id="1", display_phone_number="x")
        s.rollback()
        with pytest.raises(NotFound):
            store.create_account(s, client_id=w.client_id, agent_id="otro", phone_number_id="123",
                                 waba_id="1", display_phone_number="x")
        account = store.get_account(s, w.account_id)
        assert store.token_for(account) == "global"
        store.update_account(s, account, access_token="propio")
        assert store.token_for(account) == "propio"
        store.update_account(s, account, access_token="", active=False)
        assert account.access_token is None and not account.active
        assert [a.id for a in store.list_accounts(s, w.client_id)] == [w.account_id]
        assert store.list_accounts(s, "otro") == []


def test_cli_wa_account_is_idempotent(sessions, capsys):
    from app.cli import wa_account

    w = make_wa(sessions)
    with sessions() as s:
        wa_account(s, "200", "300", "+1 555 145 6632", "acme", "turnos", None)
        wa_account(s, "200", "300", "+1 555 145 6633", "acme", "turnos", "Prueba")
    with sessions() as s:
        a = store.account_by_pnid(s, "200")
        assert (a.display_phone_number, a.name, a.client_id, a.access_token) == ("+1 555 145 6633", "Prueba",
                                                                                 w.client_id, None)
        assert len(store.list_accounts(s)) == 2


# --- Hallazgos de la revision de la fase 1 ---

def stamped(body: str, wamid: str, ts: int) -> dict:
    p = text_payload(body, wamid)
    p["entry"][0]["changes"][0]["value"]["messages"][0]["timestamp"] = str(ts)
    return p


async def test_turn_follows_meta_timestamps_not_arrival(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()))
    # Dos POST que llegan desordenados: el turno va en el orden en que se escribieron.
    w.service.handle_payload(stamped("quería saber el precio", "wamid.b", 1790000001))
    w.service.handle_payload(stamped("hola", "wamid.a", 1790000000))
    await w.service.drain()
    assert [c[0] for c in w.llm.calls] == ["hola\nquería saber el precio"]


async def test_turn_chars_cap(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()))
    w.service = WhatsAppService(w.engine, sessions, graph_factory=lambda token: w.graph,
                                debounce_seconds=5, session_hours=24, max_turn_chars=10)
    for i, body in enumerate(["12345678", "abcdef", "no entra"]):
        w.service.handle_payload(text_payload(body, f"wamid.c{i}"))
    await asyncio.wait_for(w.service.drain(), 1)     # al llegar al tope no espera el debounce
    assert [c[0] for c in w.llm.calls] == ["12345678\na"]
    status = {m.wamid: m.status for m in messages(sessions, direction="in")}
    assert status == {"wamid.c0": "answered", "wamid.c1": "answered", "wamid.c2": "ignored"}


async def test_turns_cap_opens_another_conversation(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply(), reply(), reply()))
    w.service = WhatsAppService(w.engine, sessions, graph_factory=lambda token: w.graph,
                                debounce_seconds=0.01, session_hours=24, max_turns=2)
    for i, body in enumerate(["uno", "dos", "tres"]):
        await send(w, text_payload(body, f"wamid.t{i}"))
    first, second = conversations(sessions)
    assert [m["text"] for m in first.messages if m["role"] == "user"] == ["uno", "dos"]
    assert second.messages[0]["text"] == "tres"


async def test_get_service_is_one_instance(sessions, monkeypatch):
    from app import db, runtime
    from app.whatsapp import service as service_module

    monkeypatch.setattr(service_module, "_service", None)
    monkeypatch.setattr(runtime, "get_conversation_engine",
                        lambda: ConversationEngine(FakeLLM(), ConversationStore(sessions)))
    monkeypatch.setattr(db, "get_sessionmaker", lambda: sessions)
    # Async: corre en el loop, no en el threadpool de FastAPI.
    assert asyncio.iscoroutinefunction(service_module.get_service)
    a, b = await asyncio.gather(service_module.get_service(), service_module.get_service())
    assert a is b


def test_conversation_engine_is_one_per_process(sessions, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from app import runtime

    monkeypatch.setattr(runtime, "_engine", None)
    monkeypatch.setattr(runtime, "get_sessionmaker", lambda: sessions)
    with ThreadPoolExecutor(8) as pool:
        engines = list(pool.map(lambda _: runtime.get_conversation_engine(), range(16)))
    assert all(e is engines[0] for e in engines)


def test_sql_errors_hide_parameters():
    from app.db import make_engine

    assert make_engine("sqlite://").hide_parameters is True


def test_recipient_quita_el_9_de_celulares_argentinos():
    from app.whatsapp.service import recipient

    assert recipient("5493513962553") == "543513962553"
    assert recipient("543513962553") == "543513962553"
    assert recipient("15551456632") == "15551456632"
    assert recipient("549351") == "549351"
