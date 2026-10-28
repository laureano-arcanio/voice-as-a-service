"""Transferencia de punta a punta contra el Anura falso (`make e2e-sip`, docs/features/EQUIPO_TELEFONIA.md).

Corre el codigo real de la derivacion (app/voice/handoff.py: Transfer y RoomLine) sobre el LiveKit, livekit-sip
y nuestro Asterisk aislados, con una base SQLite propia. Sin inferencia: el TTS es un tono, el STT no devuelve
texto (la deteccion de contestador por frases se prueba en tests/test_handoff_transfer.py) y el "agente" es una
pista propia. Casos:

1. Ocupado y despues atiende, marca 1, habla y marca 2: conectada y vuelta a la IA, el cliente sigue en linea.
2. No atiende, atiende y corta durante el whisper, atiende y no marca: no se conecta y el agente vuelve.
"""
import asyncio
import contextlib
import os
import sys
import time
from types import SimpleNamespace

import numpy as np
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, "/e2e")
import smoke

from app.db import Base
from app.models import (
    Client,
    Event,
    HandoffArea,
    HandoffAreaMember,
    HandoffLeg,
    TeamMember,
    Tier,
)
from app.voice import handoff as transfer
from livekit import api, rtc

TTS_RATE = 24000
CUSTOMER_PHONE = "+5493519999999"   # cualquier otro numero del Anura falso: atiende y habla


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


class SilentVadStream:
    def push_frame(self, frame):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.Event().wait()


class FakeSession:
    """Lo que RoomLine usa de la AgentSession: TTS (un tono), STT (sin texto), VAD, say e input."""

    def __init__(self, voice: transfer.Speaker):
        self.voice = voice
        self.said: list[str] = []
        self.audio_enabled: list[bool] = []
        self.tts = SimpleNamespace(sample_rate=TTS_RATE, synthesize=lambda text: ToneStream(1.5))
        self.stt = SimpleNamespace(recognize=self._recognize)
        self.vad = SimpleNamespace(stream=SilentVadStream)
        self.input = SimpleNamespace(set_audio_enabled=self.audio_enabled.append)

    async def _recognize(self, frames, language=None):
        return SimpleNamespace(alternatives=[])

    def say(self, text, **kw):
        self.said.append(text)
        task = asyncio.ensure_future(self.voice.play(tone(1.0, TTS_RATE, 660)))

        async def wait_for_playout():
            await (await task)
        return SimpleNamespace(wait_for_playout=wait_for_playout)


def setup_db():
    engine = create_engine("sqlite:////tmp/e2e-transfer.db")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as s:
        tier = Tier(name="e2e")
        s.add(tier)
        s.flush()
        client = Client(name="E2E", slug="e2e", tier_id=tier.id)
        s.add(client)
        s.flush()
        areas = {}
        for name, phones in (("Ventas", ["+5493510000002", "+5493510000001"]),
                             ("Posventa", ["+5493510000003", "+5493510000007", "+5493510000006"])):
            area = HandoffArea(client_id=client.id, name=name, ring_seconds=4)
            s.add(area)
            s.flush()
            for i, phone in enumerate(phones):
                member = TeamMember(client_id=client.id, name=f"{name} {i + 1}", phone=phone)
                s.add(member)
                s.flush()
                s.add(HandoffAreaMember(area_id=area.id, member_id=member.id, position=i))
            areas[name] = {"id": area.id, "name": name, "when": "", "schedule": None, "schedule_text": ""}
        s.commit()
        return sessions, client.id, areas


async def call_with_customer(lk, trunk_id, name: str):
    """Room con el "agente" (pista de voz propia) y el cliente ya atendido."""
    room = rtc.Room()
    token = (api.AccessToken(smoke.KEY, smoke.SECRET).with_identity("agente")
             .with_grants(api.VideoGrants(room_join=True, room=name)).to_jwt())
    await room.connect(smoke.URL, token)
    voice = transfer.Speaker("agente", TTS_RATE)
    await voice.publish(room)
    result, status, _ = await smoke.dial(lk, trunk_id, name, CUSTOMER_PHONE, "cliente", ring=8)
    assert result == "answered", (result, status)
    deadline = time.monotonic() + 5
    while not any(p.identity == "cliente" and p.track_publications for p in room.remote_participants.values()):
        if time.monotonic() > deadline:
            raise RuntimeError("el cliente no publico su pista")
        await asyncio.sleep(0.1)
    return room, voice


async def case(lk, trunk_id, sessions, client_id, areas, area: str, conv: str):
    room, voice = await call_with_customer(lk, trunk_id, f"e2e-transfer-{conv}")
    session = FakeSession(voice)
    line = transfer.RoomLine(SimpleNamespace(room=room, api=lk), session, customer="cliente", trunk_id=trunk_id,
                             caller_id=smoke.FROM_NUMBER, hold_music=SimpleNamespace(track="default", volume=0.3),
                             max_call_seconds=120)
    said: list[tuple] = []
    tr = transfer.Transfer(sessions=sessions, line=line, conversation_id=conv, client_id=client_id,
                           areas=list(areas.values()), customer="cliente", caller=CUSTOMER_PHONE,
                           confirm_seconds=4, on_message=lambda role, text, **k: said.append((role, text)))
    t = time.monotonic()
    try:
        await line.start()
        outcome = await tr.run(area)
        await asyncio.sleep(1)
        live = {p.identity for p in (await lk.room.list_participants(
            api.ListParticipantsRequest(room=room.name))).participants}
        with sessions() as s:
            legs = [(leg.result, leg.sip_status, leg.billed_seconds > 0)
                    for leg in s.scalars(select(HandoffLeg).where(HandoffLeg.conversation_id == conv)
                                         .order_by(HandoffLeg.created_at))]
            types = [e.type for e in s.scalars(select(Event).where(Event.conversation_id == conv).order_by(Event.id))]
        return outcome, legs, types, live, session.said, round(time.monotonic() - t, 1)
    finally:
        await line.aclose()
        await room.disconnect()
        with contextlib.suppress(api.TwirpError):   # ya no estaba
            await lk.room.delete_room(api.DeleteRoomRequest(room=room.name))


async def main() -> int:
    lk = api.LiveKitAPI(smoke.URL.replace("ws", "http", 1), smoke.KEY, smoke.SECRET)
    await smoke.wait_ready(lk)
    trunk_id = await smoke.trunk(lk)
    await asyncio.sleep(3)
    sessions, client_id, areas = setup_db()

    outcome, legs, types, live, said, secs = await case(lk, trunk_id, sessions, client_id, areas, "Ventas", "c1")
    ok = (outcome.status, outcome.ended) == ("connected", "returned_to_ai") and \
        [r[:2] for r in legs] == [("busy", 486), ("connected", None)] and legs[1][2] and \
        "cliente" in live and not any(x.startswith(transfer.PERSON_PREFIX) for x in live) and \
        said[-1] == "¿Te puedo ayudar con algo más?" and "handoff.returned_to_ai" in types
    smoke.check("derivacion: ocupado, atiende, 1 y 2", ok,
                f"{outcome.status}/{outcome.ended} en {secs} s; tramos {legs}; en la room {sorted(live)}; dijo {said}")

    outcome, legs, types, live, said, secs = await case(lk, trunk_id, sessions, client_id, areas, "Posventa", "c2")
    ok = outcome.status == "failed" and [r[0] for r in legs] == ["no_answer", "not_confirmed", "not_confirmed"] \
        and not any(r[2] for r in legs) and "cliente" in live and said[-1].startswith("No pude comunicarte")
    smoke.check("derivacion: no atiende, corta, no marca", ok,
                f"{outcome.status}/{outcome.result} en {secs} s; tramos {legs}; en la room {sorted(live)}")
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
