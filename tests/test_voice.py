from app import config, livekit_agent, voices
from app.conversation.workflow import WORKFLOWS_DIR, load_workflow


async def resolve(monkeypatch, served):
    async def fake():
        return served
    monkeypatch.setattr(livekit_agent, "served_voices", fake)
    monkeypatch.setattr(config, "VLLM_TTS_VOICE", "arf_03034")
    return await livekit_agent.resolve_voice("berlin_signup")


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
    assert await livekit_agent.resolve_voice("berlin_signup", "martin") == "martin"


def test_catalog_has_41_voices_with_metrics():
    cat = voices.catalog()
    assert len(cat) == 41
    assert all(v.genero in ("mujer", "hombre") and v.wer is not None and v.car_s is not None for v in cat.values())
    # Cada voz de un workflow tiene que estar en el catalogo (y en el checkpoint servido).
    assert all(load_workflow(p.stem).agent.voice in cat for p in WORKFLOWS_DIR.glob("*.yml"))


def test_search_filters_and_sorts():
    found = voices.search(genero="hombre", wer_max=3, car_min=15, car_max=18)
    assert found and all(v["genero"] == "hombre" and v["wer"] <= 3 and 15 <= v["car_s"] <= 18 for v in found)
    assert [v["wer"] for v in found] == sorted(v["wer"] for v in found)
    assert voices.search(wer_max=0) == []
