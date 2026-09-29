import datetime

from app.models import CallMode, CallRow, CallStatus, Client, ConversationRow, Tier
from app.services import quota

UTC = datetime.UTC


def naive_utc(*args) -> datetime.datetime:
    """Como guarda la base: UTC sin zona."""
    return datetime.datetime(*args, tzinfo=UTC).replace(tzinfo=None)


def test_month_bounds_in_billing_timezone():
    # 1-oct 01:00 UTC es todavia 30-sep en Buenos Aires (UTC-3).
    start, end = quota.month_bounds(datetime.datetime(2026, 10, 1, 1, 0, tzinfo=UTC))
    assert (start, end) == (naive_utc(2026, 9, 1, 3), naive_utc(2026, 10, 1, 3))
    assert quota.month_bounds(month="2026-12") == (naive_utc(2026, 12, 1, 3), naive_utc(2027, 1, 1, 3))


def _client(s, **limits) -> Client:
    tier = Tier(name="t", **limits)
    client = Client(name="c", slug="c", tier=tier)
    s.add(client)
    s.flush()
    return client


def _call(s, client, mode, status, started_ago=None, duration=0, created_ago=0):
    now = datetime.datetime.now(UTC).replace(tzinfo=None)
    conv = ConversationRow(id=f"c{len(s.new) + s.query(ConversationRow).count()}", client_id=client.id,
                           status="active", fields={}, messages=[])
    s.add(conv)
    s.add(CallRow(conversation_id=conv.id, client_id=client.id, mode=mode, status=status, duration_seconds=duration,
                  started_at=None if started_ago is None else now - datetime.timedelta(seconds=started_ago),
                  created_at=now - datetime.timedelta(seconds=created_ago)))
    s.flush()


def test_running_calls_count_elapsed_time(sessions):
    with sessions() as s:
        c = _client(s, inbound_minutes=10)
        _call(s, c, CallMode.entrante, CallStatus.finalizada, started_ago=500, duration=240)
        _call(s, c, CallMode.entrante, CallStatus.en_curso, started_ago=120)
        _call(s, c, CallMode.saliente, CallStatus.finalizada, started_ago=100, duration=90)
        remaining = quota.remaining_seconds(s, c, CallMode.entrante)
        assert 600 - 240 - 125 <= remaining <= 600 - 240 - 120
        assert quota.remaining_seconds(s, c, CallMode.saliente) is None     # sin tope
        assert quota.remaining_seconds(s, c, CallMode.prueba) is None       # no consume minutos


def test_stale_active_calls_do_not_block(sessions):
    with sessions() as s:
        c = _client(s, max_concurrent_calls=1)
        # Quedo "en curso" hace horas (se cayo el worker): no ocupa lugar.
        _call(s, c, CallMode.prueba, CallStatus.en_curso, started_ago=7200, created_ago=7200)
        assert quota.active_calls(s, c.id) == 0
        assert quota.admit(s, c.id, CallMode.prueba) is None
        _call(s, c, CallMode.prueba, CallStatus.sonando)
        assert quota.active_calls(s, c.id) == 1
