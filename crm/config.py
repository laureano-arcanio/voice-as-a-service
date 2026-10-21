"""Configuracion del CRM (docs/CRM_PLAN.md), con prefijo CRM_ en el .env."""
import datetime
import zoneinfo
from functools import cache
from pathlib import Path

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

    # Dias habiles despues del primer mail para que el seguimiento aparezca en "Hoy".
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
