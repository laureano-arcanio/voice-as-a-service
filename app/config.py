"""Configuracion por variables de entorno (.env), validada con pydantic-settings.

Uso: `from app.config import settings` y `settings.vllm_api_key`. Por compatibilidad
con los scripts, `config.VLLM_API_KEY` (el nombre de la variable) tambien funciona.
"""
from functools import cache
from pathlib import Path
from typing import Literal

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
    # Cookie de sesion con Secure. True: siempre. False: solo si el pedido llega por HTTPS
    # (por el tunel); asi sigue andando en http://localhost:8011.
    auth_cookie_secure: bool = True
    # Pares TCP de los que se cree CF-Connecting-IP y X-Forwarded-Proto. cloudflared (host)
    # llega al contenedor por el gateway de la red de compose (hoy 172.24.0.1): `gateway` lo
    # resuelve al arrancar (la subred puede cambiar si se recrea la red). No todo 172.16/12:
    # ahi estan las redes de los contenedores de otros proyectos de este host.
    trusted_proxy_cidrs: str = "127.0.0.1/32,::1/128,gateway"
    # Origenes validos para un POST/PATCH/DELETE con la cookie, ademas del mismo Host (CSRF).
    app_origins: str = "https://app.atentina.com.ar"
    # /api/v1/docs y openapi.json: admin (solo admin con sesion), public u off.
    api_docs: Literal["admin", "public", "off"] = "admin"
    # CSP solo informativa (Content-Security-Policy-Report-Only), para probar sin romper.
    csp_report_only: bool = False
    # Logins fallidos (en memoria, por proceso), en ventanas de 15 min y de un dia. El tope
    # por email solo frena a las IP que ya fallaron en la ventana (no deja afuera al dueno).
    login_fail_ip_email_15m: int = 5
    login_fail_ip_15m: int = 20
    login_fail_ip_day: int = 100
    login_fail_email_15m: int = 10
    # Tope del cuerpo de los pedidos a /api (413).
    api_max_body_bytes: int = 1_048_576
    # Uso de GPU por usuario o API key, por hora.
    rate_tts_preview_per_hour: int = 60
    rate_conversations_per_hour: int = 60
    rate_turns_per_hour: int = 600
    # Unico cliente (slug) que puede pedir llamadas de loadtest, ademas de los admins.
    loadtest_client: str = "atentina"
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
    # Cliente de los agentes de la demo (Atentina, el mismo del loadtest y del WhatsApp propio).
    demo_client: str = "atentina"
    # Unicos agentes (slugs) que se pueden llamar desde la landing, y su tope de llamadas activas
    # entre todos (el tier de Atentina no tiene limites). El cupo diario cuenta solo sus llamadas.
    demo_agents: str = "atentina_comercial,turnos,cobranzas,reclamos"
    demo_max_concurrent_calls: int = 3
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

    # --- Formulario de contacto de la landing (POST /api/v1/demo/contact) ---
    # Aviso por mail con Resend (dominio atentina.com.ar verificado). Sin clave o sin destino,
    # el pedido igual se guarda en contact_requests.
    resend_api_key: str = ""
    contact_to: str = ""   # destinos separados por coma
    contact_from: str = "Atentina <web@atentina.com.ar>"
    contact_ip_per_hour: int = 3
    contact_ip_per_day: int = 10

    # --- WhatsApp (Cloud API de Meta, docs/WHATSAPP_PLAN.md) ---
    wa_app_id: str = ""
    wa_app_secret: str = ""  # firma X-Hub-Signature-256; vacio = el webhook rechaza todo
    wa_verify_token: str = ""  # challenge GET del webhook; vacio = lo rechaza
    wa_access_token: str = ""
    wa_public_url: str = ""
    wa_graph_version: str = "v25.0"
    # PIN de dos pasos de nuestros numeros (alta manual, sin token propio): retry_register.
    wa_registration_pin: str = ""
    # Fase 2 (Embedded Signup): config de Facebook Login for Business.
    wa_config_id: str = ""
    # Claves Fernet separadas por coma (la primera cifra; las otras solo descifran, para rotar).
    wa_token_key: str = ""
    wa_signup_per_hour: int = 10      # por cliente
    wa_templates_per_hour: int = 20   # plantillas creadas, por cliente
    wa_sdk_locale: str = "es_LA"
    # Fase 1: tras estas horas sin mensajes del cliente, un mensaje nuevo abre otra conversacion.
    wa_session_hours: int = 24
    # Junta en un turno los mensajes que llegan seguidos (el equivalente de CONTINUATION_WINDOW).
    wa_debounce_seconds: float = 2.0
    wa_unsupported_reply: str = "Por ahora no puedo ver imágenes ni archivos. ¿Me lo escribís?"
    wa_max_reply_chars: int = 4096  # tope de Meta para un texto; se trunca
    # Topes contra abuso y contra el largo de contexto del LLM (--max-model-len 32768):
    # caracteres por turno (lo que pase se descarta) y turnos por conversacion (despues, otra).
    wa_max_turn_chars: int = 2000
    wa_max_turns: int = 40
    # Audios (fase 3 parcial): entrada por el STT, salida como nota de voz por el TTS.
    # mirror: nota de voz si el turno tuvo algun audio del cliente; never: siempre texto; always: siempre audio.
    wa_audio_reply: Literal["mirror", "never", "always"] = "mirror"
    wa_audio_max_bytes: int = 4 * 1024 * 1024  # Meta acepta hasta 16 MB; 4 MB = mp3 de 128 kbps y 120 s, holgado
    wa_audio_max_seconds: float = 120.0
    wa_audio_max_reply_chars: int = 600  # respuesta mas larga: sale en texto (MAX_PREVIEW_CHARS de la prueba de voz)
    wa_audio_concurrency: int = 4  # pedidos simultaneos desde WhatsApp a cada uno (STT, TTS); guarda, sin medir
    wa_audio_voice_flag: bool = True  # "voice": true al enviar: se ve como nota de voz
    wa_audio_too_long_reply: str = "Ese audio es muy largo para mí. ¿Me mandás uno más corto o me lo escribís?"
    wa_audio_empty_reply: str = "No te escuché bien, ¿me lo repetís?"
    wa_audio_error_reply: str = "No pude escuchar el audio. ¿Me lo escribís?"
    # Campañas salientes (app/whatsapp/campaigns.py y sender.py).
    wa_campaign_tick_seconds: float = 5.0   # cada cuanto el sender manda lo que toca segun el ritmo
    wa_campaign_reply_days: int = 7         # una respuesta dentro de estos dias abre la conversacion con la plantilla
    wa_campaign_max_recipients: int = 10_000  # por campaña
    wa_optout_reply: str = "Listo, no te vamos a escribir más. ¡Gracias!"

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
