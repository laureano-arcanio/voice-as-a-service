"""Grabacion completa de la llamada: del spool de Asterisk a la conversacion (docs/features/EQUIPO_TELEFONIA.md).

Asterisk (`MixMonitor`, `line-record` en extensions.conf) graba el canal de la troncal en
`<CALL_RECORDINGS_DIR>/line-spool/rec/` y al cortar lo mueve a `done/`: crudo s16le, 8 kHz, estereo intercalado
(canal 1 quien esta en el telefono, canal 2 lo que oye). Nombres: `in-<UNIQUEID>.sln` (entrante; el worker guarda
el UNIQUEID en `call_logs.line_id`) y `out-<conversation_id sin guiones>.sln` (saliente, header X-Atentina-Rec).

`line_recordings_loop` toma `done/` de a un archivo: busca la llamada, vuelve a mirar la opcion del numero (si se
apago o el numero cambio de cliente, borra), convierte a Ogg/Opus 24 kbps estereo en un hilo a
`<conversation_id>/llamada.ogg` y borra el original. Los de 0 bytes (no atendio) se borran; los que no tienen
llamada despues de `LINK_GRACE_SECONDS`, tambien. Lo que quedo en `rec/` sin escribirse mas de
`CALL_MAX_DURATION_SECONDS` + 10 min (Asterisk se cayo a mitad) es audio valido: se procesa igual."""
import asyncio
import logging
import re
import time
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..conversation.recordings import FULL_RECORDING_NAME, full_recording_path
from ..db import get_sessionmaker
from ..models import CallRow, PhoneNumber
from . import line_spool

logger = logging.getLogger(__name__)

BITRATE = 24000
RATE = 8000
# La llamada se crea antes de que corte (el worker la registra al entrar): el margen cubre el reloj y una base lenta.
LINK_GRACE_SECONDS = 120
STALE_REC_EXTRA_SECONDS = 600

_IN = re.compile(r"^in-(\d{1,20}\.\d{1,10})\.sln$")
_OUT = re.compile(r"^out-([0-9a-f]{32})\.sln$")


def spool_dir() -> Path:
    return settings.call_recordings_dir / "line-spool"


def convert(src: Path, dst: Path) -> None:
    """Crudo s16le 8 kHz estereo a Ogg/Opus 24 kbps estereo. Escribe al lado y renombra: nunca queda un .ogg a
    medias. Sincronico (va en to_thread); un byte suelto al final (archivo cortado) lo descarta el demuxer."""
    import av

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    try:
        with av.open(str(src), format="s16le", options={"sample_rate": str(RATE), "ch_layout": "stereo"}) as inp, \
                av.open(str(tmp), "w", format="ogg") as out:
            stream = out.add_stream("libopus", rate=RATE, layout="stereo")
            stream.bit_rate = BITRATE
            for frame in inp.decode(audio=0):
                for packet in stream.encode(frame):
                    out.mux(packet)
            for packet in stream.encode(None):
                out.mux(packet)
        tmp.replace(dst)
    finally:
        tmp.unlink(missing_ok=True)


def _call(s: Session, name: str) -> CallRow | None:
    if m := _IN.match(name):
        return s.scalar(select(CallRow).where(CallRow.line_id == m.group(1)).limit(1))
    if m := _OUT.match(name):
        return s.get(CallRow, str(uuid.UUID(hex=m.group(1))))
    return None


def _target(s: Session, path: Path, age: float) -> tuple[str, str | None]:
    """Que hacer con un archivo del spool: ("convert", conversation_id), ("wait", None) o ("drop", motivo)."""
    if path.stat().st_size < 4:
        return "drop", "empty"     # no atendio: MixMonitor deja el archivo vacio
    if not (_IN.match(path.name) or _OUT.match(path.name)):
        return ("drop", "unknown") if age > LINK_GRACE_SECONDS else ("wait", None)
    call = _call(s, path.name)
    if call is None:
        return ("drop", "no_call") if age > LINK_GRACE_SECONDS else ("wait", None)
    number = s.get(PhoneNumber, call.phone_number_id) if call.phone_number_id else None
    if number is None or number.client_id != call.client_id or not line_spool.wanted(number):
        return "drop", "disabled"   # la opcion se apago, o el numero se libero o cambio de cliente
    return "convert", call.conversation_id


def process(sessions: sessionmaker[Session], path: Path, now: float | None = None) -> str:
    """Un archivo del spool. Devuelve lo que paso: linked, wait o el motivo por el que se borro. Sincronico."""
    age = (now or time.time()) - path.stat().st_mtime
    with sessions() as s:
        action, detail = _target(s, path, age)
    if action == "wait":
        return "wait"
    if action == "drop":
        path.unlink(missing_ok=True)
        if detail != "empty":
            logger.info("grabacion completa: %s borrado (%s)", path.name, detail)
        return detail or "drop"
    dst = full_recording_path(detail)
    try:
        convert(path, dst)
    except Exception:
        logger.exception("grabacion completa: no se pudo convertir %s", path.name)
        path.unlink(missing_ok=True)
        return "failed"
    with sessions() as s:
        gone = s.get(CallRow, detail) is None
    if gone:   # se borro la conversacion mientras se convertia
        dst.unlink(missing_ok=True)
    path.unlink(missing_ok=True)
    logger.info("grabacion completa: %s -> %s/%s", path.name, detail, FULL_RECORDING_NAME)
    return "no_call" if gone else "linked"


def pending(now: float | None = None) -> list[Path]:
    """Lo terminado (done/) y lo que quedo en rec/ sin escribirse, el mas viejo primero."""
    now = now or time.time()
    root = spool_dir()
    files = list((root / "done").glob("*.sln")) if (root / "done").is_dir() else []
    stale = settings.call_max_duration_seconds + STALE_REC_EXTRA_SECONDS
    if (root / "rec").is_dir():
        files += [p for p in (root / "rec").glob("*.sln") if now - p.stat().st_mtime > stale]
    return sorted(files, key=lambda p: p.stat().st_mtime)


def sweep(sessions: sessionmaker[Session]) -> dict[str, int]:
    """Una vuelta sobre el spool. Devuelve cuantos archivos por resultado."""
    done: dict[str, int] = {}
    for path in pending():
        try:
            result = process(sessions, path)
        except FileNotFoundError:
            continue    # otro lo movio o borro en el medio
        except Exception:   # la base caida o un archivo que no se puede borrar: no traba a los demas
            logger.exception("grabacion completa: no se pudo procesar %s", path.name)
            result = "error"
        done[result] = done.get(result, 0) + 1
    return done


async def line_recordings_loop() -> None:
    """Corre en la app (lifespan): un archivo a la vez, en un hilo, cada `line_recordings_tick_seconds`."""
    sessions = get_sessionmaker()
    while True:
        try:
            await asyncio.to_thread(sweep, sessions)
        except Exception:
            logger.exception("grabacion completa: fallo la vuelta del spool")
        await asyncio.sleep(settings.line_recordings_tick_seconds)
