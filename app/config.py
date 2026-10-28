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
    # Trunk SIP entrante (lo crea `make livekit-sip`). Al cargar o borrar numeros por la API
    # se agregan o quitan de los dos trunks en caliente (app/services/livekit.py): sin
    # reiniciar livekit-sip ni cortar llamadas. Los tests lo apagan.
    livekit_sip_inbound_trunk_name: str = "anura-asterisk-inbound"
    livekit_sip_sync: bool = True
    livekit_agent_name: str = "aiva-outbound-caller"
    call_max_duration_seconds: int = 900
    # Grabaciones por mensaje (record_audio en la definicion; app/conversation/recordings.py):
    # storage/ montado en `agent` y en `app` (WhatsApp), no versionado (.gitignore).
    call_recordings_dir: Path = Field(default=BASE_DIR / "storage" / "recordings")
    # Aperturas pregeneradas (conversation.opening_audio; app/conversation/opening_audio.py).
    opening_audio_dir: Path = Field(default=BASE_DIR / "storage" / "openings")
    # Imagenes de los links para llamar (app/services/call_links.py): las sirve `app`, sin backup.
    call_link_images_dir: Path = Field(default=BASE_DIR / "storage" / "call-links")
    # Logos de la marca blanca (app/services/branding.py): <client_id>/<hash>.<ext>; en el backup.
    branding_dir: Path = Field(default=BASE_DIR / "storage" / "branding")
    # Musica de espera de las derivaciones (docs/DERIVACIONES_PLAN.md, 4.8): <tema>.ogg; "default" es la de
    # LiveKit Agents.
    hold_music_dir: Path = Field(default=BASE_DIR / "storage" / "hold-music")
    # Aviso "Esta llamada está siendo grabada" de las llamadas directas (app/voice/direct.py): <voz>.wav, lo
    # sintetiza el worker la primera vez. Al cambiar el checkpoint del TTS, borrarlo como las aperturas.
    notice_audio_dir: Path = Field(default=BASE_DIR / "storage" / "notices")

    # --- Inferencia ---
    vllm_api_key: str = "not-needed"
    vllm_llm_base_url: str = "http://vllm-llm:8000/v1"
    vllm_llm_model: str = "RedHatAI/Qwen3.5-9B-quantized.w4a16"
    # Configuracion del modelo propio (la de cada modelo va en su override o en el .env, no en el codigo):
    # razonamiento (chat_template_kwargs.enable_thinking) con su tope de tokens, y muestreo. Sin definir, rige
    # el del servidor (vLLM toma el generation_config del modelo).
    llm_thinking: bool = False
    llm_thinking_budget: int = 128
    llm_temperature: float | None = None
    llm_top_p: float | None = None
    llm_top_k: int | None = None
    llm_min_p: float | None = None
    # Voz: espera de silencio para dar el turno por terminado, con el turn detector seguro (min) o dudando
    # (max). Es configuracion del detector de turno (modelo), no del codigo.
    voice_min_endpointing_delay: float = 0.4
    voice_max_endpointing_delay: float = 1.0
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
    # Derivacion a personas desde la demo (agentes con areas, hoy atentina_comercial): cualquiera de internet
    # hace sonar al equipo y gasta minutos y canales de Anura; los topes por IP y diarios son los de la demo.
    demo_handoff: bool = False
    demo_join_timeout_seconds: int = 60
    demo_daily_minutes: int = 120
    demo_ip_calls_per_hour: int = 4
    demo_ip_calls_per_day: int = 10
    demo_ip_tts_per_hour: int = 30
    demo_ip_sessions_per_hour: int = 20
    demo_tts_max_chars: int = 300

    # --- Link publico para llamar a un agente (docs/LINK_LLAMADA_PLAN.md) ---
    # Base de las URLs (https://llamar.atentina.com.ar): con ese Host, app sirve solo la pagina del
    # link y su API (app/api/call_link_host.py). Vacio: la pagina queda en <host del panel>/llamar/<token>.
    call_link_base_url: str = ""
    # Site key publica de Turnstile (la misma de la landing); el widget tiene que permitir el host
    # del link. Sin ella o sin TURNSTILE_SECRET_KEY la pagina dice "no disponible".
    turnstile_site_key: str = ""

    # --- Teléfono del equipo en su host (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 16) ---
    # Base (https://telefono.atentina.com.ar): con ese Host, app sirve en `/` la app del teléfono (web/telefono.html)
    # y la API; nada más del panel (app/api/phone_app_host.py). Vacío: queda en <host del panel>/movil.
    phone_app_base_url: str = ""
    call_link_default_seconds: int = 300
    call_link_join_timeout_seconds: int = 60
    call_link_ip_calls_per_hour: int = 4
    call_link_ip_calls_per_day: int = 10
    # Llamadas por link a la vez entre todos los clientes: deja lugar a las entrantes por telefono.
    # Sin medir con Gemma (como CALL_CAMPAIGN_MAX_CONCURRENT): no subirlo sin un CAP.
    call_link_max_concurrent: int = 8

    # --- Formulario de contacto de la landing (POST /api/v1/demo/contact) ---
    # Aviso por mail con Resend (dominio atentina.com.ar verificado). Sin clave o sin destino,
    # el pedido igual se guarda en contact_requests.
    resend_api_key: str = ""
    contact_to: str = ""   # destinos separados por coma
    contact_from: str = "Atentina <web@atentina.com.ar>"
    contact_ip_per_hour: int = 3
    contact_ip_per_day: int = 10

    # --- API de inferencia (/api/v1/inference: LLM, STT y TTS con API key; docs/API_INFERENCIA.md) ---
    # Tope de tokens que genera un pedido de chat (se achica al saldo del mes del cliente).
    inference_llm_max_tokens: int = 4096
    # Audio por pedido de transcripcion (bytes) y texto por pedido de sintesis (caracteres).
    inference_stt_max_bytes: int = 25 * 1024 * 1024
    inference_tts_max_chars: int = 1500
    # Tiempo maximo de cada pedido al motor.
    inference_timeout_seconds: float = 120

    # --- Mails transaccionales (app/mail/): alta de cliente y numero asignado ---
    # Salen por Resend (RESEND_API_KEY, arriba); sin clave no se envian y la API sigue igual.
    mail_from: str = "Atentina <hola@atentina.com.ar>"
    # Dashboard y sitio: los links de los mails. El de la clave es /set-password?token=...
    app_url: str = "https://app.atentina.com.ar"
    site_url: str = "https://atentina.com.ar"
    support_email: str = "hola@atentina.com.ar"
    # Vigencia del link para crear la clave (de un solo uso).
    password_setup_hours: int = 72
    # Resumen por email de cada llamada (app/mail/call_summary.py): cada cuanto mira los pendientes
    # y cuanto de la transcripcion va en el mail (el resto, en el dashboard).
    call_summary_tick_seconds: float = 15
    call_summary_transcript_chars: int = 8000

    # --- Registro autoservicio y cobro de planes (docs/SUSCRIPCIONES_PLAN.md) ---
    # Registro desde la landing (POST /api/v1/demo/signup, con Turnstile). Va al tier publico con precio 0.
    signup_enabled: bool = True
    signup_ip_per_hour: int = 3
    signup_ip_per_day: int = 10
    # Verificacion del email antes del paso del pago (POST /api/v1/demo/signup/check), por IP.
    signup_check_ip_per_hour: int = 30
    # "Olvidé mi clave" (POST /api/v1/auth/password-reset): por IP y por email.
    password_reset_ip_per_hour: int = 5
    password_reset_email_per_hour: int = 3
    # Cambio de clave o de email desde el perfil (POST /api/v1/auth/me/...): codigo de 6 digitos al email
    # actual, vigencia, mails por hora e intentos fallidos por cada 15 min, por usuario.
    account_code_minutes: int = 15
    account_code_sends_per_hour: int = 5
    account_code_attempts_15m: int = 5
    # Datos para la transferencia, como se muestran al cliente (una linea por dato: titular, CUIT, CBU, alias).
    bank_transfer_info: str = ""
    # A quien avisar de un pedido de plan por transferencia (vacio: SUPPORT_EMAIL).
    billing_notify_to: str = ""
    # Dias con el plan pago despues del vencimiento sin pago, y dias que un numero queda suspendido
    # (asignado, sin atender) despues de bajar a un plan con menos numeros, antes de volver al inventario.
    billing_grace_days: int = 7
    billing_number_hold_days: int = 30
    # Aviso de renovacion de las transferencias, estos dias antes del vencimiento.
    billing_reminder_days: int = 5
    # Cada cuanto corre el barrido de vencimientos (app/billing/loop.py).
    billing_tick_seconds: float = 900
    # Mercado Pago (suscripciones con debito automatico, fase 3). Sin access token no se ofrece.
    # En sandbox: las credenciales de prueba de la app y, como pagador, el email del comprador de prueba
    # (MP rechaza un pagador real con credenciales de prueba).
    mp_billing_access_token: str = ""
    mp_billing_public_key: str = ""
    mp_billing_webhook_secret: str = ""   # firma x-signature; vacio = el webhook rechaza todo
    mp_billing_test_payer_email: str = ""
    mp_api_url: str = "https://api.mercadopago.com"

    # --- WhatsApp (Cloud API de Meta, docs/WHATSAPP_PLAN.md) ---
    wa_app_id: str = ""
    wa_app_secret: str = ""  # firma X-Hub-Signature-256; vacio = el webhook rechaza todo
    wa_verify_token: str = ""  # challenge GET del webhook; vacio = lo rechaza
    wa_access_token: str = ""
    wa_public_url: str = ""
    wa_graph_version: str = "v25.0"
    # PIN de dos pasos de nuestros numeros (alta manual, sin token propio): retry_register.
    wa_registration_pin: str = ""
    # Fase 2 (Embedded Signup): config de Facebook Login for Business. Apagado hasta tener el Tech Provider: los
    # clientes conectan su numero con su propia app de Meta (docs/ADMIN_SOPORTE_PLAN.md, seccion 4).
    wa_embedded_signup: bool = False
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
    # Campañas de voz (app/campaigns/dialer.py, docs/LLAMADAS_SALIENTES_PLAN.md, secciones 4 y 5).
    call_campaign_tick_seconds: float = 2.0     # cada cuanto el dialer revisa que llamar
    # Llamadas de campaña a la vez entre todos los clientes: deja lugar a las entrantes y la demo. 8 hasta
    # medir la capacidad con Gemma (fase 5 del plan).
    call_campaign_max_concurrent: int = 8
    call_campaign_failure_streak: int = 10      # intentos seguidos fallidos que pausan la campaña (trunk o Anura caidos)
    call_ringing_timeout_seconds: int = 30      # cuanto suena antes de dar la llamada por no atendida
    # Derivacion de llamadas (docs/DERIVACIONES_PLAN.md, 4.6): canales de la cuenta de Anura (rtp.conf). Una
    # llamada por Anura ocupa uno y una derivada dos; sin canal libre la derivacion no se intenta.
    anura_channels: int = 10

    # --- Observabilidad del hardware (docs/OBSERVABILIDAD.md) ---
    # Prometheus de docker-compose.monitoring.yml; vacio = la pantalla Sistema responde 503 monitoring_off.
    prometheus_url: str = "http://prometheus:9090"
    # Token con el que Prometheus lee /internal/metrics (make monitoring-config lo crea); vacio = 404.
    monitoring_token: str = ""
    # Segundos para marcar 1 despues del whisper (sin el 1 no se conecta: un contestador termina aca).
    handoff_confirm_seconds: int = 8
    # Feriados (fechas YYYY-MM-DD separadas por coma, hora local de billing_timezone): el dialer no marca esos
    # dias (plan, seccion 11). Las campañas de WhatsApp no los miran.
    campaign_holidays: str = ""
    # Webhook de las campañas (app/campaigns/callbacks.py, plan seccion 8): cada cuanto se entrega lo pendiente,
    # tiempo maximo de un POST, intentos por evento (con espera creciente) y si se permite un host privado
    # o http (solo para desarrollo: sin esto un cliente podria apuntar a la red interna).
    campaign_callback_tick_seconds: float = 5.0
    campaign_callback_timeout_seconds: float = 10.0
    campaign_callback_max_attempts: int = 6
    campaign_callback_allow_private: bool = False

    # Herramientas del cliente (docs/TOOLS_PLAN.md). Sandbox de codigo (servicio tools-runner, red interna);
    # vacio = sin herramientas de codigo.
    tools_runner_url: str = ""
    tools_runner_token: str = ""
    # Zona de {{today}} y {{now}} en la definicion de un agente y en las herramientas.
    agent_timezone: str = "America/Argentina/Buenos_Aires"

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
