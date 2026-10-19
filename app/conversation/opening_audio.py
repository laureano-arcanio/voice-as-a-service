"""Apertura pregenerada (`conversation.opening_audio` en la definicion del agente).

En la llamada, el TTS de LiveKit parte el texto en frases y sintetiza cada una por separado: la
entonacion de cada frase no ve las otras. Con la bandera, al guardar el agente la app sintetiza
la apertura entera en un solo pedido y el worker de voz reproduce ese audio al atender.

- Un WAV (PCM 16 bits, mono, 24 kHz: lo que entrega Qwen3-TTS) por version y voz, en
  `OPENING_AUDIO_DIR/<agent_id>/<version>-<voz>.wav`. Cada guardado es una version nueva, asi
  que se regenera al guardar y una llamada en curso sigue con el de su version.
- Lo genera `app` al crear o guardar el agente (en segundo plano, despues de responder) y lo
  lee `agent`: `storage/` esta montado en los dos.
- Si no esta (fallo el TTS, todavia se genera, la llamada eligio otra voz, la apertura tiene
  `{{variables}}` de una campaña), la apertura se sintetiza en vivo como siempre.
- Al cambiar el checkpoint del TTS los WAV quedan con la voz vieja: borrar el directorio (o
  volver a guardar los agentes).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import httpx

from ..config import settings
from ..services.tts import SAMPLE_RATE, wav_from_pcm
from .models import Workflow

logger = logging.getLogger(__name__)

TTS_TIMEOUT = httpx.Timeout(60, connect=5)
WAV_HEADER_BYTES = 44


def voice_for(workflow: Workflow) -> str:
    """La voz con que se pregenera: la del agente o la del servidor (resolve_voice en el worker)."""
    return workflow.agent.voice or settings.vllm_tts_voice


def path_for(agent_id: str, version: int, voice: str) -> Path:
    return settings.opening_audio_dir / agent_id / f"{version}-{voice}.wav"


def wanted(workflow: Workflow) -> bool:
    """La bandera y una apertura fija: con `{{variables}}` el texto cambia por contacto."""
    text = workflow.conversation.opening.strip()
    return workflow.conversation.opening_audio and bool(text) and "{{" not in text


async def generate(agent_id: str, workflow: Workflow) -> Path | None:
    """Sintetiza la apertura de esa version. No levanta: si falla, la llamada usa el TTS en vivo."""
    if not wanted(workflow):
        return None
    voice = voice_for(workflow)
    if not voice or voice == "default":     # mataria el engine de vllm-tts (AGENTS.md)
        return None
    path = path_for(agent_id, workflow.version, voice)
    if path.exists():
        return path
    body = {"model": settings.vllm_tts_model, "voice": voice,
            "input": workflow.conversation.opening.strip(), "response_format": "pcm"}
    try:
        async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
            r = await client.post(f"{settings.vllm_tts_base_url}/audio/speech", json=body,
                                  headers={"Authorization": f"Bearer {settings.vllm_api_key}"})
        r.raise_for_status()
        if not r.content:
            raise ValueError("audio vacio")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(wav_from_pcm(r.content))
        tmp.replace(path)       # el worker nunca ve un WAV a medio escribir
    except Exception:
        logger.exception("apertura pregenerada de %s v%s (voz %s): fallo, se usa el TTS en vivo",
                         agent_id, workflow.version, voice)
        return None
    logger.info("apertura pregenerada %s (%.1f s)", path, len(r.content) / (2 * SAMPLE_RATE))
    return path


def load_pcm(agent_id: str, workflow: Workflow, voice: str, text: str) -> bytes | None:
    """PCM (24 kHz, mono) de la apertura pregenerada, si esta y corresponde a lo que va a sonar."""
    if not wanted(workflow) or text != workflow.conversation.opening:
        return None
    path = path_for(agent_id, workflow.version, voice)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    return data[WAV_HEADER_BYTES:] or None


def delete(agent_id: str) -> None:
    shutil.rmtree(settings.opening_audio_dir / agent_id, ignore_errors=True)
