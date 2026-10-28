"""Captura y transcripcion por frase de las pistas de una room (VAD + STT), sin AgentSession.

Lo usan el modo escucha de la derivacion (RoomLine en app/voice/handoff.py) y las llamadas directas
(app/voice/direct.py, docs/LLAMADAS_DIRECTAS_PLAN.md): por cada fin de habla del VAD de una identidad que se
escucha, on_phrase(identidad, texto, pcm a 16 kHz). El audio de las identidades de `keep` se guarda entero
(deteccion de contestador por STT de lo primero que se oye).
"""
import asyncio
import logging

from livekit import rtc

logger = logging.getLogger("agent.listen")

SAMPLE_RATE = 16000
# Al terminar una pista (salio de la room): silencio al VAD para que cierre la frase en curso (min_silence 0,3 s).
FLUSH_SILENCE_SECONDS = 0.6


class Listener:
    def __init__(self, vad, stt, on_phrase, *, language: str = "es"):
        self.vad = vad
        self.stt = stt
        self.on_phrase = on_phrase           # on_phrase(identidad, texto, pcm16k)
        self.language = language
        self.listening: set[str] = set()     # identidades que se transcriben
        self.keep: set[str] = set()          # identidades cuyo audio se guarda en `audio`
        self.audio: dict[str, bytearray] = {}
        self.tasks: list[asyncio.Task] = []
        self.capturing: dict[str, set[asyncio.Task]] = {}   # identidad -> sus capturas en curso

    def capture(self, track, identity: str) -> None:
        """Lee la pista: guarda el audio si la identidad esta en `keep` y lo pasa al VAD mientras se escucha."""
        task = asyncio.create_task(self._capture(track, identity))
        self.tasks.append(task)
        running = self.capturing.setdefault(identity, set())
        running.add(task)
        task.add_done_callback(running.discard)

    async def _capture(self, track, identity: str) -> None:
        buf = self.audio.setdefault(identity, bytearray()) if identity in self.keep else None
        vad_stream = None
        transcribe = None
        async for e in rtc.AudioStream(track, sample_rate=SAMPLE_RATE, num_channels=1):
            if buf is not None:
                buf.extend(bytes(e.frame.data))
            if identity in self.listening:
                if vad_stream is None:
                    vad_stream = self.vad.stream()
                    transcribe = asyncio.create_task(self._transcribe(vad_stream, identity))
                    self.tasks.append(transcribe)
                vad_stream.push_frame(e.frame)
        if vad_stream is None:
            return
        # Termino la pista (corto): la frase que estaba diciendo, sin el silencio que la cierra, entra igual.
        step = SAMPLE_RATE // 100
        silence = rtc.AudioFrame(bytes(step * 2), SAMPLE_RATE, 1, step)
        for _ in range(int(FLUSH_SILENCE_SECONDS * 100)):
            vad_stream.push_frame(silence)
        vad_stream.end_input()
        await transcribe

    async def settle(self, identity: str, timeout: float) -> None:
        """Espera (hasta `timeout`) a que terminen las capturas de `identity` (salio de la room): su ultima frase
        pasa por el STT y llega a on_phrase antes de cerrar."""
        running = [t for t in self.capturing.get(identity, ()) if not t.done()]
        if running:
            await asyncio.wait(running, timeout=timeout)

    async def _transcribe(self, vad_stream, identity: str) -> None:
        from livekit.agents import vad as agents_vad

        async for ev in vad_stream:
            if ev.type != agents_vad.VADEventType.END_OF_SPEECH or not ev.frames:
                continue
            try:
                text = await self.recognize(ev.frames)
            except Exception:
                logger.exception("STT de una frase de %s", identity)
                continue
            if text:
                self.on_phrase(identity, text, b"".join(bytes(f.data) for f in ev.frames))

    async def recognize(self, frames) -> str:
        result = await self.stt.recognize(frames, language=self.language)
        return (result.alternatives[0].text if result.alternatives else "").strip()

    async def recognize_pcm(self, pcm: bytes) -> str:
        if not pcm:
            return ""
        return await self.recognize([rtc.AudioFrame(pcm, SAMPLE_RATE, 1, len(pcm) // 2)])

    def close(self) -> None:
        for task in self.tasks:
            task.cancel()
