"""Plantillas de WhatsApp al equipo (app/whatsapp/team_notify.py), con Graph falso. Ningun caso lanza y cada uno queda
registrado en eventos y, si llego a Meta, en wa_messages."""
import datetime

import pytest
from sqlalchemy import select

from app.config import settings
from app.db import utcnow
from app.models import Client, Event, HandoffArea, HandoffAreaMember, TeamMember, Tier, WaAccount, WaMessage
from app.services import handoff as handoff_service
from app.whatsapp import crypto, team_notify
from app.whatsapp.graph import GraphError

from .test_whatsapp_service import PNID, make_wa

PHONES = ("+5493515551111", "+5493515552222", "+5493515553333")
TEMPLATE = {"name": "equipo_consulta", "language": "es_AR", "params": ["area", "persona", "cliente", "resumen", "ficha"]}


class FakeGraph:
    """fail: {destino: GraphError}. boom: excepcion cualquiera a levantar al enviar."""

    def __init__(self):
        self.sent = []
        self.fail = {}
        self.boom = None
        self.closed = 0

    async def send_template(self, pnid, to, name, language, params=None):
        if self.boom:
            raise self.boom
        if to in self.fail:
            raise self.fail[to]
        self.sent.append((pnid, to, name, language, params))
        return {"messages": [{"id": f"wamid.t{len(self.sent)}"}]}

    async def aclose(self):
        self.closed += 1


@pytest.fixture
def team(sessions):
    """Cliente con cuenta conectada y un area de aviso con tres personas con el toggle."""
    w = make_wa(sessions)
    w.fake = FakeGraph()
    w.factory = lambda token: w.fake
    with sessions() as s:
        members = [TeamMember(client_id=w.client_id, name=f"Op{i}", phone=phone, whatsapp_notify=True)
                   for i, phone in enumerate(PHONES)]
        s.add_all(members)
        area = HandoffArea(client_id=w.client_id, name="Consultas", delivery="whatsapp",
                           whatsapp={"account_id": w.account_id, "template": TEMPLATE})
        s.add(area)
        s.flush()
        s.add_all(HandoffAreaMember(area_id=area.id, member_id=m.id, position=i) for i, m in enumerate(members))
        s.commit()
        w.area, w.members = area, members
    return w


def event_list(sessions, type=None):
    with sessions() as s:
        q = select(Event).order_by(Event.id)
        if type:
            q = q.where(Event.type == type)
        return list(s.scalars(q))


def out_messages(sessions):
    with sessions() as s:
        return list(s.scalars(select(WaMessage).where(WaMessage.type == "team_notice")))


def update_account(w, **changes):
    with w.sessions() as s:
        account = s.get(WaAccount, w.account_id)
        for k, v in changes.items():
            setattr(account, k, v)
        s.commit()


async def send(w, member=None, template=TEMPLATE, values=None, area=None, client_id=None):
    return await team_notify.send(w.sessions, client_id or w.client_id, area or w.area, member or w.members[0], template,
                                  values if values is not None else {"cliente": "+5493510000000"}, None,
                                  graph_factory=w.factory)


async def assert_refused(w, reason, **kw):
    assert await send(w, **kw) == (False, None, {"reason": reason})
    assert w.fake.sent == []
    assert out_messages(w.sessions) == []
    failed = event_list(w.sessions, "handoff.whatsapp_failed")
    assert failed[-1].data["reason"] == reason
    return failed[-1]


async def test_send_ok_is_recorded(team):
    ok, wamid, error = await send(team, values={"cliente": "+5493510000000", "resumen": "dolor", "ficha": "http://x/1"})
    assert (ok, wamid, error) == (True, "wamid.t1", None)
    # Destino sin el 9 (service.recipient), por posicion, con area y persona de la plataforma.
    assert team.fake.sent == [(PNID, "543515551111", "equipo_consulta", "es_AR",
                               ["Consultas", "Op0", "+5493510000000", "dolor", "http://x/1"])]
    [msg] = out_messages(team.sessions)
    assert (msg.wamid, msg.account_id, msg.direction, msg.status) == ("wamid.t1", team.account_id, "out", "sent")
    [event] = event_list(team.sessions, "handoff.whatsapp_sent")
    assert (event.area_id, event.team_member_id, event.data["wamid"]) == (team.area.id, team.members[0].id, "wamid.t1")


async def test_params_normalized_and_reserved_win(team):
    template = {**TEMPLATE, "params": ["area", "persona", "resumen", "vacio", "falta", "nota", "numero"]}
    await send(team, template=template, values={
        "area": "otra", "persona": "otro", "resumen": "dolor\n  de\tpecho\r\n\r\nfuerte", "vacio": "  \n", "nota": None,
        "numero": 12})
    assert team.fake.sent[0][4] == ["Consultas", "Op0", "dolor de pecho fuerte", "-", "-", "-", "12"]


@pytest.mark.parametrize("caller", ["anonymous", "", None, "1234567", "+54 351"])
async def test_hidden_caller_goes_as_dash(team, caller):
    template = {**TEMPLATE, "params": ["cliente"]}
    ok, _, _ = await send(team, template=template, values={"cliente": caller})
    assert ok
    assert team.fake.sent[0][4] == ["-"]


async def test_horario_described_when_missing(team):
    with team.sessions() as s:
        area = s.get(HandoffArea, team.area.id)
        area.schedule = {"tz": "America/Argentina/Buenos_Aires", "week": {"mon": [["09:00", "18:00"]]}}
        s.commit()
        s.refresh(area)
    await send(team, area=area, template={**TEMPLATE, "params": ["horario"]})
    assert "09:00" in team.fake.sent[0][4][0]


async def test_account_of_another_client_is_refused(team, sessions):
    with sessions() as s:
        tier = Tier(name="Otro")
        s.add(tier)
        s.flush()
        other = Client(name="Otro", slug="otro", tier_id=tier.id)
        s.add(other)
        s.flush()
        other_id = other.id
        s.get(WaAccount, team.account_id).client_id = other_id
        s.commit()
    event = await assert_refused(team, "account_other_client")
    # La falla queda en el cliente de la derivacion, y al otro no le llega nada.
    assert event.client_id == team.client_id


async def test_area_or_member_of_another_client_is_refused(team):
    await assert_refused(team, "other_client", client_id=_second_client(team))


def _second_client(w):
    with w.sessions() as s:
        tier = Tier(name="Dos")
        s.add(tier)
        s.flush()
        other = Client(name="Dos", slug="dos", tier_id=tier.id)
        s.add(other)
        s.commit()
        return other.id


@pytest.mark.parametrize(("changes", "reason"), [
    ({"status": "disconnected"}, "account_disconnected"),
    ({"status": "pending"}, "account_disconnected"),
    ({"active": False}, "account_inactive"),
])
async def test_account_not_usable(team, changes, reason):
    update_account(team, **changes)
    await assert_refused(team, reason)


async def test_account_missing(team):
    area = HandoffArea(id="x", client_id=team.client_id, name="Sin cuenta", whatsapp=None)
    await assert_refused(team, "account_missing", area=area)


async def test_inactive_client(team):
    with team.sessions() as s:
        s.get(Client, team.client_id).active = False
        s.commit()
    await assert_refused(team, "client_inactive")


async def test_plan_without_whatsapp(team):
    with team.sessions() as s:
        s.get(Tier, s.get(Client, team.client_id).tier_id).whatsapp = False
        s.commit()
    await assert_refused(team, "whatsapp_not_in_plan")


async def test_toggle_off_and_no_phone(team):
    off = TeamMember(id="off", client_id=team.client_id, name="Off", phone=PHONES[0], whatsapp_notify=False)
    await assert_refused(team, "member_not_notified", member=off)
    no_phone = TeamMember(id="np", client_id=team.client_id, name="NP", phone=None, whatsapp_notify=True)
    await assert_refused(team, "member_without_phone", member=no_phone)


async def test_without_template(team):
    await assert_refused(team, "no_template", template=None)


async def test_token_key_missing(team, monkeypatch):
    # El token cifrado con una clave que ya no esta.
    update_account(team, access_token="fernet:gAAAAA-no-se-descifra")
    monkeypatch.setattr(settings, "wa_token_key", "")
    await assert_refused(team, "token_key_missing")


async def test_meta_error_is_recorded_without_raising(team):
    team.fake.fail["543515551111"] = GraphError("Template paused", code=132015, subcode=7, status=400)
    ok, wamid, error = await send(team)
    assert (ok, wamid) == (False, None)
    assert error == {"reason": "meta_rejected", "code": 132015, "subcode": 7, "message": "Template paused"}
    [msg] = out_messages(team.sessions)
    assert (msg.status, msg.wamid, msg.error["code"]) == ("failed", None, 132015)
    [event] = event_list(team.sessions, "handoff.whatsapp_failed")
    assert (event.data["code"], event.data["template"]) == (132015, "equipo_consulta")
    assert "message" not in event.data
    with team.sessions() as s:
        assert s.get(WaAccount, team.account_id).status == "connected"


async def test_unexpected_error_does_not_raise(team):
    team.fake.boom = RuntimeError("cualquiera")
    assert await send(team) == (False, None, {"reason": "internal"})
    assert event_list(team.sessions, "handoff.whatsapp_failed")[-1].data["reason"] == "internal"


async def test_broken_database_does_not_raise(team):
    def broken():
        raise RuntimeError("sin base")

    assert await team_notify.send(broken, team.client_id, team.area, team.members[0], TEMPLATE, {}, None,
                                  graph_factory=team.factory) == (False, None, {"reason": "internal"})
    notice = await team_notify.notify_area(broken, team.client_id, team.area.id, {}, None, graph_factory=team.factory)
    assert notice == team_notify.Notice(False, error={"reason": "internal"})


async def test_sent_stays_ok_if_recording_fails(team, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("sin base")

    monkeypatch.setattr(team_notify.store, "record_outbound", broken)
    assert await send(team) == (True, "wamid.t1", None)


async def test_own_token_rejected_disconnects_the_account(team):
    update_account(team, access_token=crypto.encrypt("propio") if settings.wa_token_key else "propio")
    team.fake.fail["543515551111"] = GraphError("bad token", code=190, status=401)
    _, _, error = await send(team)
    assert error["reason"] == "token_rejected"
    with team.sessions() as s:
        assert s.get(WaAccount, team.account_id).status == "disconnected"


async def test_global_token_rejected_keeps_the_account(team):
    team.fake.fail["543515551111"] = GraphError("bad token", code=190, status=401)
    await send(team)
    with team.sessions() as s:
        assert s.get(WaAccount, team.account_id).status == "connected"


async def test_default_graph_is_closed(team, monkeypatch):
    built = []

    def client(token, version):
        built.append((token, version))
        return team.fake

    monkeypatch.setattr(team_notify, "GraphClient", client)
    monkeypatch.setattr(settings, "wa_access_token", "global")
    ok, _, _ = await team_notify.send(team.sessions, team.client_id, team.area, team.members[0], TEMPLATE, {}, None)
    assert ok
    assert built == [("global", settings.wa_graph_version)]
    assert team.fake.closed == 1


# ---------- aviso de un area ----------

async def notify(w, values=None):
    return await team_notify.notify_area(w.sessions, w.client_id, w.area.id, values or {}, None, graph_factory=w.factory)


async def test_notify_reaches_only_the_first(team):
    notice = await notify(team)
    assert notice == team_notify.Notice(True, team.members[0].id, "wamid.t1")
    assert [m[1] for m in team.fake.sent] == ["543515551111"]
    with team.sessions() as s:
        assert s.get(HandoffArea, team.area.id).last_member_id == team.members[0].id
    [event] = event_list(team.sessions, "handoff.notified")
    assert (event.area_id, event.team_member_id) == (team.area.id, team.members[0].id)


async def test_notify_first_fails_only_one_receives(team):
    team.fake.fail["543515551111"] = GraphError("rechazado", code=131026, status=400)
    notice = await notify(team)
    assert (notice.ok, notice.member_id) == (True, team.members[1].id)
    assert [m[1] for m in team.fake.sent] == ["543515552222"]
    assert [e.team_member_id for e in event_list(team.sessions, "handoff.whatsapp_failed")] == [team.members[0].id]
    assert len(event_list(team.sessions, "handoff.notified")) == 1
    assert sorted(m.status for m in out_messages(team.sessions)) == ["failed", "sent"]


async def test_notify_everyone_fails(team):
    for phone in ("543515551111", "543515552222", "543515553333"):
        team.fake.fail[phone] = GraphError("rechazado", code=131026, status=400)
    notice = await notify(team)
    assert (notice.ok, notice.member_id, notice.error["code"]) == (False, None, 131026)
    assert event_list(team.sessions, "handoff.notified") == []
    assert len(event_list(team.sessions, "handoff.whatsapp_failed")) == 3
    with team.sessions() as s:
        assert s.get(HandoffArea, team.area.id).last_member_id is None


async def test_notify_skips_members_without_toggle(team):
    with team.sessions() as s:
        s.get(TeamMember, team.members[0].id).whatsapp_notify = False
        s.commit()
    assert (await notify(team)).member_id == team.members[1].id


async def test_notify_round_robin_rotates(team):
    with team.sessions() as s:
        area = s.get(HandoffArea, team.area.id)
        area.strategy, area.last_member_id = "round_robin", team.members[0].id
        s.commit()
    assert (await notify(team)).member_id == team.members[1].id
    assert (await notify(team)).member_id == team.members[2].id


async def test_notify_account_failure_does_not_try_everyone(team):
    update_account(team, status="disconnected")
    notice = await notify(team)
    assert notice.error == {"reason": "account_disconnected"}
    assert team.fake.sent == []
    assert len(event_list(team.sessions, "handoff.whatsapp_failed")) == 1


async def test_notify_token_rejected_does_not_try_everyone(team):
    team.fake.fail["543515551111"] = GraphError("bad token", code=190, status=401)
    notice = await notify(team)
    assert notice.error["reason"] == "token_rejected"
    assert len(event_list(team.sessions, "handoff.whatsapp_failed")) == 1


async def test_notify_without_candidates(team):
    with team.sessions() as s:
        for m in s.scalars(select(TeamMember).where(TeamMember.client_id == team.client_id)):
            m.whatsapp_notify = False
        s.commit()
    assert (await notify(team)).error == {"reason": "no_members"}
    assert event_list(team.sessions, "handoff.whatsapp_failed")[-1].area_id == team.area.id


def remove(w, member, how) -> None:
    with w.sessions() as s:
        row = s.get(TeamMember, member.id)
        if how == "desactivado":
            row.active = False
        else:
            handoff_service.delete_member(s, row)
        s.commit()


@pytest.mark.parametrize("how", ["borrado", "desactivado"])
async def test_notify_skips_who_left_during_the_previous_send(team, how):
    """Lleva el telefono: el segundo se fue mientras Meta rechazaba al primero, y sigue con el tercero."""
    real = team.fake.send_template

    async def send_template(pnid, to, name, language, params=None):
        if to == "543515551111":
            remove(team, team.members[1], how)
            raise GraphError("rechazado", code=131026, status=400)
        return await real(pnid, to, name, language, params)

    team.fake.send_template = send_template
    notice = await notify(team, {"cliente": "+5493510000000"})
    assert (notice.ok, notice.member_id) == (True, team.members[2].id)
    assert [m[1] for m in team.fake.sent] == ["543515553333"]
    assert [e.team_member_id for e in event_list(team.sessions, "handoff.whatsapp_failed")] == [team.members[0].id]
    assert [e.team_member_id for e in event_list(team.sessions, "handoff.whatsapp_sent")] == [team.members[2].id]


async def test_notify_with_everyone_gone_is_like_no_candidates(team):
    def leave() -> bool:
        for member in team.members:
            with team.sessions() as s:
                s.get(TeamMember, member.id).active = False
                s.commit()
        return True

    notice = await team_notify.notify_area(team.sessions, team.client_id, team.area.id, {}, None,
                                           graph_factory=team.factory, before_send=leave)
    assert notice == team_notify.Notice(False, error={"reason": "no_members"})
    assert team.fake.sent == [] and out_messages(team.sessions) == []
    [event] = event_list(team.sessions, "handoff.whatsapp_failed")
    assert (event.area_id, event.team_member_id, event.data["reason"]) == (team.area.id, None, "no_members")


async def test_notify_rejected_and_the_rest_gone_keeps_the_rejection(team):
    """Hubo un intento: el motivo es el de Meta y no se suma otra falla."""
    real = team.fake.send_template

    async def send_template(pnid, to, name, language, params=None):
        remove(team, team.members[1], "desactivado")
        remove(team, team.members[2], "desactivado")
        return await real(pnid, to, name, language, params)

    team.fake.send_template = send_template
    team.fake.fail["543515551111"] = GraphError("rechazado", code=131026, status=400)
    notice = await notify(team)
    assert (notice.ok, notice.error["code"]) == (False, 131026)
    assert len(event_list(team.sessions, "handoff.whatsapp_failed")) == 1 and team.fake.sent == []


async def test_notify_does_not_send_if_it_cannot_reread(team, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("sin base")

    monkeypatch.setattr(team_notify, "select", broken)
    assert await notify(team) == team_notify.Notice(False, error={"reason": "internal"})
    assert team.fake.sent == []
    assert ([e.team_member_id for e in event_list(team.sessions, "handoff.whatsapp_failed")]
            == [m.id for m in team.members])


async def test_notify_area_of_another_client(team):
    notice = await team_notify.notify_area(team.sessions, _second_client(team), team.area.id, {}, None,
                                           graph_factory=team.factory)
    assert notice.error == {"reason": "area_missing"}
    assert team.fake.sent == []


async def test_notify_deleted_area(team):
    notice = await team_notify.notify_area(team.sessions, team.client_id, "no-existe", {}, None,
                                           graph_factory=team.factory)
    assert notice.error == {"reason": "area_missing"}


# ---------- recent_notice ----------

def add_message(w, wa_id, type="team_notice", status="sent", hours_ago=0.0, account_id=None, direction="out"):
    with w.sessions() as s:
        s.add(WaMessage(account_id=account_id or w.account_id, direction=direction, wa_id=wa_id, type=type, status=status,
                        created_at=utcnow() - datetime.timedelta(hours=hours_ago)))
        s.commit()


def recent(w, wa_id, hours=24, account_id=None):
    with w.sessions() as s:
        return team_notify.recent_notice(s, account_id or w.account_id, wa_id, hours)


@pytest.mark.parametrize("stored", ["+5493515551111", "5493515551111", "543515551111"])
@pytest.mark.parametrize("incoming", ["+5493515551111", "5493515551111", "543515551111"])
def test_recent_notice_number_forms(team, stored, incoming):
    add_message(team, stored)
    assert recent(team, incoming)


async def test_recent_notice_after_a_real_send(team):
    # El miembro es +549..., el entrante 549... y el destino se manda sin el 9.
    await send(team)
    assert recent(team, "5493515551111")


def test_recent_notice_counts_team_relay(team):
    add_message(team, "5493515551111", type="team_relay")
    assert recent(team, "5493515551111")


@pytest.mark.parametrize("kw", [
    {"hours_ago": 25},
    {"type": "text"},
    {"type": "template"},
    {"status": "failed"},
    {"direction": "in"},
])
def test_recent_notice_does_not_count(team, kw):
    add_message(team, "5493515551111", **kw)
    assert not recent(team, "5493515551111")


def test_recent_notice_other_number_or_account(team, sessions):
    add_message(team, "5493515551111")
    assert not recent(team, "5493515559999")
    assert not recent(team, "5493515551111", account_id="otra-cuenta")
