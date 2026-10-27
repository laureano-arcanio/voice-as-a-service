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
    is_workflow_complete,
    pending_fields,
    validate_updates,
)

from .helpers import BASE


def state_with(workflow, **fields):
    values = {name: None for name in workflow.fields}
    values.update(fields)
    return ConversationState(conversation_id="c", agent_id=workflow.id, fields=values)


def test_pending_follows_priority(workflow):
    state = state_with(workflow, company_name="Acme")
    assert pending_fields(workflow, state)[:3] == ["contact_name", "company_activity", "employee_count"]


def test_required_if_no_demo_completes_without_email(workflow):
    assert is_workflow_complete(workflow, state_with(workflow, **BASE, wants_demo=False))


def test_required_if_demo_requires_email(workflow):
    state = state_with(workflow, **BASE, wants_demo=True)
    assert pending_fields(workflow, state) == ["email"]
    state.fields["email"] = "juan@acme.com"
    assert is_workflow_complete(workflow, state)


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
        AgentInfo(name="Sofía", role="asesora", language="es-AR", voice=voice)


def test_voice_is_optional_and_lowercased():
    assert AgentInfo(name="A", role="r", language="es-AR").voice is None
    assert AgentInfo(name="A", role="r", language="es-AR", voice=" Martin ").voice == "martin"


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
