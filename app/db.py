"""Capa comun de la base (PostgreSQL en el stack, SQLite en los tests y el eval).

Los modelos estan en app/models. El esquema lo manejan las migraciones de Alembic
(migrations/, `make migrate`); create_schema (create_all) queda para SQLite en
tests y scripts.
"""
import datetime
from functools import cache

from sqlalchemy import JSON, Engine, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


# Documentos JSON (datos, mensajes, progreso, latencia, definicion de agentes). En
# PostgreSQL van como jsonb (binario, indexable); en SQLite quedan como texto JSON.
JSONDoc = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime.datetime:
    """UTC naive: las columnas son `timestamp` sin zona y la API agrega la Z."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def make_engine(dsn: str) -> Engine:
    # pool_pre_ping: descarta conexiones que el server cerro (reinicio de `db`)
    # en vez de fallar el primer pedido despues.
    # En SQLite las foreign keys no se aplican (no se pide PRAGMA foreign_keys): el
    # eval y los tests corren conversaciones de plantillas que no estan en `agents`.
    # hide_parameters: los errores de SQL no llevan los valores (textos, telefonos, DNI)
    # a los logs; logger.exception los escribiria enteros.
    kw = {}
    if dsn.startswith("postgresql"):
        from .config import settings

        # El default de SQLAlchemy es 5 + 10 y 30 s de espera (H07).
        kw = {"pool_size": settings.db_pool_size, "max_overflow": settings.db_max_overflow,
              "pool_timeout": settings.db_pool_timeout}
    return create_engine(dsn, pool_pre_ping=True, hide_parameters=True, **kw)


def make_sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    """Crea las tablas que falten (tests y scripts con SQLite). Importa app.models
    para que todos los modelos esten registrados en Base.metadata."""
    from . import models  # noqa: F401

    Base.metadata.create_all(engine)


@cache
def get_engine() -> Engine:
    from .config import settings

    return make_engine(settings.db_dsn)


@cache
def get_sessionmaker() -> sessionmaker[Session]:
    return make_sessions(get_engine())
