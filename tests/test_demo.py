"""Demo publica de la landing: sesion con Turnstile, llamadas, resultado, voz y limites."""
import datetime

import jwt
import pytest

from app.cli import seed_demo
from app.config import settings
from app.db import utcnow
from app.models import Agent, CallRow, CallStatus, Client, ConversationRow
from app.services import demo, tts

V1 = "/api/v1/demo"
ORIGIN = "https://atentina.com.ar"


@pytest.fixture
def landing(api, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    monkeypatch.setattr(settings, "demo_livekit_url", "wss://rtc.example")
    api.turnstile_ok = True

    async def fake_verify(token, ip):
        return api.turnstile_ok

    monkeypatch.setattr(demo, "verify_turnstile", fake_verify)
    demo.limiter.reset()
    demo._tts_cache.clear()
    with api.sessions() as s:
        seed_demo(s)
        s.commit()
    return api


def session(api) -> dict:
    r = api.client.post(f"{V1}/sessions", json={"turnstile_token": "ok"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def call(api, headers, agent="turnos"):
    return api.client.post(f"{V1}/calls", json={"agent": agent}, headers=headers)


def finish_all(api):
    with api.sessions() as s:
        s.query(CallRow).update({"status": CallStatus.finalizada})
        s.commit()


def test_disabled_without_turnstile_secret(api):
    r = api.client.post(f"{V1}/sessions", json={"turnstile_token": "x"})
    assert r.status_code == 503 and r.json()["code"] == "demo_unavailable"


def test_seed_creates_demo_agents_once(landing):
    with landing.sessions() as s:
        seed_demo(s)
        s.commit()
        client = s.query(Client).filter_by(slug=settings.demo_client).one()
        slugs = sorted(a.slug for a in s.query(Agent).filter_by(client_id=client.id))
    assert slugs == ["cobranzas", "reclamos", "turnos"]


def test_session_requires_turnstile(landing):
    landing.turnstile_ok = False
    r = landing.client.post(f"{V1}/sessions", json={"turnstile_token": "bad"})
    assert r.status_code == 403 and r.json()["code"] == "captcha_failed"


def test_calls_require_demo_session(landing):
    assert call(landing, {}).status_code == 401
    forged = jwt.encode({"sid": "x", "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5)},
                        settings.auth_secret, algorithm="HS256")
    assert call(landing, {"Authorization": f"Bearer {forged}"}).status_code == 401


def test_start_call_and_result(landing):
    headers = session(landing)
    r = call(landing, headers)
    assert r.status_code == 201, r.text
    started = r.json()
    assert started["livekit_url"] == "wss://rtc.example" and started["token"]
    meta = landing.dispatched[-1]
    assert meta["max_duration_seconds"] == settings.demo_call_max_seconds
    assert meta["join_timeout_seconds"] == settings.demo_join_timeout_seconds and meta["phone"] is None

    url = f"{V1}/calls/{started['conversation_id']}"
    assert landing.client.get(url, headers=headers).status_code == 401
    auth = {"Authorization": f"Bearer {started['result_token']}"}
    pending = landing.client.get(url, headers=auth).json()
    assert pending["final"] is False and pending["outcome"] is None
    assert [f["label"] for f in pending["fields"]][:2] == ["Especialidad", "Turno"]

    with landing.sessions() as s:
        conv = s.get(ConversationRow, started["conversation_id"])
        conv.fields = {**conv.fields, "especialidad": "pediatría", "turno": "martes 10:00", "nombre": "Ana Paz",
                       "dni": "30111222", "obra_social": "OSDE", "confirma": True}
        conv.status = "completed"
        conv.progress = {"outcome": "turno_dado"}
        call_row = s.get(CallRow, started["conversation_id"])
        call_row.status, call_row.duration_seconds = CallStatus.finalizada, 95
        s.commit()
    done = landing.client.get(url, headers=auth).json()
    assert done["final"] and done["outcome"] == {"label": "Turno dado", "goal": True}
    assert {f["name"]: f["value"] for f in done["fields"]}["confirma"] is True
    assert done["messages"][0]["role"] == "assistant" and done["agent_name"] == "Sofía"


def test_unknown_agent(landing):
    assert call(landing, session(landing), agent="ventas").status_code == 404


def test_ip_rate_limit(landing, monkeypatch):
    monkeypatch.setattr(settings, "demo_ip_calls_per_hour", 2)
    headers = session(landing)
    assert call(landing, headers).status_code == 201
    finish_all(landing)
    assert call(landing, headers).status_code == 201
    r = call(landing, headers)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and int(r.headers["Retry-After"]) > 0


def test_ip_from_cloudflare_header(landing, monkeypatch):
    monkeypatch.setattr(settings, "demo_ip_calls_per_hour", 1)
    headers = session(landing)
    assert call(landing, {**headers, "CF-Connecting-IP": "203.0.113.1"}).status_code == 201
    finish_all(landing)
    assert call(landing, {**headers, "CF-Connecting-IP": "203.0.113.2"}).status_code == 201
    assert call(landing, {**headers, "CF-Connecting-IP": "203.0.113.1"}).status_code == 429


def test_concurrency_from_demo_tier(landing):
    headers = session(landing)
    for _ in range(3):
        assert call(landing, headers).status_code == 201
    r = call(landing, headers)
    assert r.status_code == 429 and r.json()["code"] == "concurrency_limit"


def test_daily_budget(landing, monkeypatch):
    monkeypatch.setattr(settings, "demo_daily_minutes", 1)
    headers = session(landing)
    started = call(landing, headers).json()
    with landing.sessions() as s:
        row = s.get(CallRow, started["conversation_id"])
        row.status, row.started_at, row.duration_seconds = CallStatus.finalizada, utcnow(), 61
        s.commit()
    r = call(landing, headers)
    assert r.status_code == 429 and r.json()["code"] == "daily_budget"


def test_tts_is_cached_and_limited(landing, monkeypatch):
    requests = []

    async def fake_preview(voice, text):
        requests.append((voice, text))

        async def stream():
            yield b"RIFF"
            yield b"data"

        return stream()

    monkeypatch.setattr(tts, "preview", fake_preview)
    monkeypatch.setattr(settings, "demo_ip_tts_per_hour", 3)
    headers = session(landing)
    body = {"voice": "Sofia", "text": "Hola,   te llamo por tu turno."}
    for _ in range(2):
        r = landing.client.post(f"{V1}/tts", json=body, headers=headers)
        assert r.status_code == 200 and r.content == b"RIFFdata"
    assert requests == [("sofia", "Hola, te llamo por tu turno.")]
    long_text = {"voice": "sofia", "text": "a" * (settings.demo_tts_max_chars + 1)}
    assert landing.client.post(f"{V1}/tts", json=long_text, headers=headers).status_code == 422
    assert landing.client.post(f"{V1}/tts", json=body, headers=headers).status_code == 200
    assert landing.client.post(f"{V1}/tts", json=body, headers=headers).status_code == 429


def test_cors_only_for_landing_origins(landing):
    ok = landing.client.options(f"{V1}/calls", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST",
                                                        "Access-Control-Request-Headers": "authorization"})
    assert ok.headers["access-control-allow-origin"] == ORIGIN
    other = landing.client.options(f"{V1}/calls", headers={"Origin": "https://evil.example",
                                                           "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in other.headers
