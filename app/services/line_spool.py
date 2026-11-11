"""Marcadores de la grabacion completa (docs/features/EQUIPO_TELEFONIA.md, docs/TELEFONIA_ANURA.md).

Asterisk graba una entrante (`MixMonitor`, `line-record` en extensions.conf) si existe el archivo
`<CALL_RECORDINGS_DIR>/line-spool/numbers/<e164>`; en `asterisk` es `/var/spool/atentina/numbers/<e164>`. La base
manda: un numero tiene marcador si esta asignado, no suspendido y con `record_full_call`. Se escribe o borra al
cambiar el numero (`sync_number`, tras el commit) y `line_spool_loop` reconcilia todo cada minuto (arranque de la
app, suspension y reasignacion del facturador, spool perdido o restaurado)."""
import asyncio
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import get_sessionmaker
from ..models import PhoneNumber

logger = logging.getLogger(__name__)

_MARKER = re.compile(r"^\+\d{6,15}$")    # solo se borra lo que parece un numero


def numbers_dir() -> Path:
    return settings.call_recordings_dir / "line-spool" / "numbers"


def wanted(number: PhoneNumber) -> bool:
    return bool(number.record_full_call and number.client_id and number.suspended_at is None)


def _put(e164: str) -> None:
    d = numbers_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / e164).touch()


def drop(e164: str) -> None:
    """Borra el marcador de un e164 (no falla si no esta)."""
    (numbers_dir() / e164).unlink(missing_ok=True)


def sync_number(number: PhoneNumber, *, old_e164: str | None = None) -> None:
    """Deja el marcador del numero como dice la base (`old_e164`: el que tenia antes de cambiar). Si el spool
    no se puede escribir, lo registra: el bucle lo reintenta. No corta el pedido."""
    try:
        if old_e164 and old_e164 != number.e164:
            drop(old_e164)
        if wanted(number):
            _put(number.e164)
        else:
            drop(number.e164)
    except OSError:
        logger.exception("grabacion completa: no se pudo actualizar el marcador de %s", number.e164)


def reconcile(s: Session) -> tuple[int, int]:
    """Crea los marcadores que faltan y borra los que no corresponden. Devuelve (creados, borrados)."""
    want = {n.e164 for n in s.scalars(select(PhoneNumber)) if wanted(n)}
    d = numbers_dir()
    have = {p.name for p in d.iterdir() if _MARKER.match(p.name)} if d.is_dir() else set()
    created = deleted = 0
    for e164 in sorted(want - have):
        _put(e164)
        created += 1
    for e164 in sorted(have - want):
        drop(e164)
        deleted += 1
    return created, deleted


def _reconcile_once(sessions: sessionmaker[Session]) -> None:
    with sessions() as s:
        created, deleted = reconcile(s)
    if created or deleted:
        logger.info("grabacion completa: marcadores creados %d, borrados %d", created, deleted)


async def line_spool_loop() -> None:
    """Corre en la app (lifespan): primera pasada al arrancar, despues cada `line_spool_tick_seconds`."""
    sessions = get_sessionmaker()
    while True:
        try:
            await asyncio.to_thread(_reconcile_once, sessions)
        except Exception:
            logger.exception("grabacion completa: no se pudieron reconciliar los marcadores")
        await asyncio.sleep(settings.line_spool_tick_seconds)
