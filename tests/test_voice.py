import asyncio
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
from app.conversation.models import AgentTurn, Message, TurnAttention
from app.services import voices
from app.voice import worker as livekit_agent
from app.voice.attention import AttentionWatchdog


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


# --- Repetición de la última respuesta (repeat_last_reply) ---

class _StreamEngine:
    """Motor falso para llm_node: process_turn devuelve el turno tal cual y, con `stream`, emite texto por
    on_message como haría el stream del LLM."""

    def __init__(self, turn: AgentTurn, stream: str = ""):
        self.turn, self.stream = turn, stream
        self.store = SimpleNamespace(get=lambda cid: None, save=lambda st: None)

    async def process_turn(self, conversation_id, message, on_message=None, dtmf=None):
        for i in range(0, len(self.stream), 7):
            on_message(self.stream[i:i + 7])
        return SimpleNamespace(messages=[]), self.turn


_CHAT_CTX = SimpleNamespace(items=[])


def _agent(engine) -> livekit_agent.WorkflowAgent:
    return livekit_agent.WorkflowAgent(engine=engine, conversation_id="c1",
                                       latency=livekit_agent.TurnLatencyTracker(),
                                       on_completed=lambda reason: None)


async def test_llm_node_pushes_the_repeated_reply_to_the_tts():
    """El LLM no escribió texto (solo llamó a repeat_last_reply): la última respuesta, que el motor puso en
    assistant_message, suena por el mismo camino del stream. Es un turno real: el watchdog armará la ventana
    con el done-callback de siempre."""
    agent = _agent(_StreamEngine(AgentTurn(assistant_message="¿A qué hora quiere la demo?", repeat=True)))
    assert [t async for t in agent.llm_node(_CHAT_CTX, None, None)] == ["¿A qué hora quiere la demo?"]


async def test_llm_node_does_not_add_anything_if_the_model_spoke():
    """Texto además de la herramienta: suena lo del stream y no se agrega la repetición (no se duplica)."""
    engine = _StreamEngine(AgentTurn(assistant_message="Te repito: ¿a qué hora?", repeat=True),
                           stream="Te repito.")
    agent = _agent(engine)
    assert [t async for t in agent.llm_node(_CHAT_CTX, None, None)] == ["Te repi", "to."]


async def test_llm_node_says_nothing_if_there_is_nothing_to_repeat():
    agent = _agent(_StreamEngine(AgentTurn(assistant_message="", repeat=True)))
    assert [t async for t in agent.llm_node(_CHAT_CTX, None, None)] == []


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


# --- Atención del turno (turn_attention, app/voice/attention.py) ---------------------------------


class _SayHandle:
    """Handle de say del watchdog: resuelve ya, o espera la gate del recorder para sostener
    un aviso en vuelo (los tests de re-arme y de voz durante el aviso)."""

    def __init__(self, gate: asyncio.Future | None):
        self.gate = gate

    async def wait_for_playout(self):
        if self.gate is not None:
            await self.gate


class _Recorder:
    """say/end/transfer del watchdog: lo que dijo y qué cortó o derivó."""

    def __init__(self):
        self.said: list[tuple[str, bool]] = []    # (texto, allow_interruptions)
        self.ends: list[str] = []
        self.transfers: list[str] = []
        self.gate: asyncio.Future | None = None

    def say(self, text: str, *, allow_interruptions: bool):
        self.said.append((text, allow_interruptions))
        return _SayHandle(self.gate)

    async def end(self):
        self.ends.append("no_response")

    async def transfer(self, area_id: str):
        self.transfers.append(area_id)


class _StepSleep:
    """Sleep del watchdog a paso del test: cada espera queda pendiente hasta pop(), que salta
    las canceladas por un arm/reset/disarm."""

    def __init__(self):
        self.pending: list[tuple[float, asyncio.Future]] = []

    async def __call__(self, seconds: float):
        fut = asyncio.get_running_loop().create_future()
        self.pending.append((seconds, fut))
        await fut

    def pop(self) -> float:
        while self.pending:
            seconds, fut = self.pending.pop(0)
            if not fut.done():
                fut.set_result(None)
                return seconds
        raise AssertionError("sin esperas pendientes")

    def expect(self, seconds: float) -> None:
        self.pending = [x for x in self.pending if not x[1].done()]   # muertas por un reset/arm
        assert self.pending and self.pending[0][0] == seconds, self.pending
        self.pop()

    def alive(self) -> list[float]:
        return [s for s, f in self.pending if not f.done()]


async def _tick():
    """Un paso de loop: el watchdog corre hasta su próxima espera."""
    await asyncio.sleep(0)


def _attention(rec: _Recorder, *, cfg: TurnAttention | None = None, sleep=None, busy=None,
               question=None, second=None) -> AttentionWatchdog:
    return AttentionWatchdog(cfg or TurnAttention(enabled=True), rec.say, rec.end, rec.transfer,
                             busy or (lambda: False), sleep=sleep or _StepSleep(),
                             question=question, second=second)


def _texts(rec: _Recorder) -> list[str]:
    return [text for text, _ in rec.said]


async def test_attention_reminder_sequence_7_14_30_ends_with_no_response():
    """Con 7/2/7/30: primer aviso a los 7 s, segundo a los 14, cierre a los 30 y hang_up."""
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    assert rec.said == [(settings.voice_no_response_reminder, True)]
    sleep.expect(7.0)        # 7 + 7
    await _tick()
    assert rec.said[1] == (settings.voice_no_response_second, True)
    sleep.expect(16.0)       # 30 - 14
    await _tick()
    assert rec.said[2] == (settings.voice_no_response_end, False)
    assert rec.ends == ["no_response"] and rec.transfers == []
    assert sleep.alive() == []


async def test_attention_first_reminder_repeats_the_last_question():
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, sleep=sleep, question=lambda: " ¿En qué te puedo ayudar? ")
    wd.arm()
    await _tick()
    sleep.pop()
    await _tick()
    assert rec.said[0] == (f"{settings.voice_no_response_reminder} ¿En qué te puedo ayudar?", True)
    wd.close()
    await _tick()


async def test_attention_agent_texts_win_over_the_platform_ones():
    cfg = TurnAttention(enabled=True, reminder_text="¿Seguís ahí?", end_text="Chau, gracias.")
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep, question=lambda: "¿algo?")
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    assert rec.said[0][0] == "¿Seguís ahí?"
    sleep.expect(7.0)
    await _tick()
    assert rec.said[1][0] == settings.voice_no_response_second
    sleep.expect(16.0)
    await _tick()
    assert rec.said[2][0] == "Chau, gracias."


async def test_attention_reset_cancels_the_scheduled_reminder():
    """La persona habla después del primer aviso: lo agendado se cancela y la ventana (con su
    presupuesto de avisos) arranca de nuevo."""
    cfg = TurnAttention(enabled=True, reminder_gap_ms=9000)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()             # primer aviso
    wd.reset()                # voz del usuario
    await _tick()
    assert sleep.alive() == [7.0]                                    # ventana nueva
    assert sleep.pending[0][0] == 9.0 and sleep.pending[0][1].cancelled()  # el gap murió con su tarea
    sleep.pop()
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder] * 2  # de nuevo el primer aviso
    sleep.expect(9.0)         # segundo aviso de la ventana nueva
    await _tick()
    assert rec.said[2][0] == settings.voice_no_response_second
    sleep.expect(14.0)        # cierre a los 30 de la ventana nueva
    await _tick()
    assert rec.ends == ["no_response"]


async def test_attention_voice_before_the_first_reminder_does_not_fire():
    """Voz a los 5 s (antes del aviso de los 7): no dispara nada; la ventana arranca de nuevo."""
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, sleep=sleep)
    wd.arm()
    await _tick()
    wd.reset()                # voz a los 5 s
    await _tick()
    assert rec.said == [] and sleep.alive() == [7.0]
    wd.close()
    await _tick()


async def test_attention_busy_defers_the_reminder_and_keeps_the_end_deadline():
    """Con el turno ocupado al vencer un aviso, espera y dispara al desocuparse; el cierre no
    se corre por la espera (los deadlines son absolutos desde el fin del último mensaje real)."""
    cfg = TurnAttention(enabled=True, reminder_max=1)
    busy = {"on": True}
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep, busy=lambda: busy["on"])
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    sleep.expect(0.25)       # venció con el turno ocupado: difiere sin perder el evento
    busy["on"] = False
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder]
    sleep.expect(22.75)      # 30 - 7.25: el cierre sigue en su deadline
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder, settings.voice_no_response_end]
    assert rec.ends == ["no_response"]


async def test_attention_busy_defers_the_end_too():
    cfg = TurnAttention(enabled=True, reminder_max=0)
    busy = {"on": True}
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep, busy=lambda: busy["on"])
    wd.arm()
    await _tick()
    sleep.expect(30.0)
    await _tick()
    busy["on"] = False
    sleep.expect(0.25)
    await _tick()
    assert rec.said == [(settings.voice_no_response_end, False)]
    assert rec.ends == ["no_response"]


async def test_attention_stt_timeout_consumes_budget_without_resetting_the_window():
    """STT vacío: pide que repita, consume presupuesto y no toca la ventana ni el deadline (una
    línea ruidosa no loopea el pedido ni atrasa el cierre)."""
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, sleep=sleep)
    wd.arm()
    await _tick()
    await wd.on_transcription_timeout()
    assert _texts(rec) == [settings.voice_no_response_stt]
    sleep.expect(7.0)        # la ventana sigue: mismo deadline, ahora con el texto de insistencia
    await _tick()
    assert rec.said[1] == (settings.voice_no_response_second, True)
    sleep.expect(23.0)       # presupuesto agotado: sin más avisos, cierre a los 30
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_stt, settings.voice_no_response_second,
                           settings.voice_no_response_end]
    assert rec.ends == ["no_response"]


async def test_attention_stt_timeout_without_budget_or_disarmed_says_nothing():
    cfg = TurnAttention(enabled=True, reminder_max=0)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    await wd.on_transcription_timeout()
    assert rec.said == []      # sin presupuesto de avisos: ni el pedido de repetición
    wd.disarm()
    await _tick()
    await wd.on_transcription_timeout()
    assert rec.said == []      # sin ventana (turno o derivación en curso): tampoco
    wd.close()
    await _tick()


async def test_attention_without_reminders_closes_at_the_end():
    cfg = TurnAttention(enabled=True, reminder_max=0)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(30.0)
    await _tick()
    assert rec.said == [(settings.voice_no_response_end, False)] and rec.ends == ["no_response"]


async def test_attention_end_transfer_goes_to_the_configured_area():
    cfg = TurnAttention(enabled=True, reminder_max=0, on_end="transfer", on_end_area_id="area-1")
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(30.0)
    await _tick()
    assert rec.said == [(settings.voice_no_response_end, False)]
    assert rec.transfers == ["area-1"] and rec.ends == []


async def test_attention_end_transfer_without_area_id_uses_the_first_one():
    cfg = TurnAttention(enabled=True, reminder_max=0, on_end="transfer")
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(30.0)
    await _tick()
    assert rec.transfers == [""]      # vacía = primera área; resolverla es del worker


async def test_attention_arm_during_own_say_is_ignored():
    """El aviso propio no re-arma la ventana: mientras suena, un arm() no la reinicia (los
    deadlines siguen desde el último mensaje real)."""
    cfg = TurnAttention(enabled=True, reminder_gap_ms=9000)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    rec.gate = asyncio.get_running_loop().create_future()
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()             # el aviso queda en vuelo (gate)
    wd.arm()                  # un gancho que llegue acá no reinicia nada
    await _tick()
    assert sleep.alive() == []
    rec.gate.set_result(None)
    await _tick()
    sleep.expect(9.0)         # sigue el calendario original: segundo aviso a los 16, no a los 7
    await _tick()
    sleep.expect(14.0)
    await _tick()
    assert rec.ends == ["no_response"]


async def test_attention_reset_during_a_reminder_starts_a_new_window():
    """La persona habla justo cuando suena un aviso: el aviso se corta (allow_interruptions) y
    la ventana que sigue es la de su voz, no la del aviso."""
    cfg = TurnAttention(enabled=True, reminder_gap_ms=9000)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    rec.gate = asyncio.get_running_loop().create_future()
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    wd.reset()                # voz durante el aviso
    await _tick()
    assert sleep.alive() == [7.0]      # ventana nueva: el gap de 9 del aviso murió con su tarea
    rec.gate = None                   # la gate murió con la tarea cancelada
    sleep.pop()
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder] * 2
    wd.close()
    await _tick()


async def test_attention_reset_during_the_closing_cancels_the_hang_up():
    """La persona habla durante el aviso de cierre: no se cuelga; la ventana arranca de nuevo."""
    cfg = TurnAttention(enabled=True, reminder_max=0)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    rec.gate = asyncio.get_running_loop().create_future()
    wd.arm()
    await _tick()
    sleep.expect(30.0)
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_end]
    wd.reset()                # habla durante el aviso de cierre
    await _tick()
    assert rec.ends == [] and sleep.alive() == [30.0]   # no colgó: ventana nueva
    wd.close()
    await _tick()
    assert sleep.alive() == []


async def test_attention_disarm_pauses_until_the_next_arm():
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, sleep=sleep)
    wd.arm()
    await _tick()
    wd.disarm()
    await _tick()
    assert sleep.alive() == [] and rec.said == []
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder]
    wd.close()
    await _tick()


async def test_attention_close_stops_the_window():
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, sleep=sleep)
    wd.arm()
    await _tick()
    wd.close()
    await _tick()
    assert sleep.alive() == [] and rec.said == [] and rec.ends == []


async def test_attention_end_fires_even_if_the_say_fails():
    """Sin TTS no hay aviso, pero el corte llega igual (patrón de say_end_and_hang_up) y la
    ventana sigue su curso tras un aviso fallido."""
    rec, sleep = _Recorder(), _StepSleep()

    def boom(text, *, allow_interruptions):
        rec.said.append((text, allow_interruptions))
        raise RuntimeError("tts caído")

    wd = AttentionWatchdog(TurnAttention(enabled=True), boom, rec.end, rec.transfer,
                           lambda: False, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    sleep.expect(7.0)         # el aviso fallido no tumbó la ventana
    await _tick()
    sleep.expect(16.0)
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder, settings.voice_no_response_second,
                           settings.voice_no_response_end]
    assert rec.ends == ["no_response"]


async def test_attention_close_beats_a_late_reminder():
    """end_after_ms puede quedar antes del último aviso posible: a su hora cierra, no sigue
    sumando avisos (plan, 'Qué rompería': end_after antes del último aviso)."""
    cfg = TurnAttention(enabled=True, reminder_max=5, end_after_ms=15000)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()
    sleep.expect(7.0)
    await _tick()
    sleep.expect(1.0)         # el tercer aviso sería a los 21: gana el cierre a los 15
    await _tick()
    assert _texts(rec) == [settings.voice_no_response_reminder, settings.voice_no_response_second,
                           settings.voice_no_response_end]
    assert rec.ends == ["no_response"]


def test_attention_session_params():
    """build_session con turn_attention: el timer away de LiveKit se apaga y, con stt_retry,
    se prende el timeout de transcripción; sin la función, nada cambia."""
    assert livekit_agent.attention_session_params(TurnAttention(enabled=True)) == {
        "user_away_timeout": None, "transcription_timeout": 3.0}
    assert livekit_agent.attention_session_params(TurnAttention(enabled=True, stt_retry=False)) == {
        "user_away_timeout": None}
    assert livekit_agent.attention_session_params(None) == {}
    assert livekit_agent.attention_session_params(TurnAttention(enabled=False)) == {}


async def test_attention_real_turn_rearms_after_an_interrupted_reminder():
    """Regresión del leak de `_speaking` (nunca volvía a 0): un aviso interrumpido por la voz de la
    persona no puede dejar arm/disarm ignorados para siempre. El turno real siguiente desarma (sin
    ventana durante la respuesta: nada vencido suena pegado al final de una respuesta larga) y su
    fin vuelve a armar una ventana nueva, anclada ahí y no a la voz de la persona."""
    cfg = TurnAttention(enabled=True, reminder_gap_ms=9000)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    rec.gate = asyncio.get_running_loop().create_future()
    wd.arm()                       # la apertura terminó de sonar
    await _tick()
    sleep.expect(7.0)
    await _tick()                  # el aviso queda en vuelo (gate)
    assert wd._speaking == 1
    wd.reset()                     # la persona habla durante el aviso: la tarea vieja muere
    await _tick()
    assert wd._speaking == 0       # la cancelación del say devolvió el contador
    rec.gate = None
    wd.disarm()                    # empieza el turno real (llm_node), apenas habla la persona
    await _tick()
    assert sleep.alive() == [] and len(rec.said) == 1   # la ventana de su voz murió sin disparar
    wd.arm()                       # la respuesta terminó de sonar (done-callback del speech)
    await _tick()
    assert sleep.alive() == [7.0]  # ventana nueva desde el FIN de la respuesta
    sleep.pop()
    await _tick()
    assert len(rec.said) == 2 and wd._speaking == 0
    wd.close()
    await _tick()


async def test_attention_real_turn_rearms_after_a_played_out_reminder():
    """Regresión del leak de `_speaking` (avisos reproducidos completos): el turno real siguiente
    desarma y, al terminar la respuesta, re-arma una ventana nueva: el próximo aviso sale a
    `reminder_after_ms` del fin de esa respuesta y el resto de la secuencia es de esa ventana."""
    cfg = TurnAttention(enabled=True, reminder_gap_ms=9000)
    rec, sleep = _Recorder(), _StepSleep()
    wd = _attention(rec, cfg=cfg, sleep=sleep)
    wd.arm()
    await _tick()
    sleep.expect(7.0)
    await _tick()                  # el aviso suena ENTERO
    assert wd._speaking == 0
    wd.reset()                     # la persona habla
    await _tick()                  # ventana anclada a su voz
    wd.disarm()                    # turno real en curso
    await _tick()
    assert sleep.alive() == [] and len(rec.said) == 1
    wd.arm()                       # la respuesta terminó de sonar
    await _tick()
    sleep.expect(7.0)              # primer aviso de la ventana nueva, a los 7 del fin de la respuesta
    await _tick()
    assert len(rec.said) == 2
    sleep.expect(9.0)              # el segundo, al gap de esa ventana
    await _tick()
    sleep.expect(14.0)             # cierre a los 30 del fin de la respuesta
    await _tick()
    assert rec.ends == ["no_response"] and wd._speaking == 0
