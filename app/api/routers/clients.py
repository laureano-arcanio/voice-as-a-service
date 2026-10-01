from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ...models import Agent, Client, ConversationRow, PhoneNumber, Tier, WaAccount
from ...services import phone_numbers, quota
from ...services.errors import Conflict, Invalid, NotFound
from ..deps import DB, AdminPrincipal, CurrentPrincipal
from ..schemas import (
    ClientIn,
    ClientOut,
    ClientUpdate,
    MinutesUsageOut,
    NumbersUsageOut,
    UsageOut,
)

router = APIRouter(prefix="/clients", tags=["clients"])


def _out(db, client: Client) -> ClientOut:
    agents = db.scalar(select(func.count()).select_from(Agent).where(
        Agent.client_id == client.id, Agent.archived_at.is_(None))) or 0
    numbers = db.scalar(select(func.count()).select_from(PhoneNumber).where(PhoneNumber.client_id == client.id)) or 0
    return ClientOut.model_validate(client).model_copy(update={"agents_count": agents, "numbers_count": numbers})


def get_client(db, p, client_id: str) -> Client:
    """El cliente si existe y quien pide puede verlo (si no, 404: no se revela que existe)."""
    client = db.get(Client, client_id)
    if client is None or not p.can_access(client.id):
        raise NotFound("Cliente inexistente")
    return client


def _tier(db, tier_id: str) -> Tier:
    tier = db.get(Tier, tier_id)
    if tier is None:
        raise Invalid("Tier inexistente", "invalid_tier")
    return tier


@router.get("", response_model=list[ClientOut])
def list_clients(p: CurrentPrincipal, db: DB):
    """Admin: todos. Usuario de un cliente: el suyo."""
    q = select(Client).order_by(Client.name)
    if not p.is_admin:
        q = q.where(Client.id == p.client_id)
    return [_out(db, c) for c in db.scalars(q)]


@router.post("", response_model=ClientOut, status_code=201)
def create_client(body: ClientIn, _: AdminPrincipal, db: DB):
    _tier(db, body.tier_id)
    client = Client(**body.model_dump())
    db.add(client)
    try:
        db.commit()
    except IntegrityError:
        raise Conflict(f"Ya existe un cliente {body.slug!r}") from None
    return _out(db, client)


@router.get("/{client_id}", response_model=ClientOut)
def read_client(client_id: str, p: CurrentPrincipal, db: DB):
    return _out(db, get_client(db, p, client_id))


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: str, body: ClientUpdate, p: AdminPrincipal, db: DB):
    client = get_client(db, p, client_id)
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if "tier_id" in data:
        tier = _tier(db, data.pop("tier_id"))
        phone_numbers.check_tier_fits(db, client, tier)
        client.tier = tier
    for k, v in data.items():
        setattr(client, k, v)
    db.commit()
    return _out(db, client)


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: str, p: AdminPrincipal, db: DB):
    """Solo sin conversaciones; con historial, desactivarlo (active=false)."""
    client = get_client(db, p, client_id)
    if db.scalar(select(func.count()).select_from(ConversationRow).where(ConversationRow.client_id == client.id)):
        raise Conflict("El cliente tiene conversaciones: desactivalo en vez de borrarlo", "client_in_use")
    # wa_accounts.client_id es RESTRICT: sin esto, IntegrityError (500) en PostgreSQL.
    if db.scalar(select(func.count()).select_from(WaAccount).where(WaAccount.client_id == client.id)):
        raise Conflict("El cliente tiene números de WhatsApp conectados: desactivalo en vez de borrarlo",
                       "client_in_use")
    db.delete(client)
    db.commit()


def _minutes(m: quota.MinutesUsage) -> MinutesUsageOut:
    used = round(m.used_seconds / 60, 1)
    remaining = None if m.limit_minutes is None else round(max(m.limit_minutes * 60 - m.used_seconds, 0) / 60, 1)
    return MinutesUsageOut(used_seconds=m.used_seconds, used_minutes=used, limit_minutes=m.limit_minutes,
                           remaining_minutes=remaining)


@router.get("/{client_id}/usage", response_model=UsageOut)
def client_usage(client_id: str, p: CurrentPrincipal, db: DB,
                 month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
                                           description="YYYY-MM; sin el, el mes en curso")):
    """Consumo del mes contra los limites del tier."""
    client = get_client(db, p, client_id)
    u = quota.usage(db, client, month)
    return UsageOut(month=u.month, period_start=u.period_start, period_end=u.period_end,
                    active_calls=u.active_calls, max_concurrent_calls=u.max_concurrent_calls,
                    inbound=_minutes(u.inbound), outbound=_minutes(u.outbound),
                    phone_numbers=NumbersUsageOut(used=phone_numbers.numbers_count(db, client.id),
                                                  limit=client.tier.max_phone_numbers))
