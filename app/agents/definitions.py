"""De donde saca el motor la definicion (workflow) de un agente."""
import threading
from collections import OrderedDict
from contextlib import nullcontext
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..conversation.models import Workflow
from ..models import Agent, AgentVersion


class DefinitionSource(Protocol):
    """session: la del que llama, si ya tiene una abierta. Pedir otra conexion con una
    tomada traba el pool cuando hay mas pedidos simultaneos que conexiones."""

    def current(self, agent_id: str, session: Session | None = None) -> tuple[int, Workflow]:
        """Version vigente y su definicion. KeyError si no existe o no se puede usar."""
        ...

    def get(self, agent_id: str, version: int, session: Session | None = None) -> Workflow:
        """Una version puntual (la de una conversacion). KeyError si no existe."""
        ...


class DbDefinitions:
    """Agentes de la base. Las versiones son inmutables, asi que se cachean."""

    def __init__(self, sessions: sessionmaker[Session], cache_size: int = 256):
        self.sessions = sessions
        self._cache: OrderedDict[tuple[str, int], Workflow] = OrderedDict()
        self._size = cache_size
        self._lock = threading.Lock()

    def current(self, agent_id: str, session: Session | None = None) -> tuple[int, Workflow]:
        with self._session(session) as s:
            row = s.execute(select(Agent.version, Agent.archived_at).where(Agent.id == agent_id)).first()
        if row is None or row.archived_at is not None:
            raise KeyError(agent_id)
        return row.version, self.get(agent_id, row.version, session)

    def get(self, agent_id: str, version: int, session: Session | None = None) -> Workflow:
        key = (agent_id, version)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        with self._session(session) as s:
            definition = s.scalar(select(AgentVersion.definition).where(
                AgentVersion.agent_id == agent_id, AgentVersion.version == version))
        if definition is None:
            raise KeyError(key)
        return self._remember(agent_id, version, definition)

    def _session(self, session: Session | None):
        return nullcontext(session) if session is not None else self.sessions()

    def _remember(self, agent_id: str, version: int, definition: dict) -> Workflow:
        workflow = Workflow.model_validate(definition)
        with self._lock:
            self._cache[(agent_id, version)] = workflow
            if len(self._cache) > self._size:
                self._cache.popitem(last=False)
        return workflow
