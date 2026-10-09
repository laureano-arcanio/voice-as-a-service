"""Tamano de la definicion de un agente (H11). Va entera en el prompt de cada turno: si
ocupa casi todo el contexto del LLM (LLM_CONTEXT_TOKENS), la conversacion no entra y
cada turno da 400. Se valida al crear o editar; las ya guardadas no se tocan (un agente
viejo grande no deja de cargar: el recorte del historial lo sostiene mientras entre)."""
from ..config import settings
from ..conversation.models import Workflow
from ..llm import budget
from ..llm.prompt import build_classic_system, render_workflow, system_prompt

CHANNELS = ("voice", "whatsapp")


def prompt_tokens(workflow: Workflow) -> int:
    """Tokens estimados de la parte fija del prompt de un turno (sistema + definicion), en
    el canal mas largo: classic la lleva en el sistema; structured, en el mensaje del turno."""
    if workflow.engine == "classic":
        return max(budget.message_tokens(build_classic_system(workflow, ch)) for ch in CHANNELS)
    definition = budget.estimate_tokens(render_workflow(workflow))
    return max(budget.message_tokens(system_prompt(ch)) for ch in CHANNELS) + definition


def definition_errors(workflow: Workflow) -> list[dict]:
    """Errores de tamano en el formato del editor ({path, message}); vacio si entra."""
    errors = []
    knowledge = len(workflow.knowledge)
    if knowledge > settings.knowledge_max_chars:
        errors.append({"path": "knowledge", "message": (
            f"La base de conocimiento tiene {knowledge} caracteres y el máximo es "
            f"{settings.knowledge_max_chars}: va entera en cada turno. Resumila o sacá lo que el agente no usa.")})
    tokens, limit = prompt_tokens(workflow), budget.definition_limit()
    if tokens > limit:
        errors.append({"path": "", "message": (
            f"La definición del agente ocupa ~{tokens} tokens del LLM y el máximo es {limit} "
            f"(contexto de {settings.llm_context_tokens}, con lugar para la conversación). "
            "Acortá la base de conocimiento, las reglas o las descripciones de los campos.")})
    return errors
