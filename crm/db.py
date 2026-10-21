"""Base del CRM: separada de la de `app` (otra base, otra metadata, otras migraciones)."""
import datetime
from functools import cache

from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.db import JSONDoc, make_engine, make_sessions, utcnow  # noqa: F401


def naive_utc(dt: datetime.datetime | None) -> datetime.datetime | None:
    """Las columnas son UTC sin zona: una hora con zona se pasa a UTC; sin zona, se toma como UTC."""
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(datetime.UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


@cache
def get_engine() -> Engine:
    from .config import settings

    return make_engine(settings.db_dsn)


@cache
def get_sessionmaker() -> sessionmaker[Session]:
    return make_sessions(get_engine())


def get_session():
    with get_sessionmaker()() as s:
        yield s
