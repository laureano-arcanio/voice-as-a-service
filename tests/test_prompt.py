"""Prompt del motor (app/llm/prompt.py): solo la definicion del agente y el protocolo. Variables {{today}} y
{{now}} en las reglas, el objetivo y la base de conocimiento; sin reglas de comportamiento en el codigo."""
import datetime
from types import SimpleNamespace

import pytest

from app.agents.templates import load_reference
from app.config import settings
from app.conversation.models import ConversationState
from app.llm import prompt
from app.llm.prompt import build_system_prompt, render_variables


@pytest.fixture
def frozen(monkeypatch):
    """Lunes 26-oct-2026 15:30 en la zona que pida render_variables; guarda la zona pedida."""
    seen = []

    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            seen.append(tz)
            return datetime.datetime(2026, 10, 26, 15, 30, tzinfo=tz)

    monkeypatch.setattr(prompt, "datetime", SimpleNamespace(datetime=Frozen))
    return seen


def test_render_variables(frozen, monkeypatch):
    monkeypatch.setattr(settings, "agent_timezone", "America/Argentina/Cordoba")
    assert render_variables("Hoy es {{today}}.") == "Hoy es lunes 2026-10-26."
    assert render_variables("Ahora: {{now}}") == "Ahora: lunes 2026-10-26 15:30"
    assert str(frozen[-1]) == "America/Argentina/Cordoba"


def test_render_variables_without_variables_is_the_same_text(frozen):
    text = "Sin variables {ni llaves sueltas}."
    assert render_variables(text) is text and frozen == []
    assert render_variables("{{otra}} queda") == "{{otra}} queda"


def test_variables_in_rules_objective_and_knowledge(frozen):
    wf = load_reference("sales_discovery").model_copy(deep=True)
    wf.conversation.rules = [*wf.conversation.rules, "Si preguntan la fecha, hoy es {{today}}."]
    wf.objective.description = "Agendar desde {{today}}."
    wf.knowledge = "Horario vigente al {{now}}."
    system = build_system_prompt(wf)
    assert "Si preguntan la fecha, hoy es lunes 2026-10-26." in system
    assert "Agendar desde lunes 2026-10-26." in system
    assert "Horario vigente al lunes 2026-10-26 15:30." in system
    assert "{{" not in system


def test_the_date_is_not_injected_without_variables(frozen):
    """La fecha no se inyecta: solo esta si el agente la pide con una variable."""
    wf = load_reference("berlin_signup")
    system = build_system_prompt(wf)
    assert "2026-10-26" not in system and frozen == []


def test_system_prompt_has_only_the_definition():
    wf = load_reference("sales_discovery")
    system = build_system_prompt(wf)
    assert system.startswith(f"Sos {wf.agent.name}, {wf.agent.role}.")
    assert all(rule in system for rule in wf.conversation.rules)
    for section in ("OBJETIVO:", "DATOS A OBTENER", "REGLAS:", "BASE DE CONOCIMIENTO:", "CIERRES"):
        assert section in system
    # Sin marcas ni reglas de la plataforma: terminar y derivar son herramientas.
    for gone in ("[FIN]", "[CORTAR]", "[DERIVAR", "PASAR LA LLAMADA"):
        assert gone not in system


def test_agent_without_fields_has_no_data_section():
    wf = load_reference("sales_discovery").model_copy(deep=True)
    wf.fields = {}
    wf.completion.outcomes = [o for o in wf.completion.outcomes if not o.when]
    assert "DATOS A OBTENER" not in build_system_prompt(wf)


def whatsapp_state(guide=None):
    state = ConversationState(conversation_id="c", agent_id="a", channel="whatsapp", fields={})
    state.progress.opening_guide = guide
    return state


def test_whatsapp_guide_uses_the_rendered_opening():
    wf = load_reference("sales_discovery")
    system = build_system_prompt(wf, "whatsapp", whatsapp_state("Hola María, soy Sofía."))
    assert "Hola María, soy Sofía." in system and wf.conversation.opening not in system


def test_whatsapp_without_pre_call_prompt_is_the_same():
    wf = load_reference("sales_discovery")
    system = build_system_prompt(wf, "whatsapp", whatsapp_state())
    assert system == build_system_prompt(wf, "whatsapp") and wf.conversation.opening in system
    # En voz la apertura no va al prompt, tenga o no guia.
    assert "APERTURA" not in build_system_prompt(wf, "voice", whatsapp_state("Hola"))


def test_classic_history_derivacion_con_tool_call():
    """La respuesta que derivo va con su transfer_call y el resultado; el aviso posterior, aparte."""
    from app.conversation.models import Message
    from app.llm.prompt import classic_history
    out = classic_history([Message(role="user", text="pasame con ventas"),
                           Message(role="assistant", text="Te paso con Ventas.", handoff="Ventas"),
                           Message(role="assistant", text="No pude comunicarte con Ventas.")], False)
    assert [m["role"] for m in out] == ["user", "assistant", "tool", "assistant"]
    call = out[1]["tool_calls"][0]
    assert call["function"]["name"] == "transfer_call" and '"Ventas"' in call["function"]["arguments"]
    assert out[2]["tool_call_id"] == call["id"]
