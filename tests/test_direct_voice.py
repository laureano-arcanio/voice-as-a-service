"""Llamadas directas en el worker (app/voice/direct.py y app/voice/listen.py, docs/LLAMADAS_DIRECTAS_PLAN.md):
la logica con lineas falsas, sin LiveKit ni inferencia. La API y el ruteo estan en tests/test_direct_calls.py."""
import asyncio
import wave
from types import SimpleNamespace

import pytest
from livekit.agents import vad as agents_vad

from app.config import settings
from app.models import CallRing, CallRow, CallStatus, ConversationRow, Event, HandoffLeg
from app.services import calls as call_service
from app.services import direct_calls
from app.voice import direct
from app.voice import handoff as transfer
from app.voice.listen import Listener
from livekit import rtc

from .test_api import V1, admin, client_user, make_agent  # noqa: F401  (admin: fixture)
from .test_direct_calls import DID, add_contact, setup
from .test_handoff import member
from .test_handoff_transfer import CUSTOMER, FakeLine

PCM = b"\x01\x00" * 1600     # 0,1 s a 16 kHz


@pytest.fixture(autouse=True)
def short_rejoin(monkeypatch):
    """Que el usuario del panel salga y no vuelva no espera los 30 s de verdad."""
    monkeypatch.setattr(direct, "PANEL_REJOIN_GRACE_SECONDS", 0.2)


def messages(api, cid):
    return [(m.role, m.text, m.person, m.recording) for m in api.engine.store.get(cid).messages]


def call_row(api, cid) -> CallRow:
    with api.sessions() as s:
        return s.get(CallRow, cid)


# ---------- captura y transcripcion ----------

class FakeVadStream:
    def __init__(self, events):
        self.events = events

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for ev in self.events:
            yield ev


def test_listener_phrases_become_messages_with_person_and_recording(api, admin, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path)
    _, _, ana, _ = setup(api, admin)
    cid = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"}).json()["conversation_id"]
    sent: list[tuple] = []
    log = direct.CallLog(api.engine.store, cid, lambda topic, data: sent.append((topic, data)))
    texts = iter(["Hola, ¿quién habla?", "", "Te llamo de Acme"])

    async def recognize(frames, language=None):
        assert language == "es"
        return SimpleNamespace(alternatives=[SimpleNamespace(text=f" {next(texts)} ")])

    who = {"contacto": ("user", None), "user-1": ("assistant", "Ana")}
    listener = Listener(None, SimpleNamespace(recognize=recognize),
                        lambda identity, text, pcm: log.add(who[identity][0], text, person=who[identity][1], pcm=pcm))
    frame = rtc.AudioFrame(PCM, 16000, 1, len(PCM) // 2)
    end = SimpleNamespace(type=agents_vad.VADEventType.END_OF_SPEECH, frames=[frame])
    start = SimpleNamespace(type=agents_vad.VADEventType.START_OF_SPEECH, frames=[])

    async def run():
        await listener._transcribe(FakeVadStream([start, end, end]), "contacto")   # la segunda: STT vacio
        await listener._transcribe(FakeVadStream([end]), "user-1")

    asyncio.run(run())
    assert messages(api, cid) == [("user", "Hola, ¿quién habla?", None, 1), ("assistant", "Te llamo de Acme", "Ana", 2)]
    with wave.open(str(tmp_path / cid / "002.wav")) as w:
        assert (w.getframerate(), w.getnframes()) == (16000, 1600)
    assert sent == [("transcript", {"role": "user", "person": None, "text": "Hola, ¿quién habla?"}),
                    ("transcript", {"role": "assistant", "person": "Ana", "text": "Te llamo de Acme"})]


def test_recording_notice_is_synthesized_once(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "notice_audio_dir", tmp_path)
    said: list[str] = []

    class Voice(direct.Voice):
        async def synthesize(self, text):
            said.append(text)
            return b"\x02\x00" * 2400

    async def run():
        voice = Voice(None, None, SimpleNamespace(sample_rate=24000))   # su pista necesita el loop
        return await direct.notice_pcm(voice, "sofia"), await direct.notice_pcm(voice, "sofia")

    first, again = asyncio.run(run())
    assert first == again == b"\x02\x00" * 2400 and said == [direct.RECORDING_NOTICE]
    assert (tmp_path / "sofia.wav").is_file()


# ---------- saliente ----------

class FakeOut:
    """El lado de LiveKit de la saliente: `dialed` son los eventos despues de marcar; `talk`, despues de conectar."""

    def __init__(self, *, joins=True, dial="dialing", dialed=(), talk=(), last_words=()):
        self.joins, self.dial_result = joins, dial
        self.dialed, self.talk = list(dialed), list(talk)
        self.last_words = list(last_words)     # lo que el STT termina despues de que sale alguien (settle)
        self.events: asyncio.Queue = asyncio.Queue()
        self.sent: list[tuple] = []
        self.log: list[tuple] = []

    async def wait_for(self, identity, timeout):
        self.log.append(("wait_for", identity, timeout))
        return self.joins

    async def dial(self, identity, phone, caller_id, ring_seconds, max_seconds):
        self.log.append(("dial", identity, phone, caller_id))
        for ev in self.dialed:
            self.events.put_nowait(ev)
        return transfer.DialResult(self.dial_result, 503 if self.dial_result == "failed" else None)

    def send(self, topic, data):
        self.sent.append((topic, data))

    async def notice(self):
        self.log.append(("notice",))

    async def say(self, text):
        self.log.append(("say", text))

    async def listen(self, identities):
        self.log.append(("listen", sorted(identities)))
        for ev in self.talk:
            self.events.put_nowait(ev)

    async def settle(self, identity, timeout):
        self.log.append(("settle", identity))
        for ev in self.last_words:
            self.events.put_nowait(ev)
        self.last_words = []

    async def remove(self, identity):
        self.log.append(("remove", identity))

    def states(self):
        return [d["state"] + (f":{d['result']}" if "result" in d else "") for t, d in self.sent if t == "call_status"]


def outbound(api, admin, monkeypatch, tmp_path, **meta):
    """Una saliente directa de Ana: (metadata del worker, identidad de Ana, nueva(): otra llamada de Ana)."""
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path)
    c, _, ana, ana_id = setup(api, admin)
    add_contact(api, c["id"])

    def new(**extra):
        r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493516775617"})
        assert r.status_code == 201, r.text
        return {**api.dispatched[-1], **extra}
    return new(**meta), f"user-{ana_id}", new


def run_out(api, metadata, line):
    out = direct.Outbound(sessions=api.sessions, store=api.engine.store, line=line, metadata=metadata)
    return asyncio.run(out.run())


def test_outbound_answers_talks_and_contact_hangs_up(api, admin, monkeypatch, tmp_path):
    meta, user, _ = outbound(api, admin, monkeypatch, tmp_path, recording_notice=True)
    line = FakeOut(dialed=[("joined", direct.CONTACT), ("sip", direct.CONTACT, "dialing"),
                           ("sip", direct.CONTACT, "ringing"), ("sip", direct.CONTACT, "ringing"),
                           ("sip", direct.CONTACT, "active")],
                   talk=[("text", direct.CONTACT, "Hola", PCM), ("text", user, "Hola Juan, te llamo de Acme", PCM),
                         ("text", "otro", "no cuenta", PCM), ("left", direct.CONTACT, "")],
                   # La ultima frase del contacto, que el STT termina despues de que corta.
                   last_words=[("text", direct.CONTACT, "Chau", PCM)])
    assert run_out(api, meta, line) == "completed"
    assert line.states() == ["joining", "dialing", "ringing", "active", "ended:completed"]
    # Escucha antes del aviso de grabacion: lo que dicen mientras suena tambien queda.
    assert line.log[:4] == [("wait_for", user, 30), ("dial", "contact", "+5493516775617", DID),
                            ("listen", sorted([user, "contact"])), ("notice",)]
    assert ("settle", direct.CONTACT) in line.log
    cid = meta["conversation_id"]
    assert messages(api, cid) == [("user", "Hola", None, 1), ("assistant", "Hola Juan, te llamo de Acme", "ana@acme.com", 2),
                                  ("user", "Chau", None, 3)]
    assert sorted(p.name for p in (tmp_path / cid).iterdir()) == ["001.wav", "002.wav", "003.wav"]
    call = call_row(api, cid)
    assert (call.status, call.ended_reason) == (CallStatus.finalizada, "customer_hangup")
    assert call.started_at is not None and call.ended_at is not None
    assert api.engine.store.get(cid).status == "completed"


def test_outbound_user_does_not_join(api, admin, monkeypatch, tmp_path):
    meta, _, _ = outbound(api, admin, monkeypatch, tmp_path)
    line = FakeOut(joins=False)
    assert run_out(api, meta, line) == "failed"
    assert not [x for x in line.log if x[0] == "dial"] and line.states() == ["joining", "ended:failed"]
    call = call_row(api, meta["conversation_id"])
    assert (call.status, call.ended_reason, call.started_at) == (CallStatus.fallida, "user_not_joined", None)


def test_outbound_no_answer_busy_and_failed(api, admin, monkeypatch, tmp_path):
    meta, _, new = outbound(api, admin, monkeypatch, tmp_path)
    for left, result, reason in (("no_answer", "no_answer", "no_answer"), ("busy", "busy", "busy"),
                                 ("", "failed", "sip_call_failed")):
        meta = meta or new()
        line = FakeOut(dialed=[("sip", direct.CONTACT, "ringing"), ("left", direct.CONTACT, left)])
        assert run_out(api, meta, line) == result
        assert line.states() == ["joining", "dialing", "ringing", f"ended:{result}"]
        assert ("remove", "contact") in line.log
        call = call_row(api, meta["conversation_id"])
        assert (call.status, call.ended_reason, call.started_at) == (CallStatus.fallida, reason, None)
        meta = None
    # Falla al marcar (create_sip_participant levanta): fallida con el codigo SIP.
    meta = new()
    assert run_out(api, meta, FakeOut(dial="failed")) == "failed"
    call = call_row(api, meta["conversation_id"])
    assert (call.ended_reason, call.sip_status) == ("sip_call_failed", 503)


def test_outbound_user_hangs_up_and_hangup_from_the_api_wins(api, admin, monkeypatch, tmp_path):
    meta, user, new = outbound(api, admin, monkeypatch, tmp_path)
    line = FakeOut(dialed=[("sip", direct.CONTACT, "active")], talk=[("left", user, "")])
    assert run_out(api, meta, line) == "completed"
    assert call_row(api, meta["conversation_id"]).ended_reason == "person_hangup"

    # Cortada desde la API (POST /calls/{id}/hangup): la room se cierra y queda hangup_by_user.
    meta = new()
    with api.sessions() as s:
        s.get(CallRow, meta["conversation_id"]).ended_reason = call_service.HANGUP_REASON
        s.commit()
    line = FakeOut(dialed=[("sip", direct.CONTACT, "active")], talk=[("closed", "")])
    assert run_out(api, meta, line) == "completed"
    assert call_row(api, meta["conversation_id"]).ended_reason == call_service.HANGUP_REASON


def test_outbound_user_reloads_and_comes_back(api, admin, monkeypatch, tmp_path):
    # Recarga la pagina (sale de la room) y vuelve a entrar con "Volver a entrar": la llamada sigue.
    meta, user, new = outbound(api, admin, monkeypatch, tmp_path)
    monkeypatch.setattr(direct, "PANEL_REJOIN_GRACE_SECONDS", 5)
    line = FakeOut(dialed=[("sip", direct.CONTACT, "active")],
                   talk=[("left", user, ""), ("joined", user), ("text", user, "Perdón, se me cortó", PCM),
                         ("left", direct.CONTACT, "")])
    assert run_out(api, meta, line) == "completed"
    assert call_row(api, meta["conversation_id"]).ended_reason == "customer_hangup"
    assert [m[1] for m in messages(api, meta["conversation_id"])] == ["Perdón, se me cortó"]

    # Tambien mientras suena: sale, vuelve y el contacto atiende.
    meta = new()
    line = FakeOut(dialed=[("left", user, ""), ("sip", direct.CONTACT, "ringing"), ("joined", user),
                           ("sip", direct.CONTACT, "active")], talk=[("left", direct.CONTACT, "")])
    assert run_out(api, meta, line) == "completed"
    assert call_row(api, meta["conversation_id"]).ended_reason == "customer_hangup"

    # Sale mientras suena y no vuelve: se corta sin esperar a que atiendan.
    monkeypatch.setattr(direct, "PANEL_REJOIN_GRACE_SECONDS", 0.2)
    meta = new()
    line = FakeOut(dialed=[("left", user, ""), ("sip", direct.CONTACT, "ringing")])
    assert run_out(api, meta, line) == "no_answer"
    call = call_row(api, meta["conversation_id"])
    assert (call.status, call.ended_reason) == (CallStatus.cancelada, "person_hangup")

    # Corta desde el panel (POST /calls/{id}/hangup) mientras suena: cancelada, no fallida.
    meta = new()
    with api.sessions() as s:
        s.get(CallRow, meta["conversation_id"]).ended_reason = call_service.HANGUP_REASON
        s.commit()
    line = FakeOut(dialed=[("sip", direct.CONTACT, "ringing"), ("closed", "")])
    assert run_out(api, meta, line) == "no_answer"
    call = call_row(api, meta["conversation_id"])
    assert (call.status, call.ended_reason, call.started_at) == (CallStatus.cancelada, "hangup_by_user", None)


def test_outbound_max_duration(api, admin, monkeypatch, tmp_path):
    meta, _, _ = outbound(api, admin, monkeypatch, tmp_path, max_duration_seconds=0.3)
    line = FakeOut(dialed=[("sip", direct.CONTACT, "active")])
    assert run_out(api, meta, line) == "completed"
    assert ("say", settings.quota_end_message) in line.log
    assert call_row(api, meta["conversation_id"]).ended_reason == "max_duration"


# ---------- entrante al equipo ----------

class TeamLine(FakeLine):
    """La linea de la derivacion (FakeLine) mas lo del equipo: `on_listen`, eventos al empezar a escuchar."""

    def __init__(self, script=None, connected=(), on_listen=(), last_words=()):
        super().__init__(script or {}, connected)
        self.on_listen = list(on_listen)
        self.last_words = list(last_words)
        self.sent: list[tuple] = []

    async def listen(self, identity):
        self.log.append(("listen", identity))
        for ev in self.on_listen:
            self.events.put_nowait(ev)
        self.on_listen = []

    def send(self, topic, data):
        self.sent.append((topic, data))

    async def settle(self, identity, timeout):
        self.log.append(("settle", identity))
        for ev in self.last_words:
            self.events.put_nowait(ev)
        self.last_words = []

    async def block(self, identity):
        self.log.append(("block", identity))


def team_setup(api, admin, monkeypatch, tmp_path, *people, **number):
    """Numero del equipo con esas personas ((nombre, celular, usuario)) y una entrante en curso."""
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path)
    c, n, ana, ana_id = setup(api, admin)
    users = {"ana": (ana, ana_id)}
    ids = []
    for name, phone, user in people:
        if user and user not in users:
            u = client_user(api, admin, c, email=f"{user}@acme.com")
            users[user] = (u, u.get(f"{V1}/auth/me").json()["id"])
        body = {"name": name, "phone": phone} if phone else {"name": name, "whatsapp": "3510000000"}
        if user:
            body["user_id"] = users[user][1]
        ids.append(member(admin, c["id"], **body)["id"])
    r = admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"member_ids": ids, **number})
    assert r.status_code == 200, r.text
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493513962553")
        call_service.update_call(s, inbound.conversation_id, status=CallStatus.en_curso)
    inbound.team.ring_seconds = 1
    return c, inbound, users


def team_outcome(admin, cid):
    """El `team` del detalle de la llamada (GET /calls/{id})."""
    return admin.get(f"{V1}/calls/{cid}").json()["call"]["team"]


def team_call(api, c, inbound, line, **kw):
    return direct.TeamCall(sessions=api.sessions, store=api.engine.store, line=line,
                           conversation_id=inbound.conversation_id, client_id=c["id"], route=inbound.team,
                           customer=CUSTOMER, caller="+5493513962553", confirm_seconds=0.3, **kw)


def test_team_phone_first_nobody_then_panel_answers(api, admin, monkeypatch, tmp_path):
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None),
                                   ("Ana", None, "ana"))
    cid = inbound.conversation_id
    ana, ana_id = users["ana"]
    ana.put(f"{V1}/me/presence", json={"available": True})
    line = TeamLine({"+5493511111111": "busy"},
                    on_listen=[("text", CUSTOMER, "Hola, quería consultar", PCM), ("text", f"user-{ana_id}", "Sí, decime", PCM),
                               ("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)

    async def answer_in_the_panel():
        while not ana.get(f"{V1}/me/ringing").json():
            await asyncio.sleep(0.05)
        r = await asyncio.to_thread(ana.post, f"{V1}/direct-calls/{cid}/answer")
        assert r.status_code == 200, r.text
        line.events.put_nowait(("joined", f"user-{ana_id}"))

    async def run():
        helper = asyncio.create_task(answer_in_the_panel())
        result = await team.run()
        await helper
        return result

    assert asyncio.run(run()) == "answered" and team.reason == "customer_hangup"
    assert [x for x in line.log if x[0] in ("dial", "hold", "listen")] == [
        ("hold", True), ("dial", "+5493511111111"), ("hold", False), ("listen", f"user-{ana_id}"), ("hold", False)]
    assert messages(api, cid) == [("user", "Hola, quería consultar", None, 1), ("assistant", "Sí, decime", "Ana", 2)]
    # La transcripcion en vivo llega al panel de Ana (tema transcript), como en la saliente.
    assert line.sent == [("transcript", {"role": "user", "person": None, "text": "Hola, quería consultar"}),
                         ("transcript", {"role": "assistant", "person": "Ana", "text": "Sí, decime"})]
    with api.sessions() as s:
        assert s.get(CallRow, cid).user_id == ana_id
        assert [r.status for r in s.query(CallRing).filter_by(conversation_id=cid)] == ["answered"]
        assert s.query(HandoffLeg).one().result == "busy"


def test_team_panel_first_nobody_available_then_phone_confirms(api, admin, monkeypatch, tmp_path):
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Ana", None, "ana"),
                                   ("Pedro", "3512222222", "pedro"), ring_first="panel")
    cid = inbound.conversation_id
    # Nadie Disponible en el panel: directo a los celulares; Pedro atiende, marca 1, hablan y corta Pedro.
    line = TeamLine({"+5493512222222": "confirm"},
                    connected=[("text", "PERSON", "Hola, soy Pedro"), ("text", CUSTOMER, "Hola Pedro"),
                               ("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    whisper = next(x[1] for x in line.log if x[0] == "whisper")
    assert whisper == "Llamada a la línea de +5493513962553. Marcá 1 para atender."
    assert [(r, t, p) for r, t, p, _ in messages(api, cid)] == [("assistant", "Hola, soy Pedro", "Pedro"),
                                                               ("user", "Hola Pedro", None)]
    with api.sessions() as s:
        assert s.get(CallRow, cid).user_id == users["pedro"][1]      # atendio en su celular, con su usuario
        leg = s.query(HandoffLeg).one()
        assert leg.result == "connected" and leg.area_id is None and leg.ended_at is not None
        types = [e.type for e in s.query(Event).filter(Event.conversation_id == cid, Event.type.not_like("call.%"))
                 .order_by(Event.id)]
    assert types == ["hold.started", "handoff.dialing", "handoff.answered", "handoff.confirmed",
                     "handoff.connected", "handoff.ended", "handoff.person_hung_up", "hold.ended"]
    assert team_outcome(admin, cid) == {"answered": True, "person": "Pedro", "fallback": None}


def test_team_panel_first_one_answers(api, admin, monkeypatch, tmp_path):
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Ana", None, "ana"),
                                   ("Pedro", "3512222222", "pedro"), ring_first="panel")
    cid = inbound.conversation_id
    for u, _ in users.values():
        u.put(f"{V1}/me/presence", json={"available": True})
    pedro, pedro_id = users["pedro"]
    line = TeamLine({}, on_listen=[("left", f"user-{pedro_id}")])
    team = team_call(api, c, inbound, line)

    async def run():
        async def pedro_answers():
            while not pedro.get(f"{V1}/me/ringing").json():
                await asyncio.sleep(0.05)
            await asyncio.to_thread(pedro.post, f"{V1}/direct-calls/{cid}/answer")
            line.events.put_nowait(("joined", f"user-{users['ana'][1]}"))   # no atendio: no cuenta
            line.events.put_nowait(("joined", f"user-{pedro_id}"))
        helper = asyncio.create_task(pedro_answers())
        result = await team.run()
        await helper
        return result

    assert asyncio.run(run()) == "answered" and team.reason == "person_hangup"
    assert not [x for x in line.log if x[0] == "dial"]
    with api.sessions() as s:
        assert {r.user_id: r.status for r in s.query(CallRing).filter_by(conversation_id=cid)} == {
            pedro_id: "answered", users["ana"][1]: "cancelled"}


def test_team_after_hours_goes_to_the_agent_or_hangs_up(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None),
                               schedule={"week": {}}, team_fallback="hangup",
                               team_fallback_message="Estamos cerrados.")
    line = TeamLine()
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "hangup" and team.reason == "after_hours"
    assert ("say", "Estamos cerrados.") in line.log and not [x for x in line.log if x[0] == "dial"]
    assert messages(api, inbound.conversation_id) == [("assistant", "Estamos cerrados.", None, None)]
    # El detalle dice que nadie atendio y el respaldo (evento team.fallback).
    assert team_outcome(admin, inbound.conversation_id) == {"answered": False, "person": None, "fallback": "hangup"}

    # Respaldo agent: la conversacion pasa al agente del numero, con su apertura.
    agent = make_agent(admin, c)
    with api.sessions() as s:
        number_id = s.get(CallRow, inbound.conversation_id).phone_number_id
    r = admin.patch(f"{V1}/phone-numbers/{number_id}", json={"agent_id": agent["id"], "team_fallback": "agent"})
    assert r.status_code == 200, r.text
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493513962553")
    cid = inbound.conversation_id

    def to_agent():
        with api.sessions() as s:
            return direct_calls.fallback_to_agent(s, api.engine, cid, inbound.team.agent_id, "+5493513962553") is not None

    team = team_call(api, c, inbound, TeamLine(), to_agent=to_agent)
    assert asyncio.run(team.run()) == "agent"
    state = api.engine.store.get(cid)
    assert state.agent_id == agent["id"] and state.messages[0].role == "assistant" and len(state.messages) == 1
    with api.sessions() as s:
        assert s.get(ConversationRow, cid).agent_id == agent["id"]
        assert s.get(CallRow, cid).answered_by == "agent"
    assert team_outcome(admin, cid) == {"answered": False, "person": None, "fallback": "agent"}


def test_team_nobody_answers_voicemail_records(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None),
                               ("Ana", None, "ana"))
    cid = inbound.conversation_id
    # Juan no atiende, Ana no esta Disponible: mensaje por defecto y se graba lo que dice el que llama.
    line = TeamLine({"+5493511111111": "no_answer"},
                    on_listen=[("text", CUSTOMER, "Soy Laura, llamame al 351 555 1234", PCM), ("left", CUSTOMER)],
                    # Lo ultimo que dijo antes de cortar, sin el silencio que cierra la frase: entra igual.
                    last_words=[("text", CUSTOMER, "Gracias", PCM)])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "voicemail" and team.reason == "team_no_answer"
    assert ("say", direct.FALLBACK_MESSAGES["voicemail"]) in line.log and ("resume",) in line.log
    assert ("settle", CUSTOMER) in line.log
    assert messages(api, cid) == [("assistant", direct.FALLBACK_MESSAGES["voicemail"], None, None),
                                  ("user", "Soy Laura, llamame al 351 555 1234", None, 1), ("user", "Gracias", None, 2)]
    assert (tmp_path / cid / "001.wav").is_file()
    assert team_outcome(admin, cid) == {"answered": False, "person": None, "fallback": "voicemail"}


def test_team_panel_answer_right_before_the_rings_go_off(api, admin, monkeypatch, tmp_path):
    # Pedro atiende justo cuando vence el timbre (despues del ultimo sondeo): el worker lo ve al apagar los timbres
    # y lo espera, en vez de pasar al respaldo con la llamada ya a su nombre.
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", None, "pedro"),
                                   ring_first="panel")
    cid = inbound.conversation_id
    pedro, pedro_id = users["pedro"]
    pedro.put(f"{V1}/me/presence", json={"available": True})
    line = TeamLine({}, on_listen=[("left", f"user-{pedro_id}")])
    cancel = direct_calls.cancel_rings

    def answer_then_cancel(s, conversation_id):
        if s.get(CallRow, conversation_id).user_id is None:
            assert pedro.post(f"{V1}/direct-calls/{cid}/answer").status_code == 200
            line.events.put_nowait(("joined", f"user-{pedro_id}"))
        s.expire_all()
        cancel(s, conversation_id)

    monkeypatch.setattr(direct_calls, "cancel_rings", answer_then_cancel)
    monkeypatch.setattr(direct, "PANEL_POLL_SECONDS", 5)     # un solo sondeo: no lo ve antes del vencimiento
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert call_row(api, cid).user_id == pedro_id


def test_team_panel_answer_without_joining_is_released(api, admin, monkeypatch, tmp_path):
    # Pedro atiende pero su navegador no entra: vencida la espera, la llamada no queda a su nombre (ni ocupado),
    # un answer tardio ya no la toma y va al respaldo.
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", None, "pedro"),
                                   ring_first="panel")
    cid = inbound.conversation_id
    pedro, pedro_id = users["pedro"]
    pedro.put(f"{V1}/me/presence", json={"available": True})
    monkeypatch.setattr(direct, "PANEL_JOIN_GRACE_SECONDS", 0.3)
    line = TeamLine({}, on_listen=[("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)

    async def run():
        async def pedro_answers():
            while not pedro.get(f"{V1}/me/ringing").json():
                await asyncio.sleep(0.05)
            assert (await asyncio.to_thread(pedro.post, f"{V1}/direct-calls/{cid}/answer")).status_code == 200
        helper = asyncio.create_task(pedro_answers())
        result = await team.run()
        await helper
        return result

    assert asyncio.run(run()) == "voicemail" and team.reason == "team_no_answer"
    # Si su navegador entra tarde con el token de answer, se lo saca de la room.
    assert ("block", f"user-{pedro_id}") in line.log
    with api.sessions() as s:
        assert s.get(CallRow, cid).user_id is None
        assert [r.status for r in s.query(CallRing).filter_by(conversation_id=cid)] == ["cancelled"]
        assert direct_calls.busy_user_ids(s, c["id"]) == set()
    r = pedro.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 409 and r.json()["code"] == "not_ringing"


def test_team_phone_connected_is_cut_by_duration_and_minutes(api, admin, monkeypatch, tmp_path):
    # Atendio en el celular: sin el quota_watchdog del worker, el tope de duracion (desde que entro la llamada)
    # y los minutos entrantes los controla el tramo (Transfer.limit).
    monkeypatch.setattr(settings, "quota_check_seconds", 0.1)
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None))
    team = team_call(api, c, inbound, TeamLine({"+5493512222222": "confirm"}))
    team.deadline = 0       # ya paso el tope
    assert asyncio.run(team.run()) == "answered" and team.reason == "max_duration"

    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493513962553")
        call_service.update_call(s, inbound.conversation_id, status=CallStatus.en_curso)
    inbound.team.ring_seconds = 1
    monkeypatch.setattr(call_service, "call_remaining_seconds", lambda s, cid: 0)
    team = team_call(api, c, inbound, TeamLine({"+5493512222222": "confirm"}))
    assert asyncio.run(team.run()) == "answered" and team.reason == "quota_exhausted"


# ---------- lado de LiveKit ----------

class FakeRoom:
    def __init__(self):
        self.handlers: dict[str, list] = {}
        self.remote_participants: dict = {}
        self.name = "call-x"
        self.connected = True
        self.local_participant = SimpleNamespace(track_publications={})

    def on(self, event, fn):
        self.handlers.setdefault(event, []).append(fn)

    def off(self, event, fn):
        self.handlers[event].remove(fn)

    def isconnected(self):
        return self.connected

    def emit(self, event, *args):
        for fn in list(self.handlers.get(event, [])):
            fn(*args)


def fake_ctx(room, removed):
    async def remove_participant(req):
        removed.append(req.identity)
    return SimpleNamespace(room=room, api=SimpleNamespace(room=SimpleNamespace(remove_participant=remove_participant)))


def fake_voice():
    async def aclose():
        pass
    return SimpleNamespace(vad=None, stt=None, tts=SimpleNamespace(sample_rate=24000), aclose=aclose)


def test_outbound_room_stops_waiting_when_the_room_closes():
    # Cortada por la API antes de que entre el usuario (se borra la room): no espera el join_timeout entero.
    room = FakeRoom()
    line = direct.OutboundRoom(SimpleNamespace(room=room), fake_voice(), trunk_id="t", voice_name="sofia")

    async def run():
        task = asyncio.create_task(line.wait_for("user-1", 60))
        await asyncio.sleep(0.05)
        room.connected = False
        return await asyncio.wait_for(task, 2)

    assert asyncio.run(run()) is False


def test_team_room_kicks_a_released_user_and_lets_go_of_the_room():
    async def run():
        room, removed = FakeRoom(), []
        line = direct.TeamRoom(fake_ctx(room, removed), fake_voice(), customer=CUSTOMER, trunk_id="t", caller_id="",
                               voice_name="sofia")
        # Lo que registra RoomLine.start (sin publicar pistas).
        line._handlers = [("participant_connected", line._on_joined), ("track_subscribed", line._on_subscribed)]
        for event, fn in line._handlers:
            room.on(event, fn)
        await line.block("user-ana")                     # todavia no entro: nada que sacar
        await line.aclose()                              # respaldo al agente: la room sigue con el worker
        assert room.handlers["participant_connected"] == [line._on_blocked_join]
        assert room.handlers["track_subscribed"] == [] and room.handlers["disconnected"] == []
        # Entra tarde con el token de answer: se lo saca; otro participante no.
        for identity in ("user-ana", "persona-1"):
            p = SimpleNamespace(identity=identity)
            room.remote_participants[identity] = p
            room.emit("participant_connected", p)
        await asyncio.sleep(0.05)
        return removed

    assert asyncio.run(run()) == ["user-ana"]


def test_listener_flushes_the_last_phrase_when_the_track_ends(monkeypatch):
    # Corta en medio de una frase (sin los 0,3 s de silencio): al terminar la pista se le pasa silencio al VAD y
    # se espera su STT; settle() espera a que llegue.
    pushed: list[bytes] = []

    class Stream:
        def __init__(self):
            self.queue: asyncio.Queue = asyncio.Queue()

        def push_frame(self, frame):
            pushed.append(bytes(frame.data))

        def end_input(self):
            speech = [rtc.AudioFrame(PCM, 16000, 1, len(PCM) // 2)]
            self.queue.put_nowait(SimpleNamespace(type=agents_vad.VADEventType.END_OF_SPEECH, frames=speech))
            self.queue.put_nowait(None)

        def __aiter__(self):
            return self

        async def __anext__(self):
            ev = await self.queue.get()
            if ev is None:
                raise StopAsyncIteration
            return ev

    async def frames(track, **_):
        yield SimpleNamespace(frame=rtc.AudioFrame(PCM, 16000, 1, len(PCM) // 2))

    async def recognize(frames, language=None):
        return SimpleNamespace(alternatives=[SimpleNamespace(text="Chau")])

    monkeypatch.setattr(rtc, "AudioStream", frames)
    heard: list[tuple] = []
    listener = Listener(SimpleNamespace(stream=Stream), SimpleNamespace(recognize=recognize),
                        lambda who, text, pcm: heard.append((who, text)))
    listener.listening.add("contact")

    async def run():
        listener.capture(None, "contact")
        await listener.settle("contact", 2)

    asyncio.run(run())
    assert heard == [("contact", "Chau")]
    assert pushed[0] == PCM and set(pushed[1:]) == {bytes(320)} and len(pushed) == 1 + 60
