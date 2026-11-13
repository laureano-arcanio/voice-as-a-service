"""Conversion de definiciones viejas (app/conversation/legacy.py): las 18 del repo (copias en tests/fixtures/legacy/,
como estaban antes de reescribirlas) convierten, validan y llevan cada seccion vieja al prompt."""
import copy
import json
from pathlib import Path

import pytest

from app.conversation import legacy
from app.conversation.models import Workflow

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "legacy").glob("*.json"))


def test_there_are_the_18_definitions():
    assert len(FIXTURES) == 18


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_converts_and_validates_with_every_old_section(path):
    old = json.loads(path.read_text(encoding="utf-8"))
    before = copy.deepcopy(old)
    new = legacy.upgrade(old)
    assert old == before                                   # puro: no toca la entrada
    assert not set(legacy.OLD_KEYS) & set(new) and "role" not in new["agent"]
    w = Workflow.model_validate({**new, "id": "x", "version": 1})
    prompt = w.prompt
    agent = old["agent"]
    assert prompt.startswith(f"# Identidad\nSos {agent['name']}, {' '.join(agent['role'].split())}.")
    assert old["objective"]["description"].strip() in prompt
    for rule in old["conversation"].get("rules") or []:
        assert rule.strip() in prompt
    if old.get("knowledge", "").strip():
        assert old["knowledge"].strip() in prompt
    for name, spec in old["fields"].items():
        assert f"- {name} (" in prompt
        if spec.get("question", "").strip():
            assert " ".join(spec["question"].split()) in prompt
    for o in old["completion"]["outcomes"]:
        assert " ".join(o["message"].split()) in prompt
    for title in ("# Objetivo", "# Datos a pedir", "# Cómo conversar", "# Cierres"):
        assert title in prompt
    # El primer mensaje, la apertura; el analisis, los campos por prioridad y los resultados sin mensaje.
    assert w.first_message == old["conversation"]["opening"]
    by_priority = [n for n, _ in sorted(old["fields"].items(), key=lambda kv: kv[1]["priority"])]
    assert list(w.analysis_fields) == by_priority
    assert all(spec.type != "digits" for spec in w.analysis_fields.values())
    assert [o.id for o in w.outcomes] == [o["id"] for o in old["completion"]["outcomes"]]
    assert w.analysis.summary is True


def test_opening_flags_and_digits():
    old = json.loads(FIXTURES[0].read_text(encoding="utf-8"))
    old["conversation"] |= {"opening_audio": True, "opening_delay_ms": 800}
    name = next(iter(old["fields"]))
    old["fields"][name]["type"] = "digits"
    new = legacy.upgrade(old)
    assert new["first_message_audio"] is True and new["first_message_delay_ms"] == 800
    assert next(f for f in new["analysis"]["fields"] if f["name"] == name)["type"] == "string"


def test_fields_become_a_list_by_priority_and_ties_keep_the_input_order():
    old = json.loads(FIXTURES[0].read_text(encoding="utf-8"))
    old["fields"] = {"c": {"priority": 20, "description": "c", "question": ""},
                     "b": {"priority": 10, "description": "b", "question": ""},
                     "a": {"priority": 20, "description": "a", "question": ""}}
    old["completion"]["outcomes"] = [{"id": "fin", "label": "Fin", "message": "Chau."}]
    fields = legacy.upgrade(old)["analysis"]["fields"]
    assert isinstance(fields, list) and [f["name"] for f in fields] == ["b", "c", "a"]


def test_the_current_form_passes_unchanged():
    current = {"agent": {"name": "A", "language": "es"}, "prompt": "# Identidad\nSos A.", "conversation": {}}
    assert legacy.upgrade(current) is current
