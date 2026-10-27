import re
import unicodedata
from typing import Any

from .models import ConversationState, FieldSpec, Outcome, Workflow

EMAIL_RE = re.compile(r"^[a-z0-9_+-]+(?:\.[a-z0-9_+-]+)*@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$")


def is_required(spec: FieldSpec, fields: dict[str, Any]) -> bool:
    if spec.required_if:
        return all(fields.get(k) == v for k, v in spec.required_if.items())
    return spec.required


def pending_fields(workflow: Workflow, state: ConversationState) -> list[str]:
    """Obligatorios sin valor, por prioridad."""
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
        return normalize_email(str(value))
    if spec.type == "email_or_phone":
        return normalize_email(str(value)) or normalize_phone(str(value))
    if spec.type == "phone":
        return normalize_phone(str(value))
    if spec.type == "choice":
        option = plain(str(value))
        return next((o for o in spec.options or [] if plain(o) == option), None)
    text = str(value).strip()
    return text or None


def normalize_email(value: str) -> str | None:
    """Una direccion de email valida (en minusculas), o None."""
    text = value.strip().lower()
    return text if EMAIL_RE.match(text) else None


def plain(text: str) -> str:
    """Solo letras y numeros, sin tildes ni mayusculas."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode())


def normalize_phone(value: str) -> str | None:
    """Telefono con 8 a 15 digitos (los separadores no cuentan)."""
    digits = re.sub(r"\D", "", value)
    if not 8 <= len(digits) <= 15:
        return None
    return ("+" if value.strip().startswith("+") else "") + digits


def check_updates(workflow: Workflow, updates: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(validos, rechazados). Los campos inexistentes se descartan sin mas; los rechazados son valores de campos
    reales con tipo invalido (quedan en progress.rejected, para el panel)."""
    valid, rejected = {}, {}
    for name, value in updates.items():
        spec = workflow.fields.get(name)
        if spec is None or value is None:
            continue
        coerced = coerce_value(spec, value)
        if coerced is None:
            rejected[name] = value
        else:
            valid[name] = coerced
    return valid, rejected


def validate_updates(workflow: Workflow, updates: dict[str, Any]) -> dict[str, Any]:
    return check_updates(workflow, updates)[0]


# Cuando el resultado seria el objetivo pero faltan datos obligatorios. En la
# llamada 80ac0e22 pidio el link y corto sin actividad ni contacto, y contaba como exito.
INCOMPLETE = Outcome(id="incompleta", label="Incompleta", message="")

# El agente corto porque la conversacion no tenia que ver con su objetivo (broma, burla, acoso,
# numero equivocado; llamada 07381a4d): resultado propio, no el default del workflow, y
# ended_reason OFF_TOPIC_REASON en la llamada.
OFF_TOPIC = Outcome(id="fuera_de_tema", label="Fuera de tema", message="")
OFF_TOPIC_REASON = "off_topic"


def outcome_for(workflow: Workflow, state: ConversationState) -> Outcome:
    """El primer resultado cuyas condiciones se cumplen; el ultimo, sin when, es el default."""
    outcome = next(o for o in workflow.completion.outcomes
                   if all(state.fields.get(k) == v for k, v in o.when.items()))
    if outcome.goal and not is_workflow_complete(workflow, state):
        return INCOMPLETE
    return outcome
