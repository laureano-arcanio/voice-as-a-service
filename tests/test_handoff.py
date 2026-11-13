"""Equipo, areas de derivacion y eventos (docs/features/EQUIPO_TELEFONIA.md, fase 1)."""
import datetime
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic import command
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.config import settings
from app.conversation.models import Workflow
from app.llm.platform_tools import transfer_call_tool
from app.models import CallRow, CallStatus, Event, HandoffArea, WaAccount
from app.services import calls as call_service
from app.services import events as events_service
from app.services import handoff

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
    make_tier,
)
from .test_migration_0005 import _run

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


def test_rotate_starts_after_the_last_one():
    people = [SimpleNamespace(id=i) for i in "ABC"]
    assert [m.id for m in handoff.rotate(people, "A")] == ["B", "C", "A"]
    assert [m.id for m in handoff.rotate(people, "C")] == ["A", "B", "C"]
    # Sin ultimo o con uno que ya no esta (lo sacaron, se desactivo): desde la primera.
    assert [m.id for m in handoff.rotate(people, None)] == ["A", "B", "C"]
    assert [m.id for m in handoff.rotate(people, "X")] == ["A", "B", "C"]
    assert handoff.rotate([], "A") == []


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


# ---------- ruteo entre areas ----------

def new_area(user, cid, name="Ventas", **body):
    r = user.post(f"{V1}/handoff-areas", params={"client_id": cid}, json={"name": name, **body})
    assert r.status_code == 201, r.text
    return r.json()


def test_defaults_change_nothing(api, admin):
    c = make_client(admin)
    m = member(admin, c["id"], phone="3511111111")
    assert m["whatsapp_notify"] is False
    area = new_area(admin, c["id"])
    assert (area["delivery"], area["whatsapp"]) == ("call", None)
    assert area["after_hours_area_id"] is None and area["no_answer_area_id"] is None
    agent = make_agent(admin, c)
    definition = admin.get(f"{V1}/agents/{agent['id']}").json()["definition"]
    assert "workflows" not in definition
    # Un agente existente se guarda igual: la definicion no gana claves.
    r = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition})
    assert r.status_code == 200, r.text
    drop = ("version",)
    assert {k: v for k, v in r.json()["definition"].items() if k not in drop} == \
        {k: v for k, v in definition.items() if k not in drop}


def test_area_routes_stay_in_the_client(api, admin):
    c, other = make_client(admin), make_client(admin, slug="otro")
    theirs = new_area(admin, other["id"], "Ajena")
    guardia = new_area(admin, c["id"], "Guardia")
    # Otro cliente, al crear y al cambiar, en las dos rutas.
    for key in ("after_hours_area_id", "no_answer_area_id"):
        r = admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]}, json={"name": "X", key: theirs["id"]})
        assert r.status_code == 422 and key in r.json()["detail"]
        assert admin.patch(f"{V1}/handoff-areas/{guardia['id']}", json={key: theirs["id"]}).status_code == 422
        assert admin.patch(f"{V1}/handoff-areas/{guardia['id']}", json={key: "no-existe"}).status_code == 422
        # A si misma, tampoco.
        assert admin.patch(f"{V1}/handoff-areas/{guardia['id']}", json={key: guardia["id"]}).status_code == 422
    entrada = new_area(admin, c["id"], "Entrada", after_hours_area_id=guardia["id"], no_answer_area_id=guardia["id"])
    assert entrada["after_hours_area_id"] == guardia["id"] and entrada["no_answer_area_id"] == guardia["id"]
    # Un ciclo largo se guarda: se corta al derivar.
    r = admin.patch(f"{V1}/handoff-areas/{guardia['id']}", json={"no_answer_area_id": entrada["id"]})
    assert r.status_code == 200, r.text
    admin.patch(f"{V1}/handoff-areas/{guardia['id']}", json={"no_answer_area_id": None})

    # Un area a la que pasa otra no se borra, hasta quitar las dos rutas.
    r = admin.delete(f"{V1}/handoff-areas/{guardia['id']}")
    assert r.status_code == 409 and r.json()["code"] == "area_in_use" and "Entrada" in r.json()["detail"]
    admin.patch(f"{V1}/handoff-areas/{entrada['id']}", json={"after_hours_area_id": None})
    assert admin.delete(f"{V1}/handoff-areas/{guardia['id']}").status_code == 409
    r = admin.patch(f"{V1}/handoff-areas/{entrada['id']}", json={"no_answer_area_id": None})
    assert r.json()["no_answer_area_id"] is None
    assert admin.delete(f"{V1}/handoff-areas/{guardia['id']}").status_code == 204


def test_no_answer_member(api, admin):
    """«Si nadie atiende» con una persona: se guarda, se lee, es excluyente con el área y con los miembros."""
    c, other = make_client(admin), make_client(admin, slug="otro")
    a, b = member(admin, c["id"], phone="3511111111"), member(admin, c["id"], name="Ana", phone="3512222222")
    user_id = admin.post(f"{V1}/users", json={"email": "d@acme.com", "password": "cliente-password-1",
                                             "role": "client", "client_id": c["id"]}).json()["id"]
    sin_tel = member(admin, c["id"], name="Sin", user_id=user_id)   # solo softphone web: sin teléfono
    theirs = member(admin, other["id"], phone="3513333333")
    guardia = new_area(admin, c["id"], "Guardia")
    assert guardia["no_answer_member_id"] is None

    # Crear con persona, que no es del area.
    area = new_area(admin, c["id"], "Ventas", member_ids=[a["id"]], no_answer_member_id=b["id"])
    assert area["no_answer_member_id"] == b["id"]
    assert admin.get(f"{V1}/handoff-areas/{area['id']}").json()["no_answer_member_id"] == b["id"]
    url = f"{V1}/handoff-areas/{area['id']}"

    # Cada 422 nombra el campo en errors[path].
    bad = [{"no_answer_member_id": theirs["id"]}, {"no_answer_member_id": "no-existe"},
           {"no_answer_member_id": sin_tel["id"]},
           {"no_answer_area_id": guardia["id"]},                       # las dos a la vez (estado final)
           {"member_ids": [a["id"], b["id"]]}]                         # la persona pasa a ser miembro
    for patch in bad:
        r = admin.patch(url, json=patch)
        assert r.status_code == 422, patch
        assert [e["path"] for e in r.json()["errors"]] == ["no_answer_member_id"], r.text
    assert admin.get(url).json()["no_answer_member_id"] == b["id"]      # ningun rechazo la cambió

    # Crear con las dos, o con un miembro, tambien se rechaza.
    for body in ({"no_answer_member_id": b["id"], "no_answer_area_id": guardia["id"]},
                 {"no_answer_member_id": b["id"], "member_ids": [b["id"]]}):
        r = admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]}, json={"name": "X", **body})
        assert r.status_code == 422, body
    assert admin.get(f"{V1}/handoff-areas", params={"client_id": c["id"]}).json().__len__() == 2

    # Cambiar de destino en un solo PATCH: la persona sale, entra el area.
    r = admin.patch(url, json={"no_answer_member_id": None, "no_answer_area_id": guardia["id"]})
    assert r.status_code == 200, r.text
    assert (r.json()["no_answer_member_id"], r.json()["no_answer_area_id"]) == (None, guardia["id"])
    r = admin.patch(url, json={"no_answer_area_id": None, "no_answer_member_id": a["id"]})
    assert r.status_code == 422                                          # a es miembro
    r = admin.patch(url, json={"no_answer_area_id": None, "no_answer_member_id": b["id"]})
    assert r.status_code == 200 and r.json()["no_answer_member_id"] == b["id"]
    # null la quita; editar otra cosa no la toca.
    assert admin.patch(url, json={"description": "x"}).json()["no_answer_member_id"] == b["id"]
    assert admin.patch(url, json={"no_answer_member_id": None}).json()["no_answer_member_id"] is None

    # Una persona inactiva no se asigna ni se cambia por ella; una ya guardada que se inactiva no frena el guardado.
    off = member(admin, c["id"], name="Off", phone="3515555555", active=False)
    r = admin.patch(url, json={"no_answer_member_id": off["id"]})
    assert r.status_code == 422 and [e["path"] for e in r.json()["errors"]] == ["no_answer_member_id"]
    admin.patch(url, json={"no_answer_member_id": b["id"]})
    admin.patch(f"{V1}/team/{b['id']}", json={"active": False})
    r = admin.patch(url, json={"no_answer_member_id": b["id"], "description": "x"})
    assert r.status_code == 200 and r.json()["no_answer_member_id"] == b["id"]
    admin.patch(f"{V1}/team/{b['id']}", json={"active": True})

    # Borrar a la persona la limpia del area (SQLite no aplica la FK).
    admin.patch(url, json={"no_answer_member_id": b["id"]})
    assert admin.delete(f"{V1}/team/{b['id']}").status_code == 204
    assert admin.get(url).json()["no_answer_member_id"] is None


def test_no_answer_member_other_client(api, admin):
    c, other = make_client(admin), make_client(admin, slug="otro")
    theirs = member(admin, other["id"], phone="3513333333")
    user = client_user(api, admin, c)
    mine = new_area(user, None, "Mia")
    r = user.patch(f"{V1}/handoff-areas/{mine['id']}", json={"no_answer_member_id": theirs["id"]})
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "no_answer_member_id"
    r = user.post(f"{V1}/handoff-areas", json={"name": "Otra", "no_answer_member_id": theirs["id"]})
    assert r.status_code == 422
    # Y el de otro cliente no ve ni edita el area ajena.
    assert user.patch(f"{V1}/handoff-areas/{new_area(admin, other['id'], 'Ajena')['id']}",
                      json={"no_answer_member_id": None}).status_code == 404


def test_client_user_cannot_route_to_another_client(api, admin):
    c, other = make_client(admin), make_client(admin, slug="otro")
    theirs = new_area(admin, other["id"], "Ajena")
    user = client_user(api, admin, c)
    mine = new_area(user, None, "Mia")
    assert user.patch(f"{V1}/handoff-areas/{mine['id']}", json={"no_answer_area_id": theirs["id"]}).status_code == 422
    assert user.patch(f"{V1}/handoff-areas/{theirs['id']}", json={"no_answer_area_id": mine["id"]}).status_code == 404


def test_call_areas_redirects_and_channel(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    account = wa_account(api, c, agent)
    closed = {"week": {}}
    guardia = new_area(admin, c["id"], "Guardia", schedule=closed)
    entrada = new_area(admin, c["id"], "Entrada", schedule=closed, after_hours_area_id=guardia["id"], whatsapp={
        "account_id": account, "template": {"name": "rotacion", "language": "es_AR"}})
    solo_llamada = new_area(admin, c["id"], "Solo", whatsapp={
        "account_id": account, "call_template": {"name": "llamada", "language": "es_AR"}})
    definition = {**admin.get(f"{V1}/agents/{agent['id']}").json()["definition"], "handoff": {"areas": [
        {"area_id": a["id"]} for a in (guardia, entrada, solo_llamada)]}}
    r = admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": definition})
    assert r.status_code == 200, r.text
    config = Workflow.model_validate(r.json()["definition"]).handoff
    with api.sessions() as s:
        voice = handoff.call_areas(s, c["id"], config)
        text = handoff.call_areas(s, c["id"], config, channel="whatsapp")
    assert [(a["name"], a["redirects"]) for a in voice] == [("Guardia", False), ("Entrada", True), ("Solo", False)]
    assert [a["name"] for a in text] == ["Entrada"]
    # Cerrada sin ruta dice cerrada; con ruta atiende, porque la llamada sigue por la otra area.
    described = transfer_call_tool(voice)["function"]["description"]
    assert "Guardia: con horario a confirmar, cerrada ahora" in described
    assert "Entrada: con horario a confirmar, atiende ahora" in described
    # Una conversacion en curso, guardada sin la clave, sigue funcionando.
    old = [{k: v for k, v in a.items() if k != "redirects"} for a in voice]
    assert "Entrada: con horario a confirmar, cerrada ahora" in transfer_call_tool(old)["function"]["description"]


# ---------- WhatsApp del area ----------

def wa_account(api, client, agent, pnid="111") -> str:
    with api.sessions() as s:
        row = WaAccount(client_id=client["id"], agent_id=agent["id"], phone_number_id=pnid, waba_id="222",
                        display_phone_number="+54 351 000", name="Prueba")
        s.add(row)
        s.commit()
        return row.id


def template(*params):
    return {"name": "equipo", "language": "es_AR", "params": list(params)}


def test_area_whatsapp_rules(api, admin):
    c, other = make_client(admin), make_client(admin, slug="otro")
    account = wa_account(api, c, make_agent(admin, c))
    foreign = wa_account(api, other, make_agent(admin, other), pnid="333")
    area = new_area(admin, c["id"])

    def patch(**body):
        return admin.patch(f"{V1}/handoff-areas/{area['id']}", json=body)

    good = {"account_id": account, "template": template("area")}
    bad = [
        ({"account_id": foreign, "template": template("area")}, "call"),         # cuenta de otro cliente
        ({"account_id": "no-existe", "template": template("area")}, "call"),
        ({"account_id": account}, "call"),                                       # sin plantillas
        ({**good, "wait_seconds": 29}, "call"),
        ({**good, "wait_seconds": 3601}, "call"),
        ({"account_id": account, "template": template("Con Espacio")}, "call"),  # parametro invalido
        ({"account_id": account, "template": template("cliente")}, "call"),      # telefono antes de aceptar
        ({"account_id": account, "call_template": template("cliente")}, "call"),
        ({**good, "call_template": template("cliente")}, "whatsapp"),
        ({"account_id": account, "call_template": template("area")}, "whatsapp"),  # el aviso necesita template
        (None, "whatsapp"),
    ]
    for whatsapp, delivery in bad:
        r = patch(whatsapp=whatsapp, delivery=delivery)
        assert r.status_code == 422, (whatsapp, delivery, r.text)
    assert admin.get(f"{V1}/handoff-areas/{area['id']}").json()["whatsapp"] is None
    # Tampoco cambiando solo el delivery de un area sin plantilla.
    assert patch(delivery="whatsapp").status_code == 422
    assert admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]},
                      json={"name": "Otra", "whatsapp": {"account_id": foreign, "template": template()}}
                      ).status_code == 422

    # Rotacion y complemento: los defaults anidados se completan aunque el PATCH no los mande.
    r = patch(whatsapp={"account_id": account, "template": {"name": "rotacion", "language": "es_AR"},
                        "call_template": template("area", "nota_operador")})
    assert r.status_code == 200, r.text
    assert r.json()["whatsapp"] == {"account_id": account, "wait_seconds": 120,
                                    "template": {"name": "rotacion", "language": "es_AR", "params": []},
                                    "call_template": template("area", "nota_operador")}

    # El aviso lleva cliente; volver a llamada con esa plantilla, no.
    aviso = new_area(admin, c["id"], "Aviso", delivery="whatsapp",
                     whatsapp={"account_id": account, "template": template("cliente", "resumen", "ficha")})
    assert aviso["delivery"] == "whatsapp" and aviso["whatsapp"]["template"]["params"][0] == "cliente"
    r = admin.patch(f"{V1}/handoff-areas/{aviso['id']}", json={"delivery": "call"})
    assert r.status_code == 422 and "cliente" in r.json()["detail"]
    # Sin plantilla, un aviso no queda.
    assert admin.patch(f"{V1}/handoff-areas/{aviso['id']}", json={"whatsapp": None}).status_code == 422
    # Cambiar otra cosa no revalida la cuenta.
    r = admin.patch(f"{V1}/handoff-areas/{aviso['id']}", json={"description": "Consultas"})
    assert r.status_code == 200 and r.json()["whatsapp"]["template"]["name"] == "equipo"
    assert patch(whatsapp=None).json()["whatsapp"] is None


def test_team_whatsapp_notify(api, admin):
    c = make_client(admin)
    m = member(admin, c["id"], phone="3511111111", whatsapp_notify=True)
    assert m["whatsapp_notify"] is True
    assert admin.patch(f"{V1}/team/{m['id']}", json={"whatsapp_notify": False}).json()["whatsapp_notify"] is False
    assert admin.patch(f"{V1}/team/{m['id']}", json={"whatsapp_notify": None}).status_code == 422


def test_new_messages_and_events(admin):
    defaults = admin.get(f"{V1}/handoff-areas/defaults").json()
    assert "nombre" in defaults["variables"]
    # Los mensajes de antes de aceptar y sus variables salen de las constantes del servicio, no de una copia.
    assert defaults["pre_accept_messages"] == list(handoff.PRE_ACCEPT_MESSAGES)
    assert defaults["pre_accept_variables"] == list(handoff.PRE_ACCEPT_VARIABLES)
    assert set(defaults["pre_accept_messages"]) <= set(defaults["messages"])
    assert set(defaults["pre_accept_variables"]) <= set(defaults["variables"])
    assert {"post_call_failed", "operator_ack", "operator_contact", "accepted", "notified", "relay_failed",
            "tap_wait", "tap_taken", "tap_closed"} <= set(defaults["messages"])
    assert {"workflow.pre_call", "workflow.post_call", "handoff.rerouted", "handoff.notified", "handoff.whatsapp_sent",
            "handoff.whatsapp_failed", "handoff.relay_failed"} <= events_service.TYPES
    # Las variables de la conversacion y las del sistema entran con el mismo reemplazo; una que no viene, vacia.
    assert handoff.render("{{nota_operador}} {{call.phone}}. {{vars.x}}listo", nota_operador="Al día",
                          **{"call.phone": "+54911"}) == "Al día +54911. listo"


def test_pre_accept_message_error_marks_the_field(api, admin):
    """Un mensaje de antes de aceptar con una variable de más: el 422 nombra la clave en `detail` (API) y la
    marca en `errors` (UI), sin repetir la clave en el texto del campo."""
    c = make_client(admin)
    area = admin.post(f"{V1}/handoff-areas", params={"client_id": c["id"]}, json={"name": "Ventas"}).json()
    for key in handoff.PRE_ACCEPT_MESSAGES:
        r = admin.patch(f"{V1}/handoff-areas/{area['id']}", json={"messages": {key: "Hola {{cliente}}"}})
        body = r.json()
        assert r.status_code == 422 and body["code"] == "invalid", r.text
        assert key in body["detail"] and "{{area}}, {{persona}}, {{horario}}" in body["detail"]
        assert "antes de aceptar" not in body["detail"]
        assert [e["path"] for e in body["errors"]] == [f"messages.{key}"]
        assert key not in body["errors"][0]["message"]
        assert body["errors"][0]["message"].startswith("Todavía no lleva los datos de la persona")
    r = admin.patch(f"{V1}/handoff-areas/{area['id']}", json={"messages": {"busy": "x" * 501}})
    assert r.status_code == 422 and [e["path"] for e in r.json()["errors"]] == ["messages.busy"]


# ---------- workflows del agente ----------

def post_tool(slug="registrar_cobro", method="POST", **http):
    body = {} if method in ("GET", "DELETE") else {"body": {"type": "object", "properties": {
        "conversation_id": {"type": "string", "value": "{{call.id}}"}}}}
    return {"slug": slug, "type": "http", "definition": {
        "description": "Sin parametros del modelo.",
        "http": {"method": method, "url": f"https://api.acme.com/{slug}", **body, **http}}}


def code_tool(slug="buscar_codigo"):
    return {"slug": slug, "type": "code", "definition": {
        "description": "Sin parametros del modelo.", "allowed_hosts": ["api.acme.com"],
        "parameters": {"type": "object", "properties": {}},
        "code": "export default async function () { return {}; }"}}


@pytest.fixture
def flows(api, admin, monkeypatch):
    """Un agente sin herramientas y `save`, que guarda su definicion con otras claves."""
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    c = make_client(admin, max_tools=None, code_tools=True)
    agent = make_agent(admin, c)
    definition = admin.get(f"{V1}/agents/{agent['id']}").json()["definition"]
    assert not definition.get("tools")

    def tool(body):
        r = admin.post(f"{V1}/clients/{c['id']}/tools", json=body)
        assert r.status_code == 201, r.text

    def save(**keys):
        return admin.put(f"{V1}/agents/{agent['id']}/definition", json={"definition": {**definition, **keys}})

    tool(post_tool("buscar_ficha"))
    tool(post_tool("registrar_cobro"))
    return c, agent, tool, save


def bad_path(r, path):
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "invalid_definition"
    assert path in [e["path"] for e in r.json()["errors"]], r.text


def test_workflows_are_saved_with_their_defaults(flows):
    _, _, _, save = flows
    r = save(workflows={"pre_call": {"tool": "buscar_ficha"}, "post_call": {"tool": "registrar_cobro"}})
    assert r.status_code == 200, r.text
    assert r.json()["definition"]["workflows"] == {
        "pre_call": {"tool": "buscar_ficha", "timeout_ms": 1500},
        "post_call": {"tool": "registrar_cobro", "when": "handoff_accepted"}}
    assert not r.json()["definition"].get("tools")
    r = save(workflows={"post_call": {"tool": "registrar_cobro", "when": "always"}})
    assert r.json()["definition"]["workflows"] == {"post_call": {"tool": "registrar_cobro", "when": "always"}}
    # Lo que no sea un valor conocido no pasa el modelo.
    for bad in ({"post_call": {"tool": "registrar_cobro", "when": "nunca"}},
                {"pre_call": {"tool": "buscar_ficha", "timeout_ms": 199}},
                {"pre_call": {"tool": "buscar_ficha", "timeout_ms": 5001}},
                {"pre_call": {"tool": ""}}):
        assert save(workflows=bad).status_code == 422, bad


def test_workflow_tool_rules(flows):
    c, _, tool, save = flows
    # Inexistente, tambien en un agente sin tools (antes el chequeo salia temprano).
    bad_path(save(workflows={"pre_call": {"tool": "no_existe"}}), "workflows.pre_call.tool")
    # La misma como pre-call y post-call.
    same = save(workflows={"pre_call": {"tool": "buscar_ficha"}, "post_call": {"tool": "buscar_ficha"}})
    bad_path(same, "workflows.post_call.tool")
    assert "«Antes de la conversación» y «Después de la conversación»" in same.text
    # Tambien en las herramientas que ve el modelo.
    bad_path(save(tools=[{"tool": "buscar_ficha"}], workflows={"pre_call": {"tool": "buscar_ficha"}}),
             "workflows.pre_call.tool")
    # Con parametros del modelo.
    tool({"slug": "con_parametro", "type": "http", "definition": {
        "description": "Pide un DNI.", "http": {"method": "POST", "url": "https://api.acme.com/x", "body": {
            "type": "object", "properties": {"dni": {"type": "string", "description": "DNI"}}}}}})
    params = save(workflows={"pre_call": {"tool": "con_parametro"}})
    bad_path(params, "workflows.pre_call.tool")
    assert "herramienta automática" in params.text
    # Sin sus secretos.
    tool(post_tool("con_secreto", auth={"type": "bearer", "secret": "REGISTROS_KEY"}))
    r = save(workflows={"pre_call": {"tool": "con_secreto"}})
    bad_path(r, "workflows.pre_call.tool")
    assert "REGISTROS_KEY" in r.text
    # Post-call: http y no GET. Pre-call: admite las dos.
    tool(code_tool())
    tool(post_tool("leer", method="GET"))
    code = save(workflows={"post_call": {"tool": "buscar_codigo"}})
    get = save(workflows={"post_call": {"tool": "leer"}})
    bad_path(code, "workflows.post_call.tool")
    bad_path(get, "workflows.post_call.tool")
    # Mensajes para el cliente: sin vocabulario interno (post-call, workflow, http).
    for r in (same, params, code, get):
        for word in ("post-call", "pre-call", "workflow", "no GET", "http y"):
            assert word not in " ".join(e["message"] for e in r.json()["errors"]), (word, r.text)
    assert "Después de la conversación" in code.text and "solo lectura" in get.text
    assert save(workflows={"pre_call": {"tool": "buscar_codigo"}}).status_code == 200
    assert save(workflows={"pre_call": {"tool": "leer"}}).status_code == 200


def test_workflow_tool_outside_the_plan(api, admin):
    tier = make_tier(admin, name="baja", max_tools=None, code_tools=True)
    c = make_client(admin, tier=tier)
    r = admin.post(f"{V1}/clients/{c['id']}/tools", json=code_tool())
    assert r.status_code == 201, r.text
    # El plan baja: ya no incluye herramientas de codigo.
    assert admin.patch(f"{V1}/tiers/{tier['id']}", json={"code_tools": False}).status_code == 200
    agent = make_agent(admin, c)
    definition = admin.get(f"{V1}/agents/{agent['id']}").json()["definition"]
    r = admin.put(f"{V1}/agents/{agent['id']}/definition",
                  json={"definition": {**definition, "workflows": {"pre_call": {"tool": "buscar_codigo"}}}})
    bad_path(r, "workflows.pre_call.tool")
    assert "plan" in r.text


def test_workflow_tool_is_in_use(flows, admin):
    c, agent, tool, save = flows
    tool(post_tool("con_secreto", auth={"type": "bearer", "secret": "REGISTROS_KEY"}))
    r = admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "REGISTROS_KEY", "value": "x" * 16})
    assert r.status_code == 201, r.text
    r = save(workflows={"pre_call": {"tool": "con_secreto"}, "post_call": {"tool": "registrar_cobro"}})
    assert r.status_code == 200, r.text
    for slug in ("con_secreto", "registrar_cobro"):
        r = admin.delete(f"{V1}/clients/{c['id']}/tools/{slug}")
        assert r.status_code == 409 and r.json()["code"] == "tool_in_use", slug
    users = admin.get(f"{V1}/clients/{c['id']}/tools/registrar_cobro").json()["used_by"]
    assert [u["id"] for u in users] == [agent["id"]]
    # Sus secretos cuentan como los de cualquier herramienta del agente.
    secrets = admin.get(f"{V1}/agents/{agent['id']}/secrets").json()
    assert [(x["name"], x["used_by"]) for x in secrets] == [("REGISTROS_KEY", ["con_secreto"])]
    r = admin.delete(f"{V1}/agents/{agent['id']}/secrets/REGISTROS_KEY")
    assert r.status_code == 409 and r.json()["code"] == "secret_in_use"
    # Pedir un secreto nuevo tampoco puede romper al agente.
    changed = post_tool("registrar_cobro", auth={"type": "bearer", "secret": "OTRO"})
    r = admin.put(f"{V1}/clients/{c['id']}/tools/registrar_cobro",
                  json={"type": "http", "definition": changed["definition"]})
    assert r.status_code == 422 and r.json()["code"] == "missing_secret"
    # Sin el workflow, se borra.
    assert save().status_code == 200
    assert admin.delete(f"{V1}/clients/{c['id']}/tools/registrar_cobro").status_code == 204


def test_workflow_tools_are_hidden_from_the_model(api, flows):
    from app.services import tools as tools_service
    c, _, _, save = flows
    r = save(workflows={"pre_call": {"tool": "buscar_ficha"}, "post_call": {"tool": "registrar_cobro"}})
    definition = r.json()["definition"]
    with api.sessions() as s:
        assert tools_service.agent_tool_specs(s, c["id"], definition) == []
        assert tools_service.agent_tool_specs(s, c["id"], Workflow.model_validate(definition)) == []


def test_tool_of_another_client_is_rejected(api, admin, flows):
    other = make_client(admin, slug="otro", max_tools=None)
    agent = make_agent(admin, other)
    definition = admin.get(f"{V1}/agents/{agent['id']}").json()["definition"]
    r = admin.put(f"{V1}/agents/{agent['id']}/definition",
                  json={"definition": {**definition, "workflows": {"pre_call": {"tool": "buscar_ficha"}}}})
    bad_path(r, "workflows.pre_call.tool")


def test_old_progress_keys_are_ignored():
    """Las conversaciones guardadas con tool_vars, contact, context, preloaded u opening_guide se siguen leyendo."""
    from app.conversation.models import Progress
    p = Progress.model_validate({"tool_vars": {"a": 1}, "contact": {"nombre": "Ana"}, "context": "x",
                                 "preloaded": ["telefono"], "opening_guide": "Hola"})
    assert p.variables == {} and not hasattr(p, "opening_guide")


# ---------- migracion 0048 ----------

def test_0048_upgrade_downgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0047")
    _run(engine, command.upgrade, "0048")
    columns = {t: {c["name"]: c for c in sa.inspect(engine).get_columns(t)} for t in
               ("conversations", "team_members", "handoff_areas", "handoff_legs", "wa_threads")}
    assert {"post_call_status", "post_call_attempts", "post_call_next_at", "post_call_note"} <= set(
        columns["conversations"])
    assert not columns["team_members"]["whatsapp_notify"]["nullable"]
    assert {"after_hours_area_id", "no_answer_area_id", "delivery", "whatsapp"} <= set(columns["handoff_areas"])
    assert "wamid" in columns["handoff_legs"]
    assert {"handoff_status", "handoff_deadline", "handoff_delivery_tries"} <= set(columns["wa_threads"])
    inspector = sa.inspect(engine)
    assert "ix_conversations_post_call" in [i["name"] for i in inspector.get_indexes("conversations")]
    assert "ix_wa_threads_handoff" in [i["name"] for i in inspector.get_indexes("wa_threads")]
    assert {"handoff_areas"} == {fk["referred_table"] for fk in inspector.get_foreign_keys("handoff_areas")
                                 if fk["constrained_columns"][0].endswith("_area_id")}
    _run(engine, command.downgrade, "0047")
    inspector = sa.inspect(engine)
    assert "wamid" not in {c["name"] for c in inspector.get_columns("handoff_legs")}
    assert "delivery" not in {c["name"] for c in inspector.get_columns("handoff_areas")}
    _run(engine, command.upgrade, "0048")


# ---------- migracion 0052 ----------

def test_0052_upgrade_downgrade(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/mig.db")
    _run(engine, command.upgrade, "0051")
    assert "no_answer_member_id" not in {c["name"] for c in sa.inspect(engine).get_columns("handoff_areas")}
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO clients (id, name, slug, tier_id, active, created_at, updated_at) "
                             "VALUES ('c1', 'C', 'c1', 'pyme', 1, '2026-11-11', '2026-11-11')"))
        conn.execute(sa.text("INSERT INTO handoff_areas (id, client_id, name, created_at, updated_at) "
                             "VALUES ('a1', 'c1', 'Ventas', '2026-11-11', '2026-11-11')"))
    _run(engine, command.upgrade, "0052")
    inspector = sa.inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("handoff_areas")}
    assert columns["no_answer_member_id"]["nullable"]
    assert any(fk["constrained_columns"] == ["no_answer_member_id"] and fk["referred_table"] == "team_members"
               for fk in inspector.get_foreign_keys("handoff_areas"))
    with engine.begin() as conn:   # lo existente queda igual, con la columna nula
        assert conn.execute(sa.text("SELECT no_answer_member_id FROM handoff_areas WHERE id = 'a1'")).scalar() is None
    _run(engine, command.downgrade, "0051")
    assert "no_answer_member_id" not in {c["name"] for c in sa.inspect(engine).get_columns("handoff_areas")}
    _run(engine, command.upgrade, "0052")
