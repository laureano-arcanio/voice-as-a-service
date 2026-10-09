import asyncio
import json
import logging
import time

import httpx
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

from livekit import api

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..conversation.models import Workflow
from ..db import get_sessionmaker, utcnow
from ..models import CallMode, CallRow, CallStatus
from ..runtime import get_conversation_engine
from ..services import calls as call_service
from ..services import quota
from ..services.errors import NotFound, QuotaExceeded
from ..services.reconcile import room_metadata
from .latency import TurnLatencyTracker

logger = logging.getLogger("agent")

# Un pedido sin voz, o con "default", mata el engine de vllm-tts (busca `vivian`, que el
# checkpoint fine-tuneado no tiene; docs/TTS_FINETUNE.md, Trampas 8). Que este servida se
# mira al arrancar (check_default_voice).
if not (settings.vllm_tts_model and settings.vllm_tts_voice):
    raise RuntimeError("Faltan VLLM_TTS_MODEL y/o VLLM_TTS_VOICE en .env")
if settings.vllm_tts_voice.strip().lower() == "default":
    raise RuntimeError('VLLM_TTS_VOICE no puede ser "default": mata vllm-tts. Usar una voz del checkpoint')
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
# El corte de SIP (max_call_duration de la saliente) va despues del del worker, para que
# alcance a sonar la despedida (QUOTA_END_MESSAGE).
SIP_GRACE_SECONDS = 30


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
        except Exception:
            # Error del LLM (ej. 400 de vLLM por contexto): sin esto la llamada queda muda.
            # El turno no se guardo, asi que lo que dijo el cliente entra de nuevo en el
            # siguiente. Si ya sono parte de la respuesta, no se agrega nada.
            logger.exception("turno %s: fallo el LLM", self.conversation_id)
            if first_text is None:
                yield settings.voice_llm_error_reply
            return
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


async def check_default_voice() -> None:
    """Al arrancar: VLLM_TTS_VOICE tiene que estar servida, porque es el respaldo de todas
    las llamadas (si no, cada frase da 400). Si vllm-tts no responde, solo avisa: puede
    estar arrancando."""
    served = await served_voices()
    if served is None:
        logger.warning("vllm-tts no responde: no se pudo verificar VLLM_TTS_VOICE=%r", settings.vllm_tts_voice)
    elif settings.vllm_tts_voice not in served:
        raise RuntimeError(f"VLLM_TTS_VOICE={settings.vllm_tts_voice!r} no esta en vllm-tts ({sorted(served)})")


async def resolve_voice(workflow: Workflow, override: str | None = None) -> str:
    """La voz elegida para la llamada (override, desde la UI) o la del agente
    (agent.voice), si vllm-tts la sirve; si no, VLLM_TTS_VOICE. Una voz inexistente daria
    400 en cada frase de la llamada, y "default" mata vllm-tts."""
    voice = override or workflow.agent.voice
    if not voice or voice == settings.vllm_tts_voice or voice.strip().lower() == "default":
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


async def guard_call(conversation_id: str, limit: float, remaining, cut, check_seconds: float) -> None:
    """Corte duro de la llamada, en todas las modalidades: a los `limit` s (tope del tier y
    del pedido, quota.call_limit_seconds) o cuando `remaining()` (segundos de minutos del
    tier, async; None: sin tope; 0 tambien si el cliente se desactivo) llega a 0.
    Un error de `remaining` (ej. la base) no lo mata: se registra y se reintenta en la
    vuelta siguiente; el tope de duracion sigue corriendo igual."""
    deadline = time.monotonic() + limit
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            logger.info("llamada %s: duracion maxima (%ss), se corta", conversation_id, int(limit))
            await cut("max_duration")
            return
        await asyncio.sleep(min(check_seconds, left))
        if time.monotonic() >= deadline:
            continue
        try:
            quota_left = await remaining()
        except Exception:
            logger.exception("llamada %s: no se pudo mirar la cuota, reintento", conversation_id)
            continue
        if quota_left is not None and quota_left <= 0:
            logger.warning("llamada %s: sin minutos del tier, se corta", conversation_id)
            await cut("quota_exhausted")
            return


async def tag_room(ctx: JobContext, conversation_id: str) -> None:
    """Pone el conversation_id en la metadata de la room de una entrante: es como la
    conciliacion (services/reconcile.py) sabe que la llamada sigue viva."""
    try:
        await ctx.api.room.update_room_metadata(
            api.UpdateRoomMetadataRequest(room=ctx.room.name, metadata=room_metadata(conversation_id)))
    except Exception:
        logger.exception("no se pudo marcar la room %s de la llamada %s", ctx.room.name, conversation_id)


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
        await tag_room(ctx, conversation_id)
    else:
        mode = (CallMode.saliente if metadata.get("phone")
                else CallMode.loadtest if metadata.get("loadtest") else CallMode.prueba)
    state = engine.store.get(conversation_id)
    opening = state.messages[0].text
    phone = metadata.get("phone")

    def update_call(**values) -> None:
        with sessions() as s:
            call_service.update_call(s, conversation_id, **values)

    voice = await resolve_voice(engine.workflow(state), metadata.get("voice"))
    logger.info("llamada %s (%s): agente %s v%s, voz %s", conversation_id, mode, state.agent_id,
                state.agent_version, voice)
    session = build_session(voice)
    latency = TurnLatencyTracker()
    session.on("metrics_collected", lambda ev: latency.on_metrics(ev.metrics))
    started_at: float | None = None
    watchdog: asyncio.Task | None = None

    async def finalize(reason: str = ""):
        # La hora de fin antes de esperar la extraccion: si no, se facturaba ese tiempo.
        ended, ended_at = time.time(), utcnow()
        if watchdog is not None:
            watchdog.cancel()
        # La extraccion del ultimo turno puede seguir corriendo (el resultado sale
        # de ahi); en el motor clasico, si corto el cliente, es la unica.
        await engine.finish(conversation_id)
        with sessions() as s:
            call = s.get(CallRow, conversation_id)
            if call is None or call.status == CallStatus.fallida:
                return
            call_service.update_call(
                s, conversation_id, status=CallStatus.finalizada, ended_reason=(reason or "")[:128], ended_at=ended_at,
                duration_seconds=int(ended - started_at) if started_at else 0, latency=latency.summary())

    ctx.add_shutdown_callback(finalize)

    def fail(error: str, reason: str):
        update_call(status=CallStatus.fallida, error=error[:2000], ended_reason=reason, ended_at=utcnow())
        ctx.shutdown(reason=reason)

    async def hang_up(reason: str = "completed"):
        try:
            await ctx.delete_room()
        except Exception:
            logger.exception("llamada %s: no se pudo borrar la room", conversation_id)
        ctx.shutdown(reason=reason)

    async def say_end_and_hang_up(reason: str):
        session.interrupt()
        try:
            await asyncio.wait_for(
                session.say(settings.quota_end_message, allow_interruptions=False).wait_for_playout(), 15)
        except Exception:
            logger.exception("no se pudo avisar el corte (%s)", reason)
        await hang_up(reason)

    def remaining_now() -> int | None:
        # Minutos del mes que le quedan al cliente (contando esta y sus otras en curso).
        with sessions() as s:
            return call_service.call_remaining_seconds(s, conversation_id)

    def limit_now() -> int:
        with sessions() as s:
            return quota.call_limit_seconds(s, conversation_id, metadata.get("max_duration_seconds"))

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

    update_call(status=CallStatus.sonando)
    # Tope de esta llamada, en todas las modalidades (tambien entrantes y tiers sin limites).
    # Si la base falla aca, el tope por defecto: mejor cortar antes que no cortar.
    try:
        limit = await asyncio.to_thread(limit_now)
    except Exception:
        logger.exception("llamada %s: no se pudo calcular el tope de duracion", conversation_id)
        limit = min(settings.call_max_duration_seconds, settings.call_duration_ceiling_seconds)
    if phone:
        try:
            await ctx.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=await outbound_trunk_id(ctx.api),
                    sip_call_to=phone,
                    # Caller ID: un numero del cliente (prepare_call no despacha una saliente
                    # de un cliente sin numero: 409 no_caller_id). Vacio solo en la de un
                    # admin: Asterisk sale con ANURA_DID, la linea propia (extensions.conf).
                    sip_number=metadata.get("from_number") or "",
                    participant_identity="customer",
                    participant_name="Cliente",
                    wait_until_answered=True,
                    # Respaldo del corte del worker (guard_call), por si este se cae.
                    max_call_duration=Duration(seconds=limit + SIP_GRACE_SECONDS),
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
    # Para todas: corta al tope o cuando se acaban los minutos (o se desactiva el cliente).
    watchdog = asyncio.create_task(guard_call(
        conversation_id, limit, lambda: asyncio.to_thread(remaining_now), say_end_and_hang_up,
        settings.quota_check_seconds))
    await session.say(opening)

if __name__ == "__main__":
    asyncio.run(check_default_voice())
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=settings.livekit_agent_name,
        ws_url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    ))
