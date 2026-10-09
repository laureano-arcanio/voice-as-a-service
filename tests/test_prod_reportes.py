"""Indicadores y serie diaria agregados en SQL (H09): mismo resultado que el calculo
fila por fila de antes, sin leer mensajes, con rango por defecto y maximo."""
import datetime
import uuid
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from app.agents.definitions import DbDefinitions
from app.db import utcnow
from app.models import CallRow, ConversationRow
from app.services.errors import Invalid
from app.services.reports import CallFilter, Reports, _base_query

from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)

BA = ZoneInfo("America/Argentina/Buenos_Aires")
FULL = {"contact_name": "Ana", "company_name": "Acme", "company_activity": "x", "employee_count": 10,
        "workforce_location": "x", "attendance_process": "x", "main_problem": "x", "desired_timeline": "x",
        "decision_maker": "x", "wants_demo": True, "email": "a@b.com"}


def _add(s, client_id, agent_id, created_at, *, status="active", outcome=None, fields=None, channel="voice",
         call=None, legacy=None, version=1):
    cid = str(uuid.uuid4())
    s.add(ConversationRow(
        id=cid, client_id=client_id, agent_id=agent_id, agent_version=version if agent_id else None,
        legacy_workflow_id=legacy, channel=channel, status=status, fields=fields or {},
        messages=[{"role": "user", "text": "hola " * 50}] * 5,
        progress=None if outcome is False else {"outcome": outcome}, created_at=created_at))
    s.flush()   # sin relationship, PostgreSQL necesita la conversacion antes que la llamada
    if call:
        mode, st, secs, lat = call
        s.add(CallRow(conversation_id=cid, client_id=client_id, mode=mode, status=st, duration_seconds=secs,
                      latency=None if lat is None else {"turns": [{"x": 1}] * 20,
                                                        "stats": {"total": {"avg": lat, "p95": lat}}},
                      created_at=created_at))
    return cid


@pytest.fixture
def data(api, admin):  # noqa: F811
    c, other = make_client(admin, "acme"), make_client(admin, "otro")
    agent, other_agent = make_agent(admin, c), make_agent(admin, other)
    now = utcnow()
    sep = lambda d, h: datetime.datetime(2026, 8, d, h, 0, tzinfo=datetime.UTC).replace(tzinfo=None)
    with api.sessions() as s:
        a, cl = agent["id"], c["id"]
        for t in (now - datetime.timedelta(hours=1), sep(10, 15)):
            _add(s, cl, a, t, status="completed", outcome="demo", fields=FULL, call=("saliente", "finalizada", 120, 1.5))
            _add(s, cl, a, t, status="completed", outcome="no_demo", call=("entrante", "finalizada", 61, 2.25))
            _add(s, cl, a, t, call=("saliente", "fallida", 0, None))
            _add(s, cl, a, t, call=("entrante", "rechazada", 0, None))
            # Anterior a progress.outcome: el resultado sale de los datos.
            _add(s, cl, a, t, status="completed", outcome=False, fields=FULL, call=("prueba", "finalizada", 30, None))
            _add(s, cl, a, t, status="completed", outcome="demo", fields=FULL)               # texto (api)
            _add(s, cl, a, t, channel="whatsapp", status="completed", outcome="no_demo")
            # Plantilla vieja con un resultado que ya no existe; y una version inexistente.
            _add(s, cl, None, t, status="completed", outcome="renombrado", legacy="sales_discovery", fields=FULL)
            _add(s, cl, a, t, status="completed", outcome="demo", version=99)
            _add(s, other["id"], other_agent["id"], t, status="completed", outcome="demo",
                 call=("saliente", "finalizada", 300, 4.0))
        # Agosto: fuera de los ultimos 30 dias. Bordes de dia en Buenos Aires (UTC-3).
        _add(s, cl, a, sep(11, 2), status="completed", outcome="demo", fields=FULL)      # 10-sep local
        _add(s, cl, a, sep(12, 3), call=("loadtest", "finalizada", 10, 0.5))             # 12-sep local
        _add(s, cl, a, now - datetime.timedelta(days=45), call=("saliente", "finalizada", 999, 9.0))
        s.commit()
    return c, agent, other


def _reference(api, flt: CallFilter) -> tuple[dict, dict | None]:
    """El calculo de antes: un resumen por fila (con entidades completas) y sumas en Python."""
    with api.sessions() as s:
        r = Reports(s, DbDefinitions(api.sessions))
        rows = []
        for conv, call, an, cn, th, bn in s.execute(_base_query().where(*flt.where())).all():
            lat = (call.latency or {}).get("stats", {}).get("total") if call else None
            rows.append(r.summary(conv, call, an, cn, th, bn, lat["avg"] if lat else None))
    phone = [x for x in rows if x["mode"] not in ("api", "whatsapp")]
    done = [x for x in phone if x["status"] == "finalizada"]
    completed = [x for x in rows if x["workflow_status"] == "completed"]
    goal = [x for x in rows if x["goal"]]
    lats = [x["latency_avg"] for x in done if x["latency_avg"] is not None]
    pct = lambda n, d: round(100 * n / d, 1) if d else 0
    stats = {
        "total": len(rows), "calls": len(phone), "finished": len(done),
        "failed": sum(x["status"] == "fallida" for x in phone),
        "rejected": sum(x["status"] == "rechazada" for x in phone),
        "completed": len(completed), "completed_pct": pct(len(completed), len(rows)),
        "goal": len(goal), "goal_pct": pct(len(goal), len(rows)),
        "total_minutes": round(sum(x["duration_seconds"] for x in done) / 60, 1),
        "avg_duration": round(sum(x["duration_seconds"] for x in done) / len(done)) if done else 0,
        "latency_avg": round(sum(lats) / len(lats), 2) if lats else None,
        "whatsapp": sum(x["mode"] == "whatsapp" for x in rows),
    }
    if not (flt.date_from and flt.date_to):
        return stats, None
    days = [flt.date_from + datetime.timedelta(d) for d in range((flt.date_to - flt.date_from).days + 1)]
    buckets = {d: [] for d in days}
    for x in rows:
        dt = datetime.datetime.fromisoformat(x["created_at"].rstrip("Z")).replace(tzinfo=datetime.UTC)
        buckets[dt.astimezone(flt.tz).date()].append(x)
    p = lambda b, k: round(100 * sum(k(x) for x in b) / len(b), 1) if b else None
    return stats, {
        "labels": [d.isoformat() for d in days], "totals": [len(buckets[d]) for d in days],
        "completed_pct": [p(buckets[d], lambda x: x["workflow_status"] == "completed") for d in days],
        "goal_pct": [p(buckets[d], lambda x: x["goal"]) for d in days],
    }


def test_stats_match_row_by_row(api, admin, data):  # noqa: F811
    c, agent, _ = data
    today = datetime.datetime.now(BA).date()
    q = {"tz": "America/Argentina/Buenos_Aires"}
    for params, flt in [
        ({"client_id": c["id"]}, CallFilter(client_id=c["id"], tz=BA,
                                            date_from=today - datetime.timedelta(29), date_to=today)),
        ({}, CallFilter(tz=BA, date_from=today - datetime.timedelta(29), date_to=today)),
        ({"client_id": c["id"], "date_from": "2026-08-01", "date_to": "2026-08-30"},
         CallFilter(client_id=c["id"], tz=BA, date_from=datetime.date(2026, 8, 1), date_to=datetime.date(2026, 8, 30))),
        ({"agent_id": agent["id"], "date_from": "2026-08-10", "date_to": "2026-08-12"},
         CallFilter(agent_id=agent["id"], tz=BA, date_from=datetime.date(2026, 8, 10),
                    date_to=datetime.date(2026, 8, 12))),
    ]:
        expected, _ = _reference(api, flt)
        got = admin.get(f"{V1}/stats", params={**q, **params}).json()
        assert got == expected, params
    # El de los ultimos 30 dias tiene de todo: cuenta lo esperado, no solo lo mismo.
    got = admin.get(f"{V1}/stats", params={**q, "client_id": c["id"]}).json()
    assert (got["total"], got["calls"], got["finished"], got["failed"], got["rejected"]) == (9, 5, 3, 1, 1)
    assert got["whatsapp"] == 1 and got["goal"] == 4 and got["latency_avg"] == 1.88
    assert got["total_minutes"] == round(211 / 60, 1) and got["avg_duration"] == 70


def test_daily_matches_row_by_row(api, admin, data):  # noqa: F811
    c, _, _ = data
    for tz in ("America/Argentina/Buenos_Aires", "UTC", "Asia/Kathmandu"):
        flt = CallFilter(client_id=c["id"], tz=ZoneInfo(tz), date_from=datetime.date(2026, 8, 8),
                         date_to=datetime.date(2026, 8, 13))
        _, expected = _reference(api, flt)
        got = admin.get(f"{V1}/stats/daily", params={"client_id": c["id"], "tz": tz, "date_from": "2026-08-08",
                                                     "date_to": "2026-08-13"}).json()
        assert got == expected, tz
    ba = admin.get(f"{V1}/stats/daily", params={"client_id": c["id"], "date_from": "2026-08-10",
                                                "date_to": "2026-08-12",
                                                "tz": "America/Argentina/Buenos_Aires"}).json()
    assert ba["totals"] == [10, 0, 1] and ba["goal_pct"][1] is None


def test_stats_and_daily_do_not_read_messages(api, admin, data):  # noqa: F811
    c, _, _ = data
    sql: list[str] = []
    engine = api.sessions.kw["bind"]
    listener = lambda conn, cur, statement, *a: sql.append(statement)
    event.listen(engine, "before_cursor_execute", listener)
    try:
        admin.get(f"{V1}/stats", params={"client_id": c["id"]})
        admin.get(f"{V1}/stats/daily", params={"client_id": c["id"], "date_from": "2026-08-01",
                                               "date_to": "2026-08-30"})
        admin.get(f"{V1}/calls", params={"client_id": c["id"]})
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    report_sql = [q for q in sql if "conversations" in q and "call_logs" in q]
    assert report_sql
    assert not any("conversations.messages" in q for q in report_sql)
    # La latencia de la llamada se lee con su ruta, no el documento con los turnos.
    assert not any("call_logs.latency AS" in q for q in report_sql)


def test_list_latency_from_sql(api, admin, data):  # noqa: F811
    c, _, _ = data
    items = admin.get(f"{V1}/calls", params={"client_id": c["id"], "mode": "saliente"}).json()["items"]
    assert sorted(i["latency_avg"] or 0 for i in items) == [0, 0, 1.5, 1.5, 9.0]
    assert all(i["mode"] == "saliente" for i in items)


def test_range_default_and_max(api, admin, data):  # noqa: F811
    c, _, _ = data
    # Sin fechas: ultimos 30 dias (la de hace 45 no cuenta).
    assert admin.get(f"{V1}/stats", params={"client_id": c["id"]}).json()["total"] == 9
    old = (datetime.datetime.now(BA).date() - datetime.timedelta(days=50)).isoformat()
    assert admin.get(f"{V1}/stats", params={"client_id": c["id"], "date_from": old}).json()["total"] == 10
    too_long = {"client_id": c["id"], "date_from": "2025-01-01", "date_to": "2026-09-30"}
    r = admin.get(f"{V1}/stats", params=too_long)
    assert r.status_code == 422
    assert admin.get(f"{V1}/stats/daily", params=too_long).status_code == 422
    reversed_ = {"date_from": "2026-09-30", "date_to": "2026-09-01"}
    assert admin.get(f"{V1}/stats", params=reversed_).status_code == 422


def test_bounded_fills_dates():
    today = datetime.datetime.now(BA).date()
    f = CallFilter(tz=BA).bounded()
    assert (f.date_to, (f.date_to - f.date_from).days) == (today, 29)
    f = CallFilter(tz=BA, date_to=datetime.date(2026, 8, 30)).bounded()
    assert f.date_from == datetime.date(2026, 8, 1)
    f = CallFilter(tz=BA, date_from=today + datetime.timedelta(5)).bounded()
    assert f.date_to == f.date_from
    with pytest.raises(Invalid):
        CallFilter(date_from=datetime.date(2024, 1, 1), date_to=datetime.date(2026, 1, 1)).bounded()
