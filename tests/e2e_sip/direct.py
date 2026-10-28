"""Llamadas directas de punta a punta contra el Anura falso (`make e2e-sip`, docs/LLAMADAS_DIRECTAS_PLAN.md).

Corre el codigo real de app/voice/direct.py (Outbound/OutboundRoom y TeamCall/TeamRoom, con Transfer y RoomLine de
la derivacion) sobre el LiveKit, livekit-sip y nuestro Asterisk aislados, con una base SQLite propia. Sin
inferencia: el TTS es un tono, el VAD es por energia y el STT devuelve "(voz)" por frase (alcanza para ver los
mensajes con su WAV). Casos:

1. Saliente: el usuario del panel ("user-u1") entra y publica un tono; el worker marca al Anura falso (un eco),
   el contacto atiende, el usuario escucha su tono de vuelta (audio en los dos sentidos), hay mensajes de los dos
   lados con su WAV y, al salir el usuario, la llamada queda finalizada.
2. Entrante al equipo por celular: con un "cliente" ya en la room, suenan las personas del numero en orden (la
   primera da ocupado, la segunda atiende y marca 1), quedan conectadas y termina cuando corta la persona.
"""
import asyncio
import contextlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from livekit.agents import vad as agents_vad
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, "/e2e")
import smoke

from app.config import settings
from app.conversation.models import ConversationState
from app.conversation.store import ConversationStore
from app.db import Base
from app.models import (
    CallMode,
    CallRow,
    CallStatus,
    Client,
    HandoffLeg,
    PhoneNumber,
    TeamMember,
    Tier,
    User,
)
from app.services.calls import TeamPerson, TeamRoute
from app.voice import direct
from app.voice import handoff as transfer
from livekit import api, rtc

TTS_RATE = 24000
ECHO = "+5493510000008"           # atiende y devuelve lo que escucha
CUSTOMER_PHONE = "+5493519999999"  # cualquier otro numero: atiende y habla


def tone(seconds: float, rate: int, hz: int = 440) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    return (np.sin(2 * np.pi * hz * t) * 8000).astype(np.int16).tobytes()


class ToneStream:
    def __init__(self, seconds: float):
        self.pcm = tone(seconds, TTS_RATE)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self._frames()

    async def _frames(self):
        step = TTS_RATE // 10 * 2
        for i in range(0, len(self.pcm), step):
            chunk = self.pcm[i:i + step]
            yield SimpleNamespace(frame=rtc.AudioFrame(chunk, TTS_RATE, 1, len(chunk) // 2))


class EnergyVadStream:
    """Fin de habla tras 0,4 s de silencio o 1,5 s de voz seguida (el silero real necesita voz, no un tono)."""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.frames: list = []
        self.voiced = self.silence = 0.0

    def push_frame(self, frame):
        seconds = frame.samples_per_channel / frame.sample_rate
        rms = float(np.sqrt(np.mean(np.frombuffer(bytes(frame.data), np.int16).astype(np.float32) ** 2)))
        if rms > 300:
            self.frames.append(frame)
            self.voiced += seconds
            self.silence = 0.0
        elif self.frames:
            self.frames.append(frame)
            self.silence += seconds
        if self.frames and (self.silence >= 0.4 or self.voiced >= 1.5):
            self.queue.put_nowait(SimpleNamespace(type=agents_vad.VADEventType.END_OF_SPEECH, frames=self.frames))
            self.frames, self.voiced, self.silence = [], 0.0, 0.0

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.queue.get()


async def recognize(frames, language=None):
    return SimpleNamespace(alternatives=[SimpleNamespace(text="(voz)")])


def fake_voice() -> direct.Voice:
    return direct.Voice(SimpleNamespace(stream=EnergyVadStream), SimpleNamespace(recognize=recognize),
                        SimpleNamespace(sample_rate=TTS_RATE, synthesize=lambda text: ToneStream(1.0)))


def setup_db():
    engine = create_engine("sqlite:////tmp/e2e-direct.db")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as s:
        tier = Tier(name="e2e", direct_calls=True)
        s.add(tier)
        s.flush()
        client = Client(name="E2E", slug="e2e", tier_id=tier.id)
        s.add(client)
        s.flush()
        user = User(email="ana@e2e.com", password_hash="x", role="client", client_id=client.id, name="Ana")
        number = PhoneNumber(e164=smoke.FROM_NUMBER, client_id=client.id)
        s.add_all([user, number])
        s.flush()
        members = []
        for name, phone in (("Ocupado", "+5493510000002"), ("Pedro", "+5493510000001")):
            m = TeamMember(client_id=client.id, name=name, phone=phone)
            s.add(m)
            s.flush()
            members.append(TeamPerson(member_id=m.id, name=name, phone=phone, user_id=None))
        s.commit()
        return sessions, client.id, user.id, number.id, members


def new_call(sessions, client_id: str, conv: str, mode: str, phone: str, number_id: str, user_id=None) -> None:
    with sessions() as s:
        ConversationStore.add(s, ConversationState(conversation_id=conv, agent_id="", client_id=client_id,
                                                   fields={}))
        s.flush()
        s.add(CallRow(conversation_id=conv, client_id=client_id, mode=mode, phone=phone, phone_number_id=number_id,
                      user_id=user_id, status=CallStatus.en_curso if mode == CallMode.entrante else CallStatus.sonando))
        s.commit()


async def join(name: str, identity: str) -> rtc.Room:
    room = rtc.Room()
    token = (api.AccessToken(smoke.KEY, smoke.SECRET).with_identity(identity)
             .with_grants(api.VideoGrants(room_join=True, room=name, can_publish_data=True)).to_jwt())
    await room.connect(smoke.URL, token)
    return room


def peaks(room: rtc.Room, out: dict) -> None:
    def on_track(track, pub, p):
        async def read():
            async for e in rtc.AudioStream(track, sample_rate=16000, num_channels=1):
                data = np.frombuffer(bytes(e.frame.data), np.int16)
                out[p.identity] = max(out.get(p.identity, 0), int(np.abs(data).max(initial=0)))
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.create_task(read())
    room.on("track_subscribed", on_track)


async def outbound(lk, trunk_id, sessions, client_id, user_id, number_id) -> None:
    conv, name = "d1", "e2e-direct-out"
    new_call(sessions, client_id, conv, CallMode.directa, ECHO, number_id, user_id)
    store = ConversationStore(sessions)
    worker = await join(name, "agente")
    user = await join(name, f"user-{user_id}")
    heard: dict = {}
    peaks(user, heard)
    states: list[str] = []
    user.on("data_received", lambda d: states.append(json.loads(d.data)["state"]) if d.topic == "call_status" else None)
    mic = transfer.Speaker("mic", 48000)
    await mic.publish(user)
    await mic.play(tone(1.0, 48000, 330) + b"\x00\x00" * 24000, loop=True)   # 1 s de tono, 0,5 s de silencio
    line = direct.OutboundRoom(SimpleNamespace(room=worker, api=lk), fake_voice(), trunk_id=trunk_id,
                               voice_name="e2e")
    metadata = {"conversation_id": conv, "direct": True, "phone": ECHO, "from_number": smoke.FROM_NUMBER,
                "user_identity": f"user-{user_id}", "user_name": "Ana", "max_duration_seconds": 60,
                "join_timeout_seconds": 10, "recording_notice": True, "voice": "e2e"}
    out = direct.Outbound(sessions=sessions, store=store, line=line, metadata=metadata)
    t = time.monotonic()
    try:
        await line.start()
        task = asyncio.create_task(out.run())
        deadline = time.monotonic() + 20
        while "active" not in states and time.monotonic() < deadline and not task.done():
            await asyncio.sleep(0.2)
        await asyncio.sleep(2)           # el aviso de grabacion (1 s de tono) a los dos
        heard.clear()                    # desde aca, lo que vuelve del contacto es el tono del usuario (eco)
        await asyncio.sleep(4)
        await mic.stop()
        await user.disconnect()          # corta el usuario
        result = await asyncio.wait_for(task, 15)
        await asyncio.sleep(0.5)
        with sessions() as s:
            call = s.get(CallRow, conv)
            status, reason, started = call.status, call.ended_reason, call.started_at
        msgs = store.get(conv).messages
        roles = sorted({(m.role, m.person) for m in msgs if m.recording}, key=str)
        live = {p.identity for p in (await lk.room.list_participants(
            api.ListParticipantsRequest(room=name))).participants}
        ok = result == "completed" and status == CallStatus.finalizada and reason == "person_hangup" and started \
            and roles == [("assistant", "Ana"), ("user", None)] and heard.get("contact", 0) > 500 \
            and states[:2] == ["joining", "dialing"] and "active" in states
        smoke.check("directa saliente: atiende, audio de ida y vuelta, corta el usuario", ok,
                    f"{result}/{status}/{reason} en {time.monotonic() - t:.1f} s; estados {states}; "
                    f"mensajes con WAV {roles} ({len(msgs)}); audio del contacto {heard.get('contact', 0)}; "
                    f"en la room {sorted(live)}")
    finally:
        await line.aclose()
        await worker.disconnect()
        with contextlib.suppress(api.TwirpError):
            await lk.room.delete_room(api.DeleteRoomRequest(room=name))


async def inbound_by_phone(lk, trunk_id, sessions, client_id, number_id, members) -> None:
    conv, name = "d2", "e2e-direct-team"
    new_call(sessions, client_id, conv, CallMode.entrante, CUSTOMER_PHONE, number_id)
    store = ConversationStore(sessions)
    worker = await join(name, "agente")
    result, status, _ = await smoke.dial(lk, trunk_id, name, CUSTOMER_PHONE, "cliente", ring=8)
    assert result == "answered", (result, status)
    deadline = time.monotonic() + 5
    while not any(p.identity == "cliente" and p.track_publications for p in worker.remote_participants.values()):
        if time.monotonic() > deadline:
            raise RuntimeError("el cliente no publico su pista")
        await asyncio.sleep(0.1)
    line = direct.TeamRoom(SimpleNamespace(room=worker, api=lk), fake_voice(), customer="cliente", trunk_id=trunk_id,
                           caller_id=smoke.FROM_NUMBER, voice_name="e2e")
    route = TeamRoute(members=members, ring_first="phone", ring_seconds=6, schedule=None, fallback="hangup",
                      fallback_message="", agent_id=None, number_e164=smoke.FROM_NUMBER, number_label="Ventas")
    team = direct.TeamCall(sessions=sessions, store=store, line=line, conversation_id=conv, client_id=client_id,
                           route=route, customer="cliente", caller=CUSTOMER_PHONE, confirm_seconds=4)
    t = time.monotonic()
    try:
        await line.start()
        outcome = await asyncio.wait_for(team.run(), 60)
        await asyncio.sleep(1)
        with sessions() as s:
            legs = [(leg.result, leg.sip_status, leg.billed_seconds > 0)
                    for leg in s.scalars(select(HandoffLeg).where(HandoffLeg.conversation_id == conv)
                                         .order_by(HandoffLeg.created_at))]
        msgs = store.get(conv).messages
        persons = {(m.role, m.person) for m in msgs if m.recording}
        live = {p.identity for p in (await lk.room.list_participants(
            api.ListParticipantsRequest(room=name))).participants}
        ok = outcome == "answered" and team.reason == "person_hangup" and \
            [r[:2] for r in legs] == [("busy", 486), ("connected", None)] and legs[1][2] and \
            ("assistant", "Pedro") in persons and "cliente" in live and \
            not any(x.startswith(transfer.PERSON_PREFIX) for x in live)
        smoke.check("directa entrante al equipo: ocupado, atiende y marca 1, corta la persona", ok,
                    f"{outcome}/{team.reason} en {time.monotonic() - t:.1f} s; tramos {legs}; "
                    f"mensajes con WAV {sorted(persons, key=str)}; en la room {sorted(live)}")
    finally:
        await line.aclose()
        await worker.disconnect()
        with contextlib.suppress(api.TwirpError):
            await lk.room.delete_room(api.DeleteRoomRequest(room=name))


async def main() -> int:
    # Los WAV, fuera del codigo montado (solo lectura).
    settings.call_recordings_dir = Path("/tmp/e2e-direct/recordings")
    settings.notice_audio_dir = Path("/tmp/e2e-direct/notices")
    # Corta el usuario del panel: sin los 30 s de espera a que vuelva a entrar (recargo la pagina).
    direct.PANEL_REJOIN_GRACE_SECONDS = 1
    lk = api.LiveKitAPI(smoke.URL.replace("ws", "http", 1), smoke.KEY, smoke.SECRET)
    await smoke.wait_ready(lk)
    trunk_id = await smoke.trunk(lk)
    await asyncio.sleep(3)
    sessions, client_id, user_id, number_id, members = setup_db()
    await outbound(lk, trunk_id, sessions, client_id, user_id, number_id)
    await inbound_by_phone(lk, trunk_id, sessions, client_id, number_id, members)
    await lk.aclose()

    failed = [n for n, ok, _ in smoke.RESULTS if not ok]
    print(f"\n{len(smoke.RESULTS) - len(failed)}/{len(smoke.RESULTS)} casos OK"
          + (f"; fallaron: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.stdout.flush()
    # Sin el cierre normal: al recolectar los handles el SDK de LiveKit imprime AssertionError de mas.
    os._exit(code)
