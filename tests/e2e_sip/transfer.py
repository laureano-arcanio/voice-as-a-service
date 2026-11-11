"""Transferencia de punta a punta contra el Anura falso (`make e2e-sip`, docs/features/EQUIPO_TELEFONIA.md).

Corre el codigo real de la derivacion (app/voice/handoff.py: Transfer y RoomLine) sobre el LiveKit, livekit-sip
y nuestro Asterisk aislados, con una base SQLite propia. Sin inferencia: el TTS es un tono, el STT no devuelve
texto (la deteccion de contestador por frases se prueba en tests/test_handoff_transfer.py) y el "agente" es una
pista propia. Casos:

1. Ocupado y despues atiende, marca 1, habla y marca 2: conectada y vuelta a la IA, el cliente sigue en linea.
2. No atiende, atiende y corta durante el whisper, atiende y no marca: no se conecta y el agente vuelve.
3. Cadena (docs/features/EQUIPO_TELEFONIA.md): un area que nadie atiende pasa a otra por `no_answer_area_id`, con la
   musica de espera continua (una sola vez), sin el mensaje de "no pude comunicarte" en el pase, un solo
   `handoff.rerouted`, el whisper con las variables del pre-call solo a la persona y el post-call armado al conectar.
4. Cadena que termina sin conectar: el post-call no se arma y el cliente oye solo el aviso inicial y el mensaje final.
5. Rutas en ciclo: se corta al volver a un area ya visitada.
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

from app.conversation import workflows
from app.conversation.models import AgentWorkflows, PostCallWorkflow
from app.db import Base
from app.models import (
    CallMode,
    Client,
    ConversationRow,
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

        def make_area(name: str, phones: list[str], **cols) -> HandoffArea:
            area = HandoffArea(client_id=client.id, name=name, ring_seconds=4, **cols)
            s.add(area)
            s.flush()
            for i, phone in enumerate(phones):
                member = TeamMember(client_id=client.id, name=f"{name} {i + 1}", phone=phone)
                s.add(member)
                s.flush()
                s.add(HandoffAreaMember(area_id=area.id, member_id=member.id, position=i))
            areas[name] = {"id": area.id, "name": name, "when": "", "schedule": None, "schedule_text": ""}
            return area

        # Cadena: Guardia (nadie atiende) -> Central (ocupado y despues atiende); Central dice la nota del pre-call.
        central = make_area("Central", ["+5493510000002", "+5493510000001"],
                            messages={"whisper": "Emergencia de {{area}}. {{nota_operador}}. Marcá 1 para atender."})
        make_area("Guardia", ["+5493510000003"], no_answer_area_id=central.id)
        # Cadena que no conecta: Guardia 2 (nadie atiende) -> Silencio (atiende y no marca 1).
        silencio = make_area("Silencio", ["+5493510000006"])
        make_area("Guardia 2", ["+5493510000003"], no_answer_area_id=silencio.id)
        # Ciclo: A -> B -> A.
        a = make_area("Ciclo A", ["+5493510000003"])
        b = make_area("Ciclo B", ["+5493510000003"], no_answer_area_id=a.id)
        a.no_answer_area_id = b.id
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


def post_call_agent() -> SimpleNamespace:
    """Lo unico que `workflows.arm` lee del agente: un post-call `handoff_accepted`."""
    return SimpleNamespace(workflows=AgentWorkflows(post_call=PostCallWorkflow(tool="cobro", when="handoff_accepted")))


async def case(lk, trunk_id, sessions, client_id, areas, area: str, conv: str, *, probe: dict | None = None,
               with_post_call: bool = False, **transfer_kw):
    """probe: si viene, se llena con lo que paso en la linea (musica, whispers), los eventos con sus datos y el
    estado del post-call de la conversacion."""
    room, voice = await call_with_customer(lk, trunk_id, f"e2e-transfer-{conv}")
    session = FakeSession(voice)
    line = transfer.RoomLine(SimpleNamespace(room=room, api=lk), session, customer="cliente", trunk_id=trunk_id,
                             caller_id=smoke.FROM_NUMBER, hold_music=SimpleNamespace(track="default", volume=0.3),
                             max_call_seconds=120)
    holds: list[bool] = []
    whispers: list[tuple[str, str]] = []
    real_hold, real_whisper = line.hold, line.whisper

    async def hold(on):
        holds.append(on)
        await real_hold(on)

    async def whisper(identity, text):
        whispers.append((identity, text))
        await real_whisper(identity, text)
    line.hold, line.whisper = hold, whisper
    if with_post_call:
        with sessions() as s:
            s.add(ConversationRow(id=conv, client_id=client_id, status="active", fields={}, messages=[]))
            s.commit()
        transfer_kw["on_connected"] = lambda member: workflows.arm(sessions, conv, CallMode.entrante,
                                                                   post_call_agent())
    said: list[tuple] = []
    tr = transfer.Transfer(sessions=sessions, line=line, conversation_id=conv, client_id=client_id,
                           areas=list(areas.values()), customer="cliente", caller=CUSTOMER_PHONE,
                           confirm_seconds=4, on_message=lambda role, text, **k: said.append((role, text)),
                           **transfer_kw)
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
            rows = list(s.scalars(select(Event).where(Event.conversation_id == conv).order_by(Event.id)))
            types = [e.type for e in rows]
            if probe is not None:
                post = s.get(ConversationRow, conv)
                probe.update(holds=holds, whispers=whispers, events=[(e.type, e.data) for e in rows],
                             post_call=post.post_call_status if post else None)
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
        and not legs[0][2] and all(r[2] for r in legs[1:]) and "cliente" in live \
        and said[-1].startswith("No pude comunicarte")      # se cobra desde que atiende, acepte o no
    smoke.check("derivacion: no atiende, corta, no marca", ok,
                f"{outcome.status}/{outcome.result} en {secs} s; tramos {legs}; en la room {sorted(live)}")

    async def resumen():
        return "el titular no responde"

    # 3. Cadena con conexion: Guardia no atiende y pasa a Central (ocupado, atiende, marca 1 y 2).
    probe: dict = {}
    outcome, legs, types, live, said, secs = await case(
        lk, trunk_id, sessions, client_id, areas, "Guardia", "c3", probe=probe, with_post_call=True,
        summary=resumen, get_vars=lambda: {"nota_operador": "Ficha 42, al dia", "cliente": "no gana"})
    reroutes = [d for t, d in probe["events"] if t == "handoff.rerouted"]
    whispers = probe["whispers"]
    ok = (outcome.status, outcome.ended) == ("connected", "returned_to_ai") and \
        [r[:2] for r in legs] == [("no_answer", None), ("busy", 486), ("connected", None)] and \
        probe["holds"] == [True, False] and "handoff.unavailable" not in types and \
        len(reroutes) == 1 and reroutes[0].get("to") == "Central" and reroutes[0].get("reason") == "no_answer" and \
        not any(x.startswith("No pude comunicarte") for x in said) and said[-1] == "¿Te puedo ayudar con algo más?" and \
        len(whispers) == 1 and whispers[0][0].startswith(transfer.PERSON_PREFIX) and \
        "Ficha 42, al dia" in whispers[0][1] and "Central" in whispers[0][1] and \
        not any("Ficha 42" in x for x in said) and "cliente" in live and probe["post_call"] == "armed"
    smoke.check("cadena: sin respuesta, pasa a otra area, conecta y arma el post-call", ok,
                f"{outcome.status}/{outcome.ended} en {secs} s; tramos {legs}; musica {probe['holds']}; "
                f"pases {reroutes}; whispers {whispers}; post-call {probe['post_call']}; dijo {said}")

    # 4. Cadena sin conexion: Guardia 2 no atiende, Silencio atiende y no marca 1.
    probe = {}
    outcome, legs, types, live, said, secs = await case(
        lk, trunk_id, sessions, client_id, areas, "Guardia 2", "c4", probe=probe, with_post_call=True,
        summary=resumen, get_vars=lambda: {"nota_operador": "x"})
    ok = outcome.status == "failed" and [r[0] for r in legs] == ["no_answer", "not_confirmed"] and \
        probe["holds"] == [True, False] and probe["post_call"] is None and \
        sum(1 for t, _ in probe["events"] if t == "handoff.rerouted") == 1 and \
        "cliente" in live and len(said) == 2 and said[0].startswith("Te paso con Guardia 2") and \
        said[1].startswith("No pude comunicarte")
    smoke.check("cadena: termina sin conectar, no arma el post-call", ok,
                f"{outcome.status}/{outcome.result} en {secs} s; tramos {legs}; musica {probe['holds']}; "
                f"post-call {probe['post_call']}; dijo {said}")

    # 5. Rutas en ciclo: A -> B -> A corta al volver a A.
    probe = {}
    outcome, legs, types, live, said, secs = await case(lk, trunk_id, sessions, client_id, areas, "Ciclo A", "c5",
                                                        probe=probe)
    ok = outcome.status == "failed" and len(legs) == 2 and probe["holds"] == [True, False] and \
        sum(1 for t, _ in probe["events"] if t == "handoff.rerouted") == 1 and "cliente" in live
    smoke.check("cadena: el ciclo se corta", ok, f"{outcome.status} en {secs} s; tramos {legs}; dijo {said}")
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
