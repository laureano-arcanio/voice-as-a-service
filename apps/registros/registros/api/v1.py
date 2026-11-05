"""Identificación por teléfono y cobro simulado (docs/API.md).

Las respuestas salen por modelos cerrados: lo que no está declarado no sale, porque va al prompt, al
whisper o a tool_runs. Nada de datos clínicos, DNI ni teléfono."""
import datetime
import re
import secrets

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..auth import Charger, DbSession, Reader
from ..config import settings
from ..db import new_id, tenant_get, utcnow
from ..models import RELATION_CONTACTO, Charge, ConversationChoice, Person, PersonPhone, RecordLink, Tenant
from ..phones import canonical_phone

router = APIRouter(prefix="/v1")

MAX_CANDIDATES = 5
REFS_TTL = datetime.timedelta(hours=24)
LINK_TTL = datetime.timedelta(days=30)
NO_NAME = "Sin nombre"

# Forma exacta de los ids de la plataforma. Otra forma es la prueba del panel: no cobra ni guarda nada.
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


class IdentifyIn(BaseModel):
    conversation_id: str = Field(max_length=255)
    # Nulo o vacío: caller oculto. No es un error de la herramienta.
    phone: str | None = Field(default=None, alias="from", max_length=64)


class SelectIn(IdentifyIn):
    ref: str = Field(max_length=200)


class IdentifyOut(BaseModel):
    status: str
    name: str | None = None
    al_dia: bool | None = None
    candidates: str | None = None
    record: str | None = None
    operator_note: str | None = None


class SelectOut(BaseModel):
    status: str
    name: str | None = None
    al_dia: bool | None = None
    record: str | None = None
    operator_note: str | None = None


class ChargeOut(BaseModel):
    charged: bool
    operator_message: str
    test: bool | None = None


def _conversation(raw: str) -> str | None:
    """El id normalizado, para que la misma conversación no cuente dos veces por mayúsculas."""
    return raw.lower() if _UUID.fullmatch(raw) else None


def _display(person: Person) -> str:
    return person.name or NO_NAME


def _standing(person: Person) -> str:
    return "al día" if person.al_dia else "no está al día"


def _label(person: Person) -> str:
    """Lo mínimo para que la persona reconozca la ficha: nombre e inicial del apellido."""
    parts = person.name.split()
    if not parts:
        return NO_NAME
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0].upper()}."


def _matches(s: Session, tenant_id: str, phone: str) -> list[tuple[Person, str]]:
    """Fichas activas del tenant con ese teléfono, en orden estable, con la relación del teléfono."""
    rows = s.execute(
        select(Person, PersonPhone.relation)
        .join(PersonPhone, PersonPhone.person_id == Person.id)
        .where(Person.tenant_id == tenant_id, PersonPhone.tenant_id == tenant_id, PersonPhone.phone == phone,
               Person.active.is_(True))
        .order_by(Person.name, Person.id)
    )
    return [(person, relation) for person, relation in rows]


def _choice(s: Session, tenant_id: str, conversation_id: str, lock: bool = False) -> ConversationChoice | None:
    stmt = select(ConversationChoice).where(ConversationChoice.tenant_id == tenant_id,
                                            ConversationChoice.conversation_id == conversation_id)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    return s.scalar(stmt)


def _link_url(s: Session, tenant_id: str, conversation_id: str, person_ids: list[str]) -> str:
    """El link de la conversación: una sola fila por conversación, también con pedidos simultáneos."""
    s.execute(insert(RecordLink).values(
        token=secrets.token_hex(16), tenant_id=tenant_id, conversation_id=conversation_id,
        person_ids=person_ids, expires_at=utcnow() + LINK_TTL,
    ).on_conflict_do_nothing(index_elements=["tenant_id", "conversation_id"]))
    link = s.scalar(select(RecordLink).where(RecordLink.tenant_id == tenant_id,
                                             RecordLink.conversation_id == conversation_id)
                    .with_for_update().execution_options(populate_existing=True))
    link.person_ids = person_ids
    return f"{settings.public_url.rstrip('/')}/c/{link.token}"


def _candidates(s: Session, tenant_id: str, conversation_id: str, phone: str, persons: list[Person]) -> str:
    """Guarda las refs de esta conversación y este teléfono. Repetir el pedido conserva las que ya había."""
    now = utcnow()
    s.execute(insert(ConversationChoice).values(
        tenant_id=tenant_id, conversation_id=conversation_id, from_phone=phone, refs={},
        expires_at=now + REFS_TTL,
    ).on_conflict_do_nothing(index_elements=["tenant_id", "conversation_id"]))
    row = _choice(s, tenant_id, conversation_id, lock=True)
    if row.from_phone != phone or row.expires_at <= now:
        row.from_phone, row.refs, row.person_id, row.expires_at = phone, {}, None, now + REFS_TTL
    known = {person_id: ref for ref, person_id in row.refs.items()}
    refs: dict[str, str] = {}
    for person in persons:
        ref = known.get(person.id)
        while ref is None or (ref in refs):
            ref = f"r_{secrets.token_hex(2)}"
        refs[ref] = person.id
    row.refs = refs
    labels = {person_id: ref for ref, person_id in refs.items()}
    return "; ".join(f"{_label(person)} ({labels[person.id]})" for person in persons)


@router.post("/identify", response_model=IdentifyOut)
def identify(body: IdentifyIn, caller: Reader, s: DbSession) -> IdentifyOut:
    conversation_id = _conversation(body.conversation_id)
    if conversation_id is None:
        return IdentifyOut(status="test")
    phone = canonical_phone(body.phone)
    if not phone:
        return IdentifyOut(status="no_number", record="Sin teléfono", operator_note="Sin teléfono")
    tenant_id = caller.tenant_id

    # Con una elección vigente, repetir el pedido no vuelve a abrir la lista.
    choice = _choice(s, tenant_id, conversation_id)
    if choice is not None and choice.person_id and choice.from_phone == phone:
        chosen = tenant_get(s, Person, tenant_id, choice.person_id)
        if chosen is not None and chosen.active:
            url = _link_url(s, tenant_id, conversation_id, [chosen.id])
            s.commit()
            return IdentifyOut(status="single", name=_display(chosen), al_dia=chosen.al_dia,
                               record=f"Ficha: {url}", operator_note=f"{_display(chosen)}, {_standing(chosen)}")

    matches = _matches(s, tenant_id, phone)
    if not matches:
        return IdentifyOut(status="none", record="Sin ficha", operator_note="Sin ficha")

    persons = [person for person, _ in matches]
    count = len(persons)
    # Siempre primero la elección y después el link, como en select: el orden evita un deadlock.
    candidates = _candidates(s, tenant_id, conversation_id, phone, persons) if 1 < count <= MAX_CANDIDATES else None
    url = _link_url(s, tenant_id, conversation_id, [person.id for person in persons])
    s.commit()
    if count == 1:
        person, relation = matches[0]
        if relation == RELATION_CONTACTO:
            name = f"Contacto de {_display(person)}"
            note = f"{name}, {_standing(person)}"
        else:
            name = _display(person)
            note = f"{name}, titular, {_standing(person)}"
        return IdentifyOut(status="single", name=name, al_dia=person.al_dia, record=f"Ficha: {url}",
                           operator_note=note)

    record = f"Este teléfono está en {count} fichas: {url}"
    if candidates is None:
        return IdentifyOut(status="too_many", record=record, operator_note=f"Teléfono en {count} fichas, sin identificar")
    return IdentifyOut(status="multiple", candidates=candidates, record=record,
                       operator_note=f"Teléfono en {count} fichas, sin elegir todavía")


@router.post("/identify/select", response_model=SelectOut)
def select_person(body: SelectIn, caller: Reader, s: DbSession) -> SelectOut:
    conversation_id = _conversation(body.conversation_id)
    if conversation_id is None:
        return SelectOut(status="test")
    tenant_id = caller.tenant_id
    phone = canonical_phone(body.phone)
    row = _choice(s, tenant_id, conversation_id, lock=True)
    if row is None or not phone or row.from_phone != phone or row.expires_at <= utcnow():
        s.commit()
        return SelectOut(status="invalid")
    person_id = row.refs.get(body.ref)
    person = tenant_get(s, Person, tenant_id, person_id) if person_id else None
    if person is None or not person.active:
        s.commit()
        return SelectOut(status="invalid")
    row.person_id = person.id
    url = _link_url(s, tenant_id, conversation_id, [person.id])
    s.commit()
    return SelectOut(status="selected", name=_display(person), al_dia=person.al_dia, record=f"Ficha: {url}",
                     operator_note=f"{_display(person)}, {_standing(person)}")


def _charge_message(person: Person, relation: str | None) -> str:
    message = f"Cobro registrado al titular {person.titular_name or person.name or NO_NAME}"
    if not person.al_dia:
        message += ", que no está al día"  # cobra igual y lo avisa
    if relation == RELATION_CONTACTO:
        message += ", por teléfono cargado como contacto"
    return message + "."


def _resolve(s: Session, tenant_id: str, conversation_id: str, phone: str) -> tuple[Person | None, str | None, str]:
    """(ficha a cobrar, relación del teléfono, motivo si no se cobra). Se calcula al final de la conversación:
    una elección hecha durante la llamada ya cuenta, aunque haya pasado el plazo de las refs."""
    if not phone:
        return None, None, "Sin ficha para este teléfono: no se cobró."
    matches = _matches(s, tenant_id, phone)
    choice = _choice(s, tenant_id, conversation_id)
    if choice is not None and choice.person_id and choice.from_phone == phone:
        person = tenant_get(s, Person, tenant_id, choice.person_id)
        if person is None or not person.active:
            # No se pasa a otra ficha del teléfono: la persona eligió esta.
            return None, None, "La ficha elegida está de baja: no se cobró."
        relation = next((relation for match, relation in matches if match.id == person.id), None)
        return person, relation, ""
    if not matches:
        return None, None, "Sin ficha para este teléfono: no se cobró."
    if len(matches) > 1:
        return None, None, f"Este teléfono está en {len(matches)} fichas y no se eligió ninguna: no se cobró."
    return matches[0][0], matches[0][1], ""


@router.post("/charges", response_model=ChargeOut, response_model_exclude_none=True)
def charge(body: IdentifyIn, caller: Charger, s: DbSession) -> ChargeOut:
    conversation_id = _conversation(body.conversation_id)
    if conversation_id is None:
        return ChargeOut(charged=False, test=True, operator_message="Prueba: no se cobró.")
    tenant_id = caller.tenant_id
    done = select(Charge.operator_message).where(Charge.tenant_id == tenant_id,
                                                 Charge.conversation_id == conversation_id)
    previous = s.scalar(done)
    if previous is not None:
        return ChargeOut(charged=True, operator_message=previous)

    phone = canonical_phone(body.phone)
    person, relation, refusal = _resolve(s, tenant_id, conversation_id, phone)
    if person is None:
        return ChargeOut(charged=False, operator_message=refusal)

    tenant = s.get(Tenant, tenant_id)
    message = _charge_message(person, relation)
    # Dos pedidos a la vez: el segundo espera al primero y, por la constraint, no inserta.
    s.execute(insert(Charge).values(
        id=new_id(), tenant_id=tenant_id, conversation_id=conversation_id, person_id=person.id,
        titular_name=person.titular_name or person.name or NO_NAME, amount=tenant.charge_amount,
        currency=tenant.currency, from_phone=phone, operator_message=message, created_at=utcnow(),
    ).on_conflict_do_nothing(index_elements=["tenant_id", "conversation_id"]))
    s.commit()
    return ChargeOut(charged=True, operator_message=s.scalar(done))
