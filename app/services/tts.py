"""Prueba de voz: sintetiza un texto directo contra el TTS, sin llamada ni LiveKit."""
from collections.abc import AsyncIterator

import httpx

from ..config import settings
from . import voices
from .errors import Invalid, Upstream

MAX_PREVIEW_CHARS = 600


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
