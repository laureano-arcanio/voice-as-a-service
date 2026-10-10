"""Ciclo de vida del plan pago de un cliente. Toda transicion pasa por aca.

- El tier vigente sigue siendo `clients.tier_id`: los limites salen de services/limits.py como
  siempre. Este modulo solo decide cuando cambia.
- Transferencia: el cliente pide el plan (`request_plan`, queda `pending`) y un admin registra
  el pago (`record_payment`): ahi se activa por un mes. La renovacion es otro pago registrado.
- Vencido sin pago: `past_due` con el tier pago hasta `grace_until` (BILLING_GRACE_DAYS); despues
  baja al Free (`downgrade_to_free`). Los numeros que no entran en el Free quedan suspendidos
  (asignados, sin atender) BILLING_NUMBER_HOLD_DAYS y despues vuelven al inventario.
- Mercado Pago (tarjeta con debito automatico): `subscribe_card` crea la suscripcion `authorized` en MP
  con el token de la tarjeta (cobra el primer mes en el momento) y `sync` aplica lo que diga MP: pagos
  aprobados activan o renuevan hasta `next_payment_date`; una cancelacion deja el plan hasta el fin del
  periodo. Lo llaman el alta, el webhook (billing/webhook.py) y la conciliacion del barrido.
- `tick` corre en el loop de la app (billing/loop.py): vencimientos, gracia, recordatorios y
  numeros a liberar. Devuelve los mails, que se mandan despues del commit.
"""
import calendar
import datetime
import logging
import time
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..mail import messages
from ..mail.sender import Mail
from ..models import BillingPayment, Client, PhoneNumber, Role, Subscription, Tier, User
from ..models._common import new_id
from ..services import limits, phone_numbers
from ..services.errors import Conflict, Invalid, ServiceError
from . import mp

logger = logging.getLogger(__name__)

OPEN_STATUSES = ("pending", "active", "past_due")


def methods() -> list[str]:
    """Medios de pago ofrecidos: Mercado Pago solo con credenciales cargadas."""
    return ["mercadopago", "transfer"] if mp.enabled() else ["transfer"]


SUBSCRIBE_RETRIES, SUBSCRIBE_RETRY_SECONDS = 4, 1.5
wait = time.sleep   # los tests lo anulan


def mp_client() -> mp.Client:
    """Los tests lo reemplazan por uno falso."""
    return mp.Client()


def _local_date(iso: str | None) -> datetime.date | None:
    """Fecha de MP (ISO con zona) en BILLING_TIMEZONE."""
    if not iso:
        return None
    return datetime.datetime.fromisoformat(iso).astimezone(ZoneInfo(settings.billing_timezone)).date()


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
    if method != "transfer":
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
    if sub.method == "mercadopago" and sub.mp_preapproval_id and sub.status != "past_due":
        mp_client().cancel(sub.mp_preapproval_id)   # sin mas debitos; la vencida la cancela downgrade_to_free
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


# ---------- Mercado Pago ----------

def subscribe_card(s: Session, client: Client, tier_id: str, card_token_id: str,
                   user: User | None) -> tuple[Subscription, list[Mail]]:
    """Plan pago con tarjeta y debito automatico. Una tarjeta rechazada falla aca (CardRejected) y no
    queda nada. Un pedido por transferencia pendiente se reemplaza."""
    if not mp.enabled():
        raise Invalid("El pago con tarjeta todavía no está disponible", "method_unavailable")
    tier = _sellable(s, tier_id)
    _lock(s, client)
    sub = current(s, client.id)
    if sub is not None and sub.status != "pending":
        raise Conflict("Ya tenés un plan pago: cambialo desde la pantalla Plan", "already_subscribed")
    payer = user.email if user else ""
    sub_id = new_id()
    pre = mp_client().create_subscription(
        reason=f"Atentina - plan {tier.name}", external_reference=sub_id,
        payer_email=settings.mp_billing_test_payer_email or payer, card_token_id=card_token_id,
        amount=tier.price_ars, back_url=f"{settings.app_url.rstrip('/')}/plan")
    if sub is not None:   # el pedido por transferencia que no se pago
        sub.status, sub.canceled_at = "canceled", utcnow()
    new = Subscription(id=sub_id, client_id=client.id, tier_id=tier.id, method="mercadopago", status="pending",
                       mp_preapproval_id=pre.id, payer_email=payer)
    s.add(new)
    s.flush()
    try:
        mails = sync(s, new, pre)
        # El primer cobro se acredita en MP un instante despues del alta (probado en sandbox): unos
        # reintentos cortos para activarlo ya; si no, lo activan el webhook o la conciliacion.
        for _ in range(SUBSCRIBE_RETRIES):
            if new.status != "pending":
                break
            wait(SUBSCRIBE_RETRY_SECONDS)
            mails += sync(s, new)
        return new, mails
    except ServiceError as e:
        # La suscripcion ya existe en MP (y pudo cobrar): queda pendiente y la toma la conciliacion. Si
        # esto se deshiciera, MP seguiria debitando una suscripcion que no conocemos.
        logger.warning("billing: %s creada en MP, sin sincronizar: %s", pre.id, e.message)
        return new, []


def change_card_plan(s: Session, client: Client, tier_id: str) -> Subscription:
    """Cambio de plan con debito automatico: el monto nuevo rige desde el proximo debito (MP no
    prorratea). Una subida aplica el plan ya; una bajada, con el proximo pago."""
    tier = _sellable(s, tier_id)
    _lock(s, client)
    sub = current(s, client.id)
    if sub is None or sub.method != "mercadopago" or sub.status == "pending":
        raise Invalid("No tenés un plan con débito automático", "no_subscription")
    current_tier = s.get(Tier, sub.tier_id)
    mp_client().set_amount(sub.mp_preapproval_id, tier.price_ars)
    sub.cancel_at_period_end = False
    if tier.id == sub.tier_id:
        sub.pending_tier_id = None
    elif (tier.price_ars or 0) > (current_tier.price_ars or 0):
        sub.tier_id, sub.pending_tier_id = tier.id, None
        client.tier = tier
        s.flush()
        fit_numbers(s, client)
    else:
        sub.pending_tier_id = tier.id
    s.flush()
    return sub


def sync(s: Session, sub: Subscription, pre: mp.Preapproval | None = None,
         now: datetime.datetime | None = None) -> list[Mail]:
    """Aplica el estado de MP a la suscripcion: registra los pagos nuevos (una vez cada uno, por
    `mp_payment_id`); con un pago aprobado activa o renueva hasta `next_payment_date` (y aplica una bajada
    pedida); una cancelacion en MP deja el plan hasta el fin del periodo pagado."""
    api = mp_client()
    pre = pre or api.get_subscription(sub.mp_preapproval_id)
    client = s.get(Client, sub.client_id)
    _lock(s, client)
    known = set(s.scalars(select(BillingPayment.mp_payment_id).where(BillingPayment.subscription_id == sub.id)))
    approved_now = []
    for quota in api.subscription_payments(pre.id):
        pay = quota.get("payment") or {}
        status = {"approved": "approved", "rejected": "rejected", "refunded": "refunded"}.get(pay.get("status"))
        if not pay.get("id") or status is None or str(pay["id"]) in known:
            continue
        row = BillingPayment(client_id=client.id, subscription_id=sub.id, tier_id=sub.pending_tier_id or sub.tier_id,
                             method="mercadopago", status=status, mp_payment_id=str(pay["id"]),
                             amount_ars=int(round(float(quota.get("transaction_amount") or 0))),
                             paid_on=_local_date(quota.get("debit_date") or quota.get("date_created")) or limits.today(now),
                             period_end=_local_date(pre.next_payment_date), raw=quota)
        s.add(row)
        known.add(row.mp_payment_id)
        if status == "approved":
            approved_now.append(row)
    mails: list[Mail] = []
    if pre.status in ("authorized", "paused") and approved_now:
        if sub.pending_tier_id:
            sub.tier_id, sub.pending_tier_id = sub.pending_tier_id, None
        end = _local_date(pre.next_payment_date)
        if end and (sub.current_period_end is None or end > sub.current_period_end):
            sub.current_period_end = end
        sub.status, sub.grace_until = "active", None
        tier = s.get(Tier, sub.tier_id)
        client.tier = tier
        s.flush()
        fit_numbers(s, client, now)
        mails += [messages.payment_recorded(email=u.email, name=u.name, client_name=client.name, tier=tier,
                                            amount=p.amount_ars, period_end=sub.current_period_end)
                  for p in approved_now for u in _users(s, client.id)]
    elif pre.status == "cancelled" and sub.status != "canceled":
        if sub.status == "pending":
            sub.status, sub.canceled_at = "canceled", now or utcnow()
        else:
            sub.cancel_at_period_end, sub.pending_tier_id = True, None
    s.flush()
    return mails


def by_preapproval(s: Session, preapproval_id: str) -> Subscription | None:
    return s.scalar(select(Subscription).where(Subscription.mp_preapproval_id == preapproval_id))


def reconcile(s: Session, now: datetime.datetime | None = None) -> list[Mail]:
    """Por si se perdio un webhook: pregunta a MP por las suscripciones con debito automatico que
    esperan un pago (pendientes, vencidas o que vencen hoy o antes)."""
    if not mp.enabled():
        return []
    today = limits.today(now)
    mails: list[Mail] = []
    subs = s.scalars(select(Subscription).where(Subscription.method == "mercadopago",
                                                Subscription.status.in_(OPEN_STATUSES)))
    for sub in list(subs):
        if sub.status == "active" and sub.current_period_end and sub.current_period_end > today:
            continue
        try:
            mails += sync(s, sub, now=now)
        except ServiceError as e:
            logger.warning("billing: conciliacion de %s: %s", sub.mp_preapproval_id, e.message)
    return mails


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
    if sub.method == "mercadopago" and sub.mp_preapproval_id:
        try:
            mp_client().cancel(sub.mp_preapproval_id)
        except ServiceError as e:   # ya cancelada en MP (final) o MP caido: el plan baja igual
            logger.warning("billing: no se pudo cancelar %s en MP: %s", sub.mp_preapproval_id, e.message)
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
