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
from .deps import get_calls, get_engine
from .latency import TurnLatencyTracker

logger = logging.getLogger("agent")

openai.tts.AUDIO_STREAM_MODELS.add(config.VLLM_TTS_MODEL)


def pending_user_text(chat_ctx) -> str:
    texts = []
    for item in reversed(chat_ctx.items):
        role = getattr(item, "role", None)
        if role == "assistant":
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

    async def llm_node(self, chat_ctx, tools, model_settings):
        started = time.perf_counter()
        _, turn = await self.engine.process_turn(self.conversation_id, pending_user_text(chat_ctx))
        # El id de la respuesta en curso, para juntar este tiempo con el EOU y el
        # TTS del mismo turno. LiveKit no lo expone en llm_node: es la misma
        # context var privada que usa Agent internamente.
        speech = _SpeechHandleContextVar.get(None)
        self.latency.on_llm(speech.id if speech else None, time.perf_counter() - started)
        logger.info("turn %s fields=%s next=%s status=%s", self.conversation_id, turn.field_updates, turn.next_objective, turn.status)
        self.completed = turn.status == "completed"
        return turn.assistant_message


def build_session() -> AgentSession:
    vad = silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.2)
    return AgentSession(
        vad=vad,
        turn_detection=inference.TurnDetector(),
        max_endpointing_delay=1.0,
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
