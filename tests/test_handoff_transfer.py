"""Transferencia de una llamada a una persona (docs/features/EQUIPO_TELEFONIA.md, fase 2): la logica de
app/voice/handoff.py con un telefono falso, la herramienta transfer_call, el prompt y los minutos salientes."""
import asyncio
import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.conversation.models import AgentTurn, ConversationState, Message
from app.db import utcnow
from app.llm import platform_tools
from app.llm.prompt import build_turn_messages, build_system_prompt
from app.models import CallMode, CallRow, CallStatus, Event, HandoffArea, HandoffLeg, TeamMember, WaAccount
from app.services import calls as call_service
from app.services import handoff, quota
from app.voice import handoff as transfer
from app.whatsapp import team_notify
from app.whatsapp.graph import GraphError

from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)

DID = "+541152630861"
CUSTOMER = "sip_+5493513962553"


class FakeLine:
    """Cada telefono hace lo que diga `script`: confirm (atiende y marca 1), busy, no_answer, machine (dice
    lo de un buzon), silent (atiende y no marca), hangup (atiende y corta). `connected`: lo que pasa despues
    de conectar, en orden."""

    def __init__(self, script: dict[str, str], connected: list[tuple] = ()):
        self.script = script
        self.connected = list(connected)
        self.events: asyncio.Queue = asyncio.Queue()
        self.log: list[tuple] = []
        self.identity_of: dict[str, str] = {}

    async def say(self, text, interruptible=False):
        self.log.append(("say", text))

    async def hold(self, on):
        self.log.append(("hold", on))

    async def dial(self, identity, phone, ring_seconds):
        self.log.append(("dial", phone))
        self.identity_of[identity] = phone
        what = self.script[phone]
        if what in ("busy", "no_answer"):
            return transfer.DialResult(what, 486 if what == "busy" else None)
        if what == "hangup":
            self.events.put_nowait(("left", identity))
        return transfer.DialResult("answered")

    async def first_words(self, identity, seconds):
        return "Bienvenido al buzón de voz Claro" if self.script[self.identity_of[identity]] == "machine" else ""

    async def whisper(self, identity, text):
        self.log.append(("whisper", text))
        if self.script[self.identity_of[identity]] == "confirm":
            self.events.put_nowait(("dtmf", identity, "1"))

    async def stop_whisper(self):
        pass

    async def connect(self, identity):
        self.log.append(("connect", identity))
        for ev in self.connected:
            self.events.put_nowait(tuple(identity if x == "PERSON" else x for x in ev))

    async def listen(self, identity):
        pass

    async def remove(self, identity):
        self.log.append(("remove", identity))

    async def resume(self):
        self.log.append(("resume",))


def setup_call(api, admin, *, outbound_minutes=100, **area):
    """Cliente con dos personas (Ana, Juan) en Ventas y una llamada entrante en curso."""
    c = make_client(admin, outbound_minutes=outbound_minutes)
    agent = make_agent(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": DID, "agent_id": agent["id"]})
    ids = [admin.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": n, "phone": p}).json()["id"]
           for n, p in (("Ana", "3511111111"), ("Juan", "3512222222"))]
    a = admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]},
                   json={"name": "Ventas", "description": "Precios", "member_ids": ids, **area})
    assert a.status_code == 201, a.text
    with api.sessions() as s:
        call_service.start_inbound(s, api.engine, DID, "+5493513962553")
        conv = s.scalars(select(CallRow.conversation_id)).one()
        call_service.update_call(s, conv, status=CallStatus.en_curso, started_at=utcnow())
        areas = [{"id": a.json()["id"], "name": "Ventas", "when": "Precios", "schedule": None,
                  "schedule_text": "todos los días a toda hora"}]
    return c, conv, areas


def run(api, conv, client, areas, line, area="Ventas", **kw):
    said: list[tuple] = []
    tr = transfer.Transfer(sessions=api.sessions, line=line, conversation_id=conv, client_id=client["id"],
                           areas=areas, customer=CUSTOMER, caller="+5493513962553", confirm_seconds=0.3,
                           on_message=lambda role, text, **k: said.append((role, text, k.get("person"))), **kw)
    return asyncio.run(tr.run(area)), said


def event_types(api, conv):
    with api.sessions() as s:
        return [e.type for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.type.not_like("call.%"))
                                          .order_by(Event.id))]


def test_connects_after_busy_and_returns_to_ai(api, admin):
    c, conv, areas = setup_call(api, admin)
    line = FakeLine({"+5493511111111": "busy", "+5493512222222": "confirm"},
                    connected=[("text", "PERSON", "Hola, soy Juan de Ventas"),
                               ("text", CUSTOMER, "Quería un presupuesto"), ("dtmf", "PERSON", "2")])
    outcome, said = run(api, conv, c, areas, line)
    assert (outcome.status, outcome.ended) == ("connected", "returned_to_ai")
    assert [x for x in line.log if x[0] in ("dial", "connect", "say")] == [
        ("say", "Te paso con Ventas, un momento por favor."), ("dial", "+5493511111111"),
        ("dial", "+5493512222222"), ("connect", "persona-2"), ("say", "¿Te puedo ayudar con algo más?")]
    whisper = next(x[1] for x in line.log if x[0] == "whisper")
    assert whisper == "Derivación de Ventas: una consulta. Marcá 1 para atender."
    assert ("assistant", "Hola, soy Juan de Ventas", "Juan") in said and ("user", "Quería un presupuesto", None) in said
    assert event_types(api, conv) == [
        "handoff.requested", "hold.started", "handoff.dialing", "handoff.busy", "handoff.dialing",
        "handoff.answered", "hold.ended", "handoff.confirmed", "handoff.connected", "handoff.ended",
        "handoff.returned_to_ai"]
    with api.sessions() as s:
        legs = list(s.scalars(select(HandoffLeg).order_by(HandoffLeg.created_at)))
        assert [(leg.result, leg.sip_status) for leg in legs] == [("busy", 486), ("connected", None)]
        assert all(leg.ended_at for leg in legs) and legs[0].billed_seconds == 0
        # Round robin: el que atendio queda como el ultimo.
        assert s.get(HandoffArea, areas[0]["id"]).last_member_id == legs[1].team_member_id


def test_machine_silent_and_hangup_fall_back_with_message(api, admin):
    c, conv, areas = setup_call(api, admin)
    line = FakeLine({"+5493511111111": "machine", "+5493512222222": "silent"})
    outcome, _ = run(api, conv, c, areas, line)
    assert (outcome.status, outcome.result) == ("failed", "not_confirmed")
    assert ("remove", "persona-1") in line.log and ("remove", "persona-2") in line.log
    # El contestador no escucha el whisper de la segunda persona... y el cliente oye el mensaje de no atiende.
    assert line.log[-1] == ("say", handoff.render(handoff.DEFAULT_MESSAGES["no_answer"], area="Ventas"))
    assert ("hold", False) in line.log and "handoff.machine" in event_types(api, conv)

    line = FakeLine({"+5493511111111": "hangup", "+5493512222222": "busy"})
    outcome, _ = run(api, conv, c, areas, line)
    assert outcome.result == "busy"
    assert line.log[-1][1].startswith("En este momento Ventas está ocupado")


def test_person_hangs_up_resume_or_goodbye(api, admin):
    c, conv, areas = setup_call(api, admin, on_person_hangup="end")
    hung: list[str] = []

    async def hang_up(reason):
        hung.append(reason)

    line = FakeLine({"+5493511111111": "confirm"}, connected=[("left", "PERSON")])
    outcome, _ = run(api, conv, c, areas, line, hang_up=hang_up)
    assert outcome.ended == "person_hung_up" and hung == ["person_hung_up"]
    assert line.log[-1] == ("say", "Gracias por comunicarte, que tengas un buen día.")
    assert ("remove", "persona-1") not in line.log   # ya se habia ido


def test_customer_hangs_up_while_ringing(api, admin):
    c, conv, areas = setup_call(api, admin)

    class Ringing(FakeLine):
        async def dial(self, identity, phone, ring_seconds):
            self.events.put_nowait(("left", CUSTOMER))
            await asyncio.sleep(10)

    line = Ringing({})
    try:
        run(api, conv, c, areas, line)
        raise AssertionError("tenia que levantar CustomerGone")
    except transfer.CustomerGone:
        pass
    with api.sessions() as s:
        leg = s.scalars(select(HandoffLeg)).one()
        assert leg.result == "failed" and leg.ended_at is not None


def test_not_attempted_without_minutes_hours_or_area(api, admin):
    c, conv, areas = setup_call(api, admin, outbound_minutes=0)
    line = FakeLine({})
    outcome, _ = run(api, conv, c, areas, line)
    assert (outcome.status, outcome.result) == ("unavailable", "outbound_minutes")
    assert not [x for x in line.log if x[0] == "dial"]

    outcome, _ = run(api, conv, c, areas, FakeLine({}), area="Posventa")
    assert outcome.result == "unknown_area"

    admin.patch(f"{V1}/handoff-areas/{areas[0]['id']}", json={"schedule": {"week": {}}})
    line = FakeLine({})
    outcome, _ = run(api, conv, c, areas, line)
    assert outcome.result == "after_hours"
    assert line.log[-1][1].startswith("Ventas atiende")
    with api.sessions() as s:
        reasons = [e.data["reason"] for e in s.scalars(select(Event).where(Event.type == "handoff.unavailable"))]
    assert reasons == ["outbound_minutes", "unknown_area", "after_hours"]


def test_person_leg_counts_as_outbound_minutes_and_channels(api, admin, monkeypatch):
    c, conv, _ = setup_call(api, admin)
    now = utcnow()
    start, end = quota.month_bounds(now.replace(tzinfo=datetime.UTC))
    with api.sessions() as s:
        s.add(HandoffLeg(client_id=c["id"], conversation_id=conv, phone="+5493511111111", result="connected",
                         created_at=now, answered_at=now - datetime.timedelta(seconds=90),
                         connected_at=now, ended_at=now, billed_seconds=90))
        s.add(HandoffLeg(client_id=c["id"], conversation_id=conv, phone="+5493512222222", result="connected",
                         created_at=now, answered_at=now - datetime.timedelta(seconds=30), connected_at=now))
        s.add(HandoffLeg(client_id=c["id"], conversation_id=conv, phone="+5493512222222", result="machine",
                         created_at=now, answered_at=now, ended_at=now))
        s.commit()
        used = quota.used_seconds(s, c["id"], CallMode.saliente, start, end, now)
        assert used == 120 + 60                       # 90 s cerrado = 2 min + ~30 s en curso = 1; el contestador de 0 s, 0
        assert quota.used_seconds(s, c["id"], CallMode.entrante, start, end, now) == 60  # la entrante, recien empezada
        # Canales: la entrante en curso + el tramo abierto.
        assert quota.busy_channels(s, now) == 2
        monkeypatch.setattr(quota.settings, "anura_channels", 2)
        assert quota.handoff_check(s, c["id"]) == "no_channel"


# ---------- herramienta transfer_call y prompt ----------

AREAS = [{"id": "1", "name": "Ventas", "when": "Precios y visitas", "schedule": None,
          "schedule_text": "todos los días a toda hora"}]


def test_transfer_call_sets_the_handoff():
    state = ConversationState(conversation_id="x", agent_id="a", fields={})
    state.progress.handoff_areas = AREAS
    turn = AgentTurn(assistant_message="Te paso con ventas.")
    platform_tools.apply(turn, [{"name": "transfer_call", "arguments": '{"area": "Ventas"}'}], state)
    assert (turn.status, turn.handoff) == ("active", "Ventas")
    # Cortar gana: no se deriva una conversacion terminada.
    both = AgentTurn(assistant_message="Chau.")
    platform_tools.apply(both, [{"name": "transfer_call", "arguments": '{"area": "Ventas"}'},
                                {"name": "end_call", "arguments": "{}"}], state)
    assert (both.status, both.handoff) == ("completed", None)
    # Sin areas en la llamada no hay a donde derivar.
    state.progress.handoff_areas = []
    none = AgentTurn(assistant_message="Te paso.")
    platform_tools.apply(none, [{"name": "transfer_call", "arguments": '{"area": "Ventas"}'}], state)
    assert none.handoff is None


def test_transfer_call_lists_areas_and_history_keeps_the_person(api, admin):
    from app.agents.templates import ReferenceDefinitions

    workflow = ReferenceDefinitions().get("sales_discovery", 1)
    state = ConversationState(conversation_id="x", agent_id="a", fields={}, messages=[
        Message(role="assistant", text="Hola"), Message(role="user", text="Quiero hablar con alguien"),
        Message(role="assistant", text="Te paso con Ventas, un momento por favor."),
        Message(role="assistant", text="Hola, soy Juan", person="Juan", handoff_leg="L1"),
        Message(role="user", text="Quiero un presupuesto", handoff_leg="L1"),
        Message(role="assistant", text="¿Te puedo ayudar con algo más?")])
    assert [t["function"]["name"] for t in platform_tools.tools_for(state)] == ["end_call"]
    state.progress.handoff_areas = AREAS
    tools = platform_tools.tools_for(state)
    assert [t["function"]["name"] for t in tools] == ["end_call", "transfer_call"]
    transfer = tools[1]["function"]
    assert "Ventas (Precios y visitas): todos los días a toda hora, atiende ahora" in transfer["description"]
    assert transfer["parameters"]["properties"]["area"]["enum"] == ["Ventas"]
    # El prompt no lleva las areas: van en la herramienta.
    assert "Precios y visitas" not in build_system_prompt(workflow, "voice", state)
    history = build_turn_messages(workflow, state, "No, gracias")[1:]
    assert [m["role"] for m in history] == ["assistant", "user", "assistant", "assistant", "user", "assistant", "user"]
    assert history[3] == {"role": "assistant", "content": "Hola, soy Juan", "name": "Juan"}
    assert "name" not in history[4]


def test_agent_handoff_areas_are_validated(api, admin):
    c, _, areas = setup_call(api, admin)
    other = make_client(admin, slug="otro")
    other_area = admin.post(f"{V1}/handoff-areas", params={"client_id": other["id"]}, json={"name": "X"}).json()
    agent = make_agent(admin, c, template="sales_discovery", slug="ventas_texto")
    definition = admin.get(f"{V1}/agents/{agent['id']}").json()["definition"]

    def save(handoff_cfg):
        return admin.put(f"{V1}/agents/{agent['id']}/definition",
                         json={"definition": {**definition, "handoff": handoff_cfg}})

    assert save({"areas": [{"area_id": other_area["id"]}]}).status_code == 422
    assert save({"areas": [{"area_id": areas[0]["id"]}], "hold_music": {"track": "no-existe"}}).status_code == 422
    r = save({"areas": [{"area_id": areas[0]["id"], "when": "Para comprar"}]})
    assert r.status_code == 200, r.text
    assert r.json()["definition"]["handoff"]["hold_music"] == {"enabled": True, "track": "default", "volume": 0.3}
    with api.sessions() as s:
        from app.conversation.models import Workflow
        snap = handoff.call_areas(s, c["id"], Workflow.model_validate(r.json()["definition"]).handoff)
    assert [(a["name"], a["when"]) for a in snap] == [("Ventas", "Para comprar")]
    assert handoff.find_area(snap, "Ventas") is snap[0] and handoff.find_area(snap, "VENTAS ") is None


def test_area_used_by_an_agent_is_not_deleted(api, admin):
    c, _, areas = setup_call(api, admin)
    agent = make_agent(admin, c, template="sales_discovery", slug="ventas_texto")
    definition = admin.get(f"{V1}/agents/{agent['id']}").json()["definition"]
    admin.put(f"{V1}/agents/{agent['id']}/definition",
              json={"definition": {**definition, "handoff": {"areas": [{"area_id": areas[0]["id"]}]}}})
    r = admin.delete(f"{V1}/handoff-areas/{areas[0]['id']}")
    assert r.status_code == 409 and r.json()["code"] == "area_in_use"
    admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": {**definition, "handoff": {"areas": []}}})
    assert admin.delete(f"{V1}/handoff-areas/{areas[0]['id']}").status_code == 204


# ---------- cadena de areas, avisos y variables ----------

ANA, JUAN = "+5493511111111", "+5493512222222"
NOTICE = {"name": "equipo_aviso", "language": "es_AR", "params": ["area", "persona", "nombre", "ficha", "cliente"]}
COMPLEMENT = {"name": "equipo_llamada", "language": "es_AR", "params": ["area", "nombre"]}
CLOSED = {"week": {}}


class FakeGraph:
    """El Graph de team_notify. fail: destinos que Meta rechaza."""

    def __init__(self, fail=(), gate: asyncio.Event | None = None):
        self.sent: list[tuple] = []
        self.fail = fail
        self.gate = gate

    async def send_template(self, pnid, to, name, language, params=None):
        if self.gate is not None:
            await self.gate.wait()
        if to in self.fail:
            raise GraphError(131026, "No entregado")
        self.sent.append((to, name, params))
        return {"messages": [{"id": f"wamid.{len(self.sent)}"}]}

    async def aclose(self):
        pass


class Chain:
    """Cliente con Ana y Juan, con el toggle, una cuenta de WhatsApp y una llamada en curso. `area` crea areas."""

    def __init__(self, api, admin, monkeypatch, *, notify=True, graph=None, **tier):
        self.api, self.admin = api, admin
        self.client = make_client(admin, outbound_minutes=tier.pop("outbound_minutes", 100), whatsapp=True, **tier)
        agent = make_agent(admin, self.client)
        admin.post(f"{V1}/phone-numbers", json={"client_id": self.client["id"], "e164": DID, "agent_id": agent["id"]})
        self.ids = {}
        for name, phone in (("Ana", "3511111111"), ("Juan", "3512222222")):
            r = admin.post(f"{V1}/team", params={"client_id": self.client["id"]},
                           json={"name": name, "phone": phone, "whatsapp_notify": notify})
            assert r.status_code == 201, r.text
            self.ids[name] = r.json()["id"]
        with api.sessions() as s:
            account = WaAccount(client_id=self.client["id"], agent_id=agent["id"], phone_number_id="111",
                                waba_id="222", display_phone_number="+54 351 000", name="Prueba")
            s.add(account)
            s.commit()
            self.account = account.id
            call_service.start_inbound(s, api.engine, DID, "+5493513962553")
            self.conv = s.scalars(select(CallRow.conversation_id)).one()
            call_service.update_call(s, self.conv, status=CallStatus.en_curso, started_at=utcnow())
        self.graph = graph or FakeGraph()
        monkeypatch.setattr(team_notify, "GraphClient", lambda token, version: self.graph)
        self.areas: list[dict] = []

    def area(self, name: str, members=("Ana",), **body) -> str:
        r = self.admin.post(f"{V1}/handoff-areas", params={"client_id": self.client["id"]}, json={
            "name": name, "description": name, "member_ids": [self.ids[m] for m in members], **body})
        assert r.status_code == 201, r.text
        self.areas.append({"id": r.json()["id"], "name": name, "when": name, "schedule": None, "schedule_text": ""})
        return r.json()["id"]

    def notice(self, name: str, members=("Ana", "Juan"), template=NOTICE, **body) -> str:
        return self.area(name, members, delivery="whatsapp",
                         whatsapp={"account_id": self.account, "template": template}, **body)

    def whatsapp(self, **templates) -> dict:
        return {"account_id": self.account, **templates}

    def run(self, line, area: str, *, variables=None, summary=None, **kw) -> tuple[transfer.Outcome, list]:
        said: list[tuple] = []

        async def go():
            tasks: list[asyncio.Task] = []

            def spawn(coro):
                tasks.append(asyncio.create_task(coro))
                return tasks[-1]

            tr = transfer.Transfer(
                sessions=self.api.sessions, line=line, conversation_id=self.conv, client_id=self.client["id"],
                areas=self.areas, customer=CUSTOMER, caller="+5493513962553", confirm_seconds=0.3, summary=summary,
                on_message=lambda role, text, **k: said.append((role, text)), spawn_notice=spawn,
                get_vars=(variables if callable(variables) else lambda: variables or {}), **kw)
            outcome = await tr.run(area)
            await asyncio.gather(*tasks)
            return outcome

        return asyncio.run(go()), said

    def types(self) -> list[str]:
        return event_types(self.api, self.conv)

    def events(self, type: str) -> list[Event]:
        with self.api.sessions() as s:
            return list(s.scalars(select(Event).where(Event.type == type).order_by(Event.id)))


@pytest.fixture
def chain(api, admin, monkeypatch):
    return Chain(api, admin, monkeypatch)


def dials(line) -> list[str]:
    return [x[1] for x in line.log if x[0] == "dial"]


def says(line) -> list[str]:
    return [x[1] for x in line.log if x[0] == "say"]


def test_after_hours_goes_to_the_next_area(chain):
    guardia = chain.area("Guardia", ("Juan",))
    chain.area("Entrada", schedule=CLOSED, after_hours_area_id=guardia)
    line = FakeLine({JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    outcome, _ = chain.run(line, "Entrada")
    assert outcome.status == "connected" and dials(line) == [JUAN]
    # El mensaje de fuera de horario no se dice, y el de pase es de la que atiende.
    assert says(line)[0] == "Te paso con Guardia, un momento por favor."
    [event] = chain.events("handoff.rerouted")
    assert event.data["to"] == "Guardia" and event.data["reason"] == "after_hours"
    assert "handoff.unavailable" not in chain.types()


def test_nobody_answers_continues_with_continuous_music_and_one_message(chain):
    guardia = chain.area("Guardia", ("Juan",))
    chain.area("Entrada", no_answer_area_id=guardia)
    line = FakeLine({ANA: "no_answer", JUAN: "no_answer"})
    outcome, said = chain.run(line, "Entrada")
    assert outcome.status == "failed" and len(outcome.legs) == 2
    assert dials(line) == [ANA, JUAN]
    assert [x for x in line.log if x[0] == "hold"] == [("hold", True), ("hold", False)]
    assert says(line) == ["Te paso con Entrada, un momento por favor.",
                          handoff.render(handoff.DEFAULT_MESSAGES["no_answer"], area="Guardia")]
    assert len(said) == 2
    assert line.log.index(("hold", False)) > line.log.index(("dial", JUAN))
    types = chain.types()
    assert types.count("hold.started") == types.count("hold.ended") == 1
    assert types.count("handoff.requested") == 2 and types.count("handoff.rerouted") == 1


def test_no_members_continues(chain):
    guardia = chain.area("Guardia", ("Juan",))
    chain.area("Entrada", (), no_answer_area_id=guardia)
    line = FakeLine({JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    assert chain.run(line, "Entrada")[0].status == "connected"


def test_no_channel_goes_on_to_the_notice(chain, monkeypatch):
    aviso = chain.notice("Aviso final")
    guardia = chain.area("Guardia", ("Juan",), no_answer_area_id=aviso)
    chain.area("Entrada", no_answer_area_id=guardia)
    monkeypatch.setattr(quota.settings, "anura_channels", 0)
    line = FakeLine({})
    outcome, _ = chain.run(line, "Entrada")
    assert outcome.status == "notified" and dials(line) == []
    assert says(line) == ["Ya le avisé a Aviso final. Te van a contactar."]
    assert [e.data["reason"] for e in chain.events("handoff.rerouted")] == ["no_channel"]
    # Guardia queda sin atender, y es lo unico que cuenta: el pase al aviso no es un rerouted.
    assert [e.data["reason"] for e in chain.events("handoff.unavailable")] == ["no_channel"]
    assert len(chain.graph.sent) == 1


def test_nobody_answers_ends_in_the_notice_with_the_music_until_then(chain):
    aviso = chain.notice("Aviso final")
    chain.area("Entrada", no_answer_area_id=aviso)
    line = FakeLine({ANA: "no_answer"})
    outcome, _ = chain.run(line, "Entrada")
    assert outcome.status == "notified" and len(outcome.legs) == 1
    assert [x for x in line.log if x[0] == "hold"] == [("hold", True), ("hold", False)]
    assert says(line) == ["Te paso con Entrada, un momento por favor.", "Ya le avisé a Aviso final. Te van a contactar."]
    assert "handoff.rerouted" not in chain.types()


def test_outbound_minutes_goes_on_to_the_notice(api, admin, monkeypatch):
    chain = Chain(api, admin, monkeypatch, outbound_minutes=0)
    aviso = chain.notice("Aviso final")
    chain.area("Entrada", no_answer_area_id=aviso)
    outcome, _ = chain.run(FakeLine({}), "Entrada")
    assert outcome.status == "notified"
    assert [e.data["reason"] for e in chain.events("handoff.unavailable")] == ["outbound_minutes"]


def test_notice_reaches_one_person_and_says_notified(chain):
    armed = []
    chain.notice("Consultas")
    line = FakeLine({})
    outcome, said = chain.run(line, "Consultas", on_connected=armed.append,
                              variables={"nombre": "María", "ficha": "https://f/1"})
    assert (outcome.status, outcome.member_id) == ("notified", chain.ids["Ana"])
    assert chain.graph.sent == [(team_notify_recipient(ANA), "equipo_aviso",
                                 ["Consultas", "Ana", "María", "https://f/1", "+5493513962553"])]
    assert said == [("assistant", "Ya le avisé a Consultas. Te van a contactar.")]
    assert not dials(line) and not [x for x in line.log if x[0] == "hold"]
    # No es una derivacion: sin pedido, sin "te paso" y sin armar el post-call.
    assert armed == []
    types = chain.types()
    assert "handoff.requested" not in types and "handoff.rerouted" not in types
    assert "handoff.notified" in types
    with chain.api.sessions() as s:
        assert s.get(HandoffArea, chain.areas[0]["id"]).last_member_id == chain.ids["Ana"]


def test_notice_uses_the_next_person_when_meta_rejects(api, admin, monkeypatch):
    graph = FakeGraph()
    chain = Chain(api, admin, monkeypatch, graph=graph)
    graph.fail = {team_notify_recipient(ANA)}
    chain.notice("Consultas")
    outcome, _ = chain.run(FakeLine({}), "Consultas")
    assert (outcome.status, outcome.member_id) == ("notified", chain.ids["Juan"])
    assert len(graph.sent) == 1


def test_notice_skips_who_was_deactivated_during_the_previous_send(api, admin, monkeypatch):
    graph = FakeGraph(fail={team_notify_recipient(ANA)})
    chain = Chain(api, admin, monkeypatch, graph=graph)
    chain.notice("Consultas")
    real = graph.send_template

    async def send_template(pnid, to, name, language, params=None):
        with api.sessions() as s:
            s.get(TeamMember, chain.ids["Juan"]).active = False
            s.commit()
        return await real(pnid, to, name, language, params)

    graph.send_template = send_template
    line = FakeLine({})
    outcome, _ = chain.run(line, "Consultas")
    assert (outcome.status, outcome.result) == ("unavailable", "no_answer")
    assert graph.sent == [] and "handoff.notified" not in chain.types()
    assert says(line) == [handoff.render(handoff.DEFAULT_MESSAGES["no_answer"], area="Consultas")]


def test_notice_that_cannot_reread_does_not_break_the_transfer(chain, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("sin base")

    chain.notice("Consultas")
    monkeypatch.setattr(team_notify, "select", broken)
    line = FakeLine({})
    outcome, _ = chain.run(line, "Consultas")
    assert (outcome.status, outcome.result) == ("unavailable", "no_answer")
    assert chain.graph.sent == [] and "handoff.whatsapp_failed" in chain.types()
    assert says(line) == [handoff.render(handoff.DEFAULT_MESSAGES["no_answer"], area="Consultas")]


def team_notify_recipient(phone: str) -> str:
    from app.whatsapp.service import recipient
    return recipient(phone.lstrip("+"))


def test_notice_that_does_not_go_out_says_no_answer(api, admin, monkeypatch):
    chain = Chain(api, admin, monkeypatch, notify=False)
    chain.notice("Consultas")
    line = FakeLine({})
    outcome, _ = chain.run(line, "Consultas")
    assert (outcome.status, outcome.result) == ("unavailable", "no_answer")
    assert says(line) == [handoff.render(handoff.DEFAULT_MESSAGES["no_answer"], area="Consultas")]
    assert chain.graph.sent == [] and "handoff.notified" not in chain.types()
    # Un aviso directo que falla no es un pedido de derivacion, y queda como falla.
    assert "handoff.unavailable" not in chain.types() and "handoff.whatsapp_failed" in chain.types()


def test_closed_notice_is_not_a_request(chain):
    chain.notice("Consultas", schedule=CLOSED)
    outcome, _ = chain.run(FakeLine({}), "Consultas")
    assert (outcome.status, outcome.result) == ("unavailable", "after_hours")
    assert "handoff.unavailable" not in chain.types()
    assert chain.events("handoff.whatsapp_failed")[0].data["reason"] == "after_hours"


def test_failed_notice_follows_its_route(api, admin, monkeypatch):
    chain = Chain(api, admin, monkeypatch, notify=False)
    guardia = chain.area("Guardia", ("Juan",))
    chain.notice("Consultas", no_answer_area_id=guardia)
    line = FakeLine({JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    assert chain.run(line, "Consultas")[0].status == "connected"
    assert says(line)[0] == "Te paso con Guardia, un momento por favor."


def test_cycle_is_cut(chain):
    a = chain.area("A", ("Ana",))
    b = chain.area("B", ("Juan",), no_answer_area_id=a)
    chain.admin.patch(f"{V1}/handoff-areas/{a}", json={"no_answer_area_id": b})
    line = FakeLine({ANA: "no_answer", JUAN: "no_answer"})
    outcome, _ = chain.run(line, "A")
    assert outcome.status == "failed" and dials(line) == [ANA, JUAN]
    assert len(chain.events("handoff.rerouted")) == 1


def test_area_of_another_client_in_the_database_is_ignored(chain):
    other = make_client(chain.admin, "otro")
    mine = chain.area("Mia")
    with chain.api.sessions() as s:
        foreign = HandoffArea(client_id=other["id"], name="Ajena")
        s.add(foreign)
        s.flush()
        s.get(HandoffArea, mine).no_answer_area_id = foreign.id
        s.commit()
        foreign_id = foreign.id
    line = FakeLine({ANA: "no_answer"})
    outcome, _ = chain.run(line, "Mia")
    assert outcome.status == "failed" and "handoff.rerouted" not in chain.types()
    # Tampoco como primera area, aunque se la pasen.
    chain.areas.append({"id": foreign_id, "name": "Ajena"})
    assert chain.run(FakeLine({}), "Ajena")[0].result == "unknown_area"


def test_inactive_route_is_ignored(chain):
    guardia = chain.area("Guardia", ("Juan",), active=False)
    chain.area("Entrada", no_answer_area_id=guardia)
    line = FakeLine({ANA: "no_answer"})
    chain.run(line, "Entrada")
    assert dials(line) == [ANA] and "handoff.rerouted" not in chain.types()


WHISPER = {"whisper": "{{area}}: {{resumen}}. {{nota_operador}}. Marcá 1."}


@pytest.mark.parametrize("variables,heard", [
    ({"nota_operador": "María, al día"}, "Ventas: una consulta. María, al día. Marcá 1."),
    ({}, "Ventas: una consulta. . Marcá 1."),
    ({"nota_operador": None}, "Ventas: una consulta. . Marcá 1."),
])
def test_whisper_with_a_pre_call_variable(chain, variables, heard):
    chain.area("Ventas", messages=WHISPER)
    line = FakeLine({ANA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    chain.run(line, "Ventas", variables=variables)
    assert next(x[1] for x in line.log if x[0] == "whisper") == heard


def test_reserved_variables_win(chain):
    chain.area("Ventas", messages={"whisper": "{{area}} {{resumen}} {{cliente}} {{text}} {{propia}}"})
    line = FakeLine({ANA: "confirm"}, connected=[("dtmf", "PERSON", "2")])

    async def summary():
        return "pide precio"

    chain.run(line, "Ventas", summary=summary, variables={
        "area": "OTRA", "resumen": "OTRO", "cliente": "OTRO", "persona": "OTRA", "horario": "OTRO", "text": "x",
        "propia": "sí"})
    assert next(x[1] for x in line.log if x[0] == "whisper") == "Ventas pide precio +5493513962553 x sí"


def test_variables_are_read_in_each_area(chain):
    """Lo que el modelo eligio mientras tanto (select) se oye en la area siguiente."""
    guardia = chain.area("Guardia", ("Juan",), messages=WHISPER)
    chain.area("Entrada", messages=WHISPER, no_answer_area_id=guardia)
    notes = iter(["vieja", "nueva"])
    line = FakeLine({ANA: "silent", JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    chain.run(line, "Entrada", variables=lambda: {"nota_operador": next(notes)})
    assert [x[1] for x in line.log if x[0] == "whisper"] == ["Entrada: una consulta. vieja. Marcá 1.",
                                                            "Guardia: una consulta. nueva. Marcá 1."]


def test_a_failing_get_vars_does_not_stop_the_transfer(chain):
    chain.area("Ventas", messages=WHISPER)

    def broken():
        raise RuntimeError("sin base")

    line = FakeLine({ANA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    assert chain.run(line, "Ventas", variables=broken)[0].status == "connected"


def test_notice_template_takes_pre_call_variables_and_dashes_without_value(chain):
    chain.notice("Consultas")
    chain.run(FakeLine({}), "Consultas", variables={"nombre": "María"})
    [(_, name, params)] = chain.graph.sent
    assert name == "equipo_aviso" and params == ["Consultas", "Ana", "María", "-", "+5493513962553"]


def test_notice_only_asks_for_the_summary_if_the_template_has_it(chain):
    calls = []

    async def summary():
        calls.append(1)
        return "Pide un turno"

    chain.notice("Sin", template={"name": "t", "language": "es_AR", "params": ["area"]})
    chain.notice("Con", ("Ana",), template={"name": "t", "language": "es_AR", "params": ["resumen"]})
    chain.run(FakeLine({}), "Sin", summary=summary)
    assert calls == []
    chain.run(FakeLine({}), "Con", summary=summary)
    assert calls == [1] and chain.graph.sent[-1][2] == ["Pide un turno"]


def test_complement_does_not_delay_the_dial(api, admin, monkeypatch):
    gate = asyncio.Event()
    chain = Chain(api, admin, monkeypatch, graph=FakeGraph(gate=gate))
    chain.area("Ventas", ("Ana", "Juan"), whatsapp=chain.whatsapp(call_template=COMPLEMENT))

    class Line(FakeLine):
        async def dial(self, identity, phone, ring_seconds):
            # El envio sigue trabado: si el marcado lo esperara, esto no llegaria.
            assert chain.graph.sent == []
            if phone == JUAN:
                gate.set()
            return await super().dial(identity, phone, ring_seconds)

    line = Line({ANA: "no_answer", JUAN: "no_answer"})
    chain.run(line, "Ventas", variables={"nombre": "María"})
    assert dials(line) == [ANA, JUAN]
    assert sorted(x[2][1] for x in chain.graph.sent) == ["María", "María"] and len(chain.graph.sent) == 2


def test_complement_goes_once_per_person_in_the_chain(chain):
    guardia = chain.area("Guardia", ("Ana", "Juan"), whatsapp=chain.whatsapp(call_template=COMPLEMENT))
    chain.area("Entrada", ("Ana",), whatsapp=chain.whatsapp(call_template=COMPLEMENT), no_answer_area_id=guardia)
    chain.run(FakeLine({ANA: "no_answer", JUAN: "no_answer"}), "Entrada")
    assert len(chain.graph.sent) == 2 and len(chain.events("handoff.whatsapp_sent")) == 2


def test_complement_with_the_toggle_off_leaves_no_failure(api, admin, monkeypatch):
    chain = Chain(api, admin, monkeypatch, notify=False)
    chain.area("Ventas", whatsapp=chain.whatsapp(call_template=COMPLEMENT))
    chain.run(FakeLine({ANA: "no_answer"}), "Ventas")
    assert chain.graph.sent == [] and "handoff.whatsapp_failed" not in chain.types()


def test_no_complement_without_call_template(chain):
    # La plantilla de rotacion es del canal de texto: en una llamada no sale.
    chain.area("Ventas", whatsapp=chain.whatsapp(template={"name": "r", "language": "es_AR", "params": ["area"]}))
    chain.run(FakeLine({ANA: "no_answer"}), "Ventas")
    assert chain.graph.sent == []


def test_complement_failure_does_not_touch_the_call(api, admin, monkeypatch):
    chain = Chain(api, admin, monkeypatch, graph=FakeGraph(fail={team_notify_recipient(ANA)}))
    chain.area("Ventas", whatsapp=chain.whatsapp(call_template=COMPLEMENT))
    line = FakeLine({ANA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    assert chain.run(line, "Ventas")[0].status == "connected"
    assert "handoff.whatsapp_failed" in chain.types()


def test_complement_with_summary_outlives_a_transfer_that_ends_first(api, admin, monkeypatch):
    """La derivacion termina (corta el cliente) y la plantilla todavia espera el resumen: no se cancela."""
    chain = Chain(api, admin, monkeypatch)
    chain.area("Ventas", whatsapp=chain.whatsapp(
        call_template={"name": "c", "language": "es_AR", "params": ["resumen"]}))

    async def summary():
        await asyncio.sleep(0.05)
        return "Pide un turno"

    class Line(FakeLine):
        async def dial(self, identity, phone, ring_seconds):
            self.events.put_nowait(("left", CUSTOMER))
            await asyncio.sleep(10)

    async def go():
        tasks = []

        def spawn(coro):
            tasks.append(asyncio.create_task(coro))
            return tasks[-1]

        tr = transfer.Transfer(sessions=api.sessions, line=Line({}), conversation_id=chain.conv,
                               client_id=chain.client["id"], areas=chain.areas, customer=CUSTOMER, summary=summary,
                               spawn_notice=spawn)
        with pytest.raises(transfer.CustomerGone):
            await tr.run("Ventas")
        await asyncio.gather(*tasks)

    asyncio.run(go())
    assert [x[2] for x in chain.graph.sent] == [["Pide un turno"]]


def test_team_ring_has_no_complement():
    assert transfer.TeamRing(name="Equipo", ring_seconds=20).whatsapp is None


def test_person_leg_is_billed_from_answer_rounded_up_like_anura(api, admin):
    """Como Anura: el tramo se cobra desde que atiende, acepte o no, por los segundos reales redondeados hacia
    arriba (60,02 s = 2 min). Sin atender, 0. El atendido en curso sin confirmar ya cuenta."""
    c, conv, areas = setup_call(api, admin)
    now = utcnow()
    start, end = quota.month_bounds(now.replace(tzinfo=datetime.UTC))
    tr = transfer.Transfer(sessions=api.sessions, line=FakeLine({}), conversation_id=conv, client_id=c["id"],
                           areas=areas, customer=CUSTOMER, caller="+5493513962553")
    member = SimpleNamespace(id=areas[0]["id"])
    person = SimpleNamespace(id=None, phone="+5493511111111")
    sec = lambda x: datetime.timedelta(seconds=x)

    connected = tr._new_leg(member, person)
    tr._update_leg(connected, answered_at=now - sec(70.02), connected_at=now - sec(60))
    leg = tr._update_leg(connected, result="connected", ended_at=now - sec(10))
    assert leg.billed_seconds == 61
    unconfirmed = tr._new_leg(member, person)
    tr._update_leg(unconfirmed, answered_at=now - sec(11))
    assert tr._update_leg(unconfirmed, result="not_confirmed", ended_at=now).billed_seconds == 11
    missed = tr._new_leg(member, person)
    assert tr._update_leg(missed, result="no_answer", ended_at=now).billed_seconds == 0
    with api.sessions() as s:
        assert quota.handoff_seconds(s, c["id"], start, end, now) == 2 * 60 + 60
        s.add(HandoffLeg(client_id=c["id"], conversation_id=conv, phone="+5493512222222",
                         created_at=now, answered_at=now - sec(5)))       # atendio, todavia sin marcar 1
        s.add(HandoffLeg(client_id=c["id"], conversation_id=conv, phone="+5493512222222", created_at=now))  # sonando
        s.commit()
        assert quota.handoff_seconds(s, c["id"], start, end, now) == 2 * 60 + 60 + 60
        assert quota.handoff_seconds(s, c["id"], start, end, now, running_exact=True) == 2 * 60 + 60 + 5


# ---------- progreso en pantalla (tema handoff_status) ----------

class TimedLine(FakeLine):
    """FakeLine con tiempos: el aviso tarda, la persona entra a la room al timbrar (`joined`, salvo en
    `no_join`) y suena un rato antes del resultado."""

    def __init__(self, script, connected=(), no_join=()):
        super().__init__(script, connected)
        self.no_join = set(no_join)

    async def say(self, text, interruptible=False):
        await asyncio.sleep(0.05)
        await super().say(text, interruptible)

    async def dial(self, identity, phone, ring_seconds):
        await asyncio.sleep(0.05)
        if phone not in self.no_join:
            self.events.put_nowait(("joined", identity))
            self.events.put_nowait(("joined", "otra-persona"))   # la de otro no cambia la fase
        await asyncio.sleep(0.1)
        return await super().dial(identity, phone, ring_seconds)

    async def whisper(self, identity, text):
        await asyncio.sleep(0.05)
        self.log.append(("whisper", text))
        if self.script[self.identity_of[identity]] == "confirm":   # marca 1 al rato de terminar el susurro
            asyncio.get_running_loop().call_later(0.05, self.events.put_nowait, ("dtmf", identity, "1"))


def phases(rows) -> list[str]:
    return [p for p, _ in rows]


def check_final(snaps: list[dict]) -> dict:
    """Uno solo final, el ultimo; todos con el formato v1 y la suma de fases cerca del total."""
    assert snaps and all(s["v"] == 1 and s["id"] == 1 for s in snaps)
    assert [s["state"] for s in snaps[:-1]] == ["running"] * (len(snaps) - 1)
    final = snaps[-1]
    assert final["state"] != "running" and final["phase"] is None and final["total"] is not None
    summed = sum(t for _, t in final["pre"]) + sum(leg["total"] for leg in final["legs"])
    assert abs(summed - final["total"]) < 0.3, (summed, final)
    for leg in final["legs"]:
        assert abs(sum(t for _, t in leg["phases"]) - leg["total"]) < 0.2, leg
    return final


def test_progress_of_an_attempt_that_answers_and_presses_1(api, admin):
    c, conv, areas = setup_call(api, admin)
    line = TimedLine({ANA: "no_answer", JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")], no_join={ANA})
    snaps: list[dict] = []
    outcome, _ = run(api, conv, c, areas, line, on_progress=snaps.append)
    assert outcome.status == "connected"
    first = snaps[0]
    assert (first["state"], first["phase"], first["area"], first["legs"]) == ("running", "preparing", "Ventas", [])
    # Mientras suena Juan: la fase en curso es ringing y el intento de Ana ya tiene su resultado.
    ringing = next(s for s in snaps if s["phase"] == "ringing")
    assert [leg["result"] for leg in ringing["legs"]] == ["no_answer", None]
    [[name, seconds]] = ringing["legs"][1]["phases"]
    assert name == "dialing" and seconds >= 0.04
    final = check_final(snaps)
    assert (final["state"], final["result"]) == ("connected", "confirmed")
    assert phases(final["pre"]) == ["preparing", "announcing"] and final["pre"][1][1] >= 0.04
    ana, juan = final["legs"]
    # Sin joined, todo el intento queda en dialing.
    assert (ana["n"], ana["of"], ana["person"], ana["result"], phases(ana["phases"])) == (
        1, 2, "Ana", "no_answer", ["dialing"])
    assert (juan["n"], juan["of"], juan["person"], juan["result"]) == (2, 2, "Juan", "confirmed")
    assert phases(juan["phases"]) == ["dialing", "ringing", "summary", "whisper", "waiting_digit"]
    assert juan["no_answer"] is False and final["reroutes"] == []


def test_progress_of_no_answer_with_ringing_and_machine(api, admin):
    c, conv, areas = setup_call(api, admin)
    line = TimedLine({ANA: "no_answer", JUAN: "machine"})
    snaps: list[dict] = []
    outcome, _ = run(api, conv, c, areas, line, on_progress=snaps.append)
    final = check_final(snaps)
    assert (final["state"], final["result"]) == ("failed", "machine")
    ana, juan = final["legs"]
    assert phases(ana["phases"]) == ["dialing", "ringing"] and ana["result"] == "no_answer"
    assert juan["result"] == "machine" and phases(juan["phases"])[:3] == ["dialing", "ringing", "summary"]


def test_progress_is_anonymous_and_never_has_phones_or_ids(api, admin):
    import json

    c, conv, areas = setup_call(api, admin)
    line = TimedLine({ANA: "busy", JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    snaps: list[dict] = []
    run(api, conv, c, areas, line, on_progress=snaps.append, progress_names=False)
    final = check_final(snaps)
    assert [leg["person"] for leg in final["legs"]] == [None, None]
    with api.sessions() as s:
        secrets = [m.id for m in s.scalars(select(TeamMember))] + [areas[0]["id"], conv, c["id"], ANA, JUAN,
                                                                    "3511111111", "Ana", "Juan"]
    payload = json.dumps(snaps)
    assert not [x for x in secrets if x in payload]


def test_progress_reroute_and_notice(chain):
    aviso = chain.notice("Aviso final")
    guardia = chain.area("Guardia", ("Juan",), no_answer_area_id=aviso)
    chain.area("Entrada", no_answer_area_id=guardia)
    snaps: list[dict] = []
    outcome, _ = chain.run(TimedLine({ANA: "no_answer", JUAN: "busy"}), "Entrada", on_progress=snaps.append)
    assert outcome.status == "notified"
    final = check_final(snaps)
    assert (final["state"], final["result"], final["area"]) == ("notified", "notified", "Aviso final")
    assert [(r["from"], r["to"], r["reason"]) for r in final["reroutes"]] == [
        ("Entrada", "Guardia", "no_answer"), ("Guardia", "Aviso final", "busy")]
    assert [(leg["area"], leg["person"], leg["n"], leg["of"]) for leg in final["legs"]] == [
        ("Entrada", "Ana", 1, 1), ("Guardia", "Juan", 1, 1)]
    assert phases(final["pre"]) == ["preparing", "announcing", "notifying"]
    assert final["reroutes"][0]["at"] <= final["reroutes"][1]["at"] <= final["total"]


def test_progress_when_not_attempted(chain):
    chain.area("Entrada", schedule=CLOSED)
    snaps: list[dict] = []
    chain.run(FakeLine({}), "Entrada", on_progress=snaps.append)
    final = check_final(snaps)
    assert (final["state"], final["result"], final["legs"]) == ("failed", "after_hours", [])
    assert phases(final["pre"]) == ["preparing"]


def test_progress_callback_that_fails_does_not_stop_the_transfer(api, admin):
    c, conv, areas = setup_call(api, admin)
    calls: list[int] = []

    def broken(snapshot):
        calls.append(1)
        raise RuntimeError("publish_data")

    line = FakeLine({ANA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    outcome, _ = run(api, conv, c, areas, line, on_progress=broken)
    assert outcome.status == "connected" and len(calls) > 3


def test_progress_ends_failed_when_the_customer_hangs_up(api, admin):
    c, conv, areas = setup_call(api, admin)

    class Ringing(FakeLine):
        async def dial(self, identity, phone, ring_seconds):
            self.events.put_nowait(("joined", identity))
            await asyncio.sleep(0.05)
            self.events.put_nowait(("left", CUSTOMER))
            await asyncio.sleep(10)

    snaps: list[dict] = []
    with pytest.raises(transfer.CustomerGone):
        run(api, conv, c, areas, Ringing({}), on_progress=snaps.append)
    final = check_final(snaps)
    assert (final["state"], final["result"]) == ("failed", "customer_hung_up")
    assert final["legs"][0]["result"] == "failed" and phases(final["legs"][0]["phases"]) == ["dialing", "ringing"]


def test_team_ring_and_no_callback_do_not_publish(api, admin):
    """run_team (entrante al equipo) no tiene pantalla: sin on_progress no hay nada que emitir ni falla."""
    c, conv, areas = setup_call(api, admin)
    line = FakeLine({ANA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    outcome, _ = run(api, conv, c, areas, line)
    assert outcome.status == "connected"


# ---------- la persona de "Si nadie atiende" (no_answer_member_id) ----------

LUCIA = "+5493513333333"


def backup_person(chain, phone="3513333333", name="Lucía", client=None) -> str:
    r = chain.admin.post(f"{V1}/team", params={"client_id": (client or chain.client)["id"]},
                         json={"name": name, "phone": phone})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def legs(chain) -> list[HandoffLeg]:
    with chain.api.sessions() as s:
        return list(s.scalars(select(HandoffLeg).order_by(HandoffLeg.created_at)))


def test_nobody_accepts_then_the_no_answer_person_connects(chain):
    lucia = backup_person(chain)
    area = chain.area("Ventas", ("Ana", "Juan"), strategy="round_robin", no_answer_member_id=lucia)
    line = FakeLine({ANA: "no_answer", JUAN: "silent", LUCIA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    snaps: list[dict] = []
    outcome, _ = chain.run(line, "Ventas", on_progress=snaps.append)
    assert (outcome.status, outcome.ended) == ("connected", "returned_to_ai")
    assert dials(line) == [ANA, JUAN, LUCIA] and ("connect", "persona-3") in line.log
    assert [x for x in line.log if x[0] == "hold"] == [("hold", True), ("hold", False)]
    # handoff.dialing marca el intento; los demas eventos, iguales a los de un miembro.
    dialing = chain.events("handoff.dialing")
    assert [e.data.get("no_answer") for e in dialing] == [None, None, True]
    assert dialing[2].team_member_id == lucia and "handoff.rerouted" not in chain.types()
    assert [leg.result for leg in legs(chain)] == ["no_answer", "not_confirmed", "connected"]
    final = check_final(snaps)
    assert [(leg["n"], leg["of"], leg["person"], leg["no_answer"]) for leg in final["legs"]] == [
        (1, 3, "Ana", False), (2, 3, "Juan", False), (3, 3, "Lucía", True)]
    assert (final["state"], final["result"]) == ("connected", "confirmed")
    # Round robin: la persona de "Si nadie atiende" no entra en la rueda.
    with chain.api.sessions() as s:
        assert s.get(HandoffArea, area).last_member_id is None


@pytest.mark.parametrize("what", ["no_answer", "busy", "silent", "hangup", "machine"])
def test_no_answer_person_who_does_not_accept_brings_back_the_agent(chain, what):
    chain.area("Ventas", ("Ana",), no_answer_member_id=backup_person(chain))
    line = FakeLine({ANA: "no_answer", LUCIA: what})
    outcome, _ = chain.run(line, "Ventas")
    assert outcome.status == "failed" and dials(line) == [ANA, LUCIA]
    key = "busy" if what == "busy" else "no_answer"
    assert says(line)[-1] == handoff.render(handoff.DEFAULT_MESSAGES[key], area="Ventas")
    assert ("resume",) in line.log and len(legs(chain)) == 2


def test_area_without_callable_members_calls_the_no_answer_person(chain):
    chain.area("Ventas", (), no_answer_member_id=backup_person(chain))
    snaps: list[dict] = []
    outcome, _ = chain.run(FakeLine({LUCIA: "confirm"}, connected=[("dtmf", "PERSON", "2")]), "Ventas",
                           on_progress=snaps.append, progress_names=False)
    assert outcome.status == "connected"
    assert "handoff.unavailable" not in chain.types()
    [leg] = check_final(snaps)["legs"]
    assert (leg["n"], leg["of"], leg["person"], leg["no_answer"]) == (1, 1, None, True)


@pytest.mark.parametrize("change", [{"active": False}, {"phone": None}, "deleted", "member"])
def test_unusable_no_answer_person_brings_back_the_agent(chain, change):
    """Inactiva, sin telefono, borrada o (si la base lo dice) miembro del area: no se la llama."""
    lucia = backup_person(chain)
    area = chain.area("Ventas", ("Ana",), no_answer_member_id=lucia)
    if change == "deleted":
        assert chain.admin.delete(f"{V1}/team/{lucia}").status_code == 204
    elif change == "member":
        with chain.api.sessions() as s:
            s.get(HandoffArea, area).no_answer_member_id = chain.ids["Ana"]
            s.commit()
    else:
        with chain.api.sessions() as s:
            m = s.get(TeamMember, lucia)
            for k, v in change.items():
                setattr(m, k, v)
            s.commit()
    line = FakeLine({ANA: "no_answer", LUCIA: "confirm"})
    outcome, _ = chain.run(line, "Ventas")
    assert outcome.status == "failed" and dials(line) == [ANA]
    assert says(line)[-1] == handoff.render(handoff.DEFAULT_MESSAGES["no_answer"], area="Ventas")


def test_unusable_no_answer_person_in_an_area_without_members_is_no_members(chain):
    lucia = backup_person(chain)
    chain.area("Ventas", (), no_answer_member_id=lucia)
    with chain.api.sessions() as s:
        s.get(TeamMember, lucia).active = False
        s.commit()
    outcome, _ = chain.run(FakeLine({}), "Ventas")
    assert (outcome.status, outcome.result) == ("unavailable", "no_members")


def test_no_answer_person_of_another_client_in_the_database_is_ignored(chain):
    other = make_client(chain.admin, slug="otro")
    foreign = backup_person(chain, phone="3513333333", client=other)
    area = chain.area("Ventas", ("Ana",))
    with chain.api.sessions() as s:
        s.get(HandoffArea, area).no_answer_member_id = foreign
        s.commit()
    line = FakeLine({ANA: "no_answer", LUCIA: "confirm"})
    assert chain.run(line, "Ventas")[0].status == "failed" and dials(line) == [ANA]


def test_no_answer_person_is_not_called_after_hours_nor_without_minutes_or_channel(chain, monkeypatch):
    chain.area("Ventas", ("Ana",), schedule=CLOSED, no_answer_member_id=backup_person(chain))
    line = FakeLine({LUCIA: "confirm"})
    outcome, _ = chain.run(line, "Ventas")
    assert (outcome.status, outcome.result) == ("unavailable", "after_hours") and dials(line) == []

    chain.admin.patch(f"{V1}/handoff-areas/{chain.areas[0]['id']}", json={"schedule": None})
    monkeypatch.setattr(quota.settings, "anura_channels", 1)   # la entrante en curso ocupa el unico canal
    line = FakeLine({LUCIA: "confirm"})
    outcome, _ = chain.run(line, "Ventas")
    assert (outcome.status, outcome.result) == ("unavailable", "no_channel") and dials(line) == []


def test_after_hours_route_uses_the_no_answer_person_of_the_next_area(chain):
    guardia = chain.area("Guardia", ("Juan",), no_answer_member_id=backup_person(chain))
    chain.area("Entrada", schedule=CLOSED, after_hours_area_id=guardia)
    line = FakeLine({JUAN: "no_answer", LUCIA: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    assert chain.run(line, "Entrada")[0].status == "connected" and dials(line) == [JUAN, LUCIA]


def test_no_answer_person_counts_in_max_attempts(chain, monkeypatch):
    chain.area("Ventas", ("Ana", "Juan"), no_answer_member_id=backup_person(chain))
    monkeypatch.setattr(transfer, "MAX_ATTEMPTS", 2)
    line = FakeLine({})
    outcome, _ = chain.run(line, "Ventas")
    assert outcome.result == "too_many_attempts" and dials(line) == []


def test_no_answer_person_leg_is_billed_from_answer(chain):
    """Su tramo es uno mas: Anura cobra desde que atiende, acepte o no."""
    chain.area("Ventas", ("Ana",), no_answer_member_id=backup_person(chain))

    class Slow(FakeLine):
        async def whisper(self, identity, text):
            await asyncio.sleep(1.1)
            await super().whisper(identity, text)

    chain.run(Slow({ANA: "no_answer", LUCIA: "silent"}), "Ventas")
    ana, lucia = legs(chain)
    assert (ana.billed_seconds, ana.answered_at) == (0, None)
    assert lucia.result == "not_confirmed" and lucia.answered_at is not None and lucia.billed_seconds >= 2
    assert lucia.billed_seconds == quota.elapsed_seconds((lucia.ended_at - lucia.answered_at).total_seconds())


def test_with_no_answer_area_everything_stays_the_same(chain):
    guardia = chain.area("Guardia", ("Juan",))
    chain.area("Entrada", ("Ana",), no_answer_area_id=guardia)
    line = FakeLine({ANA: "no_answer", JUAN: "confirm"}, connected=[("dtmf", "PERSON", "2")])
    assert chain.run(line, "Entrada")[0].status == "connected" and dials(line) == [ANA, JUAN]
    assert [e.data.get("no_answer") for e in chain.events("handoff.dialing")] == [None, None]
