from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ...config import settings
from ...models import Client, Tier
from ...services import phone_numbers
from ...services.errors import Conflict, Invalid, NotFound
from ..deps import DB, AdminPrincipal
from ..schemas import TierIn, TierOut, TierUpdate

router = APIRouter(prefix="/tiers", tags=["tiers"])


def _out(db, tier: Tier) -> TierOut:
    count = db.scalar(select(func.count()).select_from(Client).where(Client.tier_id == tier.id)) or 0
    return TierOut.model_validate(tier).model_copy(update={"clients_count": count})


def _check_duration(seconds: int | None) -> None:
    """Mas que el tope duro de SIP/Asterisk no se cumpliria: la llamada se corta ahi igual."""
    if seconds is not None and seconds > settings.call_duration_ceiling_seconds:
        raise Invalid(f"La duración máxima no puede pasar de {settings.call_duration_ceiling_seconds} s "
                      "(CALL_DURATION_CEILING_SECONDS)", "invalid_max_call_duration")


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
    _check_duration(body.max_call_duration_seconds)
    tier = Tier(**body.model_dump())
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
    """Solo los campos enviados; un limite en null lo deja ilimitado (la duracion vuelve a
    CALL_MAX_DURATION_SECONDS; la retencion, sin borrado). Aplica desde ya al mes en curso."""
    tier = _get(db, tier_id)
    _check_duration(body.max_call_duration_seconds)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is None and k in ("name", "description"):
            continue    # no son nulables: null = no cambiar
        setattr(tier, k, v)
    if tier.max_phone_numbers is not None:
        for client in db.scalars(select(Client).where(Client.tier_id == tier.id)):
            phone_numbers.check_tier_fits(db, client, tier)
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
