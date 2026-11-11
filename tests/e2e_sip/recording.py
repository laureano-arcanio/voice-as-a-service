"""Grabacion completa en Asterisk (MixMonitor, asterisk/conf/extensions.conf line-record), contra el Anura falso.

- Entrante con marcador (numbers/+543510000099): el Anura falso llama por AMI, quien llama habla y marca 4; el
  runner (el lado del agente) contesta con un tono. El 4 tiene que llegar a la room, el atributo atentina.line
  (header X-Atentina-Line) tiene que nombrar el archivo y done/in-<line>.sln tener la voz en el canal 1 y el tono
  en el 2.
- Entrante sin marcador: no queda nada en el spool.
- Saliente con X-Atentina-Rec: la central (3510000009) devuelve el digito que le llega; el runner manda un tono y
  marca 7. El 7 tiene que volver y done/out-<32 hex>.sln tener la central en el canal 1 y el tono en el 2.
- Saliente con un X-Atentina-Rec invalido: no graba.
"""
import asyncio
import math
import os
import statistics
import sys
import time
import uuid
from array import array
from pathlib import Path

import smoke
from google.protobuf.duration_pb2 import Duration

from livekit import api, rtc

sys.path.insert(0, "/scripts")
from livekit_sip_setup import INBOUND_HEADERS_TO_ATTRIBUTES

SPOOL = Path("/spool")
REC_NUMBER, PLAIN_NUMBER = "+543510000099", "+543510000098"
RATE = 8000


async def inbound_setup(lk: api.LiveKitAPI) -> None:
    # Como scripts/livekit_sip_setup.py, con los numeros del e2e y sin agente despachado. Idempotente.
    if any(t.name == "e2e-inbound" for t in (await lk.sip.list_inbound_trunk(api.ListSIPInboundTrunkRequest())).items):
        return
    t = await lk.sip.create_inbound_trunk(api.CreateSIPInboundTrunkRequest(trunk=api.SIPInboundTrunkInfo(
        name="e2e-inbound", numbers=[REC_NUMBER, PLAIN_NUMBER], auth_username="livekit",
        auth_password=os.environ["LIVEKIT_SIP_PASSWORD"], headers_to_attributes=INBOUND_HEADERS_TO_ATTRIBUTES)))
    await lk.sip.create_dispatch_rule(api.CreateSIPDispatchRuleRequest(dispatch_rule=api.SIPDispatchRuleInfo(
        name="e2e-dispatch", trunk_ids=[t.sip_trunk_id],
        rule=api.SIPDispatchRule(dispatch_rule_individual=api.SIPDispatchRuleIndividual(room_prefix="e2e-in-")))))


async def originate(number: str) -> None:
    """El Anura falso llama a nuestro Asterisk (numero nacional con 0, como Anura) y conecta con 'llama'."""
    reader, writer = await asyncio.open_connection("200.13.42.10", 5038)
    await reader.readline()
    for action in ("Action: Login\r\nUsername: e2e\r\nSecret: e2e-ami\r\n",
                   (f"Action: Originate\r\nChannel: PJSIP/0{number[3:]}@e2e-user\r\nContext: from-atentina\r\n"
                    "Exten: llama\r\nPriority: 1\r\nCallerID: <3519998877>\r\nAsync: true\r\n")):
        writer.write((action + "\r\n").encode())
        await writer.drain()
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
    writer.close()


class Side(smoke.Room):
    """El lado del agente con una pista propia para mandarle un tono al telefono."""

    async def join(self) -> None:
        await super().join()
        self.source = rtc.AudioSource(RATE, 1)
        track = rtc.LocalAudioTrack.create_audio_track("tono", self.source)
        await self.room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))

    def digits(self) -> list[str]:
        return [d for ds in self.dtmf.values() for d in ds]

    async def tone(self, seconds: float, hz: int = 1000) -> None:
        n = RATE // 100   # frames de 10 ms
        for i in range(int(seconds * 100)):
            data = array("h", (int(8000 * math.sin(2 * math.pi * hz * (i * n + k) / RATE)) for k in range(n)))
            await self.source.capture_frame(rtc.AudioFrame(data.tobytes(), RATE, 1, n))


async def new_room(lk: api.LiveKitAPI, seen: set[str], seconds: float = 15) -> str:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for r in (await lk.room.list_rooms(api.ListRoomsRequest())).rooms:
            if r.name.startswith("e2e-in-") and r.name not in seen:
                seen.add(r.name)
                return r.name
        await asyncio.sleep(0.2)
    raise TimeoutError("no aparecio la room de la entrante")


async def wait_file(path: Path, seconds: float = 10) -> bool:
    deadline = time.monotonic() + seconds
    while not path.exists() and time.monotonic() < deadline:
        await asyncio.sleep(0.2)
    return path.exists()


def analyze(path: Path) -> tuple[bool, str]:
    """Estereo crudo de 8 kHz: canal 1 la voz del telefono (sola), canal 2 el tono de 1 kHz (solo)."""
    a = array("h")
    a.frombytes(path.read_bytes())
    if sys.byteorder != "little":
        a.byteswap()
    left, right = a[0::2], a[1::2]
    w = RATE // 10

    def rms(x):
        return math.sqrt(sum(v * v for v in x) / len(x)) if x else 0.0

    wins = []
    for i in range(0, len(left) - w + 1, w):
        lw, rw = left[i:i + w], right[i:i + w]
        crossings = sum(1 for j in range(1, w) if (rw[j - 1] < 0) != (rw[j] < 0))
        wins.append((rms(lw), rms(rw), crossings * 5))   # cruces por 100 ms -> Hz
    voice = [x for x in wins if x[0] > 300 and x[1] < 100]
    tone = [x for x in wins if x[1] > 300 and x[0] < 100]
    hz = statistics.median(x[2] for x in tone) if tone else 0
    ok = len(voice) >= 10 and len(tone) >= 10 and 900 <= hz <= 1100
    return ok, (f"{len(left) / RATE:.1f} s, {len(voice) / 10:.1f} s de voz sola en el canal 1, "
                f"{len(tone) / 10:.1f} s de tono solo en el canal 2 ({hz:.0f} Hz)")


def spool_files() -> set[str]:
    return {f"{d}/{p.name}" for d in ("rec", "done") for p in (SPOOL / d).glob("*")}


async def inbound(lk: api.LiveKitAPI, seen: set[str], number: str, record: bool) -> None:
    name = f"entrante {'con' if record else 'sin'} marcador"
    for attempt in range(8):   # hasta que nuestro Asterisk quede registrado en el Anura falso
        await originate(number)
        try:
            room = await new_room(lk, seen, 4)
            break
        except TimeoutError:
            if attempt == 7:
                raise
    side = Side(room)
    await side.join()
    try:
        deadline = time.monotonic() + 15
        while "4" not in side.digits() and time.monotonic() < deadline:
            await asyncio.sleep(0.1)
        caller = next((p for p in side.room.remote_participants.values() if p.identity.startswith("sip_")), None)
        line = caller.attributes.get("atentina.line", "") if caller else ""
        digits = side.digits()
        await side.tone(2.5)
        deadline = time.monotonic() + 10
        while caller and caller.identity not in side.left and time.monotonic() < deadline:
            await asyncio.sleep(0.2)
        path = SPOOL / "done" / f"in-{line}.sln"
        if record:
            ok = bool(line) and digits == ["4"] and await wait_file(path)
            detail = f"línea {line!r}, DTMF {digits}"
            if ok:
                ok, extra = analyze(path)
                detail += f"; {extra}"
        else:
            await asyncio.sleep(2)
            left = sorted(f for f in spool_files() if line and line in f)
            ok = bool(line) and digits == ["4"] and not left
            detail = f"línea {line!r}, DTMF {digits}, en el spool: {left}"
        smoke.check(name, ok, detail)
    finally:
        await side.close(lk)


async def outbound(lk: api.LiveKitAPI, trunk_id: str, rec: str, record: bool) -> None:
    name = "saliente con X-Atentina-Rec" if record else "saliente con X-Atentina-Rec invalido"
    side = Side(f"e2e-out-{uuid.uuid4().hex[:6]}")
    await side.join()
    before = spool_files()
    try:
        await lk.sip.create_sip_participant(api.CreateSIPParticipantRequest(
            room_name=side.name, sip_trunk_id=trunk_id, sip_call_to="+5493510000009", sip_number=smoke.FROM_NUMBER,
            participant_identity="destino", wait_until_answered=True, ringing_timeout=Duration(seconds=8),
            max_call_duration=Duration(seconds=60), headers={"X-Atentina-Rec": rec}))
        await asyncio.sleep(1)
        await side.tone(2)
        await side.room.local_participant.publish_dtmf(code=7, digit="7")
        deadline = time.monotonic() + 20
        while "destino" not in side.left and time.monotonic() < deadline:
            await asyncio.sleep(0.2)
        digits = side.dtmf.get("destino")
        if record:
            path = SPOOL / "done" / f"out-{rec.replace('-', '')}.sln"
            ok = digits == ["7"] and await wait_file(path)
            detail = f"DTMF de vuelta {digits}"
            if ok:
                ok, extra = analyze(path)
                detail += f"; {extra}"
        else:
            await asyncio.sleep(2)
            new = sorted(spool_files() - before)
            ok = digits == ["7"] and not new
            detail = f"DTMF de vuelta {digits}, archivos nuevos: {new}"
        smoke.check(name, ok, detail)
    finally:
        await side.close(lk)


async def main() -> int:
    lk = api.LiveKitAPI(smoke.URL.replace("ws", "http", 1), smoke.KEY, smoke.SECRET)
    await smoke.wait_ready(lk)
    trunk_id = await smoke.trunk(lk)
    await inbound_setup(lk)
    await asyncio.sleep(3)   # que Asterisk termine de registrarse en el Anura falso
    (SPOOL / "numbers" / REC_NUMBER).touch()
    seen: set[str] = set()
    await inbound(lk, seen, REC_NUMBER, record=True)
    await inbound(lk, seen, PLAIN_NUMBER, record=False)
    await outbound(lk, trunk_id, str(uuid.uuid4()), record=True)
    await outbound(lk, trunk_id, "../../etc/passwd", record=False)
    await lk.aclose()

    failed = [n for n, ok, _ in smoke.RESULTS if not ok]
    print(f"\n{len(smoke.RESULTS) - len(failed)}/{len(smoke.RESULTS)} casos OK"
          + (f"; fallaron: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.stdout.flush()
    os._exit(code)   # como smoke.py: el SDK de LiveKit a veces aborta al liberar la room
