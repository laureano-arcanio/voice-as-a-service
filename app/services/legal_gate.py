"""Corte por aceptacion de las condiciones: funciones que no se habilitan para un cliente hasta que acepta las
versiones vigentes (docs/TERMINOS_PLAN.md, 6; llamadas directas, docs/LLAMADAS_DIRECTAS_PLAN.md, 7).

Aparte de services/legal.py, que importa el mail y la demo: este lo usan calls, phone_numbers y direct_calls sin
ciclos de import.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import legal
from ..models import LegalAcceptance
from .errors import Forbidden


class TermsPending(Forbidden):
    """El cliente no acepto las versiones vigentes y la funcion las exige (llamadas directas)."""


def client_accepted_current(s: Session, client_id: str) -> bool:
    """Si el cliente acepto las versiones vigentes de los dos documentos. Alcanza con que las haya aceptado
    cualquier usuario del cliente (cada uno, uno o los dos): la aceptacion es en nombre de la empresa (punto 1 de
    las condiciones), la entrante no tiene usuario y por API key no hay modal. Lee legal_acceptances.client_id,
    que queda aunque se borre el usuario."""
    done = set(s.execute(select(LegalAcceptance.document, LegalAcceptance.version)
                         .where(LegalAcceptance.client_id == client_id)).tuples())
    return all((v.doc.id, v.version) in done for v in legal.current_all())


def check_client_accepted(s: Session, client_id: str) -> None:
    """Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md, 7): no se habilitan hasta que el cliente acepte la
    version que las cubre (grabacion siempre, No Llame). 403 terms_pending."""
    if not client_accepted_current(s, client_id):
        raise TermsPending("Aceptá las condiciones nuevas para usar el teléfono del equipo", "terms_pending")
