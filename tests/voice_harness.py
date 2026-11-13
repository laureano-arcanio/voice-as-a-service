"""Arnes del worker de voz: corre el `entrypoint` real con la room, la sesion y el telefono falsos, y el motor, la base
y la herramienta reales. Imita el orden del SDK de LiveKit: espera el entrypoint y recien despues corre los callbacks
de cierre (livekit/agents/ipc/job_proc_lazy_main.py). Sin LiveKit ni modelos: lo que hace una llamada real lo prueba
make e2e-sip."""
import asyncio
import json
import time
from types import SimpleNamespace

from app.agents.templates import reference_data
from app.conversation.models import Message
from app.models import CallMode, CallRow
from app.services import calls as call_service
from app.voice import worker

from .test_api import V1, make_client
from .test_handoff_transfer import FakeLine

DID = "+541152630861"
CALLER = "+5493513962553"
CUSTOMER = f"sip_{CALLER}"


class FakeHandle:
    """Lo que devuelve session.say: se puede esperar, directo o con wait_for_playout."""

    def __await__(self):
        return asyncio.sleep(0).__await__()

    async def wait_for_playout(self):
        await asyncio.sleep(0)


class FakeSession:
    def __init__(self, log: list):
        self.log = log
        self.agent = None
        self.input = SimpleNamespace(set_audio_enabled=lambda on: None)

    def on(self, event, fn):
        pass

    async def start(self, agent, room):
        self.agent = agent
        self.log.append("session.start")

    def say(self, text, **kw):
        self.log.append(f"say:{text}")
        return FakeHandle()

    def interrupt(self):
        pass


class FakeRoom:
    def __init__(self):
        self.name = "room-prueba"
        self.remote_participants: dict = {}
        self.handlers: dict = {}
        self.connected = True

    def on(self, event, fn):
        self.handlers[event] = fn

    def isconnected(self) -> bool:
        return self.connected

    def join(self, identity: str, **attributes):
        participant = SimpleNamespace(identity=identity, attributes=attributes)
        self.remote_participants[identity] = participant
        return participant

    def leave(self, identity: str):
        """El cliente se va: la room lo saca y avisa."""
        participant = self.remote_participants.pop(identity)
        self.handlers["participant_disconnected"](participant)


class FakeCtx:
    def __init__(self, metadata: dict, log: list, attributes: dict | None, sip_error: Exception | None):
        self.log = log
        self.job = SimpleNamespace(metadata=json.dumps(metadata))
        self.room = FakeRoom()
        self.attributes = attributes        # los de la entrante; None si la persona entra despues
        self.sip_error = sip_error
        self.callbacks: list = []
        self.reason = ""
        self.sip_requests: list = []
        self.api = SimpleNamespace(sip=SimpleNamespace(create_sip_participant=self._dial))

    async def connect(self):
        if self.attributes is not None:
            self.room.join(CUSTOMER, **self.attributes)

    async def _dial(self, request):
        self.log.append("create_sip_participant")
        self.sip_requests.append(request)
        if self.sip_error is not None:
            raise self.sip_error
        self.room.join("customer")

    async def wait_for_participant(self):
        if not self.room.remote_participants:
            self.room.join(CUSTOMER)
        return next(iter(self.room.remote_participants.values()))

    def add_shutdown_callback(self, fn):
        self.callbacks.append(fn)

    def shutdown(self, reason: str = ""):
        self.reason = self.reason or reason

    async def delete_room(self):
        self.log.append("delete_room")
        self.room.connected = False


class Harness:
    """Una llamada: `run` corre el entrypoint, `during` (lo que pasa con la llamada en curso) y los callbacks."""

    def __init__(self, api, monkeypatch, script: dict | None = None, connected: list | None = None):
        self.api = api
        self.log: list = []
        self.script = script or {}
        self.connected = connected or []
        self.session = FakeSession(self.log)
        self.ctx: FakeCtx | None = None
        self.line: FakeLine | None = None
        harness = self

        class Line(FakeLine):
            """El FakeLine de los tests de derivacion, con la forma de RoomLine."""

            def __init__(self, ctx, session, **kw):
                super().__init__(harness.script, connected=harness.connected)
                harness.line = self

            async def start(self):
                pass

            async def aclose(self):
                pass

        async def resolve_voice(workflow, override=None):
            return "voz"

        async def trunk_id(lkapi):
            return "trunk"

        monkeypatch.setattr(worker, "get_conversation_engine", lambda: api.engine)
        monkeypatch.setattr(worker, "get_sessionmaker", lambda: api.sessions)
        monkeypatch.setattr(worker, "build_session", lambda voice, conversation_id=None: self.session)
        monkeypatch.setattr(worker, "resolve_voice", resolve_voice)
        monkeypatch.setattr(worker, "outbound_trunk_id", trunk_id)
        monkeypatch.setattr(worker.transfer, "RoomLine", Line)

    def on_pre_call(self, monkeypatch, action=None):
        """Registra el pre-call en el orden de la llamada; `action(ctx)` corre mientras espera."""
        real = self.api.engine.run_pre_call

        async def run_pre_call(conversation_id, actor=None):
            self.log.append("pre_call")
            # Con finalize y la salida del cliente registrados: si no, un corte aca se perderia.
            self.log.append(("registered", bool(self.ctx.callbacks),
                             "participant_disconnected" in self.ctx.room.handlers))
            result = await real(conversation_id, actor)
            if action is not None:
                action(self.ctx)
            return result

        monkeypatch.setattr(self.api.engine, "run_pre_call", run_pre_call)

    async def run(self, metadata: dict, *, attributes: dict | None = None, sip_error: Exception | None = None,
                  during=None) -> None:
        self.ctx = FakeCtx(metadata, self.log, attributes, sip_error)
        await worker.entrypoint(self.ctx)
        if during is not None:
            await during(self)
        for callback in self.ctx.callbacks:
            await callback(self.ctx.reason)

    def call(self, conversation_id: str) -> CallRow:
        with self.api.sessions() as s:
            return s.get(CallRow, conversation_id)

    @property
    def order(self) -> list[str]:
        return [x for x in self.log if isinstance(x, str)]


def inbound_attributes(wa_id: str | None = None) -> dict:
    attributes = {"sip.trunkPhoneNumber": DID, "sip.phoneNumber": CALLER}
    return {**attributes, "wa.wacid": wa_id} if wa_id else attributes


def seed_call(api, agent_id: str, client_id: str, mode: CallMode, phone: str | None = None) -> str:
    """Una llamada ya admitida, como la deja la API antes de despachar el worker (services/calls.py)."""
    with api.sessions() as s:
        outbound = mode in (CallMode.saliente, CallMode.celular)
        state, _ = api.engine.new_conversation(agent_id, client_id, session=s, call={
            "phone": phone, "direction": "outbound" if outbound else "inbound", "mode": str(mode),
            **({"to": phone} if outbound else {"from": phone})})
        api.engine.store.add(s, state)
        s.flush()
        s.add(CallRow(conversation_id=state.conversation_id, client_id=client_id, mode=mode, phone=phone))
        s.commit()
    return state.conversation_id


def team_to_agent(monkeypatch, api, spoken: str = "Te estoy comunicando, aguardá."):
    """El numero lo atiende el equipo: nadie atiende y pasa al agente, con el to_agent real del worker."""
    real = call_service.start_inbound

    def start_inbound(s, engine, dialed, caller, wa_id=None, line_id=None):
        inbound = real(s, engine, dialed, caller, wa_id=wa_id, line_id=line_id)
        inbound.team = SimpleNamespace(agent_id=api.engine.store.get(inbound.conversation_id).agent_id)
        return inbound

    async def run_inbound_team(ctx, inbound, *, to_agent, **kw):
        state = api.engine.store.get(inbound.conversation_id)
        state.messages = [Message(role="assistant", text=spoken)]
        api.engine.store.save(state)
        assert to_agent()
        return time.time() - 30, 2

    monkeypatch.setattr(worker.call_service, "start_inbound", start_inbound)
    monkeypatch.setattr(worker.direct, "run_inbound_team", run_inbound_team)


ASSIGN = [{"var": "situacion", "path": "status"}, {"var": "nombre", "path": "name"},
          {"var": "al_dia", "path": "al_dia", "hide": True}, {"var": "ficha", "path": "record", "hide": True},
          {"var": "nota_operador", "path": "operator_note", "hide": True}]
OPENING = "Hola {{nombre}}, soy Ana."
OPERATORS = {"+5493511111111": "confirm", "+5493512222222": "confirm"}


def http_tool(slug: str, url: str, method: str = "POST", assign: list | None = None, **http) -> dict:
    body = {"type": "object", "properties": {"conversation_id": {"type": "string", "value": "{{call.id}}"},
                                             "from": {"type": "string", "value": "{{call.phone}}"}}}
    return {"slug": slug, "type": "http", "definition": {
        "description": "Herramienta de un workflow.", "assign": assign or [],
        "http": {"method": method, "url": url, **({"body": body} if method != "GET" else {}), **http}}}


def identify_tool(base: str, **kw) -> dict:
    return http_tool("buscar_ficha", base + "/identificar", assign=ASSIGN, **kw)


def charge_tool(base: str) -> dict:
    return http_tool("registrar_cobro", base + "/cobrar")


def new_client(admin, slug: str = "acme"):
    return make_client(admin, slug, max_tools=None, code_tools=True, outbound_minutes=100, whatsapp=True,
                       call_links=True)


def add_tool(admin, client: dict, tool: dict) -> None:
    r = admin.post(f"{V1}/clients/{client['id']}/tools", json=tool)
    assert r.status_code == 201, r.text


def add_area(admin, client: dict) -> str:
    ids = [admin.post(f"{V1}/team", params={"client_id": client["id"]}, json={"name": n, "phone": p}).json()["id"]
           for n, p in (("Ana", "3511111111"), ("Juan", "3512222222"))]
    r = admin.post(f"{V1}/handoff-areas", params={"client_id": client["id"]},
                   json={"name": "Ventas", "description": "Precios", "member_ids": ids})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_agent(admin, client: dict, *, workflows: dict | None = None, opening: str = OPENING,
              area: str | None = None, slug: str = "ana", **extra) -> dict:
    """Agente del cliente con esa apertura, que atiende DID (si el numero todavia esta libre)."""
    definition = reference_data("sales_discovery")
    definition["first_message"] = opening
    if workflows:
        definition["workflows"] = workflows
    if area:
        definition["handoff"] = {"areas": [{"area_id": area, "when": "Precios"}]}
    r = admin.post(f"{V1}/agents", json={"client_id": client["id"], "name": "Ana", "slug": slug,
                                         "definition": {**definition, **extra}})
    assert r.status_code == 201, r.text
    agent = r.json()
    number = admin.post(f"{V1}/phone-numbers", json={"client_id": client["id"], "e164": DID, "agent_id": agent["id"]})
    assert number.status_code in (201, 409, 422), number.text
    return agent


class Clock:
    """time y utcnow de los modulos de voz, con `skip(s)`: simula una espera de `s` segundos sin esperarla."""

    def __init__(self, monkeypatch, *modules):
        import datetime

        from app.db import utcnow

        self.offset = 0.0
        clock = self
        real_time = time

        class _Time:
            def __getattr__(self, name):
                return getattr(real_time, name)

            def time(self):
                return real_time.time() + clock.offset

        for module in modules:
            monkeypatch.setattr(module, "time", _Time())
            monkeypatch.setattr(module, "utcnow", lambda: utcnow() + datetime.timedelta(seconds=clock.offset))

    def skip(self, seconds: float) -> None:
        self.offset += seconds
