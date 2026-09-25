import re
import unicodedata
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from .models import ConversationState, FieldSpec, Outcome, Workflow

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
# Un email dictado llega como se dice ("juan punto perez arroba gmail punto com").
SPOKEN_EMAIL = [
    (r"\bguion bajo\b", "_"), (r"\bguion medio\b", "-"), (r"\bguion\b", "-"),
    (r"\barroba\b", "@"), (r"\bpunto\b", "."),
]
EMAIL_SEARCH = re.compile(r"[a-z0-9_+-]+(?:\.[a-z0-9_+-]+)*@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}")


@cache
def load_workflow(workflow_id: str) -> Workflow:
    return Workflow.model_validate(workflow_data(workflow_id))


def workflow_data(workflow_id: str) -> dict:
    """El YAML como dict. Con extends toma el workflow base y pisa las claves
    de primer nivel que define (ej. el mismo agente con otro engine)."""
    path = WORKFLOWS_DIR / f"{workflow_id}.yml"
    if not re.fullmatch(r"[a-z0-9_]+", workflow_id) or not path.exists():
        raise KeyError(workflow_id)
    data = yaml.safe_load(path.read_text())
    if base := data.pop("extends", None):
        data = {**workflow_data(base), **data}
    return data


def workflow_ids() -> list[str]:
    return sorted(p.stem for p in WORKFLOWS_DIR.glob("*.yml"))


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
    if spec.type == "choice":
        option = plain(str(value))
        return next((o for o in spec.options or [] if plain(o) == option), None)
    text = str(value).strip()
    return text or None


def normalize_email(value: str) -> str | None:
    """Email escrito o dictado -> direccion, o None. Del texto dictado se queda
    con la direccion: "escribime a juan arroba acme punto com" -> juan@acme.com."""
    text = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    for spoken, written in SPOKEN_EMAIL:
        text = re.sub(spoken, f" {written} ", text)
    text = re.sub(r"\s*([@._-])\s*", r"\1", text.strip())
    match = EMAIL_SEARCH.search(text)
    return match.group(0) if match and EMAIL_RE.match(match.group(0)) else None


def plain(text: str) -> str:
    """Solo letras y numeros, sin tildes ni mayusculas."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode())


def normalize_phone(value: str) -> str | None:
    """Telefono con 8 a 15 digitos (el LLM pasa a cifras lo dictado en palabras)."""
    digits = re.sub(r"\D", "", value)
    if not 8 <= len(digits) <= 15:
        return None
    return ("+" if value.strip().startswith("+") else "") + digits


def said(value: str, user_message: str) -> bool:
    """El email sale de lo que dijo el usuario: su parte antes de la @ esta en
    el mensaje (comparando solo letras y numeros, asi vale tambien deletreado).
    Con "Escribime a" cortado, el LLM completaba con el correo de la empresa."""
    return plain(value.split("@")[0]) in plain(user_message)


def check_updates(workflow: Workflow, updates: dict[str, Any], user_message: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(validos, rechazados). Los campos inexistentes se descartan sin mas; los
    rechazados son valores de campos reales con tipo invalido (o un email que el
    usuario no dijo), para avisarle al LLM."""
    valid, rejected = {}, {}
    for name, value in updates.items():
        spec = workflow.fields.get(name)
        if spec is None or value is None:
            continue
        coerced = coerce_value(spec, value)
        if (coerced is not None and spec.type in ("email", "email_or_phone") and "@" in str(coerced)
                and user_message is not None and not said(coerced, user_message)):
            coerced = None
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


def outcome_for(workflow: Workflow, state: ConversationState) -> Outcome:
    """El primer resultado cuyas condiciones se cumplen; el ultimo, sin when, es el default."""
    outcome = next(o for o in workflow.completion.outcomes
                   if all(state.fields.get(k) == v for k, v in o.when.items()))
    if outcome.goal and not is_workflow_complete(workflow, state):
        return INCOMPLETE
    return outcome
