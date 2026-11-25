"""Catalogo de variables dinamicas (app/conversation/variables.py): el mismo para todos los clientes."""
from fastapi import APIRouter

from ...conversation import variables
from ...llm.prompt import DEFAULT_ANALYSIS_PROMPT
from ..deps import CurrentPrincipal
from ..schemas import VariableCatalogOut

router = APIRouter(tags=["variables"])


@router.get("/variables/catalog", response_model=VariableCatalogOut)
def variable_catalog(_: CurrentPrincipal):
    """Reglas de nombres de las variables de usuario, topes y las variables del sistema con donde se pueden usar
    (`applies_to`: prompt, first_message, analysis, handoff, tool). Sin datos del cliente. `defaults` trae los
    textos de la plataforma para los botones "Partir del predeterminado" y "Restaurar el predeterminado" del
    editor del análisis."""
    return {**variables.catalog(), "defaults": {"analysis_prompt": DEFAULT_ANALYSIS_PROMPT}}
