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

# --- LLM conversacional en vivo + STT (OpenAI) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Modelo mas chico/rapido de la familia GPT-5.4 (marzo 2026): pensado para
# latencia minima. Se corre con reasoning_effort="none" (ver livekit_agent.py).
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
# STT: gpt-live-transcribe (julio 2026) es el modelo de OpenAI para transcripcion
# en vivo de baja latencia sobre la Realtime API (streaming por WebSocket, con
# parciales). Reemplaza a gpt-4o-transcribe / gpt-4o-mini-transcribe, que solo
# devuelven texto al cerrar el turno.
OPENAI_STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-live-transcribe")
# Ajuste de latencia de gpt-live-transcribe (minimal | low | medium | high | xhigh).
# El plugin de LiveKit 1.8 no lo expone; se inyecta en livekit_agent.py.
OPENAI_STT_DELAY = os.getenv("OPENAI_STT_DELAY", "minimal")

# --- TTS (ElevenLabs) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
# ID de una voz de tu cuenta de ElevenLabs (Voice Library) que hable espanol.
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")
# Velocidad de la voz (ElevenLabs acepta 0.8 a 1.2; 1.0 es la velocidad normal).
ELEVENLABS_SPEED = float(os.getenv("ELEVENLABS_SPEED", "1.1"))

# --- Scoring (evaluacion del transcript, OpenAI) ---
# Corre al colgar (no es latencia percibida por el cliente), asi que por defecto
# usa un escalon mas de calidad que el LLM en vivo. Comparte OPENAI_API_KEY.
OPENAI_SCORING_MODEL = os.getenv("OPENAI_SCORING_MODEL", "gpt-5.4-mini")

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
RECORDINGS_DIR = STORAGE_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Nombre de la agente y de la concesionaria para los prompts del demo
AGENT_NAME = os.getenv("AGENT_NAME", "Sof\u00eda")
DEALERSHIP_NAME = os.getenv("DEALERSHIP_NAME", "Forest Car")
