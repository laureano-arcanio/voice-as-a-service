"""Un "usuario" sintetico que se conecta a una room de LiveKit igual que un
navegador via app/livekit_dispatch.py::build_test_join_url, pero en vez de un
humano hablando por microfono, publica audio pregenerado (gen_audio.py) y
mide, del lado del cliente, cuanto tarda en empezar a sonar la respuesta del
agente despues de que el usuario termina de hablar.

Esto es intencionalmente independiente de la instrumentacion de
app/latency.py: esa mide server-side (eou/ttft/tts por speech_id); esto mide
"lo que percibiria el usuario real", de punta a punta, incluyendo cualquier
overhead de red/WebRTC que las metricas internas no ven. Se comparan ambas
en run.py.
"""
from __future__ import annotations

import asyncio
import audioop
import math
import random
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

from livekit import rtc

FRAME_MS = 20
SILENCE_RMS_THRESHOLD = 150  # int16 RMS; por debajo se considera silencio

# Formato en el que pedimos el audio del agente. El default de AudioStream
# (48kHz, frames de ~10ms) nos hacia calcular RMS ~100 veces por segundo POR
# caller; con varios callers concurrentes en un mismo proceso eso solo ya
# satura el event loop (ver comentario de arquitectura en run.py). 16kHz y
# frames de 40ms bajan ese trabajo ~10x y siguen siendo de sobra para detectar
# cuando arranca/termina de hablar el agente (resolucion +-40ms sobre
# latencias del orden de 1-2s).
LISTEN_SAMPLE_RATE = 16000
LISTEN_FRAME_MS = 40

# Sin esto, si _mic_loop se atrasa (contencion de CPU) o muere por una
# excepcion, _speak() se queda esperando _pending_done PARA SIEMPRE: no hay
# excepcion, no hay log, la llamada queda colgada indefinidamente. Probado en
# vivo con 18 callers en un proceso: las 18 llamadas quedaron trabadas despues
# del saludo, sin generar una sola request mas al backend. Este timeout hace
# que falle visible (y quede en el CSV) en vez de colgarse.
SPEAK_TIMEOUT_EXTRA_S = 30.0
# Silencio sostenido para dar por terminada una respuesta del agente. Probado
# en vivo: las respuestas del LLM en este proyecto no son cortas -- vistas
# hasta 12-15s de audio TTS por turno (varias oraciones). Un umbral chico
# (0.5s, el valor original) confunde una pausa normal ENTRE oraciones de una
# misma respuesta con el final de la respuesta -- eso partia una respuesta
# larga en varios "bursts" falsos y rompia la deteccion de fin de turno (ver
# WAIT_UNTIL_SILENT mas abajo). 1.5s da margen de sobra para pausas de
# puntuacion sin alargar mucho la deteccion del fin real.
SILENCE_HOLD_S = 1.5
FRAME_TIMEOUT_S = 1.5        # sin frames nuevos durante esto = tambien fin de burst (mismo motivo)

# La gran mayoria de las respuestas de un cliente real son cortas ("si",
# "no", "dale") y las largas son la excepcion -- cada turno samplea una
# categoria con esta distribucion (ver gen_audio.py para las categorias).
CATEGORY_WEIGHTS = {"short": 0.50, "medium": 0.25, "long": 0.25}

# Pausa de "pensar la respuesta" entre que el agente termina de hablar y el
# usuario arranca el turno siguiente. No es fija -- una llamada real tiene
# pausas cortas la mayoria de las veces y ocasionalmente una larga (alguien
# que duda, que escribe algo, etc), asi que se samplea de una lognormal
# (siempre positiva, cola larga a la derecha) en vez de una constante.
# mu/sigma elegidos para que la mediana caiga cerca de 2.5s y los extremos
# del rango [MIN, MAX] salgan con una probabilidad chica pero real -- el pedido
# original fue "esperamos 1, 5, 10s" como ejemplos de magnitud, no un valor fijo.
THINK_TIME_MIN_S = 1.0
THINK_TIME_MAX_S = 10.0
_THINK_TIME_MU = math.log(2.5)
_THINK_TIME_SIGMA = 0.6


def sample_think_time() -> float:
    v = random.lognormvariate(_THINK_TIME_MU, _THINK_TIME_SIGMA)
    return min(THINK_TIME_MAX_S, max(THINK_TIME_MIN_S, v))


def load_pcm16_mono(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, f"{path}: se espera PCM16 mono"
        return w.readframes(w.getnframes()), w.getframerate()


class _BurstDetector:
    """Mira el audio remoto (la respuesta del agente) y trackea un timestamp
    de "arranco a hablar" (speaking_since) mientras dure el burst actual --
    eso es lo que un usuario real percibiria como "el agente empezo a
    hablar".

    A proposito NO cuenta bursts (nro de veces que hubo una transicion
    silencio->habla): el caller siempre espera a que el burst anterior
    termine (speaking vuelve a False) antes de generar uno nuevo (hablando de
    nuevo el o esperando), asi que en cualquier momento en que el caller
    empieza a escuchar solo puede haber UN burst relevante -- el primero que
    aparezca. Contar bursts era fragil: una respuesta larga con una pausa
    interna mas larga que SILENCE_HOLD_S se detectaba como 2+ bursts, y ese
    desfasaje se acumulaba turno a turno (probado en vivo: terminaba dando
    latencias negativas de varios segundos, del orden de la duracion de la
    respuesta anterior)."""

    def __init__(self) -> None:
        self.speaking_since: float | None = None
        self._speaking = False
        self._last_loud_at = 0.0
        self.last_frame_at = 0.0

    def feed(self, frame: rtc.AudioFrame, now: float) -> None:
        self.last_frame_at = now
        rms = audioop.rms(bytes(frame.data), 2)
        if rms > SILENCE_RMS_THRESHOLD:
            if not self._speaking:
                self._speaking = True
                self.speaking_since = now
            self._last_loud_at = now
        elif self._speaking and (now - self._last_loud_at) > SILENCE_HOLD_S:
            self._speaking = False
            self.speaking_since = None

    def tick(self, now: float) -> None:
        # Si el track deja de mandar frames del todo (en vez de mandar
        # silencio real), esto igual cierra el burst.
        if self._speaking and self.last_frame_at and (now - self.last_frame_at) > FRAME_TIMEOUT_S:
            self._speaking = False
            self.speaking_since = None

    @property
    def speaking(self) -> bool:
        return self._speaking


@dataclass
class Turn:
    sent_end: float
    category: str
    agent_started: float | None = None
    error: str | None = None
    think_time_s: float | None = None  # pausa DESPUES de este turno
    # Timestamps epoch (no monotonic) para poder compararlos entre procesos y
    # reconstruir la linea de tiempo de la llamada en el reporte.
    started_ts: float = 0.0   # el usuario empieza a hablar
    ended_ts: float = 0.0     # el agente termino de responder (antes de la pausa)
    speech_s: float = 0.0     # cuanto habla el usuario en este turno

    @property
    def latency(self) -> float | None:
        if self.agent_started is None:
            return None
        return self.agent_started - self.sent_end


@dataclass
class CallerResult:
    call_id: str
    room_name: str
    turns: list[Turn]
    error: str | None = None
    greeted: bool = False  # sono el saludo: el agente tomo la llamada


class AgentHangup(Exception):
    """El agente cerro la room antes de que el caller terminara sus turnos."""


class VirtualCaller:
    def __init__(
        self,
        call_id: str,
        room_name: str,
        livekit_url: str,
        token: str,
        utterances: dict[str, list[Path]],
        n_turns: int = 4,
        greeting_timeout: float = 20.0,
        turn_timeout: float = 15.0,
        reply_timeout: float = 25.0,
    ) -> None:
        self.call_id = call_id
        self.room_name = room_name
        self.livekit_url = livekit_url
        self.token = token
        self.utterances = utterances
        self.n_turns = n_turns
        self.greeting_timeout = greeting_timeout
        self.turn_timeout = turn_timeout
        self.reply_timeout = reply_timeout

        self.room = rtc.Room()
        self._detector = _BurstDetector()
        self._audio_source: rtc.AudioSource | None = None
        self._mic_sample_rate = 24000  # el de vllm-tts (ver gen_audio.py)
        self._mic_task: asyncio.Task | None = None
        self._pending_pcm = bytearray()
        self._pending_done = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._streams: list[rtc.AudioStream] = []
        # Sin esto, si el agente cierra la room (workflow completo, job caido)
        # el caller esperaria cada turno hasta el timeout.
        self._disconnected = asyncio.Event()

    async def run(self) -> CallerResult:
        turns: list[Turn] = []
        error: str | None = None
        greeted = False
        try:
            self._wire_events()
            await self.room.connect(
                self.livekit_url, self.token, options=rtc.RoomOptions(auto_subscribe=True)
            )
            await self._wait_for_speech_start(self.greeting_timeout)  # arranca el saludo
            greeted = True
            await self._wait_until_silent(self.reply_timeout)  # y lo dejamos terminar
            await self._publish_mic()
            for i in range(self.n_turns):
                path, category = self._pick_utterance()
                pcm, sr = load_pcm16_mono(path)
                if sr != self._mic_sample_rate:
                    raise ValueError(f"sample rate {sr} != mic {self._mic_sample_rate} (regenerar audio)")
                started_ts = time.time()
                sent_end = await self._speak(pcm)
                turn = Turn(sent_end=sent_end, category=category, started_ts=started_ts,
                            speech_s=len(pcm) / (self._mic_sample_rate * 2))
                turns.append(turn)
                try:
                    turn.agent_started = await self._wait_for_speech_start(self.turn_timeout)
                    # Esperamos a que el agente termine de hablar -- si
                    # mandaramos el audio del turno siguiente apenas detectamos
                    # que arranco a responder (como hacia antes), estariamos
                    # interrumpiendolo (barge-in) en casi todos los turnos: el
                    # VAD del agente lo toma como interrupcion real, cancela la
                    # generacion en curso y eso infla la latencia medida muy
                    # por encima de lo que percibe un usuario que espera su
                    # turno. Probado en vivo: asi es como aparecian los
                    # `cancelled: True` y las latencias negativas en el CSV.
                    await self._wait_until_silent(self.reply_timeout)
                except TimeoutError as e:
                    turn.error = str(e)
                # Cierra el turno: desde que el usuario empezo a hablar hasta
                # que el agente termino de responder (sin contar la pausa).
                turn.ended_ts = time.time()
                # Pausa de "pensar la respuesta" antes del proximo turno --
                # variable (ver sample_think_time), no fija: ademas de ser mas
                # realista, desincroniza a los callers concurrentes entre si
                # (sin esto todos tienden a hablar en lockstep, en vez de
                # generar carga escalonada como en trafico real).
                turn.think_time_s = sample_think_time()
                await asyncio.sleep(turn.think_time_s)
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
        finally:
            await self._cleanup()
        return CallerResult(call_id=self.call_id, room_name=self.room_name, turns=turns, error=error,
                            greeted=greeted)

    async def _cleanup(self) -> None:
        # El orden importa: primero frenamos nuestras tasks (dejan de usar el
        # stream y el source), despues cerramos los objetos del SDK y recien
        # ahi desconectamos. Sin este cierre ordenado, el bridge FFI de
        # livekit sigue intentando empujar eventos a colas de un event loop
        # que ya se cerro, y aparece "error putting to queue: Event loop is
        # closed" al terminar el proceso.
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        for stream in self._streams:
            try:
                await stream.aclose()
            except Exception:  # noqa: BLE001
                pass
        if self._audio_source is not None:
            try:
                await self._audio_source.aclose()
            except Exception:  # noqa: BLE001
                pass
        try:
            await self.room.disconnect()
        except Exception:  # noqa: BLE001
            pass

    def _pick_utterance(self) -> tuple[Path, str]:
        categories = list(CATEGORY_WEIGHTS.keys())
        weights = [CATEGORY_WEIGHTS[c] for c in categories]
        category = random.choices(categories, weights=weights, k=1)[0]
        return random.choice(self.utterances[category]), category

    def _wire_events(self) -> None:
        def on_track_subscribed(track, publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                self._tasks.append(asyncio.create_task(self._consume_audio(track)))

        self.room.on("track_subscribed", on_track_subscribed)
        self.room.on("disconnected", lambda *_: self._disconnected.set())

    def _check_connected(self) -> None:
        if self._disconnected.is_set():
            raise AgentHangup("el agente cerro la llamada antes de terminar los turnos")

    async def _consume_audio(self, track: rtc.Track) -> None:
        stream = rtc.AudioStream(
            track,
            sample_rate=LISTEN_SAMPLE_RATE,
            num_channels=1,
            frame_size_ms=LISTEN_FRAME_MS,
        )
        self._streams.append(stream)
        async for ev in stream:
            self._detector.feed(ev.frame, time.monotonic())

    async def _wait_for_speech_start(self, timeout: float) -> float:
        # Precondicion (mantenida por run()): el detector esta en silencio
        # cuando se llama esto -- siempre se pasa por _wait_until_silent antes
        # de volver a hablar. Por eso alcanza con esperar la PRIMERA transicion
        # a "hablando", sin llevar la cuenta de cuantos bursts hubo en total
        # (ver comentario en _BurstDetector).
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._check_connected()
            now = time.monotonic()
            self._detector.tick(now)
            if self._detector.speaking and self._detector.speaking_since is not None:
                return self._detector.speaking_since
            await asyncio.sleep(0.02)
        raise TimeoutError("timeout esperando que el agente empiece a responder")

    async def _wait_until_silent(self, timeout: float) -> None:
        # Safety net: si por lo que sea el detector nunca vuelve a "silencio"
        # (ej. quedo mal sincronizado), no bloqueamos la llamada para siempre.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._check_connected()
            now = time.monotonic()
            self._detector.tick(now)
            if not self._detector.speaking:
                return
            await asyncio.sleep(0.02)
        raise TimeoutError("timeout esperando que el agente termine de hablar")

    async def _publish_mic(self) -> None:
        self._audio_source = rtc.AudioSource(self._mic_sample_rate, 1)
        track = rtc.LocalAudioTrack.create_audio_track("mic", self._audio_source)
        opts = rtc.TrackPublishOptions()
        opts.source = rtc.TrackSource.SOURCE_MICROPHONE
        await self.room.local_participant.publish_track(track, opts)
        self._mic_task = asyncio.create_task(self._mic_loop())
        self._tasks.append(self._mic_task)

    async def _mic_loop(self) -> None:
        # Mantiene el track "vivo" con silencio real entre turnos -- igual
        # que un microfono de verdad capturando ambiente -- para que el VAD
        # del agente vea silencio continuo (y dispare endpointing) en vez de
        # un track pausado. Cuando hay un turno pendiente (_pending_pcm),
        # manda ese audio en su lugar, un frame de FRAME_MS por vez.
        assert self._audio_source is not None
        frame_samples = int(self._mic_sample_rate * FRAME_MS / 1000)
        frame_bytes = frame_samples * 2  # int16 mono
        silence = b"\x00" * frame_bytes
        try:
            while True:
                if self._pending_pcm:
                    chunk = bytes(self._pending_pcm[:frame_bytes])
                    del self._pending_pcm[:frame_bytes]
                    if len(chunk) < frame_bytes:
                        chunk += b"\x00" * (frame_bytes - len(chunk))
                    if not self._pending_pcm:
                        self._pending_done.set()
                else:
                    chunk = silence
                frame = rtc.AudioFrame(chunk, self._mic_sample_rate, 1, frame_samples)
                await self._audio_source.capture_frame(frame)
                await asyncio.sleep(FRAME_MS / 1000)
        except asyncio.CancelledError:
            pass

    async def _speak(self, pcm: bytes) -> float:
        self._check_connected()
        self._pending_done.clear()
        self._pending_pcm.extend(pcm)
        # El audio se manda en tiempo real (un frame de FRAME_MS por vez), asi
        # que esto deberia tardar lo que dura el audio; el margen extra cubre
        # jitter del scheduler sin permitir que se cuelgue para siempre.
        audio_s = len(pcm) / (self._mic_sample_rate * 2)
        done = asyncio.ensure_future(self._pending_done.wait())
        hangup = asyncio.ensure_future(self._disconnected.wait())
        try:
            await asyncio.wait({done, hangup}, timeout=audio_s + SPEAK_TIMEOUT_EXTRA_S,
                               return_when=asyncio.FIRST_COMPLETED)
        finally:
            done.cancel()
            hangup.cancel()
        self._check_connected()
        if not self._pending_done.is_set():
            raise TimeoutError("timeout mandando el audio del usuario")
        return time.monotonic()
