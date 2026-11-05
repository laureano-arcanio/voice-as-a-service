"""Base propia de Registros. Las columnas de fecha son UTC sin zona."""
import datetime
import uuid
from functools import cache
from typing import TypeVar

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

# Los que esperan una conexión fallan rápido: /health no se puede colgar con el pool lleno.
POOL_TIMEOUT_SECONDS = 5
CONNECT_TIMEOUT_SECONDS = 3


class Base(DeclarativeBase):
    pass


T = TypeVar("T", bound=Base)


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


def make_engine(dsn: str) -> Engine:
    # pool_pre_ping: tras un reinicio de db descarta las conexiones muertas.
    # hide_parameters: los errores de SQL no llevan teléfonos ni datos de salud a los logs.
    return create_engine(
        dsn,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=POOL_TIMEOUT_SECONDS,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )


@cache
def get_engine() -> Engine:
    return make_engine(settings.db_dsn)


@cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session():
    with get_sessionmaker()() as s:
        yield s


def tenant_get(s: Session, model: type[T], tenant_id: str, row_id: str) -> T | None:
    """Fila por id, solo si es de ese tenant. Las rutas leen por acá, nunca con s.get a secas."""
    row = s.get(model, row_id)
    return row if row is not None and row.tenant_id == tenant_id else None
