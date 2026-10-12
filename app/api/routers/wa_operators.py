"""Operadores de WhatsApp (docs/APPS_PLAN.md): el dueño de un negocio que le habla a su
asistente por un numero compartido. Sus mensajes los atiende el agente del operador, del cliente
del operador, no el agente del numero. Solo admin."""
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...models import Agent, Client, WaAccount, WaOperator
from ...services.errors import Conflict, Invalid, NotFound
from ..deps import DB, AdminPrincipal
from ..schemas import WaOperatorIn, WaOperatorOut, WaOperatorUpdate
from .clients import get_client

router = APIRouter(prefix="/wa-operators", tags=["whatsapp"])


def _out(db, op: WaOperator) -> WaOperatorOut:
    account, client, agent = db.get(WaAccount, op.account_id), db.get(Client, op.client_id), db.get(Agent, op.agent_id)
    return WaOperatorOut.model_validate(op).model_copy(update={
        "account_number": account.display_phone_number if account else None,
        "client_name": client.name if client else None, "agent_name": agent.name if agent else None})


def _agent(db, client_id: str, agent_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.client_id != client_id:
        raise Invalid("El agente no es de ese cliente")
    if agent.archived_at is not None:
        raise Invalid("El agente está archivado")
    return agent


def _get(db, op_id: str) -> WaOperator:
    op = db.get(WaOperator, op_id)
    if op is None:
        raise NotFound("Operador inexistente")
    return op


@router.get("", response_model=list[WaOperatorOut])
def list_operators(_: AdminPrincipal, db: DB, client_id: str | None = None):
    q = select(WaOperator).order_by(WaOperator.created_at)
    if client_id:
        q = q.where(WaOperator.client_id == client_id)
    return [_out(db, op) for op in db.scalars(q)]


@router.post("", response_model=WaOperatorOut, status_code=201)
def create_operator(body: WaOperatorIn, p: AdminPrincipal, db: DB):
    if db.get(WaAccount, body.account_id) is None:
        raise NotFound("Número de WhatsApp inexistente")
    get_client(db, p, body.client_id)
    _agent(db, body.client_id, body.agent_id)
    op = WaOperator(**body.model_dump())
    db.add(op)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Ese contacto ya es operador de ese número", "operator_exists") from None
    return _out(db, op)


@router.patch("/{op_id}", response_model=WaOperatorOut)
def update_operator(op_id: str, body: WaOperatorUpdate, _: AdminPrincipal, db: DB):
    op = _get(db, op_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("agent_id"):
        op.agent_id = _agent(db, op.client_id, data["agent_id"]).id
    if data.get("name") is not None:
        op.name = data["name"]
    if data.get("active") is not None:
        op.active = data["active"]
    db.commit()
    return _out(db, op)


@router.delete("/{op_id}", status_code=204)
def delete_operator(op_id: str, _: AdminPrincipal, db: DB):
    db.delete(_get(db, op_id))
    db.commit()
