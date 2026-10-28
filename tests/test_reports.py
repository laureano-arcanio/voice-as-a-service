"""Reportes (docs/REPORTES_PLAN.md, 9.2): /api/v1/reports/* con datos sembrados en la base."""
import datetime
import uuid

import pytest

from app.models import (
    BillingPayment,
    CallRow,
    Campaign,
    CampaignContact,
    Client,
    Contact,
    ContactOptout,
    ConversationRow,
    Event,
    HandoffArea,
    HandoffLeg,
    PhoneNumber,
    Subscription,
    TeamMember,
    ToolRun,
    WaAccount,
    WaAccountStatusLog,
    WaMessage,
    WaThread,
)
from app.services import report_stats

from .test_api import V1, admin, client_user, make_agent, make_client, make_tier  # noqa: F401  (admin: fixture)

PERIOD = {"date_from": "2026-10-01", "date_to": "2026-10-10", "tz": "UTC"}
NOW = datetime.datetime(2026, 10, 12, 12, 0)
T = lambda day, h, m=0: datetime.datetime(2026, 10, day, h, m)   # noqa: E731


def conv(s, client_id, agent_id, at, *, channel="voice", mode="entrante", status="finalizada", duration=0,
         conversion=None, goal=None, outcome=None, phone=None, ended_reason="", line=None, latency=None,
         messages=(), fields=None, cc=None, **call) -> str:
    """Una conversacion con su llamada (mode None: sin llamada, por API o WhatsApp)."""
    cid = str(uuid.uuid4())
    s.add(ConversationRow(id=cid, client_id=client_id, agent_id=agent_id, agent_version=1, channel=channel,
                          status="completed" if conversion == "complete" else "active", fields=fields or {},
                          messages=list(messages), progress={}, outcome=outcome, goal=goal, conversion=conversion,
                          created_at=at, **{k: call.pop(k) for k in ("llm_input_tokens", "llm_output_tokens")
                                            if k in call}))
    s.flush()
    if mode is not None:
        started = at if status == "finalizada" else None
        s.add(CallRow(conversation_id=cid, client_id=client_id, mode=mode, status=status, phone=phone,
                      phone_number_id=line, duration_seconds=duration, ended_reason=ended_reason, latency=latency,
                      started_at=started, ended_at=started + datetime.timedelta(seconds=duration) if started else None,
                      campaign_contact_id=cc, created_at=at, **call))
    return cid


def turn(provider, ms, error=None):
    trace = {"kind": "turno", "ms": ms, "provider": provider, "model": f"{provider}-m"}
    if error:
        trace["error"] = error
    return [{"role": "user", "text": "hola"},
            {"role": "assistant", "text": "sí", "llm": [trace, {"kind": "herramienta", "ms": 5}]}]


@pytest.fixture
def data(api, admin, monkeypatch):
    monkeypatch.setattr(report_stats, "utcnow", lambda: NOW)
    acme = make_client(admin, "acme", tier=make_tier(admin, name="Free", price_ars=0, inbound_minutes=100))
    beta = make_client(admin, "beta", tier=make_tier(admin, name="Pago", price_ars=29000, inbound_minutes=1,
                                                     advanced_reports=True))
    zeta = make_client(admin, "zeta", tier=make_tier(admin, name="Otro", inbound_minutes=10))
    a, b = make_agent(admin, acme)["id"], make_agent(admin, beta)["id"]
    ids = {"acme": acme["id"], "beta": beta["id"], "zeta": zeta["id"], "agent_a": a, "agent_b": b}
    with api.sessions() as s:
        line = PhoneNumber(client_id=acme["id"], e164="+541152630861", agent_id=a)
        s.add(line)
        s.flush()
        ids["line"] = line.id
        ac = acme["id"]
        c1 = conv(s, ac, a, T(2, 10), duration=120, conversion="complete", goal=True, outcome="demo",
                  phone="+5493510000001", ended_reason="customer_hangup", line=line.id,
                  latency={"turns": [{"total": 1.0, "stt": 0.1}, {"total": 2.0, "stt": 0.3}]},
                  messages=turn("local", 100) + [{"role": "user", "text": "chau"}],
                  fields={"contact_name": "Ana", "company_name": "X"}, summary_email="failed",
                  llm_input_tokens=100, llm_output_tokens=20)
        c2 = conv(s, ac, a, T(2, 11, 30), duration=10, conversion="partial", phone="+5493510000001",
                  ended_reason="completed", line=line.id, messages=turn("openrouter", 300, "boom"),
                  fields={"contact_name": "Beto", "company_name": ""})
        c3 = conv(s, ac, a, T(3, 9), channel="whatsapp", mode=None, conversion="empty")
        conv(s, ac, a, T(4, 15), mode="web", duration=60, conversion="complete", goal=False)
        conv(s, ac, a, T(5, 10), mode="prueba", duration=30)
        conv(s, ac, a, T(5, 11), mode="loadtest", duration=30)
        conv(s, ac, a, T(6, 10), status="rechazada", ended_reason="inbound_minutes", phone="+5493510000003")
        conv(s, ac, a, T(6, 12), mode=None)
        conv(s, ac, a, datetime.datetime(2026, 9, 25, 10), duration=30, phone="+5493510000003")
        # Derivaciones: c1 pedida y atendida (Juan atiende a los 10 s; Pedro no atendio), c2 sin disponibilidad.
        area = HandoffArea(client_id=ac, name="Ventas")
        juan, pedro = TeamMember(client_id=ac, name="Juan"), TeamMember(client_id=ac, name="Pedro")
        s.add_all([area, juan, pedro])
        s.flush()
        s.add_all([
            Event(client_id=ac, type="handoff.requested", conversation_id=c1, area_id=area.id, at=T(2, 10, 1)),
            Event(client_id=ac, type="handoff.connected", conversation_id=c1, area_id=area.id, at=T(2, 10, 2)),
            Event(client_id=ac, type="handoff.unavailable", conversation_id=c2, area_id=area.id, at=T(2, 11, 31)),
            HandoffLeg(client_id=ac, conversation_id=c1, area_id=area.id, team_member_id=pedro.id, phone="+5491100000001",
                       result="no_answer", created_at=T(2, 10, 1), ended_at=T(2, 10, 1)),
            HandoffLeg(client_id=ac, conversation_id=c1, area_id=area.id, team_member_id=juan.id, phone="+5491100000002",
                       result="connected", created_at=datetime.datetime(2026, 10, 2, 10, 1, 30),
                       answered_at=datetime.datetime(2026, 10, 2, 10, 1, 40), connected_at=T(2, 10, 2),
                       ended_at=T(2, 10, 3), billed_seconds=60),
        ])
        # WhatsApp: c3 con 2 entrantes (una nota de voz), una saliente entregada y una fallida.
        acc = WaAccount(client_id=ac, agent_id=a, phone_number_id="111", waba_id="222",
                        display_phone_number="+54 9 351 000-0000", quality_rating="GREEN")
        s.add(acc)
        s.flush()
        s.add_all([
            WaThread(conversation_id=c3, account_id=acc.id, client_id=ac, wa_id="5493510000002", created_at=T(3, 9)),
            WaMessage(account_id=acc.id, conversation_id=c3, direction="in", wa_id="5493510000002", type="text",
                      status="answered", created_at=T(3, 9)),
            WaMessage(account_id=acc.id, conversation_id=c3, direction="in", wa_id="5493510000002", type="audio",
                      status="answered", created_at=T(3, 9, 5)),
            WaMessage(account_id=acc.id, conversation_id=c3, direction="out", wa_id="5493510000002", type="text",
                      status="delivered", created_at=T(3, 9, 1)),
            WaMessage(account_id=acc.id, conversation_id=c3, direction="out", wa_id="5493510000002", type="text",
                      status="failed", error={"code": 131026, "message": "Undeliverable"}, created_at=T(3, 9, 6)),
            WaAccountStatusLog(account_id=acc.id, status="connected", quality_rating="GREEN", at=T(1, 8)),
            ToolRun(client_id=ac, agent_id=a, conversation_id=c1, slug="stock", type="http", ok=True, ms=100,
                    created_at=T(2, 10)),
            ToolRun(client_id=ac, agent_id=a, conversation_id=c1, slug="stock", type="http", ok=True, ms=200,
                    created_at=T(2, 10)),
            ToolRun(client_id=ac, agent_id=a, conversation_id=c2, slug="stock", type="http", ok=False, ms=300,
                    status_code=500, error="HTTP 500", created_at=T(2, 11)),
        ])
        # beta: una entrante que se pisa con c1 y una campaña de voz (atendida; ocupado dos veces y baja).
        bc = beta["id"]
        conv(s, bc, b, T(2, 10, 1), duration=60, conversion="complete", goal=True, phone="+5493519999999")
        k1, k2 = Contact(client_id=bc, phone="+5493511111111"), Contact(client_id=bc, phone="+5493512222222")
        camp = Campaign(client_id=bc, agent_id=b, name="Cobranza", channel="voice", status="done", concurrency=1,
                        started_at=T(5, 13), finished_at=T(5, 16))
        s.add_all([k1, k2, camp])
        s.flush()
        cc1 = CampaignContact(campaign_id=camp.id, contact_id=k1.id, status="done", result="answered", attempts=1)
        cc2 = CampaignContact(campaign_id=camp.id, contact_id=k2.id, status="failed", result="busy", attempts=2)
        s.add_all([cc1, cc2])
        s.flush()
        cc1.conversation_id = conv(s, bc, b, T(5, 14), mode="saliente", duration=90, conversion="complete",
                                   goal=True, cc=cc1.id)
        conv(s, bc, b, T(5, 15), mode="saliente", status="fallida", ended_reason="busy", cc=cc2.id)
        s.add(ContactOptout(client_id=bc, phone=k2.phone, channel="voice", source="manual", created_at=T(5, 15)))
        s.add(Subscription(client_id=bc, tier_id=beta["tier"]["id"], method="transfer", status="active"))
        s.add(BillingPayment(client_id=bc, method="transfer", amount_ars=29000, paid_on=datetime.date(2026, 10, 3)))
        s.get(Client, bc).created_via = "signup"
        s.get(Client, bc).created_at = T(1, 12)
        s.get(Client, zeta["id"]).created_at = datetime.datetime(2026, 9, 1)
        s.commit()
    ids["admin"] = admin
    return ids


def report(user, name, status=200, **params):
    r = user.get(f"{V1}/reports/{name}", params={**PERIOD, **params})
    assert r.status_code == status, r.text
    return r.json()


def test_summary_kpis_daily_and_previous(api, data):
    out = report(data["admin"], "summary", client_id=data["acme"])
    k = out["kpis"]
    # Sin prueba, loadtest ni la conversación por API.
    assert k["conversations"] == 5 and k["by_channel"] == {"voice_in": 3, "voice_out": 0, "whatsapp": 1, "web": 1}
    assert (k["conversion_pct"], k["goal_pct"]) == (40.0, 20.0)
    # Los absolutos de los porcentajes: 2 y 1 de las 5 atendidas por un agente; las 3 llamadas del agente terminaron.
    assert (k["with_agent"], k["conversions"], k["goals"], k["finished"], k["failed"]) == (5, 2, 1, 3, 0)
    assert (k["transfers"], k["transfers_answered"], k["transfer_pct"]) == (2, 1, 40.0)
    assert (k["minutes"], k["avg_duration"], k["rejected_by_limit"], k["wa_messages"]) == (3.2, 63, 1, 4)
    assert out["previous"]["conversations"] == 1 and out["previous"]["minutes"] == 0.5
    assert out["period"] == {"date_from": "2026-10-01", "date_to": "2026-10-10"}
    day = next(d for d in out["daily"] if d["date"] == "2026-10-02")
    assert day == {"date": "2026-10-02", "voice_in": 2, "voice_out": 0, "whatsapp": 0, "web": 0, "transfers": 2, "transfers_answered": 1}
    assert len(out["daily"]) == 10
    # Con las pruebas: la de prueba y la de la API; el loadtest nunca.
    assert report(data["admin"], "summary", client_id=data["acme"], include_tests=True)["kpis"]["conversations"] == 7
    # Por linea y por canal.
    assert report(data["admin"], "summary", client_id=data["acme"], phone_number_id=data["line"])["kpis"][
        "conversations"] == 2
    assert report(data["admin"], "summary", client_id=data["acme"], channel="whatsapp")["kpis"]["conversations"] == 1


def test_summary_counts_finished_and_failed_calls(api, data):
    k = report(data["admin"], "summary", client_id=data["beta"])["kpis"]
    # Una entrante y una saliente terminaron y una saliente falló; las dos terminadas convirtieron y cumplieron.
    assert (k["conversations"], k["with_agent"], k["conversions"], k["goals"]) == (3, 3, 2, 2)
    assert (k["finished"], k["failed"], k["conversion_pct"], k["goal_pct"]) == (2, 1, 66.7, 66.7)
    # Una entrante y dos salientes (la de la campaña y la que falló), por día.
    assert k["by_channel"] == {"voice_in": 1, "voice_out": 2, "whatsapp": 0, "web": 0}
    out = report(data["admin"], "summary", client_id=data["beta"])["daily"]
    assert [(d["voice_in"], d["voice_out"]) for d in out if d["date"] in ("2026-10-02", "2026-10-05")] == [(1, 0), (0, 2)]


def test_scope_by_client(api, data):
    user = client_user(api, data["admin"], {"id": data["acme"]})
    assert report(user, "summary")["kpis"]["conversations"] == 5
    assert report(user, "summary", client_id=data["acme"])["kpis"]["conversations"] == 5
    assert report(user, "summary", 403, client_id=data["beta"])
    assert report(user, "calls", 403, client_id=data["beta"])
    # El admin sin cliente ve todos.
    out = report(data["admin"], "summary")
    assert out["kpis"]["conversations"] == 8


def test_calls_report(api, data):
    out = report(data["admin"], "calls", client_id=data["acme"])
    daily = {d["date"]: d for d in out["daily"]}
    assert daily["2026-10-02"]["entrante"] == 2 and daily["2026-10-04"]["web"] == 1
    assert sum(d["prueba"] for d in out["daily"]) == 0
    friday = datetime.date(2026, 10, 2).weekday()
    assert {"weekday": friday, "hour": 10, "count": 1} in out["heatmap"]
    assert out["by_line"] == [{"phone_number_id": data["line"], "number": "+541152630861", "calls": 2,
                               "minutes": 2.2, "conversion_pct": 50.0}]
    assert out["by_agent"] == [{"agent_id": data["agent_a"], "agent_name": "Ventas", "calls": 4, "minutes": 3.2,
                                "avg_duration": 63, "conversion_pct": 50.0, "goal_pct": 25.0}]
    durations = {d["bucket"]: d["count"] for d in out["durations"]}
    assert durations == {"0-15s": 1, "15-60s": 0, "1-3m": 2, "3-5m": 0, "5-10m": 0, "10m+": 0}
    ended = {e["reason"]: e["count"] for e in out["ended"]}
    assert {r: n for r, n in ended.items() if n} == {"customer_hangup": 1, "agent_end": 1, "rejected": 1, "other": 1}
    assert list(ended) == list(report_stats.ENDED_REASONS)
    # El total es el de by_type y ended (todas las llamadas), no solo las finalizadas de durations.
    assert out["total"] == sum(ended.values()) == sum(t["calls"] for t in out["by_type"]) == 4
    assert out["early_hangups"] == 1
    callers = out["callers"]
    # 351...01 (dos llamadas) y el WhatsApp, nuevos; 351...03 ya había llamado en septiembre.
    assert (callers["new"], callers["returning"]) == (2, 1)
    assert [(c["phone"], c["count"]) for c in callers["top"]] == [("5493510000001", 2)]


def test_direct_calls_are_reported_apart(api, data):
    """Las directas y las entrantes del equipo no tienen agente: cuentan como llamadas, no como conversion."""
    ana = client_user(api, data["admin"], {"id": data["acme"]})
    ana_id = ana.get(f"{V1}/auth/me").json()["id"]
    before = {name: report(data["admin"], name, client_id=data["acme"])
              for name in ("summary", "outcomes", "transfers", "technical")}
    with api.sessions() as s:
        conv(s, data["acme"], None, T(7, 10), mode="directa", duration=300, phone="+5493510000009", user_id=ana_id)
        team = conv(s, data["acme"], None, T(7, 11), mode="entrante", duration=60, phone="+5493510000010",
                    answered_by="team", user_id=ana_id)
        # Sus celulares (Transfer.run_team) dejan handoff.*: no son derivaciones de un agente.
        s.add_all([Event(client_id=data["acme"], type=t, conversation_id=team, at=T(7, 11, 1))
                   for t in ("handoff.unavailable", "handoff.connected")])
        s.commit()
    out = report(data["admin"], "calls", client_id=data["acme"])
    day = next(d for d in out["daily"] if d["date"] == "2026-10-07")
    assert (day["directa"], day["entrante"]) == (1, 1)
    assert out["by_type"] == [{"type": "agent", "calls": 4, "minutes": 3.2, "avg_duration": 63},
                              {"type": "direct", "calls": 1, "minutes": 5.0, "avg_duration": 300},
                              {"type": "team", "calls": 1, "minutes": 1.0, "avg_duration": 60}]
    assert out["by_user"] == [{"user_id": ana_id, "user_name": "ana@acme.com", "direct": 1, "team": 1, "calls": 2,
                               "minutes": 6.0, "avg_duration": 180}]
    # Sin agente no entran en los de agente, ni el mapa de la hora en que llaman las directas.
    assert [a["agent_id"] for a in out["by_agent"]] == [data["agent_a"]] and out["by_agent"][0]["calls"] == 4
    assert {"weekday": datetime.date(2026, 10, 7).weekday(), "hour": 10, "count": 1} not in out["heatmap"]
    # Los demas reportes cuentan las llamadas y los minutos, pero la conversion y el embudo siguen siendo del agente.
    k = report(data["admin"], "summary", client_id=data["acme"])["kpis"]
    assert k["conversations"] == 7 and (k["by_channel"]["voice_in"], k["by_channel"]["voice_out"]) == (4, 1) and k["minutes"] == 9.2
    assert (k["conversion_pct"], k["goal_pct"], k["transfer_pct"]) == (40.0, 20.0, 40.0)
    assert (k["transfers"], k["transfers_answered"]) == (2, 1)
    summary = report(data["admin"], "summary", client_id=data["acme"])
    assert next(d for d in summary["daily"] if d["date"] == "2026-10-07")["transfers_answered"] == 0
    after = report(data["admin"], "outcomes", client_id=data["acme"])
    assert after["funnel"] == before["outcomes"]["funnel"]
    assert after["conversion_daily"] == before["outcomes"]["conversion_daily"]
    assert report(data["admin"], "transfers", client_id=data["acme"]) == before["transfers"]
    assert report(data["admin"], "technical", client_id=data["acme"])["turns_avg"] == before["technical"]["turns_avg"]
    # Por tipo de canal: son llamadas de voz.
    assert report(data["admin"], "summary", client_id=data["acme"], channel="voice")["kpis"]["conversations"] == 5
    report(data["admin"], "platform")
    # Sin llamadas directas, los tres tipos igual estan.
    empty = report(data["admin"], "calls", client_id=data["zeta"])
    assert [t["type"] for t in empty["by_type"]] == ["agent", "direct", "team"] and empty["by_user"] == []


def test_direct_calls_end_reasons_and_total(api, data):
    """Como terminan las directas, con su motivo y no "otro"; el total del KPI es el de by_type y ended."""
    with api.sessions() as s:
        for i, (mode, status, reason, team) in enumerate((
                ("directa", "finalizada", "person_hangup", None), ("directa", "fallida", "user_not_joined", None),
                ("directa", "fallida", "no_answer", None), ("directa", "fallida", "busy", None),
                ("entrante", "finalizada", "team_no_answer", "team"), ("entrante", "finalizada", "after_hours", "team"),
                ("entrante", "finalizada", "max_duration", "team"), ("entrante", "fallida", "worker_error", "team"))):
            conv(s, data["zeta"], None, T(7, 10 + i), mode=mode, status=status, ended_reason=reason, duration=30,
                 phone=f"+54935100001{i:02d}", answered_by=team)
        s.commit()
    out = report(data["admin"], "calls", client_id=data["zeta"])
    ended = {e["reason"]: e["count"] for e in out["ended"] if e["count"]}
    assert ended == {"person_hangup": 1, "user_not_joined": 1, "no_answer": 1, "busy": 1, "team_no_answer": 1,
                     "after_hours": 1, "max_duration": 1, "worker_error": 1}
    assert out["total"] == 8 == sum(t["calls"] for t in out["by_type"])
    assert sum(d["count"] for d in out["durations"]) == 4      # las finalizadas


def test_days_and_hours_in_the_local_zone(api, data):
    out = report(data["admin"], "calls", client_id=data["acme"], tz="America/Argentina/Buenos_Aires")
    friday = datetime.date(2026, 10, 2).weekday()
    assert {"weekday": friday, "hour": 7, "count": 1} in out["heatmap"]   # 10:00 UTC = 07:00 en Argentina


def test_outcomes_report(api, data):
    out = report(data["admin"], "outcomes", client_id=data["acme"])
    daily = {d["date"]: d for d in out["conversion_daily"]}
    assert daily["2026-10-02"] == {"date": "2026-10-02", "complete": 1, "partial": 1, "empty": 0}
    assert daily["2026-10-06"]["empty"] == 1     # sin conversion guardada: sin datos
    assert out["funnel"] == {"conversations": 5, "with_data": 3, "complete": 2, "goal": 1}
    assert out["by_agent"] == [{"agent_id": data["agent_a"], "agent_name": "Ventas", "total": 5, "complete": 2,
                                "partial": 1, "empty": 2, "goal": 1}]
    [demo] = out["outcomes"]
    assert (demo["outcome"], demo["goal"], demo["count"]) == ("demo", True, 1) and demo["label"]
    fields = {f["field"]: f for f in out["fields"]}
    assert (fields["contact_name"]["captured"], fields["contact_name"]["total"], fields["contact_name"]["pct"]) == (
        2, 5, 40.0)
    assert fields["company_name"]["captured"] == 1 and "email" not in fields     # email no es obligatorio
    assert out["by_version"] == [{"agent_id": data["agent_a"], "agent_name": "Ventas", "version": 1, "total": 5,
                                  "conversion_pct": 40.0, "goal_pct": 20.0}]


def test_messages_report(api, data):
    out = report(data["admin"], "messages", client_id=data["acme"])
    day = next(d for d in out["daily"] if d["date"] == "2026-10-03")
    assert day == {"date": "2026-10-03", "inbound": 2, "outbound": 2, "inbound_audio": 1, "outbound_audio": 0,
                   "conversations": 1}
    assert sum(c["count"] for c in out["heatmap"]) == 2
    assert out["delivery"] == {"sent": 1, "delivered": 1, "read": 0, "failed": 1}
    assert out["failures"] == [{"code": "131026", "message": "Undeliverable", "count": 1}]
    assert out["per_conversation_avg"] == 4.0
    assert out["conversion"] == {"complete": 0, "partial": 0, "empty": 1}
    [acc] = out["accounts"]
    assert acc["quality_rating"] == "GREEN" and len(acc["history"]) == 1
    # Otro canal: nada de WhatsApp.
    assert report(data["admin"], "messages", client_id=data["acme"], channel="voice")["delivery"]["failed"] == 0


def test_transfers_report(api, data):
    out = report(data["admin"], "transfers", client_id=data["acme"])
    assert out["kpis"] == {"requested": 2, "answered": 1, "not_answered": 0, "unavailable": 1, "answer_pct": 50.0,
                           "avg_answer_seconds": 10.0, "minutes": 1.0}
    [area] = out["by_area"]
    assert (area["name"], area["requested"], area["answered"], area["unavailable"]) == ("Ventas", 2, 1, 1)
    members = {m["name"]: m for m in out["by_member"]}
    assert (members["Juan"]["answered"], members["Juan"]["avg_answer_seconds"], members["Juan"]["minutes"]) == (
        1, 10.0, 1.0)
    assert (members["Pedro"]["attempts"], members["Pedro"]["not_answered"]) == (1, 1)
    assert next(d for d in out["daily"] if d["date"] == "2026-10-02") == {"date": "2026-10-02", "requested": 2,
                                                                          "answered": 1}
    assert out["whatsapp"] == {"assigned": 0, "first_reply": 0, "avg_first_reply_seconds": None, "reassigned": 0}


def test_campaigns_report(api, data):
    beta = client_user(api, data["admin"], {"id": data["beta"]}, email="bea@beta.com")
    out = report(beta, "campaigns")
    [c] = out["campaigns"]
    assert {k: c[k] for k in ("name", "channel", "contacts", "attempts", "reached", "complete", "goal", "optouts",
                              "minutes")} == {"name": "Cobranza", "channel": "voice", "contacts": 2, "attempts": 3,
                                              "reached": 1, "complete": 1, "goal": 1, "optouts": 1, "minutes": 1.5}
    assert {r["reason"]: r["count"] for r in out["no_contact"]}["busy"] == 1
    monday = datetime.date(2026, 10, 5).weekday()
    assert out["best_hours"] == [{"weekday": monday, "hour": 14, "attempts": 1, "reached": 1},
                                 {"weekday": monday, "hour": 15, "attempts": 1, "reached": 0}]


def test_plan_gates_advanced_reports(api, data):
    acme = client_user(api, data["admin"], {"id": data["acme"]})
    for name in ("outcomes", "messages", "transfers", "campaigns"):
        assert report(acme, name, 403)["code"] == "advanced_reports_not_in_plan"
        report(data["admin"], name, client_id=data["acme"])     # el admin siempre
    for name in ("summary", "calls"):
        report(acme, name)
    beta = client_user(api, data["admin"], {"id": data["beta"]}, email="bea@beta.com")
    report(beta, "outcomes")


def test_technical_is_admin_only(api, data):
    acme = client_user(api, data["admin"], {"id": data["acme"]})
    report(acme, "technical", 403)
    report(acme, "platform", 403)
    out = report(data["admin"], "technical", client_id=data["acme"])
    day = next(d for d in out["latency_daily"] if d["date"] == "2026-10-02")
    assert (day["p50"], day["p95"], day["stt_p50"]) == (1.5, 1.95, 0.2)
    providers = {p["provider"]: p for p in out["by_provider"]}
    assert providers["local"] == {"provider": "local", "model": "local-m", "turns": 1, "avg_ms": 100, "errors": 0}
    assert (providers["openrouter"]["avg_ms"], providers["openrouter"]["errors"]) == (300, 1)
    assert out["turns_avg"] == 0.6      # 3 mensajes del cliente en 5 conversaciones
    [tool] = out["tools"]
    assert {k: tool[k] for k in ("slug", "runs", "errors", "error_pct", "p50_ms", "p95_ms", "last_error")} == {
        "slug": "stock", "runs": 3, "errors": 1, "error_pct": 33.3, "p50_ms": 200, "p95_ms": 290,
        "last_error": "HTTP 500"}
    assert out["failed_summary_emails"] == 1
    assert (out["tokens"]["input"], out["tokens"]["output"]) == (100, 20)


def test_platform_report(api, data):
    assert report(data["admin"], "platform", 422, client_id=data["acme"])
    out = report(data["admin"], "platform")
    rows = {c["name"]: c for c in out["clients"]}
    assert rows["Acme"]["conversations"] == 5 and rows["Acme"]["tier"] == "Free"
    assert rows["Beta"]["quota_pct"] == 100.0     # 1 minuto entrante de 1
    assert {(a["name"], a["kind"]) for a in out["alerts"]} == {("Beta", "near_quota"), ("Zeta", "inactive")}
    biz = out["business"]
    assert (biz["mrr_ars"], biz["payments_month_ars"], biz["past_due"], biz["free_to_paid"]) == (29000, 29000, 0, 1)
    assert next(d for d in biz["signups"] if d["date"] == "2026-10-01")["count"] == 1
    op = out["operation"]
    # c1 (acme, 10:00 a 10:02) y la de beta (10:01 a 10:02) se pisan.
    assert {"date": "2026-10-02", "hour": 10, "peak": 2} in op["peak_concurrency"]
    assert {"reason": "inbound_minutes", "count": 1} in op["rejected"]
    assert {"date": "2026-10-05", "reason": "busy", "count": 1} in op["failures"]


def test_platform_alerts_skip_internal_tier(api, data):
    """El tier interno es una marca (tiers.internal), no el nombre: "Casa" sin actividad no alerta; un tier
    llamado "Interno" sin la marca, si."""
    admin = data["admin"]
    casa = make_client(admin, "casa", tier=make_tier(admin, name="Casa", internal=True))
    interno = make_client(admin, "interno", tier=make_tier(admin, name="Interno"))
    with api.sessions() as s:
        for c in (casa, interno):
            s.get(Client, c["id"]).created_at = datetime.datetime(2026, 9, 1)
        s.commit()
    alerts = {a["name"] for a in report(admin, "platform")["alerts"]}
    assert "Interno" in alerts and "Casa" not in alerts


def test_period_defaults_and_limits(api, data):
    out = data["admin"].get(f"{V1}/reports/summary").json()
    start, end = (datetime.date.fromisoformat(out["period"][k]) for k in ("date_from", "date_to"))
    assert (end - start).days == 29 and len(out["daily"]) == 30
    r = data["admin"].get(f"{V1}/reports/summary", params={"date_from": "2025-01-01", "date_to": "2026-10-10"})
    assert r.status_code == 422
    r = data["admin"].get(f"{V1}/reports/summary", params={"tz": "Marte/Base"})
    assert r.status_code == 422
