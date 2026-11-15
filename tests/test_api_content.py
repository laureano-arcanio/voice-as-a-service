"""Contenido de la API en disco (services/api_content.py): guardar, nombres, guarda de disco, purga por cliente
y borrado del cliente."""
import datetime

import pytest

from app.config import settings
from app.models import ApiRequest, Client
from app.services import api_content, api_requests

from .test_api import V1, admin, make_client  # noqa: F401  (admin: fixture)

TODAY = datetime.date(2026, 11, 14)


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path / "rec")
    monkeypatch.setattr(api_content, "_room", (0.0, True))
    return tmp_path / "rec" / "api"


def _client(sessions, slug="acme", days=30):
    with sessions() as s:
        from app.models import Tier
        tier = s.query(Tier).first() or Tier(name=f"t-{slug}", description="")
        c = Client(name=slug, slug=slug, tier=tier)
        s.add(c)
        s.flush()
        c.api_content_retention_days = days   # en el alta, None toma el default (30)
        s.commit()
        return c.id


def _row(sessions, client_id, created_at):
    with sessions() as s:
        rid, at = api_requests.log(s, client_id, None, "llm", "ok", created_at=created_at)
    return rid, at


def _bytes(sessions, rid):
    with sessions() as s:
        return s.get(ApiRequest, rid).content_bytes


def test_defaults_on_new_client(sessions):
    cid = _client(sessions, days=30)
    with sessions() as s:
        c = Client(name="b", slug="b", tier_id=s.get(Client, cid).tier_id)
        s.add(c)
        s.commit()
        assert c.store_api_content is True and c.api_content_retention_days == 30


def test_save_writes_and_sets_bytes(sessions, store):
    cid = _client(sessions)
    rid, at = _row(sessions, cid, datetime.datetime(2026, 11, 14, 23, 59))
    n = api_content.save(sessions, rid, cid, at, {"request.json": b"{}", "response.json": b'{"a":1}'})
    assert n == 9 and _bytes(sessions, rid) == 9
    d = store / cid / "2026-11-14" / rid
    assert sorted(p.name for p in d.iterdir()) == ["request.json", "response.json"]
    with sessions() as s:
        assert set(api_content.files_of(s.get(ApiRequest, rid))) == {"request.json", "response.json"}


def test_input_name_never_from_client(sessions, store):
    assert api_content.input_name("input.../../x") == "input.bin"
    assert api_content.input_name("../../etc/passwd") == "input.bin"
    assert api_content.input_name("Nota.MP3") == "input.mp3"
    cid = _client(sessions)
    rid, at = _row(sessions, cid, datetime.datetime(2026, 11, 14))
    api_content.save(sessions, rid, cid, at, {"input.../../x": b"abc"})
    d = store / cid / "2026-11-14" / rid
    assert [p.name for p in d.iterdir()] == ["input.bin"]
    assert not (store / cid / "x").exists()


def test_no_room_does_not_write(sessions, store, monkeypatch):
    monkeypatch.setattr(settings, "api_content_min_free_gb", 10**9)
    cid = _client(sessions)
    rid, at = _row(sessions, cid, datetime.datetime(2026, 11, 14))
    assert api_content.save(sessions, rid, cid, at, {"request.json": b"{}"}) is None
    assert _bytes(sessions, rid) is None and not store.exists()


def test_save_failure_does_not_raise(sessions, store, monkeypatch):
    cid = _client(sessions)
    rid, at = _row(sessions, cid, datetime.datetime(2026, 11, 14))
    store.parent.mkdir(parents=True)
    store.write_text("no es carpeta")   # mkdir falla
    assert api_content.save(sessions, rid, cid, at, {"request.json": b"{}"}) is None
    assert _bytes(sessions, rid) is None


def _day(sessions, cid, day):
    rid, at = _row(sessions, cid, datetime.datetime.combine(day, datetime.time(12)))
    api_content.save(sessions, rid, cid, at, {"request.json": b"{}"})
    return rid


def test_purge_per_client(sessions, store):
    week = _client(sessions, "semana", days=7)
    forever = _client(sessions, "siempre", days=None)
    day8, day7, day6 = (TODAY - datetime.timedelta(days=n) for n in (8, 7, 6))
    old, edge, recent = _day(sessions, week, day8), _day(sessions, week, day7), _day(sessions, week, day6)
    kept = _day(sessions, forever, day8)
    orphan = store / week / (TODAY - datetime.timedelta(days=30)).isoformat() / "sin-fila"
    orphan.mkdir(parents=True)
    (store / week / "no-es-fecha").mkdir()
    with sessions() as s:
        dirs, rows = api_content.purge(s, TODAY)
    assert (dirs, rows) == (2, 1)
    assert _bytes(sessions, old) is None and _bytes(sessions, edge) == 2 and _bytes(sessions, recent) == 2
    assert not (store / week / day8.isoformat()).exists() and not orphan.parent.exists()
    assert (store / week / day7.isoformat()).is_dir() and (store / week / day6.isoformat()).is_dir()
    assert (store / week / "no-es-fecha").is_dir()
    assert _bytes(sessions, kept) == 2 and (store / forever / day8.isoformat()).is_dir()


def test_lower_from_forever_purges_next_run(sessions, store):
    cid = _client(sessions, days=None)
    rid = _day(sessions, cid, TODAY - datetime.timedelta(days=400))
    with sessions() as s:
        assert api_content.purge(s, TODAY) == (0, 0)
        s.get(Client, cid).api_content_retention_days = 7
        s.commit()
        assert api_content.purge(s, TODAY) == (1, 1)
    assert _bytes(sessions, rid) is None


def test_delete_removes_folder_keeps_row(sessions, store):
    cid = _client(sessions)
    rid = _day(sessions, cid, TODAY)
    with sessions() as s:
        row = s.get(ApiRequest, rid)
        api_content.delete(s, row)
        s.commit()
    assert _bytes(sessions, rid) is None and not (store / cid / TODAY.isoformat() / rid).exists()


def test_pcm_to_wav():
    import io
    import wave
    with wave.open(io.BytesIO(api_content.pcm_to_wav(b"\0\0" * 2400))) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()) == (24000, 1, 2, 2400)


def test_delete_client_drops_content(api, admin, store, sessions):  # noqa: F811
    c = make_client(admin, slug="qa_borrar")
    other = make_client(admin, slug="qa_otro")
    _day(sessions, c["id"], TODAY)
    _day(sessions, other["id"], TODAY)
    assert admin.delete(f"{V1}/clients/{c['id']}").status_code == 204
    assert not (store / c["id"]).exists() and (store / other["id"]).is_dir()


def test_billing_loop_purges(sessions, store, monkeypatch):
    from app.billing import loop
    cid = _client(sessions, days=7)
    rid = _day(sessions, cid, datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=30))
    monkeypatch.setattr(loop, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(loop.notify, "deliver", lambda mails: None)
    loop.run_once()
    assert _bytes(sessions, rid) is None
