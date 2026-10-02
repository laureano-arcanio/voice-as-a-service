"""Definiciones de agentes en el repo: la plantilla de la UI y los agentes de referencia.

- Plantilla (app/agents/templates/asistente.json): el asistente basico que ofrece la UI como punto
  de partida. Sin plantilla, el agente arranca en blanco (blank_definition). El motor se elige al
  crearlo: la definicion es la misma con los dos.
- Agentes de referencia (app/agents/reference/<id>.json): los que siembra el seed (Atentina, la demo
  de la landing y el del test de capacidad), el eval y los tests, que corren sin base. No se ofrecen
  en la UI. El sufijo _classic o _structured del id elige el motor: demo_booking_classic es
  demo_booking.json con el motor classic.
"""
import json
import re
from functools import cache
from pathlib import Path

from ..conversation.models import Workflow

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
ENGINES = ("classic", "structured")
ID_RE = re.compile(r"[a-z0-9_]+")


def _read(directory: Path, name: str) -> dict:
    path = directory / f"{name}.json"
    if not ID_RE.fullmatch(name) or not path.exists():
        raise KeyError(name)
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- plantilla de la UI ----------

def template_ids() -> list[str]:
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))


def template_data(template_id: str) -> dict:
    return _read(TEMPLATES_DIR, template_id)


def blank_definition(client_name: str) -> dict:
    """Agente en blanco: lo minimo para que la definicion sea valida (un dato y el resultado
    por defecto). Se completa desde el formulario de la UI."""
    return {
        "engine": "classic",
        "agent": {"name": "Asistente", "role": f"asistente virtual de {client_name}", "language": "es-AR"},
        "objective": {"description": ""},
        "conversation": {"opening": "Hola, ¿en qué te puedo ayudar?", "rules": []},
        "knowledge": "",
        "fields": {"consulta": {"priority": 10, "label": "Consulta", "description": "Qué necesita la persona.",
                                "type": "string", "required": True, "question": "¿En qué te puedo ayudar?"}},
        "completion": {"outcomes": [{"id": "fin", "label": "Atendida", "when": {},
                                     "message": "Gracias por comunicarte.", "goal": False}]},
    }


# ---------- agentes de referencia ----------

def reference_ids() -> list[str]:
    """Los archivos, sin las variantes por motor."""
    return sorted(p.stem for p in REFERENCE_DIR.glob("*.json"))


def reference_data(agent_id: str) -> dict:
    """La definicion de agent_id; con sufijo _classic o _structured, la del archivo sin el
    sufijo y ese motor. id queda en agent_id."""
    try:
        data = _read(REFERENCE_DIR, agent_id)
    except KeyError:
        base, _, engine = agent_id.rpartition("_")
        if engine not in ENGINES or not base:
            raise
        data = {**_read(REFERENCE_DIR, base), "engine": engine}
    return {**data, "id": agent_id}


@cache
def load_reference(agent_id: str) -> Workflow:
    return Workflow.model_validate(reference_data(agent_id))


class ReferenceDefinitions:
    """Fuente de definiciones con los agentes de referencia: agent_id es su id (eval y tests)."""

    def current(self, agent_id: str, session=None) -> tuple[int, Workflow]:
        workflow = load_reference(agent_id)
        return workflow.version, workflow

    def get(self, agent_id: str, version: int, session=None) -> Workflow:
        return load_reference(agent_id)
