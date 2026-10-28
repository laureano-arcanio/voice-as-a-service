"""Prueba SIP de punta a punta contra el Anura falso (docker-compose.e2e-sip.yml, `make e2e-sip`).

Recorre LiveKit -> livekit-sip -> nuestro Asterisk (config de produccion) -> Anura falso con los casos de
la derivacion (docs/features/EQUIPO_TELEFONIA.md y 8): atiende y marca 1 y 2, ocupado, no atiende, buzon,
congestion, atiende y no marca, atiende y corta, y dos tramos a la vez en la misma room aislados entre
si. Sale con codigo 1 si falla algun caso. No usa la inferencia: valida senalizacion, DTMF y audio.
"""
import asyncio
import os
import sys
import time

from google.protobuf.duration_pb2 import Duration
from livekit import api, rtc

URL = os.environ["LIVEKIT_URL"]
KEY, SECRET = os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
TRUNK_NAME = "anura-asterisk-outbound"
FROM_NUMBER = "+543510000000"


def sip_status(e: BaseException) -> int | None:
    # Como app/services/campaign_calls.sip_status.
    try:
        return int((getattr(e, "metadata", None) or {}).get("sip_status_code"))
    except (TypeError, ValueError):
        return None


async def wait_ready(lk: api.LiveKitAPI, seconds: int = 60) -> None:
    deadline = time.monotonic() + seconds
    while True:
        try:
            await lk.room.list_rooms(api.ListRoomsRequest())
            return
        except Exception:
            if time.monotonic() > deadline:
                raise
            await asyncio.sleep(1)


async def trunk(lk: api.LiveKitAPI) -> str:
    # Como scripts/livekit_sip_setup.py: Asterisk en este host, con el usuario livekit.
    for t in (await lk.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())).items:
        if t.name == TRUNK_NAME:
            return t.sip_trunk_id
    t = await lk.sip.create_outbound_trunk(api.CreateSIPOutboundTrunkRequest(trunk=api.SIPOutboundTrunkInfo(
        name=TRUNK_NAME, address="127.0.0.1:5080", numbers=[FROM_NUMBER], auth_username="livekit",
        auth_password=os.environ["LIVEKIT_SIP_PASSWORD"])))
    return t.sip_trunk_id


class Room:
    """El lado del agente: entra a la room y junta DTMF, audio y salidas por participante."""

    def __init__(self, name: str):
        self.name = name
        self.room = rtc.Room()
        self.dtmf: dict[str, list[str]] = {}
        self.audio_peak: dict[str, int] = {}
        self.left: dict[str, float] = {}
        self.tracks: dict[str, str] = {}
        self.t0 = time.monotonic()

    async def join(self) -> None:
        token = (api.AccessToken(KEY, SECRET).with_identity("agente")
                 .with_grants(api.VideoGrants(room_join=True, room=self.name)).to_jwt())
        self.room.on("sip_dtmf_received", lambda e: self.dtmf.setdefault(e.participant.identity, []).append(e.digit))
        self.room.on("participant_disconnected", lambda p: self.left.setdefault(p.identity, time.monotonic() - self.t0))
        self.room.on("track_published", lambda pub, p: self.tracks.__setitem__(p.identity, pub.sid))
        self.room.on("track_subscribed", self._on_track)
        await self.room.connect(URL, token)

    def _on_track(self, track, pub, p):
        async def read():
            async for e in rtc.AudioStream(track, sample_rate=8000, num_channels=1):
                data = memoryview(bytes(e.frame.data)).cast("h")
                self.audio_peak[p.identity] = max(self.audio_peak.get(p.identity, 0), max(map(abs, data), default=0))
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.create_task(read())

    async def close(self, lk: api.LiveKitAPI) -> None:
        await self.room.disconnect()
        try:
            await lk.room.delete_room(api.DeleteRoomRequest(room=self.name))
        except Exception:
            pass


async def dial(lk, trunk_id, room, number, identity, ring=8) -> tuple[str, int | None, float]:
    """(resultado, codigo SIP, segundos): answered, no_answer o failed."""
    t = time.monotonic()
    try:
        await lk.sip.create_sip_participant(api.CreateSIPParticipantRequest(
            room_name=room, sip_trunk_id=trunk_id, sip_call_to=number, sip_number=FROM_NUMBER,
            participant_identity=identity, wait_until_answered=True, ringing_timeout=Duration(seconds=ring),
            max_call_duration=Duration(seconds=120)))
        return "answered", None, time.monotonic() - t
    except api.TwirpError as e:
        status = sip_status(e)
        return ("no_answer" if status is None and "timed out" in e.message else "failed"), status, time.monotonic() - t


RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'OK  ' if ok else 'FALLA'} {name}: {detail}", flush=True)


async def single(lk, trunk_id, name, number, expect, *, wait=0.0, ring=8, after=None):
    r = Room(f"e2e-{name}")
    await r.join()
    try:
        result, status, secs = await dial(lk, trunk_id, r.name, number, "destino", ring)
        if wait:
            await asyncio.sleep(wait)
        ok = (result, status) == expect if isinstance(expect, tuple) else result == expect
        detail = f"{result} (SIP {status}) en {secs:.1f} s"
        if ok and after:
            ok, extra = after(r)
            detail += f"; {extra}"
        check(name, ok, detail)
    finally:
        await r.close(lk)


async def isolation(lk, trunk_id):
    """Dos tramos a la vez (cliente y persona) en la misma room, sin escucharse hasta conectarlos."""
    r = Room("e2e-dos-tramos")
    await r.join()
    try:
        cliente = asyncio.create_task(dial(lk, trunk_id, r.name, "+5493519999999", "cliente"))
        persona = asyncio.create_task(dial(lk, trunk_id, r.name, "+5493510000006", "persona"))
        results = [(await cliente)[0], (await persona)[0]]
        deadline = time.monotonic() + 5
        while not {"cliente", "persona"} <= set(r.tracks) and time.monotonic() < deadline:
            await asyncio.sleep(0.1)
        if not {"cliente", "persona"} <= set(r.tracks):
            check("dos tramos aislados", False, f"{results}, pistas publicadas: {sorted(r.tracks)}")
            return
        for who, other in (("persona", "cliente"), ("cliente", "persona")):
            await lk.room.update_subscriptions(api.UpdateSubscriptionsRequest(
                room=r.name, identity=who, track_sids=[r.tracks[other]], subscribe=False))
        await asyncio.sleep(3)
        live = {p.identity for p in (await lk.room.list_participants(api.ListParticipantsRequest(room=r.name))).participants}
        ok = results == ["answered", "answered"] and {"cliente", "persona"} <= live and r.audio_peak.get("cliente", 0) > 500
        check("dos tramos aislados", ok, f"{results}, en la room: {sorted(live)}, audio del cliente {r.audio_peak.get('cliente', 0)}")
    finally:
        await r.close(lk)


async def main() -> int:
    lk = api.LiveKitAPI(URL.replace("ws", "http", 1), KEY, SECRET)
    await wait_ready(lk)
    trunk_id = await trunk(lk)
    await asyncio.sleep(3)   # que Asterisk termine de registrarse en el Anura falso

    await single(lk, trunk_id, "persona confirma y vuelve", "+5493510000001", "answered", wait=14,
                 after=lambda r: (r.dtmf.get("destino") == ["1", "2"] and r.audio_peak.get("destino", 0) > 500,
                                  f"DTMF {r.dtmf.get('destino')}, audio {r.audio_peak.get('destino', 0)}"))
    await single(lk, trunk_id, "ocupado", "+5493510000002", ("failed", 486))
    await single(lk, trunk_id, "no atiende", "+5493510000003", "no_answer", ring=6)
    await single(lk, trunk_id, "buzon", "+5493510000004", "answered", wait=6,
                 after=lambda r: (r.audio_peak.get("destino", 0) > 500, f"audio {r.audio_peak.get('destino', 0)}"))
    await single(lk, trunk_id, "congestion", "+5493510000005", ("failed", 503))
    await single(lk, trunk_id, "atiende y corta", "+5493510000007", "answered", wait=5,
                 after=lambda r: ("destino" in r.left, f"cortó a los {r.left.get('destino', 0):.1f} s"))
    await isolation(lk, trunk_id)
    await lk.aclose()

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} casos OK" + (f"; fallaron: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
