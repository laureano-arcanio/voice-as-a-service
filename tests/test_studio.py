"""Estudio: texto a voz y transcripcion. Motores falsos: ningun test llama a un modelo."""
import io
import wave

import pytest
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services import studio, tts

from .test_api import V1 as API
from .test_api import admin, client_user, make_client  # noqa: F401  (admin: fixture)
from .test_tts_stream import engine  # noqa: F401  (engine: fixture)


def wav_bytes(seconds: float, rate: int = 16_000) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x10\x00" * int(seconds * rate))
    return out.getvalue()


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path / "recordings")
    return tmp_path / "recordings"


@pytest.fixture
def tts_engine(monkeypatch):
    """2 s de audio por pedazo de texto, y los textos que recibio."""
    seen = []

    async def fake(voice, text):
        seen.append((voice, text))
        yield b"\x01\x00" * tts.SAMPLE_RATE
        yield b"\x01\x00" * tts.SAMPLE_RATE

    monkeypatch.setattr(tts, "synthesize_pcm", fake)
    return seen


@pytest.fixture
def stt_engine(monkeypatch):
    seen = []

    async def fake(pcm):
        seen.append(len(pcm))
        return f"pedazo {len(seen)}"

    monkeypatch.setattr(studio, "transcribe_chunk", fake)
    return seen


@pytest.fixture
def account(api, admin, storage):
    client = make_client(admin, inbound_minutes=20, outbound_minutes=0, api_tts_minutes=20, api_stt_minutes=20)
    return client, client_user(api, admin, client)


async def drain(sessions, kind):
    while job := studio.claim(sessions, kind):
        await studio.process(sessions, kind, job)


def inbound_seconds(user, client_id):
    return user.get(f"{API}/clients/{client_id}/usage").json()["inbound"]["used_seconds"]


def inference(user, client_id):
    return user.get(f"{API}/clients/{client_id}/inference-usage").json()


# ---------- pedazos ----------

def test_split_text_respects_limit_and_keeps_every_word():
    text = "Hola mundo. " * 40 + "palabra " * 200 + "\nFin de la historia."
    pieces = studio.split_text(text, 100)
    assert all(len(p) <= 100 for p in pieces)
    assert " ".join(pieces).split() == text.split()


def test_split_text_cuts_a_word_longer_than_the_limit():
    assert studio.split_text("a" * 250, 100) == ["a" * 100, "a" * 100, "a" * 50]


def test_audio_chunks_cover_the_whole_file_and_cut_in_silence(tmp_path):
    loud, quiet = b"\xff\x7f" * 16_000 * 9, b"\0\0" * 16_000
    path = tmp_path / "a.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes(loud + quiet + loud)
    chunks = list(studio.audio_chunks(path, 10))
    assert sum(len(c) for c in chunks) == len(loud) * 2 + len(quiet)
    assert all(len(c) <= 10 * 16_000 * 2 for c in chunks)
    assert len(chunks[0]) >= len(loud)      # corto dentro del silencio, no en el audio


def test_a_playlist_disguised_as_audio_is_rejected(tmp_path):
    """El demuxer concat leeria otros archivos del servidor."""
    path = tmp_path / "evil.mp3"
    path.write_text("ffconcat version 1.0\nfile '/etc/passwd'\n")
    with pytest.raises(studio.Invalid):
        studio.probe_seconds(path)


# ---------- texto a voz ----------

async def test_speech_is_saved_downloaded_and_billed_by_real_seconds(api, account, tts_engine):
    client, user = account
    r = user.post(f"{API}/studio/speech", json={"text": "Hola. " * 200, "voice": "sofia"})
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["status"] == "queued" and item["billed_seconds"] > 0     # reservado

    await drain(api.sessions, "tts")

    done = user.get(f"{API}/studio/items/{item['id']}").json()
    chunks = len(tts_engine)
    assert chunks > 1 and done["status"] == "done" and done["progress"] == 100
    assert done["audio_seconds"] == pytest.approx(chunks * 2 + (chunks - 1) * studio.PAUSE_BETWEEN_CHUNKS)
    assert done["billed_seconds"] == done["audio_seconds"]
    assert done["text"].startswith("Hola.")
    # Descuenta de los minutos de sintesis, no de los entrantes; va en `studio`, no en una key.
    u = inference(user, client["id"])
    assert u["tts_minutes"]["used"] == u["studio"]["tts_minutes"] == pytest.approx(done["audio_seconds"] / 60, abs=0.01)
    assert u["stt_minutes"]["used"] == 0 and u["keys"] == [] and u["requests"]["tts"] == 0
    assert inbound_seconds(user, client["id"]) == 0

    wav = user.get(f"{API}/studio/items/{item['id']}/audio")
    assert wav.status_code == 200 and wav.content[:4] == b"RIFF"
    for fmt, media, magic in (("mp3", "audio/mpeg", None), ("ogg", "audio/ogg", b"OggS"), ("flac", "audio/flac", b"fLaC")):
        r = user.get(f"{API}/studio/items/{item['id']}/audio", params={"format": fmt, "download": True})
        assert r.status_code == 200 and r.headers["content-type"].startswith(media), fmt
        assert "attachment" in r.headers["content-disposition"] and f".{fmt}" in r.headers["content-disposition"]
        assert r.content and (magic is None or r.content.startswith(magic))


def test_speech_without_minutes_is_rejected_and_reserves_nothing(api, admin, storage, tts_engine):
    client = make_client(admin, inbound_minutes=20, api_tts_minutes=1)
    user = client_user(api, admin, client)
    r = user.post(f"{API}/studio/speech", json={"text": "palabra " * 500, "voice": "sofia"})
    assert r.status_code == 429 and r.json()["code"] == "api_tts_minutes"
    assert r.json()["detail"].endswith("te quedan 1 minuto este mes")
    assert user.get(f"{API}/studio/items").json()["total"] == 0


def test_studio_does_not_need_inbound_minutes_but_needs_its_engine_in_the_plan(api, admin, storage, tts_engine):
    user = client_user(api, admin, make_client(admin, inbound_minutes=0, api_tts_minutes=5, api_stt_minutes=0))
    assert user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}).status_code == 201
    r = user.post(f"{API}/studio/transcriptions", files={"file": ("a.wav", wav_bytes(2))})
    assert r.status_code == 403 and r.json()["code"] == "not_in_plan"
    other = client_user(api, admin, make_client(admin, slug="otra", api_tts_minutes=0, api_stt_minutes=5),
                        email="b@otra.com")
    r = other.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"})
    assert r.status_code == 403 and r.json()["code"] == "not_in_plan"
    assert other.post(f"{API}/studio/transcriptions", files={"file": ("a.wav", wav_bytes(2))}).status_code == 201
    assert other.get(f"{API}/studio/items").json()["total"] == 1


def test_two_jobs_cannot_spend_the_same_minutes(api, admin, storage, tts_engine):
    client = make_client(admin, api_tts_minutes=1)
    user = client_user(api, admin, client)
    text = "palabra " * 80     # unos 40 s
    assert user.post(f"{API}/studio/speech", json={"text": text, "voice": "sofia"}).status_code == 201
    r = user.post(f"{API}/studio/speech", json={"text": text, "voice": "sofia"})
    assert r.status_code == 429


def test_unknown_voice_never_reaches_the_engine(api, account, tts_engine):
    _, user = account
    r = user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "default"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_voice"
    assert tts_engine == []


async def test_failed_job_does_not_bill(api, account, monkeypatch):
    client, user = account

    async def broken(voice, text):
        raise RuntimeError("motor caido")
        yield b""

    monkeypatch.setattr(tts, "synthesize_pcm", broken)
    item = user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}).json()
    await drain(api.sessions, "tts")
    done = user.get(f"{API}/studio/items/{item['id']}").json()
    assert done["status"] == "failed" and done["billed_seconds"] == 0 and done["error"]
    assert inference(user, client["id"])["tts_minutes"]["used"] == 0


def test_interrupted_job_goes_back_to_the_queue(api, account, tts_engine):
    _, user = account
    item = user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}).json()
    sessions = api.sessions
    assert studio.claim(sessions, "tts")["id"] == item["id"]
    assert studio.claim(sessions, "tts") is None
    assert studio.requeue_interrupted(sessions) == 1
    assert studio.claim(sessions, "tts")["id"] == item["id"]


async def test_loop_survives_a_database_that_is_not_ready(monkeypatch):
    calls = []

    def flaky(sessions):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("no existe la tabla")
        return 0

    async def worker(sessions, kind):
        calls.append(kind)

    monkeypatch.setattr(settings, "studio_tick_seconds", 0)
    monkeypatch.setattr(studio, "get_sessionmaker", lambda: None)
    monkeypatch.setattr(studio, "requeue_interrupted", flaky)
    monkeypatch.setattr(studio, "_worker", worker)
    await studio.studio_loop()
    assert calls == [1, 1, "tts", "stt"]


# ---------- transcripcion ----------

async def test_transcription_is_saved_in_pieces_and_billed(api, account, stt_engine, monkeypatch):
    client, user = account
    monkeypatch.setattr(settings, "studio_stt_chunk_seconds", 2)
    r = user.post(f"{API}/studio/transcriptions", files={"file": ("reunión.wav", wav_bytes(5), "audio/wav")})
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["title"] == "reunión.wav" and item["billed_seconds"] == pytest.approx(5)

    await drain(api.sessions, "stt")

    done = user.get(f"{API}/studio/items/{item['id']}").json()
    assert done["status"] == "done" and done["text"].startswith("pedazo 1 pedazo 2")
    assert len(stt_engine) >= 3 and done["billed_seconds"] == pytest.approx(5)
    u = inference(user, client["id"])
    assert u["stt_minutes"]["used"] == u["studio"]["stt_minutes"] == pytest.approx(5 / 60, abs=0.01)
    assert u["tts_minutes"]["used"] == 0 and inbound_seconds(user, client["id"]) == 0
    original = user.get(f"{API}/studio/items/{item['id']}/audio")
    assert original.content[:4] == b"RIFF" and original.headers["content-type"].startswith("audio/wav")


@pytest.mark.parametrize(("name", "content", "code"), [
    ("pagina.html", b"<script>alert(1)</script>", "audio_format"),
    ("roto.mp3", b"esto no es audio", "audio_invalid"),
])
def test_bad_uploads_leave_nothing(api, account, storage, name, content, code):
    client, user = account
    r = user.post(f"{API}/studio/transcriptions", files={"file": (name, content)})
    assert r.status_code == 422 and r.json()["code"] == code
    assert user.get(f"{API}/studio/items").json()["total"] == 0
    assert not list((storage / "studio" / client["id"]).glob("*")) if (storage / "studio" / client["id"]).exists() else True


def test_transcription_longer_than_the_minutes_left_is_rejected(api, admin, storage):
    client = make_client(admin, inbound_minutes=20, api_stt_minutes=1)
    user = client_user(api, admin, client)
    r = user.post(f"{API}/studio/transcriptions", files={"file": ("a.wav", wav_bytes(90))})
    assert r.status_code == 429 and r.json()["code"] == "api_stt_minutes"
    assert user.get(f"{API}/studio/items").json()["total"] == 0


# ---------- historial ----------

async def test_delete_removes_content_but_not_the_minutes(api, account, storage, tts_engine):
    client, user = account
    item = user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}).json()
    await drain(api.sessions, "tts")
    assert user.delete(f"{API}/studio/items/{item['id']}").status_code == 204
    assert user.get(f"{API}/studio/items/{item['id']}").status_code == 404
    assert user.get(f"{API}/studio/items").json()["total"] == 0
    assert not (storage / "studio" / client["id"] / item["id"]).exists()
    assert inference(user, client["id"])["tts_minutes"]["used"] == pytest.approx(2 / 60, abs=0.01)


def test_deleting_a_queued_job_releases_its_reservation(api, account, tts_engine):
    client, user = account
    item = user.post(f"{API}/studio/speech", json={"text": "Hola. " * 20, "voice": "sofia"}).json()
    assert inference(user, client["id"])["tts_minutes"]["used"] > 0
    user.delete(f"{API}/studio/items/{item['id']}")
    assert inference(user, client["id"])["tts_minutes"]["used"] == 0
    assert studio.claim(api.sessions, "tts") is None


def test_a_job_being_processed_cannot_be_deleted(api, account, tts_engine):
    _, user = account
    item = user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}).json()
    studio.claim(api.sessions, "tts")
    r = user.delete(f"{API}/studio/items/{item['id']}")
    assert r.status_code == 409 and r.json()["code"] == "studio_busy"


def test_another_client_cannot_see_the_items(api, admin, account, tts_engine):
    _, user = account
    other_client = make_client(admin, slug="otra", api_tts_minutes=20)
    other = client_user(api, admin, other_client, email="b@otra.com")
    item = user.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}).json()
    assert other.get(f"{API}/studio/items").json()["total"] == 0
    assert inference(other, other_client["id"])["tts_minutes"]["used"] == 0
    for r in (other.get(f"{API}/studio/items/{item['id']}"),
              other.get(f"{API}/studio/items/{item['id']}/audio"),
              other.delete(f"{API}/studio/items/{item['id']}")):
        assert r.status_code == 404


def test_support_admin_can_see_but_not_spend(api, admin, account, tts_engine):
    client, _ = account
    support = {"X-Atentina-Client": client["id"]}
    r = admin.post(f"{API}/studio/speech", json={"text": "Hola", "voice": "sofia"}, headers=support)
    assert r.status_code == 403 and r.json()["code"] == "support_read_only"
    assert admin.get(f"{API}/studio/items", headers=support).status_code == 200


# ---------- pruebas de voz: sin cargo ----------

@pytest.mark.parametrize("fmt", ["pcm", "wav"])
def test_voice_test_does_not_bill_nor_keep_an_item(account, engine, fmt):
    client, user = account
    r = user.post(f"{API}/tts/preview", json={"voice": "sofia", "text": "Hola", "format": fmt})
    assert r.status_code == 200 and r.content
    assert user.get(f"{API}/studio/items").json()["total"] == 0
    u = inference(user, client["id"])
    assert u["tts_minutes"]["used"] == 0 and u["studio"] == {"tts_minutes": 0, "stt_minutes": 0}
    assert inbound_seconds(user, client["id"]) == 0


def test_voice_test_works_without_any_minutes_in_the_plan(api, admin, storage, engine):
    user = client_user(api, admin, make_client(admin, inbound_minutes=0, api_tts_minutes=0))
    r = user.post(f"{API}/tts/preview", json={"voice": "sofia", "text": "Hola"})
    assert r.status_code == 200 and list(engine)


def test_old_voice_test_rows_do_not_count(api, account):
    from app.models import StudioItem
    client, user = account
    with api.sessions() as s:
        s.add(StudioItem(client_id=client["id"], kind="tts", origin="voice_test", status="done", title="Hola",
                         billed_seconds=600))
        s.commit()
    assert inference(user, client["id"])["tts_minutes"]["used"] == 0
    assert inbound_seconds(user, client["id"]) == 0


def test_support_admin_voice_test_does_not_bill(api, admin, account, engine):
    client, user = account
    r = admin.post(f"{API}/tts/preview", json={"voice": "sofia", "text": "Hola"},
                   headers={"X-Atentina-Client": client["id"]})
    assert r.status_code == 200
    assert inference(user, client["id"])["tts_minutes"]["used"] == 0
    assert user.get(f"{API}/studio/items").json()["total"] == 0
