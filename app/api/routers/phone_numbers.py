"""Inventario de numeros (los que provee Anura): carga, asignacion a clientes con
el tope del tier y ruteo a un agente del cliente.

- Admin: carga, asigna, libera, borra y rutea.
- Cliente (usuario o API key): ve sus numeros y elige que agente atiende cada uno.
Despues de cargar o borrar numeros: `make livekit-sip` (el trunk entrante los lista).
"""
from typing import Literal

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...mail import notify
from ...models import Agent, Client, PhoneNumber
from ...services import phone_numbers as service
from ...services.errors import Conflict, NotFound
from ..deps import DB, AdminPrincipal, CurrentPrincipal, scoped_client_id
from ..schemas import (
    AssignIn,
    PhoneNumberBulkIn,
    PhoneNumberBulkOut,
    PhoneNumberIn,
    PhoneNumberOut,
    PhoneNumberUpdate,
)
from .clients import get_client

router = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


def _out(db, n: PhoneNumber) -> PhoneNumberOut:
    agent = db.get(Agent, n.agent_id) if n.agent_id else None
    client = db.get(Client, n.client_id) if n.client_id else None
    return PhoneNumberOut.model_validate(n).model_copy(
        update={"agent_name": agent.name if agent else None, "client_name": client.name if client else None})


def _get(db, p, number_id: str) -> PhoneNumber:
    n = db.get(PhoneNumber, number_id)
    # Un numero libre solo lo ve el admin.
    if n is None or not p.can_access(n.client_id):
        raise NotFound("Número inexistente")
    return n


@router.get("", response_model=list[PhoneNumberOut])
def list_numbers(p: CurrentPrincipal, db: DB, client_id: str | None = None,
                 status: Literal["free", "assigned"] | None = None):
    """Admin: todo el inventario (status=free: libres). Cliente: los suyos."""
    q = select(PhoneNumber).order_by(PhoneNumber.e164)
    if cid := scoped_client_id(p, client_id):
        q = q.where(PhoneNumber.client_id == cid)
    if status == "free":
        q = q.where(PhoneNumber.client_id.is_(None))
    elif status == "assigned":
        q = q.where(PhoneNumber.client_id.is_not(None))
    return [_out(db, n) for n in db.scalars(q)]


@router.post("", response_model=PhoneNumberOut, status_code=201)
def create_number(body: PhoneNumberIn, p: AdminPrincipal, db: DB, background: BackgroundTasks):
    """Carga un numero; con client_id lo asigna (tope del tier) y con agent_id lo rutea.
    Asignado, avisa por mail a los usuarios del cliente."""
    if body.client_id:
        get_client(db, p, body.client_id)
    n = PhoneNumber(e164=body.e164, label=body.label, provider=body.provider)
    db.add(n)
    try:
        db.flush()
    except IntegrityError:
        raise Conflict(f"El número {body.e164} ya está cargado", "number_exists") from None
    if body.client_id:
        service.assign(db, n, body.client_id)
        service.set_agent(db, n, body.agent_id)
    db.commit()
    background.add_task(notify.deliver, notify.number_assigned_mails(db, n))
    return _out(db, n)


@router.post("/bulk", response_model=PhoneNumberBulkOut, status_code=201)
def load_numbers(body: PhoneNumberBulkIn, _: AdminPrincipal, db: DB):
    """Carga varios numeros libres al inventario; los repetidos o invalidos se informan en skipped."""
    result = service.load(db, body.numbers, body.label, body.provider)
    db.commit()
    return PhoneNumberBulkOut(created=[_out(db, n) for n in result.created], skipped=result.skipped)


@router.post("/{number_id}/assign", response_model=PhoneNumberOut)
def assign_number(number_id: str, body: AssignIn, p: AdminPrincipal, db: DB, background: BackgroundTasks):
    """Asigna un numero libre a un cliente y avisa por mail a sus usuarios.
    409 phone_numbers_limit si su tier no tiene lugar."""
    n = _get(db, p, number_id)
    get_client(db, p, body.client_id)
    was_there = n.client_id == body.client_id
    service.assign(db, n, body.client_id)
    db.commit()
    if not was_there:   # asignar de nuevo al mismo cliente no cambia nada: sin mail
        background.add_task(notify.deliver, notify.number_assigned_mails(db, n))
    return _out(db, n)


@router.post("/{number_id}/release", response_model=PhoneNumberOut)
def release_number(number_id: str, p: AdminPrincipal, db: DB):
    """Lo devuelve al inventario (sin cliente ni agente): sus entrantes dejan de atenderse."""
    n = _get(db, p, number_id)
    service.release(n)
    db.commit()
    return _out(db, n)


@router.patch("/{number_id}", response_model=PhoneNumberOut)
def update_number(number_id: str, body: PhoneNumberUpdate, p: CurrentPrincipal, db: DB):
    """Etiqueta y agente que atiende las entrantes (un agente del mismo cliente)."""
    n = _get(db, p, number_id)
    data = body.model_dump(exclude_unset=True)
    if "agent_id" in data:
        service.set_agent(db, n, data["agent_id"])
    if data.get("label") is not None:
        n.label = data["label"]
    db.commit()
    return _out(db, n)


@router.delete("/{number_id}", status_code=204)
def delete_number(number_id: str, p: AdminPrincipal, db: DB):
    """Solo libres: uno asignado se libera primero."""
    n = _get(db, p, number_id)
    if n.client_id is not None:
        raise Conflict("El número está asignado a un cliente: liberalo antes de borrarlo", "number_assigned")
    db.delete(n)
    db.commit()
