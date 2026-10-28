"""Versiones publicadas de las condiciones y de la politica de privacidad, para el admin (pantalla Legales): cada
texto con su huella y cuantas aceptaciones tiene. La landing solo lista la vigente; las anteriores se abren por el
link permanente de los mails de aceptacion (docs/features/LEGAL.md)."""
from typing import Literal

from fastapi import APIRouter

from ... import legal as legal_docs
from ...services import legal
from ..deps import DB, AdminPrincipal
from ..schemas import LegalVersionAdminOut, LegalVersionTextOut
from .auth import legal_out

router = APIRouter(prefix="/legal", tags=["legal"])


def _admin_out(v: legal_docs.Version, counts: dict[tuple[str, str], int]) -> dict:
    return {**legal_out(v).model_dump(), "current": v == legal_docs.current(v.doc.id),
            "acceptances": counts.get((v.doc.id, v.version), 0)}


@router.get("/versions", response_model=list[LegalVersionAdminOut])
def list_versions(_: AdminPrincipal, db: DB):
    """Todas las versiones de cada documento, la mas nueva primero."""
    counts = legal.acceptance_counts(db)
    return [_admin_out(v, counts) for d in legal_docs.DOCS for v in reversed(legal_docs.versions(d.id))]


@router.get("/versions/{document}/{version}", response_model=LegalVersionTextOut)
def get_version(document: Literal["terms", "privacy"], version: str, _: AdminPrincipal, db: DB):
    """Una version con su texto exacto."""
    v = legal.find_version(document, version)
    return {**_admin_out(v, legal.acceptance_counts(db)), "text": v.text}
