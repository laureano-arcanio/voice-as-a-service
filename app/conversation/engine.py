import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..llm.resolver import LLMResolver
from ..tools.conversation import ConversationTools
from . import variables
from .models import (
    AgentTurn,
    Channel,
    ConversationState,
    Extraction,
    Message,
    TurnMedia,
    Workflow,
)
from .store import ConversationStore
from .workflow import (
    OFF_TOPIC_ID,
    OFF_TOPIC_REASON,
    check_updates,
)

if TYPE_CHECKING:
    from ..agents.definitions import DefinitionSource

logger = logging.getLogger(__name__)
# El modulo, con otro nombre donde el parametro `variables` lo tapa (new_conversation).
_vars = variables


def _llm_info(llm) -> dict:
    """Proveedor y modelo del turno, para la traza, cuando contesto uno externo o el respaldo."""
    info = getattr(llm, "info", None)
    return info() if callable(info) else {}


def _usage(result) -> dict:
    """Tokens de una respuesta del LLM (AgentTurn o Extraction), para la traza; 0 si el proveedor no los da."""
    return {"input_tokens": getattr(result, "input_tokens", 0) or 0,
            "output_tokens": getattr(result, "output_tokens", 0) or 0}


def _add_usage(state: ConversationState, result) -> None:
    """Suma los tokens de la respuesta a los de la conversacion (conversations.llm_*_tokens, reportes)."""
    usage = _usage(result)
    state.llm_input_tokens += usage["input_tokens"]
    state.llm_output_tokens += usage["output_tokens"]


def _last_agent_reply(state: ConversationState) -> str:
    """La ultima respuesta del agente antes del turno en curso, para la repeticion (repeat_last_reply,
    docs/features/ATENCION_TURNO.md). La misma regla que la "ultima pregunta" del watchdog de silencio
    (app/voice/worker.py): las piernas y los avisos de una derivacion se guardan como assistant y no
    cuentan; sin ninguna, el saludo. Vacia si el agente todavia no dijo nada."""
    for m in reversed(state.messages):
        if m.role == "assistant" and m.person is None and m.handoff_leg is None and m.text.strip():
            return m.text
    return next((m.text for m in state.messages if m.role == "assistant"), "")


def _use_last_reply(turn: AgentTurn, state: ConversationState) -> None:
    """La repeticion sin texto del modelo repite la ultima respuesta tal cual (sin volver a saludar). Si el
    modelo escribio algo antes de llamar a la herramienta, se respeta: no se duplica el audio. Los dos
    caminos del turno (clásico y _external_turn) usan este helper."""
    if turn.repeat and not turn.assistant_message.strip():
        turn.assistant_message = _last_agent_reply(state)


# Cuanto espera un turno a la extraccion del anterior. Corre mientras suena la
# respuesta y el cliente contesta (varios segundos), asi que casi nunca espera;
# si se pasa, el turno sigue con el estado viejo y la conversacion completa.
EXTRACTION_WAIT = 1.5


class ConversationEngine:
    """Un solo motor. El LLM conversa con el prompt armado de la definicion, usa las herramientas del agente y
    las de la plataforma (terminar, derivar), y decide cuando termina. Los datos los saca otra llamada al LLM,
    la extraccion, una vez al terminar. Con `external` en la definicion (tu propio agente) cada turno lo contesta
    el endpoint del cliente, sin el prompt de la definicion ni extraccion (app/llm/external.py).
    El canal no cambia el trabajo del motor: solo el formato que se pide en el prompt (app/llm/prompt.py).

    definitions: de donde salen los workflows (agentes de la base o de referencia;
    app/agents). Sin pasarla, los agentes de referencia del repo (eval y tests)."""

    def __init__(self, llm, store: ConversationStore, definitions: "DefinitionSource | None" = None):
        from ..agents.templates import ReferenceDefinitions

        self.llm = llm
        # Que LLM atiende cada turno segun workflow.llm (conexiones BYOK; app/llm/resolver.py).
        # Sin plan en el agente es self.llm, igual que antes.
        self.llms = LLMResolver(llm, store.sessions)
        self.store = store
        self.definitions = definitions or ReferenceDefinitions()
        # El store completa con la definicion la columna de los reportes (conversion).
        store.definitions = self.definitions
        self.extractions: dict[str, list[asyncio.Task]] = {}   # extracciones en curso por conversacion, en orden
        # Herramientas del cliente (http y code, docs/features/HERRAMIENTAS.md): las del agente y su contexto, por turno.
        self.tools = ConversationTools(store.sessions)
        self.external = None    # tu propio agente, al primer turno (app/llm/external.py)
        self._late_pre_calls: set[asyncio.Task] = set()     # pre-calls vencidos: que terminen y dejen su fila

    def workflow(self, state: ConversationState) -> Workflow:
        return self.definitions.get(state.agent_id, state.agent_version)

    def start_conversation(self, agent_id: str, client_id: str | None = None, *, channel: Channel = "voice",
                           opening: bool | str = True, variables: dict[str, dict] | None = None,
                           call: dict | None = None) -> tuple[ConversationState, str]:
        """Crea y guarda la conversacion con la version vigente del agente. KeyError si
        no existe o esta archivado."""
        state, text = self.new_conversation(agent_id, client_id, channel=channel, opening=opening,
                                            variables=variables, call=call)
        self.store.save(state)
        return state, text

    def new_conversation(self, agent_id: str, client_id: str | None = None, session=None, *,
                         channel: Channel = "voice", opening: bool | str = True,
                         variables: dict[str, dict] | None = None,
                         call: dict | None = None) -> tuple[ConversationState, str]:
        """Como start_conversation pero sin guardarla: para guardarla en la misma
        transaccion que la llamada (services/calls.py, store.add). session: la del que
        llama, para leer el agente sin pedir otra conexion.

        opening: True, la apertura del workflow (el agente habla primero, como en una
        llamada); False, sin apertura (WhatsApp entrante: el cliente escribe primero y su
        mensaje es el turno 1); un texto, esa apertura (plantilla saliente).

        variables: los valores por fuente, `contact` (agenda o columnas de la campaña) y `request` (el pedido de
        la API o del panel), app/conversation/variables.py. call: los datos de la llamada para {{call.*}}
        (from, to, phone, direction, mode; el id lo pone el motor). El primer mensaje se renderiza con ellas; con
        pre-call queda sin renderizar hasta que este traiga lo suyo (run_pre_call)."""
        version, workflow = self.definitions.current(agent_id, session)
        state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            agent_id=agent_id, agent_version=version, client_id=client_id, channel=channel,
            fields={name: None for name in workflow.analysis_fields},
        )
        _vars.start(state, workflow, variables, call)
        if opening is False:
            return state, ""
        text = workflow.first_message if opening is True else opening
        if not (workflow.workflows and workflow.workflows.pre_call):
            text = _vars.render(text, state, workflow)
        state.messages = [Message(role="assistant", text=text)]
        return state, text

    async def run_pre_call(self, conversation_id: str, actor: str | None = None) -> str | None:
        """El pre-call del agente, si tiene, antes de que empiece la conversacion. Espera hasta su timeout_ms: si
        falla o vence, la conversacion sigue sin datos (la tarea no se cancela, para que quede su fila en tool_runs,
        y lo que traiga tarde se ignora). Devuelve la apertura renderizada en voz; None en WhatsApp o sin pre-call."""
        state = self.store.get(conversation_id)
        if state is None:
            return None
        workflow = self.workflow(state)
        pre_call = workflow.workflows.pre_call if workflow.workflows else None
        if pre_call is None:
            return None
        task = asyncio.ensure_future(self.tools.run_workflow(workflow, state, pre_call.tool, actor, "pre_call"))
        done, _ = await asyncio.wait([task], timeout=pre_call.timeout_ms / 1000)
        assigned, hidden = {}, set()
        if not done:
            logger.warning("pre-call %s: paso los %s ms, sigue sin datos", conversation_id, pre_call.timeout_ms)
            self._late_pre_calls.add(task)
            task.add_done_callback(self._late_pre_call_done)
        elif task.exception() is not None:
            logger.error("pre-call %s: fallo", conversation_id, exc_info=task.exception())
        else:
            assigned, hidden = task.result().assigned, task.result().hidden
        return self._apply_pre_call(conversation_id, workflow, assigned, hidden)

    def _late_pre_call_done(self, task: asyncio.Task) -> None:
        self._late_pre_calls.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("pre-call: fallo despues del tope", exc_info=task.exception())

    def _apply_pre_call(self, conversation_id: str, workflow: Workflow, assigned: dict, hidden: set[str]) -> str | None:
        """Suma lo que trajo el pre-call a las variables (fuente pre_call:<slug>, pisa al contacto y al pedido; las
        ocultas solo para herramientas). En voz renderiza el primer mensaje, tambien sin datos: no se lee
        "{{nombre}}"."""
        state = self.store.get(conversation_id)
        slug = workflow.workflows.pre_call.tool if workflow.workflows and workflow.workflows.pre_call else "pre_call"
        variables.merge(state, assigned, f"pre_call:{slug}", hidden)
        text = None
        if state.channel != "whatsapp":
            # La ultima: en el respaldo de equipo a agente, la apertura va despues de lo hablado en la espera.
            message = next((m for m in reversed(state.messages) if m.role == "assistant"), None)
            if message is not None:
                text = message.text = variables.render(message.text, state, workflow)
        self.store.save(state)
        return text

    async def process_turn(self, conversation_id: str, user_message: str,
                           on_message: Callable[[str], None] | None = None, *,
                           media: TurnMedia | None = None, actor: str | None = None, dtmf: str | None = None,
                           analyze: bool = True) -> tuple[ConversationState, AgentTurn]:
        """on_message recibe assistant_message a medida que lo genera el LLM
        (agente de voz). Devuelve sin esperar la extraccion de este turno.
        analyze: False, el turno que termina no lanza la extraccion (la corre la cola de la app,
        run_final_analysis).
        media: si el mensaje vino por audio y si la respuesta sale como nota de
        voz (WhatsApp); cambia el prompt del turno y no se guarda.
        actor: quien escribe (wa:<wa_id>): el numero de {{call.from}} en las herramientas.
        dtmf: el turno son teclas que marco quien llama (user_message "Marcó <dtmf>", app/voice/dtmf.py): queda en
        Message.dtmf del mensaje del usuario."""
        media = media or TurnMedia()
        await self.wait_extraction(conversation_id, EXTRACTION_WAIT)
        state = self.store.get(conversation_id)
        if state is None:
            raise KeyError(conversation_id)
        state.media = media
        workflow = self.workflow(state)
        if workflow.external is not None:
            return await self._external_turn(workflow, state, user_message, media, on_message, actor, dtmf)
        # Turno del usuario (1 = su primer mensaje): elige la etapa de workflow.llm.
        llm = self.llms.for_turn(workflow, 1 + sum(m.role == "user" for m in state.messages), state.client_id)
        if state.progress.system_prompt is None:
            # Una vez, en el primer turno (ya corrio el pre-call): lo que asigne una herramienta despues no lo
            # cambia, y el prompt queda igual en todos los turnos (prefix cache de vLLM).
            from ..llm.prompt import build_system_prompt
            state.progress.system_prompt = build_system_prompt(workflow, state.channel, state)
            self.store.save(state)

        turn_tools = self.tools.turn(workflow, state, actor)
        started = time.perf_counter()
        extra = {"tools": turn_tools} if turn_tools else {}
        result = await llm.converse(workflow, state, user_message, on_message=on_message, **extra)
        trace = [{"kind": "turno", "input": user_message, "ms": round((time.perf_counter() - started) * 1000),
                  "reasoning": result.reasoning, "output": result.raw or result.model_dump_json(),
                  **_usage(result), **_llm_info(llm)}]
        if turn_tools:
            trace += turn_tools.trace

        # Una extraccion atrasada pudo guardar mientras el LLM respondia: se
        # relee el estado y el turno solo agrega lo suyo.
        state = self.store.get(conversation_id)
        # Las herramientas del turno que se deshizo van en esta respuesta y se limpian aca: si este tambien se
        # deshace, vuelven con las suyas (retract_last_turn).
        tool_calls = state.progress.carry_tools + (result.tools or [])
        state.progress.carry_tools = []
        undo = state.model_dump(include={"status", "fields", "progress"}, exclude={"progress": {"undo"}})
        undo["n_messages"] = len(state.messages)
        state.status = result.status
        _add_usage(state, result)
        # Fuera de tema (end_call): el outcome lo pone aca; la extraccion no toca progress.outcome.
        state.progress.outcome = OFF_TOPIC_ID if result.end_reason == OFF_TOPIC_REASON else None
        state.progress.undo = undo
        if turn_tools:
            for slug, values, hidden in turn_tools.assigned:
                variables.merge(state, values, f"tool:{slug}", hidden)
        # La repeticion (repeat_last_reply): sin texto del modelo, la ultima respuesta; un turno repetido no
        # completa ni dispara la extraccion (repeat no toca status).
        _use_last_reply(result, state)
        state.messages += [Message(role="user", text=user_message, voice_note=media.user_voice_note, dtmf=dtmf),
                           Message(role="assistant", text=result.assistant_message, llm=trace,
                                   handoff=result.handoff, tools=tool_calls or None, repeat=result.repeat)]
        self.store.save(state)

        # Igual en todos los canales: se extrae al terminar (end_call) o al cortar la conversacion
        # (finish: el corte de la llamada, o el cierre o vencimiento del chat).
        if analyze and result.status == "completed" and workflow.analysis is not None:
            self._launch_extraction(conversation_id, len(state.messages) - 1)
        return state, result

    async def _external_turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                             media: TurnMedia, on_message: Callable[[str], None] | None, actor: str | None,
                             dtmf: str | None = None) -> tuple[ConversationState, AgentTurn]:
        """Motor external (app/llm/external.py): contesta el endpoint del cliente, sin extraccion. Si falla
        sin haber hablado, el agente dice error_message; con max_errors seguidos (o sin el plan), corta o deriva
        segun on_errors."""
        from ..llm.external import ExternalAgents, ExternalError
        if self.external is None:
            self.external = ExternalAgents(self.store.sessions)
        cfg = workflow.external
        try:
            result = await self.external.turn(workflow, state, user_message, on_message, actor)
            turn, trace, errors = result.turn, result.trace, 0
            trace = {**trace, **_usage(turn)}
        except ExternalError as e:
            errors = state.progress.external_errors + 1
            trace = e.trace or {"kind": "turno", "input": user_message, "ms": 0, "provider": "external",
                                "error": str(e)}
            turn = AgentTurn(assistant_message=cfg.error_message)
            if e.code == "external_agent_not_in_plan":
                turn.status, turn.end_reason = "completed", "external_agent_not_in_plan"
            elif errors >= cfg.max_errors:
                area = cfg.on_errors.split(":", 1)[1] if cfg.on_errors.startswith("transfer:") else None
                name = next((a["name"] for a in state.progress.handoff_areas if a["id"] == area), None)
                if name:
                    turn.handoff = name
                else:
                    turn.status, turn.end_reason = "completed", "external_error"
            if on_message is not None:
                on_message(turn.assistant_message)
        state = self.store.get(state.conversation_id)
        undo = state.model_dump(include={"status", "fields", "progress"}, exclude={"progress": {"undo"}})
        undo["n_messages"] = len(state.messages)
        state.progress.undo = undo
        state.progress.external_errors = errors
        state.status = turn.status
        _add_usage(state, turn)
        # Igual que en el camino clasico: fuera de tema (end_call con ese motivo) es el unico resultado
        # de plataforma que se asigna.
        state.progress.outcome = OFF_TOPIC_ID if turn.end_reason == OFF_TOPIC_REASON else None
        # La repeticion (repeat_last_reply), igual que en el camino clasico: sin texto del modelo, la ultima
        # respuesta (docs/features/ATENCION_TURNO.md). Sin esto, un agente propio que la llama queda mudo.
        _use_last_reply(turn, state)
        state.messages += [Message(role="user", text=user_message, voice_note=media.user_voice_note, dtmf=dtmf),
                           Message(role="assistant", text=turn.assistant_message, llm=[trace],
                                   handoff=turn.handoff, repeat=turn.repeat)]
        self.store.save(state)
        return state, turn

    def mark_voice_note(self, conversation_id: str) -> bool:
        """Marca la ultima respuesta del agente como enviada en nota de voz
        (WhatsApp, despues de un envio exitoso). Sin await: no se intercala con
        la extraccion, que relee y guarda el estado."""
        state = self.store.get(conversation_id)
        if state is None:
            return False
        for message in reversed(state.messages):
            if message.role == "assistant":
                message.voice_note = True
                self.store.save(state)
                return True
        return False

    def mark_recording(self, conversation_id: str, recording: int, role: str = "assistant") -> bool:
        """Asocia el numero del WAV grabado (record_audio) al ultimo mensaje de ese rol
        (WhatsApp: el audio entrante al mensaje del usuario, la nota de voz saliente al del
        agente). Sin await, igual que mark_voice_note."""
        state = self.store.get(conversation_id)
        if state is None:
            return False
        for message in reversed(state.messages):
            if message.role == role:
                message.recording = recording
                self.store.save(state)
                return True
        return False

    def _launch_extraction(self, conversation_id: str, reply: int, *, reset: bool = False, kind: str = "extraccion",
                           workflow: Workflow | None = None, raise_errors: bool = False) -> asyncio.Task:
        tasks = self.extractions.setdefault(conversation_id, [])
        previous = tasks[-1] if tasks else None
        task = asyncio.create_task(self._extract(conversation_id, reply, previous, reset=reset, kind=kind,
                                                 workflow=workflow, raise_errors=raise_errors))
        tasks.append(task)
        task.add_done_callback(lambda t: self._forget(conversation_id, t))
        return task

    async def finish(self, conversation_id: str, timeout: float = 10) -> None:
        """Al terminar la conversacion (corte de la llamada; cierre, tope o vencimiento de un
        chat de WhatsApp): espera la extraccion en curso y, si termino antes de la despedida,
        hace ahora la extraccion final (sin analysis o con tu propio agente, no hay)."""
        await self.wait_extraction(conversation_id, timeout)
        state = self.store.get(conversation_id)
        if state is None or state.status == "completed" or len(state.messages) < 2:
            return
        await self._analyze_now(state, timeout)

    async def run_final_analysis(self, conversation_id: str, timeout: float) -> None:
        """La extraccion final de una conversacion terminada, para la cola del analisis de la app. Sin estado, con
        menos de 2 mensajes, con tu propio agente o sin analysis, vuelve sin LLM. Pasa por _launch_extraction: queda
        en orden con otra del mismo proceso. Lanza lo que lance la extraccion (el que llama decide si reintenta),
        TimeoutError al vencer timeout (la extraccion se cancela y no guarda) y KeyError sin la version del agente."""
        state = self.store.get(conversation_id)
        if state is None or len(state.messages) < 2:
            return
        workflow = self.workflow(state)
        if workflow.external is not None or workflow.analysis is None:
            return
        task = self._launch_extraction(conversation_id, len(state.messages) - 1, raise_errors=True)
        await asyncio.wait_for(task, timeout)

    async def analyze(self, conversation_id: str, timeout: float = 10, *,
                      reset: bool = False, kind: str = "extraccion", workflow: Workflow | None = None) -> None:
        """El analisis sin terminar la conversacion (no cambia status): espera el que este en curso o lanza uno
        y lo espera, hasta timeout. Para el post-call de WhatsApp, que corre antes de cerrar el chat, y para
        re-correrlo en una conversacion ya guardada (reset: el extractor no ve los datos viejos y el
        resultado los pisa; kind: la marca de la traza, "reanalisis" para ese caso). workflow: la version a
        usar (re-analisis con la ultima del agente); sin el, la de la conversacion."""
        if self.extractions.get(conversation_id):
            await self.wait_extraction(conversation_id, timeout)
            return
        state = self.store.get(conversation_id)
        if state is None or len(state.messages) < 2:
            return
        await self._analyze_now(state, timeout, reset=reset, kind=kind, workflow=workflow)

    async def _analyze_now(self, state: ConversationState, timeout: float, *,
                           reset: bool = False, kind: str = "extraccion", workflow: Workflow | None = None) -> None:
        workflow = workflow or self.workflow(state)
        if workflow.external is not None or workflow.analysis is None:
            return
        await asyncio.wait([self._launch_extraction(state.conversation_id, len(state.messages) - 1,
                                                    reset=reset, kind=kind, workflow=workflow)],
                           timeout=timeout)

    def _forget(self, conversation_id: str, task: asyncio.Task) -> None:
        tasks = self.extractions.get(conversation_id, [])
        if task in tasks:
            tasks.remove(task)
        if not tasks:
            self.extractions.pop(conversation_id, None)

    async def wait_extraction(self, conversation_id: str, timeout: float | None = None) -> None:
        """Espera las extracciones en curso (cada una espera a la anterior)."""
        tasks = self.extractions.get(conversation_id)
        if tasks:
            # wait no cancela la extraccion si se cumple el timeout.
            await asyncio.wait([tasks[-1]], timeout=timeout)

    async def _extract(self, conversation_id: str, reply: int, previous: asyncio.Task | None, *,
                       reset: bool = False, kind: str = "extraccion", workflow: Workflow | None = None,
                       raise_errors: bool = False) -> None:
        """Extrae los datos de toda la conversacion y los aplica. reply: indice
        del mensaje del agente de este turno (ahi va la traza). raise_errors: la falla se loguea y se re-lanza."""
        if previous is not None:
            await asyncio.wait([previous])      # en orden; y cancelar esta no cancela la anterior
        try:
            state = self.store.get(conversation_id)
            workflow = workflow or self.workflow(state)
            await self._run_extraction(workflow, state, reply, kind, reset=reset)
        except Exception:
            logger.exception("extraction failed %s", conversation_id)
            if raise_errors:
                raise

    async def _run_extraction(self, workflow, state: ConversationState, reply: int, kind: str,
                              *, reset: bool = False) -> None:
        started = time.perf_counter()
        if reset:
            # El extractor no ve los datos viejos: una copia con los campos en null y sin resumen, para que
            # KNOWN FIELDS no sesgue la extraccion. Los campos son los de la version que corre (la ultima, si se
            # re-corrio con ella): si agrego o quito alguno, el resultado queda con los suyos.
            state = state.model_copy(update={
                "fields": {name: None for name in workflow.analysis_fields},
                "progress": state.progress.model_copy(update={"summary": None})})
        # La etapa del ultimo turno del usuario.
        llm = self.llms.for_turn(workflow, sum(m.role == "user" for m in state.messages), state.client_id)
        result: Extraction = await llm.extract(workflow, state)
        ms = round((time.perf_counter() - started) * 1000)
        # Sin await desde aca hasta guardar: nada se intercala.
        state = self.store.get(state.conversation_id)
        # Solo validacion de datos: campos inexistentes o con tipo invalido no se guardan (quedan en
        # progress.rejected, para el panel).
        updates, rejected = check_updates(workflow, result.fields)
        if reset:
            # Pisa: esta corrida es la que vale, lo que no extrajo queda en null. Recien ahora, despues del
            # await: si fallo el LLM, los datos viejos siguen.
            state.fields = {name: None for name in workflow.analysis_fields}
        state.fields.update(updates)
        state.progress.rejected = rejected
        # Con reset, el resumen se reemplaza (aunque esta corrida no lo trajo); sin el, solo si vino.
        if reset or result.summary:
            state.progress.summary = result.summary
        # La version que produjo este analisis: el detalle y la lista muestran sus campos.
        state.progress.analysis_version = workflow.version
        _add_usage(state, result)
        message = state.messages[reply]
        message.llm = (message.llm or []) + [{"kind": kind, "input": "conversación completa", "ms": ms,
                                              "reasoning": result.reasoning, "output": result.raw,
                                              **_usage(result), **_llm_info(llm)}]
        self.store.save(state)

    def retract_last_turn(self, conversation_id: str) -> bool:
        """Deshace el ultimo turno. Para cuando el cliente siguio hablando y la
        respuesta no llego a sonar: el turno siguiente trae el mensaje completo.
        La extraccion de ese turno se cancela; la del turno combinado ve todo.
        Las herramientas del turno quitado pasan al turno siguiente: si una ya tuvo efecto (reservar, cobrar), no
        se pierde y el modelo no la repite."""
        state = self.store.get(conversation_id)
        if state is None or state.progress.undo is None:
            return False
        if tasks := self.extractions.get(conversation_id):
            tasks[-1].cancel()
        undo = state.progress.undo
        n_messages = undo.pop("n_messages")
        removed, state.messages = state.messages[n_messages:], state.messages[:n_messages]
        restored = ConversationState.model_validate({**state.model_dump(), **undo})
        restored.progress.carry_tools = ([t for m in removed for t in (m.tools or [])]
                                         + restored.progress.carry_tools)
        self.store.save(restored)
        return True
