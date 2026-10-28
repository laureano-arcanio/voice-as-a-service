"""Definiciones de agentes en el repo: la plantilla de la UI y los agentes de referencia.

- Plantilla (app/agents/templates/asistente.json): el asistente basico que ofrece la UI como punto
  de partida. Sin plantilla, el agente arranca en blanco (blank_definition).
- Agentes de referencia (app/agents/reference/<id>.json): los que siembra el seed (Atentina, la demo
  de la landing y el del test de capacidad), el eval y los tests, que corren sin base. No se ofrecen
  en la UI.
"""
import json
import re
from functools import cache
from pathlib import Path

from ..conversation.models import Workflow

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
# Reglas de comportamiento de un agente de atencion, a la vista y editables (antes estaban en el prompt del motor;
# AGENTS.md, "Reglas de desarrollo"). Las trae la plantilla y un agente en blanco.
GENERIC_RULES = (
    "Pedir los datos a obtener en orden, salvo que la persona los dé antes; las preguntas sugeridas se reformulan para que la conversación sea natural.",
    "No volver a preguntar lo que la persona ya respondió.",
    "Hacer normalmente una pregunta por turno.",
    "Nunca inventar datos de la persona ni información del producto.",
    "Con los datos obligatorios, o si la persona no quiere seguir, despedirse con el mensaje del cierre que corresponda y terminar la conversación.",
    "Si la conversación no tiene nada que ver con el objetivo (una broma, alguien que se burla, insulta o acosa, un número equivocado, o alguien que después de dos intentos sigue sin hablar del tema), despedirse en una frase amable que diga para qué es esta línea y terminar con el motivo fuera de tema. Un mensaje que no se entiende no es fuera de tema: pedir que lo repita.",
    "Pasar la llamada a un área del equipo cuando la persona pide hablar con alguien o necesita algo que no se puede resolver; si el área está cerrada, decir cuándo atiende y tomar el mensaje. Si ya se intentó pasarla y no se pudo, no volver a intentarlo con esa área: tomar nombre, teléfono y qué necesita.",
)
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
        "agent": {"name": "Asistente", "role": f"asistente virtual de {client_name}", "language": "es-AR"},
        "objective": {"description": ""},
        "conversation": {"opening": "Hola, ¿en qué te puedo ayudar?", "rules": list(GENERIC_RULES)},
        "knowledge": "",
        "fields": {"consulta": {"priority": 10, "label": "Consulta", "description": "Qué necesita la persona.",
                                "type": "string", "required": True, "question": "¿En qué te puedo ayudar?"}},
        "completion": {"outcomes": [{"id": "fin", "label": "Atendida", "when": {},
                                     "message": "Gracias por comunicarte.", "goal": False}]},
    }


# ---------- agentes de referencia ----------

def reference_ids() -> list[str]:
    """Los ids de los archivos."""
    return sorted(p.stem for p in REFERENCE_DIR.glob("*.json"))


def reference_data(agent_id: str) -> dict:
    """La definicion de agent_id, con id = agent_id."""
    return {**_read(REFERENCE_DIR, agent_id), "id": agent_id}


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
