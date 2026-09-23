from functools import cache

from . import config
from .calls import CallLog
from .conversation.engine import ConversationEngine
from .conversation.store import ConversationStore
from .llm.client import LLMClient


@cache
def get_engine() -> ConversationEngine:
    llm = LLMClient(config.VLLM_LLM_BASE_URL, config.VLLM_API_KEY, config.VLLM_LLM_MODEL)
    return ConversationEngine(llm, ConversationStore(config.DB_DSN))


@cache
def get_calls() -> CallLog:
    return CallLog(get_engine().store)
