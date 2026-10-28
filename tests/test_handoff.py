"""Equipo, areas de derivacion y eventos (docs/features/EQUIPO_TELEFONIA.md, fase 1)."""
import datetime

from sqlalchemy import select

from app.models import CallRow, CallStatus, Event, HandoffArea
from app.services import calls as call_service
from app.services import handoff

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
)

DID = "+541152630861"


def member(user, cid=None, **body):
    r = user.post(f"{V1}/team", params={"client_id": cid} if cid else None, json={"name": "Juan", **body})
    assert r.status_code == 201, r.text
    return r.json()


# ---------- equipo ----------

def test_team_normalizes_and_validates(api, admin):
    c = make_client(admin)
    m = member(admin, c["id"], phone="351 677-5617")
    assert m["phone"] == "+5493516775617" and m["active"] and "whatsapp" not in m
    # Sin telefono ni usuario del panel, o un telefono de otro pais: no.
    assert admin.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": "X"}).status_code == 422
    r = admin.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": "X", "phone": "+34 600 123 456"})
    assert r.status_code == 422 and "Argentina" in r.json()["detail"]
    # Un campo que no existe (el viejo whatsapp) no alcanza.
    r = admin.post(f"{V1}/team", params={"client_id": c["id"]}, json={"name": "Ana", "whatsapp": "3513962553"})
    assert r.status_code == 422
    # Sin telefono ni usuario del panel no queda.
    assert admin.patch(f"{V1}/team/{m['id']}", json={"phone": None}).status_code == 422
    assert admin.patch(f"{V1}/team/{m['id']}", json={"active": False}).json()["active"] is False
    assert admin.patch(f"{V1}/team/{m['id']}", json={"name": None}).status_code == 422
    assert admin.delete(f"{V1}/team/{m['id']}").status_code == 204
    assert admin.get(f"{V1}/team", params={"client_id": c["id"]}).json() == []


def test_team_is_per_client_and_capped_by_tier(api, admin):
    acme = make_client(admin, max_team_members=1)
    other = make_client(admin, slug="otro")
    theirs = member(admin, other["id"], phone="3511111111")
    user = client_user(api, admin, acme)
    member(user, phone="3516775617")
    r = user.post(f"{V1}/team", json={"name": "Otra", "phone": "3512222222"})
    assert r.status_code == 429 and r.json()["code"] == "team_members_limit"
    assert [m["phone"] for m in user.get(f"{V1}/team").json()] == ["+5493516775617"]
    assert user.patch(f"{V1}/team/{theirs['id']}", json={"name": "x"}).status_code == 404
    assert user.get(f"{V1}/team", params={"client_id": other["id"]}).status_code == 403


# ---------- areas ----------

def test_area_crud_members_and_messages(api, admin):
    c = make_client(admin)
    a, b = member(admin, c["id"], phone="3511111111"), member(admin, c["id"], name="Ana", phone="3512222222")
    theirs = member(admin, make_client(admin, slug="otro")["id"], phone="3513333333")
    body = {"name": "Ventas", "description": "Precios y presupuestos", "member_ids": [b["id"], a["id"]],
            "messages": {"busy": "Ventas está ocupado, llamá en un rato.",
                         "transfer": handoff.DEFAULT_MESSAGES["transfer"]}}
    r = admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]}, json=body)
    assert r.status_code == 201, r.text
    area = r.json()
    assert area["member_ids"] == [b["id"], a["id"]] and area["return_digits"] == "2"
    assert area["ring_seconds"] == 20 and area["on_person_hangup"] == "resume" and area["open_now"]
    # Solo se guardan los mensajes que cambian el default.
    assert area["messages"] == {"busy": "Ventas está ocupado, llamá en un rato."}

    assert admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]},
                      json={"name": "ventas"}).status_code == 409
    bad = [{"member_ids": [theirs["id"]]}, {"member_ids": [a["id"], a["id"]]}, {"messages": {"hola": "x"}},
           {"return_digits": "*9"}, {"return_digits": "1"}, {"schedule": {"tz": "Marte/Olimpo"}},
           {"schedule": {"week": {"mon": [["18:00", "09:00"]]}}},
           {"schedule": {"week": {"mon": [["09:00", "13:00"], ["12:00", "18:00"]]}}},
           {"ring_seconds": None}, {"active": None}]
    for patch in bad:
        assert admin.patch(f"{V1}/handoff-areas/{area['id']}", json=patch).status_code == 422, patch

    r = admin.patch(f"{V1}/handoff-areas/{area['id']}", json={
        "return_digits": "#9", "on_person_hangup": "end",
        "schedule": {"week": {"mon": [["09:00", "13:00"], ["16:00", "20:00"]], "sat": [["09:00", "13:00"]]}}})
    assert r.status_code == 200, r.text
    assert r.json()["schedule_text"] == "los lunes de 09:00 a 13:00 y de 16:00 a 20:00, los sábados de 09:00 a 13:00"
    assert admin.patch(f"{V1}/handoff-areas/{area['id']}", json={"schedule": None}).json()["schedule"] is None

    # Borrar una persona la saca del area.
    admin.delete(f"{V1}/team/{b['id']}")
    assert admin.get(f"{V1}/handoff-areas/{area['id']}").json()["member_ids"] == [a["id"]]
    assert admin.get(f"{V1}/handoff-areas/defaults").json()["messages"]["resume"] == "¿Te puedo ayudar con algo más?"
    assert admin.delete(f"{V1}/handoff-areas/{area['id']}").status_code == 204


def test_schedule_open_hours_in_its_timezone():
    sched = handoff.validate_schedule({"week": {"fri": [["09:00", "18:00"]]}, "closed": ["2026-12-25"]})
    utc = datetime.datetime   # utcnow es naive: Argentina es UTC-3
    assert handoff.is_open(sched, utc(2026, 10, 23, 12, 0))       # viernes 09:00 en Argentina
    assert not handoff.is_open(sched, utc(2026, 10, 23, 11, 59))  # 08:59
    assert not handoff.is_open(sched, utc(2026, 10, 23, 21, 0))   # 18:00: el fin no entra
    assert not handoff.is_open(sched, utc(2026, 10, 24, 13, 0))   # sabado
    assert not handoff.is_open(sched, utc(2026, 12, 25, 13, 0))   # viernes cerrado
    assert handoff.is_open(None)


def test_candidates_order_round_robin_and_hours(api, admin):
    c = make_client(admin)
    ids = [member(admin, c["id"], name=n, phone=f"35100000{i:02d}")["id"] for i, n in enumerate("ABC")]
    user_id = admin.post(f"{V1}/users", json={"email": "d@acme.com", "password": "cliente-password-1",
                                             "role": "client", "client_id": c["id"]}).json()["id"]
    panel_only = member(admin, c["id"], name="D", user_id=user_id)["id"]
    area = admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]},
                      json={"name": "Ventas", "member_ids": [*ids, panel_only], "strategy": "round_robin"}).json()
    admin.patch(f"{V1}/team/{ids[1]}", json={"active": False})
    with api.sessions() as s:
        row = s.get(HandoffArea, area["id"])
        # Sin telefono (solo usuario del panel) o inactivo no se llama.
        assert [m.name for m in handoff.candidates(s, row)] == ["A", "C"]
        row.last_member_id = ids[0]
        assert [m.name for m in handoff.candidates(s, row)] == ["C", "A"]
        row.strategy = "sequential"
        assert [m.name for m in handoff.candidates(s, row)] == ["A", "C"]
        row.schedule = handoff.validate_schedule({"week": {}})
        assert handoff.candidates(s, row) == []


def test_describe_schedule_groups_days():
    week = {d: [["09:00", "13:00"], ["16:00", "20:00"]] for d in ("mon", "tue", "wed", "thu", "fri")}
    text = handoff.describe_schedule({"week": week | {"sat": [["09:00", "13:00"]]}})
    assert text == "de lunes a viernes de 09:00 a 13:00 y de 16:00 a 20:00, los sábados de 09:00 a 13:00"
    assert handoff.describe_schedule({"week": {"sat": [["10:00", "14:00"]], "sun": [["10:00", "14:00"]]}}) == \
        "sábado y domingo de 10:00 a 14:00"


def test_render_messages():
    text = handoff.render(handoff.DEFAULT_MESSAGES["whisper"], area="Ventas", resumen="Juan, consulta por un split")
    assert text == "Derivación de Ventas: Juan, consulta por un split. Marcá 1 para atender."
    assert handoff.render("Hola {{ persona }}, {{nada}}listo") == "Hola , listo"


# ---------- eventos ----------

def test_call_status_changes_are_events(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": DID, "agent_id": agent["id"]})
    with api.sessions() as s:
        call_service.start_inbound(s, api.engine, DID, "+5493513962553")
        conv = s.scalars(select(CallRow.conversation_id)).one()
        call_service.update_call(s, conv, status=CallStatus.en_curso)
        call_service.update_call(s, conv, status=CallStatus.en_curso)          # sin cambio: sin evento
        call_service.update_call(s, conv, status=CallStatus.finalizada, ended_reason="customer_hangup")
        assert s.scalar(select(Event.client_id).limit(1)) == c["id"]

    events = admin.get(f"{V1}/events", params={"conversation_id": conv}).json()
    assert [e["type"] for e in events][-2:] == ["call.answered", "call.ended"]
    assert events[-1]["data"] == {"mode": "entrante", "status": "finalizada", "reason": "customer_hangup"}
    # Cursor y filtro por prefijo.
    assert admin.get(f"{V1}/events", params={"after_id": events[-1]["id"]}).json() == []
    assert admin.get(f"{V1}/events", params={"type": "handoff."}).json() == []
    assert [e["type"] for e in admin.get(f"{V1}/events", params={"type": "call.ended"}).json()] == ["call.ended"]
    # Otro cliente no los ve.
    other = client_user(api, admin, make_client(admin, slug="otro"), email="x@otro.com")
    assert other.get(f"{V1}/events").json() == []


def test_messages_have_time(api, admin):
    from app.conversation.models import Message
    m = Message(role="user", text="hola")
    assert m.at is not None and m.at.tzinfo is not None
    assert Message.model_validate({"role": "user", "text": "viejo", "at": None}).at is None
