"""Plantillas de agentes: definiciones JSON en app/agents/templates/<id>.json.

Sirven para crear agentes (la UI las ofrece como punto de partida), para el seed
del cliente interno y para el eval y los tests, que corren sin base.
"""
import json
import re
from functools import cache
from pathlib import Path

from ..conversation.models import Workflow

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@cache
def load_template(template_id: str) -> Workflow:
    return Workflow.model_validate(template_data(template_id))


def template_data(template_id: str) -> dict:
    path = TEMPLATES_DIR / f"{template_id}.json"
    if not re.fullmatch(r"[a-z0-9_]+", template_id) or not path.exists():
        raise KeyError(template_id)
    return json.loads(path.read_text(encoding="utf-8"))


def template_ids() -> list[str]:
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))


class TemplateDefinitions:
    """Fuente de definiciones con las plantillas: agent_id es el id de la plantilla."""

    def current(self, agent_id: str, session=None) -> tuple[int, Workflow]:
        workflow = load_template(agent_id)
        return workflow.version, workflow

    def get(self, agent_id: str, version: int, session=None) -> Workflow:
        return load_template(agent_id)
