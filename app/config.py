import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_DSN = os.getenv("DB_DSN", "mysql+pymysql://aiva_validate:changeme@127.0.0.1/aiva_validate?charset=utf8mb4")

# --- Proveedor de voz: LiveKit Agents + troncal SIP saliente (Twilio) ---
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_SIP_TRUNK_ID = os.getenv("LIVEKIT_SIP_TRUNK_ID", "")
# Debe matchear EXACTO entre el proceso que dispara la llamada (app) y el que la
# atiende (agent) -- ver app/livekit_dispatch.py y app/livekit_agent.py.
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "aiva-outbound-caller")
CALL_MAX_DURATION_SECONDS = int(os.getenv("CALL_MAX_DURATION_SECONDS", "900"))

# --- LLM / STT / TTS: inferencia local con vLLM (ver docker-compose.yml,
# servicios vllm-llm/vllm-stt/vllm-tts) en vez de OpenAI/ElevenLabs/Anthropic.
# Los 3 hablan API compatible con OpenAI -- se siguen usando los plugins
# livekit.plugins.openai (STT/LLM/TTS), apuntando base_url a cada contenedor.
# Ninguno de los 3 valida esta key de verdad; el openai SDK solo exige que no
# venga vacia.
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "not-needed")

# LLM conversacional en vivo. /v1/responses (Responses API, WebSocket
# persistente) -- swap directo de lo que ya se usaba con OpenAI, mismo
# reasoning_effort="none" (ver livekit_agent.py) para no perder latencia con
# cadena de razonamiento previa a la respuesta.
VLLM_LLM_BASE_URL = os.getenv("VLLM_LLM_BASE_URL", "http://vllm-llm:8000/v1")
VLLM_LLM_MODEL = os.getenv("VLLM_LLM_MODEL", "Qwen/Qwen3.5-4B")

# STT. /v1/audio/transcriptions -- a diferencia de gpt-live-transcribe (Realtime
# API por WebSocket con transcript parcial mientras el cliente habla), este es
# un endpoint REST por-turno: el plugin hace commit del audio recien al
# detectar silencio (VAD) y recien ahi llega el transcript, sin parciales.
VLLM_STT_BASE_URL = os.getenv("VLLM_STT_BASE_URL", "http://vllm-stt:8000/v1")
VLLM_STT_MODEL = os.getenv("VLLM_STT_MODEL", "Qwen/Qwen3-ASR-1.7B")

# TTS. /v1/audio/speech con streaming -- swap directo de elevenlabs.TTS por
# openai.TTS(voice=...). Checkpoint -Base (voice-cloning): VLLM_TTS_VOICE
# tiene que ser el nombre de una voz clonada y subida a vllm-tts via
# POST /v1/audio/voices (ver docker-compose.yml), no un preset de fabrica --
# el checkpoint -CustomVoice (que si tenia presets) se descarto por un bug
# real: su speaker encoder devuelve embeddings de 1024 dims contra los 2048
# que espera el talker de 1.7B, y clonar con el rompia el engine (probado).
VLLM_TTS_BASE_URL = os.getenv("VLLM_TTS_BASE_URL", "http://vllm-tts:8000/v1")
VLLM_TTS_MODEL = os.getenv("VLLM_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
VLLM_TTS_VOICE = os.getenv("VLLM_TTS_VOICE", "sofia_ar")
# Velocidad de la voz. OJO: probado en vivo que el server (vllm-omni) rechaza
# con 400 cualquier valor de speed != 1.0 en modo streaming ("Streaming is not
# supported with speed adjustment") -- solo funciona en requests no-streaming,
# que no podemos usar aca (mata la latencia). Dejar en 1.0 salvo que se acepte
# perder streaming.
VLLM_TTS_SPEED = float(os.getenv("VLLM_TTS_SPEED", "1.0"))

# --- Scoring (evaluacion del transcript) ---
# Corre al colgar (no es latencia percibida por el cliente). Comparte el mismo
# LLM local de arriba -- ya no hay un modelo "mini" aparte para esto, todo
# corre contra vllm-llm.
VLLM_SCORING_MODEL = os.getenv("VLLM_SCORING_MODEL", VLLM_LLM_MODEL)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
RECORDINGS_DIR = STORAGE_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Nombre de la agente y de la concesionaria para los prompts del demo
AGENT_NAME = os.getenv("AGENT_NAME", "Sof\u00eda")
DEALERSHIP_NAME = os.getenv("DEALERSHIP_NAME", "Forest Car")
