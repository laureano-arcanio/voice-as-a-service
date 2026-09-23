from app.conversation.models import ConversationState
from app.conversation.workflow import is_workflow_complete, pending_fields, validate_updates

from .helpers import BASE



def state_with(workflow, **fields):
    values = {name: None for name in workflow.fields}
    values.update(fields)
    return ConversationState(conversation_id="c", workflow_id=workflow.id, fields=values)


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
