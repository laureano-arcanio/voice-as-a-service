"""TTS en streaming para la landing y el dashboard: PCM crudo mientras el motor sintetiza (formato pcm) y WAV completo."""
import base64
import json
import struct

import httpx
import pytest

from app.config import settings
from app.services import tts

from .test_api import V1 as API  # noqa: F401  (admin: fixture)
from .test_api import admin
from .test_demo import V1 as DEMO
from .test_demo import landing, session  # noqa: F401  (landing: fixture)


def sse(*pcm_chunks: bytes, done: bool = True) -> bytes:
    events = [{"type": "speech.audio.delta", "audio": base64.b64encode(c).decode()} for c in pcm_chunks]
    if done:
        events.append({"type": "speech.audio.done", "usage": {}})
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


class Pieces(httpx.AsyncByteStream):
    def __init__(self, body: bytes, size: int):
        self.body, self.size = body, size

    async def __aiter__(self):
        for i in range(0, len(self.body), self.size):
            yield self.body[i:i + self.size]


class Engine(list):
    """Los pedidos que recibio el motor simulado, y los bloques de audio que contesta."""

    def __init__(self):
        super().__init__()
        self.chunks = [b"\x01\x00" * 1920, b"\x02\x00" * 48000]


@pytest.fixture
def engine(monkeypatch):
    """vllm-tts simulado: guarda el pedido y contesta el SSE (pcm) o un WAV (wav)."""
    seen = Engine()
    chunks = seen.chunks

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        if body.get("stream"):
            return httpx.Response(200, stream=Pieces(sse(*chunks), 9), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, content=tts.wav_from_pcm(b"".join(chunks)))

    async def fake_open(voice, text, response_format, stream):
        voice = voice.strip().lower()
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        body = {"voice": voice, "input": text, "response_format": response_format}
        if stream:
            body["stream"] = True
        return client, await client.send(client.build_request("POST", "http://tts/v1/audio/speech", json=body),
                                         stream=True)

    monkeypatch.setattr(tts, "_open", fake_open)
    return seen


def test_wav_from_pcm_header():
    wav = tts.wav_from_pcm(b"\0\0" * 24000)
    assert wav[:4] == b"RIFF" and wav[8:16] == b"WAVEfmt "
    channels, rate, byte_rate, _, bits = struct.unpack("<HIIHH", wav[22:36])
    assert (channels, rate, byte_rate, bits) == (1, 24000, 48000, 16)
    assert struct.unpack("<I", wav[40:44])[0] == 48000 and len(wav) == 44 + 48000


def test_preview_pcm_decodes_the_engine_events_as_they_arrive(engine):
    import asyncio

    async def run():
        stream = await tts.preview_pcm("Sofia", "Hola")
        return [c async for c in stream]

    chunks = asyncio.run(run())
    assert chunks == engine.chunks                      # un bloque por evento, en orden, sin el `done`
    assert engine[0]["stream"] is True and engine[0]["response_format"] == "pcm" and engine[0]["voice"] == "sofia"


def test_demo_tts_pcm_streams_and_is_cached_apart_from_wav(landing, engine):
    headers = session(landing)
    body = {"voice": "sofia", "text": "Hola, te llamo por tu turno.", "format": "pcm"}
    pcm = b"".join(engine.chunks)
    for _ in range(2):
        r = landing.client.post(f"{DEMO}/tts", json=body, headers=headers)
        assert r.status_code == 200 and r.headers["content-type"] == "audio/pcm" and r.content == pcm
        assert r.headers["cache-control"] == "no-store" and r.headers["x-accel-buffering"] == "no"
    assert len(engine) == 1                              # la segunda salio de la cache
    r = landing.client.post(f"{DEMO}/tts", json={**body, "format": "wav"}, headers=headers)
    assert r.headers["content-type"] == "audio/wav" and r.content == tts.wav_from_pcm(pcm)
    assert len(engine) == 2 and "stream" not in engine[1]    # el WAV sigue siendo el archivo completo del motor
    default = landing.client.post(f"{DEMO}/tts", json={k: v for k, v in body.items() if k != "format"}, headers=headers)
    assert default.headers["content-type"] == "audio/wav" and len(engine) == 2
    assert landing.client.post(f"{DEMO}/tts", json={**body, "format": "mp3"}, headers=headers).status_code == 422


def test_demo_tts_pcm_counts_against_the_ip_limit(landing, engine, monkeypatch):
    monkeypatch.setattr(settings, "demo_ip_tts_per_hour", 1)
    headers = session(landing)
    body = {"voice": "sofia", "text": "Uno", "format": "pcm"}
    assert landing.client.post(f"{DEMO}/tts", json=body, headers=headers).status_code == 200
    assert landing.client.post(f"{DEMO}/tts", json={**body, "text": "Dos"}, headers=headers).status_code == 429


def test_dashboard_preview_pcm_and_wav(api, admin, engine):
    pcm = b"".join(engine.chunks)
    r = admin.post(f"{API}/tts/preview", json={"voice": "sofia", "text": "Hola", "format": "pcm"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/pcm" and r.content == pcm
    r = admin.post(f"{API}/tts/preview", json={"voice": "sofia", "text": "Hola"})
    assert r.headers["content-type"] == "audio/wav" and r.content == tts.wav_from_pcm(pcm)


def test_pcm_validates_voice_and_text_before_the_engine():
    """Una voz que el checkpoint no tiene mata el engine: se rechaza antes de hacer el pedido."""
    import asyncio

    from app.services.errors import Invalid

    for voice, text in (("vivian", "Hola"), ("default", "Hola"), ("sofia", "  "), ("sofia", "a" * 601)):
        with pytest.raises(Invalid):
            asyncio.run(tts.preview_pcm(voice, text))
