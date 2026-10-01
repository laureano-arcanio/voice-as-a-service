"""Numeros de WhatsApp conectados (wa_accounts): cada uno lo atiende un agente del cliente.

Solo admin. No hay DELETE (las conversaciones le hacen RESTRICT): se desactiva.
El token de la cuenta nunca sale en una respuesta (solo has_token).
Flujo de mensajes: app/whatsapp/service.py; plan en docs/WHATSAPP_PLAN.md.
"""
from fastapi import APIRouter

from ...models import Agent, Client, WaAccount
from ...services.errors import NotFound
from ...whatsapp import store
from ..deps import DB, AdminPrincipal
from ..schemas import WaAccountIn, WaAccountOut, WaAccountPatch

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _out(db, a: WaAccount) -> WaAccountOut:
    agent = db.get(Agent, a.agent_id)
    client = db.get(Client, a.client_id)
    return WaAccountOut(
        id=a.id, client_id=a.client_id, client_name=client.name if client else None, agent_id=a.agent_id,
        agent_name=agent.name if agent else None, phone_number_id=a.phone_number_id, waba_id=a.waba_id,
        display_phone_number=a.display_phone_number, name=a.name, has_token=bool(a.access_token),
        active=a.active, created_at=a.created_at, updated_at=a.updated_at)


def _get(db, account_id: str) -> WaAccount:
    a = store.get_account(db, account_id)
    if a is None:
        raise NotFound("Cuenta de WhatsApp inexistente")
    return a


@router.get("/accounts", response_model=list[WaAccountOut])
def list_accounts(_: AdminPrincipal, db: DB, client_id: str | None = None):
    return [_out(db, a) for a in store.list_accounts(db, client_id)]


@router.post("/accounts", response_model=WaAccountOut, status_code=201)
def create_account(body: WaAccountIn, _: AdminPrincipal, db: DB):
    """Conecta un numero: 409 si el phone_number_id ya esta, 404 si el agente no es del cliente."""
    a = store.create_account(db, **body.model_dump())
    db.commit()
    return _out(db, a)


@router.patch("/accounts/{account_id}", response_model=WaAccountOut)
def update_account(account_id: str, body: WaAccountPatch, _: AdminPrincipal, db: DB):
    """access_token "" o null lo borra (vuelve a WA_ACCESS_TOKEN)."""
    a = _get(db, account_id)
    changes = body.model_dump(exclude_unset=True)
    # Columnas NOT NULL: null es "sin cambio". El token si se puede borrar.
    changes = {k: v for k, v in changes.items() if v is not None or k == "access_token"}
    store.update_account(db, a, **changes)
    db.commit()
    return _out(db, a)


@router.post("/accounts/{account_id}/deactivate", response_model=WaAccountOut)
def deactivate_account(account_id: str, _: AdminPrincipal, db: DB):
    """Deja de responder los mensajes que lleguen a ese numero (quedan ignored)."""
    a = _get(db, account_id)
    store.update_account(db, a, active=False)
    db.commit()
    return _out(db, a)
