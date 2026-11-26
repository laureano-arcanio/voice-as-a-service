"""Evidencia del historial en `datos_de_la_herramienta` y respaldos por variante (docs/features/CASOS_DE_PRUEBA.md).

Los helpers son los minimos de `test_agent_test_runs.py`; la evidencia nueva va en este archivo.
"""
import asyncio

from app.agent_tests import runner, runs
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, Workflow
from app.llm.resolver import LLMResolver
from app.models import AgentTestCase, AgentTestRun

from .test_api import V1, admin, make_client  # noqa: F401
from .test_llm_byok import new_connection
from .test_motor_tools import Script, llm_with

# Una consulta vieja del caso: el modelo ya la vio en el historial y no la repite en el turno.
HISTORIAL = {"role": "assistant", "text": "", "tools": [
    {"id": "call_1", "name": "salidas", "arguments": "{}", "result": '{"hora": "20:00", "precio": 13500}'}]}


def definition(*, llm=None):
    data = {"id": "demo", "version": 1, "agent": {"name": "Demo", "language": "es"}, "prompt": "Atendé consultas."}
    if llm:
        data["llm"] = llm
    return Workflow.model_validate(data).model_dump(mode="json")


def make_engine(api, llm=None):
    return ConversationEngine(llm or api.llm, api.engine.store)


def case_data(cid="c1", checks=None, snapshot=None):
    return {"id": cid, "name": "Caso", "checks": checks or [], "known_failure": False,
            "snapshot": {"messages": [{"role": "assistant", "text": "Hola, soy Sofía."}],
                         "user_message": "¿Hay salidas?",
                         "user_message_at": "2026-11-20T10:00:00-03:00",
                         "progress": {"started_at": "2026-11-20T10:00:00-03:00",
                                      "call": {"id": "x", "mode": "voice"}},
                         "channel": "voice", "handoff": False, **(snapshot or {})},
            "tool_results": []}


def run_data(cases, repetitions=1):
    return {"id": "run", "repetitions": repetitions, "variants": [{"key": "publicada", "version": 1}],
            "cases": [{"id": c["id"], "name": c["name"], "checks": c["checks"],
                       "known_failure": c.get("known_failure", False)} for c in cases],
            "total": len(cases) * repetitions}


def agent_data(client, definition_, version=1):
    return {"id": "agent", "client_id": client["id"], "version": version, "definition": definition_}


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


async def run_cases(api, agent, case, llm=None):
    return await runner.execute(run_data([case]), agent, {case["id"]: case}, make_engine(api, llm),
                                api.sessions)


# ---------- datos de la herramienta: historial ademas del turno ----------

def _case_with_history():
    return case_data(checks=[{"type": "datos_de_la_herramienta"}],
                     snapshot={"messages": [{"role": "assistant", "text": "Hola, soy Sofía."},
                                            {"role": "user", "text": "¿Hay salidas?"},
                                            HISTORIAL]})


async def test_el_chequeo_acepta_los_datos_del_historial(api, admin):
    """Sin volver a consultar: la hora y el importe salen de la consulta que ya estaba en el historial."""
    case = _case_with_history()
    script = Script(("Sale a las 20:00, 13.500 pesos.", []))
    out = await run_cases(api, agent_data(make_client(admin), definition()), case, llm=llm_with(script))
    rep = out["results"][0]["variants"][0]["repetitions"][0]
    assert rep["passed"] is True and rep["failures"] == []
    assert rep["tools"] == []          # no llamo a ninguna herramienta en el turno


async def test_un_dato_que_no_esta_en_el_historial_ni_en_el_turno_falla(api, admin):
    case = _case_with_history()
    script = Script(("Sale a las 21:30.", []))
    out = await run_cases(api, agent_data(make_client(admin), definition()), case, llm=llm_with(script))
    rep = out["results"][0]["variants"][0]["repetitions"][0]
    assert rep["passed"] is False
    assert rep["failures"] == [{"check": {"type": "datos_de_la_herramienta"},
                                "message": "La hora '21:30' no está en el resultado de la herramienta",
                                "span": "21:30"}]


# ---------- respaldos por variante ----------

def test_cada_variante_cuenta_los_respaldos_y_la_lista_los_muestra(api, admin, monkeypatch):
    """Con un BYOK que falla y `fallback_local`, la variante dice cuantas repeticiones contesto el respaldo."""
    c = make_client(admin)
    conn = new_connection(admin, c)

    class Failing:
        label = "openrouter:vendor/model"
        model = "vendor/model"

        async def converse(self, *args, **kwargs):
            raise RuntimeError("proveedor caido")

    monkeypatch.setattr(LLMResolver, "_client", lambda self, data, stage, generation, defaults: Failing())
    plan = {"stages": [{"from_turn": 1, "connection": conn["id"], "model": "vendor/model"}],
            "fallback_local": True}
    r = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "Ventas",
                                         "definition": definition(llm=plan)})
    assert r.status_code == 201, r.text
    agent = r.json()
    case_id = make_case(api, c, agent, checks=[{"type": "dice", "text": "respaldo"}])
    api.llm.turns = [AgentTurn(assistant_message="respaldo local") for _ in range(3)]
    run = admin.post(f"{V1}/agents/{agent['id']}/test-runs", json={"repetitions": 3}).json()
    monkeypatch.setattr("app.runtime.get_conversation_engine", lambda: make_engine(api))
    assert runs.claim(api.sessions) == run["id"]
    asyncio.run(runs.process(api.sessions, run["id"]))

    got = admin.get(f"{V1}/agents/{agent['id']}/test-runs/{run['id']}").json()
    variant = got["results"][0]["variants"][0]
    assert variant["fallbacks"] == 3 and variant["fallback_reasons"] == {"RuntimeError": 3}
    assert variant["passed"] == 3
    with api.sessions() as s:
        assert s.get(AgentTestRun, run["id"]).summary == [
            {"case_id": case_id, "variants": [{"key": "publicada", "passed": 3, "total": 3, "fallbacks": 3}]}]
    # La lista de casos lo ve sin abrir la corrida.
    listed = admin.get(f"{V1}/agents/{agent['id']}/test-cases").json()
    assert listed[0]["last_run"]["variants"] == [{"key": "publicada", "passed": 3, "total": 3, "fallbacks": 3}]
