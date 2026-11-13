"""Llamada saliente suelta con contacto de la agenda y motivo (pantalla Llamadas, `POST /calls` con
`contact_id` y `variables.motivo`): el telefono y los datos salen del contacto y el motivo es la variable {{motivo}}."""
from app.agents.templates import reference_data
from app.conversation.variables import MAX_VALUE_CHARS
from app.llm.prompt import build_extraction_prompt, build_system_prompt

from .test_api import V1, admin, make_agent, make_client  # noqa: F401  (admin: fixture)

MOTIVO = "Quiero saber el precio de la BJ30 híbrida y si entra en el plan de ahorro. Tengo un Gol 2015 para entregar."


def _agent(admin, client, opening="Hola {{nombre}}, te llamo por tu consulta.", prompt_extra="", **extra):
    definition = reference_data("sales_discovery")
    definition["first_message"] = opening
    if prompt_extra:
        definition["prompt"] = definition["prompt"] + prompt_extra
    return make_agent(admin, client, definition=definition, **extra)


def _contact(admin, client, phone="+5493515551234", **kw) -> dict:
    out = admin.post(f"{V1}/contacts", params={"client_id": client["id"]},
                     json={"phone": phone, "name": "Marcelo", "email": "marcelo@x.com", **kw})
    assert out.status_code == 201, out.text
    return out.json()["contacts"][0]


def test_call_with_contact_and_motive(api, admin):
    c = make_client(admin)
    agent, contact = _agent(admin, c), _contact(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "contact_id": contact["id"],
                                          "variables": {"motivo": MOTIVO}})
    assert out.status_code == 201, out.text
    state = api.engine.store.get(out.json()["conversation_id"])
    assert state.messages[0].text == "Hola Marcelo, te llamo por tu consulta."
    assert state.progress.variables["motivo"] == MOTIVO and state.progress.variable_sources["motivo"] == "request"
    assert state.progress.variables["email"] == "marcelo@x.com"
    # El analisis ve las variables visibles como contexto.
    assert MOTIVO in build_extraction_prompt(api.engine.workflow(state), state)
    detail = admin.get(f"{V1}/calls/{state.conversation_id}").json()
    variables = {v["name"]: v["value"] for v in detail["variables"]}
    assert variables["motivo"] == MOTIVO and detail["call"]["phone"] == "+5493515551234"
    assert detail["call"]["mode"] == "saliente"


def test_motive_without_contact_and_in_test_mode(api, admin):
    c = make_client(admin)
    agent = _agent(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"],
                                          "variables": {"motivo": "x" * MAX_VALUE_CHARS}}).json()
    state = api.engine.store.get(out["conversation_id"])
    assert out["mode"] == "prueba" and out["join_url"]
    assert state.messages[0].text == "Hola, te llamo por tu consulta."    # sin contacto: la variable se limpia
    assert state.progress.variables["motivo"] == "x" * MAX_VALUE_CHARS
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"],
                                           "variables": {"motivo": "x" * (MAX_VALUE_CHARS + 1)}}).status_code == 422


def test_the_prompt_has_the_motive_only_where_named(api, admin):
    c = make_client(admin)
    plain, named = _agent(admin, c), _agent(admin, c, prompt_extra="\nMotivo: {{motivo}}", name="Con motivo")
    for agent, present in ((plain, False), (named, True)):
        out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491155551234",
                                              "variables": {"motivo": MOTIVO}}).json()
        state = api.engine.store.get(out["conversation_id"])
        assert (MOTIVO in build_system_prompt(api.engine.workflow(state), "voice", state)) is present


def test_without_motive_nothing_changes(api, admin):
    c = make_client(admin)
    out = admin.post(f"{V1}/calls", json={"agent_id": _agent(admin, c)["id"], "phone": "+5491155551234"}).json()
    state = api.engine.store.get(out["conversation_id"])
    assert "motivo" not in state.progress.variables
    assert "motivo" not in {v["name"] for v in admin.get(f"{V1}/calls/{state.conversation_id}").json()["variables"]}


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
