"""Numeros bloqueados por cliente (services/blocked_numbers.py): sus llamadas entrantes se cortan
sin atender. El cliente ve y carga lo suyo; un admin indica `client_id`."""
from fastapi import APIRouter

from ...models import Client
from ...services import blocked_numbers
from ...services.errors import Invalid, NotFound
from ...services.security import Principal
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import BlockedNumberIn, BlockedNumberOut

router = APIRouter(prefix="/blocked-numbers", tags=["blocked-numbers"])


def _client_id(db, p: Principal, client_id: str | None) -> str:
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    if db.get(Client, cid) is None:
        raise NotFound("Cliente inexistente")
    return cid


def _phone(raw: str) -> str:
    phone = blocked_numbers.normalize(raw)
    if phone is None:
        raise Invalid(f"Teléfono inválido: {raw}")
    return phone


@router.get("", response_model=list[BlockedNumberOut])
def list_blocked(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    return blocked_numbers.list_blocked(db, scoped_client_id(p, client_id))


@router.post("", response_model=BlockedNumberOut, status_code=201)
def block(body: BlockedNumberIn, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Bloquea un teléfono: sus llamadas entrantes a los números del cliente (línea o WhatsApp) se
    cortan sin atender y quedan como rechazadas (`blocked_number`). Si ya estaba, actualiza la nota."""
    row = blocked_numbers.add(db, _client_id(db, p, client_id), _phone(body.phone), body.note.strip(),
                              created_by=p.id if p.kind == "user" else None)
    db.commit()
    return row


@router.delete("/{phone}", status_code=204)
def unblock(phone: str, p: CurrentPrincipal, db: DB, client_id: str | None = None):
    blocked_numbers.remove(db, _client_id(db, p, client_id), _phone(phone))
    db.commit()
