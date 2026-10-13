import wave
from types import SimpleNamespace

import numpy as np
from livekit import rtc

from app.agents.templates import (
    load_reference,
    reference_ids,
    template_data,
    template_ids,
)
from app.config import settings
from app.conversation.models import Message
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


# --- Grabacion por mensaje (agent.record_audio) ---

def _frame(samples: list[int], rate: int = livekit_agent.RECORDING_SAMPLE_RATE) -> rtc.AudioFrame:
    data = np.array(samples, dtype=np.int16)
    return rtc.AudioFrame(data=data.tobytes(), sample_rate=rate, num_channels=1, samples_per_channel=len(samples))


class _FakeStore:
    def __init__(self, messages: list[Message]) -> None:
        self.messages = messages
        self.saved = 0

    def get(self, conversation_id: str):
        return SimpleNamespace(messages=self.messages)

    def save(self, state) -> None:
        self.saved += 1


class _FakeEngine:
    def __init__(self, retracts: bool = False, messages: list[Message] | None = None) -> None:
        self.retracts = retracts
        self.store = _FakeStore(messages if messages is not None else [])

    def retract_last_turn(self, conversation_id: str) -> bool:
        return self.retracts


def _recorder(record_dir, messages: list[Message] | None = None) -> livekit_agent.WorkflowAgent:
    return livekit_agent.WorkflowAgent(
        engine=_FakeEngine(messages=messages), conversation_id="c1", latency=None,
        on_completed=lambda: None, record_dir=record_dir)


def _buffer_customer(agent: livekit_agent.WorkflowAgent, samples: list[int], *, speaking: bool = False) -> None:
    """Simula el stream continuo de stt_node: `speaking` es el estado del VAD al llegar."""
    agent._rec_user_speaking = speaking
    for f in agent._rec_customer_resampler.push(_frame(samples)):
        agent._rec_push_customer(f.data)


def _read_wav(path) -> tuple[int, int, list[int]]:
    with wave.open(str(path)) as w:
        return w.getframerate(), w.getnchannels(), np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).tolist()


def test_commit_turn_writes_one_file_per_side_and_tags_messages(tmp_path):
    user_msg, assistant_msg = Message(role="user", text="hola"), Message(role="assistant", text="hola!")
    agent = _recorder(tmp_path, messages=[user_msg, assistant_msg])
    agent._commit_turn(_frame([100, 200, 300]).data, [(0, True)], _frame([10, 20]).data)
    assert _read_wav(tmp_path / "001.wav")[2] == [100, 200, 300]
    assert _read_wav(tmp_path / "002.wav")[2] == [10, 20]
    assert user_msg.recording == 1 and assistant_msg.recording == 2
    assert agent.engine.store.saved == 1


def test_commit_turn_skips_when_both_empty(tmp_path):
    agent = _recorder(tmp_path)
    agent._commit_turn(b"", [], b"")
    assert agent._rec_seq == 0
    assert not list(tmp_path.iterdir())
    assert agent.engine.store.saved == 0  # nada que asociar: no toca la conversacion


def test_commit_turn_skips_silence_without_speech(tmp_path):
    """Sin tramos marcados como habla no hay WAV del cliente, aunque haya frames."""
    history = [Message(role="user", text="..."), Message(role="assistant", text="hola!")]
    agent = _recorder(tmp_path, messages=history)
    silence = _frame([1, 2, 3]).data
    agent._commit_turn(silence, [(0, False)], b"")
    assert not list(tmp_path.iterdir())
    assert history[0].recording is None
    assert agent.engine.store.saved == 0


def test_trim_customer_drops_leading_and_trailing_silence(tmp_path):
    """Del stream continuo queda solo lo hablado (con el pre-roll), no el playout del agente
    ni la espera de la respuesta."""
    preroll = int(livekit_agent.RECORDING_PREROLL_SECONDS * livekit_agent.RECORDING_SAMPLE_RATE)
    habla = [5, 6, 7, 8]
    audio = bytes(_frame([0] * 10000).data) + bytes(_frame(habla).data) + bytes(_frame([0] * 10000).data)
    marks = [(0, False), (10000 * 2, True), ((10000 + len(habla)) * 2, False)]
    esperado = bytes(_frame([0] * preroll + habla).data)
    assert livekit_agent.WorkflowAgent._trim_customer(audio, marks) == esperado


def test_trim_customer_keeps_pauses_between_spans(tmp_path):
    audio = bytes(_frame([1, 0, 2]).data)
    marks = [(0, True), (1 * 2, False), (2 * 2, True)]
    assert livekit_agent.WorkflowAgent._trim_customer(audio, marks) == audio


def test_sequence_numbers_increment_per_turn(tmp_path):
    agent = _recorder(tmp_path)
    agent._commit_turn(b"", [], _frame([1]).data)
    agent._commit_turn(b"", [], _frame([2]).data)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["001.wav", "002.wav"]


def test_tag_recording_updates_last_message_of_each_role(tmp_path):
    """Busca desde el final: el ultimo turno guardado, no uno viejo."""
    history = [Message(role="assistant", text="hola"), Message(role="user", text="hola"),
               Message(role="assistant", text="bien?")]
    agent = _recorder(tmp_path, messages=history)
    agent._tag_recording(user_seq=5, assistant_seq=6)
    assert history[1].recording == 5 and history[2].recording == 6 and history[0].recording is None


def test_user_state_tracks_vad_speaking(tmp_path):
    agent = _recorder(tmp_path)
    agent.on_user_state(SimpleNamespace(new_state="speaking"))
    assert agent._rec_user_speaking is True
    agent.on_user_state(SimpleNamespace(new_state="listening"))
    assert agent._rec_user_speaking is False


class _FakeSpeech:
    def __init__(self, id: str, interrupted: bool) -> None:
        self.id = id
        self.interrupted = interrupted

    def done(self) -> bool:
        return True

    async def wait_for_playout(self) -> None:
        return None


async def test_settle_last_reply_commits_pending_turn_when_not_interrupted(tmp_path):
    agent = _recorder(tmp_path)
    agent._rec_pending = (_frame([1]).data, [(0, True)], _frame([2]).data)
    agent.last_reply = _FakeSpeech("s1", interrupted=False)
    await agent.settle_last_reply()
    assert agent._rec_pending is None
    assert (tmp_path / "001.wav").exists() and (tmp_path / "002.wav").exists()


async def test_settle_last_reply_commits_pending_turn_when_confirmed_despite_interruption(tmp_path):
    agent = _recorder(tmp_path)
    agent.played["s1"] = livekit_agent.CONTINUATION_WINDOW
    agent._rec_pending = (_frame([1]).data, [(0, True)], _frame([2]).data)
    agent.last_reply = _FakeSpeech("s1", interrupted=True)
    await agent.settle_last_reply()
    assert agent._rec_pending is None
    assert (tmp_path / "001.wav").exists() and (tmp_path / "002.wav").exists()


async def test_settle_last_reply_merges_customer_audio_on_retraction(tmp_path):
    """El audio del turno retractado no se pierde ni queda en un WAV aparte: vuelve
    al principio del buffer del cliente (con sus marcas de VAD) para fusionarse con
    la continuacion."""
    agent = _recorder(tmp_path)
    agent.engine = _FakeEngine(retracts=True)
    agent.played["s1"] = 0.0
    agent._rec_pending = (_frame([1, 2]).data, [(0, True)], _frame([99]).data)  # cliente, respuesta descartada
    agent.last_reply = _FakeSpeech("s1", interrupted=True)
    agent.last_user_ids = {"u1"}
    agent.consumed = {"u1"}
    _buffer_customer(agent, [3], speaking=True)  # lo que siguio diciendo mientras se decidia
    await agent.settle_last_reply()
    assert agent._rec_pending is None
    assert not list(tmp_path.iterdir())  # nada confirmado todavia, la respuesta se descarto
    assert np.frombuffer(bytes(agent._rec_customer), dtype=np.int16).tolist() == [1, 2, 3]
    assert agent._rec_marks == [(0, True), (len(_frame([1, 2]).data), True)]  # el tramo retractado vuelve al frente
    assert agent.consumed == set()


def test_flush_recording_writes_trailing_customer_audio(tmp_path):
    """Al cortar sin otra respuesta del agente, lo que dijo el cliente no se pierde."""
    agent = _recorder(tmp_path)
    _buffer_customer(agent, [42], speaking=True)
    agent.flush_recording()
    assert _read_wav(tmp_path / "001.wav")[2] == [42]


def test_flush_recording_trims_silence(tmp_path):
    """El resto tambien se recorta al habla: ni el playout del agente antes ni el silencio
    de despues."""
    agent = _recorder(tmp_path)
    _buffer_customer(agent, [0] * 5000)
    _buffer_customer(agent, [7], speaking=True)
    _buffer_customer(agent, [0] * 5000)
    agent.flush_recording()
    preroll = int(livekit_agent.RECORDING_PREROLL_SECONDS * livekit_agent.RECORDING_SAMPLE_RATE)
    assert _read_wav(tmp_path / "001.wav")[2] == [0] * preroll + [7]


def test_flush_recording_skips_silence_without_speech(tmp_path):
    agent = _recorder(tmp_path)
    _buffer_customer(agent, [1, 2, 3])
    agent.flush_recording()
    assert not list(tmp_path.iterdir())


def test_flush_recording_trailing_audio_is_not_tagged(tmp_path):
    """Ese resto no tiene mensaje (el motor nunca lo proceso): no pisa el tag de un
    mensaje anterior solo porque es el ultimo de su rol."""
    history = [Message(role="user", text="anterior", recording=1), Message(role="assistant", text="respuesta", recording=2)]
    agent = _recorder(tmp_path, messages=history)
    agent._rec_seq = 2
    _buffer_customer(agent, [7], speaking=True)
    agent.flush_recording()
    assert (tmp_path / "003.wav").exists()
    assert history[0].recording == 1 and history[1].recording == 2


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
