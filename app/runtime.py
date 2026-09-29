"""Objetos de larga vida que comparten la API y el worker de voz."""
from functools import cache

from .agents.definitions import DbDefinitions
from .config import settings
from .conversation.engine import ConversationEngine
from .conversation.store import ConversationStore
from .db import get_sessionmaker
from .llm.client import LLMClient


@cache
def get_conversation_engine() -> ConversationEngine:
    sessions = get_sessionmaker()
    llm = LLMClient(settings.vllm_llm_base_url, settings.vllm_api_key, settings.vllm_llm_model)
    return ConversationEngine(llm, ConversationStore(sessions), DbDefinitions(sessions))
