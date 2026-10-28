import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..llm.resolver import LLMResolver
from ..tools.conversation import ConversationTools
from . import contact as contact_data
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
    OFF_TOPIC,
    OFF_TOPIC_REASON,
    check_updates,
    normalize_phone,
    outcome_for,
)

if TYPE_CHECKING:
    from ..agents.definitions import DefinitionSource

logger = logging.getLogger(__name__)


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
        # El store completa con la definicion las columnas de los reportes (conversion, goal).
        store.definitions = self.definitions
        self.extractions: dict[str, list[asyncio.Task]] = {}   # extracciones en curso por conversacion, en orden
        # Herramientas del cliente (http y code, docs/features/HERRAMIENTAS.md): las del agente y su contexto, por turno.
        self.tools = ConversationTools(store.sessions)
        self.external = None    # tu propio agente, al primer turno (app/llm/external.py)

    def workflow(self, state: ConversationState) -> Workflow:
        return self.definitions.get(state.agent_id, state.agent_version)

    def start_conversation(self, agent_id: str, client_id: str | None = None, *, channel: Channel = "voice",
                           opening: bool | str = True, contact: dict | None = None) -> tuple[ConversationState, str]:
        """Crea y guarda la conversacion con la version vigente del agente. KeyError si
        no existe o esta archivado."""
        state, text = self.new_conversation(agent_id, client_id, channel=channel, opening=opening, contact=contact)
        self.store.save(state)
        return state, text

    def new_conversation(self, agent_id: str, client_id: str | None = None, session=None, *,
                         channel: Channel = "voice", opening: bool | str = True,
                         contact: dict | None = None, phone: str | None = None,
                         context: str | None = None) -> tuple[ConversationState, str]:
        """Como start_conversation pero sin guardarla: para guardarla en la misma
        transaccion que la llamada (services/calls.py, store.add). session: la del que
        llama, para leer el agente sin pedir otra conexion.

        opening: True, la apertura del workflow (el agente habla primero, como en una
        llamada); False, sin apertura (WhatsApp entrante: el cliente escribe primero y su
        mensaje es el turno 1); un texto, esa apertura (plantilla saliente).

        contact: los datos del contacto de una campaña de voz (`vars`; app/conversation/contact.py):
        reemplazan los `{{variable}}` de la apertura, precargan los campos del workflow que se llaman
        igual y el resto va al prompt. Con `{}` (una campaña sin datos) la apertura igual se limpia de
        variables; sin contact (None) no se toca.

        phone: el numero de la otra punta de la llamada (entrante o saliente). Precarga los campos de tipo
        phone que el contacto no cargo: el agente no lo pregunta. Sin numero (link para llamar), lo pide.

        context: el motivo de una llamada saliente suelta (texto libre); va al prompt (contact.prompt_block)."""
        version, workflow = self.definitions.current(agent_id, session)
        state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            agent_id=agent_id, agent_version=version, client_id=client_id, channel=channel,
            fields={name: None for name in workflow.fields},
        )
        if contact is not None:
            preloaded, state.progress.contact = contact_data.preload(workflow, contact)
            state.fields.update(preloaded)
            state.progress.preloaded = list(preloaded)
        if context and context.strip():
            state.progress.context = context.strip()[:contact_data.MAX_CONTEXT_CHARS]
        if phone and (number := normalize_phone(phone)):
            for name, spec in workflow.fields.items():
                if spec.type == "phone" and state.fields.get(name) is None:
                    state.fields[name] = number
                    state.progress.preloaded.append(name)
        if opening is False:
            return state, ""
        text = workflow.conversation.opening if opening is True else opening
        if contact is not None:
            text = contact_data.render_template(text, contact)
        state.messages = [Message(role="assistant", text=text)]
        return state, text

    async def process_turn(self, conversation_id: str, user_message: str,
                           on_message: Callable[[str], None] | None = None, *,
                           media: TurnMedia | None = None, actor: str | None = None
                           ) -> tuple[ConversationState, AgentTurn]:
        """on_message recibe assistant_message a medida que lo genera el LLM
        (agente de voz). Devuelve sin esperar la extraccion de este turno.
        media: si el mensaje vino por audio y si la respuesta sale como nota de
        voz (WhatsApp); cambia el prompt del turno y no se guarda.
        actor: quien escribe (wa:<wa_id>): el numero de {{call.from}} en las herramientas."""
        media = media or TurnMedia()
        await self.wait_extraction(conversation_id, EXTRACTION_WAIT)
        state = self.store.get(conversation_id)
        if state is None:
            raise KeyError(conversation_id)
        state.media = media
        workflow = self.workflow(state)
        if workflow.external is not None:
            return await self._external_turn(workflow, state, user_message, media, on_message, actor)
        # Turno del usuario (1 = su primer mensaje): elige la etapa de workflow.llm.
        llm = self.llms.for_turn(workflow, 1 + sum(m.role == "user" for m in state.messages), state.client_id)

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
        undo = state.model_dump(include={"status", "fields", "progress"}, exclude={"progress": {"undo"}})
        undo["n_messages"] = len(state.messages)
        state.status = result.status
        _add_usage(state, result)
        # Fuera de tema (end_call): el resultado lo decide el agente al cortar, no los datos (_extract no lo pisa).
        state.progress.outcome = OFF_TOPIC.id if result.end_reason == OFF_TOPIC_REASON else None
        state.progress.undo = undo
        if turn_tools:
            state.progress.tool_vars = turn_tools.ctx.vars
        state.messages += [Message(role="user", text=user_message, voice_note=media.user_voice_note),
                           Message(role="assistant", text=result.assistant_message, llm=trace)]
        self.store.save(state)

        # Igual en todos los canales: se extrae al terminar (end_call) o al cortar la conversacion
        # (finish: el corte de la llamada, o el cierre o vencimiento del chat).
        if result.status == "completed" and workflow.fields:
            self._launch_extraction(conversation_id, len(state.messages) - 1)
        return state, result

    async def _external_turn(self, workflow: Workflow, state: ConversationState, user_message: str,
                             media: TurnMedia, on_message: Callable[[str], None] | None, actor: str | None
                             ) -> tuple[ConversationState, AgentTurn]:
        """Motor external (app/llm/external.py): contesta el endpoint del cliente, sin extraccion. Si falla
        sin haber hablado, el agente dice error_message; con max_errors seguidos (o sin el plan), corta o deriva
        segun on_errors."""
        from ..llm.external import ExternalAgents, ExternalError
        if self.external is None:
            self.external = ExternalAgents(self.store.sessions)
        cfg = workflow.external
        outcome = None
        try:
            result = await self.external.turn(workflow, state, user_message, on_message, actor)
            turn, outcome, trace, errors = result.turn, result.outcome, result.trace, 0
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
        if turn.status == "completed" and turn.end_reason is None:
            ids = [o.id for o in workflow.completion.outcomes]
            state.progress.outcome = outcome if outcome in ids else ids[-1]
        state.messages += [Message(role="user", text=user_message, voice_note=media.user_voice_note),
                           Message(role="assistant", text=turn.assistant_message, llm=[trace])]
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

    def _launch_extraction(self, conversation_id: str, reply: int) -> asyncio.Task:
        tasks = self.extractions.setdefault(conversation_id, [])
        previous = tasks[-1] if tasks else None
        task = asyncio.create_task(self._extract(conversation_id, reply, previous))
        tasks.append(task)
        task.add_done_callback(lambda t: self._forget(conversation_id, t))
        return task

    async def finish(self, conversation_id: str, timeout: float = 10) -> None:
        """Al terminar la conversacion (corte de la llamada; cierre, tope o vencimiento de un
        chat de WhatsApp): espera la extraccion en curso y, si termino antes de la despedida,
        hace ahora la extraccion final (sin datos a obtener o con tu propio agente, no hay)."""
        await self.wait_extraction(conversation_id, timeout)
        state = self.store.get(conversation_id)
        if state is None or state.status == "completed" or len(state.messages) < 2:
            return
        workflow = self.workflow(state)
        if workflow.external is not None or not workflow.fields:
            return
        await asyncio.wait([self._launch_extraction(conversation_id, len(state.messages) - 1)], timeout=timeout)

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

    async def _extract(self, conversation_id: str, reply: int, previous: asyncio.Task | None) -> None:
        """Extrae los datos de toda la conversacion y los aplica. reply: indice
        del mensaje del agente de este turno (ahi va la traza)."""
        if previous is not None:
            await asyncio.wait([previous])      # en orden; y cancelar esta no cancela la anterior
        try:
            state = self.store.get(conversation_id)
            workflow = self.workflow(state)
            await self._run_extraction(workflow, state, reply, "extraccion")
        except Exception:
            logger.exception("extraction failed %s", conversation_id)
        finally:
            state = self.store.get(conversation_id)
            if state is not None and state.status == "completed" and state.progress.outcome != OFF_TOPIC.id:
                state.progress.outcome = outcome_for(self.workflow(state), state).id
                self.store.save(state)

    async def _run_extraction(self, workflow, state: ConversationState, reply: int, kind: str) -> None:
        started = time.perf_counter()
        # La etapa del ultimo turno del usuario.
        llm = self.llms.for_turn(workflow, sum(m.role == "user" for m in state.messages), state.client_id)
        result: Extraction = await llm.extract(workflow, state)
        ms = round((time.perf_counter() - started) * 1000)
        # Sin await desde aca hasta guardar: nada se intercala.
        state = self.store.get(state.conversation_id)
        # Solo validacion de datos: campos inexistentes o con tipo invalido no se guardan (quedan en
        # progress.rejected, para el panel).
        updates, rejected = check_updates(workflow, result.fields)
        state.fields.update(updates)
        state.progress.rejected = rejected
        _add_usage(state, result)
        message = state.messages[reply]
        message.llm = (message.llm or []) + [{"kind": kind, "input": "conversación completa", "ms": ms,
                                              "reasoning": result.reasoning, "output": result.raw,
                                              **_usage(result), **_llm_info(llm)}]
        self.store.save(state)

    def retract_last_turn(self, conversation_id: str) -> bool:
        """Deshace el ultimo turno. Para cuando el cliente siguio hablando y la
        respuesta no llego a sonar: el turno siguiente trae el mensaje completo.
        La extraccion de ese turno se cancela; la del turno combinado ve todo."""
        state = self.store.get(conversation_id)
        if state is None or state.progress.undo is None:
            return False
        if tasks := self.extractions.get(conversation_id):
            tasks[-1].cancel()
        undo = state.progress.undo
        state.messages = state.messages[:undo.pop("n_messages")]
        restored = ConversationState.model_validate({**state.model_dump(), **undo})
        self.store.save(restored)
        return True
