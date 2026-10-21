"""Llamada saliente suelta con contacto de la agenda y motivo (pantalla Llamadas, `POST /calls` con
`contact_id` y `context`): el telefono y los datos salen del contacto y el motivo va al prompt."""
from app.agents.templates import reference_data
from app.conversation.contact import MAX_CONTEXT_CHARS, prompt_block
from app.llm.prompt import build_extraction_prompt, build_user_prompt

from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)

MOTIVO = "Quiero saber el precio de la BJ30 híbrida y si entra en el plan de ahorro. Tengo un Gol 2015 para entregar."


def _agent(admin, client, opening="Hola {{nombre}}, te llamo por tu consulta."):
    definition = reference_data("sales_discovery")
    definition["conversation"] = {**definition["conversation"], "opening": opening}
    return make_agent(admin, client, definition=definition)


def _contact(admin, client, phone="+5493515551234", **kw) -> dict:
    out = admin.post(f"{V1}/contacts", params={"client_id": client["id"]},
                     json={"phone": phone, "name": "Marcelo", "attributes": {"vehiculo": "Gol 2015"}, **kw})
    assert out.status_code == 201, out.text
    return out.json()["contacts"][0]


def test_call_with_contact_and_context(api, admin):
    c = make_client(admin)
    agent, contact = _agent(admin, c), _contact(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "contact_id": contact["id"], "context": MOTIVO})
    assert out.status_code == 201, out.text
    state = api.engine.store.get(out.json()["conversation_id"])
    assert state.messages[0].text == "Hola Marcelo, te llamo por tu consulta."
    assert state.progress.context == MOTIVO
    block = prompt_block(state)
    assert "MOTIVO DEL LLAMADO" in block and MOTIVO in block and "- vehiculo: Gol 2015" in block
    assert MOTIVO in build_extraction_prompt(api.engine.workflow(state), state)
    detail = admin.get(f"{V1}/calls/{state.conversation_id}").json()
    assert detail["context"] == MOTIVO and detail["call"]["phone"] == "+5493515551234"
    assert detail["call"]["mode"] == "saliente"


def test_context_without_contact_and_in_test_mode(api, admin):
    c = make_client(admin)
    agent = _agent(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "context": "x" * MAX_CONTEXT_CHARS}).json()
    state = api.engine.store.get(out["conversation_id"])
    assert out["mode"] == "prueba" and out["join_url"]
    assert state.messages[0].text == "Hola, te llamo por tu consulta."    # sin contacto: la variable se limpia
    assert state.progress.context == "x" * MAX_CONTEXT_CHARS
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"],
                                           "context": "x" * (MAX_CONTEXT_CHARS + 1)}).status_code == 422


def test_structured_prompt_has_the_context(api, admin):
    c = make_client(admin)
    agent = _agent(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234",
                                          "context": MOTIVO}).json()
    state = api.engine.store.get(out["conversation_id"])
    prompt = build_user_prompt(api.engine.workflow(state), state, "Hola")
    assert prompt.index(MOTIVO) < prompt.index("CONVERSATION:")


def test_without_context_nothing_changes(api, admin):
    c = make_client(admin)
    out = admin.post(f"{V1}/calls", json={"agent_id": _agent(admin, c)["id"], "phone": "+5491155551234"}).json()
    state = api.engine.store.get(out["conversation_id"])
    assert state.progress.context is None and "MOTIVO DEL LLAMADO" not in prompt_block(state)
    assert admin.get(f"{V1}/calls/{state.conversation_id}").json()["context"] is None


def test_contact_of_another_client_or_archived(api, admin):
    c, other = make_client(admin), make_client(admin, slug="otro")
    agent = _agent(admin, c)
    foreign = _contact(admin, other)
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "contact_id": foreign["id"]}).status_code == 404
    mine = _contact(admin, c)
    admin.post(f"{V1}/contacts/archive", params={"client_id": c["id"]}, json={"contact_ids": [mine["id"]]})
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "contact_id": mine["id"]}).status_code == 409


def test_opted_out_number_is_not_called(api, admin):
    c = make_client(admin)
    agent, contact = _agent(admin, c), _contact(admin, c)
    admin.post(f"{V1}/contacts/optouts", params={"client_id": c["id"]},
               json={"phone": contact["phone"], "channel": "voice"})
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "contact_id": contact["id"]})
    assert out.status_code == 409 and out.json()["code"] == "opted_out"
