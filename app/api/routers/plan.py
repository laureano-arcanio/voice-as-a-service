"""Lo que incluye el plan del cliente, para que la UI bloquee con el motivo lo que no
(docs/ARQUITECTURA.md)."""
from fastapi import APIRouter

from ...models import Client
from ...services import features
from ...services.errors import Invalid, NotFound
from ..deps import DB, CurrentPrincipal, scoped_client_id
from ..schemas import PlanFeaturesOut

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/features", response_model=PlanFeaturesOut)
def plan_features(p: CurrentPrincipal, db: DB, client_id: str | None = None):
    """Cada funcion con `enabled` y, si no esta, `reason` (lo que hace falta). `free`: el plan es gratis.
    Un admin indica `client_id`."""
    cid = scoped_client_id(p, client_id)
    if cid is None:
        raise Invalid("Indicá client_id")
    client = db.get(Client, cid)
    if client is None:
        raise NotFound("Cliente inexistente")
    return features.plan_features(db, client)
