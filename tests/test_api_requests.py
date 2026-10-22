"""Lista de pedidos a la API de inferencia (/api/v1/api-requests): que se anota de cada pedido
(ok, cortado, error, rechazado) y quien ve que (admin: todos; cliente: los suyos)."""
import asyncio

from app.models import ApiRequest

from .test_api import V1, admin, client_user  # noqa: F401  (admin: fixture)
from .test_inference import (  # noqa: F401  (engines: fixture)
    _access,
    _delta,
    _gated_gateway,
    chat,
    engines,
    make_client_with_tier,
    make_key,
    stt,
    tts,
)

URL = f"{V1}/api-requests"


def rows(api) -> list[ApiRequest]:
    with api.sessions() as s:
        return list(s.query(ApiRequest).order_by(ApiRequest.created_at))


def test_each_engine_request_is_logged_with_its_usage(api, admin, engines):
    client = make_client_with_tier(admin)
    key = make_key(admin, client)
    assert chat(api, key).status_code == 200
    assert chat(api, key, stream=True).status_code == 200
    assert stt(api, key).status_code == 200
    assert tts(api, key, voice="martin").status_code == 200
    llm, llm_stream, transcription, speech = rows(api)
    assert (llm.kind, llm.status, llm.stream, llm.input_tokens, llm.output_tokens) == ("llm", "ok", False, 10, 5)
    assert llm_stream.stream and llm_stream.status == "ok" and llm_stream.ttfb_ms is not None
    assert (transcription.kind, transcription.audio_seconds, transcription.input_tokens) == ("stt", 12.5, None)
    assert (speech.kind, speech.voice, speech.response_format, speech.audio_seconds) == ("tts", "martin", "wav", 2.0)
    assert speech.characters == len("Hola, ¿cómo estás?")
    assert all(r.http_status == 200 and r.duration_ms >= 0 and r.api_key_id for r in (llm, transcription, speech))


def test_errors_and_quota_rejections_are_logged_but_not_rate_limits(api, admin, engines):
    client = make_client_with_tier(admin, api_stt_minutes=0, api_rate_limit=3)
    key = make_key(admin, client)
    engines.status = 500
    assert chat(api, key).status_code == 502
    assert tts(api, key, voice="nadie").status_code == 422          # no llega al motor, pero se anota
    assert stt(api, key).status_code == 403                         # el plan no incluye STT
    assert chat(api, key).status_code == 429                        # rate_limited: no se anota
    error, invalid, rejected = rows(api)
    assert (error.status, error.http_status, error.error_code) == ("error", 502, "upstream_error")
    assert (invalid.status, invalid.error_code, invalid.voice) == ("error", "invalid_voice", "nadie")
    assert (rejected.kind, rejected.status, rejected.http_status, rejected.error_code) == \
        ("stt", "rejected", 403, "not_in_plan")
    assert error.input_tokens is None and error.output_tokens is None


def test_a_stream_cut_by_the_client_is_logged_as_cut(api, admin):
    access, _ = _access(api, admin)
    gate = asyncio.Event()
    gateway = _gated_gateway(api, _delta(b"\1\0" * 4800), [_delta(b"\2\0" * 4800)], gate)

    async def run():
        response = await gateway.speech(access, "sofia", "Hola", "pcm")
        chunks = response.body_iterator
        await chunks.__anext__()
        await chunks.aclose()

    asyncio.run(run())
    (row,) = rows(api)
    assert (row.status, row.stream, row.audio_seconds) == ("cut", True, 0.2)   # 9600 bytes de PCM a 48.000 por segundo


def test_admin_sees_all_with_filters_and_client_only_its_own(api, admin, engines):
    acme = make_client_with_tier(admin)
    other = make_client_with_tier(admin, "otra")
    key_a, key_b = make_key(admin, acme, name="crm"), make_key(admin, acme, name="web")
    chat(api, key_a)
    stt(api, key_b)
    tts(api, make_key(admin, other))

    page = admin.get(URL).json()
    assert page["total"] == 3 and {i["client_name"] for i in page["items"]} == {"Acme", "Otra"}
    assert page["summary"]["by_kind"] == {"llm": 1, "stt": 1, "tts": 1}
    assert page["summary"]["input_tokens"] == 10 and page["summary"]["stt_seconds"] == 12.5

    only_acme = admin.get(URL, params={"client_id": acme["id"], "kind": ["llm", "stt"]}).json()
    assert only_acme["total"] == 2
    crm = only_acme["items"][1]
    assert crm["api_key_name"] == "crm" and crm["kind"] == "llm"
    assert admin.get(URL, params={"api_key_id": crm["api_key_id"]}).json()["total"] == 1
    assert admin.get(URL, params={"status": "error"}).json()["total"] == 0
    assert admin.get(URL, params={"date_from": "2020-01-01", "date_to": "2020-01-31"}).json()["total"] == 0

    ana = client_user(api, admin, acme)
    mine = ana.get(URL).json()
    assert mine["total"] == 2 and {i["client_id"] for i in mine["items"]} == {acme["id"]}
    assert ana.get(URL, params={"client_id": other["id"]}).status_code == 403
    assert ana.get(URL, params={"limit": 1}).json()["total"] == 2
