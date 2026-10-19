"""Apertura pregenerada (conversation.opening_audio): se sintetiza al guardar el agente y el worker la reproduce."""
import asyncio
import json

import httpx
import pytest

from app.config import settings
from app.conversation import opening_audio
from app.conversation.models import Workflow
from app.services import tts

from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)

PCM = b"\x01\x00" * 4800     # 0,2 s a 24 kHz


@pytest.fixture
def tts_engine(monkeypatch, tmp_path):
    """vllm-tts simulado (PCM crudo) y el directorio de aperturas en tmp."""
    monkeypatch.setattr(settings, "opening_audio_dir", tmp_path)
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, content=PCM)

    real = httpx.AsyncClient
    monkeypatch.setattr(opening_audio.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    return seen


def workflow(opening="Hola, soy Sofía. ¿En qué te puedo ayudar?", flag=True, version=3, voice="sofia") -> Workflow:
    return Workflow.model_validate({
        "id": "ventas", "version": version, "engine": "assistant",
        "agent": {"name": "Sofía", "role": "ventas", "language": "es", "voice": voice},
        "objective": {"description": "x"},
        "conversation": {"opening": opening, "opening_audio": flag},
        "completion": {"outcomes": [{"id": "fin", "label": "Fin", "message": "Chau"}]},
    })


def test_defaults():
    w = workflow(flag=False)
    assert w.conversation.opening_delay_ms == 200 and not opening_audio.wanted(w)


def test_generate_and_load(tts_engine, tmp_path):
    w = workflow()
    path = asyncio.run(opening_audio.generate("a1", w))
    assert path == tmp_path / "a1" / "3-sofia.wav"
    assert path.read_bytes() == tts.wav_from_pcm(PCM)
    assert tts_engine[0]["input"] == w.conversation.opening and tts_engine[0]["voice"] == "sofia"
    assert tts_engine[0]["response_format"] == "pcm"
    assert opening_audio.load_pcm("a1", w, "sofia", w.conversation.opening) == PCM
    # Otra voz, otro texto (variables de campaña) u otra version: en vivo.
    assert opening_audio.load_pcm("a1", w, "martin", w.conversation.opening) is None
    assert opening_audio.load_pcm("a1", w, "sofia", "Hola Juan") is None
    assert opening_audio.load_pcm("a1", workflow(version=4), "sofia", w.conversation.opening) is None
    # Ya generada: no vuelve a pedirla.
    asyncio.run(opening_audio.generate("a1", w))
    assert len(tts_engine) == 1


def test_skips_variables_and_flag_off(tts_engine):
    assert asyncio.run(opening_audio.generate("a1", workflow(opening="Hola {{nombre}}"))) is None
    assert asyncio.run(opening_audio.generate("a1", workflow(flag=False))) is None
    assert tts_engine == []


def test_tts_failure_does_not_raise(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "opening_audio_dir", tmp_path)
    real = httpx.AsyncClient
    monkeypatch.setattr(opening_audio.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(lambda r: httpx.Response(500)), **kw))
    assert asyncio.run(opening_audio.generate("a1", workflow())) is None
    assert not list(tmp_path.rglob("*.wav"))


def test_generated_on_save_and_deleted_with_agent(api, admin, tts_engine, tmp_path):
    agent = make_agent(admin, make_client(admin), template="demo_booking")
    assert tts_engine == []      # sin la bandera no se genera
    definition = agent["definition"]
    definition["conversation"] |= {"opening_audio": True, "opening_delay_ms": 500}
    v2 = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition}).json()
    assert v2["definition"]["conversation"]["opening_delay_ms"] == 500
    assert (tmp_path / agent["id"] / f"2-{agent['voice']}.wav").exists()
    assert admin.delete(f"{V1}/agents/{agent['id']}").status_code == 204
    assert not (tmp_path / agent["id"]).exists()
