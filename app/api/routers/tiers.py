from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ...models import Client, Tier
from ...services import limits, phone_numbers
from ...services.errors import Conflict, NotFound
from ..deps import DB, AdminPrincipal
from ..schemas import TierIn, TierOut, TierUpdate

router = APIRouter(prefix="/tiers", tags=["tiers"])


def _out(db, tier: Tier) -> TierOut:
    count = db.scalar(select(func.count()).select_from(Client).where(Client.tier_id == tier.id)) or 0
    return TierOut.model_validate(tier).model_copy(update={"clients_count": count})


def _get(db, tier_id: str) -> Tier:
    tier = db.get(Tier, tier_id)
    if tier is None:
        raise NotFound("Tier inexistente")
    return tier


@router.get("", response_model=list[TierOut])
def list_tiers(_: AdminPrincipal, db: DB):
    return [_out(db, t) for t in db.scalars(select(Tier).order_by(Tier.name))]


@router.post("", response_model=TierOut, status_code=201)
def create_tier(body: TierIn, _: AdminPrincipal, db: DB):
    data = body.model_dump()
    data["campaign_channels"] = list(dict.fromkeys(data["campaign_channels"]))
    tier = Tier(**data)
    db.add(tier)
    try:
        db.commit()
    except IntegrityError:
        raise Conflict(f"Ya existe un tier {body.name!r}") from None
    return _out(db, tier)


@router.get("/{tier_id}", response_model=TierOut)
def get_tier(tier_id: str, _: AdminPrincipal, db: DB):
    return _out(db, _get(db, tier_id))


@router.patch("/{tier_id}", response_model=TierOut)
def update_tier(tier_id: str, body: TierUpdate, _: AdminPrincipal, db: DB):
    """Solo los campos enviados; un limite en null lo deja ilimitado. Aplica desde ya
    al mes en curso."""
    tier = _get(db, tier_id)
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        if v is None and k in ("name", "description", "campaign_channels", "campaign_followup"):
            continue    # no son nulables: null = no cambiar
        if k == "campaign_channels":
            v = list(dict.fromkeys(v))
        setattr(tier, k, v)
    if tier.max_phone_numbers is not None:
        for client in db.scalars(select(Client).where(Client.tier_id == tier.id)):
            phone_numbers.check_tier_fits(db, client, tier)
    if "campaign_channels" in changes:      # las campañas de un canal que el plan ya no incluye se pausan
        for client in db.scalars(select(Client).where(Client.tier_id == tier.id)):
            limits.pause_campaigns_outside_plan(db, client, limits.effective_limits(db, client))
    try:
        db.commit()
    except IntegrityError:
        raise Conflict("Ya existe un tier con ese nombre") from None
    return _out(db, tier)


@router.delete("/{tier_id}", status_code=204)
def delete_tier(tier_id: str, _: AdminPrincipal, db: DB):
    tier = _get(db, tier_id)
    if db.scalar(select(func.count()).select_from(Client).where(Client.tier_id == tier.id)):
        raise Conflict("El tier tiene clientes asignados", "tier_in_use")
    db.delete(tier)
    db.commit()
