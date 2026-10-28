"""Corte por aceptacion de las condiciones: funciones que no se habilitan para un cliente hasta que acepta la
version que las cubre (docs/TERMINOS_PLAN.md, 6; llamadas directas, docs/LLAMADAS_DIRECTAS_PLAN.md, 7).

Aparte de services/legal.py, que importa el mail y la demo: este lo usan calls, phone_numbers y direct_calls sin
ciclos de import.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import legal
from ..models import LegalAcceptance
from .errors import Forbidden

# Primera version de cada documento que cubre las llamadas directas (grabacion del equipo siempre, No Llame). El
# corte pide esta o una posterior, no la vigente: si no, cada version nueva apagaria el telefono del equipo hasta
# que alguien entre al panel (el modal ya pide la vigente para usar el panel). Las versiones son fechas AAAA-MM-DD:
# se comparan como texto.
MIN_DIRECT_CALLS_VERSION = "2026-10-28"


class TermsPending(Forbidden):
    """El cliente no acepto la version que cubre la funcion (llamadas directas)."""


def client_accepted_direct_calls(s: Session, client_id: str) -> bool:
    """Si el cliente acepto, de cada documento, MIN_DIRECT_CALLS_VERSION o una posterior. Alcanza con que las haya
    aceptado cualquier usuario del cliente (cada uno, uno o los dos): la aceptacion es en nombre de la empresa
    (punto 1 de las condiciones), la entrante no tiene usuario y por API key no hay modal. Lee
    legal_acceptances.client_id, que queda aunque se borre el usuario."""
    rows = s.execute(select(LegalAcceptance.document, LegalAcceptance.version)
                     .where(LegalAcceptance.client_id == client_id,
                            LegalAcceptance.version >= MIN_DIRECT_CALLS_VERSION)).tuples()
    return {doc.id for doc in legal.DOCS} <= {document for document, _ in rows}


def check_client_accepted(s: Session, client_id: str) -> None:
    """Llamadas directas (docs/LLAMADAS_DIRECTAS_PLAN.md, 7): no se habilitan hasta que el cliente acepte la
    version que las cubre (grabacion siempre, No Llame) o una posterior. 403 terms_pending."""
    if not client_accepted_direct_calls(s, client_id):
        raise TermsPending("Aceptá las condiciones nuevas para usar el teléfono del equipo", "terms_pending")
