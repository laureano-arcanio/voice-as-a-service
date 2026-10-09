"""API de inferencia (/api/v1/inference): alcance de las keys, limites del tier (tokens, minutos y
pedidos por minuto), consumo registrado y reenvio a los motores (simulados con httpx.MockTransport)."""
import asyncio
import base64
import datetime
import json
import struct
from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.models import ApiUsageDaily
from app.services import api_usage
from app.services.inference import InferenceGateway, audio_seconds, get_gateway

from .test_api import V1, admin, client_user, make_agent  # noqa: F401  (admin: fixture)

INF = f"{V1}/inference"
UNLIMITED = {"api_llm_input_tokens": None, "api_llm_output_tokens": None, "api_tts_minutes": None,
             "api_stt_minutes": None, "api_rate_limit": None}


def wav(seconds: float, rate: int = 24_000) -> bytes:
    data = b"\0\0" * int(seconds * rate)
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


class Slices(httpx.AsyncByteStream):
    """El cuerpo en pedazos de `size` bytes, para que una linea del SSE llegue partida."""
    def __init__(self, body: bytes, size: int):
        self.body, self.size = body, size

    async def __aiter__(self):
        for i in range(0, len(self.body), self.size):
            yield self.body[i:i + self.size]


class Engines:
    """Los tres motores simulados: guarda cada pedido y contesta lo que se configure."""
    def __init__(self):
        self.calls: list[dict] = []
        self.chat_usage = {"prompt_tokens": 10, "completion_tokens": 5}
        self.stt_seconds = 12.5
        self.tts_seconds = 2.0
        self.status = 200              # para forzar un error del motor
        self.error_body = {"error": {"message": "boom"}}
        self.stream_usage = True       # el stream trae el chunk final con usage
        self.slice = 7

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        ctype = request.headers.get("content-type", "")
        body = json.loads(request.content) if ctype.startswith("application/json") else request.content
        self.calls.append({"path": path, "body": body, "auth": request.headers.get("authorization")})
        if self.status != 200:
            return httpx.Response(self.status, json=self.error_body)
        if path.endswith("/chat/completions"):
            if body.get("stream"):
                chunks = [{"choices": [{"delta": {"content": t}}], "usage": None} for t in ("Ho", "la", "!")]
                if self.stream_usage:
                    chunks.append({"choices": [], "usage": self.chat_usage})
                sse = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"
                return httpx.Response(200, stream=Slices(sse.encode(), self.slice),
                                      headers={"content-type": "text/event-stream"})
            return httpx.Response(200, json={"id": "c1", "choices": [{"message": {"role": "assistant", "content": "Hola"},
                                                                     "finish_reason": "stop"}],
                                             "usage": self.chat_usage})
        if path.endswith("/audio/transcriptions"):
            return httpx.Response(200, json={"task": "transcribe", "language": None, "duration": self.stt_seconds,
                                             "text": "hola mundo", "segments": []})
        if path.endswith("/audio/speech"):
            if body.get("stream"):    # como vllm-tts: eventos SSE con el PCM en base64 y un `done` con el uso
                pcm = b"\0\0" * int(self.tts_seconds * 24_000)
                parts = [pcm[:3840], pcm[3840:]] if len(pcm) > 3840 else [pcm]
                events = [{"type": "speech.audio.delta", "response_format": "pcm", "audio": base64.b64encode(p).decode()}
                          for p in parts]
                events.append({"type": "speech.audio.done", "usage": {"input_tokens": 5, "output_tokens": 16,
                                                                      "total_tokens": 21}})
                sse = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)
                return httpx.Response(200, stream=Slices(sse.encode(), self.slice),
                                      headers={"content-type": "text/event-stream"})
            return httpx.Response(200, stream=Slices(wav(self.tts_seconds), 4096), headers={"content-type": "audio/wav"})
        return httpx.Response(404)


@pytest.fixture
def engines(api):
    up = Engines()
    gateway = InferenceGateway(api.sessions, transport=httpx.MockTransport(up))
    api.app.dependency_overrides[get_gateway] = lambda: gateway
    return up


def make_client_with_tier(admin, slug="acme", **api_limits):
    r = admin.post(f"{V1}/tiers", json={"name": f"tier-{slug}", **UNLIMITED, **api_limits})
    assert r.status_code == 201, r.text
    r = admin.post(f"{V1}/clients", json={"name": slug.title(), "slug": slug, "tier_id": r.json()["id"]})
    assert r.status_code == 201, r.text
    return r.json()


def make_key(admin, client, scopes=("llm", "stt", "tts"), name="k"):
    r = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": name, "scopes": list(scopes)})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['key']}"}


def chat(api, key, **body):
    return api.client.post(f"{INF}/chat/completions", headers=key,
                           json={"model": "x", "messages": [{"role": "user", "content": "hola"}], **body})


def stt(api, key, size=1000, **form):
    return api.client.post(f"{INF}/audio/transcriptions", headers=key, data=form,
                           files={"file": ("a.wav", b"\0" * size, "audio/wav")})


def tts(api, key, **body):
    return api.client.post(f"{INF}/audio/speech", headers=key,
                           json={"input": "Hola, ¿cómo estás?", "voice": "sofia", **body})


def usage(api, key, **params):
    r = api.client.get(f"{INF}/usage", headers=key, params=params)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- keys y alcance ----------

def test_key_scopes_are_stored_and_listed(api, admin):
    client = make_client_with_tier(admin)
    r = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "solo llm", "scopes": ["tts", "llm", "llm"]})
    assert r.status_code == 201 and r.json()["scopes"] == ["llm", "tts"]        # orden fijo, sin repetidos
    assert admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "default"}).json()["scopes"] == ["calls"]
    assert admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "x", "scopes": ["root"]}).status_code == 422
    assert admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "x", "scopes": []}).status_code == 422
    assert {k["name"]: k["scopes"] for k in admin.get(f"{V1}/clients/{client['id']}/api-keys").json()} == {
        "solo llm": ["llm", "tts"], "default": ["calls"]}


def test_client_user_creates_inference_keys_for_its_client(api, admin):
    client = make_client_with_tier(admin)
    ana = client_user(api, admin, client)
    r = ana.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "app", "scopes": ["llm"]})
    assert r.status_code == 201
    other = make_client_with_tier(admin, "otra")
    assert ana.post(f"{V1}/clients/{other['id']}/api-keys", json={"name": "x", "scopes": ["llm"]}).status_code == 404


def test_requires_an_api_key_with_the_engine_scope(api, admin, engines):
    client = make_client_with_tier(admin)
    only_llm = make_key(admin, client, ["llm"])
    assert api.client.post(f"{INF}/chat/completions", json={"messages": [{"role": "user", "content": "x"}]}).status_code == 401
    assert admin.post(f"{INF}/chat/completions", json={"messages": [{"role": "user", "content": "x"}]}).status_code == 401  # sesion
    assert api.client.post(f"{INF}/chat/completions", headers={"Authorization": "Bearer vaas_nope"},
                           json={"messages": [{"role": "user", "content": "x"}]}).status_code == 401
    assert chat(api, only_llm).status_code == 200
    for r in (stt(api, only_llm), tts(api, only_llm)):
        assert r.status_code == 403 and r.json()["code"] == "scope_missing"
    assert engines.calls and all(c["path"].endswith("/chat/completions") for c in engines.calls)   # no llego a los otros


def test_inference_and_calls_keys_do_not_cross(api, admin, engines):
    client = make_client_with_tier(admin)
    calls_key = make_key(admin, client, ["calls"])
    inference_key = make_key(admin, client, ["llm", "stt", "tts"])
    r = chat(api, calls_key)
    assert r.status_code == 403 and r.json()["code"] == "scope_missing"
    assert api.client.get(f"{V1}/agents", headers=calls_key).status_code == 200
    r = api.client.get(f"{V1}/agents", headers=inference_key)
    assert r.status_code == 403 and r.json()["code"] == "scope_missing"
    assert api.client.get(f"{V1}/auth/me", headers=inference_key).status_code == 403
    both = make_key(admin, client, ["calls", "llm"])
    assert chat(api, both).status_code == 200 and api.client.get(f"{V1}/agents", headers=both).status_code == 200


def test_revoked_key_and_inactive_client_are_rejected(api, admin, engines):
    client = make_client_with_tier(admin)
    r = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "k", "scopes": ["llm"]}).json()
    key = {"Authorization": f"Bearer {r['key']}"}
    assert chat(api, key).status_code == 200
    assert admin.patch(f"{V1}/clients/{client['id']}", json={"active": False}).status_code == 200
    r2 = chat(api, key)
    assert r2.status_code == 429 and r2.json()["code"] == "client_inactive"
    admin.patch(f"{V1}/clients/{client['id']}", json={"active": True})
    assert admin.delete(f"{V1}/clients/{client['id']}/api-keys/{r['id']}").status_code == 204
    assert chat(api, key).status_code == 401


# ---------- LLM ----------

def test_chat_forwards_a_safe_request_and_counts_tokens(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    r = chat(api, key, temperature=0.2, max_tokens=50, top_p=0.9, n=None)
    assert r.status_code == 200 and r.json()["choices"][0]["message"]["content"] == "Hola"
    sent = engines.calls[-1]
    assert sent["path"].endswith("/chat/completions") and sent["auth"] == f"Bearer {settings.vllm_api_key}"
    body = sent["body"]
    assert body["model"] == settings.vllm_llm_model          # el del cliente se ignora
    assert body["max_tokens"] == 50 and body["temperature"] == 0.2 and body["stream"] is False
    assert body["chat_template_kwargs"] == {"enable_thinking": settings.llm_thinking}
    u = usage(api, key)
    assert u["llm_input_tokens"]["used"] == 10 and u["llm_output_tokens"]["used"] == 5 and u["requests"]["llm"] == 1


def test_chat_caps_max_tokens(api, admin, engines, monkeypatch):
    monkeypatch.setattr(settings, "inference_llm_max_tokens", 100)
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    chat(api, key)
    assert engines.calls[-1]["body"]["max_tokens"] == 100          # sin max_tokens: el tope
    chat(api, key, max_tokens=5000)
    assert engines.calls[-1]["body"]["max_tokens"] == 100          # mas que el tope: el tope
    chat(api, key, max_completion_tokens=7)
    assert engines.calls[-1]["body"]["max_tokens"] == 7


def test_chat_rejects_what_the_platform_does_not_allow(api, admin, engines):
    key = make_key(admin, make_client_with_tier(admin))
    assert chat(api, key, n=3).status_code == 422
    assert api.client.post(f"{INF}/chat/completions", headers=key, json={"messages": []}).status_code == 422
    r = api.client.post(f"{INF}/chat/completions", headers=key,
                        json={"messages": [{"role": "user", "content": "x"}], "chat_template_kwargs": {"enable_thinking": True},
                              "guided_json": {}, "logprobs": True})
    assert r.status_code == 200
    body = engines.calls[-1]["body"]
    assert body["chat_template_kwargs"] == {"enable_thinking": settings.llm_thinking}
    assert "guided_json" not in body and "logprobs" not in body


def test_input_and_output_tokens_are_limited_separately(api, admin, engines):
    client = make_client_with_tier(admin, api_llm_input_tokens=10, api_llm_output_tokens=1000)
    key = make_key(admin, client)
    assert chat(api, key).status_code == 200                         # usa 10 de 10 de entrada
    r = chat(api, key)
    assert r.status_code == 429 and r.json()["code"] == "api_llm_input_tokens"
    assert len(engines.calls) == 1                                    # el segundo no llego al motor

    client2 = make_client_with_tier(admin, "salida", api_llm_input_tokens=1000, api_llm_output_tokens=5)
    key2 = make_key(admin, client2)
    assert chat(api, key2).status_code == 200                        # 5 de 5 de salida
    r = chat(api, key2)
    assert r.status_code == 429 and r.json()["code"] == "api_llm_output_tokens"


def test_max_tokens_shrinks_to_what_is_left_and_the_next_request_is_cut(api, admin, engines):
    client = make_client_with_tier(admin, api_llm_output_tokens=20)
    key = make_key(admin, client)
    engines.chat_usage = {"prompt_tokens": 3, "completion_tokens": 15}
    chat(api, key, max_tokens=100)
    assert engines.calls[-1]["body"]["max_tokens"] == 20            # lo que le queda
    engines.chat_usage = {"prompt_tokens": 3, "completion_tokens": 5}
    assert chat(api, key, max_tokens=100).status_code == 200
    assert engines.calls[-1]["body"]["max_tokens"] == 5             # 20 - 15
    r = chat(api, key, max_tokens=100)                              # llego justo a 20: ya no entra
    assert r.status_code == 429 and r.json()["code"] == "api_llm_output_tokens" and len(engines.calls) == 2


def test_plan_without_the_engine_is_forbidden_and_none_is_unlimited(api, admin, engines):
    closed = make_client_with_tier(admin, api_llm_input_tokens=0, api_llm_output_tokens=0, api_tts_minutes=0,
                                   api_stt_minutes=0)
    key = make_key(admin, closed)
    for r in (chat(api, key), stt(api, key), tts(api, key)):
        assert r.status_code == 403 and r.json()["code"] == "not_in_plan"
    assert engines.calls == []
    # Un solo motor cerrado: los otros andan.
    partial = make_client_with_tier(admin, "parcial", api_tts_minutes=0)
    key = make_key(admin, partial)
    assert chat(api, key).status_code == 200 and tts(api, key).status_code == 403


def test_chat_stream_relays_sse_and_counts_the_final_usage(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    engines.chat_usage = {"prompt_tokens": 8, "completion_tokens": 3}
    r = chat(api, key, stream=True)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    assert r.text.count("data: ") == 5 and r.text.rstrip().endswith("data: [DONE]")
    assert engines.calls[-1]["body"]["stream_options"] == {"include_usage": True}
    u = usage(api, key)
    assert (u["llm_input_tokens"]["used"], u["llm_output_tokens"]["used"], u["requests"]["llm"]) == (8, 3, 1)


def test_chat_stream_without_usage_is_estimated(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    engines.stream_usage = False                                     # el stream se corto antes del chunk de usage
    assert chat(api, key, stream=True).status_code == 200
    u = usage(api, key)
    assert u["llm_output_tokens"]["used"] == 3 and u["llm_input_tokens"]["used"] >= 1   # 3 chunks con contenido


def test_engine_errors_are_not_billed(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    engines.status = 500
    r = chat(api, key)
    assert r.status_code == 502 and r.json()["code"] == "upstream_error" and "boom" not in r.text
    engines.status = 400
    engines.error_body = {"error": {"message": "context length exceeded"}}
    r = chat(api, key)
    assert r.status_code == 400 and r.json()["code"] == "upstream_rejected" and "context length" in r.json()["detail"]
    assert chat(api, key, stream=True).status_code == 400
    assert usage(api, key)["requests"] == {"llm": 0, "stt": 0, "tts": 0}


# ---------- STT ----------

def test_transcription_counts_audio_seconds_and_formats(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    r = stt(api, key, language="es")
    assert r.status_code == 200 and r.json() == {"text": "hola mundo", "usage": {"type": "duration", "seconds": 12.5}}
    sent = engines.calls[-1]
    assert sent["path"].endswith("/audio/transcriptions") and b"verbose_json" in sent["body"]   # pide la duracion
    assert stt(api, key, response_format="text").text == "hola mundo"
    v = stt(api, key, response_format="verbose_json").json()
    assert v["text"] == "hola mundo" and v["duration"] == 12.5
    assert stt(api, key, response_format="srt").status_code == 422
    u = usage(api, key)
    assert u["stt_minutes"]["used"] == round(37.5 / 60, 2) and u["requests"]["stt"] == 3


def test_transcription_minutes_are_limited(api, admin, engines):
    client = make_client_with_tier(admin, api_stt_minutes=1)
    key = make_key(admin, client)
    engines.stt_seconds = 45
    assert stt(api, key).status_code == 200
    assert stt(api, key).status_code == 200                          # 45 < 60: entra, y se pasa (90 s)
    r = stt(api, key)
    assert r.status_code == 429 and r.json()["code"] == "api_stt_minutes"
    assert usage(api, key)["stt_minutes"] == {"used": 1.5, "limit": 1, "remaining": 0}


def test_transcription_limits_the_upload_and_the_engine_errors(api, admin, engines, monkeypatch):
    key = make_key(admin, make_client_with_tier(admin))
    monkeypatch.setattr(settings, "inference_stt_max_bytes", 2000)
    assert stt(api, key, size=2000).status_code == 200
    r = stt(api, key, size=2001)
    assert r.status_code == 400 and r.json()["code"] == "payload_too_large"
    assert stt(api, key, size=0).status_code == 422
    engines.status = 400
    engines.error_body = {"detail": "no se pudo decodificar el audio"}
    r = stt(api, key)
    assert r.status_code == 400 and "decodificar" in r.json()["detail"]
    assert usage(api, key)["requests"]["stt"] == 1


def test_big_audio_passes_the_body_limit_but_big_json_does_not(api, admin, engines, monkeypatch):
    key = make_key(admin, make_client_with_tier(admin))
    assert stt(api, key, size=3 * 1024 * 1024).status_code == 200     # mas que el 1 MiB del resto de /api
    r = api.client.post(f"{INF}/chat/completions", headers=key,
                        json={"messages": [{"role": "user", "content": "x" * (2 * 1024 * 1024)}]})
    assert r.status_code == 413


# ---------- TTS ----------

def test_speech_streams_audio_and_counts_seconds(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    engines.tts_seconds = 2.5
    r = tts(api, key)
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert r.content[:4] == b"RIFF" and len(r.content) == 44 + 2 * 60_000
    sent = engines.calls[-1]["body"]
    assert sent["voice"] == "sofia" and sent["model"] == settings.vllm_tts_model and sent["response_format"] == "wav"
    r = tts(api, key, response_format="pcm", voice="Martin")         # mayusculas: se normaliza
    assert r.status_code == 200 and len(r.content) == 2 * 60_000 and engines.calls[-1]["body"]["voice"] == "martin"
    u = usage(api, key)
    assert u["tts_minutes"]["used"] == round(5 / 60, 2) and u["requests"]["tts"] == 2


def sse_events(text: str) -> list[dict]:
    return [json.loads(line[5:]) for line in text.splitlines() if line.startswith("data:")]


def test_speech_pcm_uses_the_engine_stream_and_wav_does_not(api, admin, engines):
    key = make_key(admin, make_client_with_tier(admin))
    engines.tts_seconds = 1.0
    tts(api, key, response_format="pcm")
    assert engines.calls[-1]["body"]["stream"] is True               # pcm: el motor transmite
    r = tts(api, key)                                                 # wav: archivo completo, encabezado correcto
    assert "stream" not in engines.calls[-1]["body"] and r.content[:4] == b"RIFF"
    assert struct.unpack("<I", r.content[40:44])[0] == 48_000


def test_speech_sse_events_and_usage(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    engines.tts_seconds = 2.0
    r = tts(api, key, stream_format="sse")                            # sin response_format: pcm
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = sse_events(r.text)
    assert [e["type"] for e in events] == ["speech.audio.delta", "speech.audio.delta", "speech.audio.done"]
    audio = b"".join(base64.b64decode(e["audio"]) for e in events[:-1])
    assert len(audio) == 96_000                                        # 2 s de PCM 24 kHz 16 bits
    assert events[-1]["duration_seconds"] == 2.0 and events[-1]["usage"]["output_tokens"] == 16
    assert usage(api, key)["tts_minutes"]["used"] == round(2 / 60, 2)
    assert tts(api, key, stream_format="sse", response_format="wav").status_code == 422     # sse solo con pcm
    assert tts(api, key, stream_format="chunked").status_code == 422
    assert len(engines.calls) == 1


def test_speech_quota_applies_to_streams(api, admin, engines):
    client = make_client_with_tier(admin, api_tts_minutes=1)
    key = make_key(admin, client)
    engines.tts_seconds, engines.slice = 70, 16_384
    assert tts(api, key, response_format="pcm").status_code == 200
    r = tts(api, key, stream_format="sse")
    assert r.status_code == 429 and r.json()["code"] == "api_tts_minutes"


def _access(api, admin, **limits):
    client = make_client_with_tier(admin, **limits)
    key = make_key(admin, client)
    with api.sessions() as s:
        from app.models import ApiKey
        key_id = s.query(ApiKey).filter_by(client_id=client["id"]).one().id
    return SimpleNamespace(client=SimpleNamespace(id=client["id"], slug="x"), key=SimpleNamespace(id=key_id),
                           remaining=api_usage.Remaining()), key


def _gated_gateway(api, first: bytes, rest: list[bytes], gate: asyncio.Event) -> InferenceGateway:
    """Un motor que manda el primer pedazo y no sigue hasta que el cliente lo haya recibido: si el gateway
    acumulara todo antes de reenviar, el primer pedazo nunca llegaria y el test se cuelga (y falla)."""
    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield first
            await asyncio.wait_for(gate.wait(), 5)
            for part in rest:
                yield part

    return InferenceGateway(api.sessions, transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=Body(), headers={"content-type": "text/event-stream"})))


def _delta(pcm: bytes) -> bytes:
    event = {"type": "speech.audio.delta", "audio": base64.b64encode(pcm).decode()}
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()


def test_tts_pcm_is_forwarded_before_the_engine_finishes(api, admin):
    access, _ = _access(api, admin)
    gate = asyncio.Event()
    done = b'event: speech.audio.done\ndata: {"type": "speech.audio.done", "usage": {}}\n\n'
    gateway = _gated_gateway(api, _delta(b"\1\0" * 100), [_delta(b"\2\0" * 50), done], gate)

    async def run():
        response = await gateway.speech(access, "sofia", "Hola", "pcm")
        chunks = response.body_iterator
        first = await asyncio.wait_for(chunks.__anext__(), 2)      # llega con el motor todavia sintetizando
        assert first == b"\1\0" * 100 and not gate.is_set()
        gate.set()
        return first, [c async for c in chunks]

    first, rest = asyncio.run(run())
    assert rest == [b"\2\0" * 50]
    with api.sessions() as s:
        t = api_usage.totals(s, access.client.id, *api_usage.month_days())
    assert t.tts_requests == 1 and t.tts_seconds == 300 / 48_000


def test_tts_stream_cut_by_the_client_bills_what_was_delivered(api, admin):
    access, _ = _access(api, admin)
    gate = asyncio.Event()
    gateway = _gated_gateway(api, _delta(b"\1\0" * 4800), [_delta(b"\2\0" * 4800)], gate)

    async def run():
        response = await gateway.speech(access, "sofia", "Hola", "pcm")
        chunks = response.body_iterator
        await chunks.__anext__()
        await chunks.aclose()                                      # el cliente se va

    asyncio.run(run())
    with api.sessions() as s:
        t = api_usage.totals(s, access.client.id, *api_usage.month_days())
    assert t.tts_requests == 1 and t.tts_seconds == 9600 / 48_000


def test_llm_stream_is_forwarded_before_the_engine_finishes_and_a_cut_is_estimated(api, admin):
    access, _ = _access(api, admin)
    gate = asyncio.Event()
    token = b'data: {"choices":[{"delta":{"content":"Ho"}}],"usage":null}\n\n'
    gateway = _gated_gateway(api, token, [token, b"data: [DONE]\n\n"], gate)

    async def run():
        response = await gateway.chat(access, {"messages": [{"role": "user", "content": "hola"}], "stream": True})
        chunks = response.body_iterator
        first = await asyncio.wait_for(chunks.__anext__(), 2)
        assert first == token and not gate.is_set()
        await chunks.aclose()                                      # corta con el motor todavia generando

    asyncio.run(run())
    with api.sessions() as s:
        t = api_usage.totals(s, access.client.id, *api_usage.month_days())
    assert t.llm_requests == 1 and t.llm_output_tokens == 1 and t.llm_input_tokens >= 1   # estimado: 1 chunk


def test_speech_validates_before_touching_the_engine(api, admin, engines, monkeypatch):
    key = make_key(admin, make_client_with_tier(admin))
    r = tts(api, key, voice="vivian")                                  # una voz fuera del checkpoint mata vllm-tts
    assert r.status_code == 422 and r.json()["code"] == "invalid_voice"
    monkeypatch.setattr(settings, "inference_tts_max_chars", 10)
    assert tts(api, key, input="x" * 11).status_code == 422
    assert tts(api, key, input="   ").status_code == 422
    assert tts(api, key, response_format="mp3").status_code == 422
    assert tts(api, key, voice="default").status_code == 422
    assert engines.calls == []


def test_speech_minutes_are_limited(api, admin, engines):
    client = make_client_with_tier(admin, api_tts_minutes=1)
    key = make_key(admin, client)
    engines.tts_seconds = 40
    assert tts(api, key).status_code == 200 and tts(api, key).status_code == 200      # 80 s de 60
    r = tts(api, key)
    assert r.status_code == 429 and r.json()["code"] == "api_tts_minutes"
    assert usage(api, key)["tts_minutes"]["remaining"] == 0


def test_audio_seconds_from_the_stream():
    assert audio_seconds("wav", wav(3.0)[:44], len(wav(3.0))) == 3.0
    assert audio_seconds("wav", wav(1.0, rate=16_000)[:44], len(wav(1.0, rate=16_000))) == 1.0
    assert audio_seconds("pcm", b"", 48_000) == 1.0
    assert audio_seconds("wav", b"", 100) == 100 / 48_000       # sin encabezado legible: como PCM


# ---------- pedidos por minuto ----------

def test_rate_limit_is_per_client_across_engines_and_keys(api, admin, engines):
    client = make_client_with_tier(admin, api_rate_limit=3)
    k1, k2 = make_key(admin, client, name="a"), make_key(admin, client, name="b")
    assert chat(api, k1).status_code == 200 and stt(api, k2).status_code == 200 and tts(api, k1).status_code == 200
    r = chat(api, k2)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and int(r.headers["Retry-After"]) >= 1
    other = make_client_with_tier(admin, "otra", api_rate_limit=3)     # otro cliente no se afecta
    assert chat(api, make_key(admin, other)).status_code == 200


def test_rate_limit_zero_blocks_and_none_is_unlimited(api, admin, engines):
    blocked = make_key(admin, make_client_with_tier(admin, api_rate_limit=0))
    r = chat(api, blocked)
    assert r.status_code == 403 and r.json()["code"] == "not_in_plan"
    free = make_key(admin, make_client_with_tier(admin, "libre"))
    assert all(chat(api, free).status_code == 200 for _ in range(20))


def test_rejected_requests_also_count_for_the_rate_limit(api, admin, engines):
    client = make_client_with_tier(admin, api_rate_limit=2, api_llm_input_tokens=0, api_llm_output_tokens=0)
    key = make_key(admin, client)
    assert [chat(api, key).status_code for _ in range(3)] == [403, 403, 429]


# ---------- consumo ----------

def test_usage_by_key_and_month(api, admin, engines):
    client = make_client_with_tier(admin, api_llm_input_tokens=1000, api_llm_output_tokens=500, api_tts_minutes=10,
                                   api_stt_minutes=20, api_rate_limit=100)
    ka, kb = make_key(admin, client, name="crm"), make_key(admin, client, name="bot")
    chat(api, ka)
    chat(api, kb)
    chat(api, kb)
    stt(api, kb)
    u = usage(api, ka)
    assert u["llm_input_tokens"] == {"used": 30, "limit": 1000, "remaining": 970}
    assert u["llm_output_tokens"] == {"used": 15, "limit": 500, "remaining": 485}
    assert u["stt_minutes"]["limit"] == 20 and u["rate_limit"] == 100
    by_name = {k["name"]: k for k in u["keys"]}
    assert by_name["crm"]["requests"]["llm"] == 1 and by_name["bot"]["requests"] == {"llm": 2, "stt": 1, "tts": 0}
    assert by_name["bot"]["llm_input_tokens"] == 20
    # El admin y el usuario del cliente ven lo mismo por /clients/{id}/inference-usage.
    ana = client_user(api, admin, client)
    assert admin.get(f"{V1}/clients/{client['id']}/inference-usage").json()["llm_input_tokens"]["used"] == 30
    assert ana.get(f"{V1}/clients/{client['id']}/inference-usage").json()["requests"]["llm"] == 3
    other = make_client_with_tier(admin, "otra")
    assert ana.get(f"{V1}/clients/{other['id']}/inference-usage").status_code == 404
    # Otro mes: sin consumo.
    last = admin.get(f"{V1}/clients/{client['id']}/inference-usage", params={"month": "2020-01"}).json()
    assert last["llm_input_tokens"]["used"] == 0 and last["month"] == "2020-01"
    assert admin.get(f"{V1}/clients/{client['id']}/inference-usage", params={"month": "2020-13"}).status_code == 422
    assert api.client.get(f"{INF}/usage", headers=ka, params={"month": "x"}).status_code == 422


def test_usage_does_not_spend_quota_or_need_a_scope_with_quota(api, admin, engines):
    client = make_client_with_tier(admin, api_llm_input_tokens=0, api_llm_output_tokens=0)
    key = make_key(admin, client, ["llm"])
    assert usage(api, key)["llm_input_tokens"]["limit"] == 0
    assert api.client.get(f"{INF}/usage", headers=make_key(admin, client, ["calls"])).status_code == 403


def test_previous_month_does_not_count(api, admin, engines):
    client = make_client_with_tier(admin, api_llm_input_tokens=10)
    r = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "k", "scopes": ["llm"]}).json()
    key = {"Authorization": f"Bearer {r['key']}"}
    first, _ = api_usage.month_days()
    last_month = first - datetime.timedelta(days=1)
    with api.sessions() as s:
        api_usage.record(s, client["id"], r["id"], last_month, llm_input_tokens=999)
    assert chat(api, key).status_code == 200                           # el mes pasado no cuenta
    assert chat(api, key).status_code == 429                            # este mes: 10 de 10


def test_record_accumulates_per_day_and_key(api, admin):
    client = make_client_with_tier(admin)
    r = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "k", "scopes": ["llm"]}).json()
    day = datetime.date(2026, 3, 5)
    with api.sessions() as s:
        for _ in range(3):
            api_usage.record(s, client["id"], r["id"], day, llm_requests=1, llm_input_tokens=7, tts_seconds=0.5)
        api_usage.record(s, client["id"], r["id"], day + datetime.timedelta(days=1), llm_input_tokens=1)
        rows = s.query(ApiUsageDaily).order_by(ApiUsageDaily.day).all()
        assert [(x.day, x.llm_requests, x.llm_input_tokens, x.tts_seconds) for x in rows] == [
            (day, 3, 21, 1.5), (day + datetime.timedelta(days=1), 0, 1, 0)]
        t = api_usage.totals(s, client["id"], day, day + datetime.timedelta(days=2))
        assert (t.llm_input_tokens, t.llm_requests, t.tts_seconds) == (22, 3, 1.5)
        with pytest.raises(ValueError):
            api_usage.record(s, client["id"], r["id"], day, nope=1)


def test_month_days_in_the_billing_zone():
    # 2026-10-01 01:00 UTC todavia es 30-sep en Buenos Aires (UTC-3).
    now = datetime.datetime(2026, 10, 1, 1, 0, tzinfo=datetime.UTC)
    assert api_usage.today(now) == datetime.date(2026, 9, 30)
    assert api_usage.month_days(None, now) == (datetime.date(2026, 9, 1), datetime.date(2026, 10, 1))
    assert api_usage.month_days("2026-12") == (datetime.date(2026, 12, 1), datetime.date(2027, 1, 1))


def test_models_and_voices_listing(api, admin, engines):
    key = make_key(admin, make_client_with_tier(admin), ["tts"])
    voices = api.client.get(f"{INF}/voices", headers=key).json()
    assert "sofia" in {v["nombre"] for v in voices} and len(voices) > 10
    models = api.client.get(f"{INF}/models", headers=key).json()
    assert models["object"] == "list" and {m["engine"] for m in models["data"]} == {"llm", "stt", "tts"}
    llm_only = make_key(admin, make_client_with_tier(admin, "b"), ["llm"])
    assert api.client.get(f"{INF}/voices", headers=llm_only).status_code == 403
    assert api.client.get(f"{INF}/models").status_code == 401


# ---------- tiers ----------

def test_tier_api_limits(api, admin):
    r = admin.post(f"{V1}/tiers", json={"name": "nuevo"}).json()
    assert (r["api_llm_input_tokens"], r["api_llm_output_tokens"], r["api_tts_minutes"], r["api_stt_minutes"],
            r["api_rate_limit"]) == (0, 0, 0, 0, 60)                  # sin inferencia salvo que se le de
    r = admin.patch(f"{V1}/tiers/{r['id']}", json={"api_llm_input_tokens": 2_000_000, "api_rate_limit": None,
                                                    "api_stt_minutes": 300}).json()
    assert r["api_llm_input_tokens"] == 2_000_000 and r["api_rate_limit"] is None and r["api_stt_minutes"] == 300
    assert r["api_tts_minutes"] == 0                                    # lo no enviado no cambia
    assert admin.post(f"{V1}/tiers", json={"name": "malo", "api_tts_minutes": -1}).status_code == 422
    big = admin.post(f"{V1}/tiers", json={"name": "grande", "api_llm_output_tokens": 5_000_000_000})
    assert big.status_code == 201 and big.json()["api_llm_output_tokens"] == 5_000_000_000


def test_tier_change_applies_to_the_current_month(api, admin, engines):
    client = make_client_with_tier(admin, api_llm_input_tokens=10)
    key = make_key(admin, client)
    assert chat(api, key).status_code == 200 and chat(api, key).status_code == 429
    admin.patch(f"{V1}/tiers/{client['tier']['id']}", json={"api_llm_input_tokens": 100})
    assert chat(api, key).status_code == 200


def test_integrated_agents_do_not_spend_the_api_quota(api, admin, engines):
    """Los minutos de llamadas y la cuota de la API son independientes."""
    client = make_client_with_tier(admin, api_llm_input_tokens=0, api_llm_output_tokens=0, api_tts_minutes=0,
                                   api_stt_minutes=0)
    agent = make_agent(admin, client)
    r = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]})
    assert r.status_code == 201                                         # el agente integrado anda sin cupo de API
    assert engines.calls == []


# ---------- compatibilidad con el SDK de OpenAI ----------

def test_official_openai_sdk_works_against_the_api(api, admin, engines):
    """El SDK de OpenAI (el que usan los clientes) con base_url = /api/v1/inference: chat, stream,
    transcripcion y sintesis, y el 429 del cupo como RateLimitError."""
    import openai

    client = make_client_with_tier(admin, api_llm_output_tokens=12)
    key = make_key(admin, client)["Authorization"].removeprefix("Bearer ")
    sdk = openai.OpenAI(base_url="http://testserver/api/v1/inference", api_key=key, http_client=api.client,
                        max_retries=0)

    chat = sdk.chat.completions.create(model="atentina", messages=[{"role": "user", "content": "hola"}])
    assert chat.choices[0].message.content == "Hola" and chat.usage.prompt_tokens == 10

    engines.chat_usage = {"prompt_tokens": 4, "completion_tokens": 3}
    stream = sdk.chat.completions.create(model="atentina", stream=True, messages=[{"role": "user", "content": "hola"}])
    chunks = list(stream)
    assert "".join(c.choices[0].delta.content or "" for c in chunks if c.choices) == "Hola!"
    assert chunks[-1].usage.completion_tokens == 3

    text = sdk.audio.transcriptions.create(model="atentina", file=("a.wav", b"\0" * 500, "audio/wav"), language="es")
    assert text.text == "hola mundo"

    engines.tts_seconds = 1.0
    speech = sdk.audio.speech.create(model="atentina", voice="sofia", input="Hola", response_format="wav")
    assert speech.content[:4] == b"RIFF" and len(speech.content) == 44 + 48_000

    # TTS en streaming: pcm crudo con with_streaming_response, y los eventos SSE con stream_format.
    engines.tts_seconds = 0.5
    with sdk.audio.speech.with_streaming_response.create(model="atentina", voice="sofia", input="Hola",
                                                         response_format="pcm") as r:
        assert b"".join(r.iter_bytes()) == b"\0\0" * 12_000
    with sdk.audio.speech.with_streaming_response.create(model="atentina", voice="sofia", input="Hola",
                                                         extra_body={"stream_format": "sse"}) as r:
        events = sse_events("".join(r.iter_text()))
    assert events[-1]["type"] == "speech.audio.done" and events[-1]["duration_seconds"] == 0.5

    # 5 + 3 = 8 de 12 tokens de salida; el siguiente sigue entrando y el que lo pasa deja afuera al otro.
    engines.chat_usage = {"prompt_tokens": 1, "completion_tokens": 9}
    sdk.chat.completions.create(model="atentina", messages=[{"role": "user", "content": "hola"}])
    with pytest.raises(openai.RateLimitError) as e:
        sdk.chat.completions.create(model="atentina", messages=[{"role": "user", "content": "hola"}])
    assert e.value.status_code == 429 and e.value.body["code"] == "api_llm_output_tokens"
    with pytest.raises(openai.PermissionDeniedError):
        openai.OpenAI(base_url="http://testserver/api/v1/inference", api_key=make_key(admin, client, ["calls"])
                      ["Authorization"].removeprefix("Bearer "), http_client=api.client, max_retries=0
                      ).chat.completions.create(model="x", messages=[{"role": "user", "content": "hola"}])
