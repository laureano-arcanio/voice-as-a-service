import asyncio
import datetime
import json
import logging
import time

import httpx
from google.protobuf.duration_pb2 import Duration
from livekit import api
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, inference
from livekit.agents.voice.agent_activity import _SpeechHandleContextVar
from livekit.plugins import openai, silero

from . import config
from .calls import CallLog
from .conversation.engine import ConversationEngine
from .conversation.workflow import load_workflow
from .deps import get_calls, get_engine
from .latency import TurnLatencyTracker

logger = logging.getLogger("agent")

# Un pedido sin voz mata el engine de vllm-tts (docs/TTS_FINETUNE.md, Trampas 8).
if not (config.VLLM_TTS_MODEL and config.VLLM_TTS_VOICE):
    raise RuntimeError("Faltan VLLM_TTS_MODEL y/o VLLM_TTS_VOICE en .env")
openai.tts.AUDIO_STREAM_MODELS.add(config.VLLM_TTS_MODEL)

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


class WorkflowAgent(Agent):
    def __init__(self, engine: ConversationEngine, conversation_id: str, latency: TurnLatencyTracker, on_completed):
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

    async def on_enter(self):
        self.session.on("agent_state_changed", self.on_agent_state)

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
        self.set_dictation(state.workflow_id, turn.next_objective)
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
        vuelven a entrar en este. Si no, el principio quedaba procesado dos
        veces y el agente contestaba cada pedazo."""
        prev = self.last_reply
        if prev is None or not prev.interrupted:
            return
        if not prev.done():
            try:
                await asyncio.wait_for(prev.wait_for_playout(), SETTLE_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("reply %s not done after %ss", prev.id, SETTLE_TIMEOUT)
        self.last_reply = None
        played = self.played.get(prev.id, 0.0)
        if played < CONTINUATION_WINDOW and self.engine.retract_last_turn(self.conversation_id):
            self.consumed -= self.last_user_ids
            logger.info("turn retracted %s (reply interrupted after %.2fs)", self.conversation_id, played)

    def on_reply_done(self, speech) -> None:
        for item in speech.chat_items:
            if (e2e := (getattr(item, "metrics", None) or {}).get("e2e_latency")) is not None:
                self.latency.on_e2e(speech.id, e2e)

    def on_final_reply_done(self, speech) -> None:
        # Se corta cuando la despedida termina de sonar; si el cliente la
        # interrumpio, sigue hablando y el turno siguiente decide.
        if not speech.interrupted:
            self.on_completed()

    def set_dictation(self, workflow_id: str, objective: str | None) -> None:
        spec = load_workflow(workflow_id).fields.get(objective) if objective else None
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
                r = await client.get(f"{config.VLLM_TTS_BASE_URL}/audio/voices",
                                     headers={"Authorization": f"Bearer {config.VLLM_API_KEY}"})
                r.raise_for_status()
            _voices = (time.monotonic(), set(r.json()["voices"]) - {"default"})
        except Exception:
            logger.exception("no se pudieron leer las voces de vllm-tts")
            return None
    return _voices[1]


async def resolve_voice(workflow_id: str, override: str | None = None) -> str:
    """La voz elegida para la llamada (override, desde el dashboard) o la del workflow
    (agent.voice), si vllm-tts la sirve; si no, VLLM_TTS_VOICE. Una voz inexistente daria
    400 en cada frase de la llamada."""
    voice = override or load_workflow(workflow_id).agent.voice
    if not voice or voice == config.VLLM_TTS_VOICE:
        return config.VLLM_TTS_VOICE
    served = await served_voices()
    if served is not None and voice not in served:
        logger.error("voz %r del workflow %s no esta en vllm-tts (%s); uso %r",
                     voice, workflow_id, sorted(served), config.VLLM_TTS_VOICE)
        return config.VLLM_TTS_VOICE
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
            model=config.VLLM_STT_MODEL,
            language="es",
            base_url=config.VLLM_STT_BASE_URL,
            api_key=config.VLLM_API_KEY,
            use_realtime=False,
            vad=vad,
        ),
        llm=openai.LLM(model=config.VLLM_LLM_MODEL, base_url=config.VLLM_LLM_BASE_URL, api_key=config.VLLM_API_KEY),
        tts=openai.TTS(
            model=config.VLLM_TTS_MODEL,
            voice=voice,
            base_url=config.VLLM_TTS_BASE_URL,
            api_key=config.VLLM_API_KEY,
            response_format="pcm",
        ),
    )


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    metadata = json.loads(ctx.job.metadata or "{}")
    engine = get_engine()

    calls = get_calls()

    conversation_id = metadata.get("conversation_id")
    if conversation_id is None:
        # Entrante: la despacha la dispatch rule de LiveKit, sin metadata.
        state, opening = engine.start_conversation(config.WORKFLOW_ID)
        conversation_id = state.conversation_id
        caller = await ctx.wait_for_participant()
        calls.create(conversation_id, "entrante", caller.attributes.get("sip.phoneNumber"))
    else:
        state = engine.store.get(conversation_id)
        opening = state.messages[0].text
    phone = metadata.get("phone")

    voice = await resolve_voice(state.workflow_id, metadata.get("voice"))
    logger.info("llamada %s: workflow %s, voz %s", conversation_id, state.workflow_id, voice)
    session = build_session(voice)
    latency = TurnLatencyTracker()
    session.on("metrics_collected", lambda ev: latency.on_metrics(ev.metrics))
    started_at: float | None = None

    async def finalize(reason: str = ""):
        # La extraccion del ultimo turno puede seguir corriendo (el resultado sale
        # de ahi); en el motor clasico, si corto el cliente, es la unica.
        await engine.finish(conversation_id)
        call = calls.get(conversation_id)
        if call is None or call.status == "fallida":
            return
        calls.update(
            conversation_id, status="finalizada", ended_reason=(reason or "")[:128],
            duration_seconds=int(time.time() - started_at) if started_at else 0,
            latency=latency.summary(),
        )

    ctx.add_shutdown_callback(finalize)

    def fail(error: str, reason: str):
        calls.update(conversation_id, status="fallida", error=error[:2000], ended_reason=reason)
        ctx.shutdown(reason=reason)

    async def hang_up():
        await ctx.delete_room()
        ctx.shutdown(reason="completed")

    # En el loadtest no se corta al completar: si no, cada llamada duraria
    # distinto segun lo que conteste el caller y la carga no seria comparable
    # entre runs. Corta el caller despues de sus turnos.
    if metadata.get("loadtest"):
        on_completed = lambda: logger.info("loadtest %s: workflow completo, sigue la llamada", conversation_id)
    else:
        on_completed = lambda: asyncio.create_task(hang_up())
    agent = WorkflowAgent(engine, conversation_id, latency, on_completed=on_completed)

    ctx.room.on("participant_disconnected", lambda _: ctx.shutdown(reason="customer_hangup"))

    await session.start(agent=agent, room=ctx.room)

    calls.update(conversation_id, status="sonando")
    if phone:
        try:
            await ctx.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=config.LIVEKIT_SIP_TRUNK_ID,
                    sip_call_to=phone,
                    participant_identity="customer",
                    participant_name="Cliente",
                    wait_until_answered=True,
                    max_call_duration=Duration(seconds=config.CALL_MAX_DURATION_SECONDS),
                )
            )
        except Exception as e:
            logger.exception("sip call failed %s", conversation_id)
            fail(str(e), "sip_call_failed")
            return
    elif metadata:
        try:
            await asyncio.wait_for(ctx.wait_for_participant(), timeout=300)
        except asyncio.TimeoutError:
            fail("Nadie se conecto a la room de prueba (5 min)", "test_mode_timeout")
            return

    started_at = time.time()
    calls.update(conversation_id, status="en_curso",
                 started_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None))
    await session.say(opening)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=config.LIVEKIT_AGENT_NAME,
        ws_url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    ))
