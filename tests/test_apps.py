"""Apps por cliente (docs/APPS_PLAN.md): registro, herramientas del motor assistant, confirmacion,
links con gateway y operadores de WhatsApp. La app se simula parcheando app/apps/client.py."""
import copy
import json

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.agents.definitions import DbDefinitions
from app.apps import client as app_client
from app.apps import gateway as gateway_module
from app.apps import registry
from app.apps import tools as app_tools
from app.config import settings
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.models import App, AppLink, ConversationRow, WaOperator
from app.services import agents as agent_service
from app.services.errors import Invalid

from .helpers import FakeLLM
from .test_api import ADMIN, V1, make_agent, make_client
from .test_whatsapp_service import PNID, WA_ID, make_wa, reply, send, text_payload

SLUG = "gym-gestion"
TOKEN = "t" * 32
MANIFEST = {
    "spec": 1, "slug": SLUG, "client": "gym", "name": "Gestión del gym", "version": "0.1.0", "core": "0.1.0",
    "description": "Alumnos y asistencias",
    "views": [{"name": "minuta", "title": "Minuta del día", "description": "Quiénes vinieron en el día.",
               "params": {"fecha": {"type": "string", "default": None, "description": "AAAA-MM-DD"}}}],
    "tools": [
        {"name": "buscar_alumno", "description": "Busca alumnos por nombre.", "kind": "read",
         "input_schema": {"type": "object", "properties": {"texto": {"type": "string", "title": "Texto"}},
                          "required": ["texto"], "title": "args"}},
        {"name": "registrar_asistencias", "description": "Registra ingresos.", "kind": "write",
         "input_schema": {"$defs": {"Ingreso": {"type": "object", "title": "Ingreso", "properties": {
             "alumno": {"type": "string"}, "hora": {"type": "string"}}}},
             "type": "object", "properties": {"fecha": {"type": "string"},
                                              "ingresos": {"type": "array", "items": {"$ref": "#/$defs/Ingreso"}}}}},
        {"name": "baja_alumno", "description": "Da de baja un alumno.", "kind": "destructive",
         "input_schema": {"type": "object", "properties": {"alumno_id": {"type": "integer"}}}},
        {"name": "enviar_mensajes", "description": "Manda mensajes a alumnos.", "kind": "send",
         "input_schema": {"type": "object", "properties": {"mensajes": {"type": "array", "items": {
             "type": "object", "properties": {"alumno_id": {"type": "integer"}, "texto": {"type": "string"}}}}}}},
    ],
    "jobs": [{"name": "resumen_diario", "title": "Resumen", "hora": "08:00", "dias": [1, 2, 3, 4, 5, 6]}],
}
ASSISTANT = {
    "engine": "assistant",
    "agent": {"name": "Asis", "role": "asistente del gimnasio", "language": "es-AR"},
    "objective": {"description": "Ayudar al dueño con alumnos y asistencias"},
    "conversation": {"opening": "Hola", "rules": []},
    "fields": {},
    "completion": {"outcomes": [{"id": "default", "label": "Conversación", "message": "Chau"}]},
    "tools": [{"app": SLUG, "tools": ["*"]}],
}


class FakeApp:
    """La app del contenedor: manifest, herramientas y vistas."""

    def __init__(self, monkeypatch, manifest=None):
        self.manifest = copy.deepcopy(manifest or MANIFEST)
        self.calls: list[tuple[str, dict, str]] = []
        self.views: list[tuple[str, str, str, str]] = []
        self.results: dict[str, dict] = {}
        self.posted: list[tuple[str, dict]] = []
        self.job_reply = {"message": "Hoy vencen 2 cuotas.", "view": {"name": "minuta", "params": {}}}
        self.down = False
        monkeypatch.setattr(app_client, "get_json", self.get_json)
        monkeypatch.setattr(app_client, "call_tool", self.call_tool)
        monkeypatch.setattr(app_client, "get_view", self.get_view)
        monkeypatch.setattr(app_client, "post_json", self.post_json)

    async def post_json(self, base_url, token, path, payload, actor="atentina"):
        self.posted.append((path, payload))
        return self.job_reply if path.startswith("/jobs/") else {"ok": True}

    def get_json(self, base_url, token, path, timeout=None):
        if self.down:
            raise app_client.AppError(f"{path}: no responde")
        assert token == TOKEN
        return {"ok": True} if path == "/health" else copy.deepcopy(self.manifest)

    async def call_tool(self, base_url, token, name, arguments, actor):
        if self.down:
            raise app_client.AppError("mcp: no responde")
        self.calls.append((name, arguments, actor))
        return self.results.get(name, {"ok": True, "result": {"hecho": name}})

    async def get_view(self, base_url, token, path, query, actor, prefix):
        import httpx
        self.views.append((path, query, actor, prefix))
        if path.endswith(".css"):
            return httpx.Response(200, content=b"body{}", headers={"content-type": "text/css"})
        return httpx.Response(200, content=b"<h1>Minuta</h1>", headers={"content-type": "text/html; charset=utf-8"})


class ScriptLLM(FakeLLM):
    """Salidas del motor assistant, en orden (JSON); guarda los mensajes y esquemas de cada paso."""

    def __init__(self, *steps: dict, turns=()):
        super().__init__(*turns)
        self.steps = [json.dumps(s, ensure_ascii=False) for s in steps]
        self.seen: list[tuple[list[dict], dict]] = []

    async def structured(self, messages, schema, name="paso", thinking=None, budget=None, max_tokens=None):
        self.seen.append((copy.deepcopy(messages), schema))
        self.thinking = (thinking, budget)
        return self.steps.pop(0), None


@pytest.fixture(autouse=True)
def apps_settings(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "apps_public_host", "apps.test")
    monkeypatch.setattr(settings, "apps_public_scheme", "https")


def gym_world(sessions, monkeypatch, llm=None, assign=True):
    """Cliente gym con la app registrada (y asignada) y un agente assistant."""
    from app.models import Client, Tier

    fake = FakeApp(monkeypatch)
    with sessions() as s:
        tier = Tier(name="Tier gym")
        s.add(tier)
        s.flush()
        client = Client(name="Gym", slug="gym", tier_id=tier.id)
        s.add(client)
        s.flush()
        app = registry.register(s, SLUG, "http://app-gym-gestion:8000", TOKEN)
        if assign:
            app.client_id = client.id
        s.flush()
        agent = agent_service.create_agent(s, client, name="Asistente", slug="asistente", description="",
                                           definition=ASSISTANT if assign else {**ASSISTANT, "tools": []},
                                           template_id=None, user_id=None)
        s.commit()
        ids = client.id, agent.id, app.id
    llm = llm or ScriptLLM()
    engine = ConversationEngine(llm, ConversationStore(sessions), DbDefinitions(sessions))
    return fake, engine, llm, ids


def start(engine, agent_id, client_id):
    state, _ = engine.start_conversation(agent_id, client_id, channel="whatsapp", opening=False)
    return state.conversation_id


# ---------- registro ----------

def test_register_guarda_manifest_y_token_cifrado(sessions, monkeypatch):
    FakeApp(monkeypatch)
    with sessions() as s:
        app = registry.register(s, SLUG, "http://app-gym-gestion:8000/", TOKEN)
        s.commit()
        assert (app.version, app.status, app.client_id, app.base_url) == ("0.1.0", "ok", None, "http://app-gym-gestion:8000")
        assert app.token_enc.startswith("fernet:") and TOKEN not in app.token_enc
        assert registry.token_of(app) == TOKEN
        assert [t.name for t in registry.manifest_of(app).tools] == ["buscar_alumno", "registrar_asistencias", "baja_alumno",
                                                                  "enviar_mensajes"]


@pytest.mark.parametrize("change, motivo", [
    (lambda m: m.update(slug="otra"), "slug"),
    (lambda m: m.update(spec=2), "spec"),
    (lambda m: m["tools"].extend(dict(m["tools"][0], name=f"t{i}") for i in range(17)), "herramientas"),
    (lambda m: m["tools"][0].update(kind="borra"), "kind"),
    (lambda m: m["tools"][0].update(description="x" * 401), "descripcion"),
    (lambda m: m["tools"][0].update(name="Buscar-Alumno"), "nombre invalido"),
])
def test_register_rechaza_manifest_fuera_de_contrato(sessions, monkeypatch, change, motivo):
    fake = FakeApp(monkeypatch)
    change(fake.manifest)
    with sessions() as s, pytest.raises(Invalid) as e:
        registry.register(s, SLUG, "http://app-gym-gestion:8000", TOKEN)
    assert motivo in e.value.message


def test_register_app_caida(sessions, monkeypatch):
    FakeApp(monkeypatch).down = True
    with sessions() as s, pytest.raises(Invalid, match="no responde"):
        registry.register(s, SLUG, "http://app-gym-gestion:8000", TOKEN)


def test_health_marca_down_y_vuelve(sessions, monkeypatch):
    fake = FakeApp(monkeypatch)
    with sessions() as s:
        registry.register(s, SLUG, "http://app-gym-gestion:8000", TOKEN)
        s.commit()
    fake.down = True
    assert registry.check_health(sessions) == 1
    with sessions() as s:
        assert s.scalar(select(App.status)) == "down"
    fake.down = False
    assert registry.check_health(sessions) == 0
    with sessions() as s:
        assert s.scalar(select(App.status)) == "ok"


# ---------- herramientas ----------

def test_catalogo_con_vistas_y_esquemas_sin_ref(sessions, monkeypatch):
    _, _, _, (client_id, _, _) = gym_world(sessions, monkeypatch)
    from app.conversation.models import ToolGrant
    with sessions() as s:
        tools = app_tools.catalog(s, client_id, [ToolGrant(app=SLUG)])
        only = app_tools.catalog(s, client_id, [ToolGrant(app=SLUG, tools=["buscar_alumno"])])
        other = app_tools.catalog(s, "otro-cliente", [ToolGrant(app=SLUG)])
    by = {t.name: t for t in tools}
    assert list(by) == ["buscar_alumno", "registrar_asistencias", "baja_alumno", "enviar_mensajes", "abrir_vista"]
    items = by["registrar_asistencias"].schema["properties"]["ingresos"]["items"]
    assert items == {"type": "object", "properties": {"alumno": {"type": "string"}, "hora": {"type": "string"}}}
    assert "title" not in json.dumps(by["buscar_alumno"].schema)
    assert by["baja_alumno"].needs_confirmation and not by["registrar_asistencias"].needs_confirmation
    view = by["abrir_vista"]
    assert view.platform and view.kind == "read" and view.params == {"minuta": ["fecha"]}
    assert view.schema["properties"]["vista"] == {"enum": ["minuta"]} and "minuta (" in view.description
    assert [t.name for t in only] == ["buscar_alumno", "abrir_vista"]
    assert other == []      # la app no es de ese cliente


def test_agente_valida_las_herramientas_al_guardar(sessions, monkeypatch):
    _, _, _, (_client_id, agent_id, app_id) = gym_world(sessions, monkeypatch)
    from app.models import Agent
    with sessions() as s:
        agent = s.get(Agent, agent_id)
        with pytest.raises(Invalid) as e:
            agent_service.update_definition(s, agent, {**ASSISTANT, "tools": [{"app": SLUG, "tools": ["volar"]}]}, None)
        assert e.value.details == [{"path": "tools.0.tools", "message": f"La app {SLUG!r} no tiene la herramienta 'volar'"}]
        s.get(App, app_id).client_id = None
        with pytest.raises(Invalid) as e:
            agent_service.update_definition(s, agent, {**ASSISTANT, "agent": {**ASSISTANT["agent"], "name": "Otro"}}, None)
        assert e.value.details[0]["path"] == "tools.0.app"


def test_tools_solo_con_motor_assistant():
    from app.conversation.models import Workflow
    with pytest.raises(ValueError, match="solo el motor assistant"):
        Workflow.model_validate({**ASSISTANT, "engine": "classic", "id": "x", "version": 1,
                                 "fields": {"a": {"priority": 1, "description": "a", "question": "a"}}})


# ---------- motor assistant ----------

async def test_turno_con_herramienta_y_respuesta(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "reply", "message": "Encontré a Juan Pérez."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = {"ok": True, "result": {"candidatos": [{"id": 1, "nombre": "Juan Pérez"}]}}
    cid = start(engine, agent_id, client_id)

    state, turn = await engine.process_turn(cid, "buscame a juan", actor=f"wa:{WA_ID}")

    assert turn.assistant_message == "Encontré a Juan Pérez."
    assert fake.calls == [("buscar_alumno", {"texto": "juan"}, f"wa:{WA_ID}")]
    # El segundo paso ve el resultado de la herramienta.
    assert "Juan Pérez" in llm.seen[1][0][-1]["content"]
    system = llm.seen[0][0][0]["content"]
    assert "buscar_alumno [consulta]" in system and "baja_alumno [CONFIRMAR" in system
    # La hora va en el mensaje del usuario: el prompt de sistema no cambia entre pasos (prefix caching).
    assert "AHORA:" not in system and llm.seen[0][0][-1]["content"].startswith("AHORA: ")
    assert system == llm.seen[1][0][0]["content"]
    kinds = [t["kind"] for t in state.messages[-1].llm]
    assert kinds == ["paso", "herramienta", "paso"]
    assert state.status == "active" and state.progress.pending is None
    # El esquema: responder, o una de las 4 herramientas; sin confirm/cancel (no hay nada pendiente).
    actions = [o["properties"]["action"]["enum"][0] for o in llm.seen[0][1]["anyOf"]]
    assert actions == ["reply", "call", "call", "call", "call", "call"]


JUAN = {"ok": True, "result": {"candidatos": [{"alumno_id": 7, "nombre": "Juan Pérez"}]}}


async def test_destructiva_queda_pendiente_y_se_confirma(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan perez"}},
                    {"action": "call", "tool": "baja_alumno", "arguments": {"alumno_id": 7}},
                    {"action": "reply", "message": "¿Confirmás la baja de Juan Pérez?"},
                    {"action": "reply", "message": "Listo, Juan Pérez quedó dado de baja."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = JUAN
    cid = start(engine, agent_id, client_id)

    state, turn = await engine.process_turn(cid, "dale de baja a juan perez")
    assert [c[0] for c in fake.calls] == ["buscar_alumno"]     # la baja no se ejecuto
    assert state.progress.pending == {"tool": "baja_alumno", "arguments": {"alumno_id": 7}}
    assert "NO se ejecutó" in llm.seen[2][0][-1]["content"]
    # Mientras tanto, en el mismo turno, el LLM no puede confirmar lo que acaba de pedir.
    assert "confirm" not in json.dumps(llm.seen[2][1])

    state, turn = await engine.process_turn(cid, "sí, dale")
    assert fake.calls[-1] == ("baja_alumno", {"alumno_id": 7}, f"conversation:{cid}")
    assert "el usuario confirmó y se ejecutó baja_alumno" in llm.seen[3][0][-1]["content"]
    assert turn.assistant_message == "Listo, Juan Pérez quedó dado de baja."
    assert state.progress.pending is None


async def test_pendiente_dura_un_turno(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "call", "tool": "baja_alumno", "arguments": {"alumno_id": 7}},
                    {"action": "reply", "message": "¿Confirmás?"},
                    {"action": "reply", "message": "Ok, ¿qué más?"},
                    {"action": "reply", "message": "Nada pendiente"})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = JUAN
    cid = start(engine, agent_id, client_id)
    await engine.process_turn(cid, "dale de baja a juan")
    state, _ = await engine.process_turn(cid, "mejor contame quién vino hoy")
    assert state.progress.pending is None
    await engine.process_turn(cid, "sí")
    assert "confirm" not in json.dumps(llm.seen[-1][1])
    assert [c[0] for c in fake.calls] == ["buscar_alumno"]


async def test_id_sin_consultar_no_se_usa(sessions, monkeypatch):
    """Visto con Gemma: mandaba alumno_id 3 (otra persona) sin buscar."""
    llm = ScriptLLM({"action": "call", "tool": "baja_alumno", "arguments": {"alumno_id": 3}},
                    {"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "carlos"}},
                    {"action": "call", "tool": "baja_alumno", "arguments": {"alumno_id": 4}},
                    {"action": "reply", "message": "¿Confirmás la baja de Carlos Gómez?"})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = {"ok": True, "result": {"candidatos": [{"alumno_id": 4, "nombre": "Carlos Gómez"}]}}
    cid = start(engine, agent_id, client_id)
    state, _ = await engine.process_turn(cid, "dale de baja a carlos")
    assert "alumno_id=3 no salió de ningún resultado" in llm.seen[1][0][-1]["content"]
    assert state.progress.pending == {"tool": "baja_alumno", "arguments": {"alumno_id": 4}}
    assert [t["kind"] for t in state.messages[-1].llm].count("control") == 1


async def test_link_inventado_se_corrige(sessions, monkeypatch):
    """Visto con Gemma: respondia con un link inventado en vez de pedir la vista."""
    llm = ScriptLLM({"action": "reply", "message": "Mirá: https://gym-management.com/minuta"},
                    {"action": "call", "tool": "abrir_vista", "arguments": {"vista": "minuta"}},
                    {"action": "reply", "message": "Mirá: [[link1]]"})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "pasame la minuta")
    url = turn.assistant_message.removeprefix("Mirá: ")
    assert url.startswith("https://apps.test/gym/gym-gestion/minuta/?k=")
    llm.steps = [json.dumps({"action": "reply", "message": f"Acá está: {url}."})]
    _, turn = await engine.process_turn(cid, "pasámela de nuevo")
    assert turn.assistant_message == f"Acá está: {url}."      # un link de un turno anterior vale
    assert "no salió de ninguna herramienta" in llm.seen[1][0][-1]["content"]


async def test_link_inventado_dos_veces_se_saca(sessions, monkeypatch):
    llm = ScriptLLM({"action": "reply", "message": "Mirá: https://x.com/a"},
                    {"action": "reply", "message": "Mirá: https://x.com/b"})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "pasame la minuta")
    assert turn.assistant_message == "Mirá: (link no disponible)"


async def test_vista_devuelve_link_firmado(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "abrir_vista", "arguments": {"vista": "minuta", "fecha": "2026-10-12"}},
                    {"action": "reply", "message": "Mirá: [[link1]]"})
    _, engine, llm, (client_id, agent_id, app_id) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    state, turn = await engine.process_turn(cid, "pasame la minuta de hoy", actor=f"wa:{WA_ID}")
    # El LLM no ve el link (lo copiaba mal): ve una marca, y el sistema la cambia en la respuesta.
    result = json.loads(llm.seen[1][0][-1]["content"].split(": ", 1)[1])
    assert result["link"] == "[[link1]]" and "url" not in result
    url = turn.assistant_message.removeprefix("Mirá: ")
    assert url.startswith("https://apps.test/gym/gym-gestion/minuta/?fecha=2026-10-12&k=")
    assert url in next(t for t in state.messages[-1].llm if t["kind"] == "herramienta")["output"]
    with sessions() as s:
        link = s.scalar(select(AppLink))
        assert (link.app_id, link.view, link.params, link.created_by) == (app_id, "minuta", {"fecha": "2026-10-12"},
                                                                         f"wa:{WA_ID}")


async def test_herramienta_de_la_app_devuelve_el_link_de_una_vista(sessions, monkeypatch):
    """Contrato v1.3 (perfil de SUGYM): el resultado trae "view" y Atentina arma el link firmado; el LLM ve
    la marca, con el resumen de la app al lado."""
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "carlos"}},
                    {"action": "reply", "message": "Carlos Gómez, al día. [[link1]]"})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = {"ok": True, "result": {"resumen": "Carlos Gómez, al día.", "view": {
        "name": "minuta", "params": {"fecha": "2026-10-12", "otro": "x"}}}}
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "mostrame el perfil de carlos", actor=f"wa:{WA_ID}")
    result = json.loads(llm.seen[1][0][-1]["content"].split(": ", 1)[1])
    assert result["link"] == "[[link1]]" and result["resumen"] == "Carlos Gómez, al día." and "view" not in result
    url = turn.assistant_message.removeprefix("Carlos Gómez, al día. ")
    assert url.startswith("https://apps.test/gym/gym-gestion/minuta/?fecha=2026-10-12&k=")
    with sessions() as s:
        link = s.scalar(select(AppLink))
        assert (link.view, link.params, link.created_by) == ("minuta", {"fecha": "2026-10-12"}, f"wa:{WA_ID}")
    # Una vista que la app no declara: el resultado sigue, sin link.
    fake.results["buscar_alumno"] = {"ok": True, "result": {"resumen": "x", "view": {"name": "no_existe"}}}
    llm.steps = [json.dumps({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "otro"}}),
                 json.dumps({"action": "reply", "message": "Listo."})]
    _, turn = await engine.process_turn(cid, "y el de otro")
    assert json.loads(llm.seen[-1][0][-1]["content"].split(": ", 1)[1]) == {"resumen": "x"}
    assert turn.assistant_message == "Listo."


async def test_app_caida_vuelve_como_error_para_el_llm(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "x"}},
                    {"action": "reply", "message": "La app no anda."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.down = True
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "buscá x")
    assert "ERROR: La aplicación no responde" in llm.seen[1][0][-1]["content"]
    assert turn.assistant_message == "La app no anda."


async def test_tope_de_pasos(sessions, monkeypatch):
    monkeypatch.setattr(settings, "assistant_max_steps", 2)
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "a"}},
                    {"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "b"}})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "buscá")
    assert turn.assistant_message.startswith("Perdón")
    assert len(fake.calls) == 2


# ---------- gateway ----------

@pytest.fixture
def gateway_client(sessions, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app
    monkeypatch.setattr(gateway_module, "get_sessionmaker", lambda: sessions)
    return TestClient(app, base_url="https://apps.test")


def make_link(sessions, app_id, view="minuta", params=None):
    from app.apps import links
    with sessions() as s:
        url, link = links.create_link(s, s.get(App, app_id), view, params or {"fecha": "2026-10-12"}, "test")
        s.commit()
        return url, link.id


def test_gateway_link_cookie_y_proxy(sessions, monkeypatch, gateway_client):
    fake, _, _, (_, _, app_id) = gym_world(sessions, monkeypatch)
    url, link_id = make_link(sessions, app_id)
    path_query = url.removeprefix("https://apps.test")

    r = gateway_client.get(path_query, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/gym/gym-gestion/minuta/?fecha=2026-10-12"      # sin el token
    cookie = r.headers["set-cookie"]
    assert "Path=/gym/gym-gestion/" in cookie and "HttpOnly" in cookie and "Secure" in cookie

    r = gateway_client.get("/gym/gym-gestion/minuta/?fecha=2026-10-11")
    assert r.status_code == 200 and r.text == "<h1>Minuta</h1>"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["referrer-policy"] == "no-referrer"
    assert fake.views[-1] == ("/views/minuta", "fecha=2026-10-11", f"link:{link_id}", "/gym/gym-gestion")

    r = gateway_client.get("/gym/gym-gestion/static/app.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")
    with sessions() as s:
        assert s.get(AppLink, link_id).opens == 1


def test_gateway_rechaza_sin_link_vencido_o_de_otra_vista(sessions, monkeypatch, gateway_client):
    import datetime
    fake, _, _, (_, _, app_id) = gym_world(sessions, monkeypatch)
    fake.manifest["views"].append({"name": "alumnos", "title": "Alumnos", "params": {}})
    with sessions() as s:
        registry.refresh(s, s.get(App, app_id))
        s.commit()
    assert gateway_client.get("/gym/gym-gestion/minuta/").status_code == 401
    url, link_id = make_link(sessions, app_id)
    token = url.split("k=")[1]
    # El token de minuta no abre otra vista, ni la misma app con otro cliente en la URL.
    assert gateway_client.get(f"/gym/gym-gestion/alumnos/?k={token}").status_code == 401
    assert gateway_client.get(f"/otro/gym-gestion/minuta/?k={token}").status_code == 404
    with sessions() as s:
        s.get(AppLink, link_id).expires_at = datetime.datetime(2020, 1, 1)  # noqa: DTZ001 - la base guarda UTC sin zona
        s.commit()
    assert gateway_client.get(f"/gym/gym-gestion/minuta/?k={token}", follow_redirects=False).status_code == 401
    assert fake.views == []


def test_gateway_app_navegable_abre_todas_sus_vistas(sessions, monkeypatch, gateway_client):
    """Contrato v1.4: con navigation, la cookie abre las otras vistas de la app (el token en la URL no)."""
    fake, _, _, (_, _, app_id) = gym_world(sessions, monkeypatch)
    fake.manifest["views"].append({"name": "alumnos", "title": "Alumnos", "params": {}})

    def refresh():
        with sessions() as s:
            registry.refresh(s, s.get(App, app_id))
            s.commit()
    refresh()
    url, _ = make_link(sessions, app_id)
    gateway_client.get(url.removeprefix("https://apps.test"), follow_redirects=False)
    assert gateway_client.get("/gym/gym-gestion/alumnos/").status_code == 401
    fake.manifest["navigation"] = True
    refresh()
    assert gateway_client.get("/gym/gym-gestion/alumnos/").status_code == 200
    assert gateway_client.get("/gym/gym-gestion/inexistente/").status_code == 401


def test_gateway_no_expone_el_panel_ni_la_api(sessions, monkeypatch, gateway_client):
    gym_world(sessions, monkeypatch)
    assert gateway_client.get("/api/v1/auth/me").status_code == 404
    assert gateway_client.post("/api/v1/auth/login", json={}).status_code == 404
    assert gateway_client.get("/").status_code == 404


def test_gateway_formulario_de_una_vista(sessions, monkeypatch, gateway_client):
    """Contrato v1.2: POST solo a una vista con form, desde el gateway (Origin) y con la cookie del link."""
    import httpx
    fake, _, _, (_, _, app_id) = gym_world(sessions, monkeypatch)
    fake.manifest["views"].append({"name": "planes", "title": "Planes", "params": {}, "form": True})
    with sessions() as s:
        registry.refresh(s, s.get(App, app_id))
        s.commit()
    posts = []

    async def post_form(base_url, token, path, query, body, actor, prefix):
        posts.append((path, body, actor, prefix))
        if b"precio=" in body and b"precio=&" not in body and not body.endswith(b"precio="):
            return httpx.Response(303, headers={"location": f"{prefix}/planes/?guardado=1"})
        return httpx.Response(200, content=b"<p>No se guardo nada</p>", headers={"content-type": "text/html"})
    monkeypatch.setattr(app_client, "post_form", post_form)
    origin = {"Origin": "https://apps.test"}
    form = {"p3_precio": "70000", "precio": "1"}
    assert gateway_client.post("/gym/gym-gestion/planes/", data=form, headers=origin).status_code == 401   # sin link
    url, link_id = make_link(sessions, app_id, "planes", {})
    gateway_client.get(url.removeprefix("https://apps.test"), follow_redirects=False)
    assert gateway_client.post("/gym/gym-gestion/planes/", data=form).status_code == 403                  # sin Origin
    assert gateway_client.post("/gym/gym-gestion/planes/", data=form,
                               headers={"Origin": "https://evil.test"}).status_code == 403
    assert gateway_client.post("/gym/gym-gestion/planes/", json=form, headers=origin).status_code == 415
    r = gateway_client.post("/gym/gym-gestion/planes/", data=form, headers=origin, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/gym/gym-gestion/planes/?guardado=1"
    assert posts[-1][0] == "/views/planes" and posts[-1][2] == f"link:{link_id}" and posts[-1][3] == "/gym/gym-gestion"
    r = gateway_client.post("/gym/gym-gestion/planes/", data={"precio": ""}, headers=origin)
    assert r.status_code == 200 and "No se guardo nada" in r.text and "default-src 'none'" in r.headers["content-security-policy"]
    # Una vista sin form no recibe POST, aunque el link sea suyo.
    url, _ = make_link(sessions, app_id)
    gateway_client.get(url.removeprefix("https://apps.test"), follow_redirects=False)
    assert gateway_client.post("/gym/gym-gestion/minuta/", data=form, headers=origin).status_code == 404
    assert len(posts) == 2


# ---------- API ----------

def test_api_registro_asignacion_y_links(api, monkeypatch):
    from app.models import Role, User
    from app.services.security import hash_password
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    admin = api.login(*ADMIN)
    FakeApp(monkeypatch)
    r = admin.post(f"{V1}/apps", json={"slug": SLUG, "base_url": "http://app-gym-gestion:8000", "token": TOKEN})
    assert r.status_code == 200, r.text
    app = r.json()
    assert (app["status"], app["client_id"], [v["name"] for v in app["views"]]) == ("ok", None, ["minuta"])
    assert "token" not in json.dumps(app).lower()
    client = make_client(admin, "gym")
    r = admin.post(f"{V1}/apps/{app['id']}/assign", json={"client_id": client["id"]})
    assert r.json()["client_name"] == "Gym"
    r = admin.post(f"{V1}/apps/{app['id']}/links", json={"view": "minuta", "params": {"fecha": "2026-10-12"}})
    assert r.status_code == 201 and r.json()["url"].startswith("https://apps.test/gym/gym-gestion/minuta/")
    assert admin.get(f"{V1}/apps/{app['id']}/links").json()[0]["url"] is None
    r = admin.delete(f"{V1}/apps/{app['id']}")
    assert r.status_code == 409
    agent = make_agent(admin, client, definition=ASSISTANT)
    assert agent["engine"] == "assistant"
    r = admin.post(f"{V1}/apps/{app['id']}/release")
    assert r.json()["client_id"] is None
    with api.sessions() as s:
        assert s.scalar(select(AppLink.revoked_at)) is not None


# ---------- operadores de WhatsApp ----------

async def test_operador_habla_con_su_asistente(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "reply", "message": "Juan vino hoy a las 8:05."},
                    turns=[reply("Hola, soy el agente del número")])
    w = make_wa(sessions, llm=llm)
    fake, _, _, (gym_id, assistant_id, _) = gym_world(sessions, monkeypatch, llm)
    with sessions() as s:
        s.add(WaOperator(account_id=w.account_id, wa_id=WA_ID, client_id=gym_id, agent_id=assistant_id, name="Dueño"))
        s.commit()

    await send(w, text_payload("¿vino juan hoy?", "wamid.op1"))

    assert w.graph.sent[-1][2] == "Juan vino hoy a las 8:05."
    assert fake.calls == [("buscar_alumno", {"texto": "juan"}, f"wa:{WA_ID}")]
    with sessions() as s:
        conv = s.scalar(select(ConversationRow))
        assert (conv.client_id, conv.agent_id) == (gym_id, assistant_id)
        from app.models import WaThread
        assert s.get(WaThread, conv.id).client_id == gym_id
    # Otro contacto, por el mismo numero: el agente del numero, como siempre.
    payload = text_payload("hola", "wamid.otro")
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["from"] = "5493519999999"
    payload["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"] = "5493519999999"
    await send(w, payload)
    assert w.graph.sent[-1][2] == "Hola, soy el agente del número"


def test_api_operadores(api, monkeypatch):
    from app.models import Role, User
    from app.services.security import hash_password
    from app.whatsapp import store
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    admin = api.login(*ADMIN)
    atentina, gym = make_client(admin, "atentina"), make_client(admin, "gym")
    number_agent = make_agent(admin, atentina)
    gym_agent = make_agent(admin, gym)
    with api.sessions() as s:
        account = store.create_account(s, client_id=atentina["id"], agent_id=number_agent["id"], phone_number_id=PNID,
                                       waba_id="1", display_phone_number="+54 9 351 000 0000")
        s.commit()
        account_id = account.id
    body = {"account_id": account_id, "wa_id": WA_ID, "client_id": gym["id"], "agent_id": gym_agent["id"], "name": "Dueño"}
    r = admin.post(f"{V1}/wa-operators", json=body)
    assert r.status_code == 201, r.text
    assert (r.json()["agent_name"], r.json()["account_number"]) == ("Ventas", "+54 9 351 000 0000")
    assert admin.post(f"{V1}/wa-operators", json=body).status_code == 409
    r = admin.post(f"{V1}/wa-operators", json={**body, "wa_id": "5493511111111", "agent_id": number_agent["id"]})
    assert r.status_code == 422      # el agente no es del cliente
    op_id = admin.get(f"{V1}/wa-operators").json()[0]["id"]
    assert admin.patch(f"{V1}/wa-operators/{op_id}", json={"active": False}).json()["active"] is False
    assert admin.delete(f"{V1}/wa-operators/{op_id}").status_code == 204


def test_api_registro_con_token_de_deploy(api, monkeypatch):
    FakeApp(monkeypatch)
    body = {"slug": SLUG, "base_url": "http://app-gym-gestion:8000", "token": TOKEN}
    assert api.client.post(f"{V1}/apps", json=body).status_code == 401
    monkeypatch.setattr(settings, "apps_deploy_token", "deploy-" + "d" * 32)
    bad = {"Authorization": "Bearer otro"}
    assert api.client.post(f"{V1}/apps", json=body, headers=bad).status_code == 401
    ok = {"Authorization": "Bearer deploy-" + "d" * 32}
    r = api.client.post(f"{V1}/apps", json=body, headers=ok)
    assert r.status_code == 200, r.text
    assert api.client.post(f"{V1}/apps/{r.json()['id']}/refresh", headers=ok).json()["status"] == "ok"
    # Solo eso: no lista ni asigna.
    assert api.client.get(f"{V1}/apps", headers=ok).status_code == 401


async def test_asistente_responde_en_texto_aunque_le_hablen_por_audio(sessions, monkeypatch):
    """12-oct-2026: por audio respondia "aca tenes la lista" en una nota de voz, sin la lista."""
    from app.whatsapp.service import Item, WhatsAppService
    monkeypatch.setattr(settings, "wa_audio_reply", "mirror")
    audio = [Item(1, "pasame la lista de alumnos", "wamid.a", voice_note=True)]
    assert WhatsAppService._media(audio).reply_voice_note is True
    assert WhatsAppService._media(audio, text_only=True).reply_voice_note is False

    llm = ScriptLLM(turns=[reply("Hola")])
    w = make_wa(sessions, llm=llm)
    _, engine, _, (gym_id, assistant_id, _) = gym_world(sessions, monkeypatch, llm)
    gym_cid = start(engine, assistant_id, gym_id)
    number_cid = w.engine.start_conversation(w.agent_id, w.client_id, channel="whatsapp", opening=False)[0].conversation_id
    assert w.service._text_only(gym_cid) is True
    assert w.service._text_only(number_cid) is False



# ---------- contrato v1.1: outbox, jobs, archivos y csv ----------

async def test_send_confirmado_entrega_el_outbox_simulado(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "call", "tool": "enviar_mensajes",
                     "arguments": {"mensajes": [{"alumno_id": 7, "texto": "Hola Juan, ¡gracias!"}]}},
                    {"action": "reply", "message": "¿Le mando a Juan: «Hola Juan, ¡gracias!»?"},
                    {"action": "reply", "message": "Listo, mensaje registrado (modo prueba)."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = JUAN
    fake.results["enviar_mensajes"] = {"ok": True, "result": {"outbox": [
        {"ref": "m1", "to": "+54 9 999 000-0007", "text": "Hola Juan, ¡gracias!", "tipo": "recibo"}]}}
    cid = start(engine, agent_id, client_id)
    state, _ = await engine.process_turn(cid, "mandale las gracias a juan")
    assert state.progress.pending["tool"] == "enviar_mensajes" and fake.posted == []
    await engine.process_turn(cid, "dale")
    assert fake.posted == [("/outbox/m1", {"estado": "simulado", "detalle": "modo de prueba: no se envió",
                                           "wamid": None})]
    assert '"estado": "simulado"' in llm.seen[3][0][-1]["content"]


def _job_world(sessions, monkeypatch):
    from app.whatsapp import store as wa_store
    fake, _, _, (gym_id, assistant_id, app_id) = gym_world(sessions, monkeypatch)
    with sessions() as s:
        account = wa_store.create_account(s, client_id=gym_id, agent_id=assistant_id, phone_number_id=PNID,
                                          waba_id="1", display_phone_number="+54 9 351 000 0000")
        s.add(WaOperator(account_id=account.id, wa_id=WA_ID, client_id=gym_id, agent_id=assistant_id))
        s.commit()
    return fake, app_id


async def test_job_corre_una_vez_por_dia_y_avisa_a_los_operadores(sessions, monkeypatch):
    import datetime
    from zoneinfo import ZoneInfo

    from app.apps import jobs
    from app.models import AppJobRun
    fake, _ = _job_world(sessions, monkeypatch)
    tz = ZoneInfo(settings.assistant_timezone)
    monday_7 = datetime.datetime(2026, 10, 12, 7, 59, tzinfo=tz)
    assert await jobs.tick(sessions, monday_7) == 0                      # todavia no
    assert await jobs.tick(sessions, monday_7.replace(hour=8, minute=5)) == 1
    assert await jobs.tick(sessions, monday_7.replace(hour=9)) == 0      # ya corrio hoy
    assert await jobs.tick(sessions, monday_7.replace(hour=11)) == 0     # fuera de la ventana
    sunday = datetime.datetime(2026, 10, 18, 8, 5, tzinfo=tz)
    assert await jobs.tick(sessions, sunday) == 0                        # no es dia del job
    assert [p for p, _ in fake.posted] == ["/jobs/resumen_diario"]
    with sessions() as s:
        run = s.scalar(select(AppJobRun))
        assert (run.status, run.detail) == ("enviado", "Hoy vencen 2 cuotas.")
        assert s.scalar(select(AppLink)).created_by == "job:resumen_diario"


async def test_job_a_mano_por_la_api(api, monkeypatch):
    from app.apps import jobs
    from app.models import Role, User
    from app.services.security import hash_password
    monkeypatch.setattr(jobs, "get_sessionmaker", lambda: api.sessions, raising=False)
    import app.api.routers.apps as apps_router
    monkeypatch.setattr(apps_router, "get_sessionmaker", lambda: api.sessions)
    _, app_id = _job_world(api.sessions, monkeypatch)
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    admin = api.login(*ADMIN)
    r = admin.post(f"{V1}/apps/{app_id}/jobs/resumen_diario/run")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "Hoy vencen 2 cuotas." and body["url"].startswith("https://apps.test/gym/")
    assert body["entregas"] == [{"wa_id": WA_ID, "estado": "simulado"}]
    assert admin.post(f"{V1}/apps/{app_id}/jobs/otro/run").status_code == 404
    assert admin.get(f"{V1}/apps/{app_id}").json()["jobs"][0]["hora"] == "08:00"


async def test_archivo_del_operador_entra_al_turno_con_su_hash(sessions, monkeypatch):
    import hashlib

    from app.apps import attachments
    llm = ScriptLLM({"action": "reply", "message": "Leí una transferencia de $49.000. ¿De qué alumno es?"})
    w = make_wa(sessions, llm=llm)
    _, _, _, (gym_id, assistant_id, _) = gym_world(sessions, monkeypatch, llm)
    with sessions() as s:
        s.add(WaOperator(account_id=w.account_id, wa_id=WA_ID, client_id=gym_id, agent_id=assistant_id))
        s.commit()

    async def fake_read(data, mime):
        assert mime == "image/jpeg"
        return "Transferencia enviada\n$ 49.000,00\nN° de operación 123456"
    monkeypatch.setattr(attachments, "read", fake_read)
    w.graph.media_data, w.graph.media_mime = b"JPEG-comprobante", "image/jpeg"
    payload = text_payload("x", "wamid.img")
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message.pop("text")
    message.update(type="image", image={"id": "media.1", "mime_type": "image/jpeg", "caption": "pago de juan"})
    await send(w, payload)

    turn = llm.seen[0][0][-1]["content"].split("\n\n", 1)[1]          # después de la línea AHORA
    assert turn.startswith(f"[archivo recibido · sha256 {hashlib.sha256(b'JPEG-comprobante').hexdigest()}]")
    assert "pago de juan" in turn and "N° de operación 123456" in turn
    assert w.graph.sent[-1][2] == "Leí una transferencia de $49.000. ¿De qué alumno es?"


async def test_imagen_a_un_agente_comun_sigue_con_la_respuesta_fija(sessions, monkeypatch):
    w = make_wa(sessions)
    payload = text_payload("x", "wamid.img2")
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message.pop("text")
    message.update(type="image", image={"id": "media.2", "mime_type": "image/jpeg"})
    await send(w, payload)
    assert w.graph.sent[-1][2] == settings.wa_unsupported_reply


def test_gateway_deja_bajar_csv(sessions, monkeypatch, gateway_client):
    import httpx
    _, _, _, (_, _, app_id) = gym_world(sessions, monkeypatch)

    async def csv_view(base_url, token, path, query, actor, prefix):
        return httpx.Response(200, content="\ufeffnombre;hora\r\nJuan;08:05\r\n".encode(), headers={
            "content-type": "text/csv; charset=utf-8", "content-disposition": 'attachment; filename="minuta.csv"'})
    monkeypatch.setattr(app_client, "get_view", csv_view)
    url, _ = make_link(sessions, app_id)
    gateway_client.get(url.removeprefix("https://apps.test"), follow_redirects=False)
    r = gateway_client.get("/gym/gym-gestion/minuta/?formato=csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == 'attachment; filename="minuta.csv"'


async def test_el_turno_siguiente_ve_los_resultados_del_anterior(sessions, monkeypatch):
    """Casos de uso (12-oct-2026): sin los resultados, en "dale, mandalos" inventaba los alumno_id."""
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "reply", "message": "Encontré a Juan."},
                    {"action": "reply", "message": "ok"})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = JUAN
    cid = start(engine, agent_id, client_id)
    await engine.process_turn(cid, "buscá a juan")
    await engine.process_turn(cid, "dale")
    previous = llm.seen[2][0][-2]
    assert previous["role"] == "assistant" and previous["content"].startswith("Encontré a Juan.")
    assert '"alumno_id": 7' in previous["content"]



async def test_link_sin_marca_se_agrega_al_final(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "abrir_vista", "arguments": {"vista": "minuta"}},
                    {"action": "reply", "message": "Te paso la minuta."})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "pasame la minuta")
    text, url = turn.assistant_message.split("\n\n")
    assert text == "Te paso la minuta." and url.startswith("https://apps.test/gym/gym-gestion/minuta/?k=")


async def test_despues_de_una_busqueda_ambigua_no_registra(sessions, monkeypatch):
    """Casos de uso (12-oct-2026): "vino Juan a las diez" registraba a Juan Perez, o a los dos Juanes."""
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "call", "tool": "registrar_asistencias",
                     "arguments": {"ingresos": [{"alumno": "Juan Pérez", "hora": "10:00"}]}},
                    {"action": "reply", "message": "¿Juan Pérez o Juan Pereyra?"})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = {"ok": True, "result": {"ambiguo": True, "candidatos": [
        {"alumno_id": 1, "nombre": "Juan Pérez"}, {"alumno_id": 2, "nombre": "Juan Pereyra"}]}}
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "vino juan a las diez")
    assert [c[0] for c in fake.calls] == ["buscar_alumno"]
    assert "la búsqueda fue ambigua" in llm.seen[2][0][-1]["content"]
    assert turn.assistant_message == "¿Juan Pérez o Juan Pereyra?"
    # En el turno siguiente, con la eleccion del usuario, si registra.
    llm.steps = [json.dumps({"action": "call", "tool": "registrar_asistencias",
                             "arguments": {"ingresos": [{"alumno": "Juan Pereyra", "hora": "10:00"}]}}),
                 json.dumps({"action": "reply", "message": "Listo."})]
    await engine.process_turn(cid, "Pereyra")
    assert fake.calls[-1][0] == "registrar_asistencias"


@pytest.mark.parametrize("respuesta, ejecuta", [("Sí", True), ("sí, dale", True), ("Dale.", True), ("confirmo", True),
                                                ("Dale, mandalo", True), ("Sí, confirmo, gracias", True),
                                                ("no", False), ("cancelalo", False)])
async def test_si_o_no_claro_lo_resuelve_la_plataforma(sessions, monkeypatch, respuesta, ejecuta):
    """12-oct-2026: con "Sí" el LLM volvia a pedir la herramienta en vez de confirm, y seguia preguntando."""
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "call", "tool": "baja_alumno", "arguments": {"alumno_id": 7}},
                    {"action": "reply", "message": "¿Confirmás la baja?"},
                    {"action": "reply", "message": "Listo." if ejecuta else "Ok, no hago nada."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = JUAN
    cid = start(engine, agent_id, client_id)
    await engine.process_turn(cid, "dale de baja a juan")
    state, _ = await engine.process_turn(cid, respuesta)
    assert (fake.calls[-1][0] == "baja_alumno") is ejecuta
    assert state.progress.pending is None
    # El LLM ya no elige confirm/cancel: solo redacta la respuesta con el resultado.
    assert "confirm" not in json.dumps(llm.seen[-1][1])


async def test_otra_cosa_con_algo_pendiente_lo_decide_el_llm(sessions, monkeypatch):
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "call", "tool": "baja_alumno", "arguments": {"alumno_id": 7}},
                    {"action": "reply", "message": "¿Confirmás la baja?"},
                    {"action": "cancel"}, {"action": "reply", "message": "Vino 1 persona."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    fake.results["buscar_alumno"] = JUAN
    cid = start(engine, agent_id, client_id)
    await engine.process_turn(cid, "dale de baja a juan")
    state, _ = await engine.process_turn(cid, "¿quién vino hoy?")
    assert "confirm" in json.dumps(llm.seen[3][1])          # el LLM decide
    assert [c[0] for c in fake.calls] == ["buscar_alumno"] and state.progress.pending is None


async def test_marca_sin_vista_pide_la_vista(sessions, monkeypatch):
    """12-oct-2026: le llegó "[[link1]]" literal al usuario (escribió la marca sin pedir la vista)."""
    llm = ScriptLLM({"action": "reply", "message": "Corregido. Acá el listado: [[link1]]"},
                    {"action": "call", "tool": "abrir_vista", "arguments": {"vista": "minuta"}},
                    {"action": "reply", "message": "Corregido. Acá el listado: [[link1]]"})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "corregilo y pasame el listado")
    assert "escribiste una marca de link sin pedir la vista" in llm.seen[1][0][-1]["content"]
    assert "[[" not in turn.assistant_message and "https://apps.test/gym/gym-gestion/minuta/" in turn.assistant_message


async def test_marca_inventada_de_una_vista_que_no_existe(sessions, monkeypatch):
    """12-oct-2026: "te mando la planilla: [[link_planes]]" (la app todavía no tenía la vista planes)."""
    llm = ScriptLLM({"action": "reply", "message": "Te mando la planilla: [[link_planes]]"},
                    {"action": "reply", "message": "Te mando la planilla: [[planes]]"})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "qué planes hay")
    assert "no está en abrir_vista" in llm.seen[1][0][-1]["content"]
    assert turn.assistant_message == "Te mando la planilla:"


async def test_marca_sin_vista_dos_veces_se_saca(sessions, monkeypatch):
    llm = ScriptLLM({"action": "reply", "message": "Listo: [[link1]]"}, {"action": "reply", "message": "Listo: [[link2]]"})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    cid = start(engine, agent_id, client_id)
    _, turn = await engine.process_turn(cid, "pasame algo")
    assert turn.assistant_message == "Listo:"



@pytest.mark.parametrize("texto, si", [("Sí, confirmo.", True), ("dale, mandalos", True), ("de una", True),
                                       ("sí, pero a las 10", False), ("¿quién vino hoy?", False), ("no", False),
                                       ("sí, también Leandro Ortiz", False)])
def test_is_yes(texto, si):
    from app.conversation.assistant import is_yes
    assert is_yes(texto) is si



def test_sampling_por_familia_de_modelo():
    from app.llm.client import request_options, sampling_family
    assert sampling_family("cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4", "auto") == "gemma"
    assert sampling_family("RedHatAI/Qwen3.5-9B-quantized.w4a16", "auto") == "qwen"
    g = request_options(False, 128, None, "gemma")
    assert (g["temperature"], g["top_p"], g["extra_body"]["top_k"]) == (1.0, 0.95, 64)
    assert g["extra_body"]["chat_template_kwargs"] == {"enable_thinking": False}
    t = request_options(True, 512, None, "gemma")
    assert t["extra_body"]["chat_template_kwargs"] == {"enable_thinking": True}
    assert t["extra_body"]["thinking_token_budget"] == 512
    assert request_options(False, 128, 0.3, "gemma")["temperature"] == 0.3     # LLM_TEMPERATURE pisa


async def test_el_asistente_pide_razonamiento(sessions, monkeypatch):
    monkeypatch.setattr(settings, "assistant_thinking", True)
    monkeypatch.setattr(settings, "assistant_thinking_budget", 512)
    llm = ScriptLLM({"action": "reply", "message": "Hola"})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    await engine.process_turn(start(engine, agent_id, client_id), "hola")
    assert llm.thinking == (True, 512)



async def test_salida_no_json_se_reintenta_una_vez(sessions, monkeypatch):
    llm = ScriptLLM({"action": "reply", "message": "Hola"})
    llm.steps.insert(0, '{"action": "reply", "message": "cort')        # cortada por el tope de tokens
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    _, turn = await engine.process_turn(start(engine, agent_id, client_id), "hola")
    assert turn.assistant_message == "Hola"



async def test_repetir_herramienta_obliga_a_responder(sessions, monkeypatch):
    """12-oct-2026: con razonamiento repetía ficha_alumno hasta agotar los pasos (FALLBACK)."""
    call = {"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "sofia"}}
    llm = ScriptLLM(call, call, {"action": "reply", "message": "Vence el 16/08 y termina el 05/11."})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    _, turn = await engine.process_turn(start(engine, agent_id, client_id), "¿cuándo vence lo de sofía?")
    assert turn.assistant_message.startswith("Vence")
    assert [o["properties"]["action"]["enum"][0] for o in llm.seen[2][1]["anyOf"]] == ["reply"]


async def test_el_ultimo_paso_solo_responde(sessions, monkeypatch):
    monkeypatch.setattr(settings, "assistant_max_steps", 2)
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "a"}},
                    {"action": "reply", "message": "Listo."})
    _, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    _, turn = await engine.process_turn(start(engine, agent_id, client_id), "buscá")
    assert turn.assistant_message == "Listo."
    assert len(llm.seen[1][1]["anyOf"]) == 1



async def test_nombre_de_campo_como_valor_no_se_ejecuta(sessions, monkeypatch):
    """12-oct-2026, Gemma a temperatura 1.0: registrar_pago con "alumno": "alumno_id"."""
    llm = ScriptLLM({"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "alumno_id"}},
                    {"action": "call", "tool": "buscar_alumno", "arguments": {"texto": "juan"}},
                    {"action": "reply", "message": "Encontré a Juan."})
    fake, engine, llm, (client_id, agent_id, _) = gym_world(sessions, monkeypatch, llm)
    await engine.process_turn(start(engine, agent_id, client_id), "buscá a juan")
    assert [c[1] for c in fake.calls] == [{"texto": "juan"}]
    assert "pusiste 'alumno_id' como valor" in llm.seen[1][0][-1]["content"]


def test_placeholders():
    from app.conversation.assistant import placeholders
    assert placeholders({"alumno": "alumno_id", "medio": "efectivo"}, {"alumno", "medio"}) == ["alumno_id"]
    assert placeholders({"ingresos": [{"alumno": "alumno", "hora": "08:00"}]}, {"alumno", "hora"}) == ["alumno"]
    assert placeholders({"alumno": "Juan Pérez", "texto": "pago_id del lunes"}, {"alumno", "texto"}) == []


def test_el_protocolo_no_tiene_nada_de_un_negocio_y_las_reglas_son_del_agente():
    """12-oct-2026: las reglas de SUGYM (pagos, cuotas, comprobantes, tono) estaban en el código; son
    configuración del agente (conversation.rules)."""
    import re

    from app.conversation.assistant import SYSTEM, WHATSAPP, build_system
    from app.conversation.models import ConversationState, Workflow
    assert not re.search(r"alumno|cuota|pago|comprobante|gimnas|rioplat|importe|dueño|negocio", SYSTEM + WHATSAPP,
                         re.IGNORECASE)
    w = Workflow.model_validate({**ASSISTANT, "id": "a", "version": 1,
                                 "conversation": {"opening": "Hola", "rules": ["Hablás de vos.", "Fechas como 16/08."]},
                                 "knowledge": "Abre de 7 a 22."})
    system = build_system(w, ConversationState(conversation_id="c", agent_id="a", channel="whatsapp", fields={}), [])
    assert "REGLAS:\n- Hablás de vos.\n- Fechas como 16/08." in system and "Abre de 7 a 22." in system
    assert "Idioma: es-AR" in system
