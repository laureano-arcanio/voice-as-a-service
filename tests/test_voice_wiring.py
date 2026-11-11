"""Workflows en el worker de voz: el `entrypoint` real con el arnes (tests/voice_harness.py), en cada modo. Cuando
corre el pre-call, que se dice despues, el corte durante la espera, el arme del post-call y `finalize`."""
import asyncio
import json

import pytest
from sqlalchemy import select

from app.models import CallMode, CallRow, CallStatus, ConversationRow, Event, HandoffLeg, ToolRun, WaAccount
from app.services import calls as call_service
from app.voice import worker
from app.whatsapp import team_notify
from scripts.tools import mock_api

from .test_api import V1, admin  # noqa: F401  (admin: fixture)
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)
from .voice_harness import (
    CALLER,
    CUSTOMER,
    OPERATORS,
    Harness,
    add_agent,
    add_area,
    add_tool,
    charge_tool,
    http_tool,
    identify_tool,
    inbound_attributes,
    new_client,
    seed_call,
    team_to_agent,
)

PRE_CALL = {"pre_call": {"tool": "buscar_ficha", "timeout_ms": 1500}}
PHONE = "+5493514440000"


def identify_requests() -> list[dict]:
    return [r for r in mock_api.RECEIVED if r["path"] == "/identificar"]


def charge_requests() -> list[dict]:
    return [r for r in mock_api.RECEIVED if r["path"] == "/cobrar"]


@pytest.fixture
def client(admin):  # noqa: F811
    return new_client(admin)


@pytest.fixture
def agent(admin, client, mock_api_url):  # noqa: F811
    """Con pre-call, y con post-call handoff_accepted."""
    add_tool(admin, client, identify_tool(mock_api_url))
    add_tool(admin, client, charge_tool(mock_api_url))
    area = add_area(admin, client)
    return add_agent(admin, client, area=area, workflows={
        **PRE_CALL, "post_call": {"tool": "registrar_cobro", "when": "handoff_accepted"}})


def always_agent(admin, client, base):  # noqa: F811
    add_tool(admin, client, charge_tool(base))
    return add_agent(admin, client, workflows={"post_call": {"tool": "registrar_cobro", "when": "always"}})


def inbound_id(api) -> str:
    with api.sessions() as s:
        return s.scalars(select(CallRow.conversation_id)).one()


def row(api, conversation_id: str) -> ConversationRow:
    with api.sessions() as s:
        return s.get(ConversationRow, conversation_id)


def start_mode(api, agent, client, mode: str, monkeypatch) -> tuple[dict, dict | None, str]:
    """(metadata, atributos de la entrante, telefono que tiene que llegar en {{call.phone}})."""
    if mode == "entrante":
        return {}, inbound_attributes(), CALLER
    if mode == "whatsapp":
        return {}, inbound_attributes(wa_id="5493513962553"), CALLER
    if mode == "equipo":
        team_to_agent(monkeypatch, api)
        return {}, inbound_attributes(), CALLER
    call_mode, extra, phone = {
        "saliente": (CallMode.saliente, {"phone": PHONE}, PHONE),
        "celular": (CallMode.celular, {"phone": PHONE, "trial": True}, PHONE),
        "web": (CallMode.web, {"call_link_id": "link"}, None),
        "prueba": (CallMode.prueba, {}, None),
    }[mode]
    conversation_id = seed_call(api, agent["id"], client["id"], call_mode, phone)
    return {"conversation_id": conversation_id, **extra}, None, phone


# --- Pre-call en cada modo ------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["entrante", "whatsapp", "saliente", "celular", "web", "prueba", "equipo"])
def test_pre_call_runs_once_before_everything(api, agent, client, mode, monkeypatch):
    metadata, attributes, phone = start_mode(api, agent, client, mode, monkeypatch)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch)
    asyncio.run(h.run(metadata, attributes=attributes))

    assert h.order.count("pre_call") == 1
    assert h.order.index("pre_call") < h.order.index("session.start")
    if "create_sip_participant" in h.order:
        assert h.order.index("pre_call") < h.order.index("create_sip_participant")
    assert h.order[-1] == "say:Hola María Gómez, soy Ana."
    got = identify_requests()
    assert len(got) == 1
    assert json.loads(got[0]["body"])["from"] == (phone or "")      # {{call.phone}}: siempre la otra punta
    # Con el corte y el cierre ya registrados: si no, una persona que corta en la espera se pierde.
    assert ("registered", True, True) in h.log


def test_inbound_keeps_the_asterisk_line_for_the_full_recording(api, agent, client, monkeypatch):
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes={**inbound_attributes(), "atentina.line": "1731342342.7"}))
    assert h.call(inbound_id(api)).line_id == "1731342342.7"


@pytest.mark.parametrize("record", [True, False])
def test_outbound_asks_asterisk_for_the_full_recording(api, agent, client, monkeypatch, record):
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.saliente, PHONE)
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({"conversation_id": conversation_id, "phone": PHONE, "record_full_call": record}))
    (request,) = h.ctx.sip_requests
    assert dict(request.headers) == ({"X-Atentina-Rec": conversation_id} if record else {})


def test_loadtest_does_not_run_pre_call(api, agent, client, monkeypatch):
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.loadtest)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch)
    asyncio.run(h.run({"conversation_id": conversation_id, "loadtest": True}))
    assert "pre_call" not in h.order and identify_requests() == []
    assert "session.start" in h.order


def test_agent_without_workflows_behaves_as_today(api, admin, client, monkeypatch):
    agent = add_agent(admin, client)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    conversation_id = inbound_id(api)
    # La apertura tal cual, y ninguna marca del post-call.
    assert "pre_call" not in h.order and h.order[-1] == "say:Hola {{nombre}}, soy Ana."
    conv = row(api, conversation_id)
    assert (conv.post_call_status, conv.post_call_attempts, conv.post_call_next_at) == (None, 0, None)
    assert conv.agent_id == agent["id"]
    assert h.call(conversation_id).status == CallStatus.finalizada


# --- Apertura -------------------------------------------------------------------------------------

def test_opening_is_rendered_empty_when_the_tool_fails(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    add_tool(admin, client, http_tool("buscar_ficha", mock_api_url + "/falla", method="GET", assign=[
        {"var": "nombre", "path": "name"}], query={"veces": {"type": "string", "value": "99"},
                                                   "clave": {"type": "string", "value": "apertura"}}))
    add_agent(admin, client, workflows=PRE_CALL)
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    conversation_id = inbound_id(api)
    assert h.order[-1] == "say:Hola, soy Ana."      # no se lee "{{nombre}}"
    state = api.engine.store.get(conversation_id)
    assert state.messages[0].text == "Hola, soy Ana." and state.progress.tool_vars == {}
    with api.sessions() as s:
        run = s.scalars(select(ToolRun).where(ToolRun.conversation_id == conversation_id)).one()
    assert (run.ok, run.status_code, run.slug) == (False, 503, "buscar_ficha")


def test_slow_pre_call_expires_and_its_late_result_is_ignored(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    add_tool(admin, client, http_tool("buscar_ficha", mock_api_url + "/lento", method="GET", assign=[
        {"var": "nombre", "path": "ok"}], query={"segundos": {"type": "string", "value": "0.6"}}))
    add_agent(admin, client, workflows={"pre_call": {"tool": "buscar_ficha", "timeout_ms": 200}})
    h = Harness(api, monkeypatch)
    state_at_start = {}

    async def during(h):
        state_at_start["say"] = h.order[-1]
        await asyncio.wait(api.engine._late_pre_calls)
        await asyncio.sleep(0)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    conversation_id = inbound_id(api)
    assert state_at_start["say"] == "say:Hola, soy Ana."
    assert api.engine.store.get(conversation_id).progress.tool_vars == {}
    with api.sessions() as s:
        assert s.scalars(select(ToolRun).where(ToolRun.conversation_id == conversation_id)).one().ok is True


def test_team_fallback_rewrites_the_opening_not_what_was_said(api, agent, monkeypatch):
    team_to_agent(monkeypatch, api, spoken="Hola {{nombre}}, esto se dijo en la espera.")
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    messages = api.engine.store.get(inbound_id(api)).messages
    assert [m.text for m in messages] == ["Hola {{nombre}}, esto se dijo en la espera.", "Hola María Gómez, soy Ana."]
    assert h.order[-1] == "say:Hola María Gómez, soy Ana."


def test_campaign_keeps_its_opening_and_data(api, admin, client, agent, monkeypatch):
    with api.sessions() as s:
        state, text = api.engine.new_conversation(agent["id"], client["id"], session=s, phone=PHONE,
                                                  contact={"nombre": "Pedro", "deuda": "100"})
        api.engine.store.add(s, state)
        s.flush()
        s.add(CallRow(conversation_id=state.conversation_id, client_id=client["id"], mode=CallMode.saliente, phone=PHONE))
        s.commit()
    assert text == "Hola Pedro, soy Ana."
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({"conversation_id": state.conversation_id, "phone": PHONE}))
    assert h.order[-1] == "say:Hola Pedro, soy Ana."
    contact = api.engine.store.get(state.conversation_id).progress.contact
    assert contact["nombre"] == "Pedro" and contact["deuda"] == "100" and contact["situacion"] == "single"


# --- Corte durante el pre-call --------------------------------------------------------------------

def assert_never_started(h: Harness, api, conversation_id: str, reason: str) -> None:
    assert "session.start" not in h.order and "create_sip_participant" not in h.order
    assert not [x for x in h.order if x.startswith("say:")]
    call = h.call(conversation_id)
    assert call.status == CallStatus.finalizada and call.ended_reason == reason     # finalize corrio
    assert call.started_at is None
    assert row(api, conversation_id).post_call_status is None


def always_pre_call_agent(admin, client, base):  # noqa: F811
    add_tool(admin, client, identify_tool(base))
    add_tool(admin, client, charge_tool(base))
    return add_agent(admin, client, workflows={**PRE_CALL, "post_call": {"tool": "registrar_cobro", "when": "always"}})


def test_customer_hangs_up_during_pre_call(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    always_pre_call_agent(admin, client, mock_api_url)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch, lambda ctx: ctx.room.leave(CUSTOMER))
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    assert_never_started(h, api, inbound_id(api), "customer_hangup")


def test_customer_was_already_gone_when_pre_call_ended(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    # Se fue sin que corriera el handler: no hay salida que avisar, y el worker igual lo ve.
    always_pre_call_agent(admin, client, mock_api_url)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch, lambda ctx: ctx.room.remote_participants.clear())
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    assert_never_started(h, api, inbound_id(api), "customer_hangup")


def test_api_hang_up_during_outbound_pre_call_does_not_dial(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    # POST hang_up: pone el motivo y borra la room, sin salida de participante (services/calls.py).
    agent = always_pre_call_agent(admin, client, mock_api_url)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.saliente, PHONE)

    def hang_up(ctx):
        with api.sessions() as s:
            call_service.update_call(s, conversation_id, ended_reason=call_service.HANGUP_REASON)
        ctx.room.connected = False

    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch, hang_up)
    asyncio.run(h.run({"conversation_id": conversation_id, "phone": PHONE}))
    assert_never_started(h, api, conversation_id, call_service.HANGUP_REASON)


def test_closed_room_during_pre_call_in_any_mode(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    agent = always_pre_call_agent(admin, client, mock_api_url)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.web)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch, lambda ctx: setattr(ctx.room, "connected", False))
    asyncio.run(h.run({"conversation_id": conversation_id, "call_link_id": "link"}))
    assert "session.start" not in h.order and h.call(conversation_id).status == CallStatus.finalizada


def test_team_fallback_cut_keeps_the_time_of_the_team(api, agent, monkeypatch):
    team_to_agent(monkeypatch, api)
    h = Harness(api, monkeypatch)
    h.on_pre_call(monkeypatch, lambda ctx: ctx.room.leave(CUSTOMER))
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    assert "session.start" not in h.order
    assert h.call(inbound_id(api)).duration_seconds >= 30      # corren desde que entro al equipo


# --- Arme del post-call ---------------------------------------------------------------------------

def transfer(seen: dict, api, conversation_id=None):
    async def during(h):
        await h.session.agent.on_handoff("Ventas", False)
        seen["status"] = row(api, conversation_id or inbound_id(api)).post_call_status
    return during


def test_connected_operator_arms_handoff_accepted(api, agent, monkeypatch):
    h = Harness(api, monkeypatch, script=OPERATORS, connected=[("dtmf", "PERSON", "2")])
    seen: dict = {}
    asyncio.run(h.run({}, attributes=inbound_attributes(), during=transfer(seen, api)))
    assert seen["status"] == "armed"
    conv = row(api, inbound_id(api))
    assert conv.post_call_status == "pending" and conv.post_call_next_at is not None


def test_caller_keys_during_the_transfer_only(api, agent, monkeypatch):
    """Las teclas de quien llama quedan en la conversacion mientras hay derivacion, con el tramo si esta conectado;
    la RoomLine sigue registrada despues, sin guardarlas (las del agente son de otra parte)."""
    h = Harness(api, monkeypatch, script=OPERATORS, connected=[("dtmf", "PERSON", "2")])
    base = worker.transfer.RoomLine

    class KeyLine(base):
        async def dial(self, identity, phone, ring_seconds):
            self.on_dtmf("1")
            return await super().dial(identity, phone, ring_seconds)

        async def connect(self, identity):
            self.on_dtmf("5")
            await super().connect(identity)

    monkeypatch.setattr(worker.transfer, "RoomLine", KeyLine)
    seen: dict = {}

    async def during(h):
        await h.session.agent.on_handoff("Ventas", False)
        seen["after"] = h.line.on_dtmf

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert seen["after"] is None
    conv = inbound_id(api)
    keys = [m for m in api.engine.store.get(conv).messages if m.dtmf]
    with api.sessions() as s:
        leg = s.scalars(select(HandoffLeg.id).where(HandoffLeg.result == "connected")).one()
        digits = [e.data["digit"] for e in s.scalars(select(Event).where(Event.type == "call.dtmf"))]
    assert [(m.role, m.text, m.handoff_leg) for m in keys] == [("user", "Marcó 1", None), ("user", "Marcó 5", leg)]
    assert digits == ["1", "5"]


def test_operator_not_connected_does_not_arm(api, agent, monkeypatch):
    h = Harness(api, monkeypatch, script={k: "no_answer" for k in OPERATORS})
    seen: dict = {}
    asyncio.run(h.run({}, attributes=inbound_attributes(), during=transfer(seen, api)))
    assert seen["status"] is None and row(api, inbound_id(api)).post_call_status is None


def test_no_transfer_does_not_arm_handoff_accepted(api, agent, monkeypatch):
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes()))
    assert row(api, inbound_id(api)).post_call_status is None


def test_always_arms_when_connected(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    always_agent(admin, client, mock_api_url)
    h = Harness(api, monkeypatch)
    seen: dict = {}

    async def during(h):
        seen["status"] = row(api, inbound_id(api)).post_call_status

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert seen["status"] == "armed" and row(api, inbound_id(api)).post_call_status == "pending"


def test_always_does_not_arm_when_the_call_never_connected(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    agent = always_agent(admin, client, mock_api_url)
    conversation_id = seed_call(api, agent["id"], client["id"], CallMode.saliente, PHONE)
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({"conversation_id": conversation_id, "phone": PHONE}, sip_error=RuntimeError("sin canal")))
    assert h.call(conversation_id).status == CallStatus.fallida
    assert row(api, conversation_id).post_call_status is None


@pytest.mark.parametrize("mode,extra", [(CallMode.prueba, {}), (CallMode.loadtest, {"loadtest": True}),
                                        (CallMode.celular, {"phone": PHONE, "trial": True})])
def test_test_modes_do_not_arm(api, admin, client, mock_api_url, monkeypatch, mode, extra):  # noqa: F811
    agent = always_agent(admin, client, mock_api_url)
    conversation_id = seed_call(api, agent["id"], client["id"], mode, extra.get("phone"))
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({"conversation_id": conversation_id, **extra}))
    assert row(api, conversation_id).post_call_status is None


# --- finalize -------------------------------------------------------------------------------------

def test_finalize_marks_pending_after_the_extraction(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    always_agent(admin, client, mock_api_url)
    from app.conversation import workflows
    from app.conversation.models import Message
    api.llm.extractions = [{"contact_name": "Juan"}]
    seen = {}
    real = workflows.mark_ended

    def mark_ended(sessions, conversation_id):
        seen["field"] = api.engine.store.get(conversation_id).fields["contact_name"]
        real(sessions, conversation_id)

    monkeypatch.setattr(workflows, "mark_ended", mark_ended)

    async def during(h):
        state = api.engine.store.get(inbound_id(api))
        state.messages += [Message(role="user", text="Soy Juan"), Message(role="assistant", text="Hola Juan")]
        api.engine.store.save(state)

    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert seen["field"] == "Juan"      # el post-call ve lo extraido
    assert row(api, inbound_id(api)).post_call_status == "pending"


def test_finalize_marks_pending_even_if_finish_raises(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    always_agent(admin, client, mock_api_url)

    async def boom(conversation_id, timeout=10):
        raise RuntimeError("extraccion")

    monkeypatch.setattr(api.engine, "finish", boom)
    h = Harness(api, monkeypatch)
    with pytest.raises(RuntimeError):
        asyncio.run(h.run({}, attributes=inbound_attributes()))
    assert row(api, inbound_id(api)).post_call_status == "pending"


@pytest.mark.parametrize("how", ["fallida", "borrada"])
def test_finalize_marks_pending_with_a_failed_or_missing_call(api, admin, client, mock_api_url, monkeypatch, how):  # noqa: F811
    # finalize hace return al ver esto: la marca tiene que ir antes.
    always_agent(admin, client, mock_api_url)

    async def during(h):
        conversation_id = inbound_id(api)
        seen.append(conversation_id)
        with api.sessions() as s:
            call = s.get(CallRow, conversation_id)
            if how == "fallida":
                call.status = CallStatus.fallida
            else:
                s.delete(call)
            s.commit()

    seen: list = []
    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert row(api, seen[0]).post_call_status == "pending"


def test_customer_hangs_up_with_operator_connected_runs_post_call(api, agent, monkeypatch):
    from app.conversation import workflows
    # El operador esta conectado y el cliente corta: se mueve la room y finalize deja pendiente el cobro.
    h = Harness(api, monkeypatch, script=OPERATORS, connected=[("left", CUSTOMER)])

    async def during(h):
        await h.session.agent.on_handoff("Ventas", False)
        h.ctx.room.leave(CUSTOMER)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    conversation_id = inbound_id(api)
    assert row(api, conversation_id).post_call_status == "pending"
    asyncio.run(workflows.run_once(api.sessions, api.engine))
    assert row(api, conversation_id).post_call_status == "done"
    got = charge_requests()
    assert len(got) == 1 and got[0]["headers"]["idempotency-key"] == f"{conversation_id}:post_call"
    assert json.loads(got[0]["body"]) == {"conversation_id": conversation_id, "from": CALLER}


# --- Avisos por WhatsApp y variables en la llamada -------------------------------------------------

class FakeGraph:
    def __init__(self):
        self.sent: list[tuple] = []

    async def send_template(self, pnid, to, name, language, params=None):
        self.sent.append((to, name, params))
        return {"messages": [{"id": f"wamid.{len(self.sent)}"}]}

    async def aclose(self):
        pass


NOTICE = {"name": "equipo_consulta", "language": "es_AR", "params": ["nombre", "ficha", "cliente", "resumen"]}


@pytest.fixture
def consultas(api, admin, client, mock_api_url, monkeypatch):  # noqa: F811
    """Agente con pre-call, un area de llamada (Ventas) y una de aviso (Consultas), y el Graph falso."""
    add_tool(admin, client, identify_tool(mock_api_url))
    add_tool(admin, client, charge_tool(mock_api_url))
    ventas = add_area(admin, client)
    agent = add_agent(admin, client, area=ventas, workflows={
        **PRE_CALL, "post_call": {"tool": "registrar_cobro", "when": "handoff_accepted"}})
    with api.sessions() as s:
        account = WaAccount(client_id=client["id"], agent_id=agent["id"], phone_number_id="111", waba_id="222",
                            display_phone_number="+54 351 000", name="Prueba")
        s.add(account)
        s.commit()
        account_id = account.id
    member = admin.post(f"{V1}/team", params={"client_id": client["id"]},
                        json={"name": "Lía", "phone": "3513333333", "whatsapp_notify": True}).json()["id"]
    area = admin.post(f"{V1}/handoff-areas", params={"client_id": client["id"]}, json={
        "name": "Consultas", "description": "Lo demas", "member_ids": [member], "delivery": "whatsapp",
        "whatsapp": {"account_id": account_id, "template": NOTICE}})
    assert area.status_code == 201, area.text
    definition = dict(agent["definition"])
    definition["handoff"] = {"areas": [{"area_id": ventas, "when": "Precios"},
                                       {"area_id": area.json()["id"], "when": "Lo demas"}]}
    r = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition})
    assert r.status_code == 200, r.text
    graph = FakeGraph()
    monkeypatch.setattr(team_notify, "GraphClient", lambda token, version: graph)
    return graph


async def stub_summary(llm, conversation):
    return "Pide un turno"


def notified(api) -> list[Event]:
    with api.sessions() as s:
        return list(s.scalars(select(Event).where(Event.type == "handoff.notified")))


def test_get_vars_and_spawn_notice_reach_the_transfer(api, consultas, admin, client, monkeypatch):
    # El whisper oye lo oculto del pre-call, y el aviso lo lleva.
    monkeypatch.setattr(worker.transfer, "summarize", stub_summary)
    ventas = admin.get(f"{V1}/handoff-areas", params={"client_id": client["id"]}).json()
    ventas = next(a for a in ventas if a["name"] == "Ventas")
    r = admin.patch(f"{V1}/handoff-areas/{ventas['id']}", json={"messages": {"whisper": "{{nota_operador}}. Marcá 1."}})
    assert r.status_code == 200, r.text
    h = Harness(api, monkeypatch, script=OPERATORS, connected=[("dtmf", "PERSON", "2")])

    async def during(h):
        await h.session.agent.on_handoff("Ventas", False)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert ("whisper", "María Gómez, al día. Marcá 1.") in h.line.log


def test_notice_with_the_customer_on_the_line(api, consultas, monkeypatch):
    monkeypatch.setattr(worker.transfer, "summarize", stub_summary)
    h = Harness(api, monkeypatch)

    async def during(h):
        await h.session.agent.on_handoff("Consultas", False)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    [(_, name, params)] = consultas.sent
    assert name == "equipo_consulta"
    assert params == ["María Gómez", "Ficha: https://fichas.test/c/1", CALLER, "Pide un turno"]
    assert ("say", "Ya le avisé a Consultas. Te van a contactar.") in h.line.log
    assert len(notified(api)) == 1
    # Un aviso no arma el post-call de handoff_accepted.
    assert row(api, inbound_id(api)).post_call_status is None


def test_customer_gone_before_the_notice_still_sends_it(api, consultas, monkeypatch):
    monkeypatch.setattr(worker.transfer, "summarize", stub_summary)
    h = Harness(api, monkeypatch)

    async def during(h):
        h.ctx.room.leave(CUSTOMER)
        await h.session.agent.on_handoff("Consultas", False)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert len(consultas.sent) == 1 and len(notified(api)) == 1
    assert h.line is None    # sin nadie en la linea, no se arma el lado de LiveKit


def test_customer_gone_during_a_slow_summary_finalize_waits_and_sends_once(api, consultas, monkeypatch):
    finished: list = []
    real_finish = api.engine.finish

    async def slow(llm, conversation):
        await asyncio.sleep(0.2)
        return "Pide un turno"

    async def finish(conversation_id):
        finished.append(len(consultas.sent))
        return await real_finish(conversation_id)

    monkeypatch.setattr(worker.transfer, "summarize", slow)
    monkeypatch.setattr(api.engine, "finish", finish)
    h = Harness(api, monkeypatch)

    async def during(h):
        task = h.session.agent.on_handoff("Consultas", False)
        await asyncio.sleep(0.05)
        assert consultas.sent == []
        h.line.events.put_nowait(("left", CUSTOMER))
        h.ctx.room.leave(CUSTOMER)
        await task

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert finished == [1], "finalize espera el aviso antes de engine.finish"
    assert len(consultas.sent) == 1 and len(notified(api)) == 1
    # Corto: no se le dice que se avisó.
    assert ("say", "Ya le avisé a Consultas. Te van a contactar.") not in h.line.log


def test_finalize_does_not_wait_forever_for_a_notice(api, consultas, monkeypatch):
    async def stuck(llm, conversation):
        await asyncio.sleep(60)

    monkeypatch.setattr(worker.transfer, "summarize", stuck)
    monkeypatch.setattr(worker.transfer, "SUMMARY_TIMEOUT", 60.0)
    monkeypatch.setattr(worker, "NOTICE_WAIT_SECONDS", 0.05)
    h = Harness(api, monkeypatch)

    async def during(h):
        h.ctx.room.leave(CUSTOMER)
        await h.session.agent.on_handoff("Consultas", False)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert h.call(inbound_id(api)).status == CallStatus.finalizada and consultas.sent == []


def test_customer_gone_before_an_emergency_changes_nothing(api, consultas, monkeypatch):
    # Un area de llamada sin nadie en la linea termina como siempre: sin marcar y sin aviso.
    h = Harness(api, monkeypatch, script=OPERATORS)

    async def during(h):
        h.ctx.room.leave(CUSTOMER)
        await h.session.agent.on_handoff("Ventas", False)

    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    assert consultas.sent == [] and h.line is None
    with api.sessions() as s:
        assert s.scalars(select(HandoffLeg)).all() == []
        assert not list(s.scalars(select(Event).where(Event.type.like("handoff.%"))))


# --- duracion -------------------------------------------------------------------------------------

def test_slow_finalize_does_not_add_seconds(api, admin, client, monkeypatch):  # noqa: F811
    """Los segundos van hasta que corta el cliente: los avisos y la extraccion de finalize (90 s simulados) no suman."""
    import datetime

    from app.voice import direct

    from .voice_harness import Clock

    add_agent(admin, client)
    clock = Clock(monkeypatch, worker, direct)
    real_finish = api.engine.finish

    async def slow_finish(conversation_id):
        clock.skip(90)
        return await real_finish(conversation_id)

    monkeypatch.setattr(api.engine, "finish", slow_finish)
    cut = {}

    async def during(h):
        cut["at"] = direct.utcnow()
        h.ctx.room.leave(CUSTOMER)

    h = Harness(api, monkeypatch)
    asyncio.run(h.run({}, attributes=inbound_attributes(), during=during))
    call = h.call(inbound_id(api))
    assert call.status == CallStatus.finalizada and call.duration_seconds <= 1
    assert call.ended_at < cut["at"] + datetime.timedelta(seconds=30)


# --- Progreso de la derivacion en pantalla (tema handoff_status) ----------------------------------

class FakeData:
    """direct.DataSender sin LiveKit: guarda (tema, datos, destinatarios)."""
    sent: list = []

    def __init__(self, room):
        pass

    def send(self, topic, data, to=None):
        FakeData.sent.append((topic, data, to))


def progress_call(api, agent, client, monkeypatch, metadata: dict, mode: CallMode = CallMode.prueba,
                  attributes=None):
    FakeData.sent = []
    monkeypatch.setattr(worker.direct, "DataSender", FakeData)
    if attributes is None:
        metadata = {"conversation_id": seed_call(api, agent["id"], client["id"], mode), **metadata}
    h = Harness(api, monkeypatch, script={"+5493511111111": "no_answer", "+5493512222222": "confirm"},
                connected=[("dtmf", "PERSON", "2")])

    async def during(h):
        await h.session.agent.on_handoff("Ventas", False)
        await h.session.agent.on_handoff("Ventas", False)

    asyncio.run(h.run(metadata, attributes=attributes, during=during))
    return FakeData.sent


def test_progress_goes_to_the_customer_with_names_in_the_panel_test(api, agent, client, monkeypatch):
    sent = progress_call(api, agent, client, monkeypatch, {"handoff_progress": "names"})
    assert sent and {(topic, tuple(to)) for topic, _, to in sent} == {("handoff_status", (CUSTOMER,))}
    finals = [data for _, data, _ in sent if data["state"] != "running"]
    # Dos derivaciones en la misma llamada: cada una con su id y su final.
    assert [(d["id"], d["state"]) for d in finals] == [(1, "connected"), (2, "connected")]
    assert [leg["person"] for leg in finals[0]["legs"]] == ["Ana", "Juan"]


def test_progress_is_anonymous_in_the_link(api, agent, client, monkeypatch):
    sent = progress_call(api, agent, client, monkeypatch, {"call_link_id": "link", "handoff_progress": "anonymous"},
                         mode=CallMode.web)
    assert sent and all(leg["person"] is None for _, data, _ in sent for leg in data["legs"])


@pytest.mark.parametrize("metadata", [{}, {"from_landing": True}, {"handoff_progress": "otra"}])
def test_no_progress_without_the_flag(api, agent, client, monkeypatch, metadata):
    assert progress_call(api, agent, client, monkeypatch, metadata) == []


def test_no_progress_by_phone(api, agent, client, monkeypatch):
    assert progress_call(api, agent, client, monkeypatch, {}, attributes=inbound_attributes()) == []
