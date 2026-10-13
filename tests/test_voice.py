import wave

import numpy as np
from livekit import rtc

from app.agents.templates import (
    load_reference,
    reference_ids,
    template_data,
    template_ids,
)
from app.config import settings
from app.services import voices
from app.voice import worker as livekit_agent


async def resolve(monkeypatch, served):
    async def fake():
        return served
    monkeypatch.setattr(livekit_agent, "served_voices", fake)
    monkeypatch.setattr(settings, "vllm_tts_voice", "arf_03034")
    return await livekit_agent.resolve_voice(load_reference("berlin_signup"))


async def test_uses_workflow_voice_when_served(monkeypatch):
    assert await resolve(monkeypatch, {"sofia", "martin"}) == "sofia"


async def test_falls_back_when_voice_not_served(monkeypatch):
    # Checkpoint viejo (multi4): sofia no existe, se usa VLLM_TTS_VOICE en vez de dar 400.
    assert await resolve(monkeypatch, {"arf_03034", "arm_08784"}) == "arf_03034"


async def test_uses_workflow_voice_when_tts_unreachable(monkeypatch):
    assert await resolve(monkeypatch, None) == "sofia"


async def test_call_voice_overrides_workflow(monkeypatch):
    async def fake():
        return {"sofia", "martin"}
    monkeypatch.setattr(livekit_agent, "served_voices", fake)
    assert await livekit_agent.resolve_voice(load_reference("berlin_signup"), "martin") == "martin"


def test_catalog_has_41_voices_with_metrics():
    cat = voices.catalog()
    assert len(cat) == 41
    assert all(v.genero in ("mujer", "hombre") and v.wer is not None and v.car_s is not None for v in cat.values())
    # Cada voz de un workflow tiene que estar en el catalogo (y en el checkpoint servido).
    assert all(load_reference(t).agent.voice in cat for t in reference_ids())
    assert all(template_data(t)["agent"]["voice"] in cat for t in template_ids())


def test_search_filters_and_sorts():
    found = voices.search(genero="hombre", wer_max=3, car_min=15, car_max=18)
    assert found and all(v["genero"] == "hombre" and v["wer"] <= 3 and 15 <= v["car_s"] <= 18 for v in found)
    assert [v["wer"] for v in found] == sorted(v["wer"] for v in found)
    assert voices.search(wer_max=0) == []


# --- Grabacion por turno (agent.record_audio) ---

def _frame(samples: list[int], rate: int = livekit_agent.RECORDING_SAMPLE_RATE) -> rtc.AudioFrame:
    data = np.array(samples, dtype=np.int16)
    return rtc.AudioFrame(data=data.tobytes(), sample_rate=rate, num_channels=1, samples_per_channel=len(samples))


def _recorder(record_dir) -> livekit_agent.WorkflowAgent:
    return livekit_agent.WorkflowAgent(
        engine=None, conversation_id="c1", latency=None, on_completed=lambda: None, record_dir=record_dir)


def _buffer_customer(agent: livekit_agent.WorkflowAgent, samples: list[int]) -> None:
    for f in agent._rec_customer_resampler.push(_frame(samples)):
        agent._rec_customer.extend(f.data)


def _read_wav(path) -> tuple[int, int, list[int]]:
    with wave.open(str(path)) as w:
        return w.getframerate(), w.getnchannels(), np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).tolist()


def test_commit_turn_concatenates_customer_then_agent(tmp_path):
    agent = _recorder(tmp_path)
    agent._commit_turn(_frame([100, 200, 300]).data, _frame([10, 20]).data)
    rate, channels, pcm = _read_wav(tmp_path / "001.wav")
    assert (rate, channels, pcm) == (livekit_agent.RECORDING_SAMPLE_RATE, 1, [100, 200, 300, 10, 20])


def test_commit_turn_skips_when_both_empty(tmp_path):
    agent = _recorder(tmp_path)
    agent._commit_turn(b"", b"")
    assert agent._rec_seq == 0
    assert not list(tmp_path.iterdir())


def test_sequence_numbers_increment_per_turn(tmp_path):
    agent = _recorder(tmp_path)
    agent._commit_turn(b"", _frame([1]).data)
    agent._commit_turn(b"", _frame([2]).data)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["001.wav", "002.wav"]


class _FakeSpeech:
    def __init__(self, id: str, interrupted: bool) -> None:
        self.id = id
        self.interrupted = interrupted

    def done(self) -> bool:
        return True

    async def wait_for_playout(self) -> None:
        return None


class _FakeEngine:
    def __init__(self, retracts: bool) -> None:
        self.retracts = retracts
        self.calls = 0

    def retract_last_turn(self, conversation_id: str) -> bool:
        self.calls += 1
        return self.retracts


async def test_settle_last_reply_commits_pending_turn_when_not_interrupted(tmp_path):
    agent = _recorder(tmp_path)
    agent.engine = _FakeEngine(retracts=False)
    agent._rec_pending = (_frame([1]).data, _frame([2]).data)
    agent.last_reply = _FakeSpeech("s1", interrupted=False)
    await agent.settle_last_reply()
    assert agent._rec_pending is None
    assert (tmp_path / "001.wav").exists()


async def test_settle_last_reply_commits_pending_turn_when_confirmed_despite_interruption(tmp_path):
    agent = _recorder(tmp_path)
    agent.engine = _FakeEngine(retracts=False)
    agent.played["s1"] = livekit_agent.CONTINUATION_WINDOW
    agent._rec_pending = (_frame([1]).data, _frame([2]).data)
    agent.last_reply = _FakeSpeech("s1", interrupted=True)
    await agent.settle_last_reply()
    assert agent._rec_pending is None
    assert (tmp_path / "001.wav").exists()


async def test_settle_last_reply_merges_customer_audio_on_retraction(tmp_path):
    """El audio del turno retractado no se pierde ni queda en un WAV aparte: vuelve
    al principio del buffer del cliente para fusionarse con la continuacion."""
    agent = _recorder(tmp_path)
    agent.engine = _FakeEngine(retracts=True)
    agent.played["s1"] = 0.0
    agent._rec_pending = (_frame([1, 2]).data, _frame([99]).data)  # cliente, respuesta descartada
    agent.last_reply = _FakeSpeech("s1", interrupted=True)
    agent.last_user_ids = {"u1"}
    agent.consumed = {"u1"}
    _buffer_customer(agent, [3])  # lo que siguio diciendo mientras se decidia
    await agent.settle_last_reply()
    assert agent._rec_pending is None
    assert not list(tmp_path.iterdir())  # nada confirmado todavia, la respuesta se descarto
    assert np.frombuffer(bytes(agent._rec_customer), dtype=np.int16).tolist() == [1, 2, 3]
    assert agent.consumed == set()


def test_flush_recording_writes_trailing_customer_audio(tmp_path):
    """Al cortar sin otra respuesta del agente, lo que dijo el cliente no se pierde."""
    agent = _recorder(tmp_path)
    _buffer_customer(agent, [42])
    agent.flush_recording()
    assert (tmp_path / "001.wav").exists()


def test_flush_recording_noop_without_pending_audio(tmp_path):
    agent = _recorder(tmp_path)
    agent.flush_recording()
    assert not list(tmp_path.iterdir())


def test_disabled_recording_flush_is_noop(tmp_path):
    agent = livekit_agent.WorkflowAgent(
        engine=None, conversation_id="c1", latency=None, on_completed=lambda: None, record_dir=None)
    agent.flush_recording()
    assert not list(tmp_path.iterdir())


def test_mono_resampler_downmixes_and_resamples():
    resampler = livekit_agent._MonoResampler()
    stereo = rtc.AudioFrame(
        data=np.array([100, 200, 300, 400], dtype=np.int16).tobytes(),
        sample_rate=livekit_agent.RECORDING_SAMPLE_RATE, num_channels=2, samples_per_channel=2)
    [mono] = resampler.push(stereo)
    assert mono.num_channels == 1
    assert np.frombuffer(mono.data, dtype=np.int16).tolist() == [150, 350]

    other_rate = resampler.push(_frame([1, 2, 3], rate=8000))
    assert all(f.sample_rate == livekit_agent.RECORDING_SAMPLE_RATE for f in other_rate)
