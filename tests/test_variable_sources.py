"""Fuentes de variables (docs/ARQUITECTURA.md, "Variables"): `variables` en POST /calls y POST /conversations, los
datos de la llamada que arma cada creador ({{call.*}}), el catalogo, los templates de herramientas ({{x}}) y que lo
oculto y los secretos no lleguen al LLM ni a los headers. LLM falso; la herramienta llama a la API falsa."""
import asyncio
import json

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.agents.definitions import DbDefinitions
from app.config import settings
from app.conversation import variables
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.conversation.store import ConversationStore
from app.services import calls as calls_service
from app.tools import schema as S
from app.tools.runtime import ToolContext, render
from scripts.tools import mock_api

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)
from .test_motor_tools import Script, llm_with
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)
from .voice_harness import http_tool

PHONE = "+5491155550000"
DID = "+541152630000"


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def definition(prompt="Sos Sofía.", first_message="Hola.", **extra) -> dict:
    """Una definicion propia (no la de un agente de referencia, que cambia con su contenido)."""
    return {"agent": {"name": "Sofía", "language": "es-AR"}, "prompt": prompt, "first_message": first_message,
            **extra}


def named_agent(admin, client, prompt="Sos Sofía. Llamás a {{nombre}} por {{motivo}}. Debe {{deuda}}.",  # noqa: F811
                first_message="Hola {{nombre}}.", **extra):
    return make_agent(admin, client, definition=definition(prompt, first_message, **extra))


# ---------- POST /calls ----------

def test_calls_with_variables_and_call_data(api, admin):  # noqa: F811
    c = make_client(admin)
    number = admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": DID}).json()
    assert number["e164"] == DID
    agent = named_agent(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE,
                                          "variables": {"motivo": "Pidió presupuesto", "nombre": "Ana", "deuda": 125000,
                                                        "al_dia": False, "nada": None}})
    assert out.status_code == 201, out.text
    state = api.engine.store.get(out.json()["conversation_id"])
    p = state.progress
    assert p.variables == {"motivo": "Pidió presupuesto", "nombre": "Ana", "deuda": 125000, "al_dia": False}
    assert set(p.variable_sources.values()) == {"request"}
    assert p.call == {"id": state.conversation_id, "from": DID, "to": PHONE, "phone": PHONE,
                      "direction": "outbound", "mode": "saliente"}
    assert state.messages[0].text == "Hola Ana."


def test_calls_ignores_context(api, admin):  # noqa: F811
    """D3: `context` ya no existe; si llega se ignora y la llamada sale (sin motivo)."""
    c = make_client(admin)
    agent = named_agent(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "context": "Pidió presupuesto"})
    assert out.status_code == 201, out.text
    state = api.engine.store.get(out.json()["conversation_id"])
    assert "motivo" not in state.progress.variables
    assert state.progress.call == {"id": state.conversation_id, "direction": "inbound", "mode": "prueba"}
    assert state.messages[0].text == "Hola."


@pytest.mark.parametrize("values, path", [
    ({"datos": {"a": 1}}, "variables.datos"),
    ({"lista": [1, 2]}, "variables.lista"),
    ({"today": "ayer"}, "variables.today"),
    ({"channel": "fax"}, "variables.channel"),
    ({"call.phone": "+1"}, "variables.call.phone"),
    ({"secrets.TOKEN": "x"}, "variables.secrets.TOKEN"),
    ({"Deuda": "1"}, "variables.Deuda"),
    ({"motivo": "x" * (variables.MAX_VALUE_CHARS + 1)}, "variables.motivo"),
    ({f"v{i}": i for i in range(variables.MAX_VARIABLES + 1)}, "variables"),
])
def test_calls_rejects_bad_variables(api, admin, values, path):  # noqa: F811
    c = make_client(admin)
    agent = named_agent(admin, c)
    for url in (f"{V1}/calls", f"{V1}/conversations"):
        out = admin.post(url, json={"agent_id": agent["id"], "variables": values})
        assert out.status_code == 422, out.text
        body = out.json()
        assert body["code"] == "invalid_variables" and path in [e["path"] for e in body["errors"]]


def test_variables_at_the_limits_are_valid(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = named_agent(admin, c)
    values = {f"v{i}": "x" * variables.MAX_VALUE_CHARS for i in range(variables.MAX_VARIABLES)}
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "variables": values}).status_code == 201


def test_contact_and_request_sources(api, admin):  # noqa: F811
    """El pedido pisa al contacto de la agenda; los dos quedan con su fuente."""
    c = make_client(admin)
    agent = named_agent(admin, c)
    contact = admin.post(f"{V1}/contacts", params={"client_id": c["id"]},
                         json={"phone": PHONE, "name": "Marcelo", "email": "m@x.com"}).json()["contacts"][0]
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "contact_id": contact["id"],
                                          "variables": {"nombre": "Marce", "motivo": "Consulta"}})
    assert out.status_code == 201, out.text
    p = api.engine.store.get(out.json()["conversation_id"]).progress
    assert (p.variables["nombre"], p.variable_sources["nombre"]) == ("Marce", "request")
    assert (p.variables["email"], p.variable_sources["email"]) == ("m@x.com", "contact")
    assert p.call["to"] == PHONE and p.call["direction"] == "outbound"


# ---------- POST /conversations ----------

def test_conversation_with_variables_renders_the_prompt_once(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = named_agent(admin, c, prompt="Sos Sofía. Debe {{deuda}} ({{call.mode}}, {{channel}}). Oculta: [{{x}}].")
    started = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"], "variables": {"deuda": "125000"}})
    assert started.status_code == 201, started.text
    cid = started.json()["conversation_id"]
    state = api.engine.store.get(cid)
    assert state.progress.call == {"id": cid, "direction": "inbound", "mode": "api"}
    # Una oculta (como la deja un assign con hide) nunca va al prompt.
    variables.merge(state, {"x": "secreto-oculto"}, "tool:t", {"x"})
    api.engine.store.save(state)
    api.llm.turns = [AgentTurn(assistant_message="Hola.")]
    assert admin.post(f"{V1}/conversations/{cid}/turns", json={"message": "Hola"}).status_code == 200
    prompt = api.engine.store.get(cid).progress.system_prompt
    assert prompt.endswith("Sos Sofía. Debe 125000 (api, voice). Oculta: [].")
    assert "secreto-oculto" not in prompt


# ---------- quien crea la conversacion arma {{call.*}} ----------

def test_inbound_call_data(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = named_agent(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": DID, "agent_id": agent["id"]})
    with api.sessions() as s:
        inbound = calls_service.start_inbound(s, api.engine, DID, "5491155550000")
    p = api.engine.store.get(inbound.conversation_id).progress
    assert p.call == {"id": inbound.conversation_id, "from": "5491155550000", "to": DID, "phone": "5491155550000",
                      "direction": "inbound", "mode": "entrante"}
    assert variables.render("{{call.from}}>{{call.to}}", api.engine.store.get(inbound.conversation_id)) == \
        f"5491155550000>{DID}"


def test_catalog_same_for_everyone(api, admin):  # noqa: F811
    acme, other = make_client(admin), make_client(admin, slug="otro")
    key = admin.post(f"{V1}/clients/{other['id']}/api-keys", json={"name": "k"}).json()["key"]
    expected = variables.catalog()
    user = client_user(api, admin, acme)
    for get in (admin.get, user.get,
                lambda url: api.client.get(url, headers={"Authorization": f"Bearer {key}"})):
        out = get(f"{V1}/variables/catalog")
        assert out.status_code == 200, out.text
        assert out.json() == expected
    assert {"call.phone", "call.direction", "call.summary", "today"} <= {v["name"] for v in expected["system"]}
    assert api.client.get(f"{V1}/variables/catalog", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_secrets_and_fields_in_the_prompt_are_rejected(api, admin):  # noqa: F811
    c = make_client(admin)
    for prompt in ("Token {{secrets.CRM_TOKEN}}", "Dato {{fields.nombre}}", "Resumen {{call.summary}}"):
        out = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "X", "definition": definition(prompt)})
        assert out.status_code == 422, out.text
        assert "prompt" in [e["path"] for e in out.json()["errors"]]


# ---------- templates de herramientas ----------

@pytest.mark.parametrize("text", ["{{deuda_total}}", "{{call.phone}}", "{{call.direction}}", "{{call.summary}}",
                                  "{{channel}}", "{{today}}", "{{fields.dni}}", "{{secrets.CRM_TOKEN}}"])
def test_template_valid(text):
    S.check_template(text, "x")


@pytest.mark.parametrize("text, message", [("{{vars.deuda}}", "usá {{deuda}}"), ("{{contact.nombre}}", "usá {{nombre}}"),
                                           ("{{call.otro}}", "no existe"), ("{{otro.x}}", "desconocida"),
                                           ("{{channel.x}}", "sin punto")])
def test_template_invalid(text, message):
    with pytest.raises(ValueError, match=message.replace("{", r"\{").replace("}", r"\}")):
        S.check_template(text, "x")


@pytest.mark.parametrize("var", ["today", "now", "channel"])
def test_assign_to_a_system_variable_is_rejected(var):
    with pytest.raises(ValidationError, match="del sistema"):
        S.Assign(var=var, path="x")


@pytest.mark.parametrize("url", ["https://{{dominio}}.ejemplo.com/x", "https://api.ejemplo.com{{puerto}}/x",
                                 "https://{{call.phone}}/x"])
def test_variable_in_the_host_is_rejected(api, admin, url):  # noqa: F811
    c = make_client(admin, max_tools=None)
    out = admin.post(f"{V1}/clients/{c['id']}/tools",
                     json={"slug": "consulta", "type": "http",
                           "definition": {"description": "Consulta.", "http": {"url": url}}})
    assert out.status_code == 422, out.text
    assert "host" in out.text


def test_old_namespaces_are_rejected_on_save(api, admin):  # noqa: F811
    c = make_client(admin, max_tools=None)
    tool = {"slug": "consulta", "type": "http", "definition": {
        "description": "Consulta.", "http": {"url": "https://api.ejemplo.com/x",
                                             "headers": {"X-Deuda": "{{vars.deuda}}"}}}}
    out = admin.post(f"{V1}/clients/{c['id']}/tools", json=tool)
    assert out.status_code == 422 and "{{deuda}}" in out.text
    tool["definition"]["http"]["headers"]["X-Deuda"] = "{{deuda}}"
    assert admin.post(f"{V1}/clients/{c['id']}/tools", json=tool).status_code == 201


def test_render_reads_the_space():
    ctx = ToolContext(conversation_id="c-1", channel="whatsapp", mode="whatsapp", from_=PHONE, phone=PHONE,
                      direction="inbound", summary="Pidió demo", vars={"deuda": 125000, "token": "oculto"},
                      fields={"dni": "30111222"})
    assert render("{{deuda}}|{{token}}|{{call.phone}}|{{call.direction}}|{{channel}}|{{call.summary}}|{{fields.dni}}"
                  "|{{falta}}", ctx) == f"125000|oculto|{PHONE}|inbound|whatsapp|Pidió demo|30111222|"
    assert ctx.call()["direction"] == "inbound" and ctx.call()["summary"] == "Pidió demo"


# ---------- de punta a punta: pre-call oculto, herramienta y LLM ----------

def eco_tool(base):
    """GET /eco devuelve los headers x-* que recibio: una API que devuelve el valor oculto."""
    return {"slug": "ver_pedido", "type": "http", "definition": {
        "description": "Estado de un pedido.",
        "http": {"method": "GET", "url": base + "/eco",
                 "query": {"pedido": {"type": "string", "description": "Número de pedido"}},
                 "headers": {"X-Nota": "{{nota}}", "X-Deuda": "{{deuda}}", "X-Tel": "{{call.phone}}",
                             "X-Dir": "{{call.direction}}"}}}}


def test_hidden_reaches_the_next_tool_and_never_the_llm(api, admin, mock_api_url):  # noqa: F811
    c = make_client(admin, max_tools=None)
    ficha = http_tool("buscar_ficha", mock_api_url + "/identificar", assign=[
        {"var": "nombre", "path": "name"}, {"var": "nota", "path": "record", "hide": True}])
    for t in (ficha, eco_tool(mock_api_url)):
        assert admin.post(f"{V1}/clients/{c['id']}/tools", json=t).status_code == 201
    agent = named_agent(admin, c, prompt="Sos Sofía. Hablás con {{nombre}}. Nota: [{{nota}}].",
                        tools=[{"tool": "ver_pedido"}], workflows={"pre_call": {"tool": "buscar_ficha"}})

    script = Script(("", [("ver_pedido", {"pedido": "123"})]), ("Tu pedido está en camino.", []))
    engine = ConversationEngine(llm_with(script), ConversationStore(api.sessions), DbDefinitions(api.sessions))
    state, _ = engine.start_conversation(agent["id"], c["id"], variables={"request": {"deuda": "125000"}},
                                         call={"phone": PHONE, "to": PHONE, "direction": "outbound",
                                               "mode": "saliente"})
    assert asyncio.run(engine.run_pre_call(state.conversation_id)) == "Hola María Gómez."
    mock_api.RECEIVED.clear()
    asyncio.run(engine.process_turn(state.conversation_id, "¿Cómo va mi pedido 123?"))

    (sent,) = [r for r in mock_api.RECEIVED if r["path"] == "/eco"]
    assert sent["headers"]["x-nota"] == "Ficha: https://fichas.test/c/1"     # la oculta llega a la herramienta
    assert (sent["headers"]["x-deuda"], sent["headers"]["x-tel"], sent["headers"]["x-dir"]) == \
        ("125000", PHONE, "outbound")
    llm_seen = json.dumps(script.requests, ensure_ascii=False)
    # La API la devolvio: el modelo la ve tachada, como un secreto.
    assert "fichas.test" not in llm_seen and "[secreto:variable nota]" in llm_seen and "125000" in llm_seen
    assert "Hablás con María Gómez. Nota: []." in llm_seen
    p = engine.store.get(state.conversation_id).progress
    assert p.hidden_variables == ["nota"] and p.variable_sources["nota"] == "pre_call:buscar_ficha"


# ---------- agente externo: X-Atentina-Variables ----------

def test_external_headers_carry_visible_variables_only():
    from app.conversation.models import ConversationState, Workflow
    from app.llm.external import HEADER_MAX, ExternalAgents, variables_header
    wf = Workflow.model_validate({"id": "ventas", "version": 1, "agent": {"name": "Sofía", "language": "es-AR"},
                                  "prompt": "x"})
    state = ConversationState(conversation_id="c-1", agent_id="ventas", fields={})
    variables.start(state, wf, {"request": {"motivo": "Pidió presupuesto", "nombre": "Ñandú"}},
                    call={"from": DID, "to": PHONE, "phone": PHONE, "direction": "outbound", "mode": "saliente"})
    variables.merge(state, {"token_crm": "xyz-oculto"}, "pre_call:ficha", {"token_crm"})
    headers = ExternalAgents(None).headers(wf, state, None)
    assert json.loads(headers["X-Atentina-Variables"]) == {"motivo": "Pidió presupuesto", "nombre": "Ñandú"}
    assert headers["X-Atentina-Variables"].isascii() and "xyz-oculto" not in json.dumps(headers)
    assert (headers["X-Atentina-From"], headers["X-Atentina-To"], headers["X-Atentina-Direction"],
            headers["X-Atentina-Mode"]) == (DID, PHONE, "outbound", "saliente")
    assert not {"X-Atentina-Contact", "X-Atentina-Context"} & set(headers)
    # Siempre JSON valido y dentro del tope: lo que no entra queda afuera; un texto largo, recortado.
    big = variables_header({"a": "ñ" * 3000, "b": 1, "c": ""})
    assert len(big) <= HEADER_MAX and set(json.loads(big)) == {"a"}
    assert json.loads(variables_header({"a": "x", "b": True, "c": ""})) == {"a": "x", "b": True, "c": ""}


def test_tool_test_takes_example_variables(api, admin, mock_api_url):  # noqa: F811
    c = make_client(admin, max_tools=None)
    body = {"type": "http", "definition": eco_tool(mock_api_url)["definition"], "args": {"pedido": "1"},
            "variables": {"deuda": "125000", "nota": "n"}, "call": {"phone": PHONE, "direction": "outbound"}}
    out = admin.post(f"{V1}/clients/{c['id']}/tools/test", json=body)
    assert out.status_code == 200, out.text
    headers = out.json()["data"]["headers"]
    assert (headers["x-deuda"], headers["x-tel"], headers["x-dir"], headers["x-nota"]) == \
        ("125000", PHONE, "outbound", "n")
    out = admin.post(f"{V1}/clients/{c['id']}/tools/test", json={**body, "variables": {"now": "x"}})
    assert out.status_code == 422 and out.json()["errors"][0]["path"] == "variables.now"
