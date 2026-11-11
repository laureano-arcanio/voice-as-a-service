"""Teclas en la conversacion del agente (app/voice/dtmf.py AgentKeys, app/voice/worker.py reply_keys y run_turn): el
grupo cerrado por la pausa es un turno del usuario "Marcó 123" con Message.dtmf. LLM falso: se mira el mensaje y el
historial, nunca la respuesta."""
import asyncio
from types import SimpleNamespace

from livekit.agents import llm

from app.conversation.models import AgentTurn
from app.llm.prompt import classic_history
from app.voice import dtmf
from app.voice import worker as livekit_agent
from app.voice.latency import TurnLatencyTracker

from .test_api import admin  # noqa: F401  (fixture)
from .test_dtmf import dtmf_events, shown
from .test_external_agent import endpoint, fake_endpoint_url, start, token_key  # noqa: F401  (fixtures)
from .test_handoff_transfer import CUSTOMER, setup_call

PAUSE = 0.05


def ev(who, digit):
    return SimpleNamespace(participant=SimpleNamespace(identity=who) if who else None, digit=digit)


def agent_keys(active=lambda: True):
    digits, groups = [], []
    keys = dtmf.AgentKeys(customer=lambda: CUSTOMER, on_digit=digits.append, on_group=groups.append, active=active,
                          keys=dtmf.Keys(pause=PAUSE))
    return keys, digits, groups


# ---------- agrupador con cierre ----------

async def test_group_closes_after_the_pause():
    keys, digits, groups = agent_keys()
    for d in "123":
        keys.on_dtmf(ev(CUSTOMER, d))
    assert groups == []                 # sigue marcando: todavia no hay turno
    await asyncio.sleep(PAUSE * 3)
    keys.on_dtmf(ev(CUSTOMER, "#"))
    await asyncio.sleep(PAUSE * 3)
    assert digits == ["1", "2", "3", "#"] and groups == ["123", "#"]


async def test_only_the_callers_keys():
    keys, digits, groups = agent_keys()
    keys.on_dtmf(ev("persona-1", "1"))  # el 1 de la persona es de la derivacion
    keys.on_dtmf(ev(None, "2"))
    await asyncio.sleep(PAUSE * 3)
    assert digits == [] and groups == []


async def test_silent_during_transfer_and_after_close():
    state = {"transfer": True}
    keys, digits, groups = agent_keys(active=lambda: not state["transfer"])
    keys.on_dtmf(ev(CUSTOMER, "1"))
    await asyncio.sleep(PAUSE * 3)
    assert digits == [] and groups == []
    # Un grupo abierto cuando empieza la derivacion se descarta.
    state["transfer"] = False
    keys.on_dtmf(ev(CUSTOMER, "2"))
    state["transfer"] = True
    await asyncio.sleep(PAUSE * 3)
    assert digits == ["2"] and groups == []
    # Al cortar con un grupo abierto no se llama a la sesion.
    state["transfer"] = False
    keys.on_dtmf(ev(CUSTOMER, "3"))
    keys.close()
    await asyncio.sleep(PAUSE * 3)
    assert digits == ["2", "3"] and groups == []


# ---------- el turno ----------

class FakeSession:
    def __init__(self):
        self.replies = []

    def generate_reply(self, *, user_input):
        self.replies.append(user_input)


def worker_agent(api, conv, monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(livekit_agent.WorkflowAgent, "session", property(lambda self: session))
    return livekit_agent.WorkflowAgent(api.engine, conv, TurnLatencyTracker(), on_completed=lambda reason: None), session


def test_keys_are_a_user_turn_with_dtmf(api, admin, monkeypatch):
    c, conv, _ = setup_call(api, admin)
    agent, session = worker_agent(api, conv, monkeypatch)
    agent.reply_keys("123")
    [message] = session.replies
    assert message.role == "user" and message.text_content == "Marcó 123"
    api.llm.turns.append(AgentTurn(assistant_message="Perfecto."))
    asyncio.run(agent.run_turn(llm.ChatContext([message]), None, lambda text: None))
    assert api.llm.calls[-1][0] == "Marcó 123"
    state = api.engine.store.get(conv)
    assert [(m.role, m.text, m.dtmf) for m in state.messages[-2:]] == [
        ("user", "Marcó 123", "123"), ("assistant", "Perfecto.", None)]
    assert classic_history(state.messages, False)[-2] == {"role": "user", "content": "Marcó 123"}
    assert agent.pending_dtmf == {}


def test_phrase_and_keys_in_one_turn_without_dtmf(api, admin, monkeypatch):
    """Borde aceptado: si entra una frase dicha en el mismo turno, va unido como dos frases seguidas."""
    c, conv, _ = setup_call(api, admin)
    agent, session = worker_agent(api, conv, monkeypatch)
    said = llm.ChatMessage(role="user", content=["Quiero la opción"])
    agent.reply_keys("2")
    api.llm.turns.append(AgentTurn(assistant_message="Bien."))
    asyncio.run(agent.run_turn(llm.ChatContext([said, session.replies[0]]), None, lambda text: None))
    user = api.engine.store.get(conv).messages[-2]
    assert (user.role, user.text, user.dtmf) == ("user", "Quiero la opción Marcó 2", None)


def test_during_transfer_only_the_line_keeps_the_keys(api, admin, monkeypatch):
    """La derivacion: el handler del agente calla y la linea (KeyLog) deja un mensaje por grupo, con un evento por
    digito, sin duplicar."""
    c, conv, _ = setup_call(api, admin)
    current = {"transfer": object()}
    keys, _, groups = agent_keys(active=lambda: current["transfer"] is None)
    keys.on_digit = lambda d: dtmf.record(api.sessions, c["id"], conv, d)
    log = dtmf.KeyLog(sessions=api.sessions, store=api.engine.store, conversation_id=conv)

    async def press():
        for d in "45":
            keys.on_dtmf(ev(CUSTOMER, d))   # los dos handlers reciben el mismo sip_dtmf_received
            log.press(d)
        await asyncio.sleep(PAUSE * 3)

    asyncio.run(press())
    assert groups == []
    assert [m[:3] for m in shown(api, conv)][-1] == ("user", "Marcó 45", "45")
    assert dtmf_events(api, conv) == [("customer", {"digit": "4"}), ("customer", {"digit": "5"})]


async def test_external_agent_receives_the_text(api, admin, endpoint):
    state = await start(api, admin)
    state, _ = await api.engine.process_turn(state.conversation_id, "Marcó 1", dtmf="1")
    assert endpoint.body()["messages"][-1] == {"role": "user", "content": "Marcó 1"}
    assert (state.messages[-2].text, state.messages[-2].dtmf) == ("Marcó 1", "1")
