"""Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md): saliente de una persona, timbre en el panel, presencia,
configuracion de los numeros y ruteo de las entrantes al equipo. LiveKit simulado (fixture api)."""
import datetime

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app import legal
from app.config import settings
from app.db import utcnow
from app.models import (
    CallMode,
    CallRing,
    CallRow,
    CallStatus,
    Contact,
    ContactOptout,
    ConversationRow,
    LegalAcceptance,
    UserPresence,
)
from app.services import calls as call_service
from app.services import direct_calls, livekit, quota
from app.services.errors import NotFound

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)
from .test_handoff import member

DID = "+541152630861"
HDR = "X-Atentina-Client"


def accept_terms(user):
    """El usuario acepta las condiciones y la politica vigentes (el modal del panel): sin eso el cliente no llama
    ni atiende (403 terms_pending)."""
    body = {"terms_version": legal.current("terms").version, "privacy_version": legal.current("privacy").version}
    r = user.post(f"{V1}/auth/me/legal", json=body)
    assert r.status_code == 200 and r.json()["legal_pending"] == [], r.text
    return user


def setup(api, admin, accept=True, **tier):
    """Un cliente con llamadas directas, un numero y una usuaria (Ana) con sesion, que acepto las condiciones
    vigentes (accept=False: no)."""
    c = make_client(admin, direct_calls=tier.pop("direct_calls", True), **tier)
    n = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": DID}).json()
    ana = client_user(api, admin, c)
    if accept:
        accept_terms(ana)
    return c, n, ana, ana.get(f"{V1}/auth/me").json()["id"]


def api_key(api, admin, client):
    key = admin.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": "crm"}).json()["key"]
    return {"Authorization": f"Bearer {key}"}


def add_contact(api, client_id, phone="+5493516775617", name="Juan", optout=False):
    with api.sessions() as s:
        contact = Contact(client_id=client_id, phone=phone, name=name)
        s.add(contact)
        if optout:
            s.add(ContactOptout(client_id=client_id, phone=phone, channel="voice", source="manual"))
        s.commit()
        return contact.id


# ---------- saliente ----------

def test_outbound_from_the_panel(api, admin, monkeypatch):
    c, n, ana, ana_id = setup(api, admin)
    contact_id = add_contact(api, c["id"])
    tokens = []
    monkeypatch.setattr(livekit, "user_participant_token", lambda room, identity, name: tokens.append(
        (room, identity, name)) or "tok")
    r = ana.post(f"{V1}/direct-calls", json={"contact_id": contact_id})
    assert r.status_code == 201, r.text
    out = r.json()
    cid = out["conversation_id"]
    assert out["token"] == "tok" and out["join_url"] is None and out["room"] == f"call-{cid}"
    assert out["status"] == "pendiente"
    assert tokens == [(f"call-{cid}", f"user-{ana_id}", "ana@acme.com")]
    meta = api.dispatched[-1]
    assert meta["direct"] is True and meta["phone"] == "+5493516775617" and meta["from_number"] == DID
    assert meta["user_identity"] == f"user-{ana_id}" and meta["join_timeout_seconds"] == 30
    assert meta["recording_notice"] is False and meta["max_duration_seconds"] > 0
    with api.sessions() as s:
        call, conv = s.get(CallRow, cid), s.get(ConversationRow, cid)
        assert call.mode == CallMode.directa and call.user_id == ana_id and call.phone_number_id == n["id"]
        assert not call.opted_out_confirmed
        assert conv.agent_id is None and conv.agent_version is None and conv.channel == "voice"
    # Queda en la lista, con quien llamo, y se filtra por tipo y usuario.
    items = ana.get(f"{V1}/calls", params={"mode": "directa", "user_id": ana_id}).json()["items"]
    assert [(i["id"], i["user_name"], i["agent_id"]) for i in items] == [(cid, "ana@acme.com", None)]
    assert ana.get(f"{V1}/calls", params={"answered_by": "team"}).json()["items"] == []
    detail = ana.get(f"{V1}/calls/{cid}")
    assert detail.status_code == 200
    info = detail.json()["call"]
    assert (info["user_id"], info["user_name"], info["answered_by"]) == (ana_id, "ana@acme.com", None)
    assert info["opted_out_confirmed"] is False
    # Con un numero suelto tambien, y el aviso de grabacion del cliente viaja en la metadata.
    assert ana.put(f"{V1}/clients/{c['id']}/direct-call-settings",
                   json={"recording_notice": True}).json() == {"recording_notice": True}
    assert ana.get(f"{V1}/clients/{c['id']}/direct-call-settings").json() == {"recording_notice": True}
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+54 9 351 111-2222"})
    assert r.status_code == 201, r.text
    assert api.dispatched[-1]["phone"] == "+5493511112222" and api.dispatched[-1]["recording_notice"] is True


def test_calls_list_resolves_the_contact_and_filters_by_phone(api, admin):
    """Las directas no tienen campos: el nombre sale de la agenda por el telefono (tambien la entrante del equipo,
    con el caller como llega de Anura). GET /calls filtra por `phone` (normalizado) y por `contact_id`."""
    c, n, ana, ana_id = setup(api, admin)
    juan = add_contact(api, c["id"])
    out = ana.post(f"{V1}/direct-calls", json={"contact_id": juan}).json()["conversation_id"]
    other = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"}).json()["conversation_id"]
    member(admin, c["id"], name="Ana", user_id=ana_id, whatsapp="3510000000")
    person = ana.get(f"{V1}/team").json()[0]
    assert ana.patch(f"{V1}/phone-numbers/{n['id']}",
                     json={"answer_mode": "team", "member_ids": [person["id"]]}).status_code == 200
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "5493516775617").conversation_id
    items = {i["id"]: i for i in ana.get(f"{V1}/calls").json()["items"]}
    assert (items[out]["contact_name"], items[out]["contact_id"]) == ("Juan", juan)
    assert (items[inbound]["contact_name"], items[inbound]["contact_id"]) == ("Juan", juan)
    assert (items[other]["contact_name"], items[other]["contact_id"]) == (None, None)
    info = ana.get(f"{V1}/calls/{inbound}").json()["call"]
    assert (info["contact_id"], info["contact_name"]) == (juan, "Juan")
    # Filtros: el mismo numero escrito de otra forma, el contacto, y los dos a la vez.
    by_phone = ana.get(f"{V1}/calls", params={"phone": "351 677-5617"}).json()
    assert sorted(i["id"] for i in by_phone["items"]) == sorted([out, inbound]) and by_phone["total"] == 2
    by_contact = ana.get(f"{V1}/calls", params={"contact_id": juan}).json()["items"]
    assert sorted(i["id"] for i in by_contact) == sorted([out, inbound])
    both = ana.get(f"{V1}/calls", params={"contact_id": juan, "phone": "+5493511112222"}).json()
    assert both == {"items": [], "total": 0}
    assert ana.get(f"{V1}/calls", params={"phone": "+5493511112222"}).json()["total"] == 1
    r = ana.get(f"{V1}/calls", params={"phone": "abc"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_phone"
    # Un contacto de otro cliente: 404.
    other_client = make_client(admin, slug="otro")
    assert ana.get(f"{V1}/calls", params={"contact_id": add_contact(api, other_client["id"])}).status_code == 404


def test_outbound_by_api_key_needs_a_user_and_gives_join_url(api, admin):
    c, _, ana, ana_id = setup(api, admin)
    headers = api_key(api, admin, c)
    body = {"phone": "+5493516775617"}
    r = api.client.post(f"{V1}/direct-calls", json=body, headers=headers)
    assert r.status_code == 422 and r.json()["code"] == "user_required"
    other = make_client(admin, slug="otro", direct_calls=True)
    stranger = client_user(api, admin, other, email="x@otro.com").get(f"{V1}/auth/me").json()["id"]
    r = api.client.post(f"{V1}/direct-calls", json={**body, "user_id": stranger}, headers=headers)
    assert r.status_code == 422 and r.json()["code"] == "invalid_user"
    r = api.client.post(f"{V1}/direct-calls", json={**body, "user_id": ana_id}, headers=headers)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["token"] is None and out["join_url"].endswith(f"/telefono/llamada/{out['conversation_id']}")
    assert api.dispatched[-1]["join_timeout_seconds"] == 120
    # Entra desde el panel con su sesion; otro usuario del cliente no.
    joined = ana.post(f"{V1}/direct-calls/{out['conversation_id']}/join")
    assert joined.status_code == 200 and joined.json()["token"]
    pedro = client_user(api, admin, c, email="pedro@acme.com")
    r = pedro.post(f"{V1}/direct-calls/{out['conversation_id']}/join")
    assert r.status_code == 403 and r.json()["code"] == "not_your_call"
    assert api.client.post(f"{V1}/direct-calls/{out['conversation_id']}/join", headers=headers).status_code == 403
    # Desde el panel, user_id de otro no.
    r = ana.post(f"{V1}/direct-calls", json={**body, "user_id": "otro"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_user"


def test_opted_out_needs_confirmation_and_is_recorded(api, admin):
    c, _, ana, _ = setup(api, admin)
    contact_id = add_contact(api, c["id"], optout=True)
    r = ana.post(f"{V1}/direct-calls", json={"contact_id": contact_id})
    assert r.status_code == 409 and r.json()["code"] == "opted_out"
    r = ana.post(f"{V1}/direct-calls", json={"contact_id": contact_id, "confirm_opted_out": True})
    assert r.status_code == 201, r.text
    item = ana.get(f"{V1}/calls", params={"mode": "directa"}).json()["items"][0]
    assert item["opted_out_confirmed"] is True


def test_blocked_plan_support_and_validation(api, admin):
    c, _, ana, _ = setup(api, admin)
    admin.post(f"{V1}/blocked-numbers", params={"client_id": c["id"]}, json={"phone": "+5493516775617"})
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493516775617"})
    assert r.status_code == 403 and r.json()["code"] == "blocked_number"
    assert ana.post(f"{V1}/direct-calls", json={}).status_code == 422
    r = ana.post(f"{V1}/direct-calls", json={"phone": "12"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_phone"
    assert ana.post(f"{V1}/direct-calls", json={"contact_id": "nope"}).status_code == 404
    # Un admin en "ver como cliente" no llama, no atiende ni se pone Disponible.
    for method, path, body in (("post", "/direct-calls", {"phone": "+5493511112222"}),
                               ("post", "/direct-calls/x/answer", None), ("post", "/direct-calls/x/decline", None),
                               ("put", "/me/presence", {"available": True})):
        r = getattr(admin, method)(f"{V1}{path}", json=body, headers={HDR: c["id"]})
        assert r.status_code == 403 and r.json()["code"] == "support_read_only", path
    # Sin la funcion en el plan.
    free = make_client(admin, slug="free", direct_calls=False)
    admin.post(f"{V1}/phone-numbers", json={"client_id": free["id"], "e164": "+541152630862"})
    user = client_user(api, admin, free, email="u@free.com")
    r = user.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 429 and r.json()["code"] == "direct_calls_not_in_plan"
    # Sin numero asignado.
    bare = make_client(admin, slug="bare", direct_calls=True)
    user = accept_terms(client_user(api, admin, bare, email="u@bare.com"))
    r = user.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 409 and r.json()["code"] == "no_phone_number"


def test_outbound_minutes_and_channels(api, admin, monkeypatch):
    c, _, ana, _ = setup(api, admin, outbound_minutes=0)
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 429 and r.json()["code"] == "outbound_minutes"
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"outbound_minutes": 1})
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 201 and api.dispatched[-1]["max_duration_seconds"] == 60
    cid = r.json()["conversation_id"]
    with api.sessions() as s:
        # Una directa en curso gasta salientes y ocupa un canal de Anura.
        call = s.get(CallRow, cid)
        call.status, call.started_at = CallStatus.en_curso, utcnow() - datetime.timedelta(seconds=30)
        s.commit()
        client = s.get(CallRow, cid).client_id
        assert quota.busy_channels(s) == 1
        from app.models import Client
        assert 25 <= quota.remaining_seconds(s, s.get(Client, client), CallMode.directa) <= 30
        assert quota.usage(s, s.get(Client, client)).outbound.used_seconds >= 30
    monkeypatch.setattr(quota.settings, "anura_channels", 1)
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"outbound_minutes": None})
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 429 and r.json()["code"] == "no_channel"


def test_hangup_a_direct_call(api, admin, monkeypatch):
    _, _, ana, _ = setup(api, admin)
    cid = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"}).json()["conversation_id"]
    deleted = []

    async def fake_delete(room):
        deleted.append(room)
        return True

    monkeypatch.setattr(livekit, "delete_room", fake_delete)
    r = ana.post(f"{V1}/calls/{cid}/hangup")
    assert r.status_code == 200 and r.json()["ended_reason"] == "hangup_by_user" and deleted == [f"call-{cid}"]


# ---------- entrante en el panel: presencia, timbre, atender ----------

def _inbound_to_team(api, admin, c, n, users):
    """Pone el numero en el equipo con una persona por usuario y crea una entrante."""
    ids = [member(admin, c["id"], name=f"P{i}", user_id=u)["id"] for i, u in enumerate(users)]
    r = admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"answer_mode": "team", "member_ids": ids})
    assert r.status_code == 200, r.text
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493516775617")
    return inbound


def test_presence_ring_answer_and_decline(api, admin):
    c, n, ana, ana_id = setup(api, admin)
    pedro = client_user(api, admin, c, email="pedro@acme.com")
    pedro_id = pedro.get(f"{V1}/auth/me").json()["id"]
    luis = client_user(api, admin, c, email="luis@acme.com")
    luis_id = luis.get(f"{V1}/auth/me").json()["id"]
    inbound = _inbound_to_team(api, admin, c, n, [ana_id, pedro_id, luis_id])
    cid = inbound.conversation_id
    add_contact(api, c["id"], phone="+5493516775617", name="Juan")

    # Disponibles: Ana y Pedro (Luis no mando el pulso; el de Pedro, despues, se vence y vuelve).
    for user in (ana, pedro):
        out = user.put(f"{V1}/me/presence", json={"available": True}).json()
        assert out["available"] and out["last_seen"]
    team = {t["user_id"]: t for t in ana.get(f"{V1}/team/presence").json()}
    assert team[ana_id]["available"] and not team[luis_id]["available"] and not team[ana_id]["busy"]
    assert team[ana_id]["team_member_id"] and team[ana_id]["name"] == "P0"

    with api.sessions() as s:
        assert direct_calls.ring_panel(s, cid, [luis_id, pedro_id, ana_id]) == [pedro_id, ana_id]
    ringing = ana.get(f"{V1}/me/ringing").json()
    assert [(r["conversation_id"], r["phone"], r["contact_name"], r["number_e164"]) for r in ringing] == [
        (cid, "+5493516775617", "Juan", DID)]
    assert luis.get(f"{V1}/me/ringing").json() == []
    # Luis no tiene timbre; Pedro rechaza (sigue sonandole a Ana).
    assert luis.post(f"{V1}/direct-calls/{cid}/answer").status_code == 404
    assert pedro.post(f"{V1}/direct-calls/{cid}/decline").status_code == 204
    assert pedro.get(f"{V1}/me/ringing").json() == []
    r = pedro.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 409 and r.json()["code"] == "not_ringing"
    # Ana atiende: se queda con la llamada; un segundo click le da el mismo acceso.
    r = ana.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 200 and r.json()["token"], r.text
    assert ana.post(f"{V1}/direct-calls/{cid}/answer").status_code == 200
    with api.sessions() as s:
        assert direct_calls.answered_user(s, cid) == ana_id
        assert s.get(CallRow, cid).user_id == ana_id
        statuses = {r.user_id: r.status for r in s.query(CallRing).filter_by(conversation_id=cid)}
        assert statuses == {ana_id: "answered", pedro_id: "declined"}
        # Ocupada: ya no le suena otra.
        assert direct_calls.available_users(s, c["id"], [ana_id, pedro_id]) == [pedro_id]
    assert {t["user_id"]: t["busy"] for t in ana.get(f"{V1}/team/presence").json()}[ana_id] is True
    assert ana.post(f"{V1}/direct-calls/{cid}/join").status_code == 200

    # Sin pulso por mas de 60 s, deja de estar disponible; available=false lo borra.
    with api.sessions() as s:
        s.get(UserPresence, pedro_id).last_seen = utcnow() - datetime.timedelta(seconds=61)
        s.commit()
        assert direct_calls.available_users(s, c["id"], [pedro_id]) == []
    assert ana.put(f"{V1}/me/presence", json={"available": False}).json() == {"available": False, "last_seen": None}
    # Por API key, la presencia no (es del panel).
    r = api.client.put(f"{V1}/me/presence", json={"available": True}, headers=api_key(api, admin, c))
    assert r.status_code == 403


def test_two_people_answer_at_once(api, admin):
    c, n, ana, ana_id = setup(api, admin)
    pedro = client_user(api, admin, c, email="pedro@acme.com")
    pedro_id = pedro.get(f"{V1}/auth/me").json()["id"]
    cid = _inbound_to_team(api, admin, c, n, [ana_id, pedro_id]).conversation_id
    ana.put(f"{V1}/me/presence", json={"available": True})
    pedro.put(f"{V1}/me/presence", json={"available": True})
    with api.sessions() as s:
        assert set(direct_calls.ring_panel(s, cid, [ana_id, pedro_id])) == {ana_id, pedro_id}
    assert pedro.post(f"{V1}/direct-calls/{cid}/answer").status_code == 200
    r = ana.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 409 and r.json()["code"] == "already_answered"
    assert ana.get(f"{V1}/me/ringing").json() == []
    with api.sessions() as s:
        direct_calls.cancel_rings(s, cid)
        assert {r.status for r in s.query(CallRing).filter_by(conversation_id=cid)} == {"answered", "cancelled"}
        # Terminada, no se atiende ni se vuelve a entrar.
        s.get(CallRow, cid).status = CallStatus.finalizada
        s.commit()
    assert pedro.post(f"{V1}/direct-calls/{cid}/join").status_code == 409


def test_answer_and_the_worker_lock_the_call_before_the_rings(api, admin):
    # PostgreSQL: atender (dos a la vez) y apagar o soltar timbres (el worker) toman primero la fila de la
    # llamada (FOR UPDATE) y despues call_rings, siempre en ese orden: sin deadlock (SQLite no lo muestra).
    c, n, ana, ana_id = setup(api, admin)
    cid = _inbound_to_team(api, admin, c, n, [ana_id]).conversation_id
    ana.put(f"{V1}/me/presence", json={"available": True})
    seen: list[str] = []

    def record(state):
        stmt = state.statement
        if state.is_select and stmt._for_update_arg is not None and CallRow.__table__ in stmt.get_final_froms():
            seen.append("lock")
        elif state.is_update or state.is_insert:
            seen.append(stmt.table.name)

    event.listen(Session, "do_orm_execute", record)
    try:
        with api.sessions() as s:
            direct_calls.ring_panel(s, cid, [ana_id])
            ring_panel, seen[:] = list(seen), []
        assert ana.post(f"{V1}/direct-calls/{cid}/answer").status_code == 200
        answer, seen[:] = list(seen), []
        with api.sessions() as s:
            direct_calls.release_answer(s, cid)
            release, seen[:] = list(seen), []
            direct_calls.cancel_rings(s, cid)
            cancel = list(seen)
    finally:
        event.remove(Session, "do_orm_execute", record)
    assert ring_panel[:1] == ["lock"]
    assert answer == ["lock", "call_rings", "call_logs", "call_rings"]
    assert release == ["lock", "call_rings", "call_logs"] and cancel == ["lock", "call_rings"]


def test_stale_rings_do_not_ring_nor_answer(api, admin):
    # Se cayo el worker mientras sonaba (no apago los timbres): un timbre vencido, o el de una llamada colgada,
    # no suena en el panel ni se atiende.
    c, n, ana, ana_id = setup(api, admin)
    cid = _inbound_to_team(api, admin, c, n, [ana_id]).conversation_id
    ana.put(f"{V1}/me/presence", json={"available": True})
    with api.sessions() as s:
        direct_calls.ring_panel(s, cid, [ana_id])
        ring = s.query(CallRing).filter_by(conversation_id=cid).one()
        ring.created_at = utcnow() - datetime.timedelta(seconds=direct_calls.RING_MAX_SECONDS + 1)
        s.commit()
    assert ana.get(f"{V1}/me/ringing").json() == []
    r = ana.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 409 and r.json()["code"] == "not_ringing"
    # Vuelve a sonar (ring_panel lo reabre con la hora nueva), pero la llamada es de hace horas: colgada.
    with api.sessions() as s:
        direct_calls.ring_panel(s, cid, [ana_id])
    assert len(ana.get(f"{V1}/me/ringing").json()) == 1
    with api.sessions() as s:
        s.get(CallRow, cid).created_at = utcnow() - datetime.timedelta(
            seconds=quota.STALE_MARGIN_SECONDS + settings.call_max_duration_seconds + 1)
        s.commit()
    assert ana.get(f"{V1}/me/ringing").json() == []
    r = ana.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 409 and r.json()["code"] == "call_not_active"


def test_ringing_finds_the_contact_of_a_caller_without_plus(api, admin):
    # Anura entrega el caller sin + (o sin el 9): la agenda esta en E.164, como en el listado de llamadas.
    c, n, ana, ana_id = setup(api, admin)
    _inbound_to_team(api, admin, c, n, [ana_id])
    add_contact(api, c["id"], phone="+5493516775617", name="Juan")
    with api.sessions() as s:
        cid = call_service.start_inbound(s, api.engine, DID, "5493516775617").conversation_id
    ana.put(f"{V1}/me/presence", json={"available": True})
    with api.sessions() as s:
        direct_calls.ring_panel(s, cid, [ana_id])
    ring = ana.get(f"{V1}/me/ringing").json()
    assert [(r["phone"], r["contact_name"]) for r in ring if r["conversation_id"] == cid] == [("5493516775617", "Juan")]


# ---------- numeros: quien atiende ----------

def test_phone_number_answering_settings(api, admin):
    c, n, ana, ana_id = setup(api, admin)
    agent = make_agent(admin, c)
    juan = member(admin, c["id"], phone="3516775617")
    panel = member(admin, c["id"], name="Ana", user_id=ana_id, whatsapp="3510000000")
    wa_only = member(admin, c["id"], name="Solo WA", whatsapp="3519999999")
    theirs = member(admin, make_client(admin, slug="otro")["id"], phone="3511111111")
    assert n["answer_mode"] == "team" and n["members"] == [] and n["team_fallback"] == "voicemail"
    url = f"{V1}/phone-numbers/{n['id']}"
    bad = [{"answer_mode": "team", "member_ids": []}, {"member_ids": [theirs["id"]]},
           {"member_ids": [wa_only["id"]]}, {"member_ids": [juan["id"], juan["id"]]},
           {"member_ids": [juan["id"]], "team_fallback": "agent"}, {"ring_seconds": 4}, {"ring_seconds": 61},
           {"member_ids": [juan["id"]], "schedule": {"week": {"mon": [["18:00", "09:00"]]}}},
           {"answer_mode": "robot"}, {"ring_first": None}]
    for body in bad:
        assert ana.patch(url, json=body).status_code == 422, body
    r = ana.patch(url, json={"member_ids": [panel["id"], juan["id"]], "ring_first": "panel", "ring_seconds": 15,
                             "schedule": {"week": {"mon": [["09:00", "18:00"]]}}, "agent_id": agent["id"],
                             "team_fallback": "agent", "team_fallback_message": "  Ahora no podemos.  "})
    assert r.status_code == 200, r.text
    out = r.json()
    assert [m["id"] for m in out["members"]] == [panel["id"], juan["id"]]
    assert out["members"][0] == {"id": panel["id"], "name": "Ana", "phone": None, "user_id": ana_id}
    assert out["ring_first"] == "panel" and out["ring_seconds"] == 15 and out["team_fallback"] == "agent"
    assert out["schedule"]["week"] == {"mon": [["09:00", "18:00"]]}
    assert out["team_fallback_message"] == "Ahora no podemos." and out["agent_name"] == "Ventas"
    # Sacarle el agente con el respaldo en el agente, no.
    r = ana.patch(url, json={"agent_id": None})
    assert r.status_code == 422 and r.json()["code"] == "agent_required"
    assert ana.patch(url, json={"answer_mode": "agent"}).json()["answer_mode"] == "agent"
    # Borrar una persona la saca del numero; liberar el numero vuelve al default.
    admin.delete(f"{V1}/team/{juan['id']}")
    assert [m["id"] for m in ana.get(f"{V1}/phone-numbers").json()[0]["members"]] == [panel["id"]]
    out = admin.post(f"{V1}/phone-numbers/{n['id']}/release").json()
    assert out["members"] == [] and out["answer_mode"] == "team" and out["schedule"] is None


# ---------- entrantes: equipo o agente ----------

def test_inbound_to_team_agent_or_fallback(api, admin):
    c, n, _, ana_id = setup(api, admin)
    agent = make_agent(admin, c)
    url = f"{V1}/phone-numbers/{n['id']}"
    # Equipo sin personas y sin agente: como hoy un numero sin agente.
    with api.sessions() as s, pytest.raises(NotFound):
        call_service.start_inbound(s, api.engine, DID, "+5493516775617")
    # Equipo sin personas, con agente: va al agente.
    admin.patch(url, json={"agent_id": agent["id"]})
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493516775617")
        assert inbound.team is None and inbound.opening
        assert s.get(CallRow, inbound.conversation_id).answered_by == "agent"
    # Con personas: al equipo, sin agente en la conversacion; solo las que pueden sonar.
    juan = member(admin, c["id"], phone="3516775617")
    ana = member(admin, c["id"], name="Ana", user_id=ana_id, whatsapp="3510000000")
    r = admin.patch(url, json={"member_ids": [ana["id"], juan["id"]], "team_fallback": "agent", "ring_seconds": 25})
    assert r.status_code == 200, r.text
    admin.patch(f"{V1}/team/{juan['id']}", json={"active": False})
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493516775617")
        team = inbound.team
        assert inbound.opening == "" and team is not None
        assert [(p.member_id, p.name, p.phone, p.user_id) for p in team.members] == [(ana["id"], "Ana", None, ana_id)]
        assert (team.ring_first, team.ring_seconds, team.fallback, team.agent_id) == ("phone", 25, "agent",
                                                                                      agent["id"])
        assert team.schedule is None and team.number_e164 == DID
        call, conv = s.get(CallRow, inbound.conversation_id), s.get(ConversationRow, inbound.conversation_id)
        assert call.answered_by == "team" and call.mode == CallMode.entrante and conv.agent_id is None
    items = admin.get(f"{V1}/calls", params={"answered_by": "team"}).json()["items"]
    assert [i["id"] for i in items] == [inbound.conversation_id]
    # answer_mode=agent: al agente aunque tenga personas.
    admin.patch(url, json={"answer_mode": "agent"})
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493516775617")
        assert inbound.team is None and s.get(CallRow, inbound.conversation_id).answered_by == "agent"


def test_inbound_to_team_keeps_blocked_and_quota(api, admin):
    from app.services.errors import Forbidden, QuotaExceeded

    c, n, _, ana_id = setup(api, admin, max_concurrent_calls=1)
    ana = member(admin, c["id"], name="Ana", user_id=ana_id, whatsapp="3510000000")
    admin.patch(f"{V1}/phone-numbers/{n['id']}", json={"member_ids": [ana["id"]]})
    admin.post(f"{V1}/blocked-numbers", params={"client_id": c["id"]}, json={"phone": "+5493513775197"})
    with api.sessions() as s, pytest.raises(Forbidden):
        call_service.start_inbound(s, api.engine, DID, "+5493513775197")
    with api.sessions() as s:
        assert call_service.start_inbound(s, api.engine, DID, "+5493516775617").team is not None
    with api.sessions() as s, pytest.raises(QuotaExceeded):
        call_service.start_inbound(s, api.engine, DID, "+5493516775618")
    rejected = admin.get(f"{V1}/calls", params={"status": "rechazada"}).json()["items"]
    assert sorted(r["ended_reason"] for r in rejected) == ["blocked_number", "concurrency_limit"]
    assert {r["answered_by"] for r in rejected} == {"team"}


def test_tier_direct_calls_flag_and_plan_features(api, admin):
    c, _, ana, _ = setup(api, admin)
    tier = admin.get(f"{V1}/tiers/{c['tier']['id']}").json()
    assert tier["direct_calls"] is True
    assert admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"direct_calls": None}).json()["direct_calls"] is True
    assert ana.get(f"{V1}/plan/features").json()["features"]["direct_calls"]["enabled"] is True
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"direct_calls": False})
    assert ana.get(f"{V1}/plan/features").json()["features"]["direct_calls"]["enabled"] is False


def test_answer_after_the_rings_go_off(api, admin):
    # El worker apago los timbres (paso al celular o al respaldo): atender ya no toma la llamada.
    c, n, ana, ana_id = setup(api, admin)
    cid = _inbound_to_team(api, admin, c, n, [ana_id]).conversation_id
    ana.put(f"{V1}/me/presence", json={"available": True})
    with api.sessions() as s:
        assert direct_calls.ring_panel(s, cid, [ana_id]) == [ana_id]
        direct_calls.cancel_rings(s, cid)
    r = ana.post(f"{V1}/direct-calls/{cid}/answer")
    assert r.status_code == 409 and r.json()["code"] == "not_ringing"
    with api.sessions() as s:
        assert s.get(CallRow, cid).user_id is None


def test_team_answering_needs_the_plan(api, admin):
    # Sin llamadas directas en el plan no se elige el equipo; si el plan las pierde, las entrantes van al agente.
    c, n, ana, ana_id = setup(api, admin, direct_calls=False)
    agent = make_agent(admin, c)
    person = member(admin, c["id"], name="Ana", user_id=ana_id, whatsapp="3510000000")
    url = f"{V1}/phone-numbers/{n['id']}"
    r = ana.patch(url, json={"answer_mode": "team", "member_ids": [person["id"]], "agent_id": agent["id"]})
    assert r.status_code == 429 and r.json()["code"] == "direct_calls_not_in_plan"
    assert ana.patch(url, json={"agent_id": agent["id"], "answer_mode": "agent"}).status_code == 200
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"direct_calls": True})
    assert ana.patch(url, json={"answer_mode": "team", "member_ids": [person["id"]]}).status_code == 200
    with api.sessions() as s:
        assert call_service.start_inbound(s, api.engine, DID, "+5493516775617").team is not None
    admin.patch(f"{V1}/tiers/{c['tier']['id']}", json={"direct_calls": False})
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, DID, "+5493516775617")
        assert inbound.team is None and inbound.opening
        assert s.get(CallRow, inbound.conversation_id).answered_by == "agent"


# ---------- condiciones: sin aceptar la 2026-10-28 (o una posterior) no se llama ni se atiende ----------

def test_direct_calls_need_the_terms_that_cover_them(api, admin, monkeypatch):
    """Plan, seccion 7: la funcion no se habilita hasta que el cliente acepta la version que la cubre (graba
    siempre). Alcanza con que la acepte un usuario del cliente: vale para todos, tambien por API key."""
    c, n, ana, ana_id = setup(api, admin, accept=False)
    agent = make_agent(admin, c)
    person = member(admin, c["id"], name="Ana", user_id=ana_id, whatsapp="3510000000")
    url = f"{V1}/phone-numbers/{n['id']}"
    msg = "Aceptá las condiciones nuevas para usar el teléfono del equipo"
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 403 and r.json()["code"] == "terms_pending" and r.json()["detail"] == msg
    r = api.client.post(f"{V1}/direct-calls", json={"phone": "+5493511112222", "user_id": ana_id},
                        headers=api_key(api, admin, c))
    assert r.status_code == 403 and r.json()["code"] == "terms_pending"
    # Elegir el equipo tampoco (ni el admin); el agente si.
    for who in (ana, admin):
        r = who.patch(url, json={"answer_mode": "team", "member_ids": [person["id"]], "agent_id": agent["id"]})
        assert r.status_code == 403 and r.json()["code"] == "terms_pending"
    assert ana.patch(url, json={"agent_id": agent["id"], "answer_mode": "agent"}).status_code == 200
    # Acepta Pedro (otro usuario del cliente): vale para el cliente.
    accept_terms(client_user(api, admin, c, email="pedro@acme.com"))
    assert ana.patch(url, json={"answer_mode": "team", "member_ids": [person["id"]]}).status_code == 200
    assert ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"}).status_code == 201
    with api.sessions() as s:
        cid = call_service.start_inbound(s, api.engine, DID, "+5493516775617").conversation_id
        assert direct_calls.ring_panel(s, cid, [ana_id]) == []      # ocupada con la saliente
        s.add(CallRing(conversation_id=cid, user_id=ana_id, status="ringing"))
        s.commit()

    # Sale una version nueva de las condiciones: no apaga nada, alcanza con la 2026-10-28 (legal_gate,
    # MIN_DIRECT_CALLS_VERSION). El modal del panel la pide igual (legal_pending).
    original = legal.versions
    old = original("terms")
    newer = legal.Version(old[-1].doc, "2099-01-01", "f" * 64, "texto nuevo")
    monkeypatch.setattr(legal, "versions", lambda doc_id: (*old, newer) if doc_id == "terms" else original(doc_id))
    assert "2099-01-01" in [v["version"] for v in ana.get(f"{V1}/auth/me").json()["legal_pending"]]
    assert ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112223"}).status_code == 201
    assert ana.post(f"{V1}/direct-calls/{cid}/answer").status_code == 200
    with api.sessions() as s:
        assert call_service.start_inbound(s, api.engine, DID, "+5493516775619").team is not None


def test_direct_calls_need_the_2026_10_28_terms(api, admin):
    """Una version anterior a la que cubre las llamadas directas no alcanza: con la 2026-10-25 aceptada (y la
    2026-10-28 de la politica) sigue el 403 y las entrantes van al agente."""
    c, n, ana, ana_id = setup(api, admin, accept=False)
    agent = make_agent(admin, c)
    assert ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_id": agent["id"]}).status_code == 200
    with api.sessions() as s:     # como un cliente que acepto antes de que saliera la 2026-10-28
        for document, version in (("terms", "2026-10-25"), ("privacy", "2026-10-28")):
            s.add(LegalAcceptance(user_id=ana_id, client_id=c["id"], email="ana@acme.com", document=document,
                                  version=version, sha256="0" * 64, statement="", channel="panel"))
        s.commit()
    r = ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"})
    assert r.status_code == 403 and r.json()["code"] == "terms_pending"
    accept_terms(ana)
    assert ana.post(f"{V1}/direct-calls", json={"phone": "+5493511112222"}).status_code == 201
