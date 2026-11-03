"""Estudio: texto a voz y transcripcion para todos los planes (docs/features/ESTUDIO.md).

Cada trabajo es una fila de `studio_items`. Al crearlo se reservan los segundos estimados contra los minutos
entrantes del plan (con el lock del cliente, como quota.admit); al terminar se ajustan a los reales y, si falla,
a 0. `quota.used_seconds` suma esta tabla. Borrar saca el contenido pero deja la fila: no devuelve minutos.

`studio_loop` corre en la app y procesa de a un trabajo por motor, en pedazos cortos, porque los motores son
los mismos que atienden las llamadas. Las pruebas de voz tambien quedan aca (`recording_preview`).
"""
import asyncio
import logging
import math
import re
import shutil
import wave
from array import array
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import BinaryIO

import anyio
import av
import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import get_sessionmaker, utcnow
from ..models import CallMode, Client, StudioItem
from ..models._common import new_id
from ..whatsapp.audio import pcm_to_wav
from . import quota, tts, voices
from .errors import Conflict, Invalid, QuotaExceeded

logger = logging.getLogger(__name__)

TTS, STT = "tts", "stt"
QUEUED, PROCESSING, DONE, FAILED = "queued", "processing", "done", "failed"
ORIGIN_STUDIO, ORIGIN_VOICE_TEST = "studio", "voice_test"
AUDIO_FILE = "audio.wav"
STT_RATE = 16_000
STT_LANGUAGE = "es"
DEFAULT_CHARS_PER_SECOND = 16.0   # voz sin car_s medido: la mediana del catalogo (tts/finetune/voces.tsv)
PAUSE_BETWEEN_CHUNKS = 0.2        # silencio entre pedazos del texto, en segundos
QUIET_SEARCH_SECONDS = 3          # el audio se corta en el tramo mas silencioso de los ultimos segundos del pedazo
QUIET_WINDOW_SAMPLES = STT_RATE // 10
FAILURE_MESSAGE = "No pudimos procesarlo. No se descontaron minutos: probá de nuevo."

# Formatos de descarga: contenedor, codec, tasa, bit rate y tipo de contenido.
FORMATS = {
    "mp3": ("mp3", "libmp3lame", 24_000, 64_000, "audio/mpeg"),
    "ogg": ("ogg", "libopus", 24_000, 32_000, "audio/ogg"),
    "flac": ("flac", "flac", 24_000, None, "audio/flac"),
}
WAV_MEDIA_TYPE = "audio/wav"
# Lo que se acepta subir, con el tipo con que se sirve. Lo demas no se guarda: el archivo se sirve desde el dominio
# del panel y un tipo que el navegador ejecute (html, svg) seria un XSS.
UPLOAD_TYPES = {".mp3": "audio/mpeg", ".mpeg": "audio/mpeg", ".mpga": "audio/mpeg", ".wav": "audio/wav",
                ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg", ".flac": "audio/flac",
                ".m4a": "audio/mp4", ".mp4": "video/mp4", ".aac": "audio/aac", ".webm": "audio/webm",
                ".mkv": "video/x-matroska", ".aiff": "audio/aiff", ".aif": "audio/aiff", ".amr": "audio/amr",
                ".wma": "audio/x-ms-wma", ".3gp": "audio/3gpp"}
# Solo estos demuxers de FFmpeg: los de listas (concat, hls, dash) leerian otros archivos o URLs desde el servidor.
DEMUXERS = "mov,mp4,m4a,3gp,3g2,mj2,mp3,ogg,wav,flac,aac,matroska,webm,aiff,amr,asf"


def billable(seconds: float) -> float:
    """Lo que descuenta un audio: sus segundos reales. Sumados en el mes, no por minuto iniciado: si no, una prueba
    de voz de 5 s costaria un minuto y Free se agotaria con 20 pruebas."""
    return max(seconds, 0.0)


def item_dir(client_id: str, item_id: str) -> Path:
    return settings.call_recordings_dir / "studio" / client_id / item_id


def _no_minutes(message: str = "No te quedan minutos en el plan este mes") -> QuotaExceeded:
    return QuotaExceeded(message, "inbound_minutes")


def _reserve(s: Session, client_id: str, seconds: float) -> None:
    """Toma el lock del cliente y verifica el cupo: quien llama inserta el item y hace commit en la misma sesion."""
    client = s.scalar(select(Client).where(Client.id == client_id).with_for_update(key_share=True, of=Client))
    if client is None or not client.active:
        raise QuotaExceeded("El cliente no está activo", "client_inactive")
    left = quota.remaining_seconds(s, client, CallMode.entrante)
    if left is None or seconds <= left:
        return
    if left <= 0:
        raise _no_minutes()
    raise _no_minutes(f"Necesita unos {math.ceil(seconds / 60)} minutos y te quedan {max(left // 60, 0)} este mes")


def check_minutes(s: Session, client: Client) -> None:
    """Para una prueba de voz: que quede algo. El largo no se estima, son 200 caracteres como mucho."""
    left = quota.remaining_seconds(s, client, CallMode.entrante)
    if left is not None and left <= 0:
        raise _no_minutes()


def _title(text: str) -> str:
    return " ".join(text.split())[:80]


# ---------- texto a voz ----------

def estimate_tts_seconds(text: str, voice: str) -> float:
    entry = voices.catalog().get(voice)
    return len(text) / ((entry.car_s if entry else None) or DEFAULT_CHARS_PER_SECOND)


def create_speech(s: Session, client_id: str, user_id: str | None, text: str, voice: str) -> StudioItem:
    voice = voice.strip().lower()
    # Una voz fuera del catalogo mata el engine de vllm-tts (AGENTS.md).
    if voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}", "invalid_voice")
    text = text.strip()
    if not text:
        raise Invalid("El texto está vacío", "invalid_request")
    if len(text) > settings.studio_tts_max_chars:
        raise Invalid(f"El texto puede tener hasta {settings.studio_tts_max_chars} caracteres", "invalid_request")
    estimate = billable(estimate_tts_seconds(text, voice))
    _reserve(s, client_id, estimate)
    item = StudioItem(client_id=client_id, created_by=user_id, kind=TTS, status=QUEUED, title=_title(text), voice=voice,
                      text=text, billed_seconds=estimate)
    s.add(item)
    s.commit()
    return item


def split_text(text: str, limit: int) -> list[str]:
    """Pedazos de hasta `limit` caracteres, cortados por oraciones (o por palabras, en una oracion muy larga)."""
    pieces: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?…:;])\s+|\n+", text):
        sentence = sentence.strip()
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit + 1)
            cut = cut if cut > 0 else limit
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        pieces.append(current)
    return pieces


def _wav_writer(path: Path) -> wave.Wave_write:
    path.parent.mkdir(parents=True, exist_ok=True)
    w = wave.open(str(path), "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(tts.SAMPLE_RATE)
    return w


async def _run_speech(sessions: sessionmaker[Session], item_id: str, client_id: str, voice: str, text: str) -> None:
    chunks = split_text(text, settings.studio_tts_chunk_chars)
    directory = item_dir(client_id, item_id)
    part = directory / f"{AUDIO_FILE}.part"
    writer = await asyncio.to_thread(_wav_writer, part)
    silence = b"\0\0" * int(tts.SAMPLE_RATE * PAUSE_BETWEEN_CHUNKS)
    frames = 0
    try:
        for n, chunk in enumerate(chunks, start=1):
            pcm = bytearray(silence if n > 1 else b"")
            async for piece in tts.synthesize_pcm(voice, chunk):
                pcm += piece
            await asyncio.to_thread(writer.writeframes, bytes(pcm))
            frames += len(pcm) // 2
            await asyncio.to_thread(_progress, sessions, item_id, n * 100 // len(chunks))
    finally:
        await asyncio.to_thread(writer.close)
    await asyncio.to_thread(part.rename, directory / AUDIO_FILE)
    await asyncio.to_thread(_finish, sessions, item_id, frames / tts.SAMPLE_RATE, None, AUDIO_FILE)


# ---------- transcripcion ----------

def _open_upload(file: BinaryIO):
    return av.open(file, options={"format_whitelist": DEMUXERS})


def probe_seconds(path: Path) -> float:
    """Duracion del archivo: la del encabezado o, si no la trae, decodificandolo. Invalid si no tiene audio legible."""
    try:
        with path.open("rb") as f, _open_upload(f) as container:
            if not container.streams.audio:
                raise Invalid("El archivo no tiene audio", "audio_invalid")
            if container.duration:
                return container.duration / av.time_base
            seconds = 0.0
            for frame in container.decode(audio=0):
                seconds += frame.samples / frame.rate
            return seconds
    except Invalid:
        raise
    except Exception as e:      # av.error.FFmpegError y afines: audio corrupto o formato raro
        raise Invalid("No pudimos leer ese archivo de audio", "audio_invalid") from e


def create_transcription(s: Session, client_id: str, user_id: str | None, upload: BinaryIO,
                         filename: str | None) -> StudioItem:
    name = Path((filename or "audio").replace("\\", "/")).name[:200] or "audio"
    suffix = Path(name).suffix.lower()
    if suffix not in UPLOAD_TYPES:
        raise Invalid(f"Ese formato no se puede transcribir. Subí uno de estos: {', '.join(sorted(UPLOAD_TYPES))}",
                      "audio_format")
    item_id = new_id()
    directory = item_dir(client_id, item_id)
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / f"source{suffix}"
    try:
        with source.open("wb") as out:
            shutil.copyfileobj(upload, out)
        if source.stat().st_size > settings.studio_stt_max_bytes:
            raise Invalid(f"El archivo supera los {settings.studio_stt_max_bytes // (1024 * 1024)} MB", "audio_too_large")
        seconds = probe_seconds(source)
        if seconds > settings.studio_stt_max_seconds:
            raise Invalid(f"El audio supera las {settings.studio_stt_max_seconds // 3600} horas", "audio_too_long")
        estimate = billable(seconds)
        _reserve(s, client_id, estimate)
        item = StudioItem(id=item_id, client_id=client_id, created_by=user_id, kind=STT, status=QUEUED, title=name,
                          language=STT_LANGUAGE, file_name=source.name, audio_seconds=seconds, billed_seconds=estimate)
        s.add(item)
        s.commit()
    except Exception:
        s.rollback()
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return item


def _quietest_cut(pcm: bytes, start: int) -> int:
    """El byte, desde `start`, donde empieza la ventana con menos energia: ahi se corta para no partir una palabra."""
    samples = array("h")
    samples.frombytes(pcm[start:])
    best, best_energy = len(samples), None
    for i in range(0, len(samples) - QUIET_WINDOW_SAMPLES + 1, QUIET_WINDOW_SAMPLES):
        energy = sum(map(abs, samples[i:i + QUIET_WINDOW_SAMPLES]))
        if best_energy is None or energy < best_energy:
            best, best_energy = i, energy
    return start + best * 2


def audio_chunks(path: Path, chunk_seconds: int) -> Iterator[bytes]:
    """PCM s16 mono a 16 kHz en pedazos de hasta `chunk_seconds`, sin cargar el archivo entero en memoria.
    Sincronico: cada `next` va en un thread."""
    size = chunk_seconds * STT_RATE * 2
    search = min(QUIET_SEARCH_SECONDS, chunk_seconds // 2) * STT_RATE * 2
    buffer = bytearray()
    with path.open("rb") as f, _open_upload(f) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=STT_RATE)
        for frame in container.decode(audio=0):
            for out in resampler.resample(frame):
                buffer += bytes(out.planes[0])[:out.samples * 2]
            while len(buffer) >= size:
                cut = _quietest_cut(bytes(buffer[:size]), size - search)
                yield bytes(buffer[:cut])
                del buffer[:cut]
        for out in resampler.resample(None):
            buffer += bytes(out.planes[0])[:out.samples * 2]
    while len(buffer) > size:
        cut = _quietest_cut(bytes(buffer[:size]), size - search)
        yield bytes(buffer[:cut])
        del buffer[:cut]
    if buffer:
        yield bytes(buffer)


async def transcribe_chunk(pcm: bytes) -> str:
    """Un pedazo al STT, igual que la API de inferencia."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.inference_timeout_seconds, connect=5)) as http:
        r = await http.post(f"{settings.vllm_stt_base_url}/audio/transcriptions",
                            data={"model": settings.vllm_stt_model, "language": STT_LANGUAGE, "response_format": "json"},
                            files={"file": ("audio.wav", pcm_to_wav(pcm), "audio/wav")},
                            headers={"Authorization": f"Bearer {settings.vllm_api_key}"})
    r.raise_for_status()
    return (r.json().get("text") or "").strip()


async def _run_transcription(sessions: sessionmaker[Session], item_id: str, client_id: str, file_name: str,
                             expected: float) -> None:
    source = item_dir(client_id, item_id) / file_name
    chunks = await asyncio.to_thread(audio_chunks, source, settings.studio_stt_chunk_seconds)
    parts: list[str] = []
    samples = 0
    while (pcm := await asyncio.to_thread(next, chunks, None)) is not None:
        samples += len(pcm) // 2
        # Bloques muy cortos o sin voz: el STT no tiene nada que decir de menos de 0,1 s (como en WhatsApp).
        if len(pcm) >= STT_RATE // 5 and (text := await transcribe_chunk(pcm)):
            parts.append(text)
        seconds = samples / STT_RATE
        await asyncio.to_thread(_progress, sessions, item_id, min(int(seconds * 100 / max(expected, 1)), 99))
    await asyncio.to_thread(_finish, sessions, item_id, samples / STT_RATE, " ".join(parts), None)


# ---------- cola ----------

def _progress(sessions: sessionmaker[Session], item_id: str, progress: int) -> None:
    with sessions() as s:
        if item := s.get(StudioItem, item_id):
            item.progress = progress
            s.commit()


def _finish(sessions: sessionmaker[Session], item_id: str, seconds: float, text: str | None,
            file_name: str | None) -> None:
    with sessions() as s:
        item = s.get(StudioItem, item_id)
        if item is None:
            return
        item.status, item.progress, item.finished_at = DONE, 100, utcnow()
        item.audio_seconds, item.billed_seconds = seconds, billable(seconds)
        if text is not None:
            item.text = text
        if file_name is not None:
            item.file_name = file_name
        s.commit()


def _fail(sessions: sessionmaker[Session], item_id: str) -> None:
    """Sin resultado no se cobra. El archivo subido queda, como el resto del historial del cliente."""
    with sessions() as s:
        item = s.get(StudioItem, item_id)
        if item is None:
            return
        item.status, item.error, item.finished_at, item.billed_seconds = FAILED, FAILURE_MESSAGE, utcnow(), 0.0
        s.commit()
        if item.kind == TTS:
            shutil.rmtree(item_dir(item.client_id, item.id), ignore_errors=True)


def claim(sessions: sessionmaker[Session], kind: str) -> dict | None:
    """El trabajo mas viejo del motor, ya en `processing`. SKIP LOCKED por si hay dos procesos."""
    with sessions() as s:
        item = s.scalar(select(StudioItem).where(StudioItem.kind == kind, StudioItem.status == QUEUED,
                                                 StudioItem.deleted_at.is_(None))
                        .order_by(StudioItem.created_at).limit(1).with_for_update(skip_locked=True))
        if item is None:
            return None
        item.status = PROCESSING
        s.commit()
        return {"id": item.id, "client_id": item.client_id, "voice": item.voice, "text": item.text,
                "file_name": item.file_name, "seconds": item.audio_seconds or 0.0}


def requeue_interrupted(sessions: sessionmaker[Session]) -> int:
    """Los que estaban en proceso cuando se reinicio la app vuelven a la cola."""
    with sessions() as s:
        items = s.scalars(select(StudioItem).where(StudioItem.status == PROCESSING)).all()
        for item in items:
            item.status, item.progress = QUEUED, 0
        s.commit()
        return len(items)


async def process(sessions: sessionmaker[Session], kind: str, job: dict) -> None:
    try:
        if kind == TTS:
            await _run_speech(sessions, job["id"], job["client_id"], job["voice"], job["text"])
        else:
            await _run_transcription(sessions, job["id"], job["client_id"], job["file_name"], job["seconds"])
    except asyncio.CancelledError:
        raise   # la app se apaga: al volver, requeue_interrupted
    except Exception:
        logger.exception("estudio: fallo el trabajo %s (%s)", job["id"], kind)
        await asyncio.to_thread(_fail, sessions, job["id"])


async def _worker(sessions: sessionmaker[Session], kind: str) -> None:
    while True:
        await asyncio.sleep(settings.studio_tick_seconds)
        try:
            while job := await asyncio.to_thread(claim, sessions, kind):
                await process(sessions, kind, job)
        except Exception:
            logger.exception("estudio: fallo la vuelta de %s", kind)


async def studio_loop() -> None:
    """Corre en la app (lifespan): un trabajo a la vez por motor, para no competir con las llamadas."""
    sessions = get_sessionmaker()
    # Reintenta: si la base no esta lista al arrancar (o falta migrar), la cola no se tiene que morir en silencio.
    while True:
        try:
            await asyncio.to_thread(requeue_interrupted, sessions)
            break
        except Exception:
            logger.exception("estudio: no se pudieron recuperar los trabajos interrumpidos")
            await asyncio.sleep(settings.studio_tick_seconds)
    await asyncio.gather(_worker(sessions, TTS), _worker(sessions, STT))


# ---------- historial ----------

def page(s: Session, client_id: str | None, kind: str | None, limit: int, offset: int) -> tuple[list[StudioItem], int]:
    where = [StudioItem.deleted_at.is_(None)]
    if client_id:
        where.append(StudioItem.client_id == client_id)
    if kind:
        where.append(StudioItem.kind == kind)
    total = s.scalar(select(func.count()).select_from(StudioItem).where(*where)) or 0
    return list(s.scalars(select(StudioItem).where(*where).order_by(StudioItem.created_at.desc())
                          .limit(limit).offset(offset))), total


def delete_item(s: Session, item: StudioItem) -> None:
    """Saca el audio y el texto y deja la fila con sus segundos. Lo que estaba en cola todavia no se uso: no descuenta."""
    if item.status == PROCESSING:
        raise Conflict("Se está procesando: esperá a que termine para borrarlo", "studio_busy")
    if item.status == QUEUED:
        item.status, item.billed_seconds = FAILED, 0.0
    item.deleted_at, item.text, item.file_name = utcnow(), None, None
    s.commit()
    shutil.rmtree(item_dir(item.client_id, item.id), ignore_errors=True)


def _convert(source: Path, target: Path, fmt: str) -> None:
    container, codec, rate, bit_rate, _ = FORMATS[fmt]
    part = target.with_name(f"{target.name}.part")
    with av.open(str(source)) as src, av.open(str(part), "w", format=container) as dst:
        stream = dst.add_stream(codec, rate=rate, layout="mono")
        if bit_rate:
            stream.bit_rate = bit_rate
        resampler = av.AudioResampler(format=stream.format.name, layout="mono", rate=rate)

        def write(frame) -> None:
            for out in resampler.resample(frame):
                for packet in stream.encode(out):
                    dst.mux(packet)

        for frame in src.decode(audio=0):
            write(frame)
        write(None)
        for packet in stream.encode(None):
            dst.mux(packet)
    part.rename(target)


def audio_file(item: StudioItem, fmt: str) -> tuple[Path, str, str]:
    """(archivo, tipo de contenido, extension) del audio. El STT, el archivo que se subio; el TTS, en el formato
    pedido: la primera vez se convierte y queda guardado al lado."""
    if not item.file_name:
        raise Invalid("Este elemento no tiene audio", "no_audio")
    source = item_dir(item.client_id, item.id) / item.file_name
    if item.kind == STT:
        return source, UPLOAD_TYPES.get(source.suffix.lower(), "application/octet-stream"), source.suffix
    if fmt == "wav":
        return source, WAV_MEDIA_TYPE, ".wav"
    target = source.with_suffix(f".{fmt}")
    if not target.is_file():
        _convert(source, target, fmt)
    return target, FORMATS[fmt][4], f".{fmt}"


# ---------- pruebas de voz ----------

def _save_preview(sessions: sessionmaker[Session], client_id: str, user_id: str | None, voice: str, text: str,
                  pcm: bytes) -> None:
    seconds = len(pcm) / tts.BYTES_PER_SECOND
    with sessions() as s:
        item = StudioItem(client_id=client_id, created_by=user_id, kind=TTS, origin=ORIGIN_VOICE_TEST, status=DONE,
                          title=_title(text), voice=voice.strip().lower(), text=text.strip(), progress=100,
                          audio_seconds=seconds, billed_seconds=billable(seconds), file_name=AUDIO_FILE,
                          finished_at=utcnow())
        s.add(item)
        s.flush()
        path = item_dir(client_id, item.id) / AUDIO_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(tts.wav_from_pcm(pcm))
        s.commit()


def recording_preview(stream: AsyncIterator[bytes], sessions: sessionmaker[Session], *, client_id: str,
                      user_id: str | None, voice: str, text: str, audio_format: str) -> AsyncIterator[bytes]:
    """Deja pasar el audio de la prueba de voz y, al terminar, la guarda y descuenta lo entregado: si el navegador
    corta, cuenta lo que salio. Fallar al guardar no le corta el audio al que escucha."""
    async def run() -> AsyncIterator[bytes]:
        audio = bytearray()
        try:
            async for chunk in stream:
                audio += chunk
                yield chunk
        finally:
            pcm = bytes(audio[tts.WAV_HEADER_BYTES:] if audio_format == "wav" else audio)
            pcm = pcm[:len(pcm) // 2 * 2]
            if pcm:
                with anyio.CancelScope(shield=True):
                    try:
                        await anyio.to_thread.run_sync(
                            lambda: _save_preview(sessions, client_id, user_id, voice, text, pcm))
                    except Exception:
                        logger.exception("estudio: no se pudo guardar la prueba de voz")

    return run()
