"""Condiciones del servicio y politica de privacidad con version (docs/features/LEGAL.md).

Cada version es un archivo `texts/<slug>/<version>.md` (version = fecha de publicacion, AAAA-MM-DD) que **no se edita
una vez publicado**: un cambio es un archivo nuevo, y la vigente es la de fecha mas alta. El SHA-256 del archivo queda
en cada aceptacion (`legal_acceptances`), asi se puede probar que texto exacto se acepto. La landing muestra los
mismos archivos: `make legal-sync` los copia a landing/src/data/legal/.
"""
import hashlib
import pathlib
from dataclasses import dataclass
from functools import cache

from ..config import settings

TEXTS = pathlib.Path(__file__).parent / "texts"


@dataclass(frozen=True)
class LegalDoc:
    id: str       # terms | privacy: lo que guarda legal_acceptances.document
    slug: str     # carpeta en texts/ y path de la landing
    title: str


DOCS = (LegalDoc("terms", "terminos", "Condiciones del servicio"),
        LegalDoc("privacy", "privacidad", "Política de privacidad"))
BY_ID = {d.id: d for d in DOCS}


@dataclass(frozen=True)
class Version:
    doc: LegalDoc
    version: str
    sha256: str
    text: str

    @property
    def url(self) -> str:
        """Link permanente a esta version (no cambia aunque salga otra)."""
        return f"{settings.site_url.rstrip('/')}/{self.doc.slug}/{self.version}"


@cache
def versions(doc_id: str) -> tuple[Version, ...]:
    doc = BY_ID[doc_id]
    out = []
    for path in sorted((TEXTS / doc.slug).glob("*.md")):
        raw = path.read_bytes()
        out.append(Version(doc, path.stem, hashlib.sha256(raw).hexdigest(), raw.decode()))
    return tuple(out)


def current(doc_id: str) -> Version:
    return versions(doc_id)[-1]


def current_all() -> list[Version]:
    return [current(d.id) for d in DOCS]


def checkbox_text(terms_version: str, privacy_version: str) -> str:
    """Lo que dice la casilla del registro y del panel; se guarda tal cual en cada aceptacion."""
    return (f"Leí y acepto las Condiciones del servicio (versión {terms_version}) "
            f"y la Política de privacidad (versión {privacy_version}).")
