"""API JSON del panel: fichas de personas del tenant de la sesión.

Reglas de la carga:
- La ficha se valida con el JSON Schema del tenant al guardar, nunca al leer: una ficha vieja se
  sigue viendo aunque el formulario cambie.
- El equipo carga las fichas: quien tiene usuario en el tenant. No hay carga por el titular.
- `version` evita pisar a otro. No se guardan versiones anteriores; audit_log dice quién y cuándo.
- Teléfono o dato de `filters` repetido: se permite y se advierte.
- Baja: la ficha deja de verse y de identificarse; queda en la base con sus cobros.
"""
import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from jsonschema import Draft202012Validator
from pydantic import BaseModel
from sqlalchemy import String, cast, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONPATH
from sqlalchemy.orm import Session

from .. import audit
from ..auth import CurrentUser, DbSession
from ..db import utcnow
from ..manifest import Manifest, ManifestError, names_of, parse_manifest, phones_of, sync_person
from ..models import Charge, Person, PersonPhone, Tenant, User
from ..phones import canonical_phone

router = APIRouter(prefix="/panel/api")

PAGE_SIZE_DEFAULT = 50
PAGE_SIZE_MAX = 100
CHARGES_SHOWN = 200
MAX_DATA_BYTES = 256_000
MAX_DATA_DEPTH = 32
REPEATED_NAMES_SHOWN = 3

ID_RE = re.compile(r"[0-9a-f-]{36}")

# Sin repetir el valor recibido: un error no lleva datos personales.
SCHEMA_MESSAGES = {
    "required": "Este dato es obligatorio",
    "minLength": "Este dato es obligatorio",
    "type": "El formato no es válido",
    "enum": "Elegí una de las opciones",
    "const": "Elegí una de las opciones",
    "maxLength": "Es demasiado largo",
}
SCHEMA_MESSAGE_DEFAULT = "El valor no es válido"


# --- Validación ---


@dataclass(frozen=True)
class FieldError(Exception):
    field: str
    message: str


def _no_form() -> HTTPException:
    return HTTPException(409, "Este tenant todavía no tiene formulario cargado")


def _form_of(tenant: Tenant) -> tuple[dict, Manifest]:
    if tenant.form_schema is None or tenant.manifest is None:
        raise _no_form()
    try:
        return tenant.form_schema, parse_manifest(tenant.manifest)
    except ManifestError:
        raise _no_form() from None


def _field_path(parts) -> str:
    """Ruta de jsonschema en el formato de los `name` del formulario: contactos[0].telefono."""
    path = ""
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)
    return path


def _join(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key


def _schema_errors(schema: dict, data: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    for error in Draft202012Validator(schema).iter_errors(data):
        parent = _field_path(error.absolute_path)
        if error.validator == "required":
            for key in error.validator_value:
                if isinstance(error.instance, dict) and key not in error.instance:
                    errors.setdefault(_join(parent, key), SCHEMA_MESSAGES["required"])
        else:
            errors.setdefault(parent, SCHEMA_MESSAGES.get(error.validator, SCHEMA_MESSAGE_DEFAULT))
    return errors


def _concrete_values(data: object, path: str) -> list[tuple[str, Any]]:
    """Como manifest.values_at, con la ruta de cada valor: a[*].b da (a[0].b, valor), (a[1].b, valor)..."""
    current: list[tuple[str, Any]] = [("", data)]
    for part in path.split("."):
        key, each = (part[:-3], True) if part.endswith("[*]") else (part, False)
        found: list[tuple[str, Any]] = []
        for prefix, item in current:
            if not isinstance(item, dict) or key not in item:
                continue
            here = _join(prefix, key)
            if not each:
                found.append((here, item[key]))
            elif isinstance(item[key], list):
                found.extend((f"{here}[{i}]", value) for i, value in enumerate(item[key]))
        current = found
    return [(field, value) for field, value in current if value is not None]


def _phone_errors(manifest: Manifest, data: dict) -> dict[str, str]:
    """Un texto sin dígitos ("No sé", "No aplica") se acepta y no es un teléfono."""
    errors = {}
    for path in manifest.phone_paths + manifest.contact_phone_paths:
        for field, value in _concrete_values(data, path):
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                continue
            text_value = str(value)
            if any(ch.isdigit() for ch in text_value) and not canonical_phone(text_value):
                errors[field] = "El teléfono no es válido: revisá que tenga característica y número"
    return errors


def _check_storable(value: object, depth: int = 0) -> None:
    """Lo que el JSON acepta y jsonb no: sin esto, sería un 500."""
    if depth > MAX_DATA_DEPTH:
        raise HTTPException(422, "La ficha tiene demasiados niveles")
    if isinstance(value, float) and not math.isfinite(value):
        raise HTTPException(422, "La ficha tiene un número inválido")
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise HTTPException(422, "La ficha tiene caracteres inválidos") from None
        if "\x00" in value:
            raise HTTPException(422, "La ficha tiene caracteres inválidos")
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_storable(key, depth + 1)
            _check_storable(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_storable(item, depth + 1)


def _validated(tenant: Tenant, data: dict) -> Manifest:
    schema, manifest = _form_of(tenant)
    _check_storable(data)
    if len(json.dumps(data)) > MAX_DATA_BYTES:
        raise HTTPException(422, "La ficha es demasiado grande")
    errors = _schema_errors(schema, data)
    for field, message in _phone_errors(manifest, data).items():
        errors.setdefault(field, message)
    if not names_of(manifest, data)[0]:
        errors.setdefault(manifest.name, SCHEMA_MESSAGES["required"])
    if errors:
        raise HTTPException(422, {
            "message": "Revisá los datos marcados",
            "fields": [{"field": field, "message": message} for field, message in errors.items()],
        })
    return manifest


# --- Búsqueda ---


def _normalize(value: str) -> str:
    """Para comparar documentos y códigos: sin mayúsculas, puntos, guiones ni espacios."""
    return re.sub(r"[\W_]", "", value.lower())


def _filter_match(path: str, normalized: str, *, exact: bool = False):
    """La ficha tiene ese valor en una ruta de `filters`, comparado normalizado."""
    parts = []
    for part in path.split("."):
        key, each = (part[:-3], True) if part.endswith("[*]") else (part, False)
        parts.append(f'"{key}"' + ("[*]" if each else ""))
    jsonpath = "$." + ".".join(parts)
    values = func.jsonb_array_elements_text(
        func.jsonb_path_query_array(Person.data, cast(literal(jsonpath, String), JSONPATH))
    ).table_valued("value")
    stored = func.regexp_replace(func.lower(values.c.value), "[^[:alnum:]]", "", "g")
    condition = stored == normalized if exact else stored.contains(normalized, autoescape=True)
    return exists(select(1).select_from(values).where(condition))


def _search_condition(tenant_id: str, q: str, manifest: Manifest | None):
    conditions = [Person.name.icontains(q, autoescape=True)]
    phone = canonical_phone(q)
    if phone:
        conditions.append(exists(select(1).where(PersonPhone.person_id == Person.id,
                                                 PersonPhone.tenant_id == tenant_id,
                                                 PersonPhone.phone == phone)))
    normalized = _normalize(q)
    if normalized and manifest is not None:
        conditions.extend(_filter_match(path, normalized) for path in manifest.filters)
    return or_(*conditions)


def _manifest_or_none(tenant: Tenant) -> Manifest | None:
    try:
        return parse_manifest(tenant.manifest)
    except ManifestError:
        return None


# --- Respuestas ---


def _when(value) -> str | None:
    return f"{value.isoformat()}Z" if value is not None else None  # UTC sin zona en la base


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _email_of(s: Session, user_id: str | None) -> str | None:
    return s.scalar(select(User.email).where(User.id == user_id)) if user_id else None


def _charges(s: Session, person: Person) -> list[dict]:
    rows = s.scalars(select(Charge).where(Charge.tenant_id == person.tenant_id, Charge.person_id == person.id)
                     .order_by(Charge.created_at.desc()).limit(CHARGES_SHOWN))
    return [{
        "id": row.id,
        "titular_name": row.titular_name,
        "amount": _money(row.amount),
        "currency": row.currency,
        "status": row.status,
        "from_phone": row.from_phone,
        "operator_message": row.operator_message,
        "created_at": _when(row.created_at),
    } for row in rows]


def _detail(s: Session, person: Person) -> dict:
    return {
        "id": person.id,
        "name": person.name,
        "titular_name": person.titular_name,
        "al_dia": person.al_dia,
        "al_dia_by": _email_of(s, person.al_dia_by),
        "al_dia_at": _when(person.al_dia_at),
        "data": person.data,
        "version": person.version,
        "created_by": _email_of(s, person.created_by),
        "created_at": _when(person.created_at),
        "updated_at": _when(person.updated_at),
        "charges": _charges(s, person),
    }


def _others_names(s: Session, person: Person, condition) -> list[str]:
    return list(s.scalars(select(Person.name).where(
        Person.tenant_id == person.tenant_id, Person.active, Person.id != person.id, condition,
    ).order_by(Person.name).limit(REPEATED_NAMES_SHOWN)))


def _warnings(s: Session, person: Person, manifest: Manifest) -> list[dict]:
    warnings: list[dict] = []
    for path in manifest.phone_paths + manifest.contact_phone_paths:
        for field, value in _concrete_values(person.data, path):
            phone = canonical_phone(str(value)) if isinstance(value, (str, int)) else ""
            if not phone:
                continue
            names = _others_names(s, person, exists(select(1).where(
                PersonPhone.person_id == Person.id, PersonPhone.tenant_id == person.tenant_id,
                PersonPhone.phone == phone)))
            if names:
                warnings.append({"field": field, "message": f"Este teléfono también está en: {', '.join(names)}"})
    for path in manifest.filters:
        for field, value in _concrete_values(person.data, path):
            normalized = _normalize(value) if isinstance(value, str) else ""
            if not normalized:
                continue
            names = _others_names(s, person, _filter_match(path, normalized, exact=True))
            if names:
                warnings.append({"field": field, "message": f"Este dato también está en: {', '.join(names)}"})
    return warnings


def get_active_person(s: Session, tenant_id: str, person_id: str, *, lock: bool = False) -> Person | None:
    """Ficha vigente de ese tenant. Una ajena o de baja da lo mismo que una que no existe."""
    if not ID_RE.fullmatch(person_id):
        return None
    query = select(Person).where(Person.id == person_id, Person.tenant_id == tenant_id, Person.active)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return s.scalar(query)


def _person_or_404(s: Session, tenant_id: str, person_id: str, *, lock: bool = False) -> Person:
    person = get_active_person(s, tenant_id, person_id, lock=lock)
    if person is None:
        raise HTTPException(404, "No existe esa ficha")
    return person


# --- Rutas ---


class PersonIn(BaseModel):
    data: dict


class PersonUpdate(PersonIn):
    version: int


class AlDiaIn(BaseModel):
    al_dia: bool


def search_persons(s: Session, tenant_id: str, q: str, al_dia: bool | None, page: int, per_page: int) -> dict:
    """Lista de fichas vigentes de ese tenant. La usan el panel del cliente y el admin."""
    tenant = s.get(Tenant, tenant_id)
    conditions = [Person.tenant_id == tenant_id, Person.active]
    q = q.replace("\x00", "").strip()
    if q:
        conditions.append(_search_condition(tenant_id, q, _manifest_or_none(tenant)))
    if al_dia is not None:
        conditions.append(Person.al_dia.is_(al_dia))
    total = s.scalar(select(func.count()).select_from(Person).where(*conditions))
    # Solo columnas de la lista: los datos clínicos no se leen acá.
    rows = s.execute(
        select(Person.id, Person.name, Person.titular_name, Person.al_dia, Person.al_dia_at, Person.updated_at,
               User.email.label("al_dia_by"))
        .outerjoin(User, User.id == Person.al_dia_by)
        .where(*conditions)
        .order_by(func.lower(Person.name), Person.id)
        .limit(per_page).offset((page - 1) * per_page)
    )
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [{
            "id": row.id,
            "name": row.name,
            "titular_name": row.titular_name,
            "al_dia": row.al_dia,
            "al_dia_by": row.al_dia_by,
            "al_dia_at": _when(row.al_dia_at),
            "updated_at": _when(row.updated_at),
        } for row in rows],
    }


def person_detail(s: Session, tenant_id: str, person_id: str) -> tuple[Person, dict]:
    """Ficha vigente de ese tenant con sus cobros; 404 si es de baja, de otro tenant o no existe. Sin audit:
    lo registra quien llama, si corresponde."""
    person = _person_or_404(s, tenant_id, person_id)
    return person, _detail(s, person)


# Parámetros de la lista, compartidos con /admin/api.
SearchQ = Annotated[str, Query(max_length=200)]
PageQ = Annotated[int, Query(ge=1, le=1_000_000)]
PerPageQ = Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)]


@router.get("/persons")
def list_persons(
    user: CurrentUser,
    s: DbSession,
    q: SearchQ = "",
    al_dia: bool | None = None,
    page: PageQ = 1,
    per_page: PerPageQ = PAGE_SIZE_DEFAULT,
) -> dict:
    return search_persons(s, user.tenant_id, q, al_dia, page, per_page)


@router.post("/persons", status_code=201)
def create_person(body: PersonIn, user: CurrentUser, s: DbSession) -> dict:
    manifest = _validated(s.get(Tenant, user.tenant_id), body.data)
    person = Person(tenant_id=user.tenant_id, name="", titular_name="", data=body.data, created_by=user.id)
    s.add(person)
    sync_person(s, person, manifest)
    audit.record(s, user.tenant_id, "person_create", user_id=user.id, person_id=person.id)
    warnings = _warnings(s, person, manifest)
    s.commit()
    return {**_detail(s, person), "warnings": warnings}


@router.get("/persons/{person_id}")
def read_person(person_id: str, user: CurrentUser, s: DbSession) -> dict:
    person, detail = person_detail(s, user.tenant_id, person_id)
    audit.record(s, user.tenant_id, "person_view", user_id=user.id, person_id=person.id)
    s.commit()
    return detail


@router.put("/persons/{person_id}")
def update_person(person_id: str, body: PersonUpdate, user: CurrentUser, s: DbSession) -> dict:
    person = _person_or_404(s, user.tenant_id, person_id, lock=True)
    if person.version != body.version:
        raise HTTPException(409, "Otra persona modificó esta ficha mientras la editabas")
    manifest = _validated(s.get(Tenant, user.tenant_id), body.data)
    person.data = body.data
    person.version += 1
    sync_person(s, person, manifest)
    audit.record(s, user.tenant_id, "person_update", user_id=user.id, person_id=person.id,
                 detail={"version": person.version})
    warnings = _warnings(s, person, manifest)
    s.commit()
    return {**_detail(s, person), "warnings": warnings}


@router.put("/persons/{person_id}/al-dia")
def set_al_dia(person_id: str, body: AlDiaIn, user: CurrentUser, s: DbSession) -> dict:
    """No cambia `version`: marcarla no pisa a quien está editando el formulario."""
    person = _person_or_404(s, user.tenant_id, person_id, lock=True)
    if person.al_dia != body.al_dia:
        person.al_dia, person.al_dia_by, person.al_dia_at = body.al_dia, user.id, utcnow()
        audit.record(s, user.tenant_id, "person_al_dia", user_id=user.id, person_id=person.id,
                     detail={"al_dia": body.al_dia})
    s.commit()
    return {"al_dia": person.al_dia, "al_dia_by": _email_of(s, person.al_dia_by), "al_dia_at": _when(person.al_dia_at)}


@router.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: str, user: CurrentUser, s: DbSession) -> None:
    person = _person_or_404(s, user.tenant_id, person_id, lock=True)
    person.active = False
    audit.record(s, user.tenant_id, "person_delete", user_id=user.id, person_id=person.id)
    s.commit()
