"""Prompt del motor (app/llm/prompt.py): el canal y el prompt del agente tal cual, con sus {{variables}}; sin
reglas de comportamiento ni bloques de la plataforma. Se renderiza una vez, en el primer turno."""
import datetime

import pytest

from app.agents.templates import load_reference
from app.config import settings
from app.conversation import variables
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, ConversationState, Message
from app.llm.prompt import (
    CHANNEL,
    build_extraction_prompt,
    build_system_prompt,
    build_turn_messages,
)

from .helpers import FakeLLM


def state_for(wf, **progress) -> ConversationState:
    state = ConversationState(conversation_id="c", agent_id=wf.id, fields={n: None for n in wf.analysis_fields})
    for k, v in progress.items():
        setattr(state.progress, k, v)
    return state


def with_prompt(text: str, **extra):
    wf = load_reference("sales_discovery").model_copy(deep=True)    # la de referencia esta en cache
    wf.prompt = text
    for k, v in extra.items():
        setattr(wf, k, v)
    return wf


def test_system_prompt_is_the_channel_and_the_prompt():
    wf = load_reference("sales_discovery")
    system = build_system_prompt(wf)
    assert system == f"{CHANNEL['voice']}\n\n{wf.prompt.strip()}"
    # Sin marcas ni reglas de la plataforma: terminar y derivar son herramientas.
    for gone in ("[FIN]", "[CORTAR]", "[DERIVAR", "PASAR LA LLAMADA", "DATOS DEL CONTACTO", "MOTIVO DEL LLAMADO",
                 "DATOS YA CONOCIDOS", "APERTURA"):
        assert gone not in system


def test_without_state_the_prompt_is_not_rendered():
    """La vista previa del editor (POST /agents/prompt) muestra las variables tal cual."""
    wf = with_prompt("Hoy es {{today}}. Debe {{deuda}}.")
    assert build_system_prompt(wf).endswith("Hoy es {{today}}. Debe {{deuda}}.")


def test_variables_are_rendered_and_missing_ones_are_empty(monkeypatch):
    monkeypatch.setattr(settings, "agent_timezone", "America/Argentina/Cordoba")
    wf = with_prompt("Hoy es {{today}}. Hola {{nombre}}, debés {{deuda}}. Te llamo al {{call.phone}}.")
    state = state_for(wf, started_at="2026-10-26T15:30:00-03:00", call={"phone": "+5493515551234"})
    variables.merge(state, {"nombre": "Ana"}, "contact")
    system = build_system_prompt(wf, "voice", state)
    assert system.endswith("Hoy es lunes 2026-10-26. Hola Ana, debés. Te llamo al +5493515551234.")


def test_hidden_variables_and_secrets_never_reach_the_prompt():
    wf = with_prompt("Token {{token_crm}} y {{nombre}}.")
    state = state_for(wf)
    variables.merge(state, {"nombre": "Ana", "token_crm": "xyz"}, "pre_call:ficha", hidden={"token_crm"})
    system = build_system_prompt(wf, "voice", state)
    assert "xyz" not in system and system.endswith("Token y Ana.")
    extraction = build_extraction_prompt(wf, state)
    assert "xyz" not in extraction and '"nombre": "Ana"' in extraction


def test_a_value_with_braces_is_not_rendered_again():
    wf = with_prompt("Dijo: {{nota}}")
    state = state_for(wf)
    variables.merge(state, {"nota": "{{call.phone}} {{secrets.X}}", "x": "1"}, "request")
    assert build_system_prompt(wf, "voice", state).endswith("Dijo: {{call.phone}} {{secrets.X}}")


def test_extraction_prompt_has_instructions_fields_and_variables():
    wf = load_reference("sales_discovery").model_copy(deep=True)
    wf.analysis.instructions = "Mirá solo lo que dijo {{nombre}}."
    state = state_for(wf)
    variables.merge(state, {"nombre": "Ana"}, "request")
    text = build_extraction_prompt(wf, state)
    assert text.startswith(f"AGENTE: {wf.agent.name}.")
    assert "INSTRUCCIONES:\nMirá solo lo que dijo Ana." in text and "CAMPOS:" in text and "VARIABLES:" in text
    assert "OBJETIVO" not in text
    # Los campos en el orden del JSON.
    assert text.index("contact_name") < text.index("wants_demo")


async def test_the_prompt_is_rendered_once_and_does_not_change(store, monkeypatch):
    """Primer turno: queda en progress.system_prompt. Lo que asigne una herramienta despues o el paso del minuto
    no lo cambian (prefix cache)."""
    llm = FakeLLM(AgentTurn(assistant_message="¿Empresa?"), AgentTurn(assistant_message="¿Rubro?"))
    engine = ConversationEngine(llm, store)
    wf = load_reference("sales_discovery")
    monkeypatch.setattr(wf, "prompt", wf.prompt + "\nAhora: {{now}}. Deuda: {{deuda}}.")
    seen = []
    real = llm.converse

    async def converse(workflow, state, user_message, on_message=None, tools=None):
        seen.append(build_turn_messages(workflow, state, user_message)[0]["content"])
        return await real(workflow, state, user_message, on_message, tools)
    llm.converse = converse
    state, _ = engine.start_conversation("sales_discovery")
    await engine.process_turn(state.conversation_id, "Hola")
    after = store.get(state.conversation_id)
    assert after.progress.system_prompt == seen[0] and "Deuda:." in seen[0]
    variables.merge(after, {"deuda": "125000"}, "tool:consultar_deuda")
    after.progress.started_at = (datetime.datetime.fromisoformat(after.progress.started_at)
                                 - datetime.timedelta(minutes=5)).isoformat()
    store.save(after)
    await engine.process_turn(state.conversation_id, "Acme")
    assert seen[1] == seen[0]


def test_whatsapp_has_no_opening_guide():
    wf = load_reference("sales_discovery")
    state = state_for(wf)
    state.channel = "whatsapp"
    system = build_system_prompt(wf, "whatsapp", state)
    assert "APERTURA" not in system and wf.first_message not in system


def test_classic_history_derivacion_con_tool_call():
    """La respuesta que derivo va con su transfer_call y el resultado; el aviso posterior, aparte."""
    from app.llm.prompt import classic_history
    out = classic_history([Message(role="user", text="pasame con ventas"),
                           Message(role="assistant", text="Te paso con Ventas.", handoff="Ventas"),
                           Message(role="assistant", text="No pude comunicarte con Ventas.")], False)
    assert [m["role"] for m in out] == ["user", "assistant", "tool", "assistant"]
    call = out[1]["tool_calls"][0]
    assert call["function"]["name"] == "transfer_call" and '"Ventas"' in call["function"]["arguments"]
    assert out[2]["tool_call_id"] == call["id"]


@pytest.mark.parametrize("text", ["Clave {{secrets.API}}", "Dato {{fields.email}}", "Resumen {{ call.summary }}"])
def test_tool_only_variables_are_rejected_in_the_prompt(text):
    from pydantic import ValidationError

    from app.conversation.models import Workflow
    base = {"id": "x", "version": 1, "agent": {"name": "A", "language": "es"}}
    with pytest.raises(ValidationError, match="prompt: "):
        Workflow.model_validate({**base, "prompt": text})
    with pytest.raises(ValidationError, match="first_message: "):
        Workflow.model_validate({**base, "first_message": text})
    with pytest.raises(ValidationError, match="analysis.instructions: "):
        Workflow.model_validate({**base, "analysis": {"instructions": text}})
