import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_DSN = os.getenv("DB_DSN", "mysql+pymysql://aiva_validate:changeme@127.0.0.1/aiva_validate?charset=utf8mb4")
WORKFLOW_ID = os.getenv("WORKFLOW_ID", "sales_discovery")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_SIP_TRUNK_ID = os.getenv("LIVEKIT_SIP_TRUNK_ID", "")
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "aiva-outbound-caller")
CALL_MAX_DURATION_SECONDS = int(os.getenv("CALL_MAX_DURATION_SECONDS", "900"))

VLLM_API_KEY = os.getenv("VLLM_API_KEY", "not-needed")
VLLM_LLM_BASE_URL = os.getenv("VLLM_LLM_BASE_URL", "http://vllm-llm:8000/v1")
VLLM_LLM_MODEL = os.getenv("VLLM_LLM_MODEL", "Qwen/Qwen3.5-4B")
VLLM_STT_BASE_URL = os.getenv("VLLM_STT_BASE_URL", "http://stt-parakeet:8000/v1")
VLLM_STT_MODEL = os.getenv("VLLM_STT_MODEL", "nvidia/parakeet-tdt-0.6b-v3")
VLLM_TTS_BASE_URL = os.getenv("VLLM_TTS_BASE_URL", "http://vllm-tts:8000/v1")
VLLM_TTS_MODEL = os.getenv("VLLM_TTS_MODEL", "arf_03034-ft")
VLLM_TTS_VOICE = os.getenv("VLLM_TTS_VOICE", "arf_03034")
