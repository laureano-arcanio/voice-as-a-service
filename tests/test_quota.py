import datetime

import pytest

from app.models import CallMode, CallRow, CallStatus, Client, ConversationRow, Tier
from app.services import quota
from app.services.errors import QuotaExceeded

UTC = datetime.UTC


def naive_utc(*args) -> datetime.datetime:
    """Como guarda la base: UTC sin zona."""
    return datetime.datetime(*args, tzinfo=UTC).replace(tzinfo=None)


def test_month_bounds_in_billing_timezone():
    # 1-oct 01:00 UTC es todavia 30-sep en Buenos Aires (UTC-3).
    start, end = quota.month_bounds(datetime.datetime(2026, 10, 1, 1, 0, tzinfo=UTC))
    assert (start, end) == (naive_utc(2026, 9, 1, 3), naive_utc(2026, 10, 1, 3))
    assert quota.month_bounds(month="2026-12") == (naive_utc(2026, 12, 1, 3), naive_utc(2027, 1, 1, 3))


def _client(s, slug="c", **limits) -> Client:
    tier = Tier(name=f"t-{slug}", **limits)
    client = Client(name=slug, slug=slug, tier=tier)
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


def test_period_start_in_billing_timezone():
    # 15-oct 15:45 UTC = 12:45 en Buenos Aires (UTC-3).
    now = naive_utc(2026, 10, 15, 15, 45)
    assert quota.period_start("hour", now) == naive_utc(2026, 10, 15, 15)
    assert quota.period_start("day", now) == naive_utc(2026, 10, 15, 3)
    assert quota.period_start("month", now) == naive_utc(2026, 10, 1, 3)
    # 02:30 UTC todavia es el dia anterior (23:30) en Buenos Aires.
    assert quota.period_start("day", naive_utc(2026, 10, 15, 2, 30)) == naive_utc(2026, 10, 14, 3)


def test_call_count_limits_cut_by_hour_and_day(sessions):
    with sessions() as s:
        c = _client(s, max_calls_per_hour=2, max_calls_per_day=3)
        _call(s, c, CallMode.entrante, CallStatus.finalizada, created_ago=60)
        _call(s, c, CallMode.saliente, CallStatus.fallida, created_ago=120)
        # No cuentan: rechazada por el tier, prueba y loadtest.
        _call(s, c, CallMode.entrante, CallStatus.rechazada, created_ago=30)
        _call(s, c, CallMode.prueba, CallStatus.finalizada, created_ago=30)
        _call(s, c, CallMode.loadtest, CallStatus.finalizada, created_ago=30)
        with pytest.raises(QuotaExceeded) as e:
            quota.admit(s, c.id, CallMode.entrante)
        assert e.value.code == "calls_per_hour"
        # Las de prueba y el loadtest no tienen este tope.
        assert quota.admit(s, c.id, CallMode.prueba) is None


def test_call_count_limit_per_day_ignores_older_days(sessions):
    with sessions() as s:
        c = _client(s, max_calls_per_day=1, max_calls_per_month=2)
        _call(s, c, CallMode.entrante, CallStatus.finalizada, created_ago=3 * 86400)   # hace 3 dias
        # Con la de hace 3 dias no se pasa del dia; si cae en el mes, ya hay 1 de 2.
        _call(s, c, CallMode.saliente, CallStatus.finalizada, created_ago=10)
        with pytest.raises(QuotaExceeded) as e:
            quota.admit(s, c.id, CallMode.saliente)
        assert e.value.code == "calls_per_day"


def test_call_count_limit_per_month_and_unlimited(sessions):
    with sessions() as s:
        c = _client(s, max_calls_per_month=1)
        assert quota.admit(s, c.id, CallMode.entrante) is None
        _call(s, c, CallMode.entrante, CallStatus.finalizada, created_ago=0)
        with pytest.raises(QuotaExceeded) as e:
            quota.admit(s, c.id, CallMode.saliente)
        assert e.value.code == "calls_per_month"
        free = _client(s, "unl")
        for _ in range(3):
            _call(s, free, CallMode.entrante, CallStatus.finalizada)
        assert quota.admit(s, free.id, CallMode.entrante) is None     # NULL = ilimitado


def test_usage_reports_call_counts(sessions):
    with sessions() as s:
        c = _client(s, max_calls_per_hour=20)
        _call(s, c, CallMode.entrante, CallStatus.finalizada, created_ago=10)
        _call(s, c, CallMode.prueba, CallStatus.finalizada, created_ago=10)
        u = quota.usage(s, c)
        assert (u.calls_hour.used, u.calls_hour.limit) == (1, 20)
        assert u.calls_day.limit is None and u.calls_month.used == 1
