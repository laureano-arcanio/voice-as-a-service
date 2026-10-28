"""Transferencia de una llamada a una persona (docs/features/EQUIPO_TELEFONIA.md, fase 2): la logica de
app/voice/handoff.py con un telefono falso, la herramienta transfer_call, el prompt y los minutos salientes."""
import asyncio
import datetime

from sqlalchemy import select

from app.conversation.models import AgentTurn, ConversationState, Message
from app.db import utcnow
from app.llm import platform_tools
from app.llm.prompt import build_turn_messages, build_system_prompt
from app.models import CallMode, CallRow, CallStatus, Event, HandoffArea, HandoffLeg
from app.services import calls as call_service
from app.services import handoff, quota
from app.voice import handoff as transfer

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

    async def say(self, text):
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
        assert 118 <= used <= 122                     # 90 cerrado + ~30 en curso; el contestador no cuenta
        assert quota.used_seconds(s, c["id"], CallMode.entrante, start, end, now) < 5
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
