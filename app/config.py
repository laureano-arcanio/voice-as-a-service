"""Configuracion por variables de entorno (.env), validada con pydantic-settings.

Uso: `from app.config import settings` y `settings.vllm_api_key`. Por compatibilidad
con los scripts, `config.VLLM_API_KEY` (el nombre de la variable) tambien funciona.
"""
from functools import cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    db_dsn: str = "postgresql+psycopg://aiva_validate:changeme@127.0.0.1:5432/aiva_validate"

    # --- Auth ---
    # Firma de los JWT de sesion. Sin valor la app no arranca (ver main.create_app).
    auth_secret: str = ""
    auth_token_hours: int = 12
    # Cookie de sesion con Secure: solo viaja por HTTPS. En el server de validacion
    # (HTTP plano) va en false.
    auth_cookie_secure: bool = True
    # Admin inicial que crea `python -m app.cli seed` (solo si no existe).
    admin_email: str = ""
    admin_password: str = ""

    # --- Limites por tier ---
    # El mes de consumo empieza el dia 1 a las 00:00 en esta zona.
    billing_timezone: str = "America/Argentina/Buenos_Aires"
    # Cada cuanto el worker revisa los minutos del cliente durante una llamada.
    quota_check_seconds: int = 15
    quota_reject_message: str = (
        "Hola. En este momento no podemos atender tu llamada. Por favor, volvé a llamar más tarde. Gracias."
    )
    quota_end_message: str = "Disculpá, tenemos que terminar la llamada. Gracias por tu tiempo."

    # --- LiveKit ---
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    # Trunk SIP saliente. Vacio: el agente busca por nombre el que crea `make livekit-sip`
    # (LIVEKIT_SIP_OUTBOUND_TRUNK_NAME). Con LiveKit propio conviene dejarlo vacio: su Redis no
    # persiste y el ID cambia en cada reinicio del host (docker-compose.livekit.yml).
    livekit_sip_trunk_id: str = ""
    livekit_sip_outbound_trunk_name: str = "anura-asterisk-outbound"
    livekit_agent_name: str = "aiva-outbound-caller"
    call_max_duration_seconds: int = 900

    # --- Inferencia ---
    vllm_api_key: str = "not-needed"
    vllm_llm_base_url: str = "http://vllm-llm:8000/v1"
    vllm_llm_model: str = "RedHatAI/Qwen3.5-9B-quantized.w4a16"
    # Pensamiento del LLM en cada turno, con tope de tokens (vLLM corta el razonamiento
    # ahi y sigue con el JSON). Sin tope llegaba a ~4000 tokens y 50 s; con 128, ~2,3 s
    # por turno contra ~1,5 s sin pensar (Qwen3.5-4B, sin carga).
    llm_thinking: bool = False
    llm_thinking_budget: int = 128
    # Muestreo recomendado por Qwen para cada modo; LLM_TEMPERATURE lo pisa si se define.
    llm_temperature: float | None = None
    vllm_stt_base_url: str = "http://stt-parakeet:8000/v1"
    vllm_stt_model: str = "nvidia/parakeet-tdt-0.6b-v3"
    vllm_tts_base_url: str = "http://vllm-tts:8000/v1"
    # Sin default: tienen que coincidir con el checkpoint que sirve vllm-tts (.env, docs/TTS_FINETUNE.md).
    vllm_tts_model: str = ""
    vllm_tts_voice: str = ""

    # --- Demo de la landing (/api/v1/demo, docs/LANDING.md) ---
    turnstile_secret_key: str = ""
    demo_allowed_origins: str = "https://atentina.com.ar,https://www.atentina.com.ar"
    demo_client: str = "landing"
    demo_livekit_url: str = ""
    demo_session_minutes: int = 30
    demo_call_max_seconds: int = 180
    demo_join_timeout_seconds: int = 60
    demo_daily_minutes: int = 120
    demo_ip_calls_per_hour: int = 4
    demo_ip_calls_per_day: int = 10
    demo_ip_tts_per_hour: int = 30
    demo_ip_sessions_per_hour: int = 20
    demo_tts_max_chars: int = 300

    # --- WhatsApp (Cloud API de Meta, docs/WHATSAPP_PLAN.md) ---
    wa_app_id: str = ""
    wa_app_secret: str = ""  # firma X-Hub-Signature-256; vacio = el webhook rechaza todo
    wa_verify_token: str = ""  # challenge GET del webhook; vacio = lo rechaza
    wa_access_token: str = ""
    wa_public_url: str = ""
    wa_graph_version: str = "v25.0"
    # Fase 1: tras estas horas sin mensajes del cliente, un mensaje nuevo abre otra conversacion.
    wa_session_hours: int = 24
    # Junta en un turno los mensajes que llegan seguidos (el equivalente de CONTINUATION_WINDOW).
    wa_debounce_seconds: float = 2.0
    wa_unsupported_reply: str = "Por ahora solo puedo leer mensajes de texto. ¿Me lo escribís?"
    wa_max_reply_chars: int = 4096  # tope de Meta para un texto; se trunca
    # Topes contra abuso y contra el largo de contexto del LLM (--max-model-len 32768):
    # caracteres por turno (lo que pase se descarta) y turnos por conversacion (despues, otra).
    wa_max_turn_chars: int = 2000
    wa_max_turns: int = 40

    # --- Frontend ---
    # Build de la SPA (web/, `npm run build`). Si no existe, la API funciona sin UI.
    web_dist_dir: Path = Field(default=BASE_DIR / "web" / "dist")


@cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def __getattr__(name: str):
    """config.VLLM_API_KEY -> settings.vllm_api_key (scripts anteriores a Settings)."""
    if name.isupper() and hasattr(settings, name.lower()):
        return getattr(settings, name.lower())
    raise AttributeError(name)
