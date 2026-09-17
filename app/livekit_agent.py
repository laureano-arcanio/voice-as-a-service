"""Worker del agente de LiveKit: atiende las llamadas salientes despachadas por
app/livekit_dispatch.py, marca al cliente via la troncal SIP saliente (Twilio),
corre la conversacion (STT-LLM-TTS) y escribe el resultado final directo en la
base de datos.

A diferencia de Vapi (que nos avisaba el resultado por webhook a BASE_URL), este
proceso corre en el mismo codebase que la app y comparte la misma base MySQL, asi
que no hace falta ningun webhook: al terminar la llamada este mismo proceso arma
el transcript, corre el scoring (app/scoring.py, sin cambios) y guarda todo.
"""
import asyncio
import json
import time

from google.protobuf.duration_pb2 import Duration
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    get_job_context,
    inference,
    metrics as lk_metrics,
)
from livekit.plugins import elevenlabs, openai, silero
from livekit.plugins.openai import stt as _openai_stt
from openai.types import Reasoning

from . import config, prompts, scoring
from .db import Call, SessionLocal, ensure_schema
from .latency import TurnLatencyTracker


# El plugin de OpenAI (1.8.0) arma la config de la sesion realtime de STT sin el
# campo `delay`, que es el ajuste de latencia de gpt-live-transcribe. Se envuelve
# la funcion del modulo para agregarlo (el SDK ya lo tiene tipado y el API lo
# acepta). Sacar cuando el plugin lo exponga como parametro.
_orig_transcription = _openai_stt._transcription


def _transcription_with_delay(opts):
    transcription = _orig_transcription(opts)
    if config.OPENAI_STT_DELAY:
        transcription.delay = config.OPENAI_STT_DELAY
    return transcription


_openai_stt._transcription = _transcription_with_delay


class ValidationAgent(Agent):
    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Llamar UNA vez terminaste de despedirte del cliente, para cortar la llamada."""
        # Sin esto, shutdown() corta la room de inmediato y se pisa el audio de
        # despedida que el LLM genero en el mismo turno (se corta a mitad o ni
        # llega a sonar) -- hay que esperar a que termine de reproducirse.
        await ctx.wait_for_playout()
        job_ctx = get_job_context()
        if job_ctx:
            # shutdown() solo termina nuestro job/proceso -- no cuelga la llamada
            # SIP en si. Hay que borrar la room para desconectar al participante
            # SIP (el telefono del cliente) y que Twilio corte la llamada real.
            await job_ctx.delete_room()
            job_ctx.shutdown(reason="agent_ended_call")


def _load_call(local_call_id: int):
    with SessionLocal() as s:
        call = s.get(Call, local_call_id)
        if not call:
            return None
        return {
            "phone": call.phone,
            "client": {"name": call.client_name, "gender": call.client_gender, "notes": call.client_notes},
            "questions": json.loads(call.questions_snapshot or "[]"),
        }


def _set_status(local_call_id: int, **fields):
    with SessionLocal() as s:
        call = s.get(Call, local_call_id)
        if not call:
            return
        for k, v in fields.items():
            setattr(call, k, v)
        s.commit()


def _finalize_and_score(local_call_id: int, started_at: float, ended_reason: str, transcript: list,
                        latency: dict | None = None):
    with SessionLocal() as s:
        call = s.get(Call, local_call_id)
        if not call:
            return
        call.status = "finalizada"
        call.ended_reason = ended_reason[:120]
        call.duration_seconds = int(time.time() - started_at)
        call.transcript_json = json.dumps(transcript, ensure_ascii=False)
        call.latency_json = json.dumps(latency, ensure_ascii=False) if latency else ""
        s.commit()
        if not transcript:
            return
        try:
            questions = json.loads(call.questions_snapshot or "[]")
            bands = json.loads(call.bands_snapshot or "[]")
            result = scoring.score_call(transcript, questions, bands)
            call.score = result["score"]
            call.outcome = result["outcome"]
            call.score_detail = json.dumps(result, ensure_ascii=False)
            call.score_error = ""
        except Exception as e:  # noqa: BLE001
            call.score_error = str(e)
        s.commit()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    metadata = json.loads(ctx.job.metadata or "{}")
    local_call_id = metadata.get("local_call_id")
    if local_call_id is None:
        return

    data = _load_call(local_call_id)
    if not data:
        return

    started_at = time.time()
    transcript: list = []
    latency = TurnLatencyTracker()
    finalized = False
    dial_succeeded = False

    def on_conversation_item_added(event):
        item = event.item
        role = getattr(item, "role", None)
        if role == "assistant":
            role_label = "agente"
        elif role == "user":
            role_label = "cliente"
        else:
            return
        text = getattr(item, "text_content", None)
        if text:
            transcript.append({"role": role_label, "text": text})

    async def finalize(reason: str = "unknown"):
        nonlocal finalized
        if finalized:
            return
        finalized = True
        if not dial_succeeded:
            # La llamada nunca llego a conectar (dial fallido); ese path ya dejo
            # status="fallida" escrito, no lo pisamos con "finalizada".
            return
        # _finalize_and_score hace una llamada HTTP bloqueante a OpenAI (scoring).
        # Corrida directa (sin hilo) trababa el event loop del worker el tiempo
        # suficiente para que el framework lo de por colgado y lo mate a los 10s
        # (shutdown_process_timeout) antes de que el commit del score llegue a
        # persistir -- por eso corre en un hilo aparte.
        latency.log_summary()
        await asyncio.to_thread(
            _finalize_and_score, local_call_id, started_at, reason, transcript, latency.summary()
        )

    ctx.add_shutdown_callback(finalize)

    system_prompt = prompts.build_system_prompt(
        data["questions"], config.AGENT_NAME, config.DEALERSHIP_NAME, data["client"]
    )
    greeting = prompts.first_message(config.AGENT_NAME, config.DEALERSHIP_NAME, data["client"])

    # Un solo VAD compartido: lo usa la sesion para detectar habla/interrupciones
    # y tambien el STT de OpenAI para hacer commit del buffer de audio, porque
    # gpt-live-transcribe no tiene endpointing del lado del servidor (sin esto el
    # plugin cargaria una segunda instancia de Silero por su cuenta).
    # min_silence_duration: default 0.55s. Como gpt-live-transcribe no tiene
    # endpointing propio, el plugin recien hace commit del audio cuando este VAD
    # detecta silencio, y ese tiempo se suma entero a la latencia STT (medido:
    # ~1.2s por turno con el default). 0.3s la recorta a costa de cortar pausas
    # cortas del cliente a mitad de frase.
    vad = silero.VAD.load(min_silence_duration=0.3)
    session = AgentSession(
        vad=vad,
        turn_detection=inference.TurnDetector(),
        # Default es 2.5-3.0s (ver livekit.agents.voice.turn._ENDPOINTING_DEFAULTS)
        # -- el turn-detector rara vez esta seguro con respuestas cortas ("Si"/"No")
        # y cae al tope casi siempre. Bajarlo acota ese peor caso a costa de poder
        # cortar al cliente si hace una pausa mas larga que esto a mitad de frase.
        max_endpointing_delay=1.0,
        # gpt-live-transcribe es realtime-only: el plugin abre una sesion de
        # transcripcion por WebSocket y emite parciales (interim) mientras el
        # cliente habla, asi el turn-detector y el LLM arrancan antes.
        stt=openai.STT(
            model=config.OPENAI_STT_MODEL,
            language="es",
            api_key=config.OPENAI_API_KEY,
            vad=vad,
        ),
        # Responses API por WebSocket persistente (use_websocket=True, default):
        # evita el handshake HTTP por turno y, a diferencia del plugin de chat
        # completions, informa prompt_cached_tokens en las metricas (el otro
        # siempre reporta 0, no lo parsea). El prefijo del prompt (system +
        # historial) es identico entre turnos, asi que OpenAI lo cachea solo.
        # reasoning none: sin cadena de razonamiento antes del primer token (el
        # plugin solo lo setea para los modelos que conoce, y gpt-5.4-nano no
        # esta en esa lista). verbosity low acorta respuestas que se leen en voz alta.
        llm=openai.responses.LLM(
            model=config.OPENAI_MODEL,
            temperature=0.4,
            reasoning=Reasoning(effort="none"),
            verbosity="low",
            api_key=config.OPENAI_API_KEY,
        ),
        tts=elevenlabs.TTS(
            voice_id=config.ELEVENLABS_VOICE_ID,
            model=config.ELEVENLABS_MODEL,
            api_key=config.ELEVENLABS_API_KEY,
            # Sin esto flash_v2_5 autodetecta el idioma por frase y en frases
            # cortas ("Perfecto.", "Genial.") puede caer en otro idioma y
            # pronunciar mal tildes y entonacion. language_code fuerza espanol.
            language="es",
            # stability/similarity_boost son obligatorios en VoiceSettings; estos
            # son los defaults de ElevenLabs. speed va de 0.8 a 1.2.
            voice_settings=elevenlabs.VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                speed=config.ELEVENLABS_SPEED,
            ),
        ),
    )
    session.on("conversation_item_added", on_conversation_item_added)
    # Desglose de latencia por turno: app/latency.py agrupa EOU/LLM/TTS por
    # speech_id y loguea una linea por turno ("turno N | total X = eou + ttft +
    # tts ...") mas un resumen al colgar; el detalle queda en calls.latency_json.
    # log_metrics() sigue emitiendo el detalle crudo de cada componente.
    def on_metrics_collected(ev):
        lk_metrics.log_metrics(ev.metrics)
        latency.on_metrics(ev.metrics)

    session.on("metrics_collected", on_metrics_collected)

    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        if participant.identity == "customer":
            ctx.shutdown(reason="customer_hangup")

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    await session.start(agent=ValidationAgent(instructions=system_prompt), room=ctx.room)

    _set_status(local_call_id, status="sonando")
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=config.LIVEKIT_SIP_TRUNK_ID,
                sip_call_to=data["phone"],
                participant_identity="customer",
                participant_name="Cliente",
                wait_until_answered=True,
                max_call_duration=Duration(seconds=config.CALL_MAX_DURATION_SECONDS),
            )
        )
    except api.SipCallError as e:
        _set_status(local_call_id, status="fallida", score_error=str(e))
        ctx.shutdown(reason="sip_call_failed")
        return
    except Exception as e:  # noqa: BLE001
        _set_status(local_call_id, status="fallida", score_error=str(e))
        ctx.shutdown(reason="dispatch_error")
        return

    dial_succeeded = True
    _set_status(local_call_id, status="en_curso")
    # El saludo es interrumpible como cualquier otro turno (default de la
    # sesion): si el cliente habla encima, el agente se calla y escucha.
    await session.say(greeting)


if __name__ == "__main__":
    # El worker escribe columnas nuevas (latency_json); asegurarse de que existan
    # aunque la app todavia no haya arrancado contra esta base.
    ensure_schema()
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=config.LIVEKIT_AGENT_NAME,
        ws_url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
        # Default es 10s -- muy poco para esperar el scoring (app/scoring.py usa
        # timeout=90 en su llamada a OpenAI). Dar margen para que el hilo de
        # _finalize_and_score termine antes de que el proceso sea matado.
        shutdown_process_timeout=100.0,
    ))
