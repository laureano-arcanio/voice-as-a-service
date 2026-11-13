"""Derivacion por WhatsApp de texto (app/whatsapp/handoffs.py): pre-call, fin con `always`, rotacion, toque, entrega al
operador y reenvio. Con Graph, LLM y herramientas falsos.

tests/fixtures/wa_button_webhook.json NO es una captura real. El log de T0 (produccion, 4-nov-2026) no guardo el payload
completo: la estructura sigue el formato de Meta para type=button y tests/fixtures/wa/text.json. Lo unico medido es que
context.id del toque coincide exacto con el wamid devuelto al enviar la plantilla.
"""
import asyncio
import copy
import datetime
import json
from pathlib import Path

import pytest
from sqlalchemy import event, select, update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.conversation import workflows
from app.db import utcnow
from app.models import (
    Agent,
    ClientTool,
    ConversationRow,
    Event,
    HandoffArea,
    HandoffAreaMember,
    HandoffLeg,
    TeamMember,
    WaAccount,
    WaMessage,
    WaThread,
)
from app.services import agents as agent_service
from app.services import handoff as handoff_service
from app.services import quota
from app.tools.runtime import ToolResult
from app.whatsapp import campaigns, handoffs, store, team_notify
from app.whatsapp.graph import GraphError
from app.whatsapp.service import Inbox

from .helpers import FakeLLM
from .test_api import V1, admin, make_client  # noqa: F401  (fixture)
from .test_whatsapp_audio import FakeAudio
from .test_whatsapp_service import (
    FIXTURES,
    PNID,
    SEND_TO,
    WA_ID,
    FakeGraph,
    conversations,
    make_wa,
    reply,
    send,
    status_payload,
    text_payload,
)

ROTATION = {"name": "equipo_rotacion", "language": "es_AR", "params": ["area"]}
NOTICE = {"name": "equipo_aviso", "language": "es_AR", "params": ["area", "nombre", "cliente", "resumen", "ficha"]}
OPS = {"ana": "+5493515551111", "juan": "+5493515552222", "eva": "+5493515553333"}
TO = {"ana": "543515551111", "juan": "543515552222", "eva": "543515553333"}
FROM = {"ana": "5493515551111", "juan": "5493515552222", "eva": "5493515553333"}
PERSON_PHONE = f"+{WA_ID}"


def rejected() -> GraphError:
    return GraphError("rechazado", status=400, code=131047)


class Graph(FakeGraph):
    """Registra en orden plantillas y textos. fail_template: {destino: error}; reject_text(to, body): el error de un
    texto, o None; gate: frena las plantillas hasta abrirla, solo las de gate_to si esta puesto; text_gate: frena los
    textos a la persona hasta abrirla; op_gate: frena los textos a op_gate_to hasta abrirla."""

    def __init__(self):
        super().__init__()
        self.log: list[tuple] = []
        self.fail_template: dict = {}
        self.reject_text = lambda to, body: None
        self.gate: asyncio.Event | None = None
        self.gate_to: str | None = None
        self.entered = asyncio.Event()
        self.text_gate: asyncio.Event | None = None
        self.text_entered = asyncio.Event()
        self.op_gate: asyncio.Event | None = None
        self.op_gate_to: str | None = None
        self.op_entered = asyncio.Event()

    async def send_template(self, pnid, to, name, language, params=None):
        if self.gate and self.gate_to in (None, to):
            self.entered.set()
            await self.gate.wait()
        if to in self.fail_template:
            raise self.fail_template[to]
        self.log.append(("template", to, name, params))
        return {"messages": [{"id": f"wamid.tpl{sum(x[0] == 'template' for x in self.log)}"}]}

    async def send_text(self, pnid, to, body):
        if self.text_gate and to == SEND_TO:
            self.text_entered.set()
            await self.text_gate.wait()
        if self.op_gate and to == self.op_gate_to:
            self.op_entered.set()
            await self.op_gate.wait()
        if error := self.reject_text(to, body):
            raise error
        self.log.append(("text", to, body))
        self.sent.append((pnid, to, body))
        return {"messages": [{"id": f"wamid.txt{len(self.sent)}"}]}

    def texts(self, to: str) -> list[str]:
        return [x[2] for x in self.log if x[0] == "text" and x[1] == to]

    def templates(self) -> list[str]:
        return [x[1] for x in self.log if x[0] == "template"]


def make_area(w, name, members=(), *, delivery="call", template=ROTATION, wait=120, account=None, **columns) -> str:
    with w.sessions() as s:
        area = HandoffArea(client_id=w.client_id, name=name, delivery=delivery, **columns,
                           whatsapp={"account_id": account or w.account_id, "wait_seconds": wait,
                                     **({"template": template} if template else {})})
        s.add(area)
        s.flush()
        for i, key in enumerate(members):
            member = s.scalar(select(TeamMember).where(TeamMember.client_id == w.client_id, TeamMember.phone == OPS[key]))
            if member is None:
                member = TeamMember(client_id=w.client_id, name=key.capitalize(), phone=OPS[key], whatsapp_notify=True)
                s.add(member)
                s.flush()
            s.add(HandoffAreaMember(area_id=area.id, member_id=member.id, position=i))
        s.commit()
        return area.id


def tool_row(s, client_id, slug):
    s.add(ClientTool(client_id=client_id, slug=slug, type="http", definition={
        "description": "De un workflow.",
        "http": {"method": "POST", "url": "https://fichas.test/x",
                 "body": {"type": "object", "properties": {
                     "from": {"type": "string", "value": "{{call.phone}}"}}}}}))


def configure(w, areas=(), post_call=None, pre_call=False) -> None:
    """Version nueva del agente, con sus areas y sus workflows."""
    with w.sessions() as s:
        agent = s.get(Agent, w.agent_id)
        definition = {**agent.definition}
        flows = {}
        if post_call:
            tool_row(s, w.client_id, "registrar_cobro")
            flows["post_call"] = {"tool": "registrar_cobro", "when": post_call}
        if pre_call:
            tool_row(s, w.client_id, "buscar_ficha")
            flows["pre_call"] = {"tool": "buscar_ficha", "timeout_ms": 1000}
        s.flush()
        if flows:
            definition["workflows"] = flows
        if areas:
            definition["handoff"] = {"areas": [{"area_id": a, "when": "Emergencias"} for a in areas]}
        agent_service.update_definition(s, agent, definition, None)
        s.commit()


class Tools:
    """Reemplaza engine.tools.run_workflow: guion por clave y registro de lo que se llamo."""

    def __init__(self, w):
        self.calls: list[tuple[str, str | None]] = []
        self.post_call = ToolResult(ok=True, status=200, data={"charged": True, "operator_message": "Cobro registrado."})
        self.pre_call = ToolResult(ok=True, status=200, assigned={"nombre": "María Gómez", "ficha": "https://f/1"})
        self.gate: asyncio.Event | None = None
        w.engine.tools.run_workflow = self.run

    async def run(self, workflow, state, slug, actor, key, *, emit=True):
        self.calls.append((key, actor))
        if self.gate and key == "post_call":
            await self.gate.wait()
        result = self.post_call if key == "post_call" else self.pre_call
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def h(sessions, monkeypatch):
    """Cuenta con un area de dos personas y un agente que puede derivar."""
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.2)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(*[reply("Te paso con el equipo.", handoff="Guardia")] * 1))
    w.area_id = make_area(w, "Guardia", ["ana", "juan"])
    configure(w, [w.area_id])
    w.tools = Tools(w)
    return w


def tap_payload(wamid: str, op: str = "ana", tap_id: str = "wamid.tap1", pnid: str = PNID) -> dict:
    p = json.loads((Path(FIXTURES).parent / "wa_button_webhook.json").read_text())
    value = p["entry"][0]["changes"][0]["value"]
    value["metadata"]["phone_number_id"] = pnid
    value["contacts"][0]["wa_id"] = FROM[op]
    value["messages"][0].update({"id": tap_id, "from": FROM[op], "context": {"from": "15550000000", "id": wamid}})
    return p


def media_payload(kind: str, wamid: str, **extra) -> dict:
    p = text_payload("x", wamid)
    message = p["entry"][0]["changes"][0]["value"]["messages"][0]
    del message["text"]
    message.update(type=kind, **extra)
    return p


def thread_of(w, conversation_id=None) -> WaThread:
    with w.sessions() as s:
        q = select(WaThread).where(WaThread.wa_id == WA_ID).order_by(WaThread.created_at.desc())
        thread = s.get(WaThread, conversation_id) if conversation_id else s.scalars(q).first()
        s.expunge(thread)
        return thread


def legs(w) -> list[HandoffLeg]:
    with w.sessions() as s:
        rows = list(s.scalars(select(HandoffLeg).order_by(HandoffLeg.created_at)))
        for r in rows:
            s.expunge(r)
        return rows


def set_thread(w, **values) -> None:
    with w.sessions() as s:
        thread = s.scalars(select(WaThread).where(WaThread.wa_id == WA_ID).order_by(WaThread.created_at.desc())).first()
        for k, v in values.items():
            setattr(thread, k, v)
        s.commit()


def event_types(w) -> list[str]:
    with w.sessions() as s:
        return list(s.scalars(select(Event.type).order_by(Event.id)))


def events_of(w, type) -> list[dict]:
    with w.sessions() as s:
        return [e.data for e in s.scalars(select(Event).where(Event.type == type).order_by(Event.id))]


def post_call_row(w):
    with w.sessions() as s:
        return s.scalars(select(ConversationRow).order_by(ConversationRow.created_at.desc())).first()


async def derive(w, llm_text="Te paso con el equipo.") -> None:
    """Un mensaje de la persona con el que el modelo deriva."""
    w.llm.turns[:] = [reply(llm_text, handoff="Guardia")]
    await send(w, text_payload("me desmayé", f"wamid.in{len(event_types(w))}"))


async def expire(w) -> None:
    """Vence lo que espera el barrido."""
    set_thread(w, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await w.service.handoffs.sweep()
    await w.service.drain()


async def due(w) -> int:
    """Vence el deadline y barre, sin drain: expire se cuelga con un gate cerrado."""
    set_thread(w, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    return await w.service.handoffs.sweep()


async def until(check, timeout: float = 3.0) -> None:
    """Espera a que se cumpla, dejando correr las tareas."""
    async with asyncio.timeout(timeout):
        while not check():
            await asyncio.sleep(0.005)


async def cancel_tasks(w) -> None:
    """Lo que le pasa a las tareas si `app` muere: nadie llega a escribir el resultado."""
    for task in list(w.service._tasks):
        task.cancel()
    await w.service.drain()


async def accept(w, wamid="wamid.tpl1", op="ana", tap_id="wamid.tap1") -> None:
    await send(w, tap_payload(wamid, op, tap_id))


# --- Pre-call y fin de la conversacion -------------------------------------------------------------

async def test_pre_call_only_on_new_conversation_and_webhook_not_delayed(h):
    configure(h, [h.area_id], pre_call=True)
    h.tools.gate = None
    h.llm.turns[:] = [reply("Hola María"), reply("Sigo")]
    h.service.handle_payload(text_payload("hola", "wamid.1"))      # sincronico: agenda y vuelve
    assert h.tools.calls == []
    await h.service.drain()
    assert h.tools.calls == [("pre_call", f"wa:{WA_ID}")]
    state = h.engine.store.get(thread_of(h).conversation_id)
    assert state.progress.variables["nombre"] == "María Gómez"
    await send(h, text_payload("sigo", "wamid.2"))
    assert len(h.tools.calls) == 1


async def test_pre_call_failure_goes_on(h):
    configure(h, [h.area_id], pre_call=True)
    h.tools.pre_call = RuntimeError("caido")
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.1"))
    assert h.graph.texts(SEND_TO) == ["Hola"]


async def test_always_runs_on_session_end_close_and_expiry(h):
    configure(h, [h.area_id], post_call="always")
    # Vence por el barrido.
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.1"))
    set_thread(h, last_user_at=utcnow() - datetime.timedelta(days=3))
    assert await h.service.sweep() == 1
    await h.service.drain()
    assert post_call_row(h).post_call_status == "pending"
    await workflows.run_once(h.sessions, h.engine)
    assert post_call_row(h).post_call_status == "done"
    assert [c for c in h.tools.calls if c[0] == "post_call"] == [("post_call", f"wa:{WA_ID}")]
    # Vencida al llegar el siguiente mensaje: otra conversacion, y la anterior corre.
    h.llm.turns[:] = [reply("Hola"), reply("De nuevo")]
    await send(h, text_payload("hola", "wamid.2"))
    first = thread_of(h).conversation_id
    set_thread(h, last_user_at=utcnow() - datetime.timedelta(days=3))
    await send(h, text_payload("volví", "wamid.3"))
    with h.sessions() as s:
        assert s.get(ConversationRow, first).post_call_status == "pending"


async def test_always_is_armed_before_finish(h):
    """Si `app` se recrea durante engine.finish, queda armed y el loop lo toma al vencer."""
    configure(h, [h.area_id], post_call="always")
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.1"))
    with h.sessions() as s:
        thread = s.scalar(select(WaThread))
        h.service.close_thread(s, thread)
        s.commit()
    row = post_call_row(h)
    assert row.post_call_status == "armed" and row.post_call_next_at > utcnow()
    # Si `finish` no llega a terminar, el loop lo toma al vencer el margen.
    await workflows.run_once(h.sessions, h.engine, now=lambda: utcnow() + datetime.timedelta(seconds=61))
    assert post_call_row(h).post_call_status == "done"
    assert h.tools.calls == [("post_call", f"wa:{WA_ID}")]


async def test_always_runs_after_closing(h):
    configure(h, [h.area_id], post_call="always")
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.1"))
    conv = thread_of(h).conversation_id
    with h.sessions() as s:
        h.service.close_thread(s, s.get(WaThread, conv))
        s.commit()
    h.service.end(conv)
    await h.service.drain()
    assert post_call_row(h).post_call_status == "pending"
    await workflows.run_once(h.sessions, h.engine)
    assert post_call_row(h).post_call_status == "done"


async def test_close_endpoint_arms_always(api, admin, sessions):  # noqa: F811
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(reply("Hola")))
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id], post_call="always")
    await send(w, text_payload("hola", "wamid.1"))
    conv = thread_of(w).conversation_id
    assert admin.post(f"{V1}/whatsapp/threads/{conv}/close").status_code == 204
    assert post_call_row(w).post_call_status in ("armed", "pending")
    assert admin.post(f"{V1}/whatsapp/threads/{conv}/close").status_code == 204


async def test_handoff_accepted_without_acceptance_never_runs(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    set_thread(h, last_user_at=utcnow() - datetime.timedelta(days=3))
    await h.service.sweep()
    await h.service.drain()
    await workflows.run_once(h.sessions, h.engine)
    assert post_call_row(h).post_call_status is None
    assert h.tools.calls == []


# --- Rotacion ---------------------------------------------------------------------------------------

async def test_transfer_call_only_with_template_areas(sessions):
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(reply("Hola")))
    voice_only = make_area(w, "Voz", ["ana"], template=None)
    with w.sessions() as s:
        s.get(HandoffArea, voice_only).whatsapp = None
        s.commit()
    rotation = make_area(w, "Guardia", ["ana"])
    configure(w, [voice_only, rotation])
    await send(w, text_payload("hola", "wamid.1"))
    state = w.engine.store.get(conversations(sessions)[0].id)
    assert [a["name"] for a in state.progress.handoff_areas] == ["Guardia"]


async def test_agent_with_voice_areas_does_not_see_it(sessions):
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(reply("Hola")))
    voice_only = make_area(w, "Voz", ["ana"], template=None)
    with w.sessions() as s:
        s.get(HandoffArea, voice_only).whatsapp = None
        s.commit()
    configure(w, [voice_only])
    await send(w, text_payload("hola", "wamid.1"))
    assert w.engine.store.get(conversations(sessions)[0].id).progress.handoff_areas == []


async def test_campaign_reply_does_not_see_it(h, monkeypatch):
    target = campaigns.ReplyTarget(recipient_id="r", campaign_id="c", agent_id=None, opening="Plantilla")
    monkeypatch.setattr(campaigns, "reply_target", lambda *a: target)
    monkeypatch.setattr(campaigns, "mark_replied", lambda *a: None)
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.1"))
    assert h.engine.store.get(thread_of(h).conversation_id).progress.handoff_areas == []


async def test_first_template_after_reply_without_contact_data(h):
    await derive(h)
    assert [x[0] for x in h.graph.log] == ["text", "template"]
    assert h.graph.log[1] == ("template", TO["ana"], "equipo_rotacion", ["Guardia"])
    thread = thread_of(h)
    assert thread.handoff_status == "waiting" and thread.handoff_area_id == h.area_id
    [leg] = legs(h)
    assert (leg.wamid, leg.result, leg.billed_seconds) == ("wamid.tpl1", "whatsapp_sent", 0) and leg.ended_at
    assert thread.handoff_leg_id == leg.id
    assert thread.handoff_deadline > utcnow() + datetime.timedelta(seconds=100)


async def test_empty_model_text_sends_transfer_message(h):
    await derive(h, llm_text="")
    assert h.graph.texts(SEND_TO) == ["Te paso con Guardia, un momento por favor."]
    assert h.engine.store.get(thread_of(h).conversation_id).messages[-1].text.startswith("Te paso con Guardia")


async def test_retraction_gives_one_rotation(sessions, monkeypatch):
    gate = asyncio.Event()

    class Slow(FakeLLM):
        async def converse(self, workflow, state, user_message, on_message=None, tools=None):
            if not gate.is_set():
                gate.set()
                await asyncio.sleep(0.15)
            return await super().converse(workflow, state, user_message, on_message, tools)

    w = make_wa(sessions, graph=Graph(), llm=Slow(reply("Uno", handoff="Guardia"), reply("Dos", handoff="Guardia")))
    w.area_id = make_area(w, "Guardia", ["ana", "juan"])
    configure(w, [w.area_id])
    w.service.handle_payload(text_payload("hola", "wamid.1"))
    await gate.wait()
    await send(w, text_payload("hola otra vez", "wamid.2"))
    assert w.graph.templates() == [TO["ana"]]
    assert w.graph.texts(SEND_TO) == ["Dos"]


async def test_expiry_passes_to_next_and_records(h):
    await derive(h)
    await expire(h)
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    first, second = legs(h)
    assert first.result == "no_answer" and second.result == "whatsapp_sent"
    assert "handoff.no_answer" in event_types(h)
    assert events_of(h, "handoff.no_answer")[0]["channel"] == "whatsapp"


async def test_failed_status_of_template_advances(h):
    await derive(h)
    await send(h, status_payload("status_failed.json", "wamid.tpl1"))
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert legs(h)[0].result == "failed"


async def test_failed_status_of_old_template_does_not_advance(h):
    await derive(h)
    await expire(h)
    await send(h, status_payload("status_failed.json", "wamid.tpl1"))
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert thread_of(h).handoff_leg_id == legs(h)[1].id


async def test_sync_rejection_tries_next_person(h):
    h.graph.fail_template[TO["ana"]] = rejected()
    await derive(h)
    assert h.graph.templates() == [TO["juan"]]
    first, second = legs(h)
    assert first.result == "failed" and second.wamid == "wamid.tpl1"
    assert thread_of(h).handoff_status == "waiting"


async def test_two_advances_one_template_nobody_skipped(h):
    await derive(h)
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await asyncio.gather(h.service.handoffs.sweep(), h.service.handoffs.sweep())
    await h.service.drain()
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert len(legs(h)) == 2


async def test_tap_during_sending_wins(h):
    await derive(h)
    h.graph.gate = asyncio.Event()
    h.graph.entered.clear()
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    sweep = asyncio.ensure_future(h.service.handoffs.sweep())
    await sweep     # el barrido no espera el envio
    await h.graph.entered.wait()
    assert thread_of(h).handoff_status == "sending"
    await send_tap_with_open_gate(h)
    assert thread_of(h).handoff_status == "accepted"
    assert thread_of(h).handoff_status == "accepted"
    assert legs(h)[0].result == "connected"


async def send_tap_with_open_gate(w) -> None:
    """El toque entra con el envio de la siguiente plantilla frenado; la entrega termina antes de abrirla."""
    w.service.handle_payload(tap_payload("wamid.tpl1"))
    await until(lambda: thread_of(w).handoff_status == "accepted")
    w.graph.gate.set()
    await w.service.drain()


async def test_late_tap_while_waiting_for_next(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await accept(h)
    assert len([c for c in h.tools.calls if c[0] == "post_call"]) == 1
    assert thread_of(h).handoff_status == "accepted"
    assert any("recibió tu pedido" in t for t in h.graph.texts(SEND_TO))


async def test_late_tap_with_rotation_closed_within_limit_and_past_it(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await expire(h)
    assert thread_of(h).handoff_status == "closed"
    assert any("No pude comunicarte" in t for t in h.graph.texts(SEND_TO))
    await accept(h)
    assert thread_of(h).handoff_status == "accepted"
    assert len(h.tools.calls) == 1
    assert h.graph.texts(SEND_TO)[-1].endswith("Lo que escribas acá también le llega.")


async def test_late_tap_past_limit_is_rejected(h):
    await derive(h)
    await expire(h)
    await expire(h)
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await accept(h)
    assert thread_of(h).handoff_status == "closed"
    assert h.graph.texts(TO["ana"]) == ["Esta solicitud ya se cerró."]
    assert post_call_row(h).post_call_status is None


async def test_two_simultaneous_taps_one_accepted(h):
    await derive(h)
    await expire(h)
    h.service.handle_payload(tap_payload("wamid.tpl1", "ana", "wamid.tapA"))
    h.service.handle_payload(tap_payload("wamid.tpl2", "juan", "wamid.tapB"))
    await h.service.drain()
    assert thread_of(h).handoff_status == "accepted"
    assert [leg.result for leg in legs(h)].count("connected") == 1
    assert h.graph.texts(TO["juan"]) == ["Ya la tomó Ana."] or h.graph.texts(TO["ana"]) == ["Ya la tomó Juan."]


async def test_second_tap_of_owner_gets_contact_again(h):
    await derive(h)
    await accept(h)
    before = h.graph.texts(TO["ana"])
    await accept(h, tap_id="wamid.tap2")
    assert len(h.graph.texts(TO["ana"])) == len(before) + 1
    assert PERSON_PHONE in h.graph.texts(TO["ana"])[-1]
    assert [leg.result for leg in legs(h)].count("connected") == 1


async def test_tap_of_owner_during_delivery_waits(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.gate = asyncio.Event()
    await derive(h)
    first = asyncio.ensure_future(accept(h))
    while thread_of(h).handoff_status != "delivering" or not h.graph.texts(TO["ana"]):
        await asyncio.sleep(0.01)
    h.service.handle_payload(tap_payload("wamid.tpl1", "ana", "wamid.tap2"))
    await asyncio.sleep(0.02)
    assert "Estamos confirmando, te paso los datos en un momento." in h.graph.texts(TO["ana"])
    h.tools.gate.set()
    await first
    await h.service.drain()
    assert thread_of(h).handoff_status == "accepted"


async def test_restart_in_sending_resumes(h):
    await derive(h)
    set_thread(h, handoff_status="sending", handoff_leg_id=None)
    await expire(h)
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert thread_of(h).handoff_status == "waiting"


async def test_restart_in_delivering_resumes_from_ack(h):
    await derive(h)
    set_thread(h, handoff_status="delivering", handoff_delivery_tries=0, handoff_leg_id=legs(h)[0].id)
    with h.sessions() as s:
        s.get(HandoffLeg, legs(h)[0].id).answered_at = utcnow()
        s.commit()
    await expire(h)
    texts = h.graph.texts(TO["ana"])
    assert texts[0].startswith("Recibido.") and PERSON_PHONE in texts[1]
    assert thread_of(h).handoff_status == "accepted"


async def test_end_of_chain_says_no_answer_in_text(h):
    await derive(h)
    await expire(h)
    await expire(h)
    thread = thread_of(h)
    assert thread.handoff_status == "closed" and thread.handoff_closed_at is not None
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Guardia")
    assert h.engine.store.get(thread.conversation_id).messages[-1].text.endswith("te contactan más tarde.")


async def test_end_of_chain_says_no_answer_in_audio(sessions):
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(), audio=FakeAudio())
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    await derive(w)
    set_thread(w, handoff_voice_note=True)
    await expire(w)
    assert len(w.graph.audios) == 1
    assert thread_of(w).handoff_status == "closed"


async def test_end_of_chain_with_notice_says_notified(h):
    aviso = make_area(h, "Aviso final", ["eva"], delivery="whatsapp", template=NOTICE)
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).no_answer_area_id = aviso
        s.commit()
    await derive(h)
    await expire(h)
    await expire(h)
    assert h.graph.log[-2][0:3] == ("template", TO["eva"], "equipo_aviso")
    params = h.graph.log[-2][3]
    assert params[0] == "Aviso final" and params[2] == PERSON_PHONE
    assert h.graph.texts(SEND_TO)[-1] == "Ya le avisé a Aviso final. Te van a contactar."
    assert thread_of(h).handoff_status == "closed"
    # Un pase a un area de aviso no suma como pase: el pedido quedo sin atender.
    assert "handoff.rerouted" not in event_types(h)
    assert "handoff.notified" in event_types(h)


async def test_notice_failing_falls_back_to_no_answer(h):
    aviso = make_area(h, "Aviso final", ["eva"], delivery="whatsapp", template=NOTICE)
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).no_answer_area_id = aviso
        s.commit()
    h.graph.fail_template[TO["eva"]] = rejected()
    await derive(h)
    await expire(h)
    await expire(h)
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Aviso final")


async def test_direct_notice_area_does_not_rotate_or_run_post_call(sessions, monkeypatch):
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(reply("Listo", handoff="Consultas")))
    area = make_area(w, "Consultas", ["ana"], delivery="whatsapp", template=NOTICE)
    configure(w, [area], post_call="handoff_accepted")
    tools = Tools(w)
    await send(w, text_payload("una consulta", "wamid.1"))
    assert w.graph.templates() == [TO["ana"]]
    assert thread_of(w).handoff_status == "closed"
    assert tools.calls == []
    assert "handoff.requested" not in event_types(w)


async def test_area_without_template_is_skipped(h):
    no_template = make_area(h, "Sin plantilla", ["eva"], template=None)
    final = make_area(h, "Final", ["eva"])
    with h.sessions() as s:
        s.get(HandoffArea, no_template).no_answer_area_id = final
        s.get(HandoffArea, h.area_id).no_answer_area_id = no_template
        s.commit()
    await derive(h)
    await expire(h)
    await expire(h)
    assert h.graph.templates() == [TO["ana"], TO["juan"], TO["eva"]]
    assert thread_of(h).handoff_area_id == final


async def test_after_hours_goes_to_its_route(h):
    other = make_area(h, "Noche", ["eva"])
    closed = {"tz": "UTC", "week": {}, "closed": []}
    with h.sessions() as s:
        area = s.get(HandoffArea, h.area_id)
        area.schedule, area.after_hours_area_id = closed, other
        s.commit()
    await derive(h)
    assert h.graph.templates() == [TO["eva"]]
    assert thread_of(h).handoff_area_id == other


async def test_cycle_in_routes_is_cut(h):
    other = make_area(h, "Otra", [])
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).no_answer_area_id = other
        s.get(HandoffArea, other).no_answer_area_id = h.area_id
        s.commit()
    await derive(h)
    await expire(h)
    await expire(h)
    assert thread_of(h).handoff_status == "closed"


async def test_summary_in_params_is_calculated(h):
    class Summary(FakeLLM):
        async def structured(self, messages, schema, name, thinking=False, max_tokens=200):
            return json.dumps({"resumen": "Se desmayó"}), None

    llm = Summary(reply("Te paso", handoff="Guardia"))
    h.engine.llm = llm
    h.engine.llms.default = llm
    h.engine.llms.for_turn = lambda *a: llm
    with h.sessions() as s:
        area = s.get(HandoffArea, h.area_id)
        area.whatsapp = {**area.whatsapp, "template": {**ROTATION, "params": ["area", "resumen"]}}
        s.commit()
    h.llm = llm
    await derive(h)
    assert h.graph.log[-1][3] == ["Guardia", "Se desmayó"]


async def test_tap_from_other_number_has_no_effect(h):
    await derive(h)
    h.llm.turns[:] = [reply("Hola")]
    await send(h, tap_payload("wamid.tpl1", "juan"))
    assert thread_of(h).handoff_status == "waiting"
    assert h.graph.texts(TO["juan"]) != ["Recibido. Estamos confirmando, te paso los datos en un momento."]
    assert legs(h)[0].answered_at is None


async def test_tap_from_other_account_has_no_effect(h):
    await derive(h)
    with h.sessions() as s:
        s.add(WaAccount(client_id=h.client_id, agent_id=h.agent_id, phone_number_id="999", waba_id="1",
                        display_phone_number="+1", active=True))
        s.commit()
    h.llm.turns[:] = [reply("Hola")]
    await send(h, tap_payload("wamid.tpl1", "ana", pnid="999"))
    assert thread_of(h).handoff_status == "waiting" and legs(h)[0].answered_at is None


async def test_tap_from_other_client_has_no_effect(h, sessions):
    await derive(h)
    with h.sessions() as s:
        leg = s.scalar(select(HandoffLeg))
        from app.models import Client, Tier
        tier = Tier(name="O")
        s.add(tier)
        s.flush()
        other = Client(name="Otro", slug="otro", tier_id=tier.id)
        s.add(other)
        s.flush()
        leg.client_id = other.id
        s.commit()
    h.llm.turns[:] = [reply("Hola")]
    await accept(h)
    assert thread_of(h).handoff_status == "waiting"


async def test_tap_of_previous_rotation_is_rejected(h):
    await derive(h)
    await expire(h)
    await expire(h)
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    set_thread(h, handoff_started_at=utcnow() + datetime.timedelta(seconds=5))
    await accept(h)
    assert h.graph.texts(TO["ana"]) == ["Esta solicitud ya se cerró."]


async def test_campaign_button_unchanged(h):
    p = tap_payload("wamid.de-una-campana", "ana")
    h.llm.turns[:] = [reply("Te ayudo")]
    await send(h, p)
    assert h.graph.texts(TO["ana"]) == ["Te ayudo"]
    with h.sessions() as s:
        assert s.scalar(select(WaThread).where(WaThread.wa_id == FROM["ana"])) is not None


async def test_no_post_call_without_acceptance(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await expire(h)
    assert h.tools.calls == []


async def test_post_call_actor_is_the_person_with_other_account(h):
    with h.sessions() as s:
        other = store.create_account(s, client_id=h.client_id, agent_id=h.agent_id, phone_number_id="200",
                                     waba_id="100000000000001", display_phone_number="+1 555 000 0001")
        area = s.get(HandoffArea, h.area_id)
        area.whatsapp = {**area.whatsapp, "account_id": other.id}
        s.commit()
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await send(h, tap_payload("wamid.tpl1", "ana", pnid="200"))
    assert h.tools.calls == [("post_call", f"wa:{WA_ID}")]
    assert next(x for x in h.graph.sent if x[1] == TO["ana"])[0] == "200"
    assert h.graph.sent[-1][0] == PNID and h.graph.sent[-1][1] == SEND_TO
    assert thread_of(h).handoff_status == "accepted"


async def test_free_reply_and_audio_of_operator_are_fixed(sessions, monkeypatch):
    monkeypatch.setattr(settings, "wa_audio_reply", "never")
    audio = FakeAudio()
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(reply("Te paso", handoff="Guardia")), audio=audio)
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    await derive(w)
    calls = len(w.llm.calls)
    p = text_payload("ya voy", "wamid.op1")
    value = p["entry"][0]["changes"][0]["value"]
    value["messages"][0]["from"] = FROM["ana"]
    await send(w, p)
    a = copy.deepcopy(p)
    message = a["entry"][0]["changes"][0]["value"]["messages"][0]
    message.update(id="wamid.op2", type="audio", audio={"id": "m1"})
    del message["text"]
    await asyncio.sleep(0.06)
    await send(w, a)
    assert w.graph.texts(TO["ana"]) == [settings.wa_team_reply] * 2
    assert len(w.llm.calls) == calls and audio.heard == []
    with w.sessions() as s:
        assert s.scalar(select(WaThread).where(WaThread.wa_id == FROM["ana"])) is None


async def test_operator_after_window_goes_to_agent(h):
    await derive(h)
    with h.sessions() as s:
        for msg in s.scalars(select(WaMessage).where(WaMessage.type == "team_notice")):
            msg.created_at = utcnow() - datetime.timedelta(hours=25)
        s.commit()
    p = text_payload("hola", "wamid.op1")
    p["entry"][0]["changes"][0]["value"]["messages"][0]["from"] = FROM["ana"]
    h.llm.turns[:] = [reply("Te ayudo")]
    await send(h, p)
    assert h.graph.texts(TO["ana"]) == ["Te ayudo"]


async def test_pending_writers_keeps_the_lock(h):
    """Un escritor esperando el lock: el turno que lo suelta no borra el inbox, o el siguiente tomaria otro lock."""
    key = (PNID, WA_ID)
    inbox = h.service._inbox.setdefault(key, Inbox())
    order = []

    async def writer():
        async with h.service.contact_lock(PNID, WA_ID):
            order.append("writer")
            assert h.service._inbox[key] is inbox

    await inbox.lock.acquire()
    task = asyncio.ensure_future(writer())
    await asyncio.sleep(0)
    assert inbox.pending_writers == 1
    inbox.lock.release()
    assert not inbox.idle(asyncio.get_running_loop().time(), 0)     # locked() ya es False, y el escritor sigue
    await task
    assert order == ["writer"] and key not in h.service._inbox


async def test_text_leg_does_not_use_channels_or_minutes(h):
    await derive(h)
    await accept(h)
    now = utcnow()
    with h.sessions() as s:
        assert quota.busy_channels(s, now) == 0
        assert quota.handoff_seconds(s, h.client_id, now - datetime.timedelta(days=1),
                                     now + datetime.timedelta(days=1), now) == 0


# --- Entrega ----------------------------------------------------------------------------------------

async def test_delivery_order_contact_only_after_post_call(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    seen = []
    real = h.tools.run

    async def run(workflow, state, slug, actor, key, *, emit=True):
        seen.append(list(h.graph.texts(TO["ana"])))
        return await real(workflow, state, slug, actor, key, emit=emit)

    h.engine.tools.run_workflow = run
    await derive(h)
    assert PERSON_PHONE not in str(h.graph.log[1])
    await accept(h)
    assert len(seen) == 1 and len(seen[0]) == 1
    assert seen[0][0].startswith("Recibido.") and PERSON_PHONE not in seen[0][0]
    _, contact = h.graph.texts(TO["ana"])
    assert contact.startswith("Cobro registrado.\n\nContacto:") and PERSON_PHONE in contact
    assert h.graph.texts(SEND_TO)[-1].endswith("también le llega.")
    thread = thread_of(h)
    assert thread.handoff_status == "accepted"
    assert thread.handoff_deadline > utcnow() + datetime.timedelta(hours=23)
    [leg] = legs(h)
    assert leg.result == "connected" and leg.connected_at and leg.answered_at
    types = event_types(h)
    assert "handoff.confirmed" in types and "handoff.connected" in types
    with h.sessions() as s:
        assert s.get(HandoffArea, h.area_id).last_member_id == leg.team_member_id


async def test_ack_rejected_no_post_call_nothing_to_person_advances(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    before = h.graph.texts(SEND_TO)
    h.graph.reject_text = lambda to, body: rejected() if to == TO["ana"] else None
    await accept(h)
    assert h.tools.calls == []
    assert h.graph.texts(SEND_TO) == before
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert thread_of(h).handoff_status == "waiting"
    assert legs(h)[0].result == "failed"


async def test_ack_rejected_on_late_tap_back_to_closed(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await expire(h)
    closed = thread_of(h)
    before = h.graph.texts(SEND_TO)
    h.graph.reject_text = lambda to, body: rejected() if to == TO["ana"] else None
    await accept(h)
    thread = thread_of(h)
    assert thread.handoff_status == "closed"
    assert thread.handoff_closed_at == closed.handoff_closed_at
    assert thread.handoff_deadline == closed.handoff_deadline
    assert h.graph.texts(SEND_TO) == before and h.tools.calls == []


async def test_post_call_failing_delivers_and_loop_retries(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.post_call = ToolResult(ok=False, error="timeout", transport=True)
    await derive(h)
    await accept(h)
    assert h.graph.texts(TO["ana"])[1].startswith("No se pudo confirmar el registro.")
    assert PERSON_PHONE in h.graph.texts(TO["ana"])[1]
    row = post_call_row(h)
    assert row.post_call_status == "pending" and row.post_call_attempts == 1
    assert thread_of(h).handoff_status == "accepted"
    h.tools.post_call = ToolResult(ok=True, status=200, data={})
    await workflows.run_once(h.sessions, h.engine, now=lambda: utcnow() + datetime.timedelta(minutes=1))
    assert post_call_row(h).post_call_status == "done"


async def test_post_call_slow_delivers_then_finishes_on_its_own(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.gate = asyncio.Event()
    await derive(h)
    h.service.handle_payload(tap_payload("wamid.tpl1"))
    while thread_of(h).handoff_status != "accepted":
        await asyncio.sleep(0.02)
    assert h.graph.texts(TO["ana"])[1].startswith("No se pudo confirmar")
    assert post_call_row(h).post_call_status == "running"
    h.tools.gate.set()
    await h.service.drain()
    assert post_call_row(h).post_call_status == "done"
    assert post_call_row(h).post_call_note == "Cobro registrado."


async def test_no_charge_delivers_with_operator_message(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.post_call = ToolResult(ok=True, status=200, data={"charged": False, "operator_message": "Sin ficha, no se cobró."})
    await derive(h)
    await accept(h)
    assert h.graph.texts(TO["ana"])[1].startswith("Sin ficha, no se cobró.\n\nContacto:")


async def test_no_post_call_agent_delivers_without_note(h):
    await derive(h)
    await accept(h)
    assert h.graph.texts(TO["ana"])[1].startswith("Contacto: Contacto Prueba, " + PERSON_PHONE)


async def test_llm_down_delivers_with_fallback_summary(h):
    await derive(h)
    await accept(h)     # FakeLLM no tiene structured: falla como un LLM caido
    assert handoff_service.FALLBACK_SUMMARY in h.graph.texts(TO["ana"])[1]


async def test_contact_rejected_retries_without_ack_then_fails(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    h.graph.reject_text = lambda to, body: rejected() if to == TO["ana"] and "Contacto" in body else None
    await accept(h)
    thread = thread_of(h)
    assert (thread.handoff_status, thread.handoff_delivery_tries) == ("delivering", 1)
    assert len(h.graph.texts(TO["ana"])) == 1
    await expire(h)
    assert thread_of(h).handoff_delivery_tries == 2
    assert len(h.graph.texts(TO["ana"])) == 1          # no repite (a)
    await expire(h)
    assert legs(h)[0].result == "failed"
    assert thread_of(h).handoff_status == "waiting"
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    # Otra aceptacion no repite el post-call.
    h.graph.reject_text = lambda to, body: None
    await accept(h, "wamid.tpl2", "juan", "wamid.tap2")
    assert len(h.tools.calls) == 1
    assert h.graph.texts(TO["juan"])[1].startswith("Cobro registrado.")


def team_texts(w) -> list[str]:
    """Los wamid de los textos al equipo, en orden: acuse y contacto."""
    with w.sessions() as s:
        return list(s.scalars(select(WaMessage.wamid).where(WaMessage.type == "team_notice",
                                                            WaMessage.wamid.like("wamid.txt%"))
                              .order_by(WaMessage.created_at)))


async def test_async_failed_of_contact_is_delivery_failure(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await accept(h)
    await send(h, status_payload("status_failed.json", team_texts(h)[1]))
    assert thread_of(h).handoff_status == "waiting"
    assert legs(h)[0].result == "failed" and h.graph.templates() == [TO["ana"], TO["juan"]]
    assert len(h.tools.calls) == 1


async def test_async_failed_of_ack_during_delivery_is_delivery_failure(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.gate = asyncio.Event()
    await derive(h)
    h.service.handle_payload(tap_payload("wamid.tpl1"))
    await until(lambda: len(team_texts(h)) == 1)
    h.service.handle_payload(status_payload("status_failed.json", team_texts(h)[0]))
    await until(lambda: thread_of(h).handoff_status == "waiting")
    h.tools.gate.set()
    await h.service.drain()
    assert legs(h)[0].result == "failed" and h.graph.templates() == [TO["ana"], TO["juan"]]
    assert thread_of(h).handoff_status == "waiting"


async def test_async_failed_of_ack_after_a_contact_that_went_out_changes_nothing(h):
    """El operador tiene los datos: el contacto salio despues del acuse que fallo."""
    await derive(h)
    await accept(h)
    await send(h, status_payload("status_failed.json", team_texts(h)[0]))
    assert thread_of(h).handoff_status == "accepted"
    assert legs(h)[0].result == "connected" and h.graph.templates() == [TO["ana"]]
    assert "handoff.whatsapp_failed" not in event_types(h)


@pytest.mark.parametrize("later", ["contact_failed", "other_number", "other_conversation"])
async def test_async_failed_of_ack_when_the_later_send_does_not_count(h, later):
    """Lo posterior tiene que ser un envio que no fallo, a ese numero y de esta conversacion."""
    await derive(h)
    await accept(h)
    ack, contact = team_texts(h)
    with h.sessions() as s:
        row = s.scalar(select(WaMessage).where(WaMessage.wamid == contact))
        if later == "contact_failed":
            row.status = "failed"
        elif later == "other_number":
            row.wa_id = FROM["juan"]
        else:
            row.conversation_id = None
        s.commit()
    await send(h, status_payload("status_failed.json", ack))
    assert thread_of(h).handoff_status == "waiting"
    assert legs(h)[0].result == "failed"


async def test_late_failed_does_not_reopen_an_emergency_closed_by_hand(h):
    conv = await accepted(h)
    contact = team_texts(h)[1]
    with h.sessions() as s:
        handoffs.stop_relay(s, conv)
        s.commit()
    await send(h, status_payload("status_failed.json", contact))
    thread = thread_of(h, conv)
    assert thread.handoff_status == "accepted" and thread.handoff_deadline <= utcnow()
    assert legs(h)[0].result == "connected" and h.graph.templates() == [TO["ana"]]
    assert "handoff.whatsapp_failed" not in event_types(h)


async def test_async_failed_does_not_touch_other_thread_of_the_operator(h):
    await accepted(h)
    first = thread_of(h).conversation_id
    second_id = "5493510000001"
    p = text_payload("me caí", "wamid.b1")
    value = p["entry"][0]["changes"][0]["value"]
    value["messages"][0]["from"] = second_id
    value["contacts"] = [{"profile": {"name": "Luis"}, "wa_id": second_id}]
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(h, p)
    await send(h, tap_payload("wamid.tpl2", "ana", "wamid.tapB"))
    with h.sessions() as s:
        second = s.scalar(select(WaThread.conversation_id).where(WaThread.wa_id == second_id))
        wamid = s.scalar(select(WaMessage.wamid).where(WaMessage.type == "team_notice",
                                                       WaMessage.conversation_id == first,
                                                       WaMessage.wamid.like("wamid.txt%"))
                         .order_by(WaMessage.created_at.desc()).limit(1))
    await send(h, status_payload("status_failed.json", wamid))
    assert thread_of(h, first).handoff_status == "waiting"
    assert thread_of(h, second).handoff_status == "accepted"


async def test_async_failed_of_another_number_in_the_conversation_is_ignored(h):
    """Un aviso a otra persona de la misma conversacion no es la entrega de quien la tomo."""
    conv = await accepted(h)
    with h.sessions() as s:
        s.add(WaMessage(wamid="wamid.oth", account_id=h.account_id, direction="out", wa_id=FROM["juan"],
                        type="team_notice", status="sent", conversation_id=conv))
        s.commit()
    await send(h, status_payload("status_failed.json", "wamid.oth"))
    assert thread_of(h).handoff_status == "accepted"
    assert legs(h)[0].result == "connected"


async def test_post_call_running_is_waited_not_repeated(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    conv = thread_of(h).conversation_id
    with h.sessions() as s:
        row = s.get(ConversationRow, conv)
        row.post_call_status, row.post_call_attempts = "running", 1
        row.post_call_next_at = utcnow() + datetime.timedelta(minutes=3)
        s.commit()

    async def finish():
        await asyncio.sleep(0.05)
        with h.sessions() as s:
            row = s.get(ConversationRow, conv)
            row.post_call_status, row.post_call_note = "done", "Nota del otro."
            s.commit()

    await asyncio.gather(finish(), accept(h))
    assert h.tools.calls == []
    assert h.graph.texts(TO["ana"])[1].startswith("Nota del otro.")


async def test_post_call_running_past_wait_delivers_failed(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    with h.sessions() as s:
        row = s.get(ConversationRow, thread_of(h).conversation_id)
        row.post_call_status, row.post_call_attempts = "running", 1
        row.post_call_next_at = utcnow() + datetime.timedelta(minutes=3)
        s.commit()
    await accept(h)
    assert h.tools.calls == []
    assert h.graph.texts(TO["ana"])[1].startswith("No se pudo confirmar")


async def test_pending_waiting_retry_is_not_advanced(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    next_at = utcnow() + datetime.timedelta(minutes=10)
    with h.sessions() as s:
        row = s.get(ConversationRow, thread_of(h).conversation_id)
        row.post_call_status, row.post_call_attempts, row.post_call_next_at = "pending", 2, next_at
        s.commit()
    await accept(h)
    assert h.tools.calls == []
    row = post_call_row(h)
    assert row.post_call_next_at == next_at and row.post_call_status == "pending"
    assert h.graph.texts(TO["ana"])[1].startswith("No se pudo confirmar")


@pytest.mark.parametrize("message", ["No está al día: se cobró igual.", "No se cobró: sin ficha."])
async def test_note_survives_repeats_and_second_acceptance(h, message):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.post_call = ToolResult(ok=True, status=200, data={"operator_message": message})
    await derive(h)
    h.graph.reject_text = lambda to, body: rejected() if to == TO["ana"] and "Contacto" in body else None
    attempts = []
    real_reject = h.graph.reject_text

    def reject(to, body):
        if "Contacto" in body:
            attempts.append(body)
        return real_reject(to, body)

    h.graph.reject_text = reject
    await accept(h)                 # primer (c), rechazado
    await expire(h)                 # el barrido lo repite
    assert len(attempts) == 2 and all(a.startswith(message) for a in attempts)
    # `app` recreada: tries=0, repite desde (a) y no corre otro post-call.
    set_thread(h, handoff_delivery_tries=0)
    h.graph.reject_text = lambda to, body: None
    await expire(h)
    assert h.graph.texts(TO["ana"])[-1].startswith(message)
    assert len(h.tools.calls) == 1
    # Segunda aceptacion en la misma conversacion.
    set_thread(h, handoff_status="waiting", handoff_leg_id=None)
    await expire(h)
    with h.sessions() as s:
        assert s.get(ConversationRow, thread_of(h).conversation_id).post_call_status == "done"
    await accept(h, "wamid.tpl2", "juan", "wamid.tap2")
    assert h.graph.texts(TO["juan"])[-1].startswith(message)
    assert len(h.tools.calls) == 1


async def test_final_text_fits_with_max_note_and_phone(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.post_call = ToolResult(ok=True, status=200, data={"operator_message": "n" * 5000})
    with h.sessions() as s:
        area = s.get(HandoffArea, h.area_id)
        area.messages = {"operator_contact": "Contacto: {{cliente}}. " + "x" * 470}
        s.commit()
    await derive(h)
    await accept(h)
    text = h.graph.texts(TO["ana"])[1]
    assert len(text) <= settings.wa_max_reply_chars
    assert text.startswith("n" * 1000) and PERSON_PHONE in text


async def test_final_text_cuts_the_note_not_the_phone(h, monkeypatch):
    monkeypatch.setattr(settings, "wa_max_reply_chars", 300)
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.post_call = ToolResult(ok=True, status=200, data={"operator_message": "n" * 900})
    await derive(h)
    await accept(h)
    text = h.graph.texts(TO["ana"])[1]
    assert len(text) <= 300 and PERSON_PHONE in text


async def test_area_deleted_during_delivering_is_delivery_failure(h):
    await derive(h)
    set_thread(h, handoff_status="delivering", handoff_area_id=None, handoff_leg_id=legs(h)[0].id,
               handoff_delivery_tries=0)
    await expire(h)
    # Sin area no hay por donde seguir: fin de cadena, sin romper.
    assert thread_of(h).handoff_status == "closed"
    assert legs(h)[0].result == "failed"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte")


# --- Reenvio ----------------------------------------------------------------------------------------

async def accepted(w) -> str:
    await derive(w)
    await accept(w)
    assert thread_of(w).handoff_status == "accepted"
    return thread_of(w).conversation_id


async def test_relay_text_and_transcribed_audio_reach_operator_without_llm(sessions, monkeypatch):
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(), audio=FakeAudio("me duele el pecho"))
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    conv = await accepted(w)
    calls = len(w.llm.calls)
    await send(w, text_payload("sigo mal", "wamid.r1"))
    await send(w, media_payload("audio", "wamid.r2", audio={"id": "m1", "mime_type": "audio/ogg"}))
    texts = w.graph.texts(TO["ana"])
    assert texts[-2] == f"*Contacto Prueba · {PERSON_PHONE}*\nsigo mal"
    assert texts[-1] == f"*Contacto Prueba · {PERSON_PHONE}*\n[audio] me duele el pecho"
    assert len(w.llm.calls) == calls
    state = w.engine.store.get(conv)
    assert [(m.role, m.text) for m in state.messages[-2:]] == [("user", "sigo mal"), ("user", "me duele el pecho")]
    with sessions() as s:
        assert s.scalar(select(WaMessage.status).where(WaMessage.wamid == "wamid.r1")) == "answered"
        assert s.scalar(select(WaMessage.type).where(WaMessage.wa_id == FROM["ana"]).order_by(WaMessage.created_at.desc()).limit(1)) == "team_relay"
    assert "wamid.r1" in w.graph.read


async def test_what_waited_on_the_timer_is_relayed(h):
    await derive(h)
    h.service.handle_payload(text_payload("estoy solo", "wamid.r1"))
    await asyncio.sleep(0)
    await send(h, tap_payload("wamid.tpl1"))
    assert any(t.endswith("estoy solo") for t in h.graph.texts(TO["ana"]))


async def test_image_and_failed_audio_arrive_as_notice(sessions, monkeypatch):
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    from app.whatsapp.audio import AudioError
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(), audio=FakeAudio(AudioError("mal")))
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    await accepted(w)
    before = len(w.graph.texts(SEND_TO))
    await send(w, media_payload("image", "wamid.r1", image={"id": "i1"}))
    await send(w, media_payload("audio", "wamid.r2", audio={"id": "m1", "mime_type": "audio/ogg"}))
    texts = w.graph.texts(TO["ana"])
    assert texts[-2].endswith("[La persona envió: imagen]")
    assert texts[-1].endswith("[Audio que no se pudo transcribir]")
    assert len(w.graph.texts(SEND_TO)) == before     # sin la respuesta fija


async def test_two_emergencies_have_distinct_prefixes(h):
    await accepted(h)
    second_id = "5493510000001"
    p = text_payload("me caí", "wamid.b1")
    value = p["entry"][0]["changes"][0]["value"]
    value["messages"][0]["from"] = second_id
    value["contacts"] = [{"profile": {"name": "Luis"}, "wa_id": second_id}]
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(h, p)
    await send(h, tap_payload("wamid.tpl2", "ana", "wamid.tapB"))
    await send(h, text_payload("uno", "wamid.r1"))
    q = copy.deepcopy(p)
    q["entry"][0]["changes"][0]["value"]["messages"][0].update(id="wamid.r2", text={"body": "dos"})
    await send(h, q)
    texts = h.graph.texts(TO["ana"])
    assert texts[-2] == f"*Contacto Prueba · {PERSON_PHONE}*\nuno"
    assert texts[-1] == f"*Luis · +{second_id}*\ndos"


async def test_thread_closed_by_sweep_keeps_relaying(h):
    conv = await accepted(h)
    set_thread(h, last_user_at=utcnow() - datetime.timedelta(days=3))
    assert await h.service.sweep() == 1
    await h.service.drain()
    assert thread_of(h, conv).closed_at is not None
    await send(h, text_payload("sigo", "wamid.r1"))
    assert h.graph.texts(TO["ana"])[-1].endswith("sigo")
    assert len(conversations(h.sessions)) == 1


async def test_after_24h_goes_to_ai(h):
    await accepted(h)
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    h.llm.turns[:] = [reply("Te sigo yo")]
    await send(h, text_payload("hola", "wamid.r1"))
    assert h.graph.texts(SEND_TO)[-1] == "Te sigo yo"


async def test_close_endpoint_cuts_relay_also_with_closed_thread(api, admin, sessions, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM())
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    conv = await accepted(w)
    assert admin.post(f"{V1}/whatsapp/threads/{conv}/close").status_code == 204
    assert thread_of(w).handoff_deadline <= utcnow() and thread_of(w).closed_at is not None
    # Otra vez, con el hilo ya cerrado.
    set_thread(w, handoff_deadline=utcnow() + datetime.timedelta(hours=5))
    assert admin.post(f"{V1}/whatsapp/threads/{conv}/close").status_code == 204
    assert thread_of(w).handoff_deadline <= utcnow()


@pytest.mark.parametrize("status", ["sending", "waiting", "delivering"])
async def test_close_endpoint_leaves_rotation_alone(api, admin, sessions, status):  # noqa: F811
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM())
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    await derive(w)
    deadline = utcnow() + datetime.timedelta(minutes=1)
    set_thread(w, handoff_status=status, handoff_deadline=deadline)
    assert admin.post(f"{V1}/whatsapp/threads/{thread_of(w).conversation_id}/close").status_code == 204
    thread = thread_of(w)
    assert (thread.handoff_status, thread.handoff_deadline) == (status, deadline)


async def test_relay_sync_rejection_ends_it(h):
    conv = await accepted(h)
    h.graph.reject_text = lambda to, body: rejected() if to == TO["ana"] else None
    await send(h, text_payload("hola", "wamid.r1"))
    assert h.graph.texts(SEND_TO)[-1] == "No pude hacerle llegar tu mensaje a Ana. Escribime de nuevo si necesitás avisarle a otra persona."
    assert "handoff.relay_failed" in event_types(h)
    state = h.engine.store.get(conv)
    assert any(m.role == "user" and m.text == "hola" for m in state.messages)
    h.graph.reject_text = lambda to, body: None
    h.llm.turns[:] = [reply("Sigo yo")]
    await send(h, text_payload("otra", "wamid.r2"))
    assert h.graph.texts(SEND_TO)[-1] == "Sigo yo"


async def test_relay_failed_status_ends_it(h):
    await accepted(h)
    await send(h, text_payload("hola", "wamid.r1"))
    with h.sessions() as s:
        wamid = s.scalar(select(WaMessage.wamid).where(WaMessage.type == "team_relay"))
    await send(h, status_payload("status_failed.json", wamid))
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude hacerle llegar")
    h.llm.turns[:] = [reply("Sigo yo")]
    await send(h, text_payload("otra", "wamid.r2"))
    assert h.graph.texts(SEND_TO)[-1] == "Sigo yo"


async def test_transfer_call_in_flight_with_emergency_taken_is_ignored(h):
    await accepted(h)
    conv = thread_of(h).conversation_id
    state = h.engine.store.get(conv)
    from app.conversation.models import AgentTurn
    area = h.service.handoffs.transfer_area(state, AgentTurn(assistant_message="x", handoff="Guardia"))
    assert area["id"] == h.area_id
    assert h.service.handoffs.reserve(conv, area, False) == handoffs.Booking(None, h.area_id)
    assert thread_of(h).handoff_status == "accepted"
    assert events_of(h, "handoff.ignored")[-1]["live_status"] == "accepted"


async def test_other_account_same_wa_id_is_not_relayed(h):
    await accepted(h)
    with h.sessions() as s:
        store.create_account(s, client_id=h.client_id, agent_id=h.agent_id, phone_number_id="300",
                             waba_id="100000000000001", display_phone_number="+1 555 000 0002")
        s.commit()
    h.llm.turns[:] = [reply("Soy el otro número")]
    before = len(h.graph.texts(TO["ana"]))
    await send(h, text_payload("hola", "wamid.o1", pnid="300"))
    assert len(h.graph.texts(TO["ana"])) == before
    assert h.graph.sent[-1][0] == "300" and h.graph.sent[-1][2] == "Soy el otro número"


async def test_area_deleted_with_relay_active_is_relay_failed(h):
    conv = await accepted(h)
    set_thread(h, handoff_area_id=None)
    await send(h, text_payload("hola", "wamid.r1"))
    assert "handoff.relay_failed" in event_types(h)
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude hacerle llegar tu mensaje a Ana")
    assert thread_of(h, conv).handoff_deadline <= utcnow()
    h.llm.turns[:] = [reply("Sigo yo")]
    await send(h, text_payload("otra", "wamid.r2"))
    assert h.graph.texts(SEND_TO)[-1] == "Sigo yo"


async def test_member_deleted_uses_default_name(h):
    await accepted(h)
    with h.sessions() as s:
        s.get(HandoffLeg, thread_of(h).handoff_leg_id).team_member_id = None
        s.commit()
    set_thread(h, handoff_area_id=None)
    await send(h, text_payload("hola", "wamid.r1"))
    assert "la persona que tomó tu pedido" in h.graph.texts(SEND_TO)[-1]


async def test_optout_word_with_relay_and_closed_thread_reaches_operator(h, monkeypatch):
    await accepted(h)
    set_thread(h, closed_at=utcnow())
    monkeypatch.setattr(campaigns, "got_campaign", lambda *a: True)
    added = []
    monkeypatch.setattr(campaigns, "add_optout", lambda *a: added.append(a))
    await send(h, text_payload("basta", "wamid.r1"))
    assert added == []
    assert h.graph.texts(TO["ana"])[-1].endswith("basta")


async def test_end_of_relay_with_open_thread_runs_with_consecutive_user_messages(h):
    conv = await accepted(h)
    await send(h, text_payload("uno", "wamid.r1"))
    await send(h, text_payload("dos", "wamid.r2"))
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    h.llm.turns[:] = [reply("Sigo yo")]
    await send(h, text_payload("tres", "wamid.r3"))
    assert h.graph.texts(SEND_TO)[-1] == "Sigo yo"
    roles = [m.role for m in h.engine.store.get(conv).messages]
    assert roles[-4:] == ["user", "user", "user", "assistant"]


# --- Reserva antes de responder ---------------------------------------------------------------------

SECOND_ID = "5493510000001"


def single(sessions, llm=None, audio=None):
    """Area de un solo operador."""
    w = make_wa(sessions, graph=Graph(), llm=llm or FakeLLM(), audio=audio)
    w.area_id = make_area(w, "Guardia", ["ana"])
    configure(w, [w.area_id])
    w.tools = Tools(w)
    return w


def from_second(body: str, wamid: str) -> dict:
    p = text_payload(body, wamid)
    value = p["entry"][0]["changes"][0]["value"]
    value["messages"][0]["from"] = SECOND_ID
    value["contacts"] = [{"profile": {"name": "Luis"}, "wa_id": SECOND_ID}]
    return p


def inbound_status(w, wamid: str) -> str:
    with w.sessions() as s:
        return s.scalar(select(WaMessage.status).where(WaMessage.wamid == wamid))


def close_hilo(w) -> str:
    """Cierra el hilo como lo cerraria el panel. La conversacion cerrada."""
    conv = thread_of(w).conversation_id
    with w.sessions() as s:
        w.service.close_thread(s, s.get(WaThread, conv))
        s.commit()
    return conv


async def frozen_reply(w, text="Te paso con el equipo."):
    """Un turno que deriva con la respuesta a la persona frenada en Meta."""
    w.graph.text_gate = asyncio.Event()
    w.llm.turns[:] = [reply(text, handoff="Guardia")]
    w.service.handle_payload(text_payload("me desmayé", "wamid.in1"))
    await w.graph.text_entered.wait()


async def test_reservation_is_written_before_the_reply(h):
    await frozen_reply(h)
    thread = thread_of(h)
    assert thread.handoff_status == "sending" and thread.handoff_deadline > utcnow()
    assert thread.handoff_area_id == h.area_id and thread.handoff_retakes == 0
    assert h.graph.templates() == []
    assert await h.service.handoffs.sweep() == 0        # vigente: el barrido no la toca
    assert h.graph.templates() == []
    h.graph.text_gate.set()
    await h.service.drain()
    assert [x[0] for x in h.graph.log] == ["text", "template"]
    assert thread_of(h).handoff_status == "waiting"


async def test_reply_task_cancelled_template_goes_out_after_lease(h):
    await frozen_reply(h)
    await cancel_tasks(h)
    assert thread_of(h).handoff_status == "sending" and h.graph.templates() == []
    h.graph.text_gate.set()
    await expire(h)
    assert h.graph.templates() == [TO["ana"]]
    assert thread_of(h).handoff_status == "waiting"


async def test_send_that_raises_template_goes_out_after_lease(h):
    real = h.graph.send_text

    async def boom(pnid, to, body):
        if to == SEND_TO:
            raise RuntimeError("red")
        return await real(pnid, to, body)

    h.graph.send_text = boom
    await derive(h)
    assert thread_of(h).handoff_status == "sending" and h.graph.templates() == []
    h.graph.send_text = real
    await expire(h)
    assert h.graph.templates() == [TO["ana"]]


async def test_lease_expired_during_reply_gives_one_template(h):
    await frozen_reply(h)
    assert await due(h) == 1
    await until(lambda: h.graph.templates() == [TO["ana"]])
    assert thread_of(h).handoff_status == "waiting"
    h.graph.text_gate.set()
    await h.service.drain()
    assert h.graph.templates() == [TO["ana"]]       # start ve otro lease y no avanza
    assert thread_of(h).handoff_status == "waiting" and len(legs(h)) == 1


async def test_advance_with_old_lease_does_nothing(h):
    """Ni siquiera lee la cadena: antes de perder el lease al renovarlo podria calcular un resumen con el LLM."""
    await frozen_reply(h)
    real, read = h.service.handoffs._load_step, []
    h.service.handoffs._load_step = lambda *a: read.append(a) or real(*a)
    await h.service.handoffs._advance(thread_of(h).conversation_id, utcnow())
    assert read == [] and h.graph.templates() == [] and legs(h) == []
    h.graph.text_gate.set()
    await h.service.drain()
    assert len(read) == 1 and h.graph.templates() == [TO["ana"]]


async def test_reservation_starts_retakes_at_zero(h):
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.first"))
    set_thread(h, handoff_retakes=3)
    await frozen_reply(h)
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("sending", 0)
    h.graph.text_gate.set()
    await h.service.drain()


async def test_retraction_reserves_once(sessions):
    gate = asyncio.Event()

    class Slow(FakeLLM):
        async def converse(self, workflow, state, user_message, on_message=None, tools=None):
            if not gate.is_set():
                gate.set()
                await asyncio.sleep(0.15)
            return await super().converse(workflow, state, user_message, on_message, tools)

    w = make_wa(sessions, graph=Graph(), llm=Slow(reply("Uno", handoff="Guardia"), reply("Dos", handoff="Guardia")))
    w.area_id = make_area(w, "Guardia", ["ana", "juan"])
    configure(w, [w.area_id])
    calls = []
    real = w.service.handoffs.reserve
    w.service.handoffs.reserve = lambda *a: calls.append(a) or real(*a)
    w.service.handle_payload(text_payload("hola", "wamid.1"))
    await gate.wait()
    await send(w, text_payload("hola otra vez", "wamid.2"))
    assert len(calls) == 1 and "handoff.ignored" not in event_types(w)
    assert w.graph.templates() == [TO["ana"]]


# --- Si el segundo turno falla tras retractar uno que derivaba ----------------------------------------

class FailsSecond(FakeLLM):
    """El primer turno tarda, para que llegue otro mensaje; el segundo falla como un LLM caido."""

    def __init__(self, *turns):
        super().__init__(*turns)
        self.first = asyncio.Event()

    async def converse(self, workflow, state, user_message, on_message=None, tools=None):
        if not self.first.is_set():
            self.first.set()
            await asyncio.sleep(0.15)
            return await super().converse(workflow, state, user_message, on_message, tools)
        raise RuntimeError("LLM caido")


async def test_second_turn_fails_after_retraction_with_handoff_uses_it(sessions):
    llm = FailsSecond(reply("Te paso con Guardia", handoff="Guardia"))
    w = single(sessions, llm=llm)
    w.service.handle_payload(text_payload("me desmayo", "wamid.1"))
    await llm.first.wait()
    await send(w, text_payload("ayuda", "wamid.2"))
    assert w.graph.texts(SEND_TO) == ["Te paso con Guardia"]
    assert w.graph.templates() == [TO["ana"]] and thread_of(w).handoff_status == "waiting"
    assert inbound_status(w, "wamid.1") == inbound_status(w, "wamid.2") == "answered"
    messages = w.engine.store.get(thread_of(w).conversation_id).messages
    assert [(m.role, m.text) for m in messages] == [("user", "me desmayo\nayuda"), ("assistant", "Te paso con Guardia")]


async def test_second_turn_fails_without_handoff_is_error_as_always(sessions):
    llm = FailsSecond(reply("Hola"))
    w = single(sessions, llm=llm)
    w.service.handle_payload(text_payload("hola", "wamid.1"))
    await llm.first.wait()
    await send(w, text_payload("che", "wamid.2"))
    assert w.graph.texts(SEND_TO) == [] and w.graph.templates() == []
    assert inbound_status(w, "wamid.1") == inbound_status(w, "wamid.2") == "error"
    assert thread_of(w).handoff_status is None


# --- Envio interrumpido -------------------------------------------------------------------------------

async def interrupted_send(w) -> None:
    """La persona recibe la respuesta y la tarea muere con la plantilla en camino."""
    w.graph.gate = asyncio.Event()
    w.graph.entered.clear()
    await_derive = asyncio.ensure_future(derive(w))
    await w.graph.entered.wait()
    await cancel_tasks(w)
    await await_derive
    w.graph.gate = None


async def test_single_member_interrupted_is_retried_and_tap_accepts(sessions, monkeypatch):
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = single(sessions)
    await interrupted_send(w)
    [leg] = legs(w)
    assert leg.result == "whatsapp_sent" and leg.wamid is None
    await expire(w)
    assert w.graph.templates() == [TO["ana"]]
    thread = thread_of(w)
    assert thread.handoff_status == "waiting"
    first, second = legs(w)
    assert (first.result, first.wamid) == ("interrupted", None)
    assert (second.result, second.wamid) == ("whatsapp_sent", "wamid.tpl1") and thread.handoff_leg_id == second.id
    assert not any("No pude" in t for t in w.graph.texts(SEND_TO))
    assert event_types(w).count("handoff.requested") == 1
    await accept(w)
    assert thread_of(w).handoff_status == "accepted"
    assert PERSON_PHONE in w.graph.texts(TO["ana"])[-1]


async def test_interrupted_first_member_is_not_skipped(h):
    await interrupted_send(h)
    await expire(h)
    assert h.graph.templates() == [TO["ana"]]
    assert [leg.team_member_id for leg in legs(h)].count(legs(h)[0].team_member_id) == 2


async def test_rejected_member_is_not_retried_with_interrupted_one(h):
    h.graph.fail_template[TO["ana"]] = rejected()
    h.graph.gate_to = TO["juan"]
    await interrupted_send(h)
    h.graph.gate_to = None
    await expire(h)
    assert h.graph.templates() == [TO["juan"]]
    assert [leg.result for leg in legs(h)] == ["failed", "interrupted", "whatsapp_sent"]


async def test_tap_of_unregistered_template_is_a_common_button(sessions, monkeypatch):
    """Meta acepto la plantilla y `app` murio antes de guardar el wamid: ese toque no se reconoce. El operador acepta con
    la plantilla de la retoma."""
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = single(sessions)
    await interrupted_send(w)
    await expire(w)
    calls = len(w.llm.calls)
    await accept(w, "wamid.lo-que-meta-acepto", tap_id="wamid.tapviejo")
    assert thread_of(w).handoff_status == "waiting"
    assert all(leg.answered_at is None for leg in legs(w))
    assert not any(PERSON_PHONE in t for t in w.graph.texts(TO["ana"]))
    assert len(w.llm.calls) == calls
    await accept(w, tap_id="wamid.tapnuevo")
    assert thread_of(w).handoff_status == "accepted"
    assert PERSON_PHONE in w.graph.texts(TO["ana"])[-1]


async def test_late_wamid_leaves_the_leg_sent_and_tappable(h):
    """El envio estaba vivo cuando el barrido lo dio por interrumpido: su wamid vale."""
    h.graph.gate = asyncio.Event()
    derived = asyncio.ensure_future(derive(h))
    await h.graph.entered.wait()
    await due(h)
    await until(lambda: len(legs(h)) == 2)
    assert legs(h)[0].result == "interrupted"
    h.graph.gate.set()
    await derived
    await h.service.drain()
    assert [(leg.result, bool(leg.wamid)) for leg in legs(h)] == [("whatsapp_sent", True)] * 2
    assert thread_of(h).handoff_status == "waiting"
    other = next(leg for leg in legs(h) if leg.id != thread_of(h).handoff_leg_id)
    await accept(h, other.wamid)
    assert thread_of(h).handoff_status == "accepted" and thread_of(h).handoff_leg_id == other.id


async def test_delivering_retake_interrupts_only_this_rotation(h):
    await derive(h)
    thread = thread_of(h)
    before = thread.handoff_started_at - datetime.timedelta(seconds=5)
    with h.sessions() as s:
        member = legs(h)[0].team_member_id
        s.add_all([HandoffLeg(id="en-vuelo", client_id=h.client_id, conversation_id=thread.conversation_id,
                              area_id=h.area_id, team_member_id=member, phone=OPS["juan"], result="whatsapp_sent",
                              ended_at=utcnow(), billed_seconds=0),
                   HandoffLeg(id="anterior", client_id=h.client_id, conversation_id=thread.conversation_id,
                              area_id=h.area_id, team_member_id=member, phone=OPS["juan"], result="whatsapp_sent",
                              created_at=before, ended_at=before, billed_seconds=0)])
        s.get(HandoffLeg, legs(h)[0].id).answered_at = utcnow()
        s.commit()
    set_thread(h, handoff_status="delivering", handoff_leg_id=thread.handoff_leg_id)
    await expire(h)
    results = {leg.id: leg.result for leg in legs(h)}
    assert results["en-vuelo"] == "interrupted" and results["anterior"] == "whatsapp_sent"
    assert results[thread.handoff_leg_id] == "connected"


# --- Barrido sin esperar y tope de retomas ------------------------------------------------------------

async def test_stuck_resume_does_not_delay_another_conversation(sessions):
    w = single(sessions)
    await derive(w)
    w.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(w, from_second("me caí", "wamid.b1"))
    other_to = "543510000001"
    inbox = w.service._inbox.setdefault((PNID, WA_ID), Inbox())
    await inbox.lock.acquire()      # un turno de la primera persona en curso: su _tell espera
    with w.sessions() as s:
        for thread in s.scalars(select(WaThread)):
            thread.handoff_deadline = utcnow() - datetime.timedelta(seconds=1)
        s.commit()
    async with asyncio.timeout(1):
        assert await w.service.handoffs.sweep() == 2
    await until(lambda: any("No pude" in t for t in w.graph.texts(other_to)))
    assert not any("No pude" in t for t in w.graph.texts(SEND_TO))
    inbox.lock.release()
    await w.service.drain()
    assert any("No pude" in t for t in w.graph.texts(SEND_TO))


async def test_two_sweeps_retake_once(h):
    await derive(h)
    h.graph.gate = asyncio.Event()
    h.graph.entered.clear()
    set_thread(h, handoff_status="sending", handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await asyncio.gather(h.service.handoffs.sweep(), h.service.handoffs.sweep())
    await h.graph.entered.wait()
    assert await h.service.handoffs.sweep() == 0
    h.graph.gate.set()
    await h.service.drain()
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert thread_of(h).handoff_status == "waiting" and thread_of(h).handoff_retakes == 0


async def test_retakes_exhausted_in_sending_closes_and_frees_the_contact(h):
    real = h.service.handoffs._advance

    async def boom(*a):
        raise RuntimeError("fila trabada")

    h.service.handoffs._advance = boom
    await derive(h)
    conv = thread_of(h).conversation_id
    for n in range(1, handoffs.MAX_RETAKES):
        await expire(h)
        assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("sending", n)
        assert not any("No pude" in t for t in h.graph.texts(SEND_TO))
    await expire(h)
    thread = thread_of(h)
    assert (thread.handoff_status, thread.handoff_retakes) == ("closed", 0)
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Guardia")
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "retakes_exhausted"
    # Una derivacion nueva del contacto reserva, tambien desde otra conversacion.
    h.service.handoffs._advance = real
    close_hilo(h)
    await derive(h)
    assert thread_of(h).conversation_id != conv and h.graph.templates() == [TO["ana"]]
    assert "handoff.ignored" not in event_types(h)


async def test_retakes_exhausted_in_delivering_is_delivery_failure(h):
    real = h.service.handoffs._deliver

    async def boom(*a):
        raise RuntimeError("fila trabada")

    await derive(h)
    h.service.handoffs._deliver = boom
    await accept(h)
    for n in range(1, handoffs.MAX_RETAKES):
        await expire(h)
        assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("delivering", n)
    h.service.handoffs._deliver = real
    await expire(h)
    assert legs(h)[0].result == "failed"
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "retakes_exhausted"
    assert h.graph.templates() == [TO["ana"], TO["juan"]]
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("waiting", 0)


async def test_expired_waiting_does_not_count_as_retake(h):
    await derive(h)
    h.graph.gate = asyncio.Event()
    h.graph.entered.clear()
    await due(h)
    await h.graph.entered.wait()
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("sending", 0)
    h.graph.gate.set()
    await h.service.drain()


async def test_retakes_go_back_to_zero_when_it_works(h):
    await derive(h)
    set_thread(h, handoff_status="sending", handoff_retakes=handoffs.MAX_RETAKES - 2)
    await expire(h)
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("waiting", 0)
    set_thread(h, handoff_retakes=handoffs.MAX_RETAKES - 2)
    await accept(h, "wamid.tpl2", "juan")
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("accepted", 0)


# --- Area borrada ---------------------------------------------------------------------------------------

def delete_area(w) -> None:
    with w.sessions() as s:
        s.delete(s.get(HandoffArea, w.area_id))
        s.commit()


async def test_area_deleted_before_the_turn(h):
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.first"))
    delete_area(h)
    h.llm.turns[:] = [reply("", handoff="Guardia")]
    await send(h, text_payload("me desmayé", "wamid.second"))
    texts = h.graph.texts(SEND_TO)
    assert texts[1] == "Te paso con el equipo, un momento por favor."
    assert inbound_status(h, "wamid.second") == "answered"
    thread = thread_of(h)
    assert thread.handoff_area_id is None and thread.handoff_status == "closed"
    assert texts[-1].startswith("No pude comunicarte con el equipo en este momento.")
    assert h.graph.templates() == []


async def test_area_of_other_client_is_not_used(h):
    """Un id en la conversacion que no es del cliente se trata como borrado."""
    from app.models import Client, Tier
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.first"))
    with h.sessions() as s:
        tier = Tier(name="O")
        s.add(tier)
        s.flush()
        other = Client(name="Otro", slug="otro", tier_id=tier.id)
        s.add(other)
        s.flush()
        s.get(HandoffArea, h.area_id).client_id = other.id
        s.commit()
    h.llm.turns[:] = [reply("", handoff="Guardia")]
    await send(h, text_payload("me desmayé", "wamid.1"))
    assert thread_of(h).handoff_area_id is None and h.graph.templates() == []
    assert h.graph.texts(SEND_TO)[1] == "Te paso con el equipo, un momento por favor."


def fail_area_write_once(w) -> list:
    """IntegrityError donde reserve escribe de verdad: en el UPDATE de su hilo con el area, como la foreign key de
    PostgreSQL si se borra el area entre la lectura y el UPDATE. SQLite no la aplica."""
    raised = []

    def check(conn, cursor, statement, parameters, context, executemany):
        if (not raised and statement.startswith("UPDATE wa_threads") and "handoff_area_id" in statement
                and w.area_id in parameters):
            raised.append(statement)
            raise IntegrityError(statement, parameters, Exception("foreign key"))

    event.listen(w.sessions.kw["bind"], "before_cursor_execute", check)
    return raised


async def test_integrity_error_retries_the_whole_transaction_without_area(h):
    await derive(h)
    await expire(h)
    await expire(h)
    old = thread_of(h).conversation_id
    assert thread_of(h).handoff_status == "closed" and thread_of(h).handoff_deadline > utcnow()
    close_hilo(h)
    raised = fail_area_write_once(h)
    h.llm.turns[:] = [reply("", handoff="Guardia")]
    await send(h, text_payload("me desmayé", "wamid.again"))
    assert raised, "la falla forzada no se disparo"
    assert h.graph.texts(SEND_TO)[-2] == "Te paso con el equipo, un momento por favor."
    assert inbound_status(h, "wamid.again") == "answered"
    thread = thread_of(h)
    assert thread.conversation_id != old and thread.handoff_area_id is None and thread.handoff_status == "closed"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con el equipo")
    # El reintento rehizo tambien el vencimiento del `closed` de la otra conversacion.
    assert thread_of(h, old).handoff_deadline <= utcnow()


@pytest.mark.parametrize("text", ["Te paso", ""], ids=["con_texto", "sin_texto"])
async def test_reserve_that_cannot_write_still_answers(h, text, monkeypatch):
    def boom(*a):
        raise RuntimeError("base caida")

    monkeypatch.setattr(h.service.handoffs, "_book", boom)
    h.llm.turns[:] = [reply(text, handoff="Guardia")]
    await send(h, text_payload("me desmayé", "wamid.1"))
    assert h.graph.texts(SEND_TO) == [text or "Te paso con Guardia, un momento por favor."]
    assert inbound_status(h, "wamid.1") == "answered"
    assert thread_of(h).handoff_status is None and h.graph.templates() == []


async def test_transfer_text_without_database_still_answers(h, monkeypatch):
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.1"))

    def boom(*a):
        raise RuntimeError("base caida")

    monkeypatch.setattr(h.service.handoffs, "_thread", boom)
    assert h.service.handoffs.transfer_text("x", h.area_id) == "Te paso con el equipo, un momento por favor."


# --- Tope del envio de la plantilla ---------------------------------------------------------------------

async def test_hung_graph_passes_to_the_next_person(h, monkeypatch):
    monkeypatch.setattr(team_notify, "SEND_DEADLINE", 0.05)
    h.graph.gate = asyncio.Event()      # nunca se abre: Meta colgado
    h.graph.gate_to = TO["ana"]
    async with asyncio.timeout(2):
        await derive(h)
    assert h.graph.templates() == [TO["juan"]]
    assert legs(h)[0].result == "failed" and thread_of(h).handoff_status == "waiting"
    assert events_of(h, "handoff.whatsapp_failed")[0]["reason"] == "internal"


def test_send_deadline_is_below_the_lease():
    """Si no, un paso vencido no significa que el envio murio."""
    assert team_notify.SEND_DEADLINE < handoffs.SENDING_LEASE.total_seconds()


# --- Una rotacion viva por contacto -----------------------------------------------------------------------

def second_area(w) -> str:
    """Otra area con rotacion, para que el modelo derive a otra con una viva."""
    other = make_area(w, "Consultas", ["eva"])
    configure(w, [w.area_id, other])
    return other


async def derive_to(w, name: str, text="", wamid="wamid.x") -> None:
    w.llm.turns[:] = [reply(text, handoff=name)]
    await send(w, text_payload("otra cosa", wamid))


async def test_same_conversation_other_area_without_text_names_the_live_one(h):
    second_area(h)
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(h, text_payload("me desmayé", "wamid.1"))
    conv = thread_of(h).conversation_id
    await derive_to(h, "Consultas")
    assert h.graph.texts(SEND_TO)[-1] == "Te paso con Guardia, un momento por favor."
    assert h.graph.templates() == [TO["ana"]] and thread_of(h).handoff_status == "waiting"
    assert thread_of(h).conversation_id == conv and thread_of(h).handoff_area_id == h.area_id
    [ignored] = events_of(h, "handoff.ignored")
    assert ignored == {"channel": "whatsapp", "area": "Consultas", "live_area": "Guardia", "live_status": "waiting",
                       "other_conversation": None}
    assert inbound_status(h, "wamid.x") == "answered"


async def test_model_text_is_not_touched_when_ignored(h):
    second_area(h)
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(h, text_payload("me desmayé", "wamid.1"))
    await derive_to(h, "Consultas", text="Te paso con Consultas")
    assert h.graph.texts(SEND_TO)[-1] == "Te paso con Consultas"
    assert len(events_of(h, "handoff.ignored")) == 1


async def test_other_conversation_live_is_named_and_not_doubled(h):
    second_area(h)
    await derive(h)
    conv = close_hilo(h)
    await derive_to(h, "Consultas")
    new = thread_of(h)
    assert new.conversation_id != conv and new.handoff_status is None
    assert h.graph.texts(SEND_TO)[-1] == "Te paso con Guardia, un momento por favor."
    assert h.graph.templates() == [TO["ana"]]
    [ignored] = events_of(h, "handoff.ignored")
    assert ignored["other_conversation"] == conv and ignored["live_area"] == "Guardia"


def by_hand(w):
    close_hilo(w)


def by_expiry(w):
    set_thread(w, last_user_at=utcnow() - datetime.timedelta(days=3))


def by_turns(w):
    w.service.max_turns = 1


@pytest.mark.parametrize("cut", [by_hand, by_expiry, by_turns], ids=["cerrar", "vencimiento", "tope_de_turnos"])
async def test_new_conversation_during_rotation_is_one_rotation(h, cut):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    conv = thread_of(h).conversation_id
    cut(h)
    before = len(h.graph.texts(SEND_TO))
    await derive_to(h, "Guardia")
    assert thread_of(h).conversation_id != conv
    assert len(h.graph.texts(SEND_TO)) == before + 1      # la persona recibe texto
    assert h.graph.templates() == [TO["ana"]]
    await accept(h)
    assert thread_of(h, conv).handoff_status == "accepted"
    assert [leg.result for leg in legs(h)] == ["connected"]
    assert [c for c in h.tools.calls if c[0] == "post_call"] == [("post_call", f"wa:{WA_ID}")]


async def test_new_rotation_cuts_the_late_tap_of_a_closed_one(h):
    await derive(h)
    await expire(h)
    await expire(h)
    old = thread_of(h).conversation_id
    assert thread_of(h).handoff_status == "closed"
    close_hilo(h)
    await derive_to(h, "Guardia", text="Te paso")
    new = thread_of(h)
    assert new.conversation_id != old and new.handoff_status == "waiting"
    assert h.graph.templates() == [TO["ana"], TO["juan"], TO["ana"]]
    await accept(h, "wamid.tpl1", tap_id="wamid.tapold")
    assert h.graph.texts(TO["ana"])[-1] == "Esta solicitud ya se cerró."
    assert thread_of(h, old).handoff_status == "closed"
    assert thread_of(h).handoff_status == "waiting"
    await accept(h, "wamid.tpl3", tap_id="wamid.tapnew")
    assert thread_of(h).handoff_status == "accepted"


async def test_ignored_derivation_does_not_cut_the_late_tap_of_a_closed_one(h):
    """Si no gana, la transaccion entera se deshace: el toque tardio de otra conversacion sigue valiendo."""
    await derive(h)
    closed = close_hilo(h)
    h.llm.turns[:] = [reply("Hola")]
    await send(h, text_payload("hola", "wamid.c2"))
    live = thread_of(h).conversation_id
    deadline = utcnow() + datetime.timedelta(minutes=10)
    with h.sessions() as s:
        row = s.get(WaThread, closed)
        row.handoff_status, row.handoff_deadline, row.handoff_closed_at = "closed", deadline, utcnow()
        other = s.get(WaThread, live)
        other.handoff_status, other.handoff_deadline, other.handoff_area_id = (
            "waiting", utcnow() + datetime.timedelta(minutes=1), h.area_id)
        s.commit()
    await derive_to(h, "Guardia")
    assert thread_of(h, closed).handoff_deadline == deadline
    assert thread_of(h, live).handoff_status == "waiting"
    assert len(events_of(h, "handoff.ignored")) == 1


async def test_finished_rotation_or_accepted_closed_by_hand_can_derive_again(h):
    await accepted(h)
    set_thread(h, handoff_deadline=utcnow())        # cerrada a mano
    await derive_to(h, "Guardia", text="De nuevo")
    assert h.graph.templates() == [TO["ana"], TO["ana"]]
    assert thread_of(h).handoff_status == "waiting" and thread_of(h).handoff_started_at is not None
    await expire(h)
    await expire(h)
    assert thread_of(h).handoff_status == "closed"
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await derive_to(h, "Guardia", text="Otra vez", wamid="wamid.y")
    assert thread_of(h).handoff_status == "waiting"
    assert "handoff.ignored" not in event_types(h)


async def test_other_account_same_wa_id_is_independent(h):
    await derive(h)
    with h.sessions() as s:
        store.create_account(s, client_id=h.client_id, agent_id=h.agent_id, phone_number_id="300",
                             waba_id="100000000000001", display_phone_number="+1 555 000 0002")
        s.commit()
    first = thread_of(h).conversation_id
    deadline = thread_of(h).handoff_deadline
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(h, text_payload("hola", "wamid.o1", pnid="300"))
    assert h.graph.templates() == [TO["ana"], TO["ana"]]
    assert "handoff.ignored" not in event_types(h)
    assert (thread_of(h, first).handoff_status, thread_of(h, first).handoff_deadline) == ("waiting", deadline)
    assert thread_of(h).conversation_id != first and thread_of(h).handoff_status == "waiting"


async def test_other_contact_of_the_account_is_independent(h):
    await derive(h)
    h.llm.turns[:] = [reply("Te paso", handoff="Guardia")]
    await send(h, from_second("me caí", "wamid.b1"))
    assert h.graph.templates() == [TO["ana"], TO["ana"]]
    assert "handoff.ignored" not in event_types(h)


# --- Fixture -------------------------------------------------------------------------------------

async def test_button_fixture_enters_the_acceptance_path(h):
    """La estructura del fixture no es captura real (ver el encabezado): solo context.id esta medido."""
    await derive(h)
    p = json.loads((Path(FIXTURES).parent / "wa_button_webhook.json").read_text())
    message = p["entry"][0]["changes"][0]["value"]["messages"][0]
    assert message["type"] == "button" and message["from"] == FROM["ana"]
    with h.sessions() as s:
        s.scalar(select(HandoffLeg)).wamid = message["context"]["id"]
        s.commit()
    await send(h, p)
    assert thread_of(h).handoff_status == "accepted"
    assert h.graph.texts(TO["ana"])[0].startswith("Recibido.")


# --- Aviso con Meta lento ---------------------------------------------------------------------------------

@pytest.fixture
def notice(sessions, monkeypatch):
    """Un area de aviso de dos personas."""
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM(reply("Listo", handoff="Consultas")))
    w.area_id = make_area(w, "Consultas", ["ana", "juan"], delivery="whatsapp", template=NOTICE)
    configure(w, [w.area_id])
    w.tools = Tools(w)
    return w


async def test_slow_notice_with_a_sweep_in_the_middle_reaches_one_person(notice):
    w = notice
    w.graph.fail_template[TO["ana"]] = rejected()
    w.graph.gate, w.graph.gate_to = asyncio.Event(), TO["ana"]
    w.service.handle_payload(text_payload("hola", "wamid.n1"))
    await asyncio.wait_for(w.graph.entered.wait(), 3)
    await due(w)
    await until(lambda: thread_of(w).handoff_retakes == 1)
    await asyncio.sleep(0.01)      # la retoma tambien queda frenada en la primera persona
    w.graph.gate.set()
    await w.service.drain()
    assert w.graph.templates() == [TO["juan"]]
    assert thread_of(w).handoff_status == "closed"
    assert [t for t in w.graph.texts(SEND_TO) if t.startswith("Ya le avisé")] == ["Ya le avisé a Consultas. Te van a contactar."]
    assert event_types(w).count("handoff.notified") == 1


async def test_rejected_notice_uses_the_renewed_lease(notice):
    """Cada persona renueva el lease: el fin de la cadena tiene que usar el ultimo."""
    w = notice
    w.graph.fail_template[TO["ana"]] = rejected()
    await send(w, text_payload("hola", "wamid.n1"))
    assert w.graph.templates() == [TO["juan"]]
    assert thread_of(w).handoff_status == "closed"
    assert w.graph.texts(SEND_TO)[-1] == "Ya le avisé a Consultas. Te van a contactar."


async def test_notify_area_that_lost_the_step_sends_nothing_and_records_no_failure(notice):
    w = notice
    result = await team_notify.notify_area(w.sessions, w.client_id, w.area_id, {}, None,
                                           graph_factory=w.service._graph, before_send=lambda: False)
    assert not result.ok and result.error is None
    assert w.graph.templates() == [] and "handoff.whatsapp_failed" not in event_types(w)


# --- Falla de una entrega: tramo desplazado y toque perdido ------------------------------------------------

def reject_for(w, op) -> None:
    w.graph.reject_text = lambda to, body: rejected() if to == TO[op] else None


def leg_of(w, op) -> HandoffLeg:
    return next(leg for leg in legs(w) if leg.phone == OPS[op])


async def test_failed_late_tap_goes_back_to_the_displaced_leg(h):
    await derive(h)
    await expire(h)
    juan = leg_of(h, "juan")
    reject_for(h, "ana")
    before = h.graph.texts(SEND_TO)
    set_thread(h, handoff_retakes=3)
    await accept(h)
    thread = thread_of(h)
    assert thread.handoff_status == "waiting" and thread.handoff_leg_id == juan.id
    assert thread.handoff_deadline == juan.created_at + datetime.timedelta(seconds=120)
    assert thread.handoff_retakes == 0
    assert h.graph.texts(SEND_TO) == before
    assert leg_of(h, "ana").result == "failed" and h.graph.templates() == [TO["ana"], TO["juan"]]
    await accept(h, "wamid.tpl2", "juan", "wamid.tap2")
    assert thread_of(h).handoff_status == "accepted"
    assert leg_of(h, "juan").result == "connected" and PERSON_PHONE in h.graph.texts(TO["juan"])[1]


async def test_displaced_leg_keeps_its_own_area(h):
    other = make_area(h, "Apoyo", ["juan"], wait=300)
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).no_answer_area_id = other
        s.delete(s.scalar(select(HandoffAreaMember).where(HandoffAreaMember.area_id == h.area_id,
                                                          HandoffAreaMember.position == 1)))
        s.commit()
    await derive(h)
    await expire(h)
    juan = leg_of(h, "juan")
    reject_for(h, "ana")
    await accept(h)
    thread = thread_of(h)
    assert (thread.handoff_status, thread.handoff_area_id) == ("waiting", other)
    assert thread.handoff_deadline == juan.created_at + datetime.timedelta(seconds=300)


async def test_failed_late_tap_with_displaced_leg_past_its_time_closes_it_and_advances(h):
    await derive(h)
    await expire(h)
    with h.sessions() as s:
        s.get(HandoffLeg, leg_of(h, "juan").id).created_at = utcnow() - datetime.timedelta(seconds=121)
        s.commit()
    set_thread(h, handoff_started_at=utcnow() - datetime.timedelta(seconds=300))
    reject_for(h, "ana")
    await accept(h)
    assert leg_of(h, "juan").result == "no_answer"
    assert "handoff.no_answer" in event_types(h)
    assert thread_of(h).handoff_status == "closed"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Guardia")


async def test_displaced_leg_past_its_time_advances_from_its_area(h):
    other = make_area(h, "Apoyo", ["juan", "eva"])
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).no_answer_area_id = other
        s.delete(s.scalar(select(HandoffAreaMember).where(HandoffAreaMember.area_id == h.area_id,
                                                          HandoffAreaMember.position == 1)))
        s.commit()
    await derive(h)
    await expire(h)
    with h.sessions() as s:
        s.get(HandoffLeg, leg_of(h, "juan").id).created_at = utcnow() - datetime.timedelta(seconds=121)
        s.commit()
    set_thread(h, handoff_started_at=utcnow() - datetime.timedelta(seconds=300))
    reject_for(h, "ana")
    await accept(h)
    assert h.graph.templates() == [TO["ana"], TO["juan"], TO["eva"]]
    assert thread_of(h).handoff_area_id == other
    assert event_types(h).count("handoff.rerouted") == 1


async def test_displaced_leg_without_area_advances(h):
    await derive(h)
    await expire(h)
    with h.sessions() as s:
        s.get(HandoffLeg, leg_of(h, "juan").id).area_id = None
        s.commit()
    reject_for(h, "ana")
    await accept(h)
    assert leg_of(h, "juan").result == "no_answer"
    assert thread_of(h).handoff_status == "closed"


async def test_rotation_already_closed_does_not_wait_for_a_displaced_leg(h):
    await derive(h)
    await expire(h)
    await expire(h)
    closed = thread_of(h)
    with h.sessions() as s:
        s.get(HandoffLeg, leg_of(h, "juan").id).result = "whatsapp_sent"
        s.commit()
    reject_for(h, "ana")
    await accept(h)
    thread = thread_of(h)
    assert thread.handoff_status == "closed" and thread.handoff_deadline == closed.handoff_deadline


async def test_displaced_leg_without_wamid_cannot_be_waited_for(h):
    await derive(h)
    await expire(h)
    with h.sessions() as s:
        s.get(HandoffLeg, leg_of(h, "juan").id).wamid = None
        s.commit()
    reject_for(h, "ana")
    await accept(h)
    assert thread_of(h).handoff_status == "closed"


async def freeze_delivery(w, wamid, op, tap_id="wamid.tapA") -> None:
    """Un toque gana y su acuse queda frenado."""
    w.graph.op_gate, w.graph.op_gate_to = asyncio.Event(), TO[op]
    w.service.handle_payload(tap_payload(wamid, op, tap_id))
    await asyncio.wait_for(w.graph.op_entered.wait(), 3)
    assert thread_of(w).handoff_status == "delivering"


async def tap_and_wait(w, wamid, op, tap_id, text) -> None:
    w.service.handle_payload(tap_payload(wamid, op, tap_id))
    await until(lambda: text in w.graph.texts(TO[op]))


async def test_lost_tap_takes_the_delivery_when_the_winner_fails(h):
    """Quien toco tarde, tras vencer su turno, tambien cuenta."""
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    ana = leg_of(h, "ana")
    assert ana.result == "no_answer" and ana.answered_at is not None
    before = h.graph.texts(SEND_TO)
    reject_for(h, "juan")
    set_thread(h, handoff_retakes=2)
    h.graph.op_gate.set()
    await h.service.drain()
    thread = thread_of(h)
    assert thread.handoff_status == "accepted" and thread.handoff_leg_id == ana.id and thread.handoff_retakes == 0
    took, ack, contact = h.graph.texts(TO["ana"])
    assert took == "Ya la tomó Juan." and ack.startswith("Recibido.") and PERSON_PHONE in contact
    assert PERSON_PHONE not in ack
    assert leg_of(h, "ana").result == "connected" and leg_of(h, "juan").result == "failed"
    assert len([c for c in h.tools.calls if c[0] == "post_call"]) == 1
    assert not any(t.startswith("No pude comunicarte") for t in h.graph.texts(SEND_TO))
    assert h.graph.texts(SEND_TO)[len(before):] == ["Ana recibió tu pedido y te va a contactar. Lo que escribas acá también le llega."]
    assert event_types(h).count("handoff.confirmed") == 2
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "ack_rejected"


async def test_lost_tap_of_the_displaced_leg_takes_the_delivery(h):
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl1", "ana")
    await tap_and_wait(h, "wamid.tpl2", "juan", "wamid.tapB", "Ya la tomó Ana.")
    assert leg_of(h, "juan").result == "whatsapp_sent"
    reject_for(h, "ana")
    h.graph.op_gate.set()
    await h.service.drain()
    assert thread_of(h).handoff_status == "accepted"
    assert leg_of(h, "juan").result == "connected" and PERSON_PHONE in h.graph.texts(TO["juan"])[-1]


async def test_lost_tap_gets_nothing_more_if_the_winner_delivers(h):
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    h.graph.op_gate.set()
    await h.service.drain()
    assert thread_of(h).handoff_leg_id == leg_of(h, "juan").id
    assert h.graph.texts(TO["ana"]) == ["Ya la tomó Juan."]
    assert leg_of(h, "juan").result == "connected" and leg_of(h, "ana").result == "no_answer"


async def test_oldest_lost_tap_goes_first_and_a_second_tap_keeps_its_place(sessions, monkeypatch):
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM())
    w.area_id = make_area(w, "Guardia", ["ana", "juan", "eva"])
    configure(w, [w.area_id])
    w.tools = Tools(w)
    await derive(w)
    await expire(w)
    await expire(w)
    await freeze_delivery(w, "wamid.tpl3", "eva")
    await tap_and_wait(w, "wamid.tpl2", "juan", "wamid.tapB", "Ya la tomó Eva.")
    first = leg_of(w, "juan").answered_at
    await tap_and_wait(w, "wamid.tpl1", "ana", "wamid.tapC", "Ya la tomó Eva.")
    w.service.handle_payload(tap_payload("wamid.tpl2", "juan", "wamid.tapD"))
    await until(lambda: len(w.graph.texts(TO["juan"])) == 2)
    assert leg_of(w, "juan").answered_at == first
    reject_for(w, "eva")
    w.graph.op_gate.set()
    await w.service.drain()
    assert thread_of(w).handoff_leg_id == leg_of(w, "juan").id
    assert w.graph.texts(TO["ana"]) == ["Ya la tomó Eva."]


async def test_all_who_tapped_fail_ends_without_loop(h):
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    h.graph.reject_text = lambda to, body: rejected() if to == TO["juan"] or body.startswith("Recibido") else None
    h.graph.op_gate.set()
    await h.service.drain()
    assert [leg.result for leg in legs(h)] == ["failed", "failed"]
    assert thread_of(h).handoff_status == "closed"
    assert len([t for t in h.graph.texts(SEND_TO) if t.startswith("No pude comunicarte")]) == 1
    assert len(events_of(h, "handoff.whatsapp_failed")) == 2


async def test_failed_contact_after_accepted_goes_to_who_tapped_without_second_charge(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await accept(h, "wamid.tpl2", "juan", "wamid.tapA")
    assert thread_of(h).handoff_status == "accepted"
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    contact = team_texts(h)[1]
    await send(h, status_payload("status_failed.json", contact))
    assert thread_of(h).handoff_status == "accepted"
    assert thread_of(h).handoff_leg_id == leg_of(h, "ana").id
    assert PERSON_PHONE in h.graph.texts(TO["ana"])[-1]
    assert len([c for c in h.tools.calls if c[0] == "post_call"]) == 1
    assert leg_of(h, "juan").connected_at is None


async def test_tap_of_another_rotation_does_not_take_the_delivery(h):
    await derive(h)
    await expire(h)
    with h.sessions() as s:
        ana = s.get(HandoffLeg, leg_of(h, "ana").id)
        ana.created_at, ana.answered_at = utcnow() - datetime.timedelta(hours=1), utcnow()
        s.commit()
    set_thread(h, handoff_started_at=utcnow() - datetime.timedelta(minutes=1))
    reject_for(h, "juan")
    await accept(h, "wamid.tpl2", "juan", "wamid.tapA")
    # Sin toque que la tome, la rotacion sigue: ana es de otra rotacion y se le vuelve a enviar la plantilla.
    assert h.graph.texts(TO["ana"]) == [] and thread_of(h).handoff_status == "waiting"
    assert h.graph.templates() == [TO["ana"], TO["juan"], TO["ana"]]


async def test_tap_with_the_rotation_over_is_not_recorded_as_lost(h):
    await derive(h)
    await expire(h)
    await expire(h)
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await accept(h)
    assert h.graph.texts(TO["ana"]) == ["Esta solicitud ya se cerró."]
    assert leg_of(h, "ana").answered_at is None


# --- Mensajes de antes de aceptar ----------------------------------------------------------------------------

async def test_pre_accept_messages_never_carry_contact_data(h):
    """Ni con los datos ya guardados en la fila: la barrera es lo que se le pasa a render."""
    all_vars = "{{area}} {{cliente}} {{ cliente }} {{nombre}} {{ficha}} {{resumen}}"
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).messages = {key: f"{key}: {all_vars}" for key in handoff_service.PRE_ACCEPT_MESSAGES}
        s.commit()
    configure(h, [h.area_id], post_call="handoff_accepted", pre_call=True)
    h.tools.gate = asyncio.Event()
    await derive(h)
    await expire(h)
    h.service.handle_payload(tap_payload("wamid.tpl1", "ana", "wamid.tapA"))
    await until(lambda: len(h.graph.texts(TO["ana"])) == 1)
    h.service.handle_payload(tap_payload("wamid.tpl1", "ana", "wamid.tapB"))
    h.service.handle_payload(tap_payload("wamid.tpl2", "juan", "wamid.tapC"))
    await until(lambda: len(h.graph.texts(TO["ana"])) == 2 and len(h.graph.texts(TO["juan"])) == 1)
    h.tools.gate.set()
    await h.service.drain()
    assert thread_of(h).handoff_status == "accepted"
    set_thread(h, handoff_deadline=utcnow() - datetime.timedelta(seconds=1))
    await send(h, tap_payload("wamid.tpl2", "juan", "wamid.tapD"))
    sent = [*h.graph.texts(TO["ana"])[:2], *h.graph.texts(TO["juan"])]
    assert sorted(t.split(":")[0] for t in sent) == sorted(handoff_service.PRE_ACCEPT_MESSAGES)
    for text in sent:
        assert text.endswith(": Guardia"), text


def test_validate_messages_limits_the_pre_accept_ones():
    for key in handoff_service.PRE_ACCEPT_MESSAGES:
        for bad in ("{{cliente}}", "{{ cliente }}", "{{ficha}}", "{{resumen}}", "{{nombre}}", "{{area}} y {{otra}}"):
            with pytest.raises(handoff_service.Invalid, match="todavía no lleva los datos"):
                handoff_service.validate_messages({key: bad})
        assert handoff_service.validate_messages({key: "{{area}} {{ persona }} {{horario}}"})
    assert handoff_service.validate_messages({"operator_contact": "{{cliente}} {{ficha}}", "whisper": "{{resumen}}",
                                              "accepted": "{{nombre}}"})
    for key in handoff_service.PRE_ACCEPT_MESSAGES:
        vars_ = handoff_service._VAR.findall(handoff_service.DEFAULT_MESSAGES[key])
        assert set(vars_) <= set(handoff_service.PRE_ACCEPT_VARIABLES)


@pytest.mark.parametrize("text", ["{{cliente}}", "{{ cliente }}", "{{ficha}}"])
def test_api_rejects_contact_data_before_accepting(api, admin, text):  # noqa: F811
    client = make_client(admin)
    r = admin.post(f"{V1}/handoff-areas", params={"client_id": client["id"]},
                   json={"name": "Guardia", "messages": {"tap_taken": text}})
    assert r.status_code == 422 and "todavía no lleva los datos" in r.text


# --- Status failed antes de la respuesta del envio ---------------------------------------------------------

async def test_failed_status_during_send_template_goes_to_the_next_person_at_once(h):
    h.graph.gate, h.graph.gate_to = asyncio.Event(), TO["ana"]
    h.llm.turns[:] = [reply("Te paso con el equipo.", handoff="Guardia")]
    h.service.handle_payload(text_payload("me desmayé", "wamid.in1"))
    await asyncio.wait_for(h.graph.entered.wait(), 3)
    h.service.handle_payload(status_payload("status_failed.json", "wamid.tpl1"))

    def status_row():
        with h.sessions() as s:
            return s.scalar(select(WaMessage).where(WaMessage.wamid == "wamid.tpl1")) is not None

    await until(status_row)
    h.graph.gate.set()
    await h.service.drain()
    ana, juan = legs(h)
    assert (ana.result, ana.wamid) == ("failed", None)
    assert juan.phone == OPS["juan"] and juan.wamid == "wamid.tpl2"
    assert thread_of(h).handoff_status == "waiting" and thread_of(h).handoff_leg_id == juan.id
    assert [e["wamid"] for e in events_of(h, "handoff.whatsapp_sent")] == ["wamid.tpl2"]
    assert [e["reason"] for e in events_of(h, "handoff.whatsapp_failed")] == ["meta_failed"]
    with h.sessions() as s:
        rows = list(s.scalars(select(WaMessage).where(WaMessage.direction == "out", WaMessage.status == "failed")))
    assert [row.wamid for row in rows] == ["wamid.tpl1"]    # sin una segunda fila por la falla


# --- Miembro borrado o desactivado ----------------------------------------------------------------------------

def remove_member(w, op, how) -> None:
    with w.sessions() as s:
        leg = s.scalar(select(HandoffLeg).where(HandoffLeg.phone == OPS[op]))
        member = s.get(TeamMember, leg.team_member_id)
        if how == "desactivado":
            member.active = False
        else:
            s.execute(update(HandoffLeg).where(HandoffLeg.team_member_id == member.id).values(team_member_id=None))
            handoff_service.delete_member(s, member)
        s.commit()


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_relay_to_a_removed_member_ends_it(h, how):
    conv = await accepted(h)
    before = len(h.graph.texts(TO["ana"]))
    remove_member(h, "ana", how)
    await send(h, text_payload("sigo mal", "wamid.r1"))
    assert len(h.graph.texts(TO["ana"])) == before
    assert events_of(h, "handoff.relay_failed")[-1]["reason"] == "no_route"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude hacerle llegar tu mensaje a")
    assert thread_of(h, conv).handoff_deadline <= utcnow()
    h.llm.turns[:] = [reply("Sigo yo")]
    await send(h, text_payload("otra", "wamid.r2"))
    assert h.graph.texts(SEND_TO)[-1] == "Sigo yo"


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_tap_of_a_removed_member_gets_nothing_and_goes_on(h, how):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    remove_member(h, "ana", how)
    await accept(h)
    assert h.graph.texts(TO["ana"]) == [] and h.tools.calls == []
    assert leg_of(h, "ana").result == "failed"
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "no_route"
    assert h.graph.templates() == [TO["ana"], TO["juan"]] and thread_of(h).handoff_status == "waiting"


@pytest.mark.parametrize("how", ["desactivado", "borrado"])
async def test_second_tap_of_a_removed_member_does_not_get_the_contact(h, how):
    text = "Esta solicitud ya se cerró."
    await accepted(h)
    before = h.graph.texts(TO["ana"])
    remove_member(h, "ana", how)
    await accept(h, tap_id="wamid.tap2")
    assert h.graph.texts(TO["ana"]) == [*before, text]


async def test_lost_tap_of_a_deactivated_member_gets_nothing(h):
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    remove_member(h, "ana", "desactivado")
    reject_for(h, "juan")
    h.graph.op_gate.set()
    await h.service.drain()
    assert h.graph.texts(TO["ana"]) == ["Ya la tomó Juan."]
    assert leg_of(h, "ana").result == "failed" and thread_of(h).handoff_status == "closed"


def remove_during_post_call(w, op, how) -> None:
    """El miembro se va mientras corre el post-call: entre el acuse y el contacto."""
    real = w.tools.run

    async def run(workflow, state, slug, actor, key, *, emit=True):
        remove_member(w, op, how)
        return await real(workflow, state, slug, actor, key, emit=emit)

    w.engine.tools.run_workflow = run


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_member_removed_during_delivery_does_not_get_the_contact(h, how):
    """Un solo operador: no sale el telefono, la entrega falla por no_route y la persona se entera."""
    with h.sessions() as s:
        s.scalar(select(TeamMember).where(TeamMember.phone == OPS["juan"])).whatsapp_notify = False
        s.commit()
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    remove_during_post_call(h, "ana", how)
    await accept(h)
    [ack] = h.graph.texts(TO["ana"])
    assert ack.startswith("Recibido.") and PERSON_PHONE not in ack
    [leg] = legs(h)
    assert leg.result == "failed" and leg.connected_at is None
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "no_route"
    assert "handoff.connected" not in event_types(h)
    assert thread_of(h).handoff_status == "closed"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Guardia")
    # El cobro ya corrio: queda hecho, una sola vez, aunque nadie haya recibido el contacto.
    assert post_call_row(h).post_call_status == "done" and len(h.tools.calls) == 1


async def test_member_deactivated_during_delivery_passes_on_without_repeating_the_charge(h):
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    remove_during_post_call(h, "ana", "desactivado")
    await accept(h)
    assert len(h.graph.texts(TO["ana"])) == 1
    assert h.graph.templates() == [TO["ana"], TO["juan"]] and thread_of(h).handoff_status == "waiting"
    await accept(h, "wamid.tpl2", "juan", "wamid.tap2")
    assert thread_of(h).handoff_status == "accepted"
    assert len(h.tools.calls) == 1 and post_call_row(h).post_call_attempts == 1
    contact = h.graph.texts(TO["juan"])[1]
    assert contact.startswith("Cobro registrado.") and PERSON_PHONE in contact
    assert len(h.graph.texts(TO["ana"])) == 1


async def test_member_deactivated_while_post_call_outlasts_the_wait(h):
    """El post-call sigue en su tarea: termina y no se repite con el operador siguiente."""
    configure(h, [h.area_id], post_call="handoff_accepted")
    h.tools.gate = asyncio.Event()
    await derive(h)
    remove_during_post_call(h, "ana", "desactivado")
    h.service.handle_payload(tap_payload("wamid.tpl1"))
    await until(lambda: len(h.graph.templates()) == 2 and thread_of(h).handoff_status == "waiting")
    assert len(h.graph.texts(TO["ana"])) == 1
    assert post_call_row(h).post_call_status == "running"
    h.tools.gate.set()
    await h.service.drain()
    assert post_call_row(h).post_call_status == "done"
    await accept(h, "wamid.tpl2", "juan", "wamid.tap2")
    assert len(h.tools.calls) == 1
    assert h.graph.texts(TO["juan"])[1].startswith("Cobro registrado.")


async def test_member_deactivated_during_a_contact_retry_does_not_get_it(h):
    """Tambien en la retoma, que no repite el acuse ni el post-call."""
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    h.graph.reject_text = lambda to, body: rejected() if to == TO["ana"] and "Contacto" in body else None
    await accept(h)
    assert thread_of(h).handoff_delivery_tries == 1
    h.graph.reject_text = lambda to, body: None
    real = h.service.handoffs._summary

    async def summary(conversation_id, timeout=None):
        remove_member(h, "ana", "desactivado")
        return await real(conversation_id, timeout)

    h.service.handoffs._summary = summary
    await expire(h)
    assert len(h.graph.texts(TO["ana"])) == 1
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "no_route"
    assert leg_of(h, "ana").result == "failed" and h.graph.templates() == [TO["ana"], TO["juan"]]


def member_gone(w, op, how) -> None:
    """Como remove_member, tambien sin tramos: desactivado, o borrado con sus tramos sin team_member_id."""
    with w.sessions() as s:
        member = s.scalar(select(TeamMember).where(TeamMember.client_id == w.client_id, TeamMember.phone == OPS[op]))
        if how == "desactivado":
            member.active = False
        else:
            s.execute(update(HandoffLeg).where(HandoffLeg.team_member_id == member.id).values(team_member_id=None))
            handoff_service.delete_member(s, member)
        s.commit()


def summary_area(w, members) -> str:
    """Un area cuya plantilla lleva el resumen, y un LLM que sabe hacerlo."""
    area = make_area(w, "Guardia2", members, template={**ROTATION, "params": ["area", "resumen"]})
    configure(w, [area])
    return area


def gone_during_summary(w, op, how) -> None:
    real = w.service.handoffs._summary

    async def summary(conversation_id, timeout=None):
        member_gone(w, op, how)
        return await real(conversation_id, timeout)

    w.service.handoffs._summary = summary


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_rotation_template_skips_who_left_during_its_summary(h, how, caplog):
    """La plantilla lleva el resumen y las variables del pre-call: sigue enseguida con el siguiente, sin el barrido."""
    summary_area(h, ["ana", "juan"])
    gone_during_summary(h, "ana", how)
    await derive_to(h, "Guardia2", "Te paso con el equipo.")
    assert h.graph.templates() == [TO["juan"]] and thread_of(h).handoff_status == "waiting"
    assert [leg.phone for leg in legs(h)] == [OPS["juan"]]
    assert [e["members"] for e in events_of(h, "handoff.requested")] == [2]
    assert "handoff.whatsapp_failed" not in event_types(h)
    assert not [r for r in caplog.records if r.levelname == "ERROR" and "resumen" not in r.getMessage()]


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_rotation_template_skips_who_left_while_meta_rejected_the_previous(h, how, caplog):
    """Tres personas: Meta rechaza a la primera y la segunda se va en esa espera."""
    area = make_area(h, "Guardia3", ["ana", "juan", "eva"])
    configure(h, [area])
    real = h.graph.send_template

    async def send_template(pnid, to, name, language, params=None):
        if to == TO["ana"]:
            member_gone(h, "juan", how)
            raise rejected()
        return await real(pnid, to, name, language, params)

    h.graph.send_template = send_template
    await derive_to(h, "Guardia3", "Te paso con el equipo.")
    assert h.graph.templates() == [TO["eva"]] and thread_of(h).handoff_status == "waiting"
    assert [leg.phone for leg in legs(h)] == [OPS["ana"], OPS["eva"]]
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_rotation_with_everyone_gone_ends_as_no_answer(h, how):
    area = make_area(h, "Guardia4", ["ana"], template={**ROTATION, "params": ["area", "resumen"]})
    configure(h, [area])
    gone_during_summary(h, "ana", how)
    await derive_to(h, "Guardia4", "Te paso con el equipo.")
    assert h.graph.templates() == [] and legs(h) == []
    assert thread_of(h).handoff_status == "closed"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Guardia4")
    assert "handoff.requested" in event_types(h) and "handoff.dialing" not in event_types(h)


async def test_rotation_member_deleted_right_before_the_insert_does_not_kill_the_task(h, caplog):
    """La FK rechaza el tramo (SQLite no las aplica: se simula el rechazo solo para esa persona)."""
    with h.sessions() as s:
        ana = s.scalar(select(TeamMember).where(TeamMember.phone == OPS["ana"])).id

    def check(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO handoff_legs") and ana in str(parameters):
            raise IntegrityError(statement, parameters, Exception("foreign key"))

    bind = h.sessions.kw["bind"]
    event.listen(bind, "before_cursor_execute", check)
    try:
        await derive(h)
    finally:
        event.remove(bind, "before_cursor_execute", check)
    assert h.graph.templates() == [TO["juan"]] and thread_of(h).handoff_status == "waiting"
    assert [leg.phone for leg in legs(h)] == [OPS["juan"]]
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


async def test_rotation_does_not_send_if_it_cannot_reread(h, monkeypatch):
    """Sin poder confirmar que sigue activa, no sale. Queda registrado y termina sin respuesta."""
    real = handoffs.select

    def broken(*columns):
        if columns == (TeamMember.active,):
            raise RuntimeError("sin base")
        return real(*columns)

    monkeypatch.setattr(handoffs, "select", broken)
    await derive(h)
    assert h.graph.templates() == [] and legs(h) == []
    assert [e["reason"] for e in events_of(h, "handoff.whatsapp_failed")] == ["internal", "internal"]
    assert thread_of(h).handoff_status == "closed"
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Guardia")


async def test_lost_tap_of_a_deleted_member_gets_closed_and_never_the_delivery(h):
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    member_gone(h, "ana", "borrado")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Esta solicitud ya se cerró.")
    assert leg_of(h, "ana").answered_at is None
    reject_for(h, "juan")
    h.graph.op_gate.set()
    await h.service.drain()
    assert h.graph.texts(TO["ana"]) == ["Esta solicitud ya se cerró."]


async def test_lost_tap_against_a_deleted_member_is_still_taken(h):
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    member_gone(h, "juan", "borrado")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó la persona que tomó tu pedido.")
    h.graph.op_gate.set()
    await h.service.drain()


async def test_notice_area_skips_who_was_deactivated_during_the_previous_send(h):
    aviso = make_area(h, "Aviso final", ["eva", "juan"], delivery="whatsapp", template=NOTICE)
    with h.sessions() as s:
        s.get(HandoffArea, h.area_id).no_answer_area_id = aviso
        s.commit()
    await derive(h)
    await expire(h)
    real = h.graph.send_template

    async def send_template(pnid, to, name, language, params=None):
        if to == TO["eva"]:
            with h.sessions() as s:
                s.scalar(select(TeamMember).where(TeamMember.phone == OPS["juan"])).active = False
                s.commit()
            raise rejected()
        return await real(pnid, to, name, language, params)

    h.graph.send_template = send_template
    await expire(h)
    assert [x for x in h.graph.log if x[0] == "template" and x[2] == NOTICE["name"]] == []
    assert h.graph.texts(SEND_TO)[-1].startswith("No pude comunicarte con Aviso final")
    assert "handoff.notified" not in event_types(h)


async def test_lost_tap_deactivated_during_its_delivery_does_not_get_the_contact(h):
    """Quien perdio toma la entrega al fallar la del otro, y se va durante el post-call."""
    configure(h, [h.area_id], post_call="handoff_accepted")
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    remove_during_post_call(h, "ana", "desactivado")
    reject_for(h, "juan")
    h.graph.op_gate.set()
    await h.service.drain()
    took, ack = h.graph.texts(TO["ana"])
    assert took == "Ya la tomó Juan." and PERSON_PHONE not in ack
    assert leg_of(h, "ana").result == "failed" and leg_of(h, "juan").result == "failed"
    assert events_of(h, "handoff.whatsapp_failed")[-1]["reason"] == "no_route"
    assert "handoff.connected" not in event_types(h) and thread_of(h).handoff_status == "closed"
    assert len(h.tools.calls) == 1


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_member_removed_during_the_summary_of_a_second_tap_does_not_get_the_contact(h, how):
    await accepted(h)
    before = h.graph.texts(TO["ana"])
    real = h.service.handoffs._summary

    async def summary(conversation_id, timeout=None):
        remove_member(h, "ana", how)
        return await real(conversation_id, timeout)

    h.service.handoffs._summary = summary
    await accept(h, tap_id="wamid.tap2")
    assert h.graph.texts(TO["ana"]) == [*before, "Esta solicitud ya se cerró."]


# --- Retomas tras una falla de entrega o un toque --------------------------------------------------------------

async def test_delivery_failed_gives_the_retakes_back(h):
    """Un _advance que lanza despues de agotar las retomas de la entrega tiene sus propias 5, no cierra enseguida."""
    real = h.service.handoffs._deliver

    async def boom(*a):
        raise RuntimeError("fila trabada")

    await derive(h)
    h.service.handoffs._deliver = boom
    await accept(h)
    for _ in range(handoffs.MAX_RETAKES - 1):
        await expire(h)
    h.service.handoffs._advance = boom
    await expire(h)
    h.service.handoffs._deliver = real
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("sending", 0)
    await expire(h)
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("sending", 1)


async def test_delivery_failed_back_to_closed_gives_the_retakes_back(h):
    async def boom(*a):
        raise RuntimeError("fila trabada")

    await derive(h)
    await expire(h)
    await expire(h)
    h.service.handoffs._deliver = boom
    await accept(h)
    for _ in range(handoffs.MAX_RETAKES):
        await expire(h)
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("closed", 0)


async def test_tap_gives_the_retakes_back(h):
    async def boom(*a):
        raise RuntimeError("fila trabada")

    await derive(h)
    set_thread(h, handoff_retakes=handoffs.MAX_RETAKES - 1)
    h.service.handoffs._deliver = boom
    await accept(h)
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("delivering", 0)
    await expire(h)
    assert (thread_of(h).handoff_status, thread_of(h).handoff_retakes) == ("delivering", 1)


async def test_most_recent_displaced_leg_is_the_one_that_waits(sessions, monkeypatch):
    monkeypatch.setattr(settings, "post_call_wait_seconds", 0.1)
    w = make_wa(sessions, graph=Graph(), llm=FakeLLM())
    w.area_id = make_area(w, "Guardia", ["ana", "juan", "eva"])
    configure(w, [w.area_id])
    w.tools = Tools(w)
    await derive(w)
    await expire(w)
    await expire(w)
    with w.sessions() as s:      # dos tramos tocables: uno quedo enviado por un wamid tardio
        s.get(HandoffLeg, leg_of(w, "ana").id).result = "whatsapp_sent"
        s.get(HandoffLeg, leg_of(w, "juan").id).result = "whatsapp_sent"
        s.commit()
    reject_for(w, "eva")
    await accept(w, "wamid.tpl3", "eva", "wamid.tapA")
    thread = thread_of(w)
    assert thread.handoff_status == "waiting" and thread.handoff_leg_id == leg_of(w, "juan").id


async def test_lost_tap_starts_its_delivery_from_the_ack(h):
    """Los intentos de contacto del que fallo no cuentan para el siguiente."""
    await derive(h)
    await expire(h)
    await freeze_delivery(h, "wamid.tpl2", "juan")
    await tap_and_wait(h, "wamid.tpl1", "ana", "wamid.tapB", "Ya la tomó Juan.")
    h.graph.reject_text = lambda to, body: rejected() if to == TO["juan"] and body.startswith("Contacto") else None
    h.graph.op_gate.set()
    await h.service.drain()
    assert thread_of(h).handoff_delivery_tries == 1
    await expire(h)
    await expire(h)
    assert thread_of(h).handoff_status == "accepted" and thread_of(h).handoff_leg_id == leg_of(h, "ana").id
    _, ack, contact = h.graph.texts(TO["ana"])
    assert ack.startswith("Recibido.") and PERSON_PHONE in contact
