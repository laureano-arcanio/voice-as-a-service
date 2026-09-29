import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from .models import AgentTurn, ConversationState, Extraction, Message, Workflow
from .store import ConversationStore
from .workflow import check_updates, is_required, outcome_for

if TYPE_CHECKING:
    from ..agents.definitions import DefinitionSource

logger = logging.getLogger(__name__)

# Cuanto espera un turno a la extraccion del anterior. Corre mientras suena la
# respuesta y el cliente contesta (varios segundos), asi que casi nunca espera;
# si se pasa, el turno sigue con el estado viejo y la conversacion completa.
EXTRACTION_WAIT = 1.5


class ConversationEngine:
    """El LLM de conversacion decide la respuesta, el objetivo siguiente y si
    la conversacion termino. Los datos los saca otra llamada al LLM, la
    extraccion, en segundo plano. La app valida los datos y guarda el estado.

    Segun el engine del workflow: structured extrae en cada turno y le pasa el
    estado al LLM (JSON con answered y next_objective); classic conversa en
    texto con el prompt del workflow, sin estado, y extrae una sola vez al final.

    definitions: de donde salen los workflows (agentes de la base o plantillas;
    app/agents). Sin pasarla, las plantillas del repo (eval y tests)."""

    def __init__(self, llm, store: ConversationStore, definitions: "DefinitionSource | None" = None):
        from ..agents.templates import TemplateDefinitions

        self.llm = llm
        self.store = store
        self.definitions = definitions or TemplateDefinitions()
        self.extractions: dict[str, list[asyncio.Task]] = {}   # extracciones en curso por conversacion, en orden

    def workflow(self, state: ConversationState) -> Workflow:
        return self.definitions.get(state.agent_id, state.agent_version)

    def start_conversation(self, agent_id: str, client_id: str | None = None) -> tuple[ConversationState, str]:
        """Crea y guarda la conversacion con la version vigente del agente. KeyError si
        no existe o esta archivado."""
        state, opening = self.new_conversation(agent_id, client_id)
        self.store.save(state)
        return state, opening

    def new_conversation(self, agent_id: str, client_id: str | None = None,
                         session=None) -> tuple[ConversationState, str]:
        """Como start_conversation pero sin guardarla: para guardarla en la misma
        transaccion que la llamada (services/calls.py, store.add). session: la del que
        llama, para leer el agente sin pedir otra conexion."""
        version, workflow = self.definitions.current(agent_id, session)
        opening = workflow.conversation.opening
        state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            agent_id=agent_id, agent_version=version, client_id=client_id,
            fields={name: None for name in workflow.fields},
            messages=[Message(role="assistant", text=opening)],
        )
        # La apertura pregunta por el primer dato del workflow.
        state.progress.asked = min(workflow.fields, key=lambda name: workflow.fields[name].priority)
        return state, opening

    async def process_turn(self, conversation_id: str, user_message: str,
                           on_message: Callable[[str], None] | None = None) -> tuple[ConversationState, AgentTurn]:
        """on_message recibe assistant_message a medida que lo genera el LLM
        (agente de voz). Devuelve sin esperar la extraccion de este turno."""
        await self.wait_extraction(conversation_id, EXTRACTION_WAIT)
        state = self.store.get(conversation_id)
        if state is None:
            raise KeyError(conversation_id)
        workflow = self.workflow(state)

        classic = workflow.engine == "classic"
        started = time.perf_counter()
        llm_turn = self.llm.converse if classic else self.llm.process_turn
        result = await llm_turn(workflow, state, user_message, on_message=on_message)
        trace = [{"kind": "turno", "input": user_message, "ms": round((time.perf_counter() - started) * 1000),
                  "reasoning": result.reasoning, "output": result.raw or result.model_dump_json()}]

        # Una extraccion atrasada pudo guardar mientras el LLM respondia: se
        # relee el estado y el turno solo agrega lo suyo.
        state = self.store.get(conversation_id)
        undo = state.model_dump(include={"status", "fields", "progress"}, exclude={"progress": {"undo"}})
        undo["n_messages"] = len(state.messages)
        asked = state.progress.asked
        state.status = result.status
        state.progress.asked = result.next_objective
        state.progress.outcome = None
        state.progress.undo = undo
        state.messages += [Message(role="user", text=user_message),
                           Message(role="assistant", text=result.assistant_message, llm=trace)]
        self.store.save(state)

        if not classic or result.status == "completed":
            self._launch_extraction(conversation_id, len(state.messages) - 1, asked if result.answered else None)
        return state, result

    def _launch_extraction(self, conversation_id: str, reply: int, answered: str | None) -> asyncio.Task:
        tasks = self.extractions.setdefault(conversation_id, [])
        previous = tasks[-1] if tasks else None
        task = asyncio.create_task(self._extract(conversation_id, reply, answered, previous))
        tasks.append(task)
        task.add_done_callback(lambda t: self._forget(conversation_id, t))
        return task

    async def finish(self, conversation_id: str, timeout: float = 10) -> None:
        """Al cortar la llamada: espera la extraccion en curso. En el clasico,
        si corto el cliente antes de la despedida, hace ahora la extraccion final."""
        await self.wait_extraction(conversation_id, timeout)
        state = self.store.get(conversation_id)
        if (state is None or state.status == "completed" or len(state.messages) < 2
                or self.workflow(state).engine != "classic"):
            return
        await asyncio.wait([self._launch_extraction(conversation_id, len(state.messages) - 1, None)], timeout=timeout)

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

    async def _extract(self, conversation_id: str, reply: int, answered: str | None,
                       previous: asyncio.Task | None) -> None:
        """Extrae los datos de toda la conversacion y los aplica. reply: indice
        del mensaje del agente de este turno (ahi va la traza). answered: el
        objetivo que el LLM de conversacion dio por respondido."""
        if previous is not None:
            await asyncio.wait([previous])      # en orden; y cancelar esta no cancela la anterior
        try:
            state = self.store.get(conversation_id)
            workflow = self.workflow(state)
            await self._run_extraction(workflow, state, reply, "extraccion")
            state = self.store.get(conversation_id)
            if (answered and state.fields.get(answered) is None and is_required(workflow.fields[answered], state.fields)
                    and answered not in state.progress.rejected):
                # El LLM de conversacion avanzo pero el dato no salio: se reintenta
                # solo ese campo; si tampoco sale, no se vuelve a preguntar.
                await self._run_extraction(workflow, state, reply, "extraccion (reintento)", only=[answered])
                state = self.store.get(conversation_id)
                if state.fields.get(answered) is None:
                    state.progress.answered_empty.append(answered)
                    self.store.save(state)
        except Exception:
            logger.exception("extraction failed %s", conversation_id)
        finally:
            state = self.store.get(conversation_id)
            if state is not None and state.status == "completed":
                state.progress.outcome = outcome_for(self.workflow(state), state).id
                self.store.save(state)

    async def _run_extraction(self, workflow, state: ConversationState, reply: int, kind: str,
                              only: list[str] | None = None) -> None:
        # Hasta el mensaje del cliente: con la respuesta del agente a la vista, la
        # extraccion "contestaba" su pregunta nueva (bf06c2d0: guardo wants_link y
        # same_number cuando el cliente solo habia dicho actividad y zona).
        seen = state.model_copy(update={"messages": state.messages[:reply]})
        started = time.perf_counter()
        result: Extraction = await self.llm.extract(workflow, seen, only)
        ms = round((time.perf_counter() - started) * 1000)
        # Sin await desde aca hasta guardar: nada se intercala.
        state = self.store.get(state.conversation_id)
        user_text = " ".join(m.text for m in state.messages if m.role == "user")
        # Solo validacion de datos: campos inexistentes o con tipo invalido no se
        # guardan, y los invalidos se le informan al LLM de conversacion.
        updates, rejected = check_updates(workflow, result.fields, user_text)
        state.fields.update(updates)
        state.progress.rejected = rejected
        state.progress.answered_empty = [f for f in state.progress.answered_empty if state.fields.get(f) is None]
        message = state.messages[reply]
        message.llm = (message.llm or []) + [{"kind": kind, "input": "conversación completa", "ms": ms,
                                              "reasoning": result.reasoning, "output": result.raw}]
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
