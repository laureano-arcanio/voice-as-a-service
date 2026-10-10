"""Ciclo de vida del plan pago de un cliente. Toda transicion pasa por aca.

- El tier vigente sigue siendo `clients.tier_id`: los limites salen de services/limits.py como
  siempre. Este modulo solo decide cuando cambia.
- Transferencia: el cliente pide el plan (`request_plan`, queda `pending`) y un admin registra
  el pago (`record_payment`): ahi se activa por un mes. La renovacion es otro pago registrado.
- Vencido sin pago: `past_due` con el tier pago hasta `grace_until` (BILLING_GRACE_DAYS); despues
  baja al Free (`downgrade_to_free`). Los numeros que no entran en el Free quedan suspendidos
  (asignados, sin atender) BILLING_NUMBER_HOLD_DAYS y despues vuelven al inventario.
- `tick` corre en el loop de la app (billing/loop.py): vencimientos, gracia, recordatorios y
  numeros a liberar. Devuelve los mails, que se mandan despues del commit.
"""
import calendar
import datetime
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..mail import messages
from ..mail.sender import Mail
from ..models import BillingPayment, Client, PhoneNumber, Role, Subscription, Tier, User
from ..services import limits, phone_numbers
from ..services.errors import Conflict, Invalid

logger = logging.getLogger(__name__)

OPEN_STATUSES = ("pending", "active", "past_due")
METHODS = ("transfer",)   # mercadopago: fase 3


def add_month(d: datetime.date) -> datetime.date:
    """El mismo dia del mes siguiente (31/01 -> 28/02)."""
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


def free_tier(s: Session) -> Tier | None:
    """El del registro: publico y con precio 0."""
    return s.scalar(select(Tier).where(Tier.public.is_(True), Tier.price_ars == 0)
                    .order_by(Tier.sort, Tier.name).limit(1))


def public_tiers(s: Session) -> list[Tier]:
    return list(s.scalars(select(Tier).where(Tier.public.is_(True), Tier.price_ars.is_not(None))
                          .order_by(Tier.sort, Tier.price_ars, Tier.name)))


def current(s: Session, client_id: str) -> Subscription | None:
    """La suscripcion no cancelada del cliente, si tiene."""
    return s.scalar(select(Subscription).where(Subscription.client_id == client_id,
                                               Subscription.status.in_(OPEN_STATUSES))
                    .order_by(Subscription.created_at.desc()).limit(1))


def _lock(s: Session, client: Client) -> None:
    # Como la admision de llamadas: serializa los cambios de plan del mismo cliente.
    s.execute(select(Client.id).where(Client.id == client.id).with_for_update(key_share=True, of=Client))


def _sellable(s: Session, tier_id: str) -> Tier:
    tier = s.get(Tier, tier_id)
    if tier is None or not tier.public or not tier.price_ars:
        raise Invalid("Ese plan no se puede contratar desde el dashboard", "invalid_tier")
    return tier


def amount_due(s: Session, sub: Subscription) -> int:
    """Lo que se cobra en el proximo periodo: el plan pedido, o el actual."""
    tier = s.get(Tier, sub.pending_tier_id or sub.tier_id)
    return tier.price_ars or 0


def fit_numbers(s: Session, client: Client, now: datetime.datetime | None = None) -> list[str]:
    """Deja atendiendo a lo sumo los numeros que permite el plan actual: suspende los que sobran
    (los asignados mas recientemente) y reactiva los suspendidos que entran. Devuelve los recien
    suspendidos (E.164)."""
    now = now or utcnow()
    limit = limits.effective_limits(s, client, now).max_phone_numbers
    numbers = list(s.scalars(select(PhoneNumber).where(PhoneNumber.client_id == client.id)))
    # Primero los que ya atendian, por antiguedad.
    numbers.sort(key=lambda n: (n.suspended_at is not None, n.assigned_at or datetime.datetime.min))
    suspended = []
    for i, n in enumerate(numbers):
        keep = limit is None or i < limit
        if keep:
            n.suspended_at = None
        elif n.suspended_at is None:
            n.suspended_at = now
            suspended.append(n.e164)
    return suspended


def _users(s: Session, client_id: str) -> list[User]:
    return list(s.scalars(select(User).where(User.client_id == client_id, User.role == Role.client,
                                             User.active.is_(True)).order_by(User.email)))


# ---------- pedidos del cliente ----------

def request_plan(s: Session, client: Client, tier_id: str, method: str, user: User | None) -> Subscription:
    """Pide un plan pago. Sin suscripcion: queda `pending` hasta el pago. Con una activa: el plan
    nuevo queda pedido (`pending_tier_id`) y se aplica al registrar el proximo pago."""
    if method not in METHODS:
        raise Invalid("Ese medio de pago todavía no está disponible", "method_unavailable")
    tier = _sellable(s, tier_id)
    _lock(s, client)
    sub = current(s, client.id)
    if sub is not None and sub.method != method:
        raise Conflict("El plan se paga con otro medio: cancelalo primero", "method_mismatch")
    if sub is None:
        sub = Subscription(client_id=client.id, tier_id=tier.id, method=method, status="pending",
                           payer_email=user.email if user else "")
        s.add(sub)
    elif sub.status == "pending":
        sub.tier_id = tier.id
    else:
        sub.pending_tier_id = None if tier.id == sub.tier_id else tier.id
        sub.cancel_at_period_end = False
    s.flush()
    return sub


def request_mails(s: Session, client: Client, sub: Subscription, user: User | None) -> list[Mail]:
    """Instrucciones de pago al usuario que lo pidio y aviso al admin."""
    tier = s.get(Tier, sub.pending_tier_id or sub.tier_id)
    amount = tier.price_ars or 0
    out = []
    if user is not None:
        out.append(messages.transfer_requested(email=user.email, name=user.name, client_name=client.name,
                                               tier=tier, amount=amount))
    to = settings.billing_notify_to or settings.support_email
    if to:
        out.append(messages.transfer_requested_admin(
            to=to, client_name=client.name, user_email=user.email if user else "-", tier=tier, amount=amount,
            client_url=f"{settings.app_url.rstrip('/')}/clients/{client.id}"))
    return out


def cancel(s: Session, client: Client) -> Subscription:
    """Baja pedida por el cliente: una pendiente se cancela ya; una activa dura hasta el fin del
    periodo pago; una vencida (en gracia) baja al Free ya."""
    _lock(s, client)
    sub = current(s, client.id)
    if sub is None:
        raise Invalid("No tenés un plan pago", "no_subscription")
    if sub.status == "pending":
        sub.status, sub.canceled_at = "canceled", utcnow()
    elif sub.status == "active":
        sub.cancel_at_period_end, sub.pending_tier_id = True, None
    else:
        downgrade_to_free(s, client, sub)
    s.flush()
    return sub


def update_fiscal(client: Client, legal_name: str, tax_id: str, tax_condition: str) -> None:
    client.legal_name, client.tax_id, client.tax_condition = legal_name.strip(), tax_id, tax_condition


# ---------- acciones del admin ----------

@dataclass
class Downgrade:
    client: Client
    old_tier: str
    new_tier: str
    suspended: list[str]


def downgrade_to_free(s: Session, client: Client, sub: Subscription,
                      now: datetime.datetime | None = None) -> Downgrade:
    """Termina la suscripcion y pasa el cliente al Free (sin Free cargado, lo desactiva)."""
    now = now or utcnow()
    sub.status, sub.canceled_at, sub.pending_tier_id = "canceled", now, None
    old = client.tier.name
    free = free_tier(s)
    if free is None:
        logger.error("billing: no hay tier publico con precio 0; %s queda inactivo", client.slug)
        client.active = False
        return Downgrade(client, old, old, [])
    client.tier = free
    s.flush()
    return Downgrade(client, old, free.name, fit_numbers(s, client, now))


def downgrade_mails(s: Session, d: Downgrade, now: datetime.datetime | None = None) -> list[Mail]:
    release_on = limits.today(now) + datetime.timedelta(days=settings.billing_number_hold_days)
    return [messages.downgraded(email=u.email, name=u.name, client_name=d.client.name, old_tier=d.old_tier,
                                new_tier=d.new_tier, suspended=d.suspended, release_on=release_on)
            for u in _users(s, d.client.id)]


def record_payment(s: Session, client: Client, *, tier_id: str, amount_ars: int, paid_on: datetime.date,
                   note: str, admin_id: str | None) -> tuple[BillingPayment, list[Mail]]:
    """Pago por transferencia confirmado por un admin: activa el plan (o lo renueva) por un mes
    desde el vencimiento actual, o desde hoy si no tenia uno vigente."""
    tier = s.get(Tier, tier_id)
    if tier is None:
        raise Invalid("Tier inexistente", "invalid_tier")
    _lock(s, client)
    sub = current(s, client.id)
    if sub is not None and sub.method != "transfer":
        raise Conflict("El cliente paga con Mercado Pago: cancelá esa suscripción primero", "method_mismatch")
    if sub is None:
        sub = Subscription(client_id=client.id, tier_id=tier.id, method="transfer", status="pending")
        s.add(sub)
    today = limits.today()
    base = sub.current_period_end if sub.status in ("active", "past_due") and sub.current_period_end else today
    sub.current_period_end = add_month(base)
    sub.tier_id, sub.status, sub.pending_tier_id = tier.id, "active", None
    sub.grace_until, sub.cancel_at_period_end = None, False
    client.tier = tier
    s.flush()
    fit_numbers(s, client)
    payment = BillingPayment(client_id=client.id, subscription_id=sub.id, tier_id=tier.id, method="transfer",
                             status="approved", amount_ars=amount_ars, paid_on=paid_on,
                             period_end=sub.current_period_end, recorded_by=admin_id, note=note.strip())
    s.add(payment)
    s.flush()
    mails = [messages.payment_recorded(email=u.email, name=u.name, client_name=client.name, tier=tier,
                                       amount=amount_ars, period_end=sub.current_period_end)
             for u in _users(s, client.id)]
    return payment, mails


def suspend(s: Session, client: Client) -> list[Mail]:
    """El admin corta el plan: una pendiente se rechaza; una activa baja al Free ya."""
    _lock(s, client)
    sub = current(s, client.id)
    if sub is None:
        raise Invalid("El cliente no tiene un plan pago", "no_subscription")
    if sub.status == "pending":
        sub.status, sub.canceled_at = "canceled", utcnow()
        return []
    return downgrade_mails(s, downgrade_to_free(s, client, sub))


# ---------- barrido periodico ----------

def tick(s: Session, now: datetime.datetime | None = None) -> list[Mail]:
    """Vencimientos, fin de la gracia, recordatorios de transferencia y numeros a liberar.
    Idempotente: se puede correr seguido. Quien llama hace commit y despues manda los mails."""
    now = now or utcnow()
    today = limits.today(now)
    mails: list[Mail] = []
    subs = list(s.scalars(select(Subscription).where(Subscription.status.in_(("active", "past_due")))))
    for sub in subs:
        client = s.get(Client, sub.client_id)
        tier = s.get(Tier, sub.tier_id)
        end = sub.current_period_end
        if end is None:
            continue
        if sub.status == "active" and end < today:
            if sub.cancel_at_period_end:
                mails += downgrade_mails(s, downgrade_to_free(s, client, sub, now), now)
                continue
            sub.status = "past_due"
            sub.grace_until = end + datetime.timedelta(days=settings.billing_grace_days)
            mails += [messages.payment_overdue(email=u.email, name=u.name, client_name=client.name, tier=tier,
                                               grace_until=sub.grace_until) for u in _users(s, client.id)]
        elif sub.status == "past_due" and sub.grace_until and sub.grace_until < today:
            mails += downgrade_mails(s, downgrade_to_free(s, client, sub, now), now)
        elif (sub.status == "active" and sub.method == "transfer" and not sub.cancel_at_period_end
              and (end - today).days <= settings.billing_reminder_days and sub.reminded_for != end):
            sub.reminded_for = end
            next_tier = s.get(Tier, sub.pending_tier_id or sub.tier_id)
            mails += [messages.renewal_reminder(email=u.email, name=u.name, client_name=client.name,
                                                tier=next_tier, amount=next_tier.price_ars or 0, period_end=end)
                      for u in _users(s, client.id)]
    hold = now - datetime.timedelta(days=settings.billing_number_hold_days)
    for number in s.scalars(select(PhoneNumber).where(PhoneNumber.suspended_at.is_not(None),
                                                      PhoneNumber.suspended_at < hold)):
        logger.info("billing: %s vuelve al inventario (suspendido desde %s)", number.e164, number.suspended_at)
        phone_numbers.release(number)
    s.flush()
    return mails
