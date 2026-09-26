"""Eval de calidad del LLM (scripts/eval): escenarios, metricas duras, simulador y
canal, sin LLM."""
import random

import pytest

from app.conversation.workflow import load_workflow, outcome_for
from app.conversation.models import ConversationState
from scripts.eval import checks
from scripts.eval.canal import CanalSttSim
from scripts.eval.escenarios import escenarios, grupos_disponibles
from scripts.eval.fichas import generar, rellenar
from scripts.eval.simulador import Guion, parsear

EVAL_WORKFLOWS = ["eval_cobranza", "eval_relevamiento", "eval_datos", "eval_turnos"]


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        yield from _strings(list(obj.values()))
    elif isinstance(obj, list):
        for x in obj:
            yield from _strings(x)


@pytest.mark.parametrize("wid", EVAL_WORKFLOWS)
def test_eval_workflows_load_in_both_engines(wid):
    assert load_workflow(wid).engine == "classic"
    s = load_workflow(f"{wid}_structured")
    assert s.engine == "structured" and s.fields == load_workflow(wid).fields


def test_cobranza_outcomes():
    wf = load_workflow("eval_cobranza")

    def outcome(**fields):
        st = ConversationState(conversation_id="x", workflow_id=wf.id, fields={**{f: None for f in wf.fields}, **fields})
        return outcome_for(wf, st).id

    assert outcome(titular=False) == "tercero"
    assert outcome(titular=True, promesa="paga_total", fecha_pago="viernes") == "acuerdo_total"
    assert outcome(titular=True, promesa="paga_total") == "incompleta"       # objetivo sin la fecha
    assert outcome(titular=True, promesa="cuotas", cuotas=3) == "acuerdo_cuotas"
    assert outcome(titular=True, promesa="no_paga") == "sin_acuerdo"


def test_all_groups_have_filled_scenarios():
    grupos = grupos_disponibles()
    assert {"cobranza", "relevamiento", "datos", "turnos", "demo_booking"} <= set(grupos)
    escs = escenarios(grupos, reps=2, seed=1)
    assert len(escs) >= 2 * 6 * 5
    for e in escs:
        load_workflow(e.agente)
        for texto in _strings([e.estilo, e.ficha, e.esperado, e.guion or []]):
            assert "{" not in texto, f"{e.id}: variable sin rellenar en {texto[:80]}"
        assert set(e.esperado["fields"]) <= set(load_workflow(e.agente).fields), e.id
        assert e.esperado["outcome"]
    # Misma semilla, misma ficha; otra repeticion, otra ficha.
    assert generar(1, "datos", "cooperativo", 0) == generar(1, "datos", "cooperativo", 0)
    assert generar(1, "datos", "cooperativo", 0)["email"] != generar(1, "datos", "cooperativo", 1)["email"]


def test_structured_variant_and_filters():
    escs = escenarios(["cobranza"], reps=1, seed=1, personas=["tercero"], engine="structured")
    assert [e.agente for e in escs] == ["eval_cobranza_structured"]
    assert any("revela" in p["motivo"] for p in escs[0].checks["prohibido"])       # el del grupo + el de la persona
    assert escenarios(["demo_booking"], 1, 1, engine="structured")[0].agente == "demo_booking"


def test_rellenar_keeps_unknown_braces():
    assert rellenar("hola {nombre} {2,}", {"nombre": "Ana"}) == "hola Ana {2,}"


def test_check_valor():
    cv = checks.check_valor
    assert cv(None, None) == "ok" and cv(None, "algo") == "mal"
    assert cv("x", None) == "falta"
    assert cv(True, True) == "ok" and cv(True, False) == "mal"
    assert cv(8, 8) == "ok" and cv(8, "8") == "ok" and cv(8, 10) == "mal" and cv(1, 10) == "mal"
    assert cv("3515551234", "351 555-1234") == "ok" and cv("3515551234", "3515551235") == "mal"
    assert cv("2 de octubre", "el viernes 2 de octubre") == "ok"
    assert cv("Avenida Colón", "avenida colon 1234, alta cordoba") == "ok"
    assert cv(["jueves", "8"], "jueves 8 de octubre 16:30") == "ok" and cv(["lunes"], "martes") == "mal"
    assert cv("*", "cualquier cosa") == "ok" and cv("*", None) == "falta"


def test_reglas_rotas():
    ch = {"siglas": ["DNI"], "frases_max": 3, "prohibido": [{"regex": "embargo", "motivo": "intimida"}]}
    assert checks.reglas_rotas("¿Me pasás tu DNI?", ch) == []
    rotas = checks.reglas_rotas("Son $23500 (con IVA). ¿Pagás? ¿O no? Te embargo.", ch)
    for r in ["simbolos", "digitos", "siglas", "mas_de_una_pregunta", "prohibido: intimida"]:
        assert r in rotas
    assert "usted" in checks.reglas_rotas("¿Usted puede pagar?", ch)
    assert "usted" in checks.reglas_rotas("Disculpe la molestia, le comento que puedes verlo.", ch)
    assert "usted" not in checks.reglas_rotas("Disculpá, te comento que podés verlo.", ch)
    assert "frases_largas" in checks.reglas_rotas("Una. Dos. Tres. Cuatro.", ch)
    assert checks.reglas_rotas("   ", ch) == ["vacio"]


def test_evaluar_summarizes_a_conversation():
    esc = escenarios(["cobranza"], reps=1, seed=1, personas=["cooperativo"])[0]
    v = esc.variables
    mensajes = [
        {"role": "assistant", "text": "Hola, ¿hablo con Carlos Gómez?"},
        {"role": "user", "text": "Sí, soy yo."},
        {"role": "assistant", "text": "Tenés una factura vencida. ¿Cómo querés pagarla?", "llm": [{"kind": "turno", "ms": 500}]},
        {"role": "user", "text": f"El {v['fecha_semana']} pago todo."},
        {"role": "assistant", "text": "Queda registrado para el viernes. ¡Gracias!",
         "llm": [{"kind": "turno", "ms": 700}, {"kind": "extraccion", "ms": 900}]},
    ]
    fields = {"titular": True, "promesa": "paga_total", "fecha_pago": v["fecha_semana"], "cuotas": 2}
    c = checks.evaluar(esc, fields, "acuerdo_total", "completed", mensajes, None)
    assert c["datos"]["titular"] == "ok" and c["datos"]["fecha_pago"] == "ok"
    assert c["datos"]["cuotas"] == "mal" and c["inventados"] == ["cuotas"]
    assert c["outcome_ok"] and c["termino"] and c["turnos"] == 2
    assert c["llm_turno_ms_p50"] == 600 and c["llm_extraccion_ms_p50"] == 900
    assert c["reglas_n"] == 0 and c["problemas"] == 3
    # Sin cerrar y con error: peor puntaje, cierre "sin_terminar".
    c2 = checks.evaluar(esc, {}, None, "active", mensajes[:3], "Timeout")
    assert c2["outcome"] == "sin_terminar" and not c2["outcome_ok"] and c2["problemas"] > c["problemas"]


def test_parsear_simulador():
    assert parsear('{"dice": "Sí, soy yo.", "corta": false}') == ("Sí, soy yo.", False)
    assert parsear('bla {"dice": "Chau", "corta": true} bla') == ("Chau", True)
    assert parsear("Hola, ¿quién habla?") == ("Hola, ¿quién habla?", False)


async def test_guion_runs_out_then_hangs_up():
    g = Guion(["Sí.", "Dale, chau."])
    assert await g.responder(None, []) == ("Sí.", False)
    assert await g.responder(None, []) == ("Dale, chau.", True)
    assert await g.responder(None, []) == ("¿Cómo? No te entendí.", False)
    assert (await g.responder(None, []))[1] is True


async def test_canal_stt_sim_is_deterministic_and_splits_email():
    canal = CanalSttSim(p_corte_email=1.0, p_homofono=1.0)
    partes = await canal.aplicar("Es luciafernandez arroba gmail punto com, señor Gómez.", random.Random(1))
    assert len(partes) == 2 and partes[1].startswith("arroba ") and "gomes" in partes[1]
    assert partes == await canal.aplicar("Es luciafernandez arroba gmail punto com, señor Gómez.", random.Random(1))
