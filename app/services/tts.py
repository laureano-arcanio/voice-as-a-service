"""Prueba de voz: sintetiza un texto directo contra el TTS, sin llamada ni LiveKit."""
from collections.abc import AsyncIterator

import httpx

from ..config import settings
from . import voices
from .errors import Invalid, ServiceError, Upstream

MAX_PREVIEW_CHARS = 600


class TtsBusy(ServiceError):
    status_code = 503
    default_code = "tts_busy"
    retry_after = 5


class PreviewSlots:
    """Sintesis fuera de una llamada en curso en este proceso: pruebas de voz del dashboard
    (/tts/preview) y de la demo publica (/demo/tts). El TTS es el mismo de las llamadas: sin
    tope global, varios clientes o visitantes a la vez le sacan lugar (H04)."""
    in_use = 0


async def preview(voice: str, text: str) -> AsyncIterator[bytes]:
    """WAV en streaming. La voz tiene que estar en el catalogo: un pedido sin voz
    valida mata el engine de vllm-tts (AGENTS.md, "Pedido al TTS sin voice")."""
    voice = voice.strip().lower()
    if voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}")
    text = text.strip()
    if not text:
        raise Invalid("Texto vacio")
    if len(text) > MAX_PREVIEW_CHARS:
        raise Invalid(f"Texto de mas de {MAX_PREVIEW_CHARS} caracteres")
    body = {"model": settings.vllm_tts_model, "voice": voice, "input": text, "response_format": "wav"}
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

    async def stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return stream()


async def synthesize_bounded(voice: str, text: str) -> bytes:
    """preview leido entero dentro del cupo TTS_PREVIEW_MAX_CONCURRENT; lleno: TtsBusy (503
    con Retry-After). Entero y no en streaming: con streaming, un cliente que corta antes de
    empezar a leer dejaba el cupo tomado (la UI y la landing lo bajan entero igual, como blob)."""
    if PreviewSlots.in_use >= settings.tts_preview_max_concurrent:
        raise TtsBusy("Hay muchas pruebas de voz en curso. Probá en unos segundos.")
    PreviewSlots.in_use += 1
    try:
        stream = await preview(voice, text)
        return b"".join([chunk async for chunk in stream])
    except httpx.HTTPError as e:
        raise Upstream(f"El TTS cortó el audio: {type(e).__name__}") from e
    finally:
        PreviewSlots.in_use -= 1
