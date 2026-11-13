"""Definiciones de agentes en el repo: la plantilla de la UI y los agentes de referencia.

- Plantillas (app/agents/templates/<id>.json): el asistente basico y una por rubro (salud, gimnasio,
  inmobiliaria, gastronomia, cobranzas), que ofrece la UI como punto de partida y el asistente de primera vez
  (docs/features/PRIMERA_VEZ.md). Llevan [EMPRESA] y [AGENTE], que se completan al crear el agente
  (fill_template). Sin plantilla, el agente arranca en blanco (blank_definition).
- Agentes de referencia (app/agents/reference/<id>.json): los que siembra el seed (Atentina, la demo
  de la landing y el del test de capacidad), el eval y los tests, que corren sin base. No se ofrecen
  en la UI.
"""
import json
import re
from functools import cache
from pathlib import Path

from ..conversation import legacy
from ..conversation.models import Workflow

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
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


COMPANY_MARK, AGENT_MARK = "[EMPRESA]", "[AGENTE]"
DEFAULT_VOICE = "sofia"
# El catalogo de voces tiene los nombres sin tildes (como web/src/features/voices/names.ts).
ACCENTED = {"sofia": "Sofía", "lucia": "Lucía", "veronica": "Verónica", "rocio": "Rocío", "belen": "Belén",
            "martin": "Martín", "nicolas": "Nicolás", "joaquin": "Joaquín", "tomas": "Tomás"}


def voice_name(voice: str) -> str:
    return ACCENTED.get(voice, voice.capitalize())


def fill_template(data: dict, company: str, voice: str | None = None) -> dict:
    """La plantilla con la empresa y el agente: el agente se llama como la voz (la de la plantilla si no se
    elige otra)."""
    voice = voice or data.get("agent", {}).get("voice") or DEFAULT_VOICE
    text = json.dumps(data, ensure_ascii=False)
    esc = lambda v: json.dumps(v, ensure_ascii=False)[1:-1]   # el reemplazo va dentro de strings JSON
    text = text.replace(COMPANY_MARK, esc(company.strip() or "la empresa")).replace(AGENT_MARK, esc(voice_name(voice)))
    filled = json.loads(text)
    filled.setdefault("agent", {})["voice"] = voice
    return filled


def blank_definition(client_name: str) -> dict:
    """Agente en blanco: un prompt corto con los titulos para completar desde la UI, sin analisis."""
    return {
        "agent": {"name": "Asistente", "language": "es-AR"},
        "prompt": (f"# Identidad\nSos Asistente, asistente virtual de {client_name}.\n\n"
                   "# Objetivo\nQué tiene que lograr el agente en la conversación.\n\n"
                   "# Cómo conversar\n- Tono, largo de las respuestas y reglas del negocio.\n\n"
                   "# Información\nLo que el agente necesita saber para responder."),
        "first_message": "Hola, ¿en qué te puedo ayudar?",
    }


def prompt_objective(prompt: str) -> str:
    """El primer parrafo bajo el titulo "# Objetivo" del prompt, o vacio."""
    m = re.search(r"^#\s*Objetivo\s*$\n+(.+?)(?:\n\s*\n|\n#|\Z)", prompt or "", re.MULTILINE | re.DOTALL)
    return " ".join(m.group(1).split()) if m else ""


def objective_of(definition: dict) -> str:
    """El objetivo de una definicion guardada, en la forma actual o la vieja."""
    return prompt_objective(str(legacy.upgrade(definition or {}).get("prompt") or ""))


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
