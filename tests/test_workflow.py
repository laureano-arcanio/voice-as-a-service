import pytest
from pydantic import ValidationError

from app.agents.templates import (
    load_reference,
    reference_ids,
    template_data,
    template_ids,
)
from app.conversation.models import AgentInfo, ConversationState, Workflow
from app.conversation.workflow import (
    check_updates,
    outcome_for,
    validate_updates,
)


def state_with(workflow, **fields):
    values = {name: None for name in workflow.analysis_fields}
    values.update(fields)
    return ConversationState(conversation_id="c", agent_id=workflow.id, fields=values)


def test_outcome_is_the_first_whose_when_holds(workflow):
    assert outcome_for(workflow, state_with(workflow, wants_demo=True)).id == "demo"
    assert outcome_for(workflow, state_with(workflow, wants_demo=False)).id == workflow.outcomes[-1].id


def test_without_outcomes_there_is_no_outcome():
    w = Workflow.model_validate({"id": "x", "version": 1, "agent": {"name": "A", "language": "es"},
                                 "prompt": "# Identidad\nSos A.", "analysis": {"fields": [
                                     {"name": "nombre", "description": "Nombre"}]}})
    assert outcome_for(w, state_with(w, nombre="Ana")) is None
    assert outcome_for(Workflow.model_validate({"id": "y", "version": 1, "agent": {"name": "A", "language": "es"}}),
                       state_with(w)) is None


def test_unknown_fields_are_ignored(workflow):
    assert validate_updates(workflow, {"random_field": "foo", "contact_name": "Juan"}) == {"contact_name": "Juan"}


def test_types_are_validated(workflow):
    updates = {"employee_count": "bastantes", "wants_demo": "quizás", "email": "juan arroba acme", "company_name": " "}
    assert validate_updates(workflow, updates) == {}


def test_types_are_coerced(workflow):
    updates = {"employee_count": "80", "wants_demo": "true", "email": " Juan@Acme.com "}
    assert validate_updates(workflow, updates) == {"employee_count": 80, "wants_demo": True, "email": "juan@acme.com"}


def test_emails_are_validated_by_format_only(workflow):
    """Solo el formato: un email dictado ("arroba", "punto") no se convierte; se guarda lo que extrae el modelo."""
    assert validate_updates(workflow, {"email": " Laureano@Gmail.com "}) == {"email": "laureano@gmail.com"}
    assert validate_updates(workflow, {"email": "juan.perez@acme.com.ar"}) == {"email": "juan.perez@acme.com.ar"}
    assert validate_updates(workflow, {"email": "Laureano arroba gmail punto com"}) == {}


def test_invalid_values_are_reported(workflow):
    valid, rejected = check_updates(workflow, {"email": "Escribime a", "random_field": "x", "contact_name": "Juan"})
    assert valid == {"contact_name": "Juan"}
    assert rejected == {"email": "Escribime a"}


def test_email_is_not_checked_against_the_user_message(workflow):
    """check_updates no recibe la conversacion: un email valido se guarda aunque el usuario no lo haya dicho."""
    valid, rejected = check_updates(workflow, {"email": "info@browix.com"})
    assert valid == {"email": "info@browix.com"} and rejected == {}


def test_every_workflow_has_a_voice():
    for rid in reference_ids():
        assert load_reference(rid).agent.voice, rid
    for tid in template_ids():
        assert template_data(tid)["agent"]["voice"], tid


@pytest.mark.parametrize("voice", ["default", " ", "Default"])
def test_voice_rejects_default_and_empty(voice):
    # "default" mata el engine de vllm-tts (docs/TTS_FINETUNE.md, Trampas 8).
    with pytest.raises(ValidationError):
        AgentInfo(name="Sofía", language="es-AR", voice=voice)


def test_voice_is_optional_and_lowercased():
    assert AgentInfo(name="A", language="es-AR").voice is None
    assert AgentInfo(name="A", language="es-AR", voice=" Martin ").voice == "martin"


def test_wa_session_minutes_is_optional_and_defaults_to_none(workflow):
    # None: en WhatsApp rige el default global (WA_SESSION_HOURS, 1440 min = 24 hs).
    assert workflow.wa_session_minutes is None


@pytest.mark.parametrize("minutes", [0, -1])
def test_wa_session_minutes_rejects_non_positive(minutes):
    data = load_reference("sales_discovery").model_dump(mode="json")
    with pytest.raises(ValidationError, match="wa_session_minutes"):
        Workflow.model_validate({**data, "wa_session_minutes": minutes})


def test_wa_session_minutes_accepts_a_custom_window():
    data = load_reference("sales_discovery").model_dump(mode="json")
    assert Workflow.model_validate({**data, "wa_session_minutes": 30}).wa_session_minutes == 30


def _def(**extra):
    """Definicion minima que valida, con lo que cambia en cada test."""
    return {"id": "x", "version": 1, "agent": {"name": "A", "language": "es"}, **extra}


def test_turn_attention_is_none_without_the_block(workflow):
    # Las definiciones existentes no tienen el bloque: queda apagado.
    assert workflow.turn_attention is None


def test_turn_attention_missing_fields_get_the_defaults():
    assert Workflow.model_validate(_def(turn_attention={})).turn_attention.enabled is False
    # Defaults del plan (2.1): 7 s el primer aviso, 2 avisos, cierre a los 30 s.
    ta = Workflow.model_validate(_def(turn_attention={"enabled": True})).turn_attention
    assert ta.model_dump() == {"enabled": True, "reminder_after_ms": 7000, "reminder_max": 2,
                               "reminder_gap_ms": 7000, "end_after_ms": 30000, "stt_retry": True,
                               "transcription_timeout_ms": 3000, "repeat_last_reply": True,
                               "reminder_text": "", "end_text": "", "on_end": "hang_up",
                               "on_end_area_id": ""}


@pytest.mark.parametrize("field, value", [
    ("reminder_after_ms", 2999), ("reminder_after_ms", 30001),
    ("reminder_max", -1), ("reminder_max", 6),
    ("reminder_gap_ms", 2999), ("reminder_gap_ms", 30001),
    ("end_after_ms", 14999), ("end_after_ms", 120001),
    ("transcription_timeout_ms", 999), ("transcription_timeout_ms", 10001),
])
def test_turn_attention_rejects_out_of_range(field, value):
    with pytest.raises(ValidationError, match=f"turn_attention.{field}"):
        Workflow.model_validate(_def(turn_attention={field: value}))


def test_turn_attention_transfer_needs_handoff_areas():
    with pytest.raises(ValidationError, match="turn_attention.on_end"):
        Workflow.model_validate(_def(turn_attention={"enabled": True, "on_end": "transfer"}))


def test_turn_attention_transfer_area_has_to_be_in_handoff():
    areas = {"areas": [{"area_id": "admin", "when": "administracion"}]}
    with pytest.raises(ValidationError, match="turn_attention.on_end_area_id"):
        Workflow.model_validate(_def(handoff=areas, turn_attention={
            "enabled": True, "on_end": "transfer", "on_end_area_id": "ventas"}))


def test_turn_attention_transfer_to_an_area_of_handoff():
    areas = {"areas": [{"area_id": "admin", "when": "administracion"}]}
    ta = Workflow.model_validate(_def(handoff=areas, turn_attention={
        "enabled": True, "on_end": "transfer", "on_end_area_id": "admin"})).turn_attention
    assert (ta.on_end, ta.on_end_area_id) == ("transfer", "admin")


def test_turn_attention_rejects_end_before_the_first_reminder():
    with pytest.raises(ValidationError, match="turn_attention.end_after_ms"):
        Workflow.model_validate(_def(turn_attention={
            "enabled": True, "reminder_after_ms": 30000, "end_after_ms": 15000}))


def test_turn_attention_without_reminders_closes_without_warning():
    # reminder_max=0: sin avisos, el cierre puede ser antes de reminder_after_ms.
    ta = Workflow.model_validate(_def(turn_attention={
        "enabled": True, "reminder_max": 0, "reminder_after_ms": 30000,
        "end_after_ms": 15000})).turn_attention
    assert ta.reminder_max == 0 and ta.end_after_ms < ta.reminder_after_ms


@pytest.mark.parametrize("field", ["reminder_text", "end_text"])
def test_turn_attention_texts_are_capped_at_300(field):
    with pytest.raises(ValidationError, match=f"turn_attention.{field}"):
        Workflow.model_validate(_def(turn_attention={"enabled": True, field: "x" * 301}))
