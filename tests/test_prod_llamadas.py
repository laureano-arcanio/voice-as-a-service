"""Ciclo de llamada y capacidad de voz (revision de produccion del 7-oct-2026): tope de
duracion por tier en todas las modalidades (H02), tope global y reserva para entrantes
(H04), llamadas colgadas, conciliacion con LiveKit, voz por defecto y frase de respaldo
ante error del LLM."""
import asyncio
import datetime
import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.models import CallMode, CallRow, CallStatus, Client, ConversationRow, Tier
from app.services import quota, reconcile
from app.services.errors import QuotaExceeded
from app.voice import worker

UTC = datetime.UTC


def _now() -> datetime.datetime:
    return datetime.datetime.now(UTC).replace(tzinfo=None)


def _client(s, slug="c", **limits) -> Client:
    client = Client(name=slug, slug=slug, tier=Tier(name=f"t-{slug}", **limits))
    s.add(client)
    s.flush()
    return client


def _call(s, client, mode=CallMode.prueba, status=CallStatus.en_curso, started_ago=None, created_ago=0,
          duration=0, updated_ago=None) -> str:
    now = _now()
    conv_id = f"c{s.query(ConversationRow).count() + 1}"
    conv = ConversationRow(id=conv_id, client_id=client.id if client else None, status="active", fields={},
                           messages=[])
    if updated_ago is not None:
        conv.updated_at = now - datetime.timedelta(seconds=updated_ago)
    s.add(conv)
    s.flush()
    s.add(CallRow(conversation_id=conv_id, client_id=client.id if client else None, mode=mode, status=status,
                  duration_seconds=duration,
                  started_at=None if started_ago is None else now - datetime.timedelta(seconds=started_ago),
                  created_at=now - datetime.timedelta(seconds=created_ago)))
    s.flush()
    return conv_id


# ---------- H02: tope de duracion ----------

def test_inbound_unlimited_tier_is_capped_at_tier_max(sessions, monkeypatch):
    monkeypatch.setattr(settings, "call_duration_ceiling_seconds", 3600)
    with sessions() as s:
        # Tier sin limites de minutos ni de concurrencia: igual corta al tope del tier.
        c = _client(s, max_call_duration_seconds=120)
        call = _call(s, c, CallMode.entrante, started_ago=0)
        assert quota.call_limit_seconds(s, call) == 120
        # El del pedido (max_duration_seconds de la API) puede bajarlo, no subirlo.
        assert quota.call_limit_seconds(s, call, requested=60) == 60
        assert quota.call_limit_seconds(s, call, requested=600) == 120


def test_call_limit_defaults_and_ceiling(sessions, monkeypatch):
    monkeypatch.setattr(settings, "call_max_duration_seconds", 900)
    monkeypatch.setattr(settings, "call_duration_ceiling_seconds", 1800)
    with sessions() as s:
        default = _client(s, "default")
        huge = _client(s, "huge", max_call_duration_seconds=7200)
        assert quota.call_limit_seconds(s, _call(s, default, CallMode.loadtest)) == 900
        assert quota.call_limit_seconds(s, _call(s, huge, CallMode.prueba)) == 1800   # techo de SIP/Asterisk


def test_call_limit_includes_remaining_minutes(sessions):
    with sessions() as s:
        c = _client(s, inbound_minutes=10, max_call_duration_seconds=1200)
        _call(s, c, CallMode.entrante, CallStatus.finalizada, started_ago=900, duration=500)
        call = _call(s, c, CallMode.entrante, started_ago=0)
        assert 99 <= quota.call_limit_seconds(s, call) <= 100


async def test_guard_cuts_at_limit_without_quota():
    cuts = []

    async def no_limit():
        return None

    async def cut(reason):
        cuts.append(reason)

    await asyncio.wait_for(worker.guard_call("x", 0.05, no_limit, cut, check_seconds=0.01), 2)
    assert cuts == ["max_duration"]


async def test_guard_survives_db_error():
    calls = 0
    cuts = []

    async def flaky():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("could not connect to server")
        return 0

    async def cut(reason):
        cuts.append(reason)

    await asyncio.wait_for(worker.guard_call("x", 60, flaky, cut, check_seconds=0.01), 2)
    assert calls == 2
    assert cuts == ["quota_exhausted"]


# ---------- llamadas colgadas ----------

def test_stale_running_call_keeps_counting_up_to_max(sessions, monkeypatch):
    monkeypatch.setattr(settings, "call_max_duration_seconds", 900)
    with sessions() as s:
        c = _client(s, inbound_minutes=100, max_concurrent_calls=1)
        # Quedo "en curso" hace 2 h (se cayo el worker): no ocupa lugar, pero consume el tope.
        _call(s, c, CallMode.entrante, started_ago=7200, created_ago=7200)
        assert quota.active_calls(s, c.id) == 0
        start, end = quota.month_bounds()
        assert quota.used_seconds(s, c.id, CallMode.entrante, start, end) == 900
        assert quota.remaining_seconds(s, c, CallMode.entrante) == 6000 - 900


def test_active_window_counts_from_started_at(sessions, monkeypatch):
    monkeypatch.setattr(settings, "call_max_duration_seconds", 900)
    with sessions() as s:
        c = _client(s)
        # Creada hace 30 min (espero a que alguien entre a la de prueba), arranco hace 10 s.
        _call(s, c, CallMode.prueba, started_ago=10, created_ago=1800)
        assert quota.active_calls(s, c.id) == 1
        assert quota.active_calls_global(s) == 1


def test_stale_window_uses_tier_max(sessions, monkeypatch):
    monkeypatch.setattr(settings, "call_duration_ceiling_seconds", 7200)
    with sessions() as s:
        long_tier = _client(s, "long", max_call_duration_seconds=3600)
        short_tier = _client(s, "short", max_call_duration_seconds=60)
        _call(s, long_tier, started_ago=2000)     # dentro de 3600 + margen: activa
        _call(s, short_tier, started_ago=2000)    # paso 60 + margen: colgada
        assert quota.active_calls(s, long_tier.id) == 1
        assert quota.active_calls(s, short_tier.id) == 0
        assert quota.active_calls_global(s) == 1


# ---------- H04: tope global ----------

def test_global_admission_across_clients(sessions, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_calls_global", 3)
    monkeypatch.setattr(settings, "inbound_reserve_calls", 0)
    with sessions() as s:
        a = _client(s, "a")
        b = _client(s, "b")      # sin limites en su tier
        _call(s, a, started_ago=10)
        _call(s, a, CallMode.saliente, CallStatus.sonando)
        _call(s, b, CallMode.entrante, CallStatus.finalizada, started_ago=100, duration=50)   # terminada: no cuenta
        assert quota.admit(s, b.id, CallMode.prueba) is None
        _call(s, b, CallMode.entrante, CallStatus.pendiente)
        with pytest.raises(QuotaExceeded) as e:
            quota.admit(s, b.id, CallMode.entrante)
        assert e.value.code == "platform_busy"
        with pytest.raises(QuotaExceeded) as e:
            quota.admit(s, a.id, CallMode.saliente)
        assert e.value.code == "platform_busy"


def test_inbound_reserve(sessions, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_calls_global", 3)
    monkeypatch.setattr(settings, "inbound_reserve_calls", 1)
    with sessions() as s:
        c = _client(s)
        _call(s, c, started_ago=5)
        _call(s, c, CallMode.loadtest, started_ago=5)
        # Quedan 1 lugar, reservado para entrantes.
        for mode in (CallMode.saliente, CallMode.prueba, CallMode.loadtest):
            with pytest.raises(QuotaExceeded) as e:
                quota.admit(s, c.id, mode)
            assert e.value.code == "platform_busy"
        assert quota.admit(s, c.id, CallMode.entrante) is None


def test_tier_limit_reported_before_global(sessions, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_calls_global", 1)
    with sessions() as s:
        c = _client(s, max_concurrent_calls=1)
        _call(s, c, started_ago=5)
        with pytest.raises(QuotaExceeded) as e:
            quota.admit(s, c.id, CallMode.entrante)
        assert e.value.code == "concurrency_limit"


# ---------- conciliacion con LiveKit ----------

class FakeLiveKit:
    def __init__(self, rooms=None, error=None):
        self.rooms, self.error = rooms or [], error
        self.room = self

    async def list_rooms(self, req):
        if self.error:
            raise self.error
        return SimpleNamespace(rooms=self.rooms)


def _room(name, metadata="", age=300):
    return SimpleNamespace(name=name, metadata=metadata,
                           creation_time=int(datetime.datetime.now(UTC).timestamp()) - age)


async def test_reconcile_closes_calls_without_room(sessions):
    with sessions() as s:
        c = _client(s, max_call_duration_seconds=600)
        live_out = _call(s, c, CallMode.saliente, started_ago=200, created_ago=300)
        live_in = _call(s, c, CallMode.entrante, started_ago=200, created_ago=300)
        gone = _call(s, c, CallMode.prueba, started_ago=500, created_ago=500, updated_ago=380)
        gone_long = _call(s, c, CallMode.entrante, started_ago=5000, created_ago=5000, updated_ago=0)
        never = _call(s, c, CallMode.saliente, CallStatus.sonando, created_ago=400)
        fresh = _call(s, c, CallMode.prueba, CallStatus.pendiente, created_ago=10)
        done = _call(s, c, CallMode.prueba, CallStatus.finalizada, started_ago=900, created_ago=900, duration=30)
        s.commit()
    lk = FakeLiveKit([_room(f"call-{live_out}"), _room("anura-abc", reconcile.room_metadata(live_in)),
                      _room("otra-room", "no es json")])
    lk.rooms[-1].creation_time = int(datetime.datetime.now(UTC).timestamp())    # sin marcar, pero nueva
    closed = await reconcile.reconcile_once(sessions, lk)
    assert sorted(closed) == sorted([gone, gone_long, never])
    with sessions() as s:
        rows = {r.conversation_id: r for r in s.query(CallRow)}
        for cid in (live_out, live_in, fresh):
            assert rows[cid].status in (CallStatus.en_curso, CallStatus.pendiente)
        assert rows[done].duration_seconds == 30
        # Hasta el ultimo guardado de la conversacion (500 - 380 s).
        assert rows[gone].status == CallStatus.finalizada and rows[gone].ended_reason == "room_gone"
        assert 119 <= rows[gone].duration_seconds <= 121
        # Nunca mas que el tope del tier.
        assert rows[gone_long].duration_seconds == 600
        assert rows[never].status == CallStatus.fallida and rows[never].duration_seconds == 0
    # Segunda pasada: nada nuevo.
    assert await reconcile.reconcile_once(sessions, lk) == []


async def test_reconcile_skips_inbound_while_untagged_room(sessions):
    with sessions() as s:
        c = _client(s)
        inbound = _call(s, c, CallMode.entrante, started_ago=200, created_ago=300)
        test_call = _call(s, c, CallMode.prueba, started_ago=200, created_ago=300)
        s.commit()
    # Una entrante vieja que el worker no pudo marcar: puede ser cualquiera de las entrantes.
    closed = await reconcile.reconcile_once(sessions, FakeLiveKit([_room("anura-xyz", age=200)]))
    assert closed == [test_call]
    with sessions() as s:
        assert s.get(CallRow, inbound).status == CallStatus.en_curso


async def test_reconcile_does_nothing_if_livekit_fails(sessions):
    with sessions() as s:
        c = _client(s)
        cid = _call(s, c, started_ago=500, created_ago=500)
        s.commit()
    with pytest.raises(ConnectionError):
        await reconcile.reconcile_once(sessions, FakeLiveKit(error=ConnectionError("livekit caido")))
    with sessions() as s:
        assert s.get(CallRow, cid).status == CallStatus.en_curso


async def test_reconcile_loop_survives_errors(sessions):
    lk = FakeLiveKit(error=ConnectionError("livekit caido"))
    task = asyncio.create_task(reconcile.reconcile_loop(sessions, lk, interval=0.01))
    await asyncio.sleep(0.05)
    assert not task.done()
    task.cancel()


def test_room_conversation():
    assert reconcile.room_conversation(_room("call-abc")) == "abc"
    assert reconcile.room_conversation(_room("anura-1", json.dumps({"conversation_id": "x"}))) == "x"
    assert reconcile.room_conversation(_room("anura-1", "")) is None
    assert reconcile.room_conversation(_room("anura-1", "[1]")) is None


# ---------- voz por defecto y respaldo del LLM ----------

async def test_default_voice_must_be_served(monkeypatch):
    monkeypatch.setattr(settings, "vllm_tts_voice", "sofia")

    async def served(voices):
        return voices

    monkeypatch.setattr(worker, "served_voices", lambda: served({"martin"}))
    with pytest.raises(RuntimeError):
        await worker.check_default_voice()
    monkeypatch.setattr(worker, "served_voices", lambda: served({"sofia"}))
    await worker.check_default_voice()
    monkeypatch.setattr(worker, "served_voices", lambda: served(None))    # TTS caido: solo avisa
    await worker.check_default_voice()


async def test_resolve_voice_never_sends_default(monkeypatch):
    from app.agents.templates import load_reference

    async def unreachable():
        return None

    monkeypatch.setattr(worker, "served_voices", unreachable)
    monkeypatch.setattr(settings, "vllm_tts_voice", "sofia")
    assert await worker.resolve_voice(load_reference("berlin_signup"), "default") == "sofia"


async def test_llm_error_says_fallback_phrase(monkeypatch):
    class BrokenEngine:
        async def process_turn(self, conversation_id, text, on_message=None):
            raise RuntimeError("400: maximum context length exceeded")

    agent = worker.WorkflowAgent(BrokenEngine(), "conv-1", latency=None, on_completed=lambda: None)
    chat_ctx = SimpleNamespace(items=[SimpleNamespace(role="user", text_content="hola", id="m1")])
    out = [chunk async for chunk in agent.llm_node(chat_ctx, [], None)]
    assert out == [settings.voice_llm_error_reply]
    # El mensaje no quedo consumido: entra de nuevo en el turno siguiente.
    assert agent.consumed == set()
