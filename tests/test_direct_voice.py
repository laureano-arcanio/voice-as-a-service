"""Llamadas directas en el worker (app/voice/direct.py y app/voice/listen.py, docs/features/EQUIPO_TELEFONIA.md):
la logica con lineas falsas, sin LiveKit ni inferencia. La API y el ruteo estan en tests/test_direct_calls.py."""
import asyncio
import datetime
import time
import wave
from types import SimpleNamespace

import pytest
from livekit.agents import vad as agents_vad

from app.config import settings
from app.models import CallRing, CallRow, CallStatus, ConversationRow, Event, HandoffLeg, PhoneNumber
from app.services import calls as call_service
from app.services import direct_calls
from app.voice import direct
from app.voice import handoff as transfer
from app.voice.listen import Listener
from livekit import rtc

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)
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

    async def dial(self, identity, phone, caller_id, ring_seconds, max_seconds, headers):
        self.log.append(("dial", identity, phone, caller_id))
        self.headers = headers
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


def test_outbound_full_call_header_only_with_the_option(api, admin, monkeypatch, tmp_path):
    """Grabacion completa: X-Atentina-Rec en la pierna del contacto solo si el numero de origen la tiene."""
    meta, _, new = outbound(api, admin, monkeypatch, tmp_path)
    assert meta["record_full_call"] is False
    line = FakeOut(dial="busy")
    run_out(api, meta, line)
    assert line.headers == {}
    with api.sessions() as s:
        s.query(PhoneNumber).update({"record_full_call": True})
        s.commit()
    meta = new()
    assert meta["record_full_call"] is True
    line = FakeOut(dial="busy")
    run_out(api, meta, line)
    assert line.headers == {"X-Atentina-Rec": meta["conversation_id"]}


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
    r = admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"answer_mode": "team", "member_ids": ids, **number})
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


def backup_person(api, admin, c, inbound, **number):
    """Luis, fuera del numero, como «si nadie atiende» (team_fallback member); otra entrante que ya lo lee."""
    luis = member(admin, c["id"], name="Luis", phone="3513333333")
    r = admin.patch(f"{V1}/phone-numbers/{inbound.team.number_id}",
                    json={"team_fallback": "member", "team_fallback_member_id": luis["id"], **number})
    assert r.status_code == 200, r.text
    return luis, next_inbound(api)


def test_team_nobody_answers_the_backup_person_answers(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    luis, inbound = backup_person(api, admin, c, inbound, strategy="round_robin")
    cid = inbound.conversation_id
    line = TeamLine({JUAN: "no_answer", LUIS: "confirm"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert dialed(line) == [JUAN, LUIS]
    # Con la misma musica de espera y el mismo whisper que los celulares del numero.
    assert [x for x in line.log if x[0] == "hold"] == [("hold", True), ("hold", False), ("hold", True),
                                                       ("hold", False), ("hold", False)]
    assert all(x[1].startswith("Llamada a la línea") for x in line.log if x[0] == "whisper")
    # No entra en la rotacion del numero.
    assert last_member(api, inbound.team.number_id) is None
    with api.sessions() as s:
        assert [(leg.result, leg.area_id) for leg in s.query(HandoffLeg).filter_by(conversation_id=cid)
                .order_by(HandoffLeg.phone)] == [("no_answer", None), ("connected", None)]
        fallbacks = [e.data["fallback"] for e in s.query(Event).filter_by(conversation_id=cid, type="team.fallback")]
    assert fallbacks == ["member"]
    assert team_outcome(admin, cid) == {"answered": True, "person": "Luis", "fallback": None}


def test_team_backup_person_does_not_answer_voicemail(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    luis, inbound = backup_person(api, admin, c, inbound, team_fallback_message="Dejanos tu mensaje.")
    cid = inbound.conversation_id
    line = TeamLine({JUAN: "no_answer", LUIS: "busy"}, on_listen=[("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "voicemail" and team.reason == "team_no_answer"
    assert dialed(line) == [JUAN, LUIS] and ("say", "Dejanos tu mensaje.") in line.log
    with api.sessions() as s:
        fallbacks = [e.data["fallback"] for e in s.query(Event).filter_by(conversation_id=cid, type="team.fallback")
                     .order_by(Event.id)]
    assert fallbacks == ["member", "voicemail"]
    assert team_outcome(admin, cid) == {"answered": False, "person": None, "fallback": "voicemail"}

    # Inactiva: no se la llama, buzon directo.
    admin.patch(f"{V1}/team/{luis['id']}", json={"active": False})
    inbound = next_inbound(api)
    assert inbound.team.fallback_member is None
    line = TeamLine({JUAN: "no_answer"}, on_listen=[("left", CUSTOMER)])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "voicemail"
    assert dialed(line) == [JUAN]


def test_team_after_hours_calls_the_backup_person(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    luis, inbound = backup_person(api, admin, c, inbound, schedule={"week": {}})
    line = TeamLine({LUIS: "confirm"}, connected=[("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "customer_hangup"
    assert dialed(line) == [LUIS]
    with api.sessions() as s:
        events = [(e.type, (e.data or {}).get("reason")) for e in s.query(Event).filter_by(
            conversation_id=inbound.conversation_id, type="team.fallback")]
    assert events == [("team.fallback", "after_hours")]

    # El que llama corta mientras le suena a Luis: termina como customer_hung_up, sin buzon.
    inbound = next_inbound(api)
    line = TeamLine({LUIS: "silent"})
    line.events.put_nowait(("left", CUSTOMER))
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "customer_hung_up" and team.reason == "customer_hangup"
    assert not [x for x in line.log if x[0] == "say"]


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


class WatchedLine(TeamLine):
    """TeamLine que anota si se busco el contestador (first_words)."""

    async def first_words(self, identity, seconds):
        self.log.append(("first_words", identity))
        return await super().first_words(identity, seconds)


def team_events(api, cid):
    with api.sessions() as s:
        return [(e.type, e.data) for e in s.query(Event).filter(Event.conversation_id == cid,
                                                                Event.type.not_like("call.%")).order_by(Event.id)]


def test_team_connect_on_answer_skips_the_whisper_and_the_1(api, admin, monkeypatch, tmp_path):
    # Conectar al atender: Juan da ocupado, Pedro atiende y no marca nada (una central): queda conectado sin whisper
    # ni busqueda de contestador, con lo que habla cada uno grabado y Pedro como el ultimo que atendio.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None),
                               ("Pedro", "3512222222", None), team_connect_on_answer=True)
    cid = inbound.conversation_id
    assert inbound.team.connect_on_answer is True and inbound.team.hold_music is True
    line = WatchedLine({"+5493511111111": "busy", "+5493512222222": "silent"},
                       on_listen=[("text", "persona-2", "La Estrella, buenos días", PCM),
                                  ("text", CUSTOMER, "Hola, quiero un remis", PCM), ("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "customer_hangup"
    assert not [x for x in line.log if x[0] in ("whisper", "first_words")]
    assert [x for x in line.log if x[0] in ("hold", "dial", "connect")] == [
        ("hold", True), ("dial", "+5493511111111"), ("dial", "+5493512222222"), ("hold", False),
        ("connect", "persona-2"), ("hold", False)]
    assert [(r, t, p) for r, t, p, _ in messages(api, cid)] == [("assistant", "La Estrella, buenos días", "Pedro"),
                                                               ("user", "Hola, quiero un remis", None)]
    with api.sessions() as s:
        legs = s.query(HandoffLeg).order_by(HandoffLeg.created_at).all()
        assert [leg.result for leg in legs] == ["busy", "connected"]
        assert legs[1].answered_at is not None and legs[1].connected_at is not None
        assert s.get(PhoneNumber, inbound.team.number_id).last_member_id == legs[1].team_member_id
    confirmed = [d for t, d in team_events(api, cid) if t == "handoff.confirmed"]
    assert len(confirmed) == 1 and confirmed[0]["auto"] is True
    assert team_outcome(admin, cid) == {"answered": True, "person": "Pedro", "fallback": None}


def test_team_connect_on_answer_connects_a_voicemail_and_falls_back_without_answer(api, admin, monkeypatch,
                                                                                   tmp_path):
    # Sin el 1 no hay deteccion de contestador: el buzon de un celular queda conectado (la opcion es para destinos
    # que siempre atienden). Si no atiende nadie, el respaldo de siempre.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None),
                               team_connect_on_answer=True)
    line = WatchedLine({"+5493512222222": "machine"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert not [x for x in line.log if x[0] in ("whisper", "first_words")]

    inbound = next_inbound(api)
    line = WatchedLine({"+5493512222222": "no_answer"}, on_listen=[("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "voicemail" and team.reason == "team_no_answer"
    assert ("say", direct.FALLBACK_MESSAGES["voicemail"]) in line.log
    assert team_outcome(admin, inbound.conversation_id) == {"answered": False, "person": None, "fallback": "voicemail"}


def test_team_without_hold_music_is_silent(api, admin, monkeypatch, tmp_path):
    # Sin musica: la linea nunca recibe hold(True), ni por telefono ni por panel, y el respaldo dice su mensaje igual.
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Ana", None, "ana"),
                                   ("Pedro", "3512222222", None), team_hold_music=False)
    assert inbound.team.hold_music is False
    line = TeamLine({"+5493512222222": "confirm"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    whisper = ("whisper", "Llamada a la línea de +5493513962553. Marcá 1 para atender.")
    assert ("hold", True) not in line.log and whisper in line.log
    assert not [t for t, _ in team_events(api, inbound.conversation_id) if t.startswith("hold.")]

    # Por el panel (Ana Disponible) y despues el respaldo: sin musica en ningun momento.
    ana, ana_id = users["ana"]
    ana.put(f"{V1}/me/presence", json={"available": True})
    inbound = next_inbound(api)
    cid = inbound.conversation_id
    line = TeamLine({"+5493512222222": "no_answer"}, on_listen=[("left", f"user-{ana_id}")])
    team = team_call(api, c, inbound, line)

    async def run():
        async def ana_answers():
            while not ana.get(f"{V1}/me/ringing").json():
                await asyncio.sleep(0.05)
            await asyncio.to_thread(ana.post, f"{V1}/direct-calls/{cid}/answer")
            line.events.put_nowait(("joined", f"user-{ana_id}"))
        helper = asyncio.create_task(ana_answers())
        result = await team.run()
        await helper
        return result

    assert asyncio.run(run()) == "answered" and ("hold", True) not in line.log

    ana.put(f"{V1}/me/presence", json={"available": False})
    inbound = next_inbound(api)
    line = TeamLine({"+5493512222222": "no_answer"}, on_listen=[("left", CUSTOMER)])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "voicemail" and ("hold", True) not in line.log
    assert ("say", direct.FALLBACK_MESSAGES["voicemail"]) in line.log


def test_team_without_music_and_connect_on_answer(api, admin, monkeypatch, tmp_path):
    # Las dos opciones a la vez: ni musica ni whisper; el pasajero corta mientras suena y el tramo queda cerrado.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None),
                               team_connect_on_answer=True, team_hold_music=False)
    line = WatchedLine({"+5493512222222": "silent"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert not [x for x in line.log if x[0] in ("whisper", "first_words") or x == ("hold", True)]

    class GoneWhileRinging(WatchedLine):
        async def dial(self, identity, phone, ring_seconds):
            self.log.append(("dial", phone))
            self.events.put_nowait(("left", CUSTOMER))
            await asyncio.sleep(5)

    inbound = next_inbound(api)
    line = GoneWhileRinging({})
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "customer_hung_up"
    with api.sessions() as s:
        leg = s.query(HandoffLeg).filter_by(conversation_id=inbound.conversation_id).one()
        assert leg.result == "failed" and leg.ended_at is not None and leg.answered_at is None


def test_team_backup_person_follows_connect_on_answer_and_music(api, admin, monkeypatch, tmp_path):
    # La persona de «si nadie atiende» suena como los telefonos del numero: con conectar al atender y sin musica,
    # atiende y queda conectada sin whisper ni 1, y nunca suena la musica.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    luis, inbound = backup_person(api, admin, c, inbound, team_connect_on_answer=True, team_hold_music=False)
    line = WatchedLine({JUAN: "no_answer", LUIS: "silent"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert dialed(line) == [JUAN, LUIS]
    assert not [x for x in line.log if x[0] in ("whisper", "first_words") or x == ("hold", True)]
    assert team_outcome(admin, inbound.conversation_id) == {"answered": True, "person": "Luis", "fallback": None}


def test_team_connect_on_answer_two_calls_at_once(api, admin, monkeypatch, tmp_path):
    # Dos entrantes a la vez al mismo numero con una sola central: cada una con su tramo conectado.
    c, first, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Central", "3512222222", None),
                             team_connect_on_answer=True)
    second = next_inbound(api)
    lines = [WatchedLine({"+5493512222222": "silent"}, connected=[("left", "PERSON")]) for _ in range(2)]
    teams = [team_call(api, c, inbound, line) for inbound, line in zip((first, second), lines)]

    async def both():
        return await asyncio.gather(*(t.run() for t in teams))

    assert asyncio.run(both()) == ["answered", "answered"]
    with api.sessions() as s:
        for inbound in (first, second):
            leg = s.query(HandoffLeg).filter_by(conversation_id=inbound.conversation_id).one()
            assert leg.result == "connected" and leg.ended_at is not None


def next_inbound(api):
    """Otra entrante al mismo numero (lee la estrategia y la ultima que atendio)."""
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493513962553")
        call_service.update_call(s, inbound.conversation_id, status=CallStatus.en_curso)
    inbound.team.ring_seconds = 1
    return inbound


def dialed(line):
    return [x[1] for x in line.log if x[0] == "dial"]


def last_member(api, number_id):
    with api.sessions() as s:
        return s.get(PhoneNumber, number_id).last_member_id


THREE = (("Juan", "3511111111", None), ("Pedro", "3512222222", None), ("Luis", "3513333333", None))
JUAN, PEDRO, LUIS = "+5493511111111", "+5493512222222", "+5493513333333"


@pytest.mark.parametrize("strategy, second", [("round_robin", [LUIS]), ("sequential", [JUAN, PEDRO])])
def test_team_phone_order_by_strategy(api, admin, monkeypatch, tmp_path, strategy, second):
    # Juan no atiende y Pedro marca 1: queda como la ultima. Rotativa: la siguiente entrante empieza por Luis;
    # en orden, otra vez por Juan.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, *THREE, strategy=strategy)
    number_id = inbound.team.number_id
    line = TeamLine({JUAN: "no_answer", PEDRO: "confirm"}, connected=[("left", "PERSON")])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "answered"
    assert dialed(line) == [JUAN, PEDRO]
    member_ids = [p.member_id for p in inbound.team.members]
    assert last_member(api, number_id) == member_ids[1]

    inbound = next_inbound(api)
    line = TeamLine({JUAN: "no_answer", PEDRO: "confirm", LUIS: "confirm"}, connected=[("left", "PERSON")])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "answered"
    assert dialed(line) == second
    # Se anota siempre, sin mirar la estrategia (pasar a Rotativa despues sigue a la ultima real).
    assert last_member(api, number_id) == member_ids[2 if strategy == "round_robin" else 1]


def test_team_panel_rings_everyone_then_the_phones_rotate(api, admin, monkeypatch, tmp_path):
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Ana", "3511111111", "ana"),
                                   ("Pedro", "3512222222", "pedro"), ring_first="panel", strategy="round_robin")
    ana_member = inbound.team.members[0].member_id
    with api.sessions() as s:
        s.get(PhoneNumber, inbound.team.number_id).last_member_id = ana_member
        s.commit()
    inbound = next_inbound(api)
    for u, _ in users.values():
        u.put(f"{V1}/me/presence", json={"available": True})
    # El panel suena a las dos a la vez (nadie atiende); despues los celulares, desde Pedro.
    line = TeamLine({"+5493511111111": "confirm", "+5493512222222": "confirm"}, connected=[("left", "PERSON")])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "answered"
    with api.sessions() as s:
        rung = {r.user_id for r in s.query(CallRing).filter_by(conversation_id=inbound.conversation_id)}
    assert rung == {users["ana"][1], users["pedro"][1]}
    assert dialed(line) == ["+5493512222222"]
    assert last_member(api, inbound.team.number_id) == inbound.team.members[0].member_id != ana_member


def test_team_marking_the_last_one_never_cuts_the_call(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None),
                               strategy="round_robin")
    number_id = inbound.team.number_id
    # Un error de base al anotar: se loguea y la llamada sigue.
    monkeypatch.setattr(direct, "TeamMember", object())
    line = TeamLine({"+5493512222222": "confirm"}, connected=[("text", "PERSON", "Hola"), ("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert [m[1] for m in messages(api, inbound.conversation_id)] == ["Hola"]
    assert last_member(api, number_id) is None


def test_team_number_reassigned_mid_call_is_not_marked(api, admin, monkeypatch, tmp_path):
    # Liberaron el numero (o paso a otro cliente) con la llamada sonando: no se anota una persona de este cliente.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None),
                               strategy="round_robin")
    number_id = inbound.team.number_id
    other = make_client(admin, slug="otro")
    with api.sessions() as s:
        s.get(PhoneNumber, number_id).client_id = other["id"]
        s.commit()
    line = TeamLine({"+5493512222222": "confirm"}, connected=[("left", "PERSON")])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "answered"
    assert last_member(api, number_id) is None


def test_team_person_deleted_mid_call_is_not_marked(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Pedro", "3512222222", None),
                               strategy="round_robin")
    admin.delete(f"{V1}/team/{inbound.team.members[0].member_id}")
    line = TeamLine({"+5493512222222": "confirm"}, connected=[("left", "PERSON")])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "answered"
    assert last_member(api, inbound.team.number_id) is None


# ---------- reintentos (team_retry_*) ----------

class RetryLine(TeamLine):
    """TeamLine en la que cada telefono hace algo distinto en cada intento (una lista; el ultimo se repite)."""

    def __init__(self, script, **kw):
        self.plans = {k: list(v) if isinstance(v, list) else [v] for k, v in script.items()}
        super().__init__({k: v[0] for k, v in self.plans.items()}, **kw)

    async def dial(self, identity, phone, ring_seconds):
        plan = self.plans[phone]
        self.script[phone] = plan.pop(0) if len(plan) > 1 else plan[0]
        return await super().dial(identity, phone, ring_seconds)


def with_retries(api, inbound, seconds, interval=0, message="", **row):
    """Reintentos escritos en la fila del numero (sin la API, que exige 15-120 de intervalo) y otra entrante."""
    with api.sessions() as s:
        number = s.get(PhoneNumber, inbound.team.number_id)
        number.team_retry_seconds, number.team_retry_interval_seconds = seconds, interval
        number.team_retry_message = message
        for k, v in row.items():
            setattr(number, k, v)
        s.commit()
    return next_inbound(api)


@pytest.fixture
def waits(monkeypatch):
    """Los segundos que espera cada vez entre intentos (TeamCall._wait)."""
    seen: list[float] = []
    real = direct.TeamCall._wait

    async def spy(self, seconds):
        seen.append(seconds)
        await real(self, seconds)
    monkeypatch.setattr(direct.TeamCall, "_wait", spy)
    return seen


def test_team_retry_busy_then_answers(api, admin, monkeypatch, tmp_path, waits):
    # Juan da ocupado: aviso, musica y al reintento atiende. El aviso no abre las pistas (sin resume).
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    inbound = with_retries(api, inbound, 60)
    assert (inbound.team.retry_seconds, inbound.team.retry_interval_seconds, inbound.team.retry_message) == (60, 0, "")
    cid = inbound.conversation_id
    line = RetryLine({JUAN: ["busy", "confirm"]}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and team.reason == "person_hangup"
    assert waits == [0] and dialed(line) == [JUAN, JUAN] and ("resume",) not in line.log
    assert [x for x in line.log if x[0] in ("hold", "say", "connect")] == [
        ("hold", True), ("hold", False), ("say", direct.RETRY_MESSAGE), ("hold", True), ("hold", False),
        ("connect", "persona-2"), ("hold", False)]
    assert messages(api, cid)[0][:2] == ("assistant", direct.RETRY_MESSAGE)
    events = team_events(api, cid)
    assert ("team.retry", {"seconds": 60}) in events and not [t for t, _ in events if t == "team.fallback"]
    with api.sessions() as s:
        assert [leg.result for leg in s.query(HandoffLeg).filter_by(conversation_id=cid)
                .order_by(HandoffLeg.created_at)] == ["busy", "connected"]
    assert team_outcome(admin, cid) == {"answered": True, "person": "Juan", "fallback": None}


def test_team_retry_until_the_limit_then_the_fallback(api, admin, monkeypatch, tmp_path, waits):
    # 2 s con 1 s de intervalo: un reintento (el siguiente empezaria en el tope) y el respaldo "corta" con su mensaje.
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    inbound = with_retries(api, inbound, 2, 1, "Aguarde en línea, por favor.", team_fallback="hangup",
                           team_fallback_message="No lo hemos podido conectar.")
    cid = inbound.conversation_id
    line = RetryLine({JUAN: "no_answer"})
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "hangup" and team.reason == "team_no_answer"
    assert waits == [1] and dialed(line) == [JUAN, JUAN]
    assert [x[1] for x in line.log if x[0] == "say"] == ["Aguarde en línea, por favor.",
                                                         "No lo hemos podido conectar."]
    fallback = [d for t, d in team_events(api, cid) if t == "team.fallback"]
    assert fallback == [{"fallback": "hangup", "reason": "team_no_answer", "retries": 1}]
    assert team_outcome(admin, cid) == {"answered": False, "person": None, "fallback": "hangup"}


def test_team_retry_customer_hangs_up_while_waiting(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    inbound = with_retries(api, inbound, 60, team_fallback="hangup")

    class HangsUp(RetryLine):
        async def say(self, text, interruptible=False):
            await super().say(text)
            self.events.put_nowait(("left", CUSTOMER))      # corta mientras oye el aviso

    line = HangsUp({JUAN: "busy"})
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "customer_hung_up" and team.reason == "customer_hangup"
    assert dialed(line) == [JUAN] and [x[1] for x in line.log if x[0] == "say"] == [direct.RETRY_MESSAGE]
    assert line.log[-1] == ("hold", False)
    assert not [t for t, _ in team_events(api, inbound.conversation_id) if t == "team.fallback"]

    # Se cierra la room en la espera: igual.
    inbound = next_inbound(api)
    line = RetryLine({JUAN: "busy"})
    line.say = lambda text, interruptible=False: line.events.put_nowait(("closed", "")) or asyncio.sleep(0)
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "customer_hung_up"


def test_team_retry_stops_without_outbound_minutes_but_not_without_a_channel(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    inbound = with_retries(api, inbound, 60, team_fallback="hangup")
    # Sin minutos salientes: no se llama, ni aviso ni reintentos.
    monkeypatch.setattr(transfer.quota, "handoff_check", lambda s, client_id: "outbound_minutes")
    line = RetryLine({JUAN: "confirm"})
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "hangup"
    assert dialed(line) == [] and direct.RETRY_MESSAGE not in [x[1] for x in line.log if x[0] == "say"]
    assert not [t for t, _ in team_events(api, inbound.conversation_id) if t == "team.retry"]

    # Sin canal libre la primera vez: se reintenta y atiende.
    answers = iter(["no_channel"])
    monkeypatch.setattr(transfer.quota, "handoff_check", lambda s, client_id: next(answers, None))
    inbound = next_inbound(api)
    line = RetryLine({JUAN: "confirm"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and dialed(line) == [JUAN] and team.retries == 1


def test_team_retry_stops_without_minutes_or_time(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    inbound = with_retries(api, inbound, 60, team_fallback="hangup")
    # Sin minutos entrantes despues del aviso: termina la etapa sin reintentar.
    monkeypatch.setattr(call_service, "call_remaining_seconds", lambda s, cid: 0)
    line = RetryLine({JUAN: "busy"})
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "hangup" and dialed(line) == [JUAN] and team.retries == 0
    monkeypatch.undo()

    # Cerca del tope de duracion (deja el buzon y los mensajes): sin aviso ni reintentos.
    inbound = next_inbound(api)
    line = RetryLine({JUAN: "busy"})
    team = team_call(api, c, inbound, line)
    team.deadline = time.monotonic() + direct.RETRY_DEADLINE_MARGIN - 1
    assert asyncio.run(team.run()) == "hangup" and dialed(line) == [JUAN] and team.retries is None
    assert [x[1] for x in line.log if x[0] == "say"] == [direct.FALLBACK_MESSAGES["hangup"]]


def test_team_retry_after_hours_and_without_music(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    # Fuera de horario: el respaldo, sin aviso ni intentos.
    line = RetryLine({JUAN: "confirm"})
    team = team_call(api, c, with_retries(api, inbound, 60, team_fallback="hangup", schedule={"week": {}}), line)
    assert asyncio.run(team.run()) == "hangup" and team.reason == "after_hours" and dialed(line) == []
    assert direct.RETRY_MESSAGE not in [x[1] for x in line.log if x[0] == "say"]

    # Sin musica: el aviso igual, y la linea nunca recibe hold.
    inbound = with_retries(api, inbound, 60, team_hold_music=False, schedule=None)
    line = RetryLine({JUAN: ["busy", "confirm"]}, connected=[("left", "PERSON")])
    assert asyncio.run(team_call(api, c, inbound, line).run()) == "answered"
    assert not [x for x in line.log if x[0] == "hold"] and ("say", direct.RETRY_MESSAGE) in line.log


def test_team_retry_keeps_an_attempt_for_the_backup_person(api, admin, monkeypatch, tmp_path):
    # El tope de intentos por llamada (MAX_ATTEMPTS) deja lugar a la persona de "si nadie atiende".
    monkeypatch.setattr(transfer, "MAX_ATTEMPTS", 3)
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    luis, inbound = backup_person(api, admin, c, inbound)
    inbound = with_retries(api, inbound, 60)
    line = RetryLine({JUAN: "busy", LUIS: "confirm"}, connected=[("left", "PERSON")])
    team = team_call(api, c, inbound, line)
    assert asyncio.run(team.run()) == "answered" and dialed(line) == [JUAN, JUAN, LUIS] and team.retries == 1
    fallback = [d for t, d in team_events(api, inbound.conversation_id) if t == "team.fallback"]
    assert fallback == [{"fallback": "member", "reason": "team_no_answer", "retries": 1}]


def test_team_retry_does_not_ring_a_released_panel_user(api, admin, monkeypatch, tmp_path):
    # Atendio en el panel y no entro (block): en los reintentos no se le vuelve a sonar.
    c, inbound, users = team_setup(api, admin, monkeypatch, tmp_path, ("Ana", None, "ana"))
    ana, ana_id = users["ana"]
    ana.put(f"{V1}/me/presence", json={"available": True})
    team = team_call(api, c, inbound, TeamLine())
    team.released.add(ana_id)
    assert asyncio.run(team._panel()) is None
    assert not ana.get(f"{V1}/me/ringing").json()


def test_team_retry_two_calls_at_once(api, admin, monkeypatch, tmp_path):
    c, inbound, _ = team_setup(api, admin, monkeypatch, tmp_path, ("Juan", "3511111111", None))
    first = with_retries(api, inbound, 60)
    second = next_inbound(api)
    lines = [RetryLine({JUAN: ["busy", "busy", "confirm"]}, connected=[("left", "PERSON")]) for _ in range(2)]
    teams = [team_call(api, c, inbound, line) for inbound, line in zip((first, second), lines)]

    async def both():
        return await asyncio.gather(*(t.run() for t in teams))

    assert asyncio.run(both()) == ["answered", "answered"]
    assert [t.retries for t in teams] == [2, 2] and [dialed(x) for x in lines] == [[JUAN] * 3] * 2
    with api.sessions() as s:
        for inbound in (first, second):
            legs = s.query(HandoffLeg).filter_by(conversation_id=inbound.conversation_id).all()
            assert sorted(leg.result for leg in legs) == ["busy", "busy", "connected"]


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


def test_outbound_seconds_stop_when_the_call_is_cut(api, admin, monkeypatch, tmp_path):
    """Los segundos van hasta que corta el contacto: los 90 s simulados de la ultima frase (settle) no suman."""
    from .voice_harness import Clock

    clock = Clock(monkeypatch, direct)
    meta, user, _ = outbound(api, admin, monkeypatch, tmp_path)
    line = FakeOut(dialed=[("joined", direct.CONTACT), ("sip", direct.CONTACT, "active")],
                   talk=[("left", direct.CONTACT, "")])
    real_settle = line.settle

    async def slow_settle(identity, timeout):
        clock.skip(90)
        await real_settle(identity, timeout)

    line.settle = slow_settle
    cut = direct.utcnow()
    assert run_out(api, meta, line) == "completed"
    call = call_row(api, meta["conversation_id"])
    assert call.duration_seconds <= 1 and call.ended_at < cut + datetime.timedelta(seconds=30)
