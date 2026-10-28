"""Prueba de voz: sintetiza un texto directo contra el TTS, sin llamada ni LiveKit.

Dos formas de recibir el audio: `preview` (WAV completo, cuando el motor termina) y `preview_pcm` (PCM crudo
a medida que el motor lo sintetiza, para reproducirlo mientras se genera: la landing y el dashboard).

Cada prueba que llega al motor queda en `api_requests` con su origen (`tracked`): el cliente la ve en los
pedidos de la API, pero no suma al cupo de TTS del plan (api_usage_daily). El texto, hasta
TTS_PREVIEW_MAX_CHARS: alcanza para escuchar una voz, no para generar audio (eso es la API de inferencia).
"""
import base64
import json
import logging
import struct
import time
from collections.abc import AsyncIterator, Awaitable

import anyio
import httpx
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..voice.speech_text import to_speech
from . import api_requests, voices
from .errors import Invalid, ServiceError, Upstream

logger = logging.getLogger(__name__)

# Origen de la prueba en api_requests.source: el panel (sesion), una API key o el MCP, y la landing.
SOURCE_PANEL = "voice_test_panel"
SOURCE_API = "voice_test_api"
SOURCE_LANDING = "voice_test_landing"
WAV_HEADER_BYTES = 44
SAMPLE_RATE = 24_000          # Qwen3-TTS: PCM de 16 bits, mono, a 24 kHz
BYTES_PER_SECOND = SAMPLE_RATE * 2


def wav_from_pcm(pcm: bytes) -> bytes:
    """Encabezado WAV de 44 bytes (mono, 16 bits, 24 kHz) delante del PCM."""
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, BYTES_PER_SECOND, 2, 16)
            + b"data" + struct.pack("<I", len(pcm)) + pcm)


async def sse_events(response: httpx.Response) -> AsyncIterator[dict]:
    """Los eventos `data: {json}` de un stream SSE, a medida que llegan (los bloques se separan con una linea
    en blanco y pueden venir partidos en cualquier byte)."""
    buf = b""
    async for chunk in response.aiter_bytes():
        buf += chunk.replace(b"\r\n", b"\n")
        while (end := buf.find(b"\n\n")) >= 0:
            block, buf = buf[:end], buf[end + 2:]
            data = b"".join(line[5:].strip() for line in block.split(b"\n") if line.startswith(b"data:"))
            if not data:
                continue
            try:
                yield json.loads(data)
            except ValueError:
                logger.warning("TTS: evento SSE ilegible (%d bytes)", len(data))


async def _open(voice: str, text: str, response_format: str, stream: bool) -> tuple[httpx.AsyncClient, httpx.Response]:
    """Valida y abre el pedido al motor. La voz tiene que estar en el catalogo: un pedido sin voz
    valida mata el engine de vllm-tts (AGENTS.md, "Pedido al TTS sin voice")."""
    voice = voice.strip().lower()
    if voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}")
    text = text.strip()
    if not text:
        raise Invalid("Texto vacio")
    if len(text) > settings.tts_preview_max_chars:
        raise Invalid(f"El texto puede tener hasta {settings.tts_preview_max_chars} caracteres")
    # El texto en palabras para la voz (numeros, horas, emails; app/voice/speech_text.py).
    body = {"model": settings.vllm_tts_model, "voice": voice, "input": to_speech(text),
            "response_format": response_format}
    if stream:
        body["stream"] = True
    client = httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5))
    try:
        upstream = await client.send(client.build_request(
            "POST", f"{settings.vllm_tts_base_url}/audio/speech", json=body,
            headers={"Authorization": f"Bearer {settings.vllm_api_key}"}), stream=True)
    except httpx.HTTPError as e:
        await client.aclose()
        raise Upstream(f"TTS no responde: {e}") from e
    if upstream.status_code != 200:
        detail = (await upstream.aread()).decode(errors="replace")[:300]
        await upstream.aclose()
        await client.aclose()
        raise Upstream(f"TTS {upstream.status_code}: {detail}")
    return client, upstream


async def preview(voice: str, text: str) -> AsyncIterator[bytes]:
    """WAV completo (el motor lo entrega cuando termina de sintetizar)."""
    client, upstream = await _open(voice, text, "wav", stream=False)

    async def stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return stream()


async def preview_pcm(voice: str, text: str) -> AsyncIterator[bytes]:
    """PCM crudo (16 bits, mono, 24 kHz) a medida que el motor lo sintetiza: el primer bloque sale a los ~80 ms
    y despues llegan bloques de ~2 s (la sintesis es ~5 veces mas rapida que la reproduccion)."""
    client, upstream = await _open(voice, text, "pcm", stream=True)

    async def stream() -> AsyncIterator[bytes]:
        try:
            async for event in sse_events(upstream):
                if event.get("type") == "speech.audio.delta" and event.get("audio"):
                    yield base64.b64decode(event["audio"])
        finally:
            await upstream.aclose()
            await client.aclose()

    return stream()


async def tracked(start: Awaitable[AsyncIterator[bytes]], sessions: sessionmaker[Session], *, client_id: str,
                  key_id: str | None, source: str, voice: str, characters: int,
                  audio_format: str) -> AsyncIterator[bytes]:
    """Abre la prueba (`preview` o `preview_pcm`) y la anota en api_requests al terminar: ok, cut (el
    navegador corto) o error (del motor). Los rechazos antes del motor (voz inexistente, texto vacio) no."""
    started = time.monotonic()
    fields = {"kind": "tts", "stream": audio_format == "pcm", "voice": voice.strip().lower(),
              "response_format": audio_format, "characters": characters, "source": source}

    def log(status: str, error: ServiceError | None, size: int, first: float | None) -> None:
        audio = max(size - (WAV_HEADER_BYTES if audio_format == "wav" else 0), 0) / BYTES_PER_SECOND
        now = time.monotonic()
        with sessions() as s:
            api_requests.log(s, client_id, key_id, status=status, **fields,
                             http_status=error.status_code if error else 200, error_code=error.code if error else None,
                             duration_ms=int((now - started) * 1000),
                             ttfb_ms=None if first is None else int((first - started) * 1000),
                             audio_seconds=round(audio, 3) if size else None)

    async def record(status: str, error: ServiceError | None = None, size: int = 0, first: float | None = None):
        # Blindado: si el navegador corta, la tarea se cancela y la prueba igual se anota.
        with anyio.CancelScope(shield=True):
            try:
                await anyio.to_thread.run_sync(lambda: log(status, error, size, first))
            except Exception:
                logger.exception("no se pudo anotar la prueba de voz")

    try:
        stream = await start
    except Upstream as e:
        await record("error", e)
        raise

    async def run() -> AsyncIterator[bytes]:
        size, first, status, error = 0, None, "cut", None
        try:
            async for chunk in stream:
                if first is None:
                    first = time.monotonic()
                size += len(chunk)
                yield chunk
            status = "ok"
        except ServiceError as e:
            status, error = "error", e
            raise
        except Exception:
            status, error = "error", Upstream("TTS")
            raise
        finally:
            await record(status, error, size, first)

    return run()
