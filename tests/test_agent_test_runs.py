"""Corridas de casos de prueba: runner, herramientas grabadas, areas congeladas y cola (docs/features/CASOS_DE_PRUEBA.md)."""
import asyncio
import datetime
import json
import uuid
from zoneinfo import ZoneInfo

import pytest
from cryptography.fernet import Fernet

from app.agent_tests import runner, runs
from app.config import settings
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, Workflow
from app.llm.resolver import LLMResolver
from app.models import AgentTestCase, AgentTestRun, HandoffArea, ToolRun
from app.llm.prompt import TRUNCATED  # noqa: F401  (documenta el recorte que se corrige con la traza)
from app.services import handoff
from app.services.handoff import DAYS

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401
from .test_llm_byok import new_connection
from .test_motor_tools import Script, llm_with


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def definition(*, prompt="Atendé consultas.", tools=(), handoff_cfg=None, llm=None):
    data = {"id": "demo", "version": 1, "agent": {"name": "Demo", "language": "es"}, "prompt": prompt,
            "tools": [{"tool": t} for t in tools]}
    if handoff_cfg:
        data["handoff"] = handoff_cfg
    if llm:
        data["llm"] = llm
    return Workflow.model_validate(data).model_dump(mode="json")


def make_engine(api, llm=None):
    return ConversationEngine(llm or api.llm, api.engine.store)


def case_data(cid="c1", checks=None, tool_results=None, snapshot=None):
    return {"id": cid, "name": "Caso", "checks": checks or [], "known_failure": False,
            "snapshot": {"messages": [{"role": "assistant", "text": "Hola, soy Sofía."}],
                         "user_message": "¿Hay salidas?",
                         "user_message_at": "2026-11-20T10:00:00-03:00",
                         "progress": {"started_at": "2026-11-20T10:00:00-03:00",
                                      "call": {"id": "x", "mode": "voice"}},
                         "channel": "voice", "handoff": False, **(snapshot or {})},
            "tool_results": tool_results or []}


def run_data(cases, variants=None, repetitions=1):
    variants = variants or [{"key": "publicada", "version": 1}]
    return {"id": "run", "repetitions": repetitions, "variants": variants,
            "cases": [{"id": c["id"], "name": c["name"], "checks": c["checks"],
                       "known_failure": c.get("known_failure", False)} for c in cases],
            "total": sum(1 for _ in cases) * len(variants) * repetitions}


def agent_data(client, definition_, version=1):
    return {"id": "agent", "client_id": client["id"], "version": version, "definition": definition_}


def make_tool(admin, client, slug="salidas"):
    body = {"slug": slug, "type": "http", "definition": {
        "description": "Busca salidas para un destino.",
        "http": {"method": "GET", "url": "http://localhost:1/salidas"}}}
    r = admin.post(f"{V1}/clients/{client['id']}/tools", json=body)
    assert r.status_code == 201, r.text


async def run_cases(api, agent, case, variants=None, repetitions=1, llm=None, stop=None, progress=None):
    return await runner.execute(run_data([case], variants, repetitions), agent, {case["id"]: case},
                                make_engine(api, llm), api.sessions, progress, stop)


def make_case(api, client, agent, checks=None):
    with api.sessions() as s:
        case = AgentTestCase(client_id=client["id"], agent_id=agent["id"], name="Caso", channel="voice",
                             snapshot={"messages": [{"role": "assistant", "text": "Hola"}],
                                       "user_message": "¿Qué horario tienen?",
                                       "progress": {"started_at": "2026-11-20T10:00:00-03:00"}},
                             tool_results=[], checks=checks or [])
        s.add(case)
        s.commit()
        return case.id


# ---------- herramientas grabadas ----------

async def test_pide_la_herramienta_y_recibe_lo_grabado(api, admin):
    c = make_client(admin, max_tools=None)
    make_tool(admin, c)
    script = Script(("", [("salidas", {"destino": "Castelli"})]), ("Hay una a las 20:00.", []))
    caso = case_data(checks=[{"type": "usa_herramienta", "tool": "salidas"}, {"type": "datos_de_la_herramienta"}],
                     tool_results=[{"name": "salidas", "arguments": '{"destino": "Castelli"}',
                                    "result": '{"hora": "20:00"}'}])
    out = await run_cases(api, agent_data(c, definition(tools=("salidas",))), caso, llm=llm_with(script))
    rep = out["results"][0]["variants"][0]["repetitions"][0]
    assert rep["passed"] is True and rep["error"] is None
    assert rep["tools"] == [{"name": "salidas", "arguments": json.dumps({"destino": "Castelli"}),
                             "result": '{"hora": "20:00"}', "recorded": True}]
    assert json.loads(script.requests[1]["messages"][-1]["content"]) == {"hora": "20:00"}


async def test_sin_resultado_grabado_devuelve_el_error_fijo(api, admin):
    c = make_client(admin, max_tools=None)
    make_tool(admin, c)
    script = Script(("", [("salidas", {})]), ("No sé.", []))
    out = await run_cases(api, agent_data(c, definition(tools=("salidas",))), case_data(), llm=llm_with(script))
    rep = out["results"][0]["variants"][0]["repetitions"][0]
    assert rep["tools"][0]["recorded"] is False
    assert json.loads(script.requests[1]["messages"][-1]["content"]) == {
        "ok": False, "error": "sin resultado grabado en el caso"}


async def test_no_ejecuta_la_herramienta_ni_deja_tool_runs(api, admin, monkeypatch):
    c = make_client(admin, max_tools=None)
    make_tool(admin, c)
    from app.tools import conversation as conversation_module
    executed = []
    monkeypatch.setattr(conversation_module, "run", lambda *a, **k: executed.append(1))
    script = Script(("", [("salidas", {})]), ("Listo.", []))
    await run_cases(api, agent_data(c, definition(tools=("salidas",))), case_data(), llm=llm_with(script))
    assert executed == []
    with api.sessions() as s:
        assert s.query(ToolRun).count() == 0


# ---------- areas y prompt grabados ----------

async def test_area_cerrada_a_la_hora_del_mensaje_aunque_ahora_este_abierta(api, admin):
    c = make_client(admin)
    tz = settings.agent_timezone
    now = datetime.datetime.now(ZoneInfo(tz))
    today = DAYS[now.weekday()]
    schedule = {"tz": tz, "week": {today: [["00:00", "24:00"]]}}
    assert handoff.is_open(schedule) is True
    with api.sessions() as s:
        area = HandoffArea(client_id=c["id"], name="Operaciones", description="", schedule=schedule)
        s.add(area)
        s.commit()
        area_id = area.id
    ayer = now - datetime.timedelta(days=1)
    at = ayer.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
    caso = case_data(snapshot={"handoff": True, "user_message_at": at,
                               "progress": {"started_at": at, "call": {"id": "x", "mode": "voice"}}})
    script = Script(("Te paso con una persona.", []))
    defn = definition(handoff_cfg={"areas": [{"area_id": area_id, "when": "consultas"}]})
    await run_cases(api, agent_data(c, defn), caso, llm=llm_with(script))
    transfer = next(t for t in script.requests[0]["tools"] if t["function"]["name"] == "transfer_call")
    assert "cerrada ahora" in transfer["function"]["description"]


async def test_el_prompt_usa_la_hora_grabada(api, admin):
    c = make_client(admin)
    script = Script(("Hola.", []))
    defn = definition(prompt="Hoy es {{today}}.")
    await run_cases(api, agent_data(c, defn), case_data(), llm=llm_with(script))
    system = script.requests[0]["messages"][0]["content"]
    assert "viernes 2026-11-20" in system


async def test_herramienta_que_no_carga_es_un_error_visible(api, admin):
    c = make_client(admin)
    script = Script(("Hola.", []))
    out = await run_cases(api, agent_data(c, definition(tools=("no_existe",))), case_data(), llm=llm_with(script))
    rep = out["results"][0]["variants"][0]["repetitions"][0]
    assert rep["passed"] is False
    assert "no se cargó" in rep["error"] and "no_existe" in rep["error"]


# ---------- variantes ----------

async def test_publicada_y_borrador_en_la_misma_corrida(api, admin):
    c = make_client(admin)
    script = Script(("Respuesta publicada.", []), ("Respuesta del borrador.", []))
    variants = [{"key": "publicada", "version": 1},
                {"key": "borrador", "version": 2, "definition": definition(prompt="Otro prompt.")}]
    out = await run_cases(api, agent_data(c, definition()), case_data(), variants=variants, llm=llm_with(script))
    reps = {v["key"]: v["repetitions"][0]["text"] for v in out["results"][0]["variants"]}
    assert reps == {"publicada": "Respuesta publicada.", "borrador": "Respuesta del borrador."}


# ---------- BYOK y tokens ----------

async def test_byok_que_falla_no_abre_el_circuito_de_las_llamadas(api, admin, monkeypatch):
    c = make_client(admin)
    conn = new_connection(admin, c)

    class Failing:
        label = "openrouter:vendor/model"
        model = "vendor/model"

        async def converse(self, *args, **kwargs):
            raise RuntimeError("proveedor caido")

    monkeypatch.setattr(LLMResolver, "_client", lambda self, data, stage, generation, defaults: Failing())
    api.llm.turns = [AgentTurn(assistant_message="respaldo local")]
    live = LLMResolver(api.llm, api.sessions)
    plan = {"stages": [{"from_turn": 1, "connection": conn["id"], "model": "vendor/model"}],
            "fallback_local": True}
    out = await run_cases(api, agent_data(c, definition(llm=plan)), case_data(), llm=api.llm)
    rep = out["results"][0]["variants"][0]["repetitions"][0]
    assert rep["text"] == "respaldo local"
    assert rep["llm"]["provider"] == "local"
    assert live.breaker.is_open(conn["id"]) is False


async def test_suma_los_tokens(api, admin):
    c = make_client(admin)

    class Tokens:
        model = "m"

        def derive(self, **kwargs):
            return self

        async def converse(self, *args, **kwargs):
            return AgentTurn(assistant_message="ok", input_tokens=7, output_tokens=5)

    out = await run_cases(api, agent_data(c, definition()), case_data(), llm=Tokens())
    assert out["input_tokens"] == 7 and out["output_tokens"] == 5


# ---------- cola ----------

def test_reinicio_marca_las_corridas_en_curso_como_fallidas(api, admin):
    c = make_client(admin)
    with api.sessions() as s:
        run = AgentTestRun(client_id=c["id"], agent_id="a", status="running", repetitions=5, variants=[],
                           cases=[], total=1)
        s.add(run)
        s.commit()
        run_id = run.id
    assert runs.requeue_interrupted(api.sessions) == 1
    with api.sessions() as s:
        got = s.get(AgentTestRun, run_id)
        assert got.status == "failed" and got.error == runs.RESTART_ERROR


def test_dos_posts_arman_una_sola_corrida(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    with api.sessions() as s:
        s.add(AgentTestCase(client_id=c["id"], agent_id=agent["id"], name="Caso", channel="voice",
                            snapshot={"messages": [], "user_message": "x", "progress": {}},
                            tool_results=[], checks=[]))
        s.commit()
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1})
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "queued" and r.json()["total"] == 1
    r2 = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1})
    assert r2.status_code == 409 and r2.json()["code"] == "test_run_in_progress"
    assert r2.json()["run_id"] == r.json()["id"]


def test_corrida_de_otro_agente_da_404(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    otro = make_agent(admin, c, template="demo_booking", slug="turnos", name="Turnos")
    with api.sessions() as s:
        case = AgentTestCase(client_id=c["id"], agent_id=agent["id"], name="Caso", channel="voice",
                             snapshot={"messages": [], "user_message": "x", "progress": {}},
                             tool_results=[], checks=[])
        s.add(case)
        s.commit()
        case_id = case.id
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1, "case_ids": [case_id]}).json()
    assert admin.get(f"{V1}/agents/{otro['id']}/test-runs/{run['id']}").status_code == 404
    r = admin.post(f"{V1}/agents/{otro['id']}/test-runs", json={"repetitions": 1, "case_ids": [case_id]})
    assert r.status_code == 404


def test_sin_casos_no_hay_corrida(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1})
    assert r.status_code == 422 and r.json()["code"] == "no_test_cases"


def test_definicion_invalida_da_422(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    with api.sessions() as s:
        s.add(AgentTestCase(client_id=c["id"], agent_id=agent["id"], name="Caso", channel="voice",
                            snapshot={"messages": [], "user_message": "x", "progress": {}},
                            tool_results=[], checks=[]))
        s.commit()
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs",
                   json={"repetitions": 1, "definition": {"id": "x", "version": 2}})
    assert r.status_code == 422 and r.json()["code"] == "invalid_definition"


async def test_la_cola_procesa_y_guarda_el_resultado(api, admin, monkeypatch):
    c = make_client(admin)
    agent = make_agent(admin, c)
    with api.sessions() as s:
        case = AgentTestCase(client_id=c["id"], agent_id=agent["id"], name="Caso", channel="voice",
                             snapshot={"messages": [{"role": "assistant", "text": "Hola"}],
                                       "user_message": "¿Qué horario tienen?",
                                       "progress": {"started_at": "2026-11-20T10:00:00-03:00"}},
                             tool_results=[], checks=[{"type": "dice", "text": "hola"}])
        s.add(case)
        s.commit()
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 2}).json()
    api.llm.turns = [AgentTurn(assistant_message="Hola, de 9 a 18."), AgentTurn(assistant_message="Hola.")]
    monkeypatch.setattr("app.runtime.get_conversation_engine", lambda: make_engine(api))
    assert runs.claim(api.sessions) == run["id"]
    await runs.process(api.sessions, run["id"])
    with api.sessions() as s:
        got = s.get(AgentTestRun, run["id"])
        assert got.status == "done" and got.done == got.total == 2
        variant = got.results[0]["variants"][0]
        assert variant["passed"] == 2 and variant["total"] == 2


def test_probar_ahora_con_un_caso_sin_guardar(api, admin):
    """T4: 'Probar ahora (5×)' manda draft_case y la publicada; la definición sin guardar arma la variante borrador."""
    from app.models import ConversationRow

    c = make_client(admin)
    agent = make_agent(admin, c)
    with api.sessions() as s:
        s.add(ConversationRow(id="cv-draft", client_id=c["id"], agent_id=agent["id"], agent_version=1,
                              channel="voice", status="completed", fields={}, messages=[
                                  {"role": "assistant", "text": "Hola."},
                                  {"role": "user", "text": "¿Qué horario?"},
                                  {"role": "assistant", "text": "De 9 a 18."}],
                              progress={"call": {"mode": "api"}}))
        s.commit()
    draft = {"conversation_id": "cv-draft", "message_index": 1, "name": "Probar",
             "checks": [{"type": "dice", "text": "9 a 18"}]}
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1, "draft_case": draft})
    assert r.status_code == 202, r.text
    run = r.json()
    assert [c["id"] for c in run["cases"]] == ["draft"]
    assert [v["key"] for v in run["variants"]] == ["publicada"]
    # Con una definición distinta, entra el borrador en la misma corrida.
    definition = {**agent["definition"], "prompt": "Otro prompt."}
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1, "draft_case": draft})
    assert r.status_code == 409
    with api.sessions() as s:
        s.query(AgentTestRun).update({"status": "done"})
        s.commit()
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs",
                   json={"repetitions": 1, "draft_case": draft, "definition": definition})
    assert r.status_code == 202, r.text
    assert [v["key"] for v in r.json()["variants"]] == ["publicada", "borrador"]


# ---------- cancelar ----------

async def test_cancelada_de_entrada_no_manda_ningun_turno(api, admin):
    c = make_client(admin)
    script = Script()
    stop = asyncio.Event()
    stop.set()
    out = await run_cases(api, agent_data(c, definition()), case_data(), repetitions=2, llm=llm_with(script),
                          stop=stop)
    assert script.requests == []
    assert out["results"] == [] and out["done"] == 0 and out["cancelled"] is True


async def test_el_pedido_corta_entre_casos_y_guarda_el_primero(api, admin):
    c = make_client(admin)
    cases = [case_data("c1"), case_data("c2")]
    script = Script(("Hola.", []))
    stop = asyncio.Event()

    async def progress(payload):
        stop.set()

    out = await runner.execute(run_data(cases, repetitions=1), agent_data(c, definition()),
                               {case["id"]: case for case in cases}, make_engine(api, llm_with(script)),
                               api.sessions, progress, stop)
    assert len(script.requests) == 1
    assert [item["case_id"] for item in out["results"]] == ["c1"]
    assert out["done"] == 1 and out["total"] == 2 and out["cancelled"] is True


async def test_pedido_con_todo_corrido_termina_done(api, admin):
    c = make_client(admin)
    stop = asyncio.Event()

    async def progress(payload):
        if payload["done"] >= payload["total"]:
            stop.set()

    out = await run_cases(api, agent_data(c, definition()), case_data(), llm=llm_with(Script(("Hola.", []))),
                          stop=stop, progress=progress)
    assert out["done"] == out["total"] == 1 and out["cancelled"] is False


def test_cancelar_en_cola_la_termina_y_la_cola_la_salta(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    make_case(api, c, agent)
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 2}).json()
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs/{run['id']}/cancel")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "cancelled" and out["started_at"] is None and out["finished_at"] is not None
    assert runs.claim(api.sessions) is None
    # Ya no hay corrida activa: se encola otra.
    assert admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1}).status_code == 202


def test_cancelar_dos_veces_y_una_terminada_no_cambian_nada(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    make_case(api, c, agent)
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1}).json()
    assert runs.claim(api.sessions) == run["id"]
    first = admin.post(f"{V1}/agents/{agent['id']}/test-runs/{run['id']}/cancel").json()
    assert first["status"] == "running" and first["cancel_requested_at"] is not None
    second = admin.post(f"{V1}/agents/{agent['id']}/test-runs/{run['id']}/cancel").json()
    assert second["cancel_requested_at"] == first["cancel_requested_at"]
    with api.sessions() as s:
        done = AgentTestRun(client_id=c["id"], agent_id=agent["id"], status="done", repetitions=1, variants=[],
                            cases=[], total=1, done=1, finished_at=datetime.datetime(2026, 11, 20, 10, 0))
        s.add(done)
        s.commit()
        done_id, finished = done.id, done.finished_at
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs/{done_id}/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "done" and r.json()["cancel_requested_at"] is None
    with api.sessions() as s:
        assert s.get(AgentTestRun, done_id).finished_at == finished


def test_cancelar_corrida_de_otro_agente_da_404(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    otro = make_agent(admin, c, template="demo_booking", slug="turnos", name="Turnos")
    make_case(api, c, agent)
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1}).json()
    assert admin.post(f"{V1}/agents/{otro['id']}/test-runs/{run['id']}/cancel").status_code == 404


def test_cancelar_corrida_de_otro_cliente_da_404(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    make_case(api, c, agent)
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1}).json()
    otro = make_client(admin, slug="beta")
    client_admin = client_user(api, admin, otro)
    r = client_admin.post(f"{V1}/agents/{agent['id']}/test-runs/{run['id']}/cancel")
    assert r.status_code == 404


def test_reinicio_con_pedido_de_cancelacion_queda_cancelada(api, admin):
    c = make_client(admin)
    with api.sessions() as s:
        run = AgentTestRun(client_id=c["id"], agent_id="a", status="running", repetitions=5, variants=[],
                           cases=[], total=1, cancel_requested_at=datetime.datetime(2026, 11, 20, 10, 0))
        s.add(run)
        s.commit()
        run_id = run.id
    assert runs.requeue_interrupted(api.sessions) == 1
    with api.sessions() as s:
        got = s.get(AgentTestRun, run_id)
        assert got.status == "cancelled" and got.error is None and got.finished_at is not None


async def test_el_vigia_prende_el_stop_con_el_pedido(api, admin):
    c = make_client(admin)
    with api.sessions() as s:
        run = AgentTestRun(client_id=c["id"], agent_id="a", status="running", repetitions=1, variants=[],
                           cases=[], total=1)
        s.add(run)
        s.commit()
        run_id = run.id
    assert runs.cancel_requested(api.sessions, run_id) is False
    with api.sessions() as s:
        s.get(AgentTestRun, run_id).cancel_requested_at = datetime.datetime(2026, 11, 20, 10, 0)
        s.commit()
    stop = asyncio.Event()
    await runs._watch(api.sessions, run_id, stop)
    assert stop.is_set() is True
    # La fila borrada (agente borrado en cascada) tambien corta.
    assert runs.cancel_requested(api.sessions, "no-existe") is True


async def test_procesar_cancelada_al_arrancar_queda_cancelada(api, admin, monkeypatch):
    c = make_client(admin)
    agent = make_agent(admin, c)
    make_case(api, c, agent)
    make_case(api, c, agent)
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 1}).json()
    assert runs.claim(api.sessions) == run["id"]
    # El vigia ve el pedido apenas arranca: no se manda ningun turno y queda cancelada.
    async def watch(sessions, run_id, stop):
        stop.set()

    monkeypatch.setattr(runs, "_watch", watch)
    script = Script()
    monkeypatch.setattr("app.runtime.get_conversation_engine", lambda: make_engine(api, llm_with(script)))
    await runs.process(api.sessions, run["id"])
    assert script.requests == []
    with api.sessions() as s:
        got = s.get(AgentTestRun, run["id"])
        assert got.status == "cancelled" and got.done == 0 and got.total == 2
        assert got.finished_at is not None and got.summary == []


def test_finish_de_una_cancelada_guarda_lo_parcial_y_el_summary(api, admin):
    c = make_client(admin)
    with api.sessions() as s:
        run = AgentTestRun(client_id=c["id"], agent_id="a", status="running", repetitions=2, variants=[],
                           cases=[], total=2)
        s.add(run)
        s.commit()
        run_id = run.id
    item = {"case_id": "c1", "name": "Caso", "variants": [
        {"key": "publicada", "version": 1, "passed": 1, "total": 1, "errors": 0, "repetitions": []}]}
    runs.finish(api.sessions, run_id, {"results": [item], "input_tokens": 7, "output_tokens": 5,
                                       "tool_revisions": {}, "total": 2, "done": 1, "cancelled": True})
    with api.sessions() as s:
        got = s.get(AgentTestRun, run_id)
        assert got.status == "cancelled" and got.done == 1 and got.total == 2
        assert got.results == [item] and got.finished_at is not None
        assert got.summary == [{"case_id": "c1", "variants": [{"key": "publicada", "passed": 1, "total": 1}]}]


async def test_la_cola_guarda_el_summary_y_el_pasa_x_n(api, admin, monkeypatch):
    c = make_client(admin)
    agent = make_agent(admin, c)
    case_id = make_case(api, c, agent, checks=[{"type": "dice", "text": "9 a 18"}])
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 2}).json()
    api.llm.turns = [AgentTurn(assistant_message="De 9 a 18."), AgentTurn(assistant_message="De 9 a 18.")]
    monkeypatch.setattr("app.runtime.get_conversation_engine", lambda: make_engine(api))
    assert runs.claim(api.sessions) == run["id"]
    await runs.process(api.sessions, run["id"])
    with api.sessions() as s:
        got = s.get(AgentTestRun, run["id"])
        assert got.status == "done" and got.summary == [
            {"case_id": case_id, "variants": [{"key": "publicada", "passed": 2, "total": 2}]}]
    # La lista sigue dando el mismo «pasa X/N».
    cases = admin.get(f"{V1}/agents/{agent['id']}/test-cases").json()
    assert cases[0]["last_run"]["variants"] == [{"key": "publicada", "passed": 2, "total": 2}]


# ---------- lista liviana y resumen ----------

def _done_run(api, c, agent_id, case_id, *, summary):
    with api.sessions() as s:
        run = AgentTestRun(
            client_id=c["id"], agent_id=agent_id, status="done", repetitions=1,
            variants=[{"key": "publicada", "version": 1}], cases=[{"id": case_id, "name": "Caso"}],
            results=[{"case_id": case_id, "name": "Caso", "variants": [
                {"key": "publicada", "version": 1, "passed": 1, "total": 1, "errors": 0,
                 "repetitions": [{"text": "De 9 a 18.", "passed": True}]}]}],
            summary=summary, done=1, total=1)
        s.add(run)
        s.commit()
        return run.id


def test_lista_liviana_sin_resultados_ni_definicion(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    case_id = make_case(api, c, agent)
    done_id = _done_run(api, c, agent["id"], case_id,
                        summary=[{"case_id": case_id, "variants": [{"key": "publicada", "passed": 1, "total": 1}]}])
    # Una segunda corrida, con borrador: la definición sin guardar viaja en `variants`.
    definition = {**agent["definition"], "prompt": "Otro prompt."}
    r = admin.post(f"{V1}/agents/{agent['id']}/test-runs",
                   json={"repetitions": 1, "definition": definition, "case_ids": [case_id]})
    assert r.status_code == 202, r.text
    created = r.json()
    assert [v["key"] for v in created["variants"]] == ["publicada", "borrador"]

    completa = admin.get(f"{V1}/agents/{agent['id']}/test-runs").json()
    assert [x["id"] for x in completa] == [created["id"], done_id]
    assert completa[1]["results"] is not None
    assert "definition" in completa[0]["variants"][1]

    lista = admin.get(f"{V1}/agents/{agent['id']}/test-runs",
                      params={"limit": 1, "include_results": False}).json()
    assert len(lista) == 1 and lista[0]["id"] == created["id"]
    assert lista[0]["results"] is None
    assert [v["key"] for v in lista[0]["variants"]] == ["publicada", "borrador"]
    assert all("definition" not in v for v in lista[0]["variants"])

    got = admin.get(f"{V1}/agents/{agent['id']}/test-runs/{created['id']}",
                    params={"include_results": False}).json()
    assert got["results"] is None and got["total"] == 2
    assert admin.get(f"{V1}/agents/{agent['id']}/test-runs", params={"limit": 31}).status_code == 422
    assert admin.get(f"{V1}/agents/{agent['id']}/test-runs", params={"limit": 0}).status_code == 422


def test_corrida_vieja_sin_summary_da_el_mismo_pasa_x_n(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    case_id = make_case(api, c, agent)
    run_id = _done_run(api, c, agent["id"], case_id, summary=None)   # anterior a la columna
    lista = admin.get(f"{V1}/agents/{agent['id']}/test-cases").json()
    assert lista[0]["last_run"]["run_id"] == run_id
    assert lista[0]["last_run"]["variants"] == [{"key": "publicada", "passed": 1, "total": 1}]
    detalle = admin.get(f"{V1}/agents/{agent['id']}/test-cases/{case_id}").json()
    assert [x["run_id"] for x in detalle["history"]] == [run_id]
    assert detalle["history"][0]["variants"] == [{"key": "publicada", "passed": 1, "total": 1}]
    # Y el `pasa X/N` de una corrida con summary coincide con el de `results`.
    segundo = _done_run(api, c, agent["id"], case_id,
                        summary=[{"case_id": case_id, "variants": [{"key": "publicada", "passed": 1, "total": 1}]}])
    assert admin.get(f"{V1}/agents/{agent['id']}/test-cases").json()[0]["last_run"]["variants"] == [
        {"key": "publicada", "passed": 1, "total": 1}]
    assert [x["run_id"] for x in admin.get(f"{V1}/agents/{agent['id']}/test-cases/{case_id}").json()["history"]] \
        == [segundo, run_id]
