"""Ruteo por contacto de WhatsApp (wa_routes): reglas por cuenta ("estos contactos los
atiende este agente"), en los mensajes y en las llamadas de WhatsApp. La voz (Anura) no
se toca: sigue el agente del numero."""
import pytest
from sqlalchemy import select

from app.agents.templates import reference_data
from app.models import Agent, Client, ConversationRow, Role, User, WaAccount, WaRoute, WaThread
from app.services import agents as agent_service
from app.services import calls as call_service
from app.services import wa_routing
from app.services.errors import NotFound
from app.services.security import hash_password
from app.whatsapp import store as wa_store

from .helpers import FakeLLM
from .test_api import ADMIN, V1, client_user, make_agent, make_client
from .test_whatsapp_service import (
    PNID,
    WA_ID,
    make_wa,
    reply,
    send,
    text_payload,
)

CALLER = "+5493510000000"


@pytest.fixture
def admin(api):
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    return api.login(*ADMIN)


def make_account(admin, client, agent, **extra):
    body = {"client_id": client["id"], "agent_id": agent["id"], "phone_number_id": PNID,
            "waba_id": "200000000000003", "display_phone_number": "+54 9 351 700-2592",
            "name": "Prueba", **extra}
    r = admin.post(f"{V1}/whatsapp/accounts", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def set_routes(admin, account_id, routes):
    return admin.put(f"{V1}/whatsapp/accounts/{account_id}/routes", json=routes)


# ---------- API ----------

def test_routes_api_allows_client_and_replaces(api, admin):
    c = make_client(admin)
    default = make_agent(admin, c)
    support = make_agent(admin, c, template="demo_booking", name="Soporte")
    acc = make_account(admin, c, default)

    r = set_routes(admin, acc["id"], [{"agent_id": support["id"], "contacts": ["+54 9 351 555 1234"]}])
    assert r.status_code == 200, r.text
    (route,) = r.json()
    assert route["agent_id"] == support["id"] and route["agent_name"] == "Soporte"
    assert route["contacts"] == ["5493515551234"]        # solo digitos

    # El listado de cuentas trae las reglas.
    (listed,) = admin.get(f"{V1}/whatsapp/accounts").json()
    assert listed["routes"] == r.json()

    # Reemplazo total: la regla vieja no queda.
    r = set_routes(admin, acc["id"], [{"agent_id": default["id"], "contacts": ["5493515559999"]}])
    assert [x["agent_id"] for x in r.json()] == [default["id"]]

    # El dueño de la cuenta tambien (como el agente por defecto).
    user = client_user(api, admin, c)
    assert set_routes(user, acc["id"], [{"agent_id": support["id"], "contacts": ["5493515551234"]}]).status_code == 200
    # Otro cliente: 404 (no se revela).
    other = client_user(api, admin, make_client(admin, "otro"), email="b@otro.com")
    assert set_routes(other, acc["id"], []).status_code == 404


def test_routes_validation(api, admin):
    c = make_client(admin)
    default = make_agent(admin, c)
    support = make_agent(admin, c, template="demo_booking", name="Soporte")
    acc = make_account(admin, c, default)
    other = make_client(admin, "otro")
    theirs = make_agent(admin, other)
    archived = make_agent(admin, c, template="demo_booking", name="Viejo")
    admin.patch(f"{V1}/agents/{archived['id']}", json={"archived": True})

    assert set_routes(admin, acc["id"],
                      [{"agent_id": theirs["id"], "contacts": ["5493515551234"]}]).status_code == 422
    assert set_routes(admin, acc["id"],
                      [{"agent_id": archived["id"], "contacts": ["5493515551234"]}]).status_code == 422
    assert set_routes(admin, acc["id"],
                      [{"agent_id": support["id"], "contacts": ["no-es-un-telefono"]}]).status_code == 422
    assert set_routes(admin, acc["id"], [{"agent_id": support["id"], "contacts": []}]).status_code == 422
    # El mismo contacto en dos listas (con + y sin + es el mismo numero): 409.
    assert set_routes(admin, acc["id"], [
        {"agent_id": support["id"], "contacts": ["+54 9 351 555 1234"]},
        {"agent_id": default["id"], "contacts": ["543515551234"]},
    ]).status_code == 409
    # El mismo agente en dos reglas: 409.
    assert set_routes(admin, acc["id"], [
        {"agent_id": support["id"], "contacts": ["5493515551234"]},
        {"agent_id": support["id"], "contacts": ["5493515559999"]},
    ]).status_code == 409
    # Nada quedo guardado por los intentos fallidos.
    with api.sessions() as s:
        assert s.scalar(select(WaRoute)) is None


def test_delete_agent_with_routes_is_409(api, admin):
    c = make_client(admin)
    default = make_agent(admin, c)
    support = make_agent(admin, c, template="demo_booking", name="Soporte")
    acc = make_account(admin, c, default)
    set_routes(admin, acc["id"], [{"agent_id": support["id"], "contacts": ["5493515551234"]}])
    assert admin.delete(f"{V1}/agents/{support['id']}").status_code == 409


# ---------- mensajes ----------

def second_agent(sessions, client_id, name="Soporte", slug="soporte"):
    with sessions() as s:
        client = s.get(Client, client_id)
        agent = agent_service.create_agent(s, client, name=name, slug=slug, description="",
                                           definition=reference_data("demo_booking_classic"),
                                           template_id=None, user_id=None)
        s.commit()
        return agent.id


def route_contact(sessions, account_id, agent_id, contacts):
    with sessions() as s:
        account = s.get(WaAccount, account_id)
        wa_routing.set_routes(s, account, [(agent_id, contacts)])
        s.commit()


def conversations(sessions):
    with sessions() as s:
        return list(s.scalars(select(ConversationRow).order_by(ConversationRow.created_at)))


async def test_message_routed_by_contact(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Lo atiende soporte."), reply("Lo atiende el numero.")))
    support = second_agent(sessions, w.client_id)
    route_contact(sessions, w.account_id, support, [WA_ID])

    await send(w, text_payload("hola", "wamid.r1"))
    (conv,) = conversations(sessions)
    assert conv.agent_id == support

    # Otro contacto: el agente por defecto de la cuenta.
    payload = text_payload("hola", "wamid.r2")
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["from"] = "5493519999999"
    payload["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"] = "5493519999999"
    await send(w, payload)
    assert {c.agent_id for c in conversations(sessions)} == {support, w.agent_id}


async def test_rule_wins_over_an_open_thread(sessions):
    """Agregar una regla manda al contacto al agente nuevo sin esperar a que el hilo venza."""
    w = make_wa(sessions, llm=FakeLLM(reply("Uno."), reply("Dos.")))
    await send(w, text_payload("hola", "wamid.t1"))
    (first,) = conversations(sessions)
    assert first.agent_id == w.agent_id

    support = second_agent(sessions, w.client_id)
    route_contact(sessions, w.account_id, support, [WA_ID])
    await send(w, text_payload("sigo", "wamid.t2"))

    rows = conversations(sessions)
    assert [c.agent_id for c in rows] == [w.agent_id, support]
    with sessions() as s:
        old = s.get(WaThread, first.id)
        assert old.closed_at is not None and s.get(WaThread, rows[1].id) is not None


async def test_archived_rule_agent_falls_back_to_the_account(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola.")))
    support = second_agent(sessions, w.client_id)
    route_contact(sessions, w.account_id, support, [WA_ID])
    with sessions() as s:
        agent_service.set_archived(s.get(Agent, support), True)
        s.commit()
    await send(w, text_payload("hola", "wamid.a1"))
    (conv,) = conversations(sessions)
    assert conv.agent_id == w.agent_id


# ---------- llamadas (WhatsApp por SIP) ----------

def wa_call(api, dialed, wa_id=None, caller=CALLER):
    with api.sessions() as s:
        return call_service.start_inbound(s, api.engine, dialed, caller, wa_id=wa_id)


def test_wa_call_routed_by_contact(api, admin):
    c = make_client(admin)
    default = make_agent(admin, c)
    support = make_agent(admin, c, template="demo_booking", name="Soporte")
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+543517002592",
                                            "agent_id": default["id"]})
    acc = make_account(admin, c, default)
    set_routes(admin, acc["id"], [{"agent_id": support["id"], "contacts": [WA_ID]}])

    # Llamada de WhatsApp de un contacto de la regla: lo atiende su agente.
    inbound = wa_call(api, "+543517002592", wa_id=WA_ID)
    assert admin.get(f"{V1}/calls/{inbound.conversation_id}").json()["agent_id"] == support["id"]

    # Contacto sin regla: el agente del numero.
    inbound = wa_call(api, "+543517002592", wa_id="5493519999999")
    assert admin.get(f"{V1}/calls/{inbound.conversation_id}").json()["agent_id"] == default["id"]

    # Llamada de Anura (sin wa_id): las reglas de WhatsApp no aplican.
    inbound = wa_call(api, "+543517002592")
    assert admin.get(f"{V1}/calls/{inbound.conversation_id}").json()["agent_id"] == default["id"]


def test_wa_call_number_without_default_agent_uses_the_rule(api, admin):
    c = make_client(admin)
    default = make_agent(admin, c)
    support = make_agent(admin, c, template="demo_booking", name="Soporte")
    # El numero solo tiene cliente (como un DID que todavia no rutea).
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+543517002631"})
    acc = make_account(admin, c, default, phone_number_id="100000000000009",
                       display_phone_number="+54 9 351 700-2631")
    set_routes(admin, acc["id"], [{"agent_id": support["id"], "contacts": [WA_ID]}])

    inbound = wa_call(api, "+543517002631", wa_id=WA_ID)
    assert admin.get(f"{V1}/calls/{inbound.conversation_id}").json()["agent_id"] == support["id"]

    # Sin regla que aplique no hay agente que atienda.
    with api.sessions() as s, pytest.raises(NotFound):
        call_service.start_inbound(s, api.engine, "+543517002631", CALLER)


def test_account_matching_ignores_format_and_the_mobile_9(api, admin):
    """El numero visible de Meta (+54 9 351 700-2592) matchea el DID de Anura (+543517002592)."""
    c = make_client(admin)
    default = make_agent(admin, c)
    acc = make_account(admin, c, default)
    with api.sessions() as s:
        account = wa_store.account_by_pnid(s, acc["phone_number_id"])
        assert wa_routing.account_for_number(s, "+543517002592").id == account.id
        assert wa_routing.account_for_number(s, "+5493517002592").id == account.id
        assert wa_routing.account_for_number(s, "+5435199999999") is None
