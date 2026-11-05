"""Configuración por variables REGISTROS_*. Sin env_file: el compose pasa solo las explícitas,
para que la app no reciba secretos de la plataforma."""
from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REGISTROS_", extra="ignore")

    db_dsn: str = "postgresql+psycopg://registros:@127.0.0.1:5432/registros"
    # A 7 conexiones: db comparte max_connections con app, agent y crm.
    db_pool_size: int = 5
    db_max_overflow: int = 2
    # Sin clave de sesión el login da 503 y /health avisa: nada arranca a medio configurar.
    session_secret: str = ""
    session_hours: int = 12
    public_url: str = "http://127.0.0.1:8040"


@cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
