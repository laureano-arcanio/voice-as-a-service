"""Pruebas del panel con número de quien llama simulado y herramientas automáticas (`caller_phone` y `workflows` en
`POST /calls` y `POST /conversations`): solo con la sesión del panel, el número llega a la llamada, a los campos de
teléfono y a las herramientas ({{call.phone}}), y nunca a la metadata del worker (no se marca)."""
import json

import pytest
from cryptography.fernet import Fernet

from app.agents.templates import reference_data
from app.api.deps import MCP_INTERNAL_HEADER, MCP_INTERNAL_SECRET
from app.config import settings
from app.models import CallRow
from app.tools import runtime

from .test_api import V1, admin, client_user, make_agent  # noqa: F401  (admin: fixture)
from .test_mcp import Mcp, new_key
from .test_oauth import connect, register
from .voice_harness import add_agent, add_tool, identify_tool, new_client

PHONE = "+5493514440000"
BASE = "https://fichas.test"
PHONE_FIELD = {"phone": {"priority": 5, "description": "Teléfono de contacto", "type": "phone", "required": False,
                         "question": "¿Un teléfono?"}}


class Http:
    """El HTTP de las herramientas: guarda los pedidos y contesta lo que haya en replies."""

    def __init__(self):
        self.replies, self.requests = [], []


@pytest.fixture
def http(monkeypatch):
    script = Http()

    async def request(self, method, url, headers, body):
        script.requests.append({"url": url, "body": json.loads(body) if body else None})
        return runtime.Response(200, script.replies.pop(0) if script.replies else {}, False)

    monkeypatch.setattr(runtime.SafeHttp, "request", request)
    return script


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def phone_agent(admin, client):  # noqa: F811
    definition = reference_data("sales_discovery")
    definition["fields"] = {**PHONE_FIELD, **definition["fields"]}
    return make_agent(admin, client, definition=definition)


def pre_call_agent(admin, client):  # noqa: F811
    add_tool(admin, client, identify_tool(BASE))
    return add_agent(admin, client, workflows={"pre_call": {"tool": "buscar_ficha", "timeout_ms": 1500}})


# ---------- voz ----------

def test_voice_test_call_with_simulated_number_does_not_dial(api, admin):  # noqa: F811
    c = new_client(admin)
    agent = phone_agent(admin, c)
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "caller_phone": " +54 9 351 444-0000 ",
                                        "workflows": True})
    assert r.status_code == 201, r.text
    out, meta = r.json(), api.dispatched[-1]
    assert out["mode"] == "prueba" and out["join_url"]
    # El worker decide el modo por la metadata: sin phone ni from_number sigue siendo prueba y no marca.
    assert meta["phone"] is None and meta["from_number"] is None and not meta["trial"] and not meta["loadtest"]
    assert PHONE not in str(meta)
    with api.sessions() as s:
        call = s.get(CallRow, out["conversation_id"])
        assert (call.mode, call.phone, call.phone_number_id) == ("prueba", PHONE, None)
    state = api.engine.store.get(out["conversation_id"])
    assert state.fields["phone"] == PHONE and "phone" in state.progress.preloaded
    assert state.progress.test_workflows is True and state.progress.caller_phone is None
    detail = admin.get(f"{V1}/calls/{out['conversation_id']}").json()["call"]
    assert detail["mode"] == "prueba" and detail["phone"] == PHONE
    # {{call.phone}} y {{call.from}} en las herramientas, como en una entrante.
    ctx = api.engine.tools.context(api.engine.workflow(state), state, None)
    assert (ctx.mode, ctx.phone, ctx.from_, ctx.to) == ("prueba", PHONE, PHONE, None)


def test_voice_without_the_new_fields_is_unchanged(api, admin):  # noqa: F811
    c = new_client(admin)
    out = admin.post(f"{V1}/calls", json={"agent_id": make_agent(admin, c)["id"], "caller_phone": "  "}).json()
    with api.sessions() as s:
        assert s.get(CallRow, out["conversation_id"]).phone is None
    assert api.engine.store.get(out["conversation_id"]).progress.test_workflows is False


@pytest.mark.parametrize("extra", [{"phone": "+5491155551234"}, {"contact_id": "x"}, {"loadtest": True}])
@pytest.mark.parametrize("field", [{"caller_phone": PHONE}, {"workflows": True}])
def test_voice_only_for_test_calls(api, admin, extra, field):  # noqa: F811
    c = new_client(admin)
    agent = make_agent(admin, c)
    if "contact_id" in extra:
        extra = {"contact_id": admin.post(f"{V1}/contacts", params={"client_id": c["id"]},
                                          json={"phone": "+5493515551234"}).json()["contacts"][0]["id"]}
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], **extra, **field})
    assert r.status_code == 422, r.text
    assert not api.dispatched


def test_service_rejects_link_trial_and_campaign(api, admin):  # noqa: F811
    """Los que crean llamadas por dentro (link, celular, campaña) no pasan los campos; si los pasaran, 422."""
    from app.services import calls
    from app.services.errors import Invalid
    from app.services.security import Principal, Role

    c = new_client(admin)
    agent = make_agent(admin, c)
    me = admin.get(f"{V1}/auth/me").json()
    p = Principal("user", me["id"], Role.admin, None)
    for extra in ({"call_link_id": "x"}, {"trial": True, "phone": "+5491155551234"},
                  {"campaign_contact_id": "x", "phone": "+5491155551234"}):
        with api.sessions() as s, pytest.raises(Invalid):
            calls.prepare_call(s, api.engine, p, calls.CallRequest(agent_id=agent["id"], caller_phone=PHONE, **extra))


def test_invalid_number_and_length(api, admin):  # noqa: F811
    c = new_client(admin)
    agent = make_agent(admin, c)
    for path in ("/calls", "/conversations"):
        r = admin.post(f"{V1}{path}", json={"agent_id": agent["id"], "caller_phone": "351-abc"})
        assert r.status_code == 422 and r.json()["code"] == "invalid_phone", r.text
        assert admin.post(f"{V1}{path}", json={"agent_id": agent["id"], "caller_phone": "+" + "1" * 40}
                          ).status_code == 422
    assert not api.dispatched


def test_client_user_session_can(api, admin):  # noqa: F811
    c = new_client(admin)
    agent = make_agent(admin, c)
    user = client_user(api, admin, c)
    assert user.post(f"{V1}/calls", json={"agent_id": agent["id"], "caller_phone": PHONE}).status_code == 201
    assert user.post(f"{V1}/conversations", json={"agent_id": agent["id"], "caller_phone": PHONE}).status_code == 201


@pytest.mark.parametrize("path", ["/calls", "/conversations"])
@pytest.mark.parametrize("field", [{"caller_phone": PHONE}, {"workflows": True}])
def test_api_key_and_oauth_get_403(api, admin, path, field):  # noqa: F811
    c = new_client(admin)
    agent = make_agent(admin, c)
    key = new_key(admin, c, scopes=("calls", "mcp"))
    r = api.client.post(f"{V1}{path}", headers={"Authorization": f"Bearer {key}"}, json={"agent_id": agent["id"], **field})
    assert r.status_code == 403 and r.json()["code"] == "panel_test_only", r.text
    # Un token OAuth (lo que usa el MCP por dentro).
    user = client_user(api, admin, c)
    access = connect(api, (c, agent, user, register(api)))["access_token"]
    r = api.client.post(f"{V1}{path}", json={"agent_id": agent["id"], **field},
                        headers={"Authorization": f"Bearer {access}", MCP_INTERNAL_HEADER: MCP_INTERNAL_SECRET})
    assert r.status_code == 403 and r.json()["code"] == "panel_test_only", r.text
    # Sin los campos, la misma API key sigue pudiendo.
    assert api.client.post(f"{V1}{path}", headers={"Authorization": f"Bearer {key}"},
                           json={"agent_id": agent["id"]}).status_code == 201
    assert not any(m.get("phone") for m in api.dispatched)


@pytest.mark.parametrize("path", ["/calls", "/conversations"])
def test_agent_of_another_client_is_404(api, admin, path):  # noqa: F811
    mine, other = new_client(admin), new_client(admin, "otro")
    foreign = make_agent(admin, other)
    user = client_user(api, admin, mine)
    r = user.post(f"{V1}{path}", json={"agent_id": foreign["id"], "caller_phone": PHONE, "workflows": True})
    assert r.status_code == 404, r.text


def test_mcp_does_not_expose_the_fields(api, admin):  # noqa: F811
    c = new_client(admin)
    tools = Mcp(api, new_key(admin, c), "all").tools()
    for name in ("start_call", "test_agent_start"):
        props = tools[name]["inputSchema"]["properties"]
        assert "caller_phone" not in props and "workflows" not in props and "agent_id" in props


# ---------- texto ----------

def test_text_conversation_with_simulated_number(api, admin):  # noqa: F811
    c = new_client(admin)
    agent = phone_agent(admin, c)
    r = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"], "caller_phone": "+54 9 351 444 0000"})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["state"]["fields"]["phone"] == PHONE
    state = api.engine.store.get(out["conversation_id"])
    assert state.progress.caller_phone == PHONE and state.progress.test_workflows is False
    with api.sessions() as s:
        assert s.get(CallRow, out["conversation_id"]) is None    # el texto no crea llamada
    ctx = api.engine.tools.context(api.engine.workflow(state), state, None)
    assert (ctx.mode, ctx.phone, ctx.from_, ctx.to) == ("", PHONE, PHONE, None)


def test_text_without_number_has_no_phone(api, admin):  # noqa: F811
    c = new_client(admin)
    out = admin.post(f"{V1}/conversations", json={"agent_id": make_agent(admin, c)["id"]}).json()
    state = api.engine.store.get(out["conversation_id"])
    ctx = api.engine.tools.context(api.engine.workflow(state), state, None)
    assert ctx.phone is None and ctx.from_ is None and state.progress.caller_phone is None


def test_text_workflows_runs_the_pre_call_with_the_number(api, admin, http):  # noqa: F811
    c = new_client(admin)
    agent = pre_call_agent(admin, c)
    http.replies = [{"status": "single", "name": "María Gómez"}]
    r = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"], "caller_phone": PHONE, "workflows": True})
    assert r.status_code == 201, r.text
    out = r.json()
    assert len(http.requests) == 1 and http.requests[0]["body"]["from"] == PHONE
    assert http.requests[0]["url"] == BASE + "/identificar"
    assert out["message"] == "Hola María Gómez, soy Ana."
    assert out["state"]["messages"][0]["text"] == "Hola María Gómez, soy Ana."
    assert api.engine.store.get(out["conversation_id"]).progress.test_workflows is True


def test_text_without_workflows_does_not_run_the_pre_call(api, admin, http):  # noqa: F811
    c = new_client(admin)
    agent = pre_call_agent(admin, c)
    out = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"], "caller_phone": PHONE}).json()
    assert http.requests == [] and out["message"] == "Hola {{nombre}}, soy Ana."


def test_external_agent_gets_the_simulated_number(api, admin):  # noqa: F811
    from app.llm.external import ExternalAgents

    c = new_client(admin)
    agent = make_agent(admin, c)
    out = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"], "caller_phone": PHONE}).json()
    state = api.engine.store.get(out["conversation_id"])
    ext = ExternalAgents(api.sessions)
    assert ext.context(state, None) == {"mode": "", "from": PHONE, "to": ""}
