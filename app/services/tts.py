"""Prueba de voz: sintetiza un texto directo contra el TTS, sin llamada ni LiveKit.

Dos formas de recibir el audio: `preview` (WAV completo, cuando el motor termina) y `preview_pcm` (PCM crudo
a medida que el motor lo sintetiza, para reproducirlo mientras se genera: la landing y el dashboard).
"""
import base64
import json
import logging
import struct
from collections.abc import AsyncIterator

import httpx

from ..config import settings
from . import voices
from .errors import Invalid, Upstream

logger = logging.getLogger(__name__)

MAX_PREVIEW_CHARS = 600
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
    if len(text) > MAX_PREVIEW_CHARS:
        raise Invalid(f"Texto de mas de {MAX_PREVIEW_CHARS} caracteres")
    body = {"model": settings.vllm_tts_model, "voice": voice, "input": text, "response_format": response_format}
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
