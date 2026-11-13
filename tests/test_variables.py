"""Variables dinamicas de la conversacion (app/conversation/variables.py): fuentes y su precedencia, las del sistema,
validacion de nombres y de la definicion, y el analisis (sin analysis no hay extraccion)."""
import json

import pytest
from pydantic import ValidationError

from app.agents.templates import blank_definition, objective_of, prompt_objective
from app.conversation import variables
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, ConversationState, Workflow

from .helpers import FakeLLM
from .test_api import V1, admin, make_client  # noqa: F401  (admin: fixture)


def new_state() -> ConversationState:
    return ConversationState(conversation_id="c-1", agent_id="a", fields={})


def workflow(**extra) -> Workflow:
    return Workflow.model_validate({"id": "ventas", "version": 3, "agent": {"name": "Sofía", "language": "es-AR"},
                                    "prompt": "# Identidad\nSos Sofía.", **extra})


def test_precedence_default_contact_request_pre_call_tool():
    state = new_state()
    wf = workflow(variables=[{"name": "deuda", "default": "0"}, {"name": "plan", "default": "base"}])
    variables.start(state, wf, {"contact": {"Deuda": "100", "nombre": "Ana"}, "request": {"motivo": "Pidió presupuesto"}})
    p = state.progress
    assert p.variables == {"deuda": "100", "plan": "base", "nombre": "Ana", "motivo": "Pidió presupuesto"}
    assert p.variable_sources == {"deuda": "contact", "plan": "default", "nombre": "contact", "motivo": "request"}
    variables.merge(state, {"deuda": "200"}, "request")
    variables.merge(state, {"deuda": "300", "nombre": "María"}, "pre_call:consultar_deuda")
    # Una fuente de menor prioridad no pisa a una mayor.
    variables.merge(state, {"deuda": "1", "nombre": "X"}, "contact")
    variables.merge(state, {"deuda": "2"}, "request")
    assert (p.variables["deuda"], p.variable_sources["deuda"]) == ("300", "pre_call:consultar_deuda")
    assert p.variables["nombre"] == "María"
    # Una herramienta en la conversacion siempre pisa, tambien a otra herramienta.
    variables.merge(state, {"deuda": "400"}, "tool:recalcular")
    variables.merge(state, {"deuda": "500"}, "tool:otra")
    assert (p.variables["deuda"], p.variable_sources["deuda"]) == ("500", "tool:otra")


def test_system_variables_cannot_be_overwritten():
    """Un contacto con columna today, channel o call.phone no cambia nada: las del sistema no se guardan."""
    state = new_state()
    variables.start(state, workflow(), {"contact": {"today": "ayer", "channel": "fax", "call.phone": "1", "Now": "x"}},
                    call={"phone": "+54 9 11 5555-0000", "id": "pisado", "otra": "x"})
    assert state.progress.call == {"id": "c-1", "phone": "+5491155550000"}
    variables.merge(state, {"agent.slug": "otro", "channel": "fax"}, "tool:x")
    # La columna "call.phone" del contacto se normaliza a call_phone: una variable de usuario, no la del sistema.
    assert state.progress.variables == {"call_phone": "1"}
    system = variables.system_values(state, workflow())
    assert system["channel"] == "voice" and system["call.phone"] == "+5491155550000"
    assert system["agent.slug"] == "ventas" and system["call.id"] == "c-1"
    assert variables.render("{{channel}} {{call.phone}} {{agent.slug}} v{{agent.version}}", state, workflow()) == \
        "voice +5491155550000 ventas v1"


@pytest.mark.parametrize("name, ok", [("call_x", True), ("deuda_total", True), ("call.x", False), ("today", False),
                                      ("channel", False), ("Deuda", False), ("1x", False), ("a" * 65, False)])
def test_names(name, ok):
    assert (variables.name_error(name) is None) is ok


def test_request_values_are_checked():
    clean, errors = variables.check_request({"motivo": "x", "vacio": None, "obj": {"a": 1}, "today": "x",
                                             "largo": "x" * (variables.MAX_VALUE_CHARS + 1)})
    assert clean == {"motivo": "x"}
    assert {e["path"] for e in errors} == {"variables.obj", "variables.today", "variables.largo"}
    _, errors = variables.check_request({f"v{i}": i for i in range(variables.MAX_VARIABLES + 1)})
    assert errors == [{"path": "variables", "message": f"hasta {variables.MAX_VARIABLES} variables"}]


def test_the_space_has_a_cap_and_flat_values():
    state = new_state()
    variables.merge(state, {f"v{i}": i for i in range(variables.MAX_VARIABLES + 5)}, "request")
    assert len(state.progress.variables) == variables.MAX_VARIABLES
    other = new_state()
    variables.merge(other, {"ficha": {"a": 1}, "texto": "x" * 3000}, "tool:ficha")
    assert other.progress.variables["ficha"] == '{"a": 1}'
    assert len(other.progress.variables["texto"]) == variables.MAX_VALUE_CHARS


def test_hidden_variables_are_tracked_and_shown_masked():
    state = new_state()
    variables.merge(state, {"token": "xyz", "nombre": "Ana"}, "pre_call:ficha", hidden={"token"})
    assert state.progress.hidden_variables == ["token"] and variables.visible(state) == {"nombre": "Ana"}
    assert variables.render("{{token}}", state) == ""
    detail = {d["name"]: d for d in variables.detail(state)}
    assert detail["token"] == {"name": "token", "value": "•••", "source": "pre_call:ficha", "hidden": True}
    assert detail["call.id"]["source"] == "system"


def test_definition_variables_are_validated():
    assert workflow(variables=[{"name": "deuda", "default": 5, "description": "Lo que debe"}]
                    ).variable_specs["deuda"].default == 5
    for bad in ([{"name": "today"}], [{"name": "call.x"}], [{"name": "Deuda"}], [{"name": "d", "default": "x" * 2001}],
                [{"name": "d", "description": "x" * 301}], [{"name": f"v{i}"} for i in range(31)],
                [{"name": "d"}, {"name": "d"}], {"d": {"default": ""}}):
        with pytest.raises(ValidationError):
            workflow(variables=bad)
    # Una {{x}} sin declarar es valida: puede venir del pre-call o de la campaña.
    assert workflow(prompt="Hola {{nombre}}", first_message="Hola {{nombre}}").prompt == "Hola {{nombre}}"


def test_lists_keep_their_order_through_json():
    """analysis.fields y variables son listas: jsonb no conserva el orden de las claves de un objeto."""
    from app.llm.client import extraction_schema

    wf = workflow(variables=[{"name": "b"}, {"name": "a"}], analysis={"fields": [
        {"name": n, "description": n} for n in ("z", "a", "m")]})
    again = Workflow.model_validate(json.loads(json.dumps(wf.model_dump(mode="json", exclude_none=True))))
    assert list(again.analysis_fields) == ["z", "a", "m"] and list(again.variable_specs) == ["b", "a"]
    assert list(extraction_schema(again)["properties"]["fields"]["properties"]) == ["z", "a", "m"]


@pytest.mark.parametrize("definition, path, message", [
    ({"variables": [{"name": "deuda"}, {"name": "deuda"}]}, "variables.1.name", "deuda repetida"),
    ({"analysis": {"fields": [{"name": "x", "description": "x"}, {"name": "x", "description": "y"}]}},
     "analysis.fields.1.name", "x repetido"),
    ({"variables": {"deuda": {"default": ""}}}, "variables", "debe ser una lista"),
    ({"analysis": {"fields": {"x": {"description": "x"}}}}, "analysis.fields", "debe ser una lista"),
])
def test_repeated_names_and_the_map_form_give_422(api, admin, definition, path, message):  # noqa: F811
    c = make_client(admin)
    body = {"agent": {"name": "A", "language": "es"}, "prompt": "# Identidad\nSos A.", **definition}
    r = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "A", "definition": body})
    assert r.status_code == 422, r.text
    error = r.json()["errors"][0]
    assert error["path"] == path and message in error["message"]


def test_detail_follows_the_declared_order():
    state = new_state()
    wf = workflow(variables=[{"name": "zeta", "default": "1"}, {"name": "alfa", "default": "2"}])
    variables.start(state, wf)
    variables.merge(state, {"otra": "x", "beta": "y"}, "request")
    names = [d["name"] for d in variables.detail(state, wf)]
    system = [v["name"] for v in variables.SYSTEM_VARIABLES if v["name"] in names]
    assert names[:4] == ["zeta", "alfa", "beta", "otra"] and names[4:] == system


def test_secrets_in_the_prompt_are_rejected_by_the_api(api, admin):  # noqa: F811
    c = make_client(admin)
    definition = {"agent": {"name": "A", "language": "es"}, "prompt": "Clave: {{secrets.API_KEY}}"}
    r = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "A", "definition": definition})
    assert r.status_code == 422 and r.json()["errors"][0]["path"] == "prompt"
    ok = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "B", "definition": {
        **definition, "prompt": "# Objetivo\nCobrar {{deuda}}.\n\n# Info\nx"}})
    assert ok.status_code == 201, ok.text
    assert ok.json()["objective"] == "Cobrar {{deuda}}."


def test_schema_has_variables_and_not_objective(api, admin):  # noqa: F811
    props = admin.get(f"{V1}/agents/schema").json()["properties"]
    assert {"prompt", "first_message", "variables", "analysis"} <= set(props)
    assert not {"objective", "conversation", "completion", "fields", "knowledge"} & set(props)


def test_blank_definition_and_objective():
    w = Workflow.model_validate({**blank_definition("Acme"), "id": "x", "version": 1})
    assert w.analysis is None and "Acme" in w.prompt and prompt_objective(w.prompt)
    assert objective_of({"objective": {"description": "Vender"}, "agent": {"name": "A", "role": "r", "language": "es"},
                         "conversation": {"opening": "Hola"}, "completion": {"outcomes": []}}) == "Vender"
    assert prompt_objective("# Identidad\nSos A.") == ""


async def test_without_analysis_there_is_no_extraction(store, monkeypatch):
    llm = FakeLLM(AgentTurn(assistant_message="Chau.", status="completed"), extractions=[{"x": 1}])
    engine = ConversationEngine(llm, store)
    bare = workflow()
    monkeypatch.setattr(engine.definitions, "current", lambda agent_id, session=None: (1, bare))
    monkeypatch.setattr(engine.definitions, "get", lambda agent_id, version, session=None: bare)
    state, _ = engine.start_conversation("ventas")
    await engine.process_turn(state.conversation_id, "Hola")
    await engine.finish(state.conversation_id)
    await engine.analyze(state.conversation_id)
    after = store.get(state.conversation_id)
    assert llm.extract_calls == [] and after.progress.outcome is None and after.status == "completed"


async def test_analyze_runs_the_analysis_without_closing(store):
    """engine.analyze (post-call de WhatsApp): saca los datos y el resumen sin terminar la conversacion."""
    from app.conversation.models import Extraction

    llm = FakeLLM(AgentTurn(assistant_message="¿Empresa?"))
    engine = ConversationEngine(llm, store)

    async def extract(workflow, state):
        llm.extract_calls.append(len(state.messages))
        return Extraction(fields={"contact_name": "Juan"}, summary="Juan quiere una demo.")
    llm.extract = extract
    state, _ = engine.start_conversation("sales_discovery")
    await engine.process_turn(state.conversation_id, "Soy Juan")
    await engine.analyze(state.conversation_id)
    after = store.get(state.conversation_id)
    assert after.status == "active" and after.fields["contact_name"] == "Juan"
    assert after.progress.summary == "Juan quiere una demo." and llm.extract_calls == [3]
