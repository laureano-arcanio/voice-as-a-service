"""Audios de WhatsApp: conversiones reales con PyAV (leidas de vuelta con soundfile), STT y
TTS con httpx.MockTransport, y el flujo del service con payloads de Meta
(tests/fixtures/wa/audio*.json), Graph, STT y TTS falsos. Sin red ni contenedores."""
import asyncio
import io
import json
import logging
import math
import struct
import wave

import httpx
import pytest
import soundfile as sf
from sqlalchemy import select

from app.config import settings
from app.conversation.models import TurnMedia
from app.llm.prompt import VOICE_NOTE_TAG
from app.models import WaMessage
from app.whatsapp import audio
from app.whatsapp.audio import AudioError, AudioTooLong
from app.whatsapp.graph import GraphClient, GraphError, MediaTooLarge
from app.whatsapp.service import WhatsAppService

from .helpers import FakeLLM
from .test_whatsapp_service import (
    PNID,
    SEND_TO,
    WA_ID,
    FakeGraph,
    conversations,
    fixture,
    image_payload,
    make_wa,
    messages,
    reply,
    send,
    text_payload,
)


def sine_wav(rate: int = 24000, seconds: float = 3.0, freq: float = 220.0) -> bytes:
    n = int(rate * seconds)
    pcm = struct.pack(f"<{n}h", *(int(9000 * math.sin(2 * math.pi * freq * i / rate)) for i in range(n)))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out.getvalue()


REAL_CLIENT = httpx.AsyncClient


def mock_http(monkeypatch, handler) -> list[httpx.Request]:
    """httpx.AsyncClient de audio.py sobre un MockTransport; devuelve los pedidos."""
    seen = []

    def wrapper(request):
        seen.append(request)
        return handler(request)

    monkeypatch.setattr(audio.httpx, "AsyncClient",
                        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(wrapper), **kw))
    return seen


@pytest.fixture(autouse=True)
def audio_settings(monkeypatch):
    monkeypatch.setattr(settings, "wa_audio_reply", "mirror")
    monkeypatch.setattr(settings, "vllm_tts_voice", "martin")
    monkeypatch.setattr(settings, "vllm_tts_model", "qwen3-tts-ft")
    monkeypatch.setattr(settings, "vllm_tts_base_url", "http://tts.test/v1")
    monkeypatch.setattr(settings, "vllm_stt_base_url", "http://stt.test/v1")
    monkeypatch.setattr(settings, "vllm_stt_model", "nvidia/parakeet-tdt-0.6b-v3")
    monkeypatch.setattr(settings, "vllm_api_key", "clave-vllm")
    monkeypatch.setattr(settings, "wa_audio_voice_flag", True)


# --- Conversiones (PyAV real) ---

@pytest.mark.parametrize("rate,opus_rate", [(24000, 24000), (22050, 48000), (16000, 16000)])
def test_wav_to_ogg_opus_se_lee_de_vuelta(rate, opus_rate):
    ogg = audio.wav_to_ogg_opus(sine_wav(rate, 3.0))
    assert ogg[:4] == b"OggS"
    info = sf.info(io.BytesIO(ogg))
    assert (info.format, info.subtype, info.channels) == ("OGG", "OPUS", 1)
    assert abs(info.duration - 3.0) <= 0.1
    data, _ = sf.read(io.BytesIO(ogg), dtype="float32")
    assert float((data ** 2).mean()) ** 0.5 > 0.05      # no es silencio
    # A 32 kbps, 3 s de audio pesan unos 12 KB (el seno sale a ~43 kbps): lejos de 512 KB.
    assert len(ogg) < 30_000
    import av
    with av.open(io.BytesIO(ogg)) as c:      # Opus en OGG se decodifica siempre a 48 kHz
        assert c.streams.audio[0].codec_context.name == "opus"
    # Tasa de entrada del encoder: la de la cabecera OpusHead (RFC 7845), mono.
    head = ogg.index(b"OpusHead")
    channels, _, input_rate = struct.unpack_from("<BHI", ogg, head + 9)
    assert (channels, input_rate) == (1, opus_rate)


def test_wav_to_ogg_opus_con_basura():
    with pytest.raises(AudioError):
        audio.wav_to_ogg_opus(b"no es un wav")


def test_decode_16k_de_una_nota_de_voz():
    ogg = audio.wav_to_ogg_opus(sine_wav(24000, 3.0))
    wav, seconds = audio.decode_16k(ogg, max_seconds=120)
    assert abs(seconds - 3.0) <= 0.1
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 16000)
        assert abs(w.getnframes() / 16000 - seconds) < 1e-6


def test_decode_16k_tope_y_basura():
    ogg = audio.wav_to_ogg_opus(sine_wav(24000, 3.0))
    with pytest.raises(AudioTooLong) as ei:
        audio.decode_16k(ogg, max_seconds=1)
    assert ei.value.seconds > 1
    with pytest.raises(AudioTooLong):              # un WAV tambien, aunque no sea OGG
        audio.decode_16k(sine_wav(8000, 2.0), max_seconds=1.5)
    with pytest.raises(AudioError) as ei:
        audio.decode_16k(b"\x00" * 500, max_seconds=120)
    assert not isinstance(ei.value, AudioTooLong)


# --- STT y TTS (httpx mockeado) ---

async def test_transcribe_manda_wav_16k_al_stt(monkeypatch):
    seen = mock_http(monkeypatch, lambda r: httpx.Response(200, json={"text": "  quiero un turno  "}))
    ogg = audio.wav_to_ogg_opus(sine_wav(24000, 2.0))
    assert await audio.transcribe(ogg, "audio/ogg; codecs=opus") == "quiero un turno"
    (r,) = seen
    assert str(r.url) == "http://stt.test/v1/audio/transcriptions"
    assert r.headers["authorization"] == "Bearer clave-vllm"
    body = r.content
    assert b'name="model"\r\n\r\nnvidia/parakeet-tdt-0.6b-v3' in body
    assert b'name="language"\r\n\r\nes' in body
    assert b'filename="audio.wav"' in body and b"RIFF" in body


async def test_transcribe_errores(monkeypatch):
    ogg = audio.wav_to_ogg_opus(sine_wav(24000, 1.0))
    mock_http(monkeypatch, lambda r: httpx.Response(503, text="down"))
    with pytest.raises(AudioError):
        await audio.transcribe(ogg, "audio/ogg")

    def boom(request):
        raise httpx.ConnectError("no", request=request)

    mock_http(monkeypatch, boom)
    with pytest.raises(AudioError):
        await audio.transcribe(ogg, "audio/ogg")

    monkeypatch.setattr(settings, "wa_audio_max_seconds", 0.5)
    seen = mock_http(monkeypatch, lambda r: httpx.Response(200, json={"text": "x"}))
    with pytest.raises(AudioTooLong):
        await audio.transcribe(ogg, "audio/ogg")
    assert seen == []                               # no llega al STT


async def test_transcribe_audio_vacio_no_va_al_stt(monkeypatch):
    seen = mock_http(monkeypatch, lambda r: httpx.Response(200, json={"text": "x"}))
    assert await audio.transcribe(audio.wav_to_ogg_opus(sine_wav(24000, 0.05)), "audio/ogg") == ""
    assert seen == []


async def test_synthesize_ogg(monkeypatch):
    seen = mock_http(monkeypatch, lambda r: httpx.Response(200, content=sine_wav(24000, 2.0)))
    ogg = await audio.synthesize_ogg("Tu turno es el lunes a las diez.", "sofia")
    info = sf.info(io.BytesIO(ogg))
    assert (info.subtype, info.channels) == ("OPUS", 1) and abs(info.duration - 2.0) <= 0.1
    (r,) = seen
    assert str(r.url) == "http://tts.test/v1/audio/speech"
    assert r.headers["authorization"] == "Bearer clave-vllm"
    assert json.loads(r.content) == {"model": "qwen3-tts-ft", "voice": "sofia",
                                     "input": "Tu turno es el lunes a las diez.", "response_format": "wav"}


async def test_synthesize_ogg_errores(monkeypatch):
    seen = mock_http(monkeypatch, lambda r: httpx.Response(500, json={"error": "engine dead"}))
    with pytest.raises(AudioError):
        await audio.synthesize_ogg("hola", "sofia")
    mock_http(monkeypatch, lambda r: httpx.Response(200, content=b""))
    with pytest.raises(AudioError):
        await audio.synthesize_ogg("hola", "sofia")
    seen = mock_http(monkeypatch, lambda r: httpx.Response(200, content=sine_wav()))
    for bad in ("", "default", " Default "):        # matan el engine de vllm-tts: ni se piden
        with pytest.raises(AudioError):
            await audio.synthesize_ogg("hola", bad)
    assert seen == []


def test_pick_voice(monkeypatch):
    assert audio.pick_voice("sofia") == "sofia"
    assert audio.pick_voice(" Valentina ") == "valentina"
    assert audio.pick_voice("no_existe") == "martin"       # fuera del catalogo: VLLM_TTS_VOICE
    assert audio.pick_voice(None) == "martin"
    assert audio.pick_voice("default") == "martin"
    monkeypatch.setattr(settings, "vllm_tts_voice", "")
    with pytest.raises(AudioError):
        audio.pick_voice(None)
    monkeypatch.setattr(settings, "vllm_tts_voice", "default")
    with pytest.raises(AudioError):
        audio.pick_voice("no_existe")


async def test_tts_colgado_no_frena_al_stt(monkeypatch):
    """STT y TTS con semaforos separados, y la espera del slot cuenta en el tope del pedido."""
    monkeypatch.setattr(settings, "wa_audio_concurrency", 1)
    monkeypatch.setattr(audio, "TTS_DEADLINE", 0.2)
    hung = asyncio.Event()

    async def handler(request):
        if request.url.host == "tts.test":
            hung.set()
            await asyncio.sleep(5)                  # talker colgado: acepta y no responde
        return httpx.Response(200, json={"text": "hola"})

    monkeypatch.setattr(audio.httpx, "AsyncClient",
                        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw))
    tts = asyncio.create_task(audio.synthesize_ogg("hola", "sofia"))
    await asyncio.wait_for(hung.wait(), 1)
    ogg = audio.wav_to_ogg_opus(sine_wav(24000, 1.0))
    assert await asyncio.wait_for(audio.transcribe(ogg, "audio/ogg"), 1) == "hola"
    with pytest.raises(AudioError):                 # el segundo TTS espera el slot: mismo tope
        await asyncio.wait_for(audio.synthesize_ogg("chau", "sofia"), 1)
    with pytest.raises(AudioError):
        await tts


# --- Flujo del service ---

class FakeAudio:
    """transcribe devuelve los textos en orden (una excepcion se levanta); gate: espera antes
    de devolver. synthesize_ogg devuelve un OGG falso, o levanta tts_fail."""

    def __init__(self, *texts):
        self.texts = list(texts)
        self.heard: list[tuple[bytes, str]] = []
        self.spoken: list[tuple[str, str]] = []
        self.tts_fail: Exception | None = None
        self.gate: asyncio.Event | None = None
        self.started = asyncio.Event()

    async def transcribe(self, data, mime):
        self.heard.append((data, mime))
        self.started.set()
        if self.gate:
            await self.gate.wait()
        text = self.texts.pop(0)
        if isinstance(text, Exception):
            raise text
        return text

    async def synthesize_ogg(self, text, voice):
        if self.tts_fail:
            raise self.tts_fail
        self.spoken.append((text, voice))
        return b"OggS-respuesta"


class MediaLLM(FakeLLM):
    """Guarda el TurnMedia que ve el LLM en cada turno."""

    def __init__(self, *turns, **kw):
        super().__init__(*turns, **kw)
        self.media: list[TurnMedia] = []

    async def process_turn(self, workflow, state, user_message, on_message=None):
        self.media.append(state.media.model_copy())
        return await super().process_turn(workflow, state, user_message, on_message)


def audio_payload(wamid: str = "wamid.voz1", ts: int | None = None, name: str = "audio.json") -> dict:
    p = fixture(name)
    msg = p["entry"][0]["changes"][0]["value"]["messages"][0]
    msg["id"] = wamid
    if ts is not None:
        msg["timestamp"] = str(ts)
    return p


def stamped_text(body: str, wamid: str, ts: int) -> dict:
    p = text_payload(body, wamid)
    p["entry"][0]["changes"][0]["value"]["messages"][0]["timestamp"] = str(ts)
    return p


def out_rows(sessions) -> list[tuple[str, str, str | None]]:
    return [(m.type, m.status, m.wamid) for m in messages(sessions, direction="out")]


REPLY = "Perfecto, te anoto para el lunes a las diez."


@pytest.mark.parametrize("template", ["demo_booking_classic", "demo_booking"])
async def test_nota_de_voz_en_mirror_responde_con_nota_de_voz(sessions, template):
    a = FakeAudio("quiero un turno para el lunes")
    w = make_wa(sessions, template=template, llm=MediaLLM(reply(REPLY)), audio=a)
    await send(w, audio_payload())

    # STT con los bytes bajados de la url de get_media
    assert w.graph.media_asked == [("200000000000001", None)]   # sin phone_number_id
    assert a.heard == [(b"OggS-entrante", "audio/ogg; codecs=opus")]
    assert [c[0] for c in w.llm.calls] == ["quiero un turno para el lunes"]
    assert w.llm.media == [TurnMedia(user_voice_note=True, reply_voice_note=True)]
    # Sale como nota de voz, con la voz del agente (no VLLM_TTS_VOICE) y al wa_id sin el 9
    assert a.spoken == [(REPLY, "sofia")]
    assert w.graph.uploaded == [(PNID, b"OggS-respuesta")]
    assert w.graph.audios == [(PNID, SEND_TO, "media.up1", True)]
    assert w.graph.sent == [] and w.graph.read == ["wamid.voz1"]
    (conv,) = conversations(sessions)
    assert [(m["role"], m["text"], m.get("voice_note")) for m in conv.messages] == [
        ("user", "quiero un turno para el lunes", True), ("assistant", REPLY, True)]
    assert "media" not in w.engine.store.get(conv.id).model_dump()
    (inb,) = messages(sessions, direction="in")
    assert (inb.type, inb.status, inb.conversation_id) == ("audio", "answered", conv.id)
    assert out_rows(sessions) == [("audio", "sent", "wamid.audio1")]


async def test_audio_de_archivo_tambien_se_transcribe(sessions):
    """Un mp3 adjunto (voice: false) va por el mismo camino; el mime es el de get_media."""
    a = FakeAudio("hola, te mando el audio")
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    w.graph.media_mime = "audio/mpeg"
    await send(w, audio_payload(name="audio_file.json"))
    assert w.graph.media_asked == [("200000000000002", None)]
    assert a.heard[0][1] == "audio/mpeg"
    assert len(w.graph.audios) == 1


async def test_never_responde_en_texto(sessions, monkeypatch):
    monkeypatch.setattr(settings, "wa_audio_reply", "never")
    a = FakeAudio("quiero un turno")
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    await send(w, audio_payload())
    assert w.llm.media == [TurnMedia(user_voice_note=True, reply_voice_note=False)]
    assert a.spoken == [] and w.graph.uploaded == []
    assert w.graph.sent == [(PNID, SEND_TO, REPLY)]
    (conv,) = conversations(sessions)
    assert [m.get("voice_note") for m in conv.messages] == [True, False]
    assert out_rows(sessions) == [("text", "sent", "wamid.out1")]


async def test_always_responde_audio_a_un_texto(sessions, monkeypatch):
    monkeypatch.setattr(settings, "wa_audio_reply", "always")
    a = FakeAudio()
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    await send(w, text_payload("hola", "wamid.t1"))
    assert w.llm.media == [TurnMedia(user_voice_note=False, reply_voice_note=True)]
    assert a.heard == [] and len(w.graph.audios) == 1 and w.graph.sent == []


async def test_mirror_a_un_texto_responde_texto(sessions):
    a = FakeAudio()
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    await send(w, text_payload("hola", "wamid.t1"))
    assert w.llm.media == [TurnMedia()]
    assert a.spoken == [] and w.graph.sent == [(PNID, SEND_TO, REPLY)]


async def test_respuesta_larga_sale_en_texto(sessions, monkeypatch):
    monkeypatch.setattr(settings, "wa_audio_max_reply_chars", 20)
    a = FakeAudio("hola")
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    await send(w, audio_payload())
    assert a.spoken == [] and w.graph.sent == [(PNID, SEND_TO, REPLY)]


async def test_tts_caido_cae_a_texto(sessions, caplog):
    caplog.set_level(logging.INFO, logger="app.whatsapp")
    a = FakeAudio("quiero un turno")
    a.tts_fail = AudioError("TTS respondio 500")
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    await send(w, audio_payload())
    assert w.graph.uploaded == [] and w.graph.sent == [(PNID, SEND_TO, REPLY)]
    assert out_rows(sessions) == [("text", "sent", "wamid.out1")]      # nada llego a Meta como audio
    (conv,) = conversations(sessions)
    assert [m.get("voice_note") for m in conv.messages] == [True, False]
    assert messages(sessions, direction="in")[0].status == "answered"
    assert "AudioError" in caplog.text
    assert "quiero un turno" not in caplog.text and REPLY not in caplog.text and WA_ID not in caplog.text


@pytest.mark.parametrize("step", ["upload", "send"])
async def test_fallo_del_envio_de_audio_cae_a_texto(sessions, step):
    a = FakeAudio("quiero un turno")
    graph = FakeGraph()
    err = GraphError("Media upload error", code=131053, status=400)
    if step == "upload":
        graph.fail_upload = err
    else:
        graph.fail_audio = err
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a, graph=graph)
    await send(w, audio_payload())
    assert graph.sent == [(PNID, SEND_TO, REPLY)]
    assert out_rows(sessions) == [("audio", "failed", None), ("text", "sent", "wamid.out1")]
    failed = messages(sessions, direction="out", type="audio")[0]
    assert failed.error["code"] == 131053 and failed.conversation_id is not None
    (conv,) = conversations(sessions)
    assert conv.messages[-1].get("voice_note") is False


async def test_audio_demasiado_grande_no_se_baja(sessions, monkeypatch):
    monkeypatch.setattr(settings, "wa_audio_max_bytes", 1000)
    a = FakeAudio("no deberia")
    w = make_wa(sessions, llm=MediaLLM(), audio=a)
    w.graph.media_size = 1001
    await send(w, audio_payload())
    assert w.graph.downloaded == [] and a.heard == [] and w.llm.calls == []
    assert w.graph.sent == [(PNID, SEND_TO, settings.wa_audio_too_long_reply)]
    assert conversations(sessions) == []
    (inb,) = messages(sessions, direction="in")
    assert (inb.type, inb.status) == ("audio", "answered")


@pytest.mark.parametrize("error,expected", [
    (AudioTooLong(130.0, 120), "wa_audio_too_long_reply"),
    (MediaTooLarge("media de mas de 4194304 bytes"), "wa_audio_too_long_reply"),
    (AudioError("STT no responde: ConnectError"), "wa_audio_error_reply"),
    ("", "wa_audio_empty_reply"),
])
async def test_audio_sin_turno_respuesta_fija(sessions, error, expected):
    a = FakeAudio(error)
    w = make_wa(sessions, llm=MediaLLM(), audio=a)
    await send(w, audio_payload())
    assert w.llm.calls == [] and a.spoken == []
    assert w.graph.sent == [(PNID, SEND_TO, getattr(settings, expected))]
    assert w.graph.read == ["wamid.voz1"]
    assert conversations(sessions) == []
    assert out_rows(sessions) == [("text", "sent", "wamid.out1")]


async def test_media_de_meta_caida_respuesta_fija(sessions, caplog):
    caplog.set_level(logging.INFO, logger="app.whatsapp")
    a = FakeAudio()
    w = make_wa(sessions, llm=MediaLLM(), audio=a)
    w.graph.fail_media = GraphError("expired", code=131052, status=404)
    await send(w, audio_payload())
    assert a.heard == [] and w.graph.sent == [(PNID, SEND_TO, settings.wa_audio_error_reply)]
    assert "GraphError" in caplog.text and "131052" in caplog.text


async def test_texto_y_audio_en_el_mismo_debounce_son_un_turno(sessions):
    """El texto llega mientras se transcribe el audio: su timer vence y no sale; el
    turno sale cuando termina el audio, con los dos en el orden de Meta."""
    a = FakeAudio("quiero un turno")
    a.gate = asyncio.Event()
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    w.service.handle_payload(audio_payload(ts=1790000001))
    await asyncio.wait_for(a.started.wait(), 1)
    w.service.handle_payload(stamped_text("para el lunes", "wamid.t1", 1790000002))
    await asyncio.sleep(0.2)                 # 4 veces el debounce de 0.05 s
    assert w.llm.calls == []
    a.gate.set()
    await w.service.drain()
    # Mezclado: la marca va solo en la linea transcripta; lo escrito no es transcripcion
    assert [c[0] for c in w.llm.calls] == [f"{VOICE_NOTE_TAG} quiero un turno\npara el lunes"]
    assert w.llm.media == [TurnMedia(user_voice_note=False, reply_voice_note=True)]
    (conv,) = conversations(sessions)
    assert [m.get("voice_note") for m in conv.messages] == [False, True]
    assert len(w.graph.audios) == 1 and w.graph.sent == []
    assert {m.status for m in messages(sessions, direction="in")} == {"answered"}


async def test_foto_no_tapa_el_aviso_de_un_audio_fallido(sessions):
    """Respuestas fijas de distinto texto en la misma ventana salen las dos."""
    a = FakeAudio(AudioError("STT no responde"), AudioError("STT no responde"))
    w = make_wa(sessions, llm=MediaLLM(), audio=a)
    w.service.debounce_seconds = 60
    await send(w, image_payload("wamid.img1"))
    await send(w, audio_payload())
    await send(w, audio_payload("wamid.voz2"))      # el mismo aviso dentro de la ventana: uno solo
    assert [b for _, _, b in w.graph.sent] == [settings.wa_unsupported_reply, settings.wa_audio_error_reply]
    assert sorted((m.wamid, m.status) for m in messages(sessions, direction="in")) == [
        ("wamid.img1", "answered"), ("wamid.voz1", "answered"), ("wamid.voz2", "ignored")]


async def test_texto_que_espera_un_audio_fallido_igual_sale(sessions):
    a = FakeAudio(AudioError("STT no responde"))
    a.gate = asyncio.Event()
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    w.service.handle_payload(audio_payload(ts=1790000001))
    await asyncio.wait_for(a.started.wait(), 1)
    w.service.handle_payload(stamped_text("para el lunes", "wamid.t1", 1790000002))
    await asyncio.sleep(0.2)
    a.gate.set()
    await w.service.drain()
    assert [c[0] for c in w.llm.calls] == ["para el lunes"]
    assert w.llm.media == [TurnMedia()]
    assert [b for _, _, b in w.graph.sent] == [settings.wa_audio_error_reply, REPLY]


async def test_audio_mientras_responde_el_llm_rehace_el_turno(sessions):
    started, gate = asyncio.Event(), asyncio.Event()

    class SlowLLM(MediaLLM):
        async def converse(self, workflow, state, user_message, on_message=None):
            started.set()
            await gate.wait()
            return await super().converse(workflow, state, user_message, on_message)

    a = FakeAudio("quiero un turno")
    w = make_wa(sessions, llm=SlowLLM(reply("vieja"), reply("combinada")), audio=a)
    w.service.handle_payload(stamped_text("hola", "wamid.t1", 1790000000))
    await asyncio.wait_for(started.wait(), 1)
    w.service.handle_payload(audio_payload(ts=1790000001))
    while not a.heard or w.service._inbox[(PNID, WA_ID)].pending_audio:
        await asyncio.sleep(0.01)
    gate.set()
    await w.service.drain()
    assert [c[0] for c in w.llm.calls] == ["hola", f"hola\n{VOICE_NOTE_TAG} quiero un turno"]
    assert w.llm.media == [TurnMedia(), TurnMedia(user_voice_note=False, reply_voice_note=True)]
    assert a.spoken == [("combinada", "sofia")] and w.graph.sent == []
    (conv,) = conversations(sessions)
    assert [(m["text"], m.get("voice_note")) for m in conv.messages] == [
        (f"hola\n{VOICE_NOTE_TAG} quiero un turno", False), ("combinada", True)]


async def test_audio_con_graph_client_real(sessions):
    """Lo que sale a Meta: get_media, descarga con Bearer, subida multipart y envio
    como nota de voz al wa_id sin el 9."""
    media_url = "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=200000000000001"
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/v25.0/200000000000001":
            return httpx.Response(200, json={"url": media_url, "mime_type": "audio/ogg; codecs=opus",
                                             "sha256": "AAAA", "file_size": 7, "id": "200000000000001",
                                             "messaging_product": "whatsapp"})
        if request.url.host == "lookaside.fbsbx.com":
            return httpx.Response(200, content=b"OggS-in")
        if path == f"/v25.0/{PNID}/media":
            return httpx.Response(200, json={"id": "media.999"})
        body = json.loads(request.content)
        if body.get("status") == "read":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(200, json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.real"}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    a = FakeAudio("quiero un turno")
    w = make_wa(sessions, llm=MediaLLM(reply(REPLY)), audio=a)
    w.service = WhatsAppService(w.engine, sessions, debounce_seconds=0.01, audio=a,
                                graph_factory=lambda token: GraphClient(token, http=http))
    await send(w, audio_payload())
    await http.aclose()
    assert all(r.headers["authorization"].startswith("Bearer ") for r in requests)
    assert [(r.method, r.url.host, r.url.path) for r in requests] == [
        ("GET", "graph.facebook.com", "/v25.0/200000000000001"),
        ("GET", "lookaside.fbsbx.com", "/whatsapp_business/attachments/"),
        ("POST", "graph.facebook.com", f"/v25.0/{PNID}/messages"),      # leido
        ("POST", "graph.facebook.com", f"/v25.0/{PNID}/media"),
        ("POST", "graph.facebook.com", f"/v25.0/{PNID}/messages"),
    ]
    assert "phone_number_id" not in requests[0].url.params     # Meta lo compara con quien subio el media
    assert a.heard == [(b"OggS-in", "audio/ogg; codecs=opus")]
    assert b"OggS-respuesta" in requests[3].content
    assert json.loads(requests[4].content) == {"messaging_product": "whatsapp", "to": SEND_TO, "type": "audio",
                                               "audio": {"id": "media.999", "voice": True}}
    with sessions() as s:
        out = s.scalar(select(WaMessage).where(WaMessage.direction == "out"))
        assert (out.type, out.wamid, out.status) == ("audio", "wamid.real", "sent")
