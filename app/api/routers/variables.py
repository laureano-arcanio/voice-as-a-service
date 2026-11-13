"""Catalogo de variables dinamicas (app/conversation/variables.py): el mismo para todos los clientes."""
from fastapi import APIRouter

from ...conversation import variables
from ..deps import CurrentPrincipal
from ..schemas import VariableCatalogOut

router = APIRouter(tags=["variables"])


@router.get("/variables/catalog", response_model=VariableCatalogOut)
def variable_catalog(_: CurrentPrincipal):
    """Reglas de nombres de las variables de usuario, topes y las variables del sistema con donde se pueden usar
    (`applies_to`: prompt, first_message, analysis, handoff, tool). Sin datos del cliente."""
    return variables.catalog()
