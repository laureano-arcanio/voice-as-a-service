"""Objetos de larga vida que comparten la API y el worker de voz."""
import threading

from .agents.definitions import DbDefinitions
from .config import settings
from .conversation.engine import ConversationEngine
from .conversation.store import ConversationStore
from .db import get_sessionmaker
from .llm.client import LLMClient

_engine: ConversationEngine | None = None
_lock = threading.Lock()


def get_conversation_engine() -> ConversationEngine:
    """Uno por proceso. Con lock y no @cache: las dependencias sincronicas corren en el
    threadpool y @cache no impide que dos hilos lo creen a la vez (las extracciones
    en curso viven en el engine)."""
    global _engine
    with _lock:
        if _engine is None:
            sessions = get_sessionmaker()
            llm = LLMClient(settings.vllm_llm_base_url, settings.vllm_api_key, settings.vllm_llm_model)
            _engine = ConversationEngine(llm, ConversationStore(sessions), DbDefinitions(sessions))
        return _engine
