"""Configuracion del CRM (docs/CRM_PLAN.md), con prefijo CRM_ en el .env."""
import datetime
import zoneinfo
from functools import cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_prefix="CRM_", extra="ignore")

    # Base `crm` en el contenedor db (make crm-db la crea).
    db_dsn: str = "postgresql+psycopg://aiva_validate:changeme@127.0.0.1:5432/crm"
    # La UI y el usuario: todo. Agentes: todo menos aprobar envios y la cola (crm/auth.py).
    api_key: str = ""
    agent_api_key: str = ""

    # Resend con acceso completo: envia y lee el estado de lo enviado.
    resend_api_key: str = ""
    mail_from: str = "Laureano Arcanio <laureano@atentina.net>"
    # Copia oculta de cada envio, para tener el hilo en Gmail. Vacio: sin copia.
    mail_bcc: str = ""
    site_url: str = "https://atentina.com.ar/"

    # Cola de envio: uno por ventana, en un momento al azar, solo en horario habil y con tope
    # diario. Dominio sin reputacion: el ritmo del 21-oct (~30 por hora como maximo).
    send_enabled: bool = True
    send_window_seconds: int = 120
    send_min_gap_seconds: int = 30
    send_daily_max: int = 50
    send_hours: str = "9-18"          # hora local, de lunes a viernes
    send_timezone: str = "America/Argentina/Buenos_Aires"

    # Estado de lo enviado en Resend (rebotes, quejas): cada cuantos segundos y cuantos dias atras.
    events_interval_seconds: int = 600
    events_days: int = 14

    # Google Analytics Data API: cuenta de servicio con rol Lector en la propiedad.
    ga_property_id: str = ""
    ga_credentials: str = ""          # ruta al JSON de la cuenta de servicio
    ga_interval_seconds: int = 86400

    # Respuestas (docs/CRM_PLAN.md, 6): Resend Receiving en un subdominio, leido cada tanto (sin webhook).
    # Apagado hasta que el subdominio y el reenvio de la casilla esten andando.
    inbound_enabled: bool = False
    inbound_interval_seconds: int = 120
    # Lo que llega de nuestras casillas (las copias BCC de cada envio) se ignora. Separados por coma.
    own_domains: str = "atentina.net,atentina.com.ar"
    # LLM local que clasifica cada respuesta (vllm-llm, en la misma red). Sin modelo: sin analisis.
    llm_url: str = "http://vllm-llm:8000/v1"
    llm_api_key: str = Field("", validation_alias=AliasChoices("CRM_LLM_API_KEY", "VLLM_API_KEY"))
    llm_model: str = Field("", validation_alias=AliasChoices("CRM_LLM_MODEL", "VLLM_LLM_MODEL"))
    llm_min_confidence: float = 0.7
    # Aviso por mail de cada respuesta (no las autorespuestas). Vacio: sin aviso.
    notify_to: str = ""
    crm_url: str = "http://127.0.0.1:8030"

    # Dias habiles despues del primer mail para que el seguimiento venza (filtro Pendiente de Leads).
    follow_up_business_days: int = 4

    web_dist_dir: Path = BASE_DIR / "web" / "dist"
    loops: bool = True                # los tests los apagan


def local_today() -> datetime.date:
    """Fecha de hoy en Argentina (dias habiles, seguimientos, vencimientos)."""
    return datetime.datetime.now(zoneinfo.ZoneInfo(settings.send_timezone)).date()


@cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
