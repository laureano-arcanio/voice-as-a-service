"""Reparto agente/equipo de la entrante (docs/features/EQUIPO_TELEFONIA.md): el numero team sortea
un porcentaje de las entrantes al agente; brazo, motivo, porcentaje y experimento quedan en call_logs.
Sorteo con generador inyectable; LLM y LiveKit falsos (fixture api)."""
import random

import pytest

from app.models import CallRow, CallStatus, ConversationRow
from app.services import calls as call_service
from app.services.errors import Forbidden

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401
from .test_direct_calls import DID, member, setup

CALLER = "+5493516775617"
WA_ID = "5493515550001"


class FixedRng:
    """random() siempre el mismo valor: 0.0 sortea agente, 0.99 equipo (con percent 50)."""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def draw(api, monkeypatch, value):
    monkeypatch.setattr(call_service, "_RNG", FixedRng(value))


def inbound(api, caller=CALLER, dialed=DID, **kw):
    with api.sessions() as s:
        return call_service.start_inbound(s, api.engine, dialed, caller, **kw)


def split_row(api, conversation_id):
    with api.sessions() as s:
        row = s.get(CallRow, conversation_id)
        return (row.split_arm, row.split_reason, row.split_percent, row.split_experiment,
                row.answered_by, row.status, row.ended_reason)


@pytest.fixture
def split(api, admin):
    """Cliente con un numero team, agente y una persona; reparto al 50 %."""
    c, n, ana, ana_id = setup(api, admin)
    agent = make_agent(admin, c)
    person = member(admin, c["id"], phone="3516775617")
    r = ana.patch(f"{V1}/phone-numbers/{n['id']}",
                  json={"answer_mode": "team", "member_ids": [person["id"]], "agent_id": agent["id"],
                        "agent_percent": 50})
    assert r.status_code == 200, r.text
    return c, n, ana, r.json(), agent


# ---------- el sorteo ----------

def test_split_draw_extremes_and_distribution():
    """0 % nunca y 100 % siempre al agente; el reparto converge a p (10.000 sorteos, ±2 pp)."""
    rng = random.Random(2026)
    assert not call_service.split_draw(0, rng)
    assert call_service.split_draw(100, rng)
    agent = sum(call_service.split_draw(37, rng) for _ in range(10_000))
    assert 3_500 <= agent <= 3_900, agent


def test_draws_agent_and_team_and_registers_the_arm(api, admin, split, monkeypatch):
    c, n, ana, out, agent = split
    assert out["agent_percent"] == 50 and out["split_experiment"] and out["split_started_at"]
    draw(api, monkeypatch, 0.0)
    inbound_team_is_none = inbound(api)
    assert inbound_team_is_none.team is None
    assert split_row(api, inbound_team_is_none.conversation_id)[:5] == \
        ("agent", "random", 50, out["split_experiment"], "agent")
    draw(api, monkeypatch, 0.99)
    to_the_team = inbound(api)
    assert to_the_team.team is not None
    assert split_row(api, to_the_team.conversation_id)[:5] == \
        ("team", "random", 50, out["split_experiment"], "team")


def test_the_same_caller_can_land_in_both_arms(api, admin, split, monkeypatch):
    """El sorteo es por llamada: no depende del que llama, ni del dia ni de la hora."""
    c, n, ana, out, agent = split
    draw(api, monkeypatch, 0.99)
    first = inbound(api).conversation_id
    draw(api, monkeypatch, 0.0)
    second = inbound(api).conversation_id
    assert split_row(api, first)[0] == "team" and split_row(api, second)[0] == "agent"


def test_draws_without_a_caller_number(api, admin, split, monkeypatch):
    """Una entrante sin numero de origen (anonima) tambien se sortea."""
    c, n, ana, out, agent = split
    draw(api, monkeypatch, 0.0)
    assert inbound(api, caller=None).team is None


def test_zero_percent_is_unchanged(api, admin, monkeypatch):
    """Sin reparto (todos los numeros existentes) la entrante al equipo va igual que hoy."""
    c, n, ana, ana_id = setup(api, admin)
    person = member(admin, c["id"], phone="3516775617")
    assert ana.patch(f"{V1}/phone-numbers/{n['id']}",
                     json={"answer_mode": "team", "member_ids": [person["id"]]}).status_code == 200
    draw(api, monkeypatch, 0.0)      # aunque el sorteo dijera agente: no hay reparto
    inbound_call = inbound(api)
    assert inbound_call.team is not None
    assert split_row(api, inbound_call.conversation_id)[:4] == (None, None, None, None)


# ---------- reglas del reparto ----------

def test_team_loop_cuts_even_when_the_draw_says_agent(api, admin, split, monkeypatch):
    """El bucle de la central (un numero del propio cliente) se corta antes del sorteo: no cae en el
    brazo agente, y la rechazada queda sin brazo (no entro al experimento)."""
    c, n, ana, out, agent = split
    own = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541199888777"}).json()
    draw(api, monkeypatch, 0.0)
    with pytest.raises(Forbidden) as e:
        inbound(api, caller=own["e164"])
    assert e.value.code == "team_loop"
    with api.sessions() as s:
        row = s.query(CallRow).filter(CallRow.status == CallStatus.rechazada).one()
    assert row.ended_reason == "team_loop"
    assert (row.split_arm, row.split_reason, row.split_percent, row.split_experiment) == (None, None, None, None)


def test_cap_sends_new_calls_to_the_team(api, admin, split, monkeypatch):
    c, n, ana, out, agent = split
    assert ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"split_max_agent_calls": 1}).status_code == 200
    draw(api, monkeypatch, 0.0)
    first = inbound(api).conversation_id
    assert split_row(api, first)[0] == "agent"
    # Con una activa del brazo agente, la siguiente que sortea agente va al equipo (cap).
    capped = inbound(api)
    assert capped.team is not None
    assert split_row(api, capped.conversation_id)[:2] == ("team", "cap")
    # Terminada la activa, vuelve a haber lugar.
    with api.sessions() as s:
        s.get(CallRow, first).status = CallStatus.finalizada
        s.commit()
    assert split_row(api, inbound(api).conversation_id)[0] == "agent"


def test_archived_agent_goes_to_the_team(api, admin, split, monkeypatch):
    c, n, ana, out, agent = split
    admin.patch(f"{V1}/agents/{agent['id']}", json={"archived": True})
    draw(api, monkeypatch, 0.0)
    to_the_team = inbound(api)
    assert to_the_team.team is not None
    assert split_row(api, to_the_team.conversation_id)[:2] == ("team", "agent_unavailable")


def test_team_without_people_registers_team_unavailable(api, admin, split, monkeypatch):
    """El equipo sin personas ya no es usable: al agente como hoy, con el brazo anotado."""
    c, n, ana, out, agent = split
    person = out["members"][0]
    admin.delete(f"{V1}/team/{person['id']}")
    draw(api, monkeypatch, 0.99)     # aunque el sorteo dijera equipo: no hay equipo
    inbound_call = inbound(api)
    assert inbound_call.team is None
    assert split_row(api, inbound_call.conversation_id)[:4] == \
        ("agent", "team_unavailable", 50, out["split_experiment"])


def test_rejected_call_keeps_its_arm(api, admin, split, monkeypatch):
    """El brazo queda en la fila tambien en las rechazadas (bloqueado despues de sortear agente)."""
    c, n, ana, out, agent = split
    assert ana.post(f"{V1}/blocked-numbers", json={"phone": CALLER}).status_code == 201
    draw(api, monkeypatch, 0.0)
    with pytest.raises(Forbidden) as e:
        inbound(api)
    assert e.value.code == "blocked_number"
    with api.sessions() as s:
        row = s.query(CallRow).filter(CallRow.status == CallStatus.rechazada).one()
    assert (row.split_arm, row.split_reason, row.split_percent) == ("agent", "random", 50)


# ---------- regla de WhatsApp: nunca se sortea ----------

def wa_account(admin, client, agent, dialed=DID):
    r = admin.post(f"{V1}/whatsapp/accounts", json={
        "client_id": client["id"], "agent_id": agent["id"], "phone_number_id": "100000000000001",
        "waba_id": "200000000000001", "display_phone_number": dialed, "name": "Cuenta"})
    assert r.status_code == 201, r.text
    return r.json()


def test_wa_rule_never_sorts(api, admin, split, monkeypatch):
    c, n, ana, out, agent = split
    support = make_agent(admin, c, template="demo_booking", name="Soporte")
    acc = wa_account(admin, c, agent)
    assert admin.put(f"{V1}/whatsapp/accounts/{acc['id']}/routes",
                     json=[{"agent_id": support["id"], "contacts": [WA_ID]}]).status_code == 200
    draw(api, monkeypatch, 0.0)     # aunque el sorteo dijera agente
    by_rule = inbound(api, wa_id=WA_ID)
    assert by_rule.team is None     # atiende el agente de la regla, como hoy
    assert split_row(api, by_rule.conversation_id)[:4] == (None, None, None, None)
    with api.sessions() as s:
        assert s.get(ConversationRow, by_rule.conversation_id).agent_id == support["id"]
    # Regla con el agente archivado: hoy va al equipo, y con reparto tambien (no se sortea).
    admin.patch(f"{V1}/agents/{support['id']}", json={"archived": True})
    archived_rule = inbound(api, wa_id=WA_ID)
    assert archived_rule.team is not None
    assert split_row(api, archived_rule.conversation_id)[:4] == (None, None, None, None)


def test_wa_call_without_a_rule_sorts(api, admin, split, monkeypatch):
    """Llamada de WhatsApp sin regla para el contacto: entra al reparto como una de linea."""
    c, n, ana, out, agent = split
    wa_account(admin, c, agent)
    draw(api, monkeypatch, 0.0)
    inbound_call = inbound(api, wa_id="5493519999999")
    assert inbound_call.team is None
    assert split_row(api, inbound_call.conversation_id)[:2] == ("agent", "random")


# ---------- configuracion: validaciones y vida del experimento ----------

def test_validations(api, admin):
    c, n, ana, ana_id = setup(api, admin)
    person = member(admin, c["id"], phone="3516775617")
    url = f"{V1}/phone-numbers/{n['id']}"
    assert ana.patch(url, json={"answer_mode": "team", "member_ids": [person["id"]]}).status_code == 200
    # Porcentaje sin agente en el numero.
    r = ana.patch(url, json={"agent_percent": 50})
    assert r.status_code == 422 and r.json()["code"] == "agent_required"
    # Rangos.
    for bad in ({"agent_percent": 101}, {"agent_percent": -1}, {"split_max_agent_calls": 0},
                {"split_max_agent_calls": 51}):
        assert ana.patch(url, json=bad).status_code == 422, bad
    # Con answer_mode=agent se ignora y se guarda 0.
    agent = make_agent(admin, c)
    out = ana.patch(url, json={"answer_mode": "agent", "agent_percent": 50}).json()
    assert out["answer_mode"] == "agent" and out["agent_percent"] == 0
    # Con agente arranca el experimento.
    r = ana.patch(url, json={"answer_mode": "team", "agent_id": agent["id"], "agent_percent": 50,
                             "split_max_agent_calls": 3})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["agent_percent"] == 50 and out["split_max_agent_calls"] == 3
    assert out["split_experiment"] and out["split_started_at"]
    # Sacarle el agente a un numero repartido, no; con el reparto en 0, si.
    assert ana.patch(url, json={"agent_id": None}).status_code == 422
    out = ana.patch(url, json={"agent_id": None, "agent_percent": 0}).json()
    assert out["agent_percent"] == 0 and out["agent_id"] is None
    # El tope en null lo quita.
    out = ana.patch(url, json={"agent_percent": 50, "agent_id": agent["id"],
                               "split_max_agent_calls": None}).json()
    assert out["split_max_agent_calls"] is None


def test_other_client_sees_or_changes_nothing(api, admin, split, monkeypatch):
    c, n, ana, out, agent = split
    other = client_user(api, admin, make_client(admin, slug="otro"), email="otro@otro.com")
    assert other.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_percent": 90}).status_code == 404
    assert other.get(f"{V1}/phone-numbers").json() == []
    # El dueño si.
    assert ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_percent": 25}).json()["agent_percent"] == 25


def test_experiment_lifecycle_and_reset(api, admin, split, monkeypatch):
    """Pasar de 0 a >0 arranca el experimento; cambiar el porcentaje no; liberar o reasignar el numero
    limpia los cuatro campos sin tocar las call_logs ya registradas."""
    c, n, ana, out, agent = split
    url = f"{V1}/phone-numbers/{n['id']}"
    draw(api, monkeypatch, 0.99)
    cid = inbound(api).conversation_id
    # Cambiar el porcentaje no cambia la etiqueta; "experimento nuevo" si.
    same = ana.patch(url, json={"agent_percent": 30}).json()
    assert same["split_experiment"] == out["split_experiment"]
    new = ana.patch(url, json={"new_experiment": True}).json()
    assert new["split_experiment"] != out["split_experiment"] and new["split_started_at"]
    assert new["agent_percent"] == 30
    draw(api, monkeypatch, 0.0)
    inbound(api)
    # Liberar: sin reparto ni etiqueta; las filas quedan como estaban.
    released = admin.post(f"{V1}/phone-numbers/{n['id']}/release").json()
    assert (released["agent_percent"], released["split_experiment"],
            released["split_started_at"], released["split_max_agent_calls"]) == (0, None, None, None)
    with api.sessions() as s:
        rows = {r.split_arm for r in s.query(CallRow).filter(CallRow.phone_number_id == n["id"])}
    assert rows == {"team", "agent"}
    # Reasignar a otro cliente: tambien arranca limpio.
    other = make_client(admin, slug="otro")
    reassigned = admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": other["id"]}).json()
    assert (reassigned["agent_percent"], reassigned["split_experiment"]) == (0, None)
