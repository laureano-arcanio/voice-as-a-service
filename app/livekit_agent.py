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
import re
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
from livekit.plugins import openai, silero
from openai.types import Reasoning

from . import config, prompts, scoring
from .db import Call, SessionLocal, active_questionnaire, ensure_schema
from .latency import TurnLatencyTracker


# Bug del server qwenllm/qwen3-asr (probado en vivo): la respuesta de
# /v1/audio/transcriptions viene con el template interno del modelo sin
# despojar, antepuesto al transcript real -- ej. para "Hola, ..." devuelve
# literal `"language Spanish<asr_text>Hola, ..."` (o "language None<asr_text>"
# cuando no detecta habla). Se parchea aca porque es un problema del lado del
# servidor, no del plugin ni de nuestro codigo -- sacar si una version nueva
# de la imagen lo arregla.
_ASR_TEMPLATE_PREFIX_RE = re.compile(r"^language\s+\S+<asr_text>")
_orig_stt_recognize_impl = openai.STT._recognize_impl


async def _recognize_impl_stripped(self, buffer, *, language=None, conn_options=None, **kwargs):
    event = await _orig_stt_recognize_impl(
        self, buffer, language=language, conn_options=conn_options, **kwargs
    )
    for alt in event.alternatives:
        alt.text = _ASR_TEMPLATE_PREFIX_RE.sub("", alt.text)
    return event


openai.STT._recognize_impl = _recognize_impl_stripped

# El plugin de TTS solo pide stream_format="audio" (streaming de bytes crudos)
# para los nombres de modelo de OpenAI que ya conoce (tts-1, tts-1-hd); para
# cualquier otro cae a stream_format="sse". Registramos nuestro modelo local
# para que pida "audio" -- probado en vivo que hace falta (con "sse" el
# servidor devuelve 400 al pedir cualquier `speed` != 1.0, ver VLLM_TTS_SPEED
# en config.py).
openai.tts.AUDIO_STREAM_MODELS.add(config.VLLM_TTS_MODEL)


class SalesAgent(Agent):
    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Llamar UNA vez terminaste de despedirte del interesado, para cortar la llamada."""
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
            "test_mode": bool(call.test_mode),
            "client": {"name": call.client_name, "gender": call.client_gender, "notes": call.client_notes},
            "questions": json.loads(call.questions_snapshot or "[]"),
        }


def _create_inbound_call(phone: str, room_name: str) -> int:
    """Arma el registro de Call para una llamada ENTRANTE: no la disparo
    nuestro dashboard (no hay local_call_id previo en la metadata del job --
    la trajo la regla de dispatch de LiveKit, ver troncal/dispatch rule
    entrante en el proyecto de LiveKit). Es el caso principal del agente
    comercial: un interesado llama a la empresa. Mismo cuestionario de
    calificacion que las salientes; el nombre es siempre
    config.INBOUND_CALLER_NAME (no hay forma de identificar al que llama)."""
    questions, bands = active_questionnaire()
    with SessionLocal() as s:
        call = Call(
            phone=phone or "(entrante)",
            client_name=config.INBOUND_CALLER_NAME,
            status="pendiente",
            provider="livekit",
            provider_call_id=room_name,
            questions_snapshot=json.dumps(questions, ensure_ascii=False),
            bands_snapshot=json.dumps(bands, ensure_ascii=False),
        )
        s.add(call)
        s.commit()
        return call.id


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
    # Sin local_call_id: no la disparo nuestro dashboard (app/main.py siempre
    # lo manda), asi que es una llamada ENTRANTE -- la trajo la regla de
    # dispatch de LiveKit (troncal SIP entrante -> agent_name=voice-as-a-service).
    # El que llama ya esta conectado a la room como participante SIP (LiveKit
    # lo pone ahi antes de despachar el agente).
    is_inbound = local_call_id is None
    if is_inbound:
        try:
            participant = await asyncio.wait_for(
                ctx.wait_for_participant(kind=[rtc.ParticipantKind.PARTICIPANT_KIND_SIP]),
                timeout=15,
            )
            phone = participant.attributes.get("sip.phoneNumber", "")
        except asyncio.TimeoutError:
            phone = ""
        local_call_id = _create_inbound_call(phone, ctx.room.name)

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
        # _finalize_and_score hace una llamada HTTP bloqueante al LLM (scoring).
        # Corrida directa (sin hilo) trababa el event loop del worker el tiempo
        # suficiente para que el framework lo de por colgado y lo mate a los 10s
        # (shutdown_process_timeout) antes de que el commit del score llegue a
        # persistir -- por eso corre en un hilo aparte.
        latency.log_summary()
        await asyncio.to_thread(
            _finalize_and_score, local_call_id, started_at, reason, transcript, latency.summary()
        )

    ctx.add_shutdown_callback(finalize)

    # El modo prueba simula una llamada ENTRANTE (vos hacés de interesado que
    # llama a la empresa); solo las salientes reales por SIP se presentan como
    # devolucion de contacto a un lead. El saludo es el mismo en los dos casos.
    answers_call = is_inbound or data["test_mode"]
    system_prompt = prompts.build_system_prompt(
        data["questions"], config.AGENT_NAME, config.COMPANY_NAME, data["client"], inbound=answers_call
    )
    greeting = prompts.first_message(config.AGENT_NAME, config.COMPANY_NAME, data["client"])

    # Un solo VAD compartido: lo usa la sesion para detectar habla/interrupciones
    # y tambien el STT para hacer commit del buffer de audio -- vllm-stt
    # (Qwen3-ASR via /v1/audio/transcriptions) es un endpoint REST por-turno,
    # sin sesion realtime por WebSocket ni endpointing propio (a diferencia de
    # gpt-live-transcribe, que se uso antes), asi que el plugin siempre depende
    # de este VAD para saber cuando cortar y mandar el audio.
    # min_silence_duration: default 0.55s. Ese tiempo se suma entero a la
    # latencia de STT (medido con gpt-live-transcribe: ~1.2s por turno con el
    # default). 0.3s la recorta a costa de cortar pausas cortas del cliente a
    # mitad de frase.
    # min_speech_duration: default 0.05s (!) -- de sobra para audio limpio de
    # navegador, pero en una llamada real por telefono/Bluetooth un click o
    # pop de linea de 50ms alcanza para que el VAD piense "el cliente empezo a
    # hablar" e interrumpa al agente a mitad de frase. Probado en llamadas
    # reales: eso deja un turno del agente cortado + un "turno de cliente"
    # con texto basura (STT transcribiendo ruido como texto en otro idioma) --
    # y ese contexto corrupto confunde al LLM en el turno siguiente (alucina
    # repitiendo el saludo completo, con un turno de cliente inventado).
    # 0.2s sigue siendo instantaneo para habla real (una palabra ya dura mas
    # que eso) pero filtra la mayoria de esos ruidos cortos.
    vad = silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.2)
    session = AgentSession(
        vad=vad,
        turn_detection=inference.TurnDetector(),
        # Default es 2.5-3.0s (ver livekit.agents.voice.turn._ENDPOINTING_DEFAULTS)
        # -- el turn-detector rara vez esta seguro con respuestas cortas ("Si"/"No")
        # y cae al tope casi siempre. Bajarlo acota ese peor caso a costa de poder
        # cortar al cliente si hace una pausa mas larga que esto a mitad de frase.
        max_endpointing_delay=1.0,
        # vllm-stt (Qwen3-ASR-1.7B, ver docker-compose.yml): use_realtime=False
        # fuerza el modo REST -- el plugin no reconoce este modelo como uno de
        # los "realtime" de OpenAI, pero se lo dejamos explicito para no
        # depender de esa deteccion automatica. Sin transcript parcial mientras
        # el cliente habla (ver comentario del VAD arriba).
        stt=openai.STT(
            model=config.VLLM_STT_MODEL,
            language="es",
            base_url=config.VLLM_STT_BASE_URL,
            api_key=config.VLLM_API_KEY,
            use_realtime=False,
            vad=vad,
        ),
        # Responses API (vllm-llm, Qwen3.5-4B): probado que vLLM soporta
        # /v1/responses con reasoning.effort="none" igual que OpenAI (0 tokens
        # de razonamiento, responde directo). verbosity="low" queda igual --
        # vLLM ignora los campos que no reconoce en vez de rechazarlos.
        # use_websocket=False: el default del plugin (True) abre una sesion
        # WS persistente contra /v1/responses -- eso es especifico de la
        # implementacion de OpenAI. vLLM solo sirve ese endpoint por HTTP
        # normal (probado: WS devuelve 403). Sin el WS se pierde el ahorro del
        # handshake por turno, pero sigue siendo un solo POST corto (misma red
        # que el contenedor).
        # store=False: sin esto, el plugin manda solo los mensajes nuevos de
        # cada turno con `previous_response_id` apuntando a la respuesta
        # anterior (asumiendo que el server la guardo, como hace OpenAI de
        # verdad). vLLM no la persiste -- probado en vivo: el turno 2 de
        # cualquier llamada real tiraba 404 "Response with id ... not found"
        # y mataba toda la sesion. store=False hace que reenvie el historial
        # completo en cada turno (mas payload, pero funciona).
        llm=openai.responses.LLM(
            model=config.VLLM_LLM_MODEL,
            temperature=0.4,
            reasoning=Reasoning(effort="none"),
            verbosity="low",
            base_url=config.VLLM_LLM_BASE_URL,
            api_key=config.VLLM_API_KEY,
            use_websocket=False,
            store=False,
        ),
        # vllm-tts (Qwen3-TTS-12Hz-1.7B-Base): /v1/audio/speech con streaming,
        # usando una voz clonada (VLLM_TTS_VOICE, ver config.py) subida una
        # sola vez al server -- el server infiere task_type=Base solo con el
        # nombre, asi que no hace falta mandar ref_audio en cada request.
        # response_format="pcm": el default del plugin (mp3) no es streameable
        # en este servidor (400: "Streaming requires response_format='pcm' or
        # 'wav'"). pcm evita ademas decodificar mp3 del lado del cliente.
        tts=openai.TTS(
            model=config.VLLM_TTS_MODEL,
            voice=config.VLLM_TTS_VOICE,
            speed=config.VLLM_TTS_SPEED,
            base_url=config.VLLM_TTS_BASE_URL,
            api_key=config.VLLM_API_KEY,
            response_format="pcm",
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
        # En modo prueba y en llamadas entrantes no hay un identity fijo
        # (en prueba te conectaste vos desde LiveKit Meet; en una entrante el
        # identity lo pone LiveKit, no nosotros) -- cualquier desconexion
        # corta, porque solo hay un participante humano esperado en la room.
        if is_inbound or data["test_mode"] or participant.identity == "customer":
            ctx.shutdown(reason="customer_hangup")

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    await session.start(agent=SalesAgent(instructions=system_prompt), room=ctx.room)

    if is_inbound:
        # El que llama ya esta conectado (LiveKit lo puso en la room antes de
        # despachar el agente) -- no hay nada que marcar ni esperar.
        pass
    elif data["test_mode"]:
        # Sin telefono: no hay nada que marcar por SIP. Se espera a que
        # alguien se conecte a esta room por LiveKit (link armado en
        # app/livekit_dispatch.py::build_test_join_url, mostrado en el
        # dashboard) y recien ahi arranca la conversacion, igual que con una
        # llamada real.
        _set_status(local_call_id, status="sonando")
        try:
            await asyncio.wait_for(ctx.wait_for_participant(), timeout=300)
        except asyncio.TimeoutError:
            _set_status(local_call_id, status="fallida", score_error="Nadie se conecto a la room de prueba (timeout 5min)")
            ctx.shutdown(reason="test_mode_timeout")
            return
    else:
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
        # timeout=90 en su llamada al LLM local). Dar margen para que el hilo de
        # _finalize_and_score termine antes de que el proceso sea matado.
        shutdown_process_timeout=100.0,
    ))
