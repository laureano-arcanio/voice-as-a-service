"""Audios de WhatsApp: nota de voz entrante -> STT, respuesta -> TTS -> nota de voz.

Las conversiones van con PyAV (ya lo trae livekit-agents): su wheel trae FFmpeg con
libopus y el contenedor ogg, asi que no hace falta ffmpeg del sistema.
- Entrada: cualquier audio de WhatsApp (OGG/Opus de las notas de voz, AAC, AMR, mp3)
  pasa a WAV mono de 16 kHz antes del STT; de paso mide la duracion exacta.
- Salida: el WAV del TTS pasa a OGG/Opus mono, lo unico que Meta acepta como nota de voz.

Prototipo (scratch/wa_audio, con un seno, no voz): WAV de 20 s a 24 kHz -> OGG/Opus de
108 KB en 60-80 ms; OGG/Opus de 20 s -> WAV de 16 kHz en 33 ms.

Los errores (AudioError) no llevan texto del cliente ni de la respuesta.
"""
from __future__ import annotations

import asyncio
import io
import logging
import time
import wave

import httpx

from ..config import settings
from ..services import voices

logger = logging.getLogger(__name__)

STT_RATE = 16000
OPUS_RATES = (8000, 12000, 16000, 24000, 48000)
# Meta muestra la nota de voz con play hasta 512 KB; con mas, con icono de descarga.
VOICE_NOTE_PLAY_BYTES = 512 * 1024
STT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
TTS_TIMEOUT = httpx.Timeout(60.0, connect=5.0)
# Tope del pedido entero, espera del slot incluida (el timeout de httpx es por lectura):
# un TTS colgado (CAP-002: el talker se cae y no vuelve solo) no retiene el turno mas que esto.
# Guardas, sin medir.
STT_DEADLINE = 45.0
TTS_DEADLINE = 90.0


class AudioError(Exception):
    """Fallo del STT, del TTS o de una conversion."""


class AudioTooLong(AudioError):
    def __init__(self, seconds: float, max_seconds: float):
        super().__init__(f"audio de {seconds:.1f} s, tope {max_seconds:.0f} s")
        self.seconds = seconds


# Guarda de pedidos simultaneos desde WhatsApp, WA_AUDIO_CONCURRENCY para cada servicio, para
# que una rafaga no acapare la 5060 Ti del TTS. Un semaforo por servicio: un TTS lento no frena
# la transcripcion (Parakeet, ~60 ms en la 3090). Uno por loop: los tests abren uno por test.
_slots: tuple[asyncio.AbstractEventLoop, dict[str, asyncio.Semaphore]] | None = None


def _slot(service: str) -> asyncio.Semaphore:
    global _slots
    loop = asyncio.get_running_loop()
    if _slots is None or _slots[0] is not loop:
        _slots = (loop, {})
    return _slots[1].setdefault(service, asyncio.Semaphore(max(1, settings.wa_audio_concurrency)))


def _pcm_s16(frame) -> bytes:
    """Bytes de un frame s16 mono (el plano puede traer relleno al final)."""
    return bytes(frame.planes[0])[:frame.samples * 2]


def decode_16k(data: bytes, max_seconds: float) -> tuple[bytes, float]:
    """WAV mono de 16 kHz s16 y su duracion. Sincronico (va en to_thread). AudioTooLong
    si la cabecera dice que pasa max_seconds (sin decodificar) o si lo pasa al decodificar."""
    import av

    limit = int(max_seconds * STT_RATE)
    pcm = bytearray()
    try:
        with av.open(io.BytesIO(data)) as src:
            if not src.streams.audio:
                raise AudioError("el archivo no tiene audio")
            if src.duration and src.duration / av.time_base > max_seconds:
                raise AudioTooLong(src.duration / av.time_base, max_seconds)
            resampler = av.AudioResampler(format="s16", layout="mono", rate=STT_RATE)
            for frame in src.decode(audio=0):
                for f in resampler.resample(frame):
                    pcm += _pcm_s16(f)
                if len(pcm) > 2 * limit:
                    raise AudioTooLong(len(pcm) / 2 / STT_RATE, max_seconds)
            for f in resampler.resample(None):
                pcm += _pcm_s16(f)
    except AudioError:
        raise
    except Exception as e:      # av.error.FFmpegError y afines: audio corrupto o formato raro
        raise AudioError(f"no se pudo decodificar el audio: {type(e).__name__}") from None
    seconds = len(pcm) / 2 / STT_RATE
    if seconds > max_seconds:
        raise AudioTooLong(seconds, max_seconds)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(STT_RATE)
        w.writeframes(bytes(pcm))
    return out.getvalue(), seconds


async def transcribe(data: bytes, mime: str) -> str:
    """Texto de un audio entrante (vacio si no se entendio nada). AudioTooLong si pasa
    WA_AUDIO_MAX_SECONDS; AudioError si no se puede decodificar o el STT falla."""
    started = time.perf_counter()
    wav, seconds = await asyncio.to_thread(decode_16k, data, settings.wa_audio_max_seconds)
    decode_ms = round((time.perf_counter() - started) * 1000)
    if seconds < 0.1:
        return ""
    started = time.perf_counter()
    try:
        async with asyncio.timeout(STT_DEADLINE), _slot("stt"), httpx.AsyncClient(timeout=STT_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.vllm_stt_base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.vllm_api_key}"},
                files={"file": ("audio.wav", wav, "audio/wav")},
                data={"model": settings.vllm_stt_model, "language": "es", "response_format": "json"},
            )
    except (httpx.HTTPError, TimeoutError) as e:
        raise AudioError(f"STT no responde: {type(e).__name__}") from None
    if resp.status_code != 200:
        raise AudioError(f"STT respondio {resp.status_code}")
    try:
        text = resp.json().get("text") or ""
    except (ValueError, AttributeError):
        raise AudioError("STT: respuesta no interpretable") from None
    logger.info("wa: stt mime=%s bytes=%d seconds=%.1f decode_ms=%d stt_ms=%d", mime.split(";")[0],
                len(data), seconds, decode_ms, round((time.perf_counter() - started) * 1000))
    return text.strip() if isinstance(text, str) else ""


def pick_voice(agent_voice: str | None) -> str:
    """La voz del agente si esta en el catalogo; si no, VLLM_TTS_VOICE. Nunca vacia ni
    "default": esos pedidos matan el engine de vllm-tts (AGENTS.md)."""
    voice = (agent_voice or "").strip().lower()
    if voice and voice != "default" and voice in voices.catalog():
        return voice
    voice = (settings.vllm_tts_voice or "").strip().lower()
    if voice in ("", "default"):
        raise AudioError("sin voz para el TTS (VLLM_TTS_VOICE vacia)")
    return voice


def wav_to_ogg_opus(wav: bytes, bitrate: int = 32000) -> bytes:
    """OGG/Opus mono, a la tasa del WAV si Opus la acepta (8/12/16/24/48 kHz), si no a 48 kHz.
    Sincronico (va en to_thread)."""
    import av

    out = io.BytesIO()
    try:
        with av.open(io.BytesIO(wav)) as src, av.open(out, "w", format="ogg") as dst:
            if not src.streams.audio:
                raise AudioError("el WAV del TTS no tiene audio")
            rate = src.streams.audio[0].rate
            rate = rate if rate in OPUS_RATES else 48000
            stream = dst.add_stream("libopus", rate=rate, layout="mono")
            stream.bit_rate = bitrate
            resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
            for frame in src.decode(audio=0):
                for f in resampler.resample(frame):
                    for packet in stream.encode(f):
                        dst.mux(packet)
            for f in resampler.resample(None):
                for packet in stream.encode(f):
                    dst.mux(packet)
            for packet in stream.encode(None):
                dst.mux(packet)
    except AudioError:
        raise
    except Exception as e:
        raise AudioError(f"no se pudo convertir a OGG/Opus: {type(e).__name__}") from None
    ogg = out.getvalue()
    if not ogg.startswith(b"OggS"):
        raise AudioError("la conversion a OGG/Opus salio vacia")
    return ogg


async def synthesize_ogg(text: str, voice: str) -> bytes:
    """Nota de voz (OGG/Opus mono) de la respuesta. AudioError si el TTS o la conversion fallan."""
    if voice.strip().lower() in ("", "default"):
        raise AudioError("voz vacia o 'default'")
    body = {"model": settings.vllm_tts_model, "voice": voice, "input": text, "response_format": "wav"}
    started = time.perf_counter()
    try:
        async with asyncio.timeout(TTS_DEADLINE), _slot("tts"), httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
            resp = await client.post(f"{settings.vllm_tts_base_url}/audio/speech", json=body,
                                     headers={"Authorization": f"Bearer {settings.vllm_api_key}"})
    except (httpx.HTTPError, TimeoutError) as e:
        raise AudioError(f"TTS no responde: {type(e).__name__}") from None
    tts_ms = round((time.perf_counter() - started) * 1000)
    if resp.status_code != 200:
        raise AudioError(f"TTS respondio {resp.status_code}")
    if not resp.content:
        raise AudioError("TTS: audio vacio")
    started = time.perf_counter()
    ogg = await asyncio.to_thread(wav_to_ogg_opus, resp.content)
    logger.info("wa: tts voice=%s chars=%d wav_bytes=%d ogg_bytes=%d tts_ms=%d conv_ms=%d", voice, len(text),
                len(resp.content), len(ogg), tts_ms, round((time.perf_counter() - started) * 1000))
    if len(ogg) > VOICE_NOTE_PLAY_BYTES:
        logger.warning("wa: nota de voz de %d bytes (> 512 KB): WhatsApp la muestra para descargar", len(ogg))
    return ogg
