"""Capa comun de la base (PostgreSQL en el stack, SQLite en los tests).

Los modelos viven junto a quien los usa (ConversationRow en conversation/store.py,
CallRow en calls.py) y comparten esta Base. El esquema se crea con create_all al
arrancar: no hay migraciones, un cambio de esquema es `make db-reset`.
"""
import datetime

from sqlalchemy import JSON, Engine, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


# Documentos JSON (datos, mensajes, progreso, latencia). En PostgreSQL van como
# jsonb (binario, indexable, sin conservar espacios ni orden de claves); en
# SQLite quedan como texto JSON.
JSONDoc = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime.datetime:
    """UTC naive: las columnas son `timestamp` sin zona y la API agrega la Z (main._iso)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def make_engine(dsn: str) -> Engine:
    # pool_pre_ping: descarta conexiones que el server cerro (reinicio de `db`)
    # en vez de fallar el primer pedido despues.
    return create_engine(dsn, pool_pre_ping=True)


def make_sessions(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    """Crea las tablas que falten. Importa los modulos con modelos para que esten
    registrados en Base.metadata aunque quien llame solo use uno."""
    from . import calls  # noqa: F401
    from .conversation import store  # noqa: F401

    Base.metadata.create_all(engine)
