"""Plan y cobro (docs/SUSCRIPCIONES_PLAN.md): la pantalla Plan del cliente, el registro de pagos por
transferencia (admin) y la vista Cobros."""
from fastapi import APIRouter, Query
from sqlalchemy import select

from ...billing import service
from ...config import settings
from ...db import utcnow
from ...mail import messages, notify
from ...models import BillingPayment, Client, PhoneNumber, Subscription, Tier, User
from ...services.errors import NotFound
from ..deps import DB, AdminPrincipal, UserPrincipal
from ..schemas import (
    BankRow,
    BillingOut,
    FiscalIn,
    FiscalOut,
    PaymentIn,
    PaymentOut,
    PaymentPatch,
    PlanOut,
    SubscribeIn,
    SubscriptionOut,
    SubscriptionRowOut,
    TierBrief,
)
from .clients import get_client

router = APIRouter(tags=["billing"])


def _brief(db, tier_id: str | None) -> TierBrief | None:
    tier = db.get(Tier, tier_id) if tier_id else None
    return TierBrief.model_validate(tier) if tier else None


def _subscription(db, sub: Subscription) -> dict:
    return dict(id=sub.id, tier=_brief(db, sub.tier_id), pending_tier=_brief(db, sub.pending_tier_id),
                method=sub.method, status=sub.status, current_period_end=sub.current_period_end,
                grace_until=sub.grace_until, cancel_at_period_end=sub.cancel_at_period_end,
                amount_due=service.amount_due(db, sub), created_at=sub.created_at)


def _payments(db, q) -> list[PaymentOut]:
    rows = list(db.scalars(q))
    clients = {c.id: c for c in db.scalars(select(Client).where(Client.id.in_({r.client_id for r in rows})))}
    tiers = dict(db.execute(select(Tier.id, Tier.name).where(Tier.id.in_({r.tier_id for r in rows if r.tier_id}))).all())
    emails = dict(db.execute(select(User.id, User.email).where(
        User.id.in_({r.recorded_by for r in rows if r.recorded_by}))).all())
    out = []
    for r in rows:
        c = clients.get(r.client_id)
        out.append(PaymentOut(
            id=r.id, client_id=r.client_id, client_name=c.name if c else "", tier_name=tiers.get(r.tier_id),
            method=r.method, status=r.status, amount_ars=r.amount_ars, paid_on=r.paid_on, period_end=r.period_end,
            note=r.note, invoiced_at=r.invoiced_at, recorded_by_email=emails.get(r.recorded_by),
            legal_name=c.legal_name if c else "", tax_id=c.tax_id if c else "",
            tax_condition=c.tax_condition if c else ""))
    return out


def _billing(db, client: Client) -> BillingOut:
    sub = service.current(db, client.id)
    suspended = db.scalars(select(PhoneNumber.e164).where(PhoneNumber.client_id == client.id,
                                                          PhoneNumber.suspended_at.is_not(None)))
    return BillingOut(
        tier=TierBrief.model_validate(client.tier), tier_price_ars=client.tier.price_ars,
        subscription=SubscriptionOut(**_subscription(db, sub)) if sub else None,
        plans=[PlanOut.model_validate(t) for t in service.public_tiers(db) if t.price_ars],
        methods=list(service.METHODS),
        fiscal=FiscalOut(legal_name=client.legal_name, tax_id=client.tax_id, tax_condition=client.tax_condition),
        bank=[BankRow(label=label, value=value) for label, value in messages.bank_rows()],
        support_email=settings.support_email,
        payments=_payments(db, select(BillingPayment).where(BillingPayment.client_id == client.id)
                           .order_by(BillingPayment.paid_on.desc(), BillingPayment.created_at.desc()).limit(24)),
        suspended_numbers=list(suspended))


# ---------- pantalla Plan (cliente; un admin tambien la ve) ----------

@router.get("/clients/{client_id}/billing", response_model=BillingOut)
def read_billing(client_id: str, p: UserPrincipal, db: DB):
    """Plan actual, suscripcion, planes que se pueden contratar, datos fiscales y pagos."""
    return _billing(db, get_client(db, p, client_id))


@router.post("/clients/{client_id}/billing/subscribe", response_model=BillingOut)
def subscribe(client_id: str, body: SubscribeIn, p: UserPrincipal, db: DB):
    """Pide un plan pago. Por transferencia: queda pendiente hasta que se registra el pago, y al
    usuario le llega un mail con los datos bancarios. Con un plan activo, el pedido se aplica al
    registrar el proximo pago."""
    client = get_client(db, p, client_id)
    user = db.get(User, p.id) if not p.is_admin else None
    sub = service.request_plan(db, client, body.tier_id, body.method, user)
    mails = service.request_mails(db, client, sub, user)
    db.commit()
    notify.deliver(mails)
    return _billing(db, client)


@router.post("/clients/{client_id}/billing/cancel", response_model=BillingOut)
def cancel(client_id: str, p: UserPrincipal, db: DB):
    """Da de baja el plan pago: sigue hasta el fin del periodo pagado y despues pasa al gratuito."""
    client = get_client(db, p, client_id)
    service.cancel(db, client)
    db.commit()
    return _billing(db, client)


@router.put("/clients/{client_id}/billing/fiscal", response_model=BillingOut)
def update_fiscal(client_id: str, body: FiscalIn, p: UserPrincipal, db: DB):
    """Datos para la factura."""
    client = get_client(db, p, client_id)
    service.update_fiscal(client, body.legal_name, body.tax_id, body.tax_condition)
    db.commit()
    return _billing(db, client)


# ---------- admin ----------

@router.post("/clients/{client_id}/billing/payments", response_model=BillingOut, status_code=201)
def record_payment(client_id: str, body: PaymentIn, p: AdminPrincipal, db: DB):
    """Registra un pago por transferencia: activa el plan, o lo renueva, por un mes desde el
    vencimiento actual (o desde hoy). Al cliente le llega un mail."""
    client = get_client(db, p, client_id)
    _, mails = service.record_payment(db, client, tier_id=body.tier_id, amount_ars=body.amount_ars,
                                      paid_on=body.paid_on, note=body.note,
                                      admin_id=p.id if p.kind == "user" else None)
    db.commit()
    notify.deliver(mails)
    return _billing(db, client)


@router.post("/clients/{client_id}/billing/suspend", response_model=BillingOut)
def suspend(client_id: str, p: AdminPrincipal, db: DB):
    """Rechaza un pedido pendiente, o corta el plan pago ya: el cliente pasa al gratuito."""
    client = get_client(db, p, client_id)
    mails = service.suspend(db, client)
    db.commit()
    notify.deliver(mails)
    return _billing(db, client)


@router.get("/billing/subscriptions", response_model=list[SubscriptionRowOut])
def list_subscriptions(_: AdminPrincipal, db: DB):
    """Suscripciones abiertas (pendientes, activas y vencidas), las que vencen antes primero."""
    subs = list(db.scalars(select(Subscription).where(Subscription.status.in_(service.OPEN_STATUSES))))
    names = dict(db.execute(select(Client.id, Client.name).where(Client.id.in_({s.client_id for s in subs}))).all())
    subs.sort(key=lambda s: (s.status != "pending", s.current_period_end or s.created_at.date()))
    return [SubscriptionRowOut(**_subscription(db, s), client_id=s.client_id, client_name=names.get(s.client_id, ""))
            for s in subs]


@router.get("/billing/payments", response_model=list[PaymentOut])
def list_payments(_: AdminPrincipal, db: DB,
                  invoiced: bool | None = Query(default=None, description="false: los que falta facturar"),
                  client_id: str | None = None, limit: int = Query(default=200, ge=1, le=1000)):
    q = select(BillingPayment).where(BillingPayment.status == "approved")
    if invoiced is not None:
        q = q.where(BillingPayment.invoiced_at.is_not(None) if invoiced else BillingPayment.invoiced_at.is_(None))
    if client_id:
        q = q.where(BillingPayment.client_id == client_id)
    return _payments(db, q.order_by(BillingPayment.paid_on.desc(), BillingPayment.created_at.desc()).limit(limit))


@router.patch("/billing/payments/{payment_id}", response_model=PaymentOut)
def update_payment(payment_id: str, body: PaymentPatch, _: AdminPrincipal, db: DB):
    """Marca un pago como facturado (la factura se emite fuera de la app)."""
    payment = db.get(BillingPayment, payment_id)
    if payment is None:
        raise NotFound("Pago inexistente")
    payment.invoiced_at = (payment.invoiced_at or utcnow()) if body.invoiced else None
    db.commit()
    return _payments(db, select(BillingPayment).where(BillingPayment.id == payment.id))[0]
