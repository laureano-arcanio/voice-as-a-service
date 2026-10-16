"""Grabaciones por mensaje (`record_audio` en la definicion del agente): un WAV mono de 16 kHz
por mensaje en `CALL_RECORDINGS_DIR/<conversation_id>/NNN.wav`, con su numero en
`Message.recording`.

Lo usan los dos caminos de audio:
- el agente de voz (`app/voice/worker.py`: un WAV por lado del turno, recortado por el VAD);
- WhatsApp (`app/whatsapp/service.py`: el audio entrante que se transcribe y la nota de voz
  que se manda).

El numero es la secuencia dentro de la conversacion. El worker de voz la lleva en memoria;
WhatsApp la sigue desde los archivos que ya hay en el directorio.

`storage/` no se versiona ni entra en el backup (AGENTS.md). El mismo directorio se sirve en
`GET /api/v1/calls/{id}/recordings/{n}` y se borra con la conversacion (`services/calls.py`).
"""
from __future__ import annotations

import wave
from pathlib import Path

from ..config import settings

RECORDING_SAMPLE_RATE = 16000


def recording_dir(conversation_id: str) -> Path:
    return settings.call_recordings_dir / conversation_id


def write_wav(path: Path, pcm: bytes) -> None:
    """Escribe el PCM (s16, mono, `RECORDING_SAMPLE_RATE`) como un WAV. Sincronico."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RECORDING_SAMPLE_RATE)
        w.writeframes(pcm)


def next_sequence(directory: Path) -> int:
    """Siguiente numero libre (001.wav, 002.wav...); 1 si no hay ninguno."""
    nums = [int(p.stem) for p in directory.glob("*.wav") if p.stem.isdigit()]
    return max(nums, default=0) + 1


def append_recording(conversation_id: str, pcm: bytes) -> int | None:
    """Un WAV con ese audio como el proximo de la conversacion; su numero, o None si esta vacio."""
    if not pcm:
        return None
    directory = recording_dir(conversation_id)
    seq = next_sequence(directory)
    write_wav(directory / f"{seq:03d}.wav", pcm)
    return seq
