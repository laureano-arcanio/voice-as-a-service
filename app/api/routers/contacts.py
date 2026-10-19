"""Agenda de contactos del cliente y bajas (docs/LLAMADAS_SALIENTES_PLAN.md, secciones 3 y 7;
la logica, en services/contacts.py).

- El cliente ve y carga lo suyo (usuario o API key); un admin indica `client_id`.
- Cargar es un upsert por telefono (uno, una lista o un CSV). Un contacto archivado que se vuelve
  a cargar se actualiza pero sigue archivado (`archived` en la respuesta).
- No hay DELETE: se archiva y se desarchiva.
- Bajas: por telefono y canal (whatsapp, voice o all); reemplazan a /whatsapp/optouts.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...models import Campaign, CampaignContact, Client, Contact
from ...services import contacts, phones
from ...services.errors import Conflict, Invalid, NotFound, QuotaExceeded
from ...services.security import Principal
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import (
    ContactCampaignOut,
    ContactImportIn,
    ContactIn,
    ContactOptoutIn,
    ContactOptoutOut,
    ContactOut,
    ContactPage,
    ContactPatch,
    ContactRejected,
    ContactsArchiveIn,
    ContactsArchiveOut,
    ContactsUpsertOut,
    OptoutChannel,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])
MAX_BATCH = 10_000


def _client_id(db, p: Principal, client_id: str | None) -> str:
    """El cliente sobre el que se escribe: el del que pide, o el que indique un admin."""
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    if db.get(Client, cid) is None:
        raise NotFound("Cliente inexistente")
    return cid


def _get(db, contact_id: str, p: Principal) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None or not p.can_access(contact.client_id):
        raise NotFound("Contacto inexistente")
    return contact


def _phone(raw: str) -> str:
    try:
        return phones.normalize_phone(raw)
    except ValueError as e:
        raise Invalid(f"Teléfono inválido: {e}") from None


def _commit(db) -> None:
    try:
        db.commit()
    except IntegrityError:      # otro pedido cargo el mismo telefono a la vez
        db.rollback()
        raise Conflict("Otro pedido cargó el mismo contacto al mismo tiempo: probá de nuevo",
                       "contact_conflict") from None


def _upsert_out(result: contacts.UpsertResult) -> ContactsUpsertOut:
    return ContactsUpsertOut(
        created=len(result.created), updated=len(result.updated), archived=len(result.archived),
        invalid=[ContactRejected(phone=x.phone, reason=x.reason, line=x.line) for x in result.invalid],
        contacts=[ContactOut.model_validate(c) for c in [*result.created, *result.updated]])


@router.get("", response_model=ContactPage)
def list_contacts(p: CurrentPrincipal, db: DB, client_id: str | None = None,
                  q: str | None = Query(default=None, max_length=100, description="Busca en nombre, telefono, email e id externo"),
                  tag: str | None = Query(default=None, max_length=32),
                  archived: Literal["false", "true", "all"] = Query(default="false", description="false: activos; true: archivados; all: todos"),
                  offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=500)):
    rows, total = contacts.list_contacts(db, scoped_client_id(p, client_id), q=q, tag=tag, archived=archived,
                                         offset=offset, limit=limit)
    return ContactPage(items=[ContactOut.model_validate(c) for c in rows], total=total)


@router.post("", response_model=ContactsUpsertOut, status_code=201)
def upsert_contacts(body: ContactIn | list[ContactIn], p: CurrentPrincipal, db: DB, response: Response,
                    client_id: str | None = None):
    """Carga un contacto o una lista (upsert por telefono): los nuevos se crean y los que ya
    existen se actualizan, sumando atributos y etiquetas. Las filas invalidas o que no entran por
    el tope del plan vuelven en `invalid`; con un solo contacto, eso es un error. Los archivados
    se actualizan pero siguen archivados (`archived`)."""
    cid = _client_id(db, p, client_id)
    single = isinstance(body, ContactIn)
    rows = [body] if single else body
    if not rows or len(rows) > MAX_BATCH:
        raise Invalid(f"La lista va de 1 a {MAX_BATCH} contactos")
    result = contacts.upsert(db, cid, [contacts.ContactRow(**r.model_dump()) for r in rows], source="api")
    if single and result.invalid:
        db.rollback()
        reason = result.invalid[0].reason
        if result.limit_hit:
            raise QuotaExceeded("Llegaste al tope de contactos de tu plan.", "contacts_limit")
        raise Invalid(f"Contacto inválido: {reason}")
    _commit(db)
    if not result.created:
        response.status_code = 200
    return _upsert_out(result)


@router.post("/import", response_model=ContactsUpsertOut)
def import_contacts(body: ContactImportIn, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Carga un CSV (upsert por telefono). Devuelve creados, actualizados e invalidos con su fila y
    el motivo."""
    cid = _client_id(db, p, client_id)
    result = contacts.import_csv(db, cid, body.csv, body.tags)
    _commit(db)
    return _upsert_out(result)


@router.post("/archive", response_model=ContactsArchiveOut)
def archive_contacts(body: ContactsArchiveIn, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Archiva en lote, por ids o por etiquetas. Sus intentos pendientes en campañas abiertas
    pasan a salteados."""
    cid = _client_id(db, p, client_id)
    n = contacts.archive_many(db, cid, body.contact_ids, body.tags)
    db.commit()
    return ContactsArchiveOut(archived=n)


# --- Bajas (antes que /{contact_id}) ---

def _optout_out(o) -> ContactOptoutOut:
    return ContactOptoutOut(client_id=o.client_id, phone=o.phone, channel=o.channel, source=o.source,
                            created_at=o.created_at)


@router.get("/optouts", response_model=list[ContactOptoutOut])
def list_optouts(p: CurrentPrincipal, db: DB, client_id: str | None = None, channel: OptoutChannel | None = None):
    return [_optout_out(o) for o in contacts.list_optouts(db, scoped_client_id(p, client_id), channel)]


@router.post("/optouts", response_model=ContactOptoutOut, status_code=201)
def add_optout(body: ContactOptoutIn, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Pone un telefono en la lista de no contactar de un canal (o de todos). Ninguna campaña de
    ese canal le escribe ni lo llama."""
    cid = _client_id(db, p, client_id)
    o = contacts.add_optout(db, cid, _phone(body.phone), body.channel, "manual")
    db.commit()
    return _optout_out(o)


@router.delete("/optouts/{phone}", status_code=204)
def remove_optout(phone: str, p: CurrentPrincipal, db: DB, client_id: str | None = None,
                  channel: Annotated[OptoutChannel | None, Query(description="Sin canal, de todos")] = None):
    """Saca un telefono de la lista de bajas, del canal indicado o de todos."""
    cid = _client_id(db, p, client_id)
    contacts.remove_optout(db, cid, _phone(phone), channel)
    db.commit()


# --- Un contacto ---

@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: str, p: CurrentPrincipal, db: DB):
    return _get(db, contact_id, p)


@router.get("/{contact_id}/campaigns", response_model=list[ContactCampaignOut])
def contact_campaigns(contact_id: str, p: CurrentPrincipal, db: DB):
    """Las campañas en las que está el contacto, las más nuevas primero, con su resultado en cada una."""
    contact = _get(db, contact_id, p)
    rows = db.execute(select(CampaignContact, Campaign).join(Campaign, Campaign.id == CampaignContact.campaign_id)
                      .where(CampaignContact.contact_id == contact.id)
                      .order_by(Campaign.created_at.desc(), Campaign.id)).all()
    return [ContactCampaignOut(
        campaign_id=c.id, campaign_name=c.name, channel=c.channel, campaign_status=c.status, status=r.status,
        result=r.result, attempts=r.attempts, last_attempt_at=r.last_attempt_at, sent_at=r.sent_at,
        conversation_id=r.conversation_id) for r, c in rows]


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: str, body: ContactPatch, p: CurrentPrincipal, db: DB):
    """Edita datos y etiquetas (los atributos y las etiquetas reemplazan a los anteriores). El
    telefono no se cambia: otro telefono es otro contacto."""
    contact = _get(db, contact_id, p)
    contacts.update_contact(db, contact, **body.model_dump(exclude_unset=True))
    db.commit()
    return contact


@router.post("/{contact_id}/archive", response_model=ContactOut)
def archive_contact(contact_id: str, p: CurrentPrincipal, db: DB):
    """Archiva el contacto (no se borra). Sus intentos pendientes en campañas abiertas pasan a salteados."""
    contact = _get(db, contact_id, p)
    contacts.archive(db, [contact])
    db.commit()
    return contact


@router.post("/{contact_id}/unarchive", response_model=ContactOut)
def unarchive_contact(contact_id: str, p: CurrentPrincipal, db: DB):
    """Vuelve a activar un contacto archivado, si el tope de contactos del plan tiene lugar (429)."""
    contact = _get(db, contact_id, p)
    contacts.unarchive(db, contact)
    db.commit()
    return contact
