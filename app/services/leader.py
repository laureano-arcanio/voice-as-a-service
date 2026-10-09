"""Consumidor unico (H14): un solo proceso corre los loops de fondo.

Barrido de chats vencidos, envio de campañas, recuperacion de entrantes de WhatsApp,
retencion y conciliacion de llamadas no pueden correr en dos procesos a la vez (dos workers
de uvicorn, o un deploy con la app vieja y la nueva solapadas): mandarian dos veces.

En PostgreSQL el lider es quien tiene el lock consultivo LOCK_KEY (pg_try_advisory_lock) en una
conexion propia, fuera del pool. Si esa conexion se cae, PostgreSQL suelta el lock y otro
proceso lo toma en la vuelta siguiente (RETRY_SECONDS). En SQLite (tests, scripts) hay un
solo proceso: siempre es lider.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from functools import cache

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# Clave del lock consultivo (bigint): "ATNT" en ASCII. Unica en la base de la app.
LOCK_KEY = 0x41544E54
RETRY_SECONDS = 15.0


class Leader:
    def __init__(self, engine: Engine, key: int = LOCK_KEY):
        self.key = key
        self._pg = engine.dialect.name == "postgresql"
        self._url = engine.url
        self._engine: Engine | None = None
        self._conn: Connection | None = None
        # Sin PostgreSQL no hay con quien competir.
        self.is_leader = not self._pg
        self._logged: bool | None = None    # ultimo estado logueado (solo los cambios)

    def try_acquire(self) -> bool:
        """Sincronico (va en un hilo). Si ya es lider, comprueba que la conexion siga viva
        (si no, el lock se perdio); si no lo es, intenta tomarlo. Devuelve is_leader."""
        if not self._pg:
            return True
        if self._conn is not None:
            try:
                self._conn.execute(text("SELECT 1"))
                self._conn.commit()
                return True
            except SQLAlchemyError:
                logger.warning("lider: se cayo la conexion del lock; se deja de ser lider")
                self._drop()
        try:
            if self._engine is None:
                # Conexion propia (NullPool): no ocupa un lugar del pool de la app.
                self._engine = create_engine(self._url, poolclass=NullPool, hide_parameters=True)
            conn = self._engine.connect()
            got = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": self.key}).scalar())
            conn.commit()       # el lock es de sesion: sigue despues del commit, sin quedar idle in transaction
            if got:
                self._conn = conn
            else:
                conn.close()
        except SQLAlchemyError:
            logger.exception("lider: no se pudo pedir el lock")
            self._drop()
        self.is_leader = self._conn is not None
        return self.is_leader

    def release(self) -> None:
        """Al apagar: suelta el lock para que otro proceso lo tome sin esperar."""
        if self._conn is not None:
            try:
                self._conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": self.key})
                self._conn.commit()
            except SQLAlchemyError:
                logger.warning("lider: no se pudo soltar el lock (se suelta al cerrar la conexion)")
        self._drop()
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def _drop(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except SQLAlchemyError:
                logger.debug("lider: la conexion del lock ya estaba cerrada")
        self._conn = None
        self.is_leader = not self._pg

    async def acquire(self) -> bool:
        now = await asyncio.to_thread(self.try_acquire)
        if self._pg and now != self._logged:
            self._logged = now
            logger.warning("lider: %s", "este proceso corre los loops de fondo" if now
                           else "otro proceso tiene el lock: loops de fondo en pausa")
        return now

    async def loop(self, interval: float = RETRY_SECONDS) -> None:
        """Corre en la app (lifespan): renueva o pide el lock cada interval segundos."""
        while True:
            await asyncio.sleep(interval)
            try:
                await self.acquire()
            except Exception:
                logger.exception("lider: fallo la vuelta del lock")


async def every(leader: Leader | None, interval: float, fn: Callable[[], Coroutine], name: str,
                first_delay: float | None = None) -> None:
    """Corre fn cada interval segundos, solo en el lider. Un fallo se loguea y sigue."""
    await asyncio.sleep(interval if first_delay is None else first_delay)
    while True:
        if leader is None or leader.is_leader:
            try:
                await fn()
            except Exception:
                logger.exception("%s: fallo", name)
        await asyncio.sleep(interval)


@cache
def get_leader() -> Leader:
    from ..db import get_engine

    return Leader(get_engine())
