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

    def capture(self, track, identity: str) -> None:
        """Lee la pista: guarda el audio si la identidad esta en `keep` y lo pasa al VAD mientras se escucha."""
        self.tasks.append(asyncio.create_task(self._capture(track, identity)))

    async def _capture(self, track, identity: str) -> None:
        buf = self.audio.setdefault(identity, bytearray()) if identity in self.keep else None
        vad_stream = None
        async for e in rtc.AudioStream(track, sample_rate=SAMPLE_RATE, num_channels=1):
            if buf is not None:
                buf.extend(bytes(e.frame.data))
            if identity in self.listening:
                if vad_stream is None:
                    vad_stream = self.vad.stream()
                    self.tasks.append(asyncio.create_task(self._transcribe(vad_stream, identity)))
                vad_stream.push_frame(e.frame)

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
