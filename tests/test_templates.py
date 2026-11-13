"""Plantillas de la UI y agentes del eval: escritos en la forma actual (prompt, first_message, analysis)."""
import pytest

from app.agents.templates import (
    fill_template,
    load_reference,
    objective_of,
    reference_data,
    reference_ids,
    template_data,
    template_ids,
)
from app.conversation import legacy, variables
from app.conversation.models import Workflow

OLD_KEYS = ("objective", "conversation", "knowledge", "fields", "completion")
EVAL_IDS = [i for i in reference_ids() if i.startswith("eval_")]
TITLES = ("# Identidad", "# Objetivo", "# Cómo conversar", "# Información", "# Límites")


def _data(kind, name):
    return template_data(name) if kind == "template" else reference_data(name)


CASES = [("template", t) for t in template_ids()] + [("reference", r) for r in EVAL_IDS]


@pytest.mark.parametrize("kind,name", CASES)
def test_written_in_the_current_form(kind, name):
    data = _data(kind, name)
    assert not legacy.is_legacy(data) and not any(k in data for k in OLD_KEYS)
    assert "role" not in data["agent"]
    assert all(t in data["prompt"] for t in TITLES)
    assert data["first_message"] and data["analysis"]["summary"] is True
    wf = Workflow.model_validate(data)
    assert wf.analysis_fields and wf.outcomes and wf.outcomes[-1].when == {}
    assert objective_of(data)


@pytest.mark.parametrize("name", template_ids())
def test_template_fills_company_and_agent(name):
    filled = fill_template(template_data(name), "Acme", "lucas")
    text = str(filled)
    assert "[EMPRESA]" not in text and "[AGENTE]" not in text
    assert "Lucas" in filled["prompt"] and Workflow.model_validate(filled)


def test_cobranzas_names_its_variables():
    data = template_data("cobranzas")
    names = [v["name"] for v in data["variables"]]
    assert names == ["nombre", "monto", "vencimiento"]
    for name in names:
        assert variables.name_error(name) is None
        assert f"{{{{{name}}}}}" in data["prompt"]
    assert "{{nombre}}" in data["first_message"]


@pytest.mark.parametrize("name", EVAL_IDS)
def test_eval_agents_load(name):
    wf = load_reference(name)
    assert wf.external is None and wf.outcomes
