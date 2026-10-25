"""Conexiones de LLM del cliente (BYOK, docs/BYOK_LLM_PLAN.md; y el endpoint de "Tu propio agente",
docs/AGENTE_EXTERNO_PLAN.md). Las gestiona el cliente (las suyas, desde el panel, con una API key `calls` o por
el MCP) o un admin (las de cualquier cliente). La API key se guarda cifrada y nunca se devuelve."""
from fastapi import APIRouter

from ...services import llm_connections as svc
from ..deps import DB, CurrentPrincipal
from ..schemas import (
    LlmConnectionIn,
    LlmConnectionOut,
    LlmConnectionPatch,
    LlmConnectionTestIn,
)
from .clients import get_client

router = APIRouter(prefix="/clients/{client_id}/llm-connections", tags=["llm-connections"])


def _out(row, used: dict[str, int]) -> LlmConnectionOut:
    return LlmConnectionOut.model_validate(row).model_copy(update={"used_by": used.get(row.id, 0)})


@router.get("", response_model=list[LlmConnectionOut])
def list_connections(client_id: str, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    used = svc.used_by(db, client.id)
    return [_out(row, used) for row in svc.active(db, client.id)]


@router.post("", response_model=LlmConnectionOut, status_code=201)
def create_connection(client_id: str, body: LlmConnectionIn, p: CurrentPrincipal, db: DB):
    """Guarda la conexion. Probarla (`POST .../{id}/test`) detecta si el proveedor soporta salida JSON
    estricta y deja el resultado en la ficha."""
    client = get_client(db, p, client_id)
    row = svc.create(db, client.id, name=body.name, kind=body.kind, base_url=body.base_url,
                     api_key=body.api_key, default_model=body.default_model,
                     user_id=p.id if p.kind == "user" else None,
                     allow_private=p.is_admin)
    db.commit()
    return _out(row, {})


@router.patch("/{connection_id}", response_model=LlmConnectionOut)
def update_connection(client_id: str, connection_id: str, body: LlmConnectionPatch, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    row = svc.update(db, svc.get(db, client.id, connection_id), name=body.name, base_url=body.base_url,
                     api_key=body.api_key, default_model=body.default_model, allow_private=p.is_admin)
    db.commit()
    return _out(row, svc.used_by(db, client.id))


@router.post("/{connection_id}/test", response_model=LlmConnectionOut)
def test_connection(client_id: str, connection_id: str, body: LlmConnectionTestIn, p: CurrentPrincipal, db: DB):
    """Hace un pedido real al proveedor (cuenta contra la clave del cliente, unos pocos tokens)."""
    client = get_client(db, p, client_id)
    row = svc.test(db, svc.get(db, client.id, connection_id), body.model, body.mode)
    db.commit()
    return _out(row, svc.used_by(db, client.id))


@router.get("/{connection_id}/models", response_model=list[str])
def connection_models(client_id: str, connection_id: str, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    return svc.models(svc.get(db, client.id, connection_id))


@router.delete("/{connection_id}", status_code=204)
def revoke_connection(client_id: str, connection_id: str, p: CurrentPrincipal, db: DB):
    """Los agentes que la usan siguen con el servidor propio (si tienen fallback_local)."""
    client = get_client(db, p, client_id)
    svc.revoke(db, svc.get(db, client.id, connection_id))
    db.commit()
