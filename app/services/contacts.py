"""Agenda de contactos del cliente y bajas (docs/LLAMADAS_SALIENTES_PLAN.md, 3.1 y 3.2).

- El telefono (E.164, services/phones.py) es unico por cliente y lo unico obligatorio.
- Cargar es un upsert por telefono: el existente se actualiza (los atributos y las etiquetas
  se suman, no se borran) y uno archivado sigue archivado: se informa aparte.
- No hay borrado: se archiva. Archivar saltea los intentos pendientes del contacto en las
  campañas que siguen abiertas.
- Tope del plan (`max_contacts`): cuenta solo los activos.
- Bajas (`contact_optouts`): por telefono y canal, aparte de la ficha.

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import (
    Campaign,
    CampaignContact,
    Client,
    Contact,
    ContactOptout,
)
from ..models.campaigns import OPTOUT_CHANNELS, OPTOUT_SOURCES
from . import campaign_callbacks as callbacks
from . import limits as limits_service
from . import phones
from .errors import Invalid, NotFound, QuotaExceeded

# Columnas del CSV (encabezado, sin importar mayusculas ni acentos).
PHONE_COLUMNS = {"telefono", "phone", "numero", "celular", "whatsapp", "wa_id", "movil"}
NAME_COLUMNS = {"nombre", "name"}
EMAIL_COLUMNS = {"email", "mail", "correo"}
EXTERNAL_ID_COLUMNS = {"external_id", "id_externo", "idexterno", "id"}
TAG_COLUMNS = {"tags", "etiquetas", "tag", "etiqueta"}
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,31}$")
MAX_TAGS = 20
MAX_ATTRIBUTES = 50
CHUNK = 500


# --- Filas y validacion ---

@dataclass
class ContactRow:
    """Un contacto a cargar, como vino (el telefono se normaliza al cargarlo)."""
    phone: str
    name: str | None = None
    email: str | None = None
    external_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    line: int | None = None     # fila del CSV (1 = encabezado)


@dataclass
class Rejected:
    phone: str
    reason: str
    line: int | None = None


@dataclass
class UpsertResult:
    created: list[Contact] = field(default_factory=list)
    updated: list[Contact] = field(default_factory=list)
    # Los actualizados que estan archivados: no se desarchivan solos.
    archived: list[Contact] = field(default_factory=list)
    invalid: list[Rejected] = field(default_factory=list)
    limit_hit: bool = False     # alguno no entro por el tope del plan


def header_key(header: str) -> str:
    text = unicodedata.normalize("NFD", header or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_]", "", text.lower())


def attribute_key(header: str) -> str:
    """El nombre de un atributo desde el encabezado del CSV: sin acentos, en minusculas y con _."""
    text = unicodedata.normalize("NFD", header or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")[:64]


def normalize_tag(tag: str) -> str:
    """ValueError si no es una etiqueta valida (letras, numeros y _ . : -, hasta 32)."""
    text = unicodedata.normalize("NFD", str(tag or "")).encode("ascii", "ignore").decode().strip().lower()
    text = re.sub(r"\s+", "_", text)
    if not TAG_RE.match(text):
        raise ValueError(f"etiqueta inválida: {tag!r} (letras, números y _ . : -, hasta 32 caracteres)")
    return text


def clean_tags(tags: list[str]) -> list[str]:
    out = list(dict.fromkeys(normalize_tag(t) for t in tags if str(t or "").strip()))
    if len(out) > MAX_TAGS:
        raise ValueError(f"máximo {MAX_TAGS} etiquetas")
    return out


def clean_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    if len(attributes) > MAX_ATTRIBUTES:
        raise ValueError(f"máximo {MAX_ATTRIBUTES} atributos")
    out: dict[str, Any] = {}
    for key, value in attributes.items():
        key = str(key).strip()
        if not key or len(key) > 64:
            raise ValueError("el nombre de un atributo va de 1 a 64 caracteres")
        if value is not None and not isinstance(value, str | int | float | bool):
            raise ValueError(f"el atributo {key} tiene que ser un texto, un número o un booleano")
        if isinstance(value, str) and len(value) > 512:
            raise ValueError(f"el atributo {key} supera los 512 caracteres")
        out[key] = value
    return out


def _text(value: str | None, limit: int, what: str) -> str | None:
    value = (value or "").strip()
    if len(value) > limit:
        raise ValueError(f"{what} de más de {limit} caracteres")
    return value or None


def _email(value: str | None) -> str | None:
    email = _text(value, 254, "email")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("email inválido")
    return email


def _clean(row: ContactRow) -> tuple[str, dict]:
    """(telefono E.164, campos validados). ValueError con el motivo si la fila no sirve."""
    phone = phones.normalize_phone(row.phone)
    return phone, {"name": _text(row.name, 128, "nombre"), "email": _email(row.email),
                   "external_id": _text(row.external_id, 128, "id externo"),
                   "attributes": clean_attributes(row.attributes), "tags": clean_tags(row.tags)}


# --- CSV ---

def sniff_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def parse_csv(text: str) -> list[ContactRow]:
    """CSV con encabezado: una columna de telefono (telefono, celular, phone...); nombre, email,
    id externo (external_id) y etiquetas (separadas por | o ;) opcionales; las demas columnas
    son atributos del contacto. Separador coma, punto y coma o tab. Invalid si no hay columna
    de telefono."""
    text = (text or "").lstrip("﻿")
    if not text.strip():
        return []
    reader = csv.reader(io.StringIO(text), delimiter=sniff_delimiter(text))
    header = next(reader, [])
    keys = [header_key(h) for h in header]
    roles = {}
    for role, names in (("phone", PHONE_COLUMNS), ("name", NAME_COLUMNS), ("email", EMAIL_COLUMNS),
                        ("external_id", EXTERNAL_ID_COLUMNS), ("tags", TAG_COLUMNS)):
        roles[role] = next((i for i, k in enumerate(keys) if k in names), None)
    if roles["phone"] is None:
        raise Invalid("El CSV necesita un encabezado con una columna telefono (o celular, phone, whatsapp)")
    used = {i for i in roles.values() if i is not None}
    extra = [(i, attribute_key(header[i])) for i in range(len(header)) if i not in used and attribute_key(header[i])]
    rows = []
    for line, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue

        def cell(i: int | None, values: list[str] = values) -> str:
            return values[i].strip() if i is not None and i < len(values) else ""

        tags = [t for t in re.split(r"[|;]", cell(roles["tags"])) if t.strip()]
        rows.append(ContactRow(
            phone=cell(roles["phone"]), name=cell(roles["name"]) or None, email=cell(roles["email"]) or None,
            external_id=cell(roles["external_id"]) or None, tags=tags, line=line,
            attributes={key: cell(i) for i, key in extra if cell(i)}))
    return rows


# --- Alta, actualizacion y busqueda ---

def find(s: Session, client_id: str, phone_list: list[str]) -> dict[str, Contact]:
    """Los contactos del cliente con esos telefonos (E.164), archivados incluidos."""
    found: dict[str, Contact] = {}
    unique = list(dict.fromkeys(phone_list))
    for i in range(0, len(unique), CHUNK):
        for c in s.scalars(select(Contact).where(Contact.client_id == client_id,
                                                 Contact.phone.in_(unique[i:i + CHUNK]))):
            found[c.phone] = c
    return found


def room(s: Session, client_id: str) -> int | None:
    """Cuantos contactos activos mas entran en la agenda segun el plan; None si no hay tope."""
    client = s.get(Client, client_id)
    if client is None:
        raise NotFound("Cliente inexistente")
    return limits_service.contacts_room(s, client_id, limits_service.effective_limits(s, client))


def _merge(contact: Contact, fields: dict) -> None:
    for key in ("name", "email", "external_id"):
        if fields[key]:
            setattr(contact, key, fields[key])
    if fields["attributes"]:
        contact.attributes = {**(contact.attributes or {}), **fields["attributes"]}
    if fields["tags"]:
        contact.tags = sorted({*(contact.tags or []), *fields["tags"]})


def new_contact(client_id: str, phone: str, source: str, *, name: str | None = None, **fields) -> Contact:
    return Contact(client_id=client_id, phone=phone, name=name, source=source, attributes={}, tags=[], **fields)


def upsert(s: Session, client_id: str, rows: list[ContactRow], source: str = "api",
           tags: list[str] | None = None) -> UpsertResult:
    """Carga contactos: crea los nuevos y actualiza los que ya tienen ese telefono. Las filas
    invalidas, o que no entran por el tope del plan, vuelven en `invalid` sin cortar la carga.
    Un telefono repetido en la lista se suma al mismo contacto. `tags`: etiquetas para todos."""
    result = UpsertResult()
    # Bloquea al cliente: dos cargas a la vez no pueden pasarse del tope.
    client = s.scalar(select(Client).where(Client.id == client_id).with_for_update(key_share=True, of=Client))
    if client is None:
        raise NotFound("Cliente inexistente")
    free = limits_service.contacts_room(s, client_id, limits_service.effective_limits(s, client))
    valid: list[tuple[ContactRow, str, dict]] = []
    for row in rows:
        try:
            phone, fields = _clean(ContactRow(**{**row.__dict__, "tags": [*row.tags, *(tags or [])]}))
        except ValueError as e:
            result.invalid.append(Rejected(row.phone, str(e), row.line))
            continue
        valid.append((row, phone, fields))
    existing = find(s, client_id, [phone for _, phone, _ in valid])
    touched: set[str] = set()
    for row, phone, fields in valid:
        contact = existing.get(phone)
        if contact is None:
            if free is not None and free <= 0:
                result.invalid.append(Rejected(row.phone, "tope de contactos del plan", row.line))
                result.limit_hit = True
                continue
            contact = new_contact(client_id, phone, source)
            _merge(contact, fields)
            s.add(contact)
            existing[phone] = contact
            touched.add(phone)
            result.created.append(contact)
            if free is not None:
                free -= 1
            continue
        _merge(contact, fields)
        if phone not in touched:
            touched.add(phone)
            result.updated.append(contact)
            if contact.archived_at is not None:
                result.archived.append(contact)
    s.flush()
    return result


def import_csv(s: Session, client_id: str, text: str, tags: list[str] | None = None) -> UpsertResult:
    return upsert(s, client_id, parse_csv(text), source="csv", tags=tags)


EDITABLE = ("name", "email", "external_id", "attributes", "tags")


def update_contact(s: Session, contact: Contact, **changes) -> Contact:
    """Edita datos y etiquetas (el telefono no: otro telefono es otro contacto). A diferencia de
    la carga, los atributos y las etiquetas reemplazan a los anteriores."""
    unknown = set(changes) - set(EDITABLE)
    if unknown:
        raise Invalid(f"Campos no editables: {', '.join(sorted(unknown))}")
    try:
        for key, value in changes.items():
            if key == "attributes":
                value = clean_attributes(value or {})
            elif key == "tags":
                value = clean_tags(value or [])
            elif key == "email":
                value = _email(value)
            else:
                value = _text(value, 128, key)
            setattr(contact, key, value)
    except ValueError as e:
        raise Invalid(str(e)) from None
    s.flush()
    return contact


def tag_filter(tag: str):
    """Contactos con esa etiqueta, en SQL portable (las etiquetas no llevan comillas ni %)."""
    pattern = '%"' + normalize_tag(tag).replace("_", "\\_") + '"%'
    return cast(Contact.tags, String).like(pattern, escape="\\")


def list_contacts(s: Session, client_id: str | None, *, q: str | None = None, tag: str | None = None,
                  archived: str = "false", offset: int = 0, limit: int = 50) -> tuple[list[Contact], int]:
    """Pagina de contactos. archived: false (activos), true (archivados) o all."""
    query = select(Contact)
    if client_id is not None:
        query = query.where(Contact.client_id == client_id)
    if archived == "false":
        query = query.where(Contact.archived_at.is_(None))
    elif archived == "true":
        query = query.where(Contact.archived_at.is_not(None))
    elif archived != "all":
        raise Invalid("archived: false, true o all")
    if q and q.strip():
        like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(or_(*(col.ilike(like, escape="\\")
                                  for col in (Contact.name, Contact.phone, Contact.email, Contact.external_id))))
    if tag:
        try:
            query = query.where(tag_filter(tag))
        except ValueError as e:
            raise Invalid(str(e)) from None
    total = s.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = s.scalars(query.order_by(Contact.created_at.desc(), Contact.id).offset(offset).limit(limit))
    return list(rows), total


# --- Archivar (no hay borrado) ---

def archive(s: Session, contacts: list[Contact]) -> int:
    """Archiva los activos de la lista. Sus intentos pendientes en campañas abiertas pasan a
    `skipped` (motivo contact_archived); los terminados quedan en los reportes. Devuelve cuantos
    archivo."""
    now = utcnow()
    active = [c for c in contacts if c.archived_at is None]
    for c in active:
        c.archived_at = now
    ids = [c.id for c in active]
    for i in range(0, len(ids), CHUNK):
        open_campaigns = select(Campaign.id).where(Campaign.status.not_in(("done", "cancelled")))
        for r, campaign in s.execute(
                select(CampaignContact, Campaign).join(Campaign, Campaign.id == CampaignContact.campaign_id).where(
                    CampaignContact.contact_id.in_(ids[i:i + CHUNK]),
                    CampaignContact.status.in_(("pending", "retry")), CampaignContact.campaign_id.in_(open_campaigns))):
            r.status = "skipped"
            r.error = {"message": "El contacto fue archivado", "reason": "contact_archived"}
            callbacks.enqueue(s, campaign, "contact.finished", r)
    s.flush()
    return len(active)


def archive_many(s: Session, client_id: str, contact_ids: list[str] | None = None,
                 tags: list[str] | None = None) -> int:
    """Archiva en lote, por ids o por etiquetas (los que tengan alguna). Cuantos archivo."""
    if not contact_ids and not tags:
        raise Invalid("Indicá contact_ids o tags")
    conditions = []
    if contact_ids:
        conditions.append(Contact.id.in_(contact_ids))
    try:
        conditions += [tag_filter(t) for t in tags or []]
    except ValueError as e:
        raise Invalid(str(e)) from None
    found = s.scalars(select(Contact).where(Contact.client_id == client_id, Contact.archived_at.is_(None),
                                            or_(*conditions)))
    return archive(s, list(found))


def unarchive(s: Session, contact: Contact) -> Contact:
    """Vuelve a activar un contacto, si el plan tiene lugar."""
    if contact.archived_at is None:
        return contact
    free = room(s, contact.client_id)
    if free is not None and free <= 0:
        raise QuotaExceeded("Llegaste al tope de contactos de tu plan: archivá alguno para desarchivar este.",
                            "contacts_limit")
    contact.archived_at = None
    s.flush()
    return contact


# --- Bajas ---

def _check_optout(channel: str, source: str | None = None) -> None:
    if channel not in OPTOUT_CHANNELS:
        raise Invalid(f"Canal inválido: {channel} (whatsapp, voice o all)")
    if source is not None and source not in OPTOUT_SOURCES:
        raise Invalid(f"Origen inválido: {source}")


def add_optout(s: Session, client_id: str, phone: str, channel: str, source: str) -> ContactOptout:
    """Pone el telefono (E.164) en la lista de no contactar del canal. Si ya estaba, no cambia."""
    _check_optout(channel, source)
    optout = s.get(ContactOptout, (client_id, phone, channel))
    if optout is None:
        optout = ContactOptout(client_id=client_id, phone=phone, channel=channel, source=source)
        s.add(optout)
        s.flush()
    return optout


def remove_optout(s: Session, client_id: str, phone: str, channel: str | None = None) -> int:
    """Saca el telefono de la lista: del canal indicado o, sin canal, de todos. NotFound si no estaba."""
    if channel is not None:
        _check_optout(channel)
    q = select(ContactOptout).where(ContactOptout.client_id == client_id, ContactOptout.phone == phone)
    if channel is not None:
        q = q.where(ContactOptout.channel == channel)
    rows = list(s.scalars(q))
    if not rows:
        raise NotFound("Ese número no está en la lista de bajas")
    for o in rows:
        s.delete(o)
    s.flush()
    return len(rows)


def list_optouts(s: Session, client_id: str | None, channel: str | None = None) -> list[ContactOptout]:
    q = select(ContactOptout).order_by(ContactOptout.created_at.desc(), ContactOptout.phone)
    if client_id is not None:
        q = q.where(ContactOptout.client_id == client_id)
    if channel is not None:
        _check_optout(channel)
        q = q.where(ContactOptout.channel == channel)
    return list(s.scalars(q))


def is_opted_out(s: Session, client_id: str, phone: str, channel: str) -> bool:
    """Si no hay que contactarlo por ese canal: su baja o la de todos."""
    return s.scalar(select(ContactOptout.phone).where(
        ContactOptout.client_id == client_id, ContactOptout.phone == phone,
        ContactOptout.channel.in_((channel, "all"))).limit(1)) is not None


def opted_out_phones(s: Session, client_id: str, channel: str) -> set[str]:
    """Los telefonos del cliente que no se pueden contactar por ese canal."""
    return set(s.scalars(select(ContactOptout.phone).where(
        ContactOptout.client_id == client_id, ContactOptout.channel.in_((channel, "all")))))
