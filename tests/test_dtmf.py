"""Teclas (DTMF) en la linea (app/voice/dtmf.py, docs/features/EQUIPO_TELEFONIA.md "Teclas marcadas"): el
agrupador, el mensaje "Marcó 123" con Message.dtmf, el evento call.dtmf, la entrante al equipo en cada fase, la
saliente directa y la derivacion del agente. Lineas falsas, sin LiveKit ni modelos."""
import asyncio
from types import SimpleNamespace

from sqlalchemy import select

from app.conversation.models import Message
from app.models import Event
from app.voice import direct, dtmf
from app.voice import handoff as transfer

from .test_api import V1, admin  # noqa: F401  (admin: fixture)
from .test_direct_voice import PCM, FakeOut, TeamLine, outbound, run_out, team_call, team_setup
from .test_handoff_transfer import CUSTOMER, FakeLine, setup_call


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def dtmf_events(api, cid):
    with api.sessions() as s:
        return [(e.actor, e.data) for e in s.scalars(select(Event).where(Event.conversation_id == cid,
                                                                          Event.type == "call.dtmf")
                                                     .order_by(Event.id))]


def shown(api, cid):
    return [(m.role, m.text, m.dtmf, m.person, m.handoff_leg) for m in api.engine.store.get(cid).messages]


# ---------- agrupador ----------

def test_keys_groups_by_party_and_pause():
    clock = Clock()
    keys = dtmf.Keys(clock=clock)
    assert keys.press("a", "1") == ("1", True)
    clock.t += 2.9
    assert keys.press("a", "2") == ("12", False)
    clock.t += dtmf.GROUP_PAUSE_SECONDS      # la pausa corta el grupo
    assert keys.press("a", "3") == ("3", True)
    assert keys.press("b", "4") == ("4", True)   # otra parte, otro grupo
    assert keys.close() == "4"
    assert keys.press("b", "5") == ("5", True)   # cerrado: el siguiente abre otro


# ---------- mensaje, evento y panel ----------

def test_keylog_extends_the_message_cuts_on_phrase_and_pause(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    cid = inbound.conversation_id
    clock, sent = Clock(), []
    log = dtmf.KeyLog(sessions=api.sessions, store=api.engine.store, conversation_id=cid,
                      send=lambda topic, data: sent.append((topic, data)), keys=dtmf.Keys(clock=clock))
    log.press("1")
    first_at = api.engine.store.get(cid).messages[-1].at
    clock.t += 1
    log.press("2")
    clock.t += 1
    log.press("3")
    direct.CallLog(api.engine.store, cid).add("assistant", "Gracias")     # una frase en el medio
    clock.t += 0.5
    log.press("4")
    clock.t += 5
    log.press("#")                                                        # despues de la pausa
    assert shown(api, cid) == [("user", "Marcó 123", "123", None, None), ("assistant", "Gracias", None, None, None),
                               ("user", "Marcó 4", "4", None, None), ("user", "Marcó #", "#", None, None)]
    # La hora es la del primer digito.
    assert api.engine.store.get(cid).messages[0].at == first_at
    assert dtmf_events(api, cid) == [("customer", {"digit": d}) for d in "1234#"]
    assert [d["text"] for _, d in sent] == ["Marcó 1", "Marcó 12", "Marcó 123", "Marcó 4", "Marcó #"]
    assert [d["extend"] for _, d in sent] == [False, True, True, False, False]
    assert sent[2] == ("transcript", {"role": "user", "person": None, "text": "Marcó 123", "dtmf": "123",
                                      "extend": True})
    # El detalle (GET /calls/{id}) trae dtmf en el mensaje; las frases, null.
    msgs = admin.get(f"{V1}/calls/{cid}").json()["messages"]
    assert [(m["text"], m["dtmf"]) for m in msgs] == [("Marcó 123", "123"), ("Gracias", None), ("Marcó 4", "4"),
                                                      ("Marcó #", "#")]
    # Los eventos salen por GET /events.
    events = admin.get(f"{V1}/events", params={"client_id": c["id"], "conversation_id": cid}).json()
    assert [e["data"]["digit"] for e in events if e["type"] == "call.dtmf"] == list("1234#")


def test_message_without_dtmf_reads_as_before():
    assert Message(role="user", text="Hola").dtmf is None
    assert Message.model_validate({"role": "user", "text": "Marcó 1", "dtmf": "1"}).dtmf == "1"


# ---------- entrante al equipo ----------

class KeyLine(TeamLine):
    """TeamLine que marca teclas de quien llama (on_dtmf, como RoomLine) en `marks`: (momento, digitos). Momentos:
    hold (empieza la musica), dial (suena un celular), connect (conectado con el celular), listen (el panel o el
    buzon empiezan a escuchar)."""

    def __init__(self, *a, marks=(), **kw):
        super().__init__(*a, **kw)
        self.marks = list(marks)
        self.on_dtmf = None

    def _mark(self, when):
        for w, digits in [m for m in self.marks if m[0] == when]:
            self.marks.remove((w, digits))
            for d in digits:
                self.on_dtmf(d)

    async def hold(self, on):
        await super().hold(on)
        if on:
            self._mark("hold")

    async def dial(self, identity, phone, ring_seconds):
        self._mark("dial")
        return await super().dial(identity, phone, ring_seconds)

    async def connect(self, identity):
        self._mark("connect")
        await super().connect(identity)

    async def listen(self, identity):
        self._mark("listen")
        await super().listen(identity)


def test_team_keys_while_waiting_and_on_the_phone_leg(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None))
    cid = inbound.conversation_id
    line = KeyLine({"+5493512222222": "confirm"}, marks=[("dial", "12"), ("connect", "3")],
                   connected=[("text", "PERSON", "Hola, soy Pedro"), ("dtmf", CUSTOMER, "9"), ("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered"
    msgs = shown(api, cid)
    # Mientras suena el celular, sin tramo; conectado, con el tramo de Pedro (el bloque no se corta en el panel).
    assert msgs[0] == ("user", "Marcó 12", "12", None, None)
    leg = msgs[1][4]
    assert leg and msgs[1:] == [("user", "Marcó 3", "3", None, leg), ("assistant", "Hola, soy Pedro", None, "Pedro", leg)]
    # El 9 de la cola es de la persona falsa en otra fase: lo de la conversacion sale solo del callback.
    assert dtmf_events(api, cid) == [("customer", {"digit": d}) for d in "123"]
    team.close()
    assert line.on_dtmf is None    # al cerrar, la linea deja de guardar teclas


def test_team_keys_while_waiting_and_talking_in_the_panel(api, admin, monkeypatch, tmp_path):
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Ana", None, "ana"))
    cid = inbound.conversation_id
    ana, ana_id = users["ana"]
    ana.put(f"{V1}/me/presence", json={"available": True})
    line = KeyLine({}, marks=[("hold", "0"), ("listen", "45")],
                   on_listen=[("text", CUSTOMER, "Hola", PCM), ("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)

    async def go():
        async def answer():
            while not ana.get(f"{V1}/me/ringing").json():
                await asyncio.sleep(0.05)
            await asyncio.to_thread(ana.post, f"{V1}/direct-calls/{cid}/answer")
            line.events.put_nowait(("joined", f"user-{ana_id}"))
        helper = asyncio.create_task(answer())
        result = await team.run()
        await helper
        return result

    assert asyncio.run(go()) == "answered"
    # En espera y ya hablando en el panel, sin pausa ni frase en el medio: un solo grupo.
    assert [m[:3] for m in shown(api, cid)] == [("user", "Marcó 045", "045"), ("user", "Hola", None)]
    # La transcripcion en vivo del panel recibe las teclas con el resto.
    assert [d["text"] for t, d in line.sent if t == "transcript"] == ["Marcó 0", "Marcó 04", "Marcó 045", "Hola"]


def test_team_keys_in_voicemail(api, admin, monkeypatch, tmp_path):
    """Nadie atiende y quien llama marca mientras deja el mensaje."""
    c2, inbound2, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None),
                                 team_fallback="voicemail")
    line2 = KeyLine({"+5493511111111": "no_answer"}, marks=[("listen", "7")],
                    on_listen=[("text", CUSTOMER, "Llamame", PCM), ("left", CUSTOMER)])
    assert asyncio.run(team_call(api, c2, inbound2, line2).run()) == "voicemail"
    assert [m[1] for m in shown(api, inbound2.conversation_id)][1:] == ["Marcó 7", "Llamame"]


# ---------- RoomLine ----------

def test_roomline_passes_only_the_callers_keys():
    got = []
    line = transfer.RoomLine.__new__(transfer.RoomLine)
    line.customer, line.events, line.on_dtmf = CUSTOMER, asyncio.Queue(), None
    ev = lambda who, d: SimpleNamespace(participant=SimpleNamespace(identity=who), digit=d)  # noqa: E731
    line._on_dtmf(ev(CUSTOMER, "1"))                 # sin on_dtmf: solo la cola
    line.on_dtmf = got.append
    line._on_dtmf(ev(CUSTOMER, "2"))
    line._on_dtmf(ev("persona-1", "1"))              # el 1 de la persona es de la derivacion
    assert got == ["2"] and line.events.qsize() == 3


# ---------- saliente directa ----------

class KeyOut(FakeOut):
    def __init__(self, *a, marks=(), **kw):
        super().__init__(*a, **kw)
        self.marks = list(marks)
        self.on_dtmf = None

    async def listen(self, identities):
        await super().listen(identities)
        for who, d in self.marks:
            self.on_dtmf(who, d)


def test_outbound_keys_of_contact_and_panel_user(api, admin, monkeypatch, tmp_path):
    meta, user, _ = outbound(api, admin, monkeypatch, tmp_path)
    line = KeyOut(dialed=[("sip", direct.CONTACT, "active")], talk=[("left", direct.CONTACT, "")],
                  marks=[(user, "1"), (user, "2"), (direct.CONTACT, "5"), ("otro", "9")])
    assert run_out(api, meta, line) == "completed"
    cid = meta["conversation_id"]
    assert shown(api, cid) == [("assistant", "Marcó 12", "12", "ana@acme.com", None),
                               ("user", "Marcó 5", "5", None, None)]
    assert dtmf_events(api, cid) == [("person", {"digit": "1", "person": "ana@acme.com"}),
                                     ("person", {"digit": "2", "person": "ana@acme.com"}),
                                     ("customer", {"digit": "5"})]


# ---------- derivacion del agente ----------

def test_transfer_leg_only_while_connected(api, admin):
    c, conv, areas = setup_call(api, admin)
    seen = []

    class Line(FakeLine):
        async def connect(self, identity):
            seen.append(tr_ref[0].leg)
            await super().connect(identity)

    line = Line({"+5493511111111": "confirm"}, connected=[("left", "PERSON")])
    tr = transfer.Transfer(sessions=api.sessions, line=line, conversation_id=conv, client_id=c["id"], areas=areas,
                           customer=CUSTOMER, confirm_seconds=0.3)
    tr_ref = [tr]
    assert tr.leg is None
    asyncio.run(tr.run("Ventas"))
    assert seen[0] and tr.leg is None
