import asyncio
import datetime
import json
import logging
import time

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

# Espera maxima de silencio antes de dar el turno por terminado cuando el turn
# detector no esta seguro. 1 s alcanza para respuestas cortas, pero corta los
# dictados: en la llamada 2d0c771b "Escribime a" + pausa llego solo, dos veces.
# Mientras se pide un dato dictado (email) se estira.
MAX_ENDPOINTING_DELAY = 1.0
DICTATION_ENDPOINTING_DELAY = 2.5
DICTATED_TYPES = {"email", "email_or_phone"}


def spoken(item) -> bool:
    return getattr(item, "role", None) == "assistant" and bool(item.text_content)


def pending_user_text(chat_ctx) -> str:
    """Lo que dijo el usuario desde la ultima respuesta que llego a sonar (una
    respuesta interrumpida antes de sonar queda vacia o no queda)."""
    texts = []
    for item in reversed(chat_ctx.items):
        role = getattr(item, "role", None)
        if spoken(item):
            break
        if role == "user" and item.text_content:
            texts.append(item.text_content)
    return " ".join(reversed(texts))


class WorkflowAgent(Agent):
    def __init__(self, engine: ConversationEngine, conversation_id: str, latency: TurnLatencyTracker):
        super().__init__(instructions="")
        self.engine = engine
        self.conversation_id = conversation_id
        self.latency = latency
        self.completed = False
        self.dictation = False

    async def llm_node(self, chat_ctx, tools, model_settings):
        started = time.perf_counter()
        state, turn = await self.engine.process_turn(self.conversation_id, pending_user_text(chat_ctx))
        # La respuesta en curso: LiveKit no la expone en llm_node, es la misma
        # context var privada que usa Agent internamente. Sirve para juntar este
        # tiempo con el EOU y el TTS del turno, y para saber si llego a sonar.
        speech = _SpeechHandleContextVar.get(None)
        self.latency.on_llm(speech.id if speech else None, time.perf_counter() - started)
        if speech is not None:
            speech.add_done_callback(self.on_reply_done)
        self.set_dictation(state.workflow_id, turn.next_objective)
        logger.info("turn %s fields=%s next=%s status=%s", self.conversation_id, turn.field_updates, turn.next_objective, turn.status)
        self.completed = turn.status == "completed"
        return turn.assistant_message

    def on_reply_done(self, speech) -> None:
        # El cliente siguio hablando y la respuesta no llego a sonar: se deshace
        # el turno, y el siguiente llm_node manda el mensaje completo. Si no, el
        # principio quedaba procesado dos veces y la pregunta, repetida.
        if speech.interrupted and not any(spoken(item) for item in speech.chat_items):
            if self.engine.retract_last_turn(self.conversation_id):
                logger.info("turn retracted %s (reply interrupted before playing)", self.conversation_id)
                self.completed = False

    def set_dictation(self, workflow_id: str, objective: str | None) -> None:
        spec = load_workflow(workflow_id).fields.get(objective) if objective else None
        dictation = spec is not None and spec.type in DICTATED_TYPES
        if dictation != self.dictation:
            self.dictation = dictation
            delay = DICTATION_ENDPOINTING_DELAY if dictation else MAX_ENDPOINTING_DELAY
            self.session.update_options(endpointing_opts={"max_delay": delay})


def build_session() -> AgentSession:
    vad = silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.2)
    return AgentSession(
        vad=vad,
        turn_detection=inference.TurnDetector(),
        max_endpointing_delay=MAX_ENDPOINTING_DELAY,
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
            voice=config.VLLM_TTS_VOICE,
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
        opening = engine.store.get(conversation_id).messages[0].text
    phone = metadata.get("phone")

    session = build_session()
    latency = TurnLatencyTracker()
    session.on("metrics_collected", lambda ev: latency.on_metrics(ev.metrics))
    agent = WorkflowAgent(engine, conversation_id, latency)
    started_at: float | None = None

    async def finalize(reason: str = ""):
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

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev):
        if agent.completed and ev.old_state == "speaking" and ev.new_state == "listening":
            asyncio.create_task(hang_up())

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
