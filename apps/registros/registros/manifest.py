"""Manifiesto del formulario de cada tenant: de qué ruta del JSON salen el nombre, el titular y los
teléfonos. Es dato cargado por CLI; más rutas de contacto amplían a quién se le puede cobrar."""
import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import RELATION_CONTACTO, RELATION_TITULAR, Person, PersonPhone
from .phones import canonical_phone

_PATH = re.compile(r"[A-Za-z_]\w*(\[\*\])?(\.[A-Za-z_]\w*(\[\*\])?)*")
NAME_MAX = 200


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Manifest:
    name: str
    titular: str
    phone_paths: tuple[str, ...]
    contact_phone_paths: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()


def _path(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not _PATH.fullmatch(value):
        raise ManifestError(f"{key}: ruta inválida")
    return value


def _paths(raw: dict, key: str, required: bool = False) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or (required and not value):
        raise ManifestError(f"{key}: tiene que ser una lista de rutas" + (" con al menos una" if required else ""))
    if not all(isinstance(p, str) and _PATH.fullmatch(p) for p in value):
        raise ManifestError(f"{key}: ruta inválida")
    return tuple(value)


def parse_manifest(raw: object) -> Manifest:
    if not isinstance(raw, dict):
        raise ManifestError("el manifiesto tiene que ser un objeto")
    return Manifest(
        name=_path(raw, "name"),
        titular=_path(raw, "titular"),
        phone_paths=_paths(raw, "phone_paths", required=True),
        contact_phone_paths=_paths(raw, "contact_phone_paths"),
        filters=_paths(raw, "filters"),
    )


def values_at(data: object, path: str) -> list:
    """Valores no nulos en una ruta: `a.b` o `a[*].b`. Una ruta que no existe da lista vacía."""
    current = [data]
    for part in path.split("."):
        key, each = (part[:-3], True) if part.endswith("[*]") else (part, False)
        found = [item[key] for item in current if isinstance(item, dict) and key in item]
        if each:
            found = [x for item in found if isinstance(item, list) for x in item]
        current = found
    return [value for value in current if value is not None]


def _first_text(data: object, path: str) -> str:
    for value in values_at(data, path):
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
            return str(value).strip()[:NAME_MAX]
    return ""


def names_of(manifest: Manifest, data: object) -> tuple[str, str]:
    """(nombre de la persona, nombre del titular). Sin titular cargado, la persona es el titular."""
    name = _first_text(data, manifest.name)
    return name, _first_text(data, manifest.titular) or name


def phones_of(manifest: Manifest, data: object) -> dict[str, str]:
    """{teléfono canónico: relación}. Un número que está en las dos rutas cuenta como titular."""
    found: dict[str, str] = {}
    for paths, relation in ((manifest.phone_paths, RELATION_TITULAR),
                            (manifest.contact_phone_paths, RELATION_CONTACTO)):
        for path in paths:
            for value in values_at(data, path):
                if isinstance(value, bool) or not isinstance(value, (str, int)):
                    continue
                phone = canonical_phone(str(value))
                if phone:
                    found.setdefault(phone, relation)
    return found


def sync_person(s: Session, person: Person, manifest: Manifest) -> None:
    """Deja nombre, titular y person_phones de la ficha como dice el manifiesto. Sin commit."""
    person.name, person.titular_name = names_of(manifest, person.data)
    s.flush()  # la ficha nueva tiene que existir antes que sus teléfonos
    wanted = phones_of(manifest, person.data)
    current = {row.phone: row for row in s.scalars(select(PersonPhone).where(PersonPhone.person_id == person.id))}
    gone = [phone for phone in current if phone not in wanted]
    if gone:
        s.execute(delete(PersonPhone).where(PersonPhone.person_id == person.id, PersonPhone.phone.in_(gone)))
    for phone, relation in wanted.items():
        if phone in current:
            current[phone].relation = relation
        else:
            s.add(PersonPhone(tenant_id=person.tenant_id, person_id=person.id, phone=phone, relation=relation))
    s.flush()
