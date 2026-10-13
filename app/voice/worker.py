import asyncio
import json
import logging
import time
import wave
from pathlib import Path

import httpx
import numpy as np
from google.protobuf.duration_pb2 import Duration
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    inference,
)
from livekit.agents.voice.agent_activity import _SpeechHandleContextVar
from livekit.plugins import openai, silero

from livekit import api, rtc

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..conversation.models import Workflow
from ..db import get_sessionmaker, utcnow
from ..models import CallMode, CallRow, CallStatus
from ..runtime import get_conversation_engine
from ..services import calls as call_service
from ..services import quota
from ..services.errors import NotFound, QuotaExceeded
from .latency import TurnLatencyTracker

logger = logging.getLogger("agent")

# Un pedido sin voz mata el engine de vllm-tts (docs/TTS_FINETUNE.md, Trampas 8).
if not (settings.vllm_tts_model and settings.vllm_tts_voice):
    raise RuntimeError("Faltan VLLM_TTS_MODEL y/o VLLM_TTS_VOICE en .env")
openai.tts.AUDIO_STREAM_MODELS.add(settings.vllm_tts_model)

# Espera de silencio antes de dar el turno por terminado. MIN_ENDPOINTING_DELAY
# cuando el turn detector cree que la frase termino (0,3 por defecto dejaba
# transcripts que llegan despues de cerrar el turno); MAX_ENDPOINTING_DELAY
# cuando duda. Con 1 s, "me gustaria poder hacer un seguimiento" + pausa se
# corto aunque el detector la vio incompleta (llamada c5fa81cd); con 2 s, en
# 7 de 11 turnos de respuestas cortas ("Sí.", "Running") el detector dudo y se
# espero el tope (llamadas b162596a y 7e78a3cc: ~2,3 s hasta que habla el
# agente). Se vuelve a 1 s: si el cliente sigue hablando, CONTINUATION_WINDOW
# une las dos partes. Mientras se pide un dato dictado (email) se estira mas
# (llamada 2d0c771b).
MIN_ENDPOINTING_DELAY = 0.4
MAX_ENDPOINTING_DELAY = 1.0
DICTATION_ENDPOINTING_DELAY = 2.5
DICTATED_TYPES = {"email", "email_or_phone"}

# Si el cliente vuelve a hablar cuando la respuesta sono menos que esto, sigue
# con la misma frase: se deshace el turno aunque haya sonado un pedazo y el
# siguiente lo recibe todo junto. Incluye los 0,5 s de voz que LiveKit exige
# para cortar al agente (interruption min_duration): ~1 s de respuesta.
CONTINUATION_WINDOW = 1.5
# Cuanto se espera a que termine de cerrarse una respuesta cortada.
SETTLE_TIMEOUT = 2.0

# Grabacion por mensaje (agent.record_audio en la definicion, docs/ARQUITECTURA.md): un WAV mono
# por mensaje (cliente y agente por separado) en RECORDINGS_DIR/<conversation_id>/NNN.wav,
# asociado a ese Message por su numero (Message.recording). Mismo sample rate que la
# convencion de audio de WhatsApp (STT_RATE en app/whatsapp/audio.py): voz, no necesita mas.
RECORDING_SAMPLE_RATE = 16000
# El WAV del cliente se recorta a lo que el VAD marco como habla (user_state_changed): el stream
# de stt_node es continuo y sin esto cada archivo arrancaba con el playout del agente. El evento
# de inicio de habla llega despues de la primera silaba (min_speech_duration): pre-roll.
RECORDING_PREROLL_SECONDS = 0.3


class _MonoResampler:
    """Frames de un canal a RECORDING_SAMPLE_RATE, mono: misma logica que
    livekit.agents.voice.recorder_io._Track._resample (modulo privado, no se importa)."""

    def __init__(self) -> None:
        self._resampler: rtc.AudioResampler | None = None
        self._source_rate: int | None = None

    def push(self, frame: rtc.AudioFrame) -> list[rtc.AudioFrame]:
        data = np.frombuffer(frame.data, dtype=np.int16).reshape(-1, frame.num_channels)
        mono = data.mean(axis=1).astype(np.int16) if frame.num_channels > 1 else data[:, 0]
        mono_frame = rtc.AudioFrame(
            data=mono.tobytes(), sample_rate=frame.sample_rate, num_channels=1, samples_per_channel=len(mono))
        if frame.sample_rate == RECORDING_SAMPLE_RATE:
            return [mono_frame]
        if self._resampler is None or self._source_rate != frame.sample_rate:
            self._source_rate = frame.sample_rate
            self._resampler = rtc.AudioResampler(
                input_rate=frame.sample_rate, output_rate=RECORDING_SAMPLE_RATE, num_channels=1)
        return self._resampler.push(mono_frame)


class WorkflowAgent(Agent):
    def __init__(self, engine: ConversationEngine, conversation_id: str, latency: TurnLatencyTracker, on_completed,
                 record_dir: Path | None = None):
        super().__init__(instructions="")
        self.engine = engine
        self.conversation_id = conversation_id
        self.latency = latency
        self.on_completed = on_completed
        self.dictation = False
        # Un turno a la vez: con preemptive generation LiveKit puede llamar a
        # llm_node antes de cerrar la respuesta anterior, y los dos turnos
        # pisaban el estado (en c5fa81cd quedo guardada una respuesta que no sono).
        self.turn_lock = asyncio.Lock()
        self.last_reply = None                  # SpeechHandle del ultimo turno guardado
        self.last_user_ids: set[str] = set()    # mensajes del cliente que proceso ese turno
        self.consumed: set[str] = set()         # mensajes del cliente ya procesados
        self.played: dict[str, float] = {}      # segundos que sono cada respuesta (speech_id)
        self._speaking: tuple[str, float] | None = None
        # Grabacion por mensaje (None: agent.record_audio en false, no se graba).
        self.record_dir = record_dir
        self._rec_seq = 0
        self._rec_customer = bytearray()        # audio del cliente desde el ultimo turno confirmado
        self._rec_marks: list[tuple[int, bool]] = []  # (offset, hablando) de cada cambio de VAD
        self._rec_user_speaking = False         # VAD: el cliente esta hablando (user_state_changed)
        self._rec_customer_resampler = _MonoResampler()
        self._rec_agent_resampler = _MonoResampler()
        self._rec_pending: tuple[bytes, list[tuple[int, bool]], bytes] | None = None  # (cliente, marcas, agente) sin confirmar

    def stt_node(self, audio, model_settings):
        if self.record_dir is None:
            return super().stt_node(audio, model_settings)
        return super().stt_node(self._tee_customer_audio(audio), model_settings)

    async def _tee_customer_audio(self, audio):
        async for frame in audio:
            for f in self._rec_customer_resampler.push(frame):
                self._rec_push_customer(f.data)
            yield frame

    def _rec_push_customer(self, data: bytes) -> None:
        """Acumula un frame del cliente y, en cada cambio de VAD, deja la marca (offset,
        hablando) para recortar el WAV del turno al habla (_trim_customer)."""
        if not self._rec_marks or self._rec_marks[-1][1] != self._rec_user_speaking:
            self._rec_marks.append((len(self._rec_customer), self._rec_user_speaking))
        self._rec_customer.extend(data)

    def tts_node(self, text, model_settings):
        if self.record_dir is None:
            return super().tts_node(text, model_settings)
        return self._tee_agent_audio(text, model_settings)

    async def _tee_agent_audio(self, text, model_settings):
        agent_audio = bytearray()
        try:
            async for frame in super().tts_node(text, model_settings):
                for f in self._rec_agent_resampler.push(frame):
                    agent_audio.extend(f.data)
                yield frame
        finally:
            # No se escribe todavia: si settle_last_reply deshace este turno (respuesta
            # interrumpida apenas empezada), este audio tiene que volver al turno siguiente,
            # no quedar en un WAV de un turno que el motor ya fusiono con otro.
            self._rec_pending = (bytes(self._rec_customer), list(self._rec_marks), bytes(agent_audio))
            self._rec_customer.clear()
            self._rec_marks.clear()

    def _commit_audio(self, audio: bytes) -> int | None:
        """Un WAV con ese audio (ya resampleado); devuelve su numero de secuencia, o None
        si no hay nada que grabar."""
        if not audio:
            return None
        self._rec_seq += 1
        path = self.record_dir / f"{self._rec_seq:03d}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RECORDING_SAMPLE_RATE)
            w.writeframes(audio)
        return self._rec_seq

    @staticmethod
    def _trim_customer(audio: bytes, marks: list[tuple[int, bool]]) -> bytes:
        """Solo lo hablado: del primer tramo marcado como habla (menos el pre-roll, que tapa
        la demora del evento de VAD) al fin del ultimo. Las pausas entre tramos quedan; el
        silencio previo (playout del agente) y el posterior (latencia y sintesis), no."""
        spans = []
        for i, (offset, speaking) in enumerate(marks):
            if speaking:
                end = marks[i + 1][0] if i + 1 < len(marks) else len(audio)
                spans.append((offset, end))
        if not spans:
            return b""
        preroll = int(RECORDING_PREROLL_SECONDS * RECORDING_SAMPLE_RATE) * 2  # 16 bits, mono
        return audio[max(0, spans[0][0] - preroll):spans[-1][1]]

    def _commit_turn(self, customer_audio: bytes, marks: list[tuple[int, bool]], agent_audio: bytes) -> None:
        """Un WAV por lado (el cliente: lo que hablo desde el turno anterior, sin los silencios;
        el agente: esta respuesta o el saludo en el primer turno), asociados al mensaje de cada
        uno (_tag_recording). Se llama solo para un turno ya confirmado (no retractado)."""
        user_seq = self._commit_audio(self._trim_customer(customer_audio, marks))
        assistant_seq = self._commit_audio(agent_audio)
        if user_seq is not None or assistant_seq is not None:
            self._tag_recording(user_seq, assistant_seq)

    def _tag_recording(self, user_seq: int | None, assistant_seq: int | None) -> None:
        """Guarda el numero de archivo en el ultimo mensaje de cada rol (ya persistidos por
        engine.process_turn: el guardado de este turno paso por el, llm_node solo cierra el
        TTS despues). Busca desde el final para no leer toda la conversacion."""
        state = self.engine.store.get(self.conversation_id)
        if state is None:
            return
        remaining = {k: v for k, v in {"assistant": assistant_seq, "user": user_seq}.items() if v is not None}
        for m in reversed(state.messages):
            if m.role in remaining:
                m.recording = remaining.pop(m.role)
                if not remaining:
                    break
        self.engine.store.save(state)

    def flush_recording(self) -> None:
        """Al cortar: confirma el ultimo turno si quedo pendiente y, si el cliente hablo
        despues sin que el agente respondiera, ese resto tambien queda en un archivo (sin
        esto se perdia el final de la llamada). Ese resto no tiene mensaje propio (el motor
        nunca llego a procesarlo): queda sin asociar."""
        if self.record_dir is None:
            return
        if self._rec_pending is not None:
            self._commit_turn(*self._rec_pending)
            self._rec_pending = None
        if self._rec_customer:
            self._commit_audio(self._trim_customer(bytes(self._rec_customer), self._rec_marks))
            self._rec_customer.clear()
            self._rec_marks.clear()

    async def on_enter(self):
        self.session.on("agent_state_changed", self.on_agent_state)
        self.session.on("user_state_changed", self.on_user_state)

    def on_user_state(self, ev) -> None:
        # VAD: marca que frames del stream continuo son habla del cliente (_rec_push_customer).
        self._rec_user_speaking = ev.new_state == "speaking"

    def on_agent_state(self, ev) -> None:
        # Pausa o corte por voz del cliente = sale de "speaking".
        speech = self.session.current_speech
        if ev.old_state == "speaking" and self._speaking:
            speech_id, since = self._speaking
            self.played[speech_id] = self.played.get(speech_id, 0.0) + ev.created_at - since
            self._speaking = None
        if ev.new_state == "speaking" and speech is not None:
            self._speaking = (speech.id, ev.created_at)

    async def llm_node(self, chat_ctx, tools, model_settings):
        # La respuesta en curso: LiveKit no la expone en llm_node, es la misma
        # context var privada que usa Agent internamente. Sirve para juntar el
        # tiempo del LLM con el EOU y el TTS del turno, y para saber cuanto sono.
        speech = _SpeechHandleContextVar.get(None)
        started = time.perf_counter()
        first_text: float | None = None
        chunks: asyncio.Queue[str | None] = asyncio.Queue()

        async def run():
            try:
                return await self.run_turn(chat_ctx, speech, chunks.put_nowait)
            finally:
                chunks.put_nowait(None)

        # El mensaje va al TTS a medida que el LLM lo escribe; el turno termina
        # (validacion y guardado) cuando llega el resto del JSON. Si LiveKit
        # descarta la respuesta a mitad de camino, se cancela sin guardar.
        task = asyncio.create_task(run())
        try:
            while (text := await chunks.get()) is not None:
                if first_text is None:
                    first_text = time.perf_counter() - started
                yield text
            state, turn = await task
        finally:
            if not task.done():
                task.cancel()
        self.latency.on_llm(speech.id if speech else None, first_text, time.perf_counter() - started)
        if speech is not None:
            speech.add_done_callback(self.on_reply_done)
            if turn.status == "completed":
                speech.add_done_callback(self.on_final_reply_done)
        self.set_dictation(self.engine.workflow(state), turn.next_objective)
        logger.info("turn %s answered=%s next=%s status=%s", self.conversation_id, turn.answered, turn.next_objective, turn.status)

    async def run_turn(self, chat_ctx, speech, on_message):
        async with self.turn_lock:
            await self.settle_last_reply()
            user_items = [item for item in chat_ctx.items
                          if getattr(item, "role", None) == "user" and item.text_content and item.id not in self.consumed]
            result = await self.engine.process_turn(
                self.conversation_id, " ".join(item.text_content for item in user_items), on_message=on_message)
            self.last_reply = speech
            self.last_user_ids = {item.id for item in user_items}
            self.consumed |= self.last_user_ids
            return result

    async def settle_last_reply(self) -> None:
        """Si la respuesta anterior se corto antes de sonar o apenas empezada, el
        cliente seguia con la misma frase: se deshace ese turno y sus mensajes
        (y, si se graba, su audio) vuelven a entrar en este. Si no, el principio
        quedaba procesado dos veces y el agente contestaba cada pedazo."""
        prev = self.last_reply
        if prev is None or not prev.interrupted:
            if self._rec_pending is not None:
                self._commit_turn(*self._rec_pending)
                self._rec_pending = None
            return
        if not prev.done():
            try:
                await asyncio.wait_for(prev.wait_for_playout(), SETTLE_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("reply %s not done after %ss", prev.id, SETTLE_TIMEOUT)
        self.last_reply = None
        played = self.played.get(prev.id, 0.0)
        # El audio de esta respuesta ya termino de sintetizarse para cuando wait_for_playout
        # resuelve (o prev.done() ya era true), asi que _tee_agent_audio ya dejo su pendiente.
        pending = self._rec_pending
        self._rec_pending = None
        if played < CONTINUATION_WINDOW and self.engine.retract_last_turn(self.conversation_id):
            self.consumed -= self.last_user_ids
            if pending is not None:
                self._rec_customer[0:0] = pending[0]
                self._rec_marks = list(pending[1]) + [(off + len(pending[0]), s) for off, s in self._rec_marks]
            logger.info("turn retracted %s (reply interrupted after %.2fs)", self.conversation_id, played)
        elif pending is not None:
            self._commit_turn(*pending)

    def on_reply_done(self, speech) -> None:
        for item in speech.chat_items:
            if (e2e := (getattr(item, "metrics", None) or {}).get("e2e_latency")) is not None:
                self.latency.on_e2e(speech.id, e2e)

    def on_final_reply_done(self, speech) -> None:
        # Se corta cuando la despedida termina de sonar; si el cliente la
        # interrumpio, sigue hablando y el turno siguiente decide.
        if not speech.interrupted:
            self.on_completed()

    def set_dictation(self, workflow: Workflow, objective: str | None) -> None:
        spec = workflow.fields.get(objective) if objective else None
        dictation = spec is not None and spec.type in DICTATED_TYPES
        if dictation != self.dictation:
            self.dictation = dictation
            delay = DICTATION_ENDPOINTING_DELAY if dictation else MAX_ENDPOINTING_DELAY
            self.session.update_options(endpointing_opts={"max_delay": delay})


# Voces que sirve vllm-tts, cacheadas VOICES_TTL s: si cambia el checkpoint, el
# worker se entera sin reiniciar.
VOICES_TTL = 60
_voices: tuple[float, set[str]] | None = None


async def served_voices() -> set[str] | None:
    """Voces del checkpoint de vllm-tts (GET /audio/voices), sin "default". None si no responde."""
    global _voices
    if _voices is None or time.monotonic() - _voices[0] > VOICES_TTL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{settings.vllm_tts_base_url}/audio/voices",
                                     headers={"Authorization": f"Bearer {settings.vllm_api_key}"})
                r.raise_for_status()
            _voices = (time.monotonic(), set(r.json()["voices"]) - {"default"})
        except Exception:
            logger.exception("no se pudieron leer las voces de vllm-tts")
            return None
    return _voices[1]


async def resolve_voice(workflow: Workflow, override: str | None = None) -> str:
    """La voz elegida para la llamada (override, desde la UI) o la del agente
    (agent.voice), si vllm-tts la sirve; si no, VLLM_TTS_VOICE. Una voz inexistente daria
    400 en cada frase de la llamada."""
    voice = override or workflow.agent.voice
    if not voice or voice == settings.vllm_tts_voice:
        return settings.vllm_tts_voice
    served = await served_voices()
    if served is not None and voice not in served:
        logger.error("voz %r del agente %s no esta en vllm-tts (%s); uso %r",
                     voice, workflow.id, sorted(served), settings.vllm_tts_voice)
        return settings.vllm_tts_voice
    return voice


def build_session(voice: str) -> AgentSession:
    vad = silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.2)
    return AgentSession(
        vad=vad,
        turn_handling={
            # v1-mini corre en el proceso (livekit-local-inference, pesos en el
            # wheel, ~27 ms por prediccion en CPU). Sin fijarlo, en modo dev o en
            # LiveKit Cloud usa v1, que va al gateway de inferencia de Cloud.
            "turn_detection": inference.TurnDetector(version="v1-mini"),
            "endpointing": {"min_delay": MIN_ENDPOINTING_DELAY, "max_delay": MAX_ENDPOINTING_DELAY},
        },
        stt=openai.STT(
            model=settings.vllm_stt_model,
            language="es",
            base_url=settings.vllm_stt_base_url,
            api_key=settings.vllm_api_key,
            use_realtime=False,
            vad=vad,
        ),
        llm=openai.LLM(model=settings.vllm_llm_model, base_url=settings.vllm_llm_base_url, api_key=settings.vllm_api_key),
        tts=openai.TTS(
            model=settings.vllm_tts_model,
            voice=voice,
            base_url=settings.vllm_tts_base_url,
            api_key=settings.vllm_api_key,
            response_format="pcm",
        ),
    )


async def outbound_trunk_id(lkapi: api.LiveKitAPI) -> str:
    """ID del trunk SIP saliente: LIVEKIT_SIP_TRUNK_ID o, si esta vacio, el que se llama
    LIVEKIT_SIP_OUTBOUND_TRUNK_NAME (el de `make livekit-sip`). Con LiveKit propio el ID
    cambia en cada reinicio del host, por eso se busca por nombre y no se cachea."""
    if settings.livekit_sip_trunk_id:
        return settings.livekit_sip_trunk_id
    trunks = await lkapi.sip.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())
    for trunk in trunks.items:
        if trunk.name == settings.livekit_sip_outbound_trunk_name:
            return trunk.sip_trunk_id
    raise RuntimeError(
        f"No hay trunk SIP saliente '{settings.livekit_sip_outbound_trunk_name}' en LiveKit: "
        "correr `make livekit-sip` (o poner LIVEKIT_SIP_TRUNK_ID en .env)"
    )


async def say_and_hang_up(ctx: JobContext, text: str, voice: str, reason: str) -> None:
    """Avisa con una frase y corta. Para la entrante que el tier no deja atender."""
    session = build_session(voice)
    try:
        await session.start(agent=Agent(instructions=""), room=ctx.room)
        await asyncio.wait_for(session.say(text, allow_interruptions=False).wait_for_playout(), 20)
    except Exception:
        logger.exception("no se pudo avisar antes de cortar (%s)", reason)
    finally:
        await ctx.delete_room()
        ctx.shutdown(reason=reason)


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    metadata = json.loads(ctx.job.metadata or "{}")
    engine = get_conversation_engine()
    sessions = get_sessionmaker()

    conversation_id = metadata.get("conversation_id")
    if conversation_id is None:
        # Entrante: la despacha la dispatch rule de LiveKit, sin metadata. Se rutea por
        # el numero marcado al agente de ese numero, con los limites de su cliente.
        caller = await ctx.wait_for_participant()
        dialed = caller.attributes.get("sip.trunkPhoneNumber")
        try:
            with sessions() as s:
                inbound = call_service.start_inbound(s, engine, dialed, caller.attributes.get("sip.phoneNumber"))
        except NotFound as e:
            logger.error("entrante a %s sin atender: %s", dialed, e.message)
            await ctx.delete_room()
            ctx.shutdown(reason=e.code)
            return
        except QuotaExceeded as e:
            logger.warning("entrante a %s rechazada por el tier: %s", dialed, e.code)
            await say_and_hang_up(ctx, settings.quota_reject_message, settings.vllm_tts_voice, e.code)
            return
        conversation_id, mode = inbound.conversation_id, CallMode.entrante
    else:
        mode = (CallMode.saliente if metadata.get("phone")
                else CallMode.loadtest if metadata.get("loadtest") else CallMode.prueba)
    state = engine.store.get(conversation_id)
    opening = state.messages[0].text
    phone = metadata.get("phone")

    def update_call(**values) -> None:
        with sessions() as s:
            call_service.update_call(s, conversation_id, **values)

    workflow = engine.workflow(state)
    voice = await resolve_voice(workflow, metadata.get("voice"))
    logger.info("llamada %s (%s): agente %s v%s, voz %s", conversation_id, mode, state.agent_id,
                state.agent_version, voice)
    record_dir = settings.call_recordings_dir / conversation_id if workflow.record_audio else None
    session = build_session(voice)
    latency = TurnLatencyTracker()
    session.on("metrics_collected", lambda ev: latency.on_metrics(ev.metrics))
    started_at: float | None = None
    watchdog: asyncio.Task | None = None

    async def finalize(reason: str = ""):
        if watchdog is not None:
            watchdog.cancel()
        agent.flush_recording()
        # La extraccion del ultimo turno puede seguir corriendo (el resultado sale
        # de ahi); en el motor clasico, si corto el cliente, es la unica.
        await engine.finish(conversation_id)
        with sessions() as s:
            call = s.get(CallRow, conversation_id)
            if call is None or call.status == CallStatus.fallida:
                return
            call_service.update_call(
                s, conversation_id, status=CallStatus.finalizada, ended_reason=(reason or "")[:128], ended_at=utcnow(),
                duration_seconds=int(time.time() - started_at) if started_at else 0, latency=latency.summary())

    ctx.add_shutdown_callback(finalize)

    def fail(error: str, reason: str):
        update_call(status=CallStatus.fallida, error=error[:2000], ended_reason=reason, ended_at=utcnow())
        ctx.shutdown(reason=reason)

    async def hang_up(reason: str = "completed"):
        await ctx.delete_room()
        ctx.shutdown(reason=reason)

    async def say_end_and_hang_up(reason: str):
        session.interrupt()
        try:
            await asyncio.wait_for(
                session.say(settings.quota_end_message, allow_interruptions=False).wait_for_playout(), 15)
        except Exception:
            logger.exception("no se pudo avisar el corte (%s)", reason)
        await hang_up(reason)

    async def quota_watchdog():
        """Corte duro: cuando al cliente se le acaban los minutos del mes (contando
        esta y sus otras llamadas en curso), avisa y corta."""
        while True:
            await asyncio.sleep(settings.quota_check_seconds)
            with sessions() as s:
                remaining = call_service.call_remaining_seconds(s, conversation_id)
            if remaining is not None and remaining <= 0:
                logger.warning("llamada %s: sin minutos del tier, se corta", conversation_id)
                await say_end_and_hang_up("quota_exhausted")
                return

    async def duration_limit(seconds: int):
        await asyncio.sleep(seconds)
        logger.info("llamada %s: duracion maxima (%ss), se corta", conversation_id, seconds)
        await say_end_and_hang_up("max_duration")

    # En el loadtest no se corta al completar: si no, cada llamada duraria
    # distinto segun lo que conteste el caller y la carga no seria comparable
    # entre runs. Corta el caller despues de sus turnos.
    if metadata.get("loadtest"):
        on_completed = lambda: logger.info("loadtest %s: workflow completo, sigue la llamada", conversation_id)
    else:
        on_completed = lambda: asyncio.create_task(hang_up())
    agent = WorkflowAgent(engine, conversation_id, latency, on_completed=on_completed, record_dir=record_dir)

    ctx.room.on("participant_disconnected", lambda _: ctx.shutdown(reason="customer_hangup"))

    await session.start(agent=agent, room=ctx.room)

    update_call(status=CallStatus.sonando)
    if phone:
        max_duration = metadata.get("max_duration_seconds") or settings.call_max_duration_seconds
        try:
            await ctx.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=await outbound_trunk_id(ctx.api),
                    sip_call_to=phone,
                    # Caller ID: el numero del cliente. Asterisk hoy lo pisa con ANURA_DID
                    # (docs/TELEFONIA_ANURA.md).
                    sip_number=metadata.get("from_number") or "",
                    participant_identity="customer",
                    participant_name="Cliente",
                    wait_until_answered=True,
                    max_call_duration=Duration(seconds=max_duration),
                )
            )
        except Exception as e:
            logger.exception("sip call failed %s", conversation_id)
            fail(str(e), "sip_call_failed")
            return
    elif mode in (CallMode.prueba, CallMode.loadtest):
        join_timeout = metadata.get("join_timeout_seconds") or 300
        try:
            await asyncio.wait_for(ctx.wait_for_participant(), timeout=join_timeout)
        except asyncio.TimeoutError:
            fail(f"Nadie se conecto a la room de prueba ({join_timeout} s)", "test_mode_timeout")
            return

    started_at = time.time()
    update_call(status=CallStatus.en_curso, started_at=utcnow())
    if mode in quota.MINUTE_MODES:
        watchdog = asyncio.create_task(quota_watchdog())
    elif not phone and metadata.get("max_duration_seconds"):
        watchdog = asyncio.create_task(duration_limit(metadata["max_duration_seconds"]))
    await session.say(opening)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=settings.livekit_agent_name,
        ws_url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    ))
