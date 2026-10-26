"""Pedidos de los botones de arrepentimiento y de baja (services/legal.py), para el admin: verlos y marcarlos
resueltos. El pedido entra por POST /demo/consumer-requests."""
from fastapi import APIRouter

from ...services import legal
from ..deps import DB, AdminPrincipal
from ..schemas import ConsumerRequestOut, ConsumerRequestPatch, ConsumerRequestStatus

router = APIRouter(prefix="/consumer-requests", tags=["consumer-requests"])


@router.get("", response_model=list[ConsumerRequestOut])
def list_requests(_: AdminPrincipal, db: DB, status: ConsumerRequestStatus | None = None):
    """Los ultimos 100, los mas nuevos primero."""
    return legal.list_requests(db, status)


@router.patch("/{request_id}", response_model=ConsumerRequestOut)
def resolve(request_id: str, body: ConsumerRequestPatch, _: AdminPrincipal, db: DB):
    """Marca el pedido como hecho o rechazado, con lo que se hizo."""
    return legal.resolve_request(db, request_id, body.status, body.resolution)
