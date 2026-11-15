"""Contenido de la API de inferencia y de las pruebas de voz, en disco (no en la base: engordaria el pg_dump).

`CALL_RECORDINGS_DIR/api/<client_id>/<AAAA-MM-DD UTC>/<request_id>/`, con nombres fijos (nada del path viene del
pedido): request.json, response.json, output.wav e input.<ext> (el audio subido al STT). La fila de `api_requests`
lleva `content_bytes` (None = no hay). La purga borra carpetas de dia enteras segun el vencimiento de cada cliente
(`clients.api_content_retention_days`, None = indefinido). Sin backup, como las grabaciones (docs/INFRA.md).
Toda falla al guardar se loguea y no se propaga: el pedido ya se respondio.
"""
import datetime
import io
import logging
import shutil
import time
import wave
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..models import ApiRequest, Client
from .studio import UPLOAD_TYPES

logger = logging.getLogger(__name__)

RETENTION_CHOICES = (7, 30, 90, 180, 365)
FIXED_NAMES = ("request.json", "response.json", "output.wav")
PCM_RATE = 24000

_room: tuple[float, bool] = (0.0, True)   # (cuando se midio, si hay lugar)


def base_dir() -> Path:
    return settings.call_recordings_dir / "api"


def client_dir(client_id: str) -> Path:
    return base_dir() / client_id


def request_dir(client_id: str, created_at: datetime.datetime, request_id: str) -> Path:
    return client_dir(client_id) / created_at.date().isoformat() / request_id


def input_name(filename: str | None) -> str:
    """input.<ext> con la extension del archivo subido si esta en la lista del Estudio; si no, input.bin."""
    suffix = Path(filename or "").suffix.lower()
    return f"input{suffix}" if suffix in UPLOAD_TYPES else "input.bin"


def _allowed(name: str) -> bool:
    return name in FIXED_NAMES or name == "input.bin" or (
        name.startswith("input.") and name[len("input"):] in UPLOAD_TYPES)


def has_room() -> bool:
    """Si el disco tiene mas de API_CONTENT_MIN_FREE_GB libres; se mide cada 60 s y se loguea cuando falta."""
    global _room
    measured, ok = _room
    now = time.monotonic()
    if now - measured < 60 and measured:
        return ok
    try:
        root = settings.call_recordings_dir
        root.mkdir(parents=True, exist_ok=True)
        ok = shutil.disk_usage(root).free / 1e9 >= settings.api_content_min_free_gb
    except OSError:
        logger.exception("api_content: no se pudo medir el disco")
        ok = False
    if not ok:
        logger.warning("api_content: menos de %s GB libres, no se guarda el contenido", settings.api_content_min_free_gb)
    _room = (now, ok)
    return ok


def save(sessions: sessionmaker[Session], row_id: str, client_id: str, created_at: datetime.datetime,
         files: dict[str, bytes]) -> int | None:
    """Escribe los archivos del pedido y anota `content_bytes`. Devuelve los bytes escritos (None si no guardo)."""
    try:
        if not files or not has_room():
            return None
        directory = request_dir(client_id, created_at, row_id)
        directory.mkdir(parents=True, exist_ok=True)
        total = 0
        for name, data in files.items():
            if not _allowed(name):
                name = "input.bin"
            (directory / name).write_bytes(data)
            total += len(data)
        with sessions() as s:
            s.execute(update(ApiRequest).where(ApiRequest.id == row_id).values(content_bytes=total))
            s.commit()
        return total
    except Exception:
        logger.exception("api_content: no se pudo guardar el contenido de %s", row_id)
        return None


def files_of(row: ApiRequest) -> dict[str, Path]:
    """Los archivos guardados del pedido, por nombre; vacio si no hay contenido."""
    if row.content_bytes is None:
        return {}
    directory = request_dir(row.client_id, row.created_at, row.id)
    if not directory.is_dir():
        return {}
    return {p.name: p for p in directory.iterdir() if p.is_file() and _allowed(p.name)}


def delete(s: Session, row: ApiRequest) -> None:
    """Borra el contenido del pedido (la fila queda); quien llama hace commit."""
    shutil.rmtree(request_dir(row.client_id, row.created_at, row.id), ignore_errors=True)
    row.content_bytes = None


def drop_client(client_id: str) -> None:
    """Al borrar el cliente: todo su contenido."""
    shutil.rmtree(client_dir(client_id), ignore_errors=True)


def purge(s: Session, today: datetime.date) -> tuple[int, int]:
    """Por cliente con vencimiento: borra las carpetas de dia anteriores a hoy - dias (tambien las huerfanas, sin
    fila) y pone content_bytes en None en sus filas. Los indefinidos no se tocan. Devuelve (carpetas, filas)."""
    dirs = rows = 0
    for client_id, days in s.execute(select(Client.id, Client.api_content_retention_days)
                                     .where(Client.api_content_retention_days.is_not(None))).all():
        cutoff = today - datetime.timedelta(days=days)
        root = client_dir(client_id)
        if root.is_dir():
            for day_dir in root.iterdir():
                try:
                    day = datetime.date.fromisoformat(day_dir.name)
                except ValueError:
                    continue
                if day < cutoff:
                    shutil.rmtree(day_dir, ignore_errors=True)
                    dirs += 1
        rows += s.execute(update(ApiRequest).where(
            ApiRequest.client_id == client_id, ApiRequest.content_bytes.is_not(None),
            ApiRequest.created_at < datetime.datetime.combine(cutoff, datetime.time())).values(
            content_bytes=None)).rowcount or 0
    s.commit()
    return dirs, rows


def pcm_to_wav(pcm: bytes) -> bytes:
    """PCM crudo del TTS (24 kHz, mono, 16 bits) en un WAV."""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(PCM_RATE)
        w.writeframes(pcm)
    return out.getvalue()
