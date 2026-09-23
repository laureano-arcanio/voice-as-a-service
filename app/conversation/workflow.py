import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from .models import ConversationState, FieldSpec, Workflow

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")


@cache
def load_workflow(workflow_id: str) -> Workflow:
    path = WORKFLOWS_DIR / f"{workflow_id}.yml"
    if not re.fullmatch(r"[a-z0-9_]+", workflow_id) or not path.exists():
        raise KeyError(workflow_id)
    return Workflow.model_validate(yaml.safe_load(path.read_text()))


def is_required(spec: FieldSpec, fields: dict[str, Any]) -> bool:
    if spec.required_if:
        return all(fields.get(k) == v for k, v in spec.required_if.items())
    return spec.required


def pending_fields(workflow: Workflow, state: ConversationState) -> list[str]:
    ordered = sorted(workflow.fields.items(), key=lambda kv: kv[1].priority)
    return [name for name, spec in ordered if state.fields.get(name) is None and is_required(spec, state.fields)]


def is_workflow_complete(workflow: Workflow, state: ConversationState) -> bool:
    return not pending_fields(workflow, state)


def coerce_value(spec: FieldSpec, value: Any) -> Any:
    if value is None:
        return None
    if spec.type == "integer":
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value) if value >= 0 else None
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None
    if spec.type == "boolean":
        if isinstance(value, bool):
            return value
        return {"true": True, "false": False}.get(str(value).strip().lower())
    if spec.type == "email":
        email = str(value).strip().lower()
        return email if EMAIL_RE.match(email) else None
    text = str(value).strip()
    return text or None


def validate_updates(workflow: Workflow, updates: dict[str, Any]) -> dict[str, Any]:
    valid = {}
    for name, value in updates.items():
        spec = workflow.fields.get(name)
        if spec is None:
            continue
        coerced = coerce_value(spec, value)
        if coerced is not None:
            valid[name] = coerced
    return valid


def completion_message(workflow: Workflow, state: ConversationState) -> str:
    if state.fields.get("wants_demo"):
        return workflow.completion.message_if_demo.strip()
    return workflow.completion.message_if_no_demo.strip()
