import re
import unicodedata
from typing import Any

from .models import AnalysisField, ConversationState, Outcome, Workflow

EMAIL_RE = re.compile(r"^[a-z0-9_+-]+(?:\.[a-z0-9_+-]+)*@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$")


def coerce_value(spec: AnalysisField, value: Any) -> Any:
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
        spec = workflow.analysis_fields.get(name)
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


# Resultado de las conversaciones guardadas cuando terminaban sin los datos obligatorios: ya no se asigna, se
# conserva para leerlas (reportes).
INCOMPLETE = Outcome(id="incompleta", label="Incompleta")

# El agente corto porque la conversacion no tenia que ver con su objetivo (broma, burla, acoso,
# numero equivocado; llamada 07381a4d): resultado propio, no el default del workflow, y
# ended_reason OFF_TOPIC_REASON en la llamada.
OFF_TOPIC = Outcome(id="fuera_de_tema", label="Fuera de tema")
OFF_TOPIC_REASON = "off_topic"


def outcome_for(workflow: Workflow, state: ConversationState) -> Outcome | None:
    """El primer resultado de analysis.outcomes cuyas condiciones se cumplen; sin resultados, None."""
    return next((o for o in workflow.outcomes if all(state.fields.get(k) == v for k, v in o.when.items())), None)


def conversion(workflow: Workflow | None, state: ConversationState) -> str:
    """Para los reportes (docs/features/REPORTES.md). complete: el agente termino la conversacion y no fue fuera de
    tema; partial: algun dato del analisis capturado; empty: ninguno. Sin la definicion (workflow None), los
    campos guardados."""
    outcome = state.progress.outcome
    if state.status == "completed" and outcome not in (INCOMPLETE.id, OFF_TOPIC.id):
        return "complete"
    names = workflow.analysis_fields if workflow is not None else state.fields
    if any(state.fields.get(n) not in (None, "") for n in names):
        return "partial"
    return "empty"


def outcome_goal(workflow: Workflow, outcome_id: str | None) -> bool | None:
    """Si el resultado cumple el objetivo del agente (None sin resultado; incompleta y fuera de tema, no)."""
    if outcome_id is None:
        return None
    return any(o.goal for o in workflow.outcomes if o.id == outcome_id)
