"""Campañas de voz (docs/features/CAMPANAS.md, fase 2): el dialer, el cierre de cada intento
(resultado SIP, reintentos, corte por fallas), la recuperacion y el polling. Con reloj falso, como el sender."""
import asyncio
import datetime
import uuid

import pytest
from livekit.api import SipCallError
from sqlalchemy import select

from app.campaigns.dialer import Dialer
from app.config import settings
from app.db import utcnow
from app.models import (
    CallRow,
    CallStatus,
    Campaign,
    CampaignContact,
    Contact,
    ContactOptout,
    ConversationRow,
)
from app.services import campaign_calls
from app.services import livekit as livekit_service

from .test_api import V1, make_agent, make_client
from .test_campaigns import (  # noqa: F401  (fixtures)
    PHONES,
    everyone,
    load_contacts,
    voice,
    voice_body,
)
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_campaigns import Clock


class Now:
    """Reloj de pared falso (UTC naive): ventanas, programacion y reintentos."""

    def __init__(self, t: datetime.datetime | None = None):
        self.t = t or utcnow()

    def __call__(self) -> datetime.datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t += datetime.timedelta(**kw)


def naive_utc(*args) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=datetime.UTC).replace(tzinfo=None)


def dialer_for(api, now=None, clock=None) -> Dialer:
    return Dialer(api.sessions, engine=lambda: api.engine, now=now or Now(), clock=clock or Clock())


def make_voice(user, agent, *, start=True, n=3, **extra) -> dict:
    """Una campaña de voz con n contactos (de a +5493515551001), abierta todo el dia."""
    load_contacts(user, [{"phone": f"351 555-100{i}", "name": f"Ana{i}"} for i in range(1, n + 1)])
    body = voice_body(agent, contact_ids=everyone(user), **{"window_start": 0, "window_end": 24, **extra})
    camp = user.post(f"{V1}/campaigns", json=body).json()["campaign"]
    if start:
        assert user.post(f"{V1}/campaigns/{camp['id']}/start").status_code == 200
    return camp


def members(api, campaign_id) -> list[CampaignContact]:
    with api.sessions() as s:
        rows = list(s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == campaign_id)
                              .order_by(CampaignContact.created_at, CampaignContact.id)))
        for r in rows:
            s.expunge(r)
        return rows


def states(api, campaign_id) -> list[tuple]:
    return [(m.status, m.result, m.attempts) for m in members(api, campaign_id)]


def campaign(api, campaign_id) -> Campaign:
    with api.sessions() as s:
        c = s.get(Campaign, campaign_id)
        s.expunge(c)
        return c


def close(api, contact_id, result, **kw):
    with api.sessions() as s:
        r = campaign_calls.close_contact(s, contact_id, result, **kw)
        s.commit()
        return r


# ---------- clasificacion del resultado (plan, seccion 5) ----------

@pytest.mark.parametrize("sip,result", [
    (486, "busy"), (600, "busy"), (408, "no_answer"), (480, "no_answer"), (487, "no_answer"),
    (404, "invalid"), (484, "invalid"), (604, "invalid"), (403, "rejected"), (603, "rejected"),
    (500, "failed"), (503, "failed"), (None, "failed")])
def test_classify_sip(sip, result):
    assert campaign_calls.classify_sip(sip) == result


def test_classify_error_reads_the_twirp_metadata():
    busy = SipCallError("unavailable", "busy", status=503, metadata={"sip_status_code": "486", "sip_status": "Busy"})
    assert campaign_calls.classify_error(busy) == ("busy", 486)
    # Sin codigo SIP: un vencimiento (timbre o plazo del pedido) es no_answer; el resto, failed.
    assert campaign_calls.classify_error(SipCallError("deadline_exceeded", "x", status=408)) == ("no_answer", None)
    assert campaign_calls.classify_error(TimeoutError()) == ("no_answer", None)
    assert campaign_calls.classify_error(RuntimeError("trunk")) == ("failed", None)
    assert campaign_calls.classify_error(
        SipCallError("unavailable", "x", status=503, metadata={"sip_status_code": "basura"})) == ("failed", None)


# ---------- el dialer ----------

async def test_dialer_dials_up_to_concurrency_and_passes_the_contact(api, voice):  # noqa: F811
    user, agent, c = voice
    camp = make_voice(user, agent, concurrency=2, rate_per_minute=600)
    clock = Clock()
    dialer = dialer_for(api, clock=clock)
    assert await dialer.tick() == 2
    assert [s[0] for s in states(api, camp["id"])] == ["in_progress", "in_progress", "pending"]
    assert [m["phone"] for m in api.dispatched] == [PHONES_E164[0], PHONES_E164[1]]
    first = members(api, camp["id"])[0]
    assert api.dispatched[0]["campaign_contact_id"] == first.id and api.dispatched[0]["voice"] is None
    with api.sessions() as s:
        call = s.scalar(select(CallRow).where(CallRow.campaign_contact_id == first.id))
        assert call.mode == "saliente" and call.phone == PHONES_E164[0] and call.client_id == c["id"]
        assert first.conversation_id == call.conversation_id and first.attempts == 1 and first.last_attempt_at
    clock.t += 2
    assert await dialer.tick() == 0      # concurrency 2: no marca otra hasta que termine una
    close(api, first.id, "answered")
    clock.t += 2
    assert await dialer.tick() == 1
    assert [s[0] for s in states(api, camp["id"])] == ["done", "in_progress", "in_progress"]


PHONES_E164 = ["+5493515551001", "+5493515551002", "+5493515551003"]


async def test_dialer_respects_the_rate(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=10, rate_per_minute=30)      # 1 cada 2 s
    clock = Clock()
    dialer = dialer_for(api, clock=clock)
    assert await dialer.tick() == 1
    assert await dialer.tick() == 0      # sin tiempo transcurrido no hay credito
    clock.t += 4
    assert await dialer.tick() == 2
    assert [s[0] for s in states(api, camp["id"])] == ["in_progress"] * 3


async def test_dialer_global_cap_across_campaigns(api, voice, monkeypatch):  # noqa: F811
    user, agent, _ = voice
    monkeypatch.setattr(settings, "call_campaign_max_concurrent", 2)
    a = make_voice(user, agent, concurrency=5, rate_per_minute=600)
    dialer = dialer_for(api)
    assert await dialer.tick() == 2
    assert [s[0] for s in states(api, a["id"])] == ["in_progress", "in_progress", "pending"]


async def test_dialer_shares_the_global_cap_between_campaigns(api, voice, monkeypatch):  # noqa: F811
    """Una campaña con mucha concurrencia no se queda con todos los lugares libres cada vez que una
    llamada termina: las campañas van por turno."""
    user, agent, _ = voice
    monkeypatch.setattr(settings, "call_campaign_max_concurrent", 2)
    a = make_voice(user, agent, n=6, concurrency=5, rate_per_minute=600, name="A")
    b = make_voice(user, agent, n=6, concurrency=1, rate_per_minute=600, name="B")
    clock = Clock()
    dialer = dialer_for(api, clock=clock)
    for _ in range(3):
        await dialer.tick()
        for m in members(api, a["id"]) + members(api, b["id"]):
            if m.status == "in_progress":
                close(api, m.id, "answered")
        clock.t += 2
    done = {name: sum(m.status == "done" for m in members(api, c["id"])) for name, c in (("a", a), ("b", b))}
    assert done["b"] >= 2 and done["a"] >= 2      # sin equidad era A: 6 y B: 0
    assert done["a"] + done["b"] <= 6


async def test_dialer_waits_outside_the_window_and_the_weekdays(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=5, rate_per_minute=600, window_start=9, window_end=20,
                      weekdays=[0, 1, 2, 3, 4])
    monday_noon = naive_utc(2026, 10, 19, 15)        # 12:00 en Buenos Aires (UTC-3), lunes
    now, clock = Now(monday_noon + datetime.timedelta(hours=9)), Clock()      # martes 00:00 UTC = lunes 21:00 local
    dialer = dialer_for(api, now=now, clock=clock)
    assert await dialer.tick() == 0
    assert states(api, camp["id"]) == [("pending", None, 0)] * 3
    now.t = naive_utc(2026, 10, 24, 15)       # sabado a mediodia
    clock.t += 2
    assert await dialer.tick() == 0
    now.t = monday_noon
    clock.t += 2
    assert await dialer.tick() == 3


async def test_dialer_activates_scheduled_and_closes_expired(api, voice):  # noqa: F811
    user, agent, _ = voice
    now = Now()
    starts = (now.t + datetime.timedelta(hours=1)).replace(tzinfo=datetime.UTC).isoformat()
    ends = (now.t + datetime.timedelta(hours=3)).replace(tzinfo=datetime.UTC).isoformat()
    camp = make_voice(user, agent, concurrency=5, rate_per_minute=600, starts_at=starts, ends_at=ends)
    assert user.get(f"{V1}/campaigns/{camp['id']}").json()["status"] == "scheduled"
    clock = Clock()
    dialer = dialer_for(api, now=now, clock=clock)
    assert await dialer.tick() == 0 and campaign(api, camp["id"]).status == "scheduled"
    now.advance(minutes=61)
    clock.t += 2
    assert await dialer.tick() == 3 and campaign(api, camp["id"]).status == "running"
    for m in members(api, camp["id"]):
        close(api, m.id, "busy", now=now.t)         # los tres a reintento
    now.advance(hours=3)
    clock.t += 2
    assert await dialer.tick() == 0
    c = campaign(api, camp["id"])
    assert c.status == "done" and c.finished_at
    assert [s[0] for s in states(api, camp["id"])] == ["skipped"] * 3


async def test_dialer_skips_optouts_and_archived(api, voice):  # noqa: F811
    user, agent, c = voice
    camp = make_voice(user, agent, concurrency=5, rate_per_minute=600)
    with api.sessions() as s:
        s.add(ContactOptout(client_id=c["id"], phone=PHONES_E164[0], channel="voice", source="manual"))
        s.add(ContactOptout(client_id=c["id"], phone=PHONES_E164[2], channel="whatsapp", source="manual"))
        s.get(Contact, members(api, camp["id"])[1].contact_id).archived_at = utcnow()
        s.commit()
    assert await dialer_for(api).tick() == 1
    assert [s[0] for s in states(api, camp["id"])] == ["skipped", "skipped", "in_progress"]
    errors = [m.error["reason"] for m in members(api, camp["id"])[:2]]
    assert errors == ["optout", "contact_archived"]
    assert [m["phone"] for m in api.dispatched] == [PHONES_E164[2]]      # la baja de WhatsApp no cuenta en voz


async def test_dialer_concurrency_limit_returns_the_contact_without_spending_the_attempt(api, admin):  # noqa: F811
    from .test_api import client_user
    c = make_client(admin, slug="cap", campaign_channels=["voice"], max_concurrent_calls=1)
    agent = make_agent(admin, c, template="demo_booking")
    user = client_user(api, admin, c, email="cap@x.com")
    camp = make_voice(user, agent, concurrency=3, rate_per_minute=600)
    clock = Clock()
    dialer = dialer_for(api, clock=clock)
    assert await dialer.tick() == 1
    assert [s[:3] for s in states(api, camp["id"])] == [("in_progress", None, 1), ("pending", None, 0),
                                                         ("pending", None, 0)]
    assert campaign(api, camp["id"]).status == "running"
    clock.t += 2
    assert await dialer.tick() == 0      # espera unos segundos tras el rechazo
    clock.t += 20
    await dialer.tick()
    assert [s[0] for s in states(api, camp["id"])] == ["in_progress", "pending", "pending"]


async def test_dialer_pauses_when_the_plan_has_no_minutes(api, admin):  # noqa: F811
    from .test_api import client_user
    c = make_client(admin, slug="mins", campaign_channels=["voice"], outbound_minutes=0)
    agent = make_agent(admin, c, template="demo_booking")
    user = client_user(api, admin, c, email="mins@x.com")
    camp = make_voice(user, agent, concurrency=3, rate_per_minute=600)
    assert await dialer_for(api).tick() == 0
    got = campaign(api, camp["id"])
    assert got.status == "paused" and "minutos" in got.status_reason
    assert states(api, camp["id"]) == [("pending", None, 0)] * 3


async def test_dialer_pauses_when_the_agent_is_archived(api, voice, admin):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=3, rate_per_minute=600)
    assert admin.patch(f"{V1}/agents/{agent['id']}", json={"archived": True}).status_code == 200
    assert await dialer_for(api).tick() == 0
    got = campaign(api, camp["id"])
    assert got.status == "paused" and "archivado" in got.status_reason
    assert states(api, camp["id"])[0][0] == "pending"


async def test_dialer_invalid_phone_fails_only_that_contact(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=1, rate_per_minute=600)
    with api.sessions() as s:
        s.get(Contact, members(api, camp["id"])[0].contact_id).phone = "+123"
        s.commit()
    assert await dialer_for(api).tick() == 0
    assert states(api, camp["id"]) == [("failed", "invalid", 1), ("pending", None, 0), ("pending", None, 0)]
    assert campaign(api, camp["id"]).status == "running"


async def test_dialer_dispatch_failure_is_a_failed_attempt(api, voice, monkeypatch):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=1, rate_per_minute=600)

    async def boom(room, metadata):
        raise RuntimeError("livekit caido")

    monkeypatch.setattr(livekit_service, "dispatch_call", boom)
    assert await dialer_for(api).tick() == 0
    first = members(api, camp["id"])[0]
    assert (first.status, first.result, first.attempts) == ("retry", "failed", 1)
    assert first.error["reason"] == "dispatch_failed" and first.next_attempt_at
    with api.sessions() as s:
        assert s.get(CallRow, first.conversation_id).status == CallStatus.fallida


async def test_dialer_retries_after_the_wait(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=1, rate_per_minute=600, retry_minutes=30)
    now, clock = Now(), Clock()
    dialer = dialer_for(api, now=now, clock=clock)
    assert await dialer.tick() == 1
    first = members(api, camp["id"])[0]
    close(api, first.id, "busy", now=now.t)
    assert states(api, camp["id"])[0] == ("retry", "busy", 1)
    assert members(api, camp["id"])[0].next_attempt_at == now.t + datetime.timedelta(minutes=30)
    clock.t += 2
    assert await dialer.tick() == 1      # el siguiente pendiente, no el que espera
    assert members(api, camp["id"])[1].status == "in_progress"
    close(api, members(api, camp["id"])[1].id, "answered", now=now.t)
    now.advance(minutes=29)
    clock.t += 2
    await dialer.tick()      # el tercero; el primero todavia espera
    assert members(api, camp["id"])[0].status == "retry"
    close(api, members(api, camp["id"])[2].id, "answered", now=now.t)
    now.advance(minutes=2)
    clock.t += 2
    assert await dialer.tick() == 1
    assert states(api, camp["id"])[0] == ("in_progress", "busy", 2)


async def test_dialer_stops_when_the_campaign_is_paused_mid_batch(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=3, rate_per_minute=600)
    dialer = dialer_for(api)
    ids = await asyncio.to_thread(dialer._claim, camp["id"])
    assert len(ids) == 3
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").status_code == 200
    assert [await dialer._dial(camp["id"], i) for i in ids] == [False, False, False]
    assert states(api, camp["id"]) == [("pending", None, 0)] * 3 and api.dispatched == []


async def test_dialer_follows_the_plan_concurrency_after_a_downgrade(api, voice, admin):  # noqa: F811
    user, agent, c = voice
    camp = make_voice(user, agent, concurrency=3, rate_per_minute=600)
    assert admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaign_concurrency": 1}).status_code == 200
    dialer = dialer_for(api)
    assert await dialer.tick() == 1      # la campaña pide 3, el plan de ahora permite 1
    assert [s[0] for s in states(api, camp["id"])] == ["in_progress", "pending", "pending"]
    assert admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"max_campaign_concurrency": 0}).status_code == 200
    await dialer.tick()
    out = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert out["status"] == "paused" and "simultáneas" in out["status_reason"]


# ---------- cierre del intento ----------

def test_close_contact_rules(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=3, max_attempts=2, retry_minutes=10, retry_on=["busy", "failed"])
    now = utcnow()
    with api.sessions() as s:
        for m in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])):
            m.status, m.attempts = "in_progress", 1
        s.commit()
    a, b, c = (m.id for m in members(api, camp["id"]))
    assert close(api, a, "busy", now=now).status == "retry"
    assert members(api, camp["id"])[0].next_attempt_at == now + datetime.timedelta(minutes=10)
    assert close(api, b, "no_answer", now=now).status == "done"       # no esta en retry_on
    assert close(api, c, "invalid", now=now, error={"message": "x"}).status == "failed"
    assert close(api, a, "answered") is None      # ya no estaba en vuelo
    with api.sessions() as s:       # ultimo intento de a: agotados los 2, queda done aunque no atienda
        s.get(CampaignContact, a).status = "in_progress"
        s.get(CampaignContact, a).attempts = 2
        s.commit()
    assert close(api, a, "busy", now=now).status == "done"
    done = campaign(api, camp["id"])
    assert done.status == "done" and done.finished_at == now


def test_resume_a_campaign_that_only_has_retries(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, n=2, concurrency=2, rate_per_minute=600)
    asyncio.run(dialer_for(api).tick())
    for m in members(api, camp["id"]):
        close(api, m.id, "busy")
    assert [s[0] for s in states(api, camp["id"])] == ["retry", "retry"]
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").status_code == 200
    r = user.post(f"{V1}/campaigns/{camp['id']}/resume")      # sin pendientes, pero con reintentos por hacer
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"
    # Lo que ya no tiene nada por hacer sigue sin poder retomarse.
    assert user.post(f"{V1}/campaigns/{camp['id']}/pause").status_code == 200
    with api.sessions() as s:
        for m in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == camp["id"])):
            m.status = "done"
        s.commit()
    assert user.post(f"{V1}/campaigns/{camp['id']}/resume").status_code == 409


def test_a_call_that_ends_after_the_campaign_was_cancelled_is_not_retried(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, n=3, concurrency=3, rate_per_minute=600)
    asyncio.run(dialer_for(api).tick())
    assert user.post(f"{V1}/campaigns/{camp['id']}/cancel").status_code == 200
    a, b, c = members(api, camp["id"])
    close(api, a.id, "busy")
    close(api, b.id, "failed")
    close(api, c.id, "answered")
    after = members(api, camp["id"])
    assert [(m.status, m.result, m.next_attempt_at) for m in after] == [
        ("done", "busy", None), ("failed", "failed", None), ("done", "answered", None)]
    assert user.get(f"{V1}/campaigns/{camp['id']}").json()["percent"] == 100.0


def test_a_late_call_on_a_cancelled_campaign_does_not_queue_a_followup(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, n=1, concurrency=1, rate_per_minute=600)
    asyncio.run(dialer_for(api).tick())
    with api.sessions() as s:
        s.get(Campaign, camp["id"]).followup = {"after": ["busy"], "account_id": "x", "template_name": "t"}
        s.commit()
    assert user.post(f"{V1}/campaigns/{camp['id']}/cancel").status_code == 200
    close(api, members(api, camp["id"])[0].id, "busy")
    assert members(api, camp["id"])[0].followup_status is None


def test_close_contact_pauses_after_a_streak_of_failures(api, voice, monkeypatch):  # noqa: F811
    user, agent, _ = voice
    monkeypatch.setattr(settings, "call_campaign_failure_streak", 3)
    camp = make_voice(user, agent, n=4, concurrency=5)
    ids = [m.id for m in members(api, camp["id"])]
    now = utcnow()
    with api.sessions() as s:
        for i, rid in enumerate(ids):
            r = s.get(CampaignContact, rid)
            r.status, r.attempts, r.last_attempt_at = "in_progress", 1, now + datetime.timedelta(seconds=i)
        s.commit()
    close(api, ids[0], "failed", now=now)
    close(api, ids[1], "busy", now=now)         # corta la racha
    close(api, ids[2], "failed", now=now)
    assert campaign(api, camp["id"]).status == "running"
    close(api, ids[3], "failed", now=now)
    assert campaign(api, camp["id"]).status == "running"       # busy, failed, failed: solo dos seguidos
    with api.sessions() as s:
        r = s.get(CampaignContact, ids[1])
        r.status, r.attempts, r.last_attempt_at = "in_progress", 1, now + datetime.timedelta(seconds=10)
        s.commit()
    close(api, ids[1], "failed", now=now)
    got = campaign(api, camp["id"])
    assert got.status == "paused" and "telefonía" in got.status_reason


def test_close_attempt_by_conversation(api, voice):  # noqa: F811
    user, agent, _ = voice
    camp = make_voice(user, agent, concurrency=1)
    conv = str(uuid.uuid4())
    first = members(api, camp["id"])[0]
    with api.sessions() as s:
        s.add(ConversationRow(id=conv, client_id=first_client(s, camp), agent_id=agent["id"], channel="voice",
                              status="active", fields={}, messages=[]))
        s.flush()
        s.add(CallRow(conversation_id=conv, mode="saliente", campaign_contact_id=first.id, status=CallStatus.sonando))
        s.get(CampaignContact, first.id).status = "in_progress"
        s.commit()
    with api.sessions() as s:
        assert campaign_calls.close_attempt(s, "no-existe", "answered") is None
        assert campaign_calls.close_attempt(s, conv, "rejected", error={"sip_status": 603}).status == "done"
        s.commit()
    got = members(api, camp["id"])[0]
    assert (got.result, got.conversation_id, got.error) == ("rejected", conv, {"sip_status": 603})


def first_client(s, camp) -> str:
    return s.get(Campaign, camp["id"]).client_id


# ---------- recuperacion ----------

def test_recover_in_progress(api, voice):  # noqa: F811
    user, agent, c = voice
    camp = make_voice(user, agent, concurrency=5, max_attempts=2)
    a, b, d = members(api, camp["id"])
    now = utcnow()
    stuck = now - datetime.timedelta(minutes=1)
    with api.sessions() as s:
        for m, conv_status in ((a, None), (b, CallStatus.finalizada), (d, CallStatus.en_curso)):
            r = s.get(CampaignContact, m.id)
            r.status, r.attempts, r.last_attempt_at = "in_progress", 1, stuck
            if conv_status:
                conv = str(uuid.uuid4())
                s.add(ConversationRow(id=conv, client_id=c["id"], agent_id=agent["id"], channel="voice",
                                      status="active", fields={}, messages=[]))
                s.flush()
                s.add(CallRow(conversation_id=conv, client_id=c["id"], mode="saliente", status=conv_status,
                              campaign_contact_id=m.id, created_at=now))
        s.commit()
    assert dialer_for(api, now=Now(now)).recover(grace_seconds=300) == 0      # recien reclamados: se esperan
    assert dialer_for(api, now=Now(now)).recover() == 2
    got = members(api, camp["id"])
    # a: no llego a llamar (el intento no se cuenta); b: la llamada termino sin cerrarse; d: sigue en curso.
    assert (got[0].status, got[0].attempts, got[0].next_attempt_at) == ("retry", 0, now)
    assert (got[1].status, got[1].attempts, got[1].result) == ("retry", 1, "failed")
    assert got[2].status == "in_progress"
    assert campaign(api, camp["id"]).status == "running"


# ---------- polling ----------

def test_polling_has_goal_minutes_and_window(api, voice):  # noqa: F811
    user, agent, c = voice
    camp = make_voice(user, agent, concurrency=3, window_start=0, window_end=24)
    a, b, _ = members(api, camp["id"])
    with api.sessions() as s:
        for m, outcome in ((a, "demo"), (b, "callback")):
            conv = str(uuid.uuid4())
            s.add(ConversationRow(id=conv, client_id=c["id"], agent_id=agent["id"], agent_version=1, channel="voice",
                                  status="completed", fields={}, messages=[], progress={"outcome": outcome}))
            s.flush()
            s.add(CallRow(conversation_id=conv, client_id=c["id"], mode="saliente", duration_seconds=120,
                          campaign_contact_id=m.id))
            r = s.get(CampaignContact, m.id)
            r.status, r.result, r.conversation_id, r.attempts, r.last_attempt_at = (
                "done", "answered", conv, 1, utcnow())
        s.commit()
    d = user.get(f"{V1}/campaigns/{camp['id']}").json()
    assert d["goal"] == 1 and d["minutes_used"] == 4.0 and d["in_window"] is True
    assert d["results"]["answered"] == 2 and d["percent"] == 66.7 and d["eta_minutes"] is not None
    assert d["progress"]["done"] == 2 and d["progress"]["pending"] == 1
    assert user.get(f"{V1}/campaigns").json()[0]["goal"] is None      # la lista no la calcula


def test_goal_is_only_recomputed_when_a_conversation_changes(api, voice, monkeypatch):  # noqa: F811
    """El detalle se consulta cada 5 s: el conteo no recorre las conversaciones si ninguna cambio."""
    user, agent, c = voice
    camp = make_voice(user, agent, concurrency=3, window_start=0, window_end=24)
    a, b, _ = members(api, camp["id"])
    convs = {}
    with api.sessions() as s:
        for m, outcome in ((a, "demo"), (b, "callback")):
            conv = str(uuid.uuid4())
            convs[m.id] = conv
            s.add(ConversationRow(id=conv, client_id=c["id"], agent_id=agent["id"], agent_version=1, channel="voice",
                                  status="completed", fields={}, messages=[], progress={"outcome": outcome}))
            s.flush()
            s.add(CallRow(conversation_id=conv, client_id=c["id"], mode="saliente", campaign_contact_id=m.id))
            r = s.get(CampaignContact, m.id)
            r.status, r.result, r.conversation_id, r.attempts, r.last_attempt_at = (
                "done", "answered", conv, 1, utcnow())
        s.commit()
    calls = []
    real = campaign_calls.goal_count
    monkeypatch.setattr(campaign_calls, "goal_count", lambda *a, **k: calls.append(1) or real(*a, **k))
    url = f"{V1}/campaigns/{camp['id']}"
    assert [user.get(url).json()["goal"] for _ in range(3)] == [1, 1, 1] and len(calls) == 1
    assert user.get(f"{url}/stats").json()["goal"] == 1 and len(calls) == 1
    with api.sessions() as s:      # la conversacion de b llega al objetivo
        s.get(ConversationRow, convs[b.id]).progress = {"outcome": "demo"}
        s.commit()
    assert user.get(url).json()["goal"] == 2 and len(calls) == 2
