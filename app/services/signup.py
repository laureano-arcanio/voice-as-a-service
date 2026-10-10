"""Registro autoservicio desde la landing (POST /api/v1/demo/signup) y "olvidé mi clave".

El registro crea el cliente y su usuario con la clave que eligio y devuelve un link de un solo uso
(`continue_url`, 10 min) que abre la sesion en el dashboard.

- Free: el cliente queda en el tier Free y va al inicio.
- Plan pago con Mercado Pago: el pago es parte del registro (paso 2 del formulario de la landing, con la
  tarjeta tokenizada). **La cuenta se crea solo si MP aprueba la tarjeta**: rechazada, no queda nada; si
  algo falla despues de crear la suscripcion en MP, se cancela alla. Va al inicio con el plan activo.
- Plan pago sin Mercado Pago: queda en Free y va a la pantalla Plan (transferencia).

Un email que ya tiene cuenta da 409 (`check_email` lo dice antes de pedir la tarjeta). Le llega un mail de
bienvenida. Los registros en los que nadie entro se borran a las PASSWORD_SETUP_HOURS.
"""
import asyncio
import datetime
import logging
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..billing import mp
from ..billing import service as billing
from ..billing.service import free_tier, public_tiers
from ..config import settings
from ..db import utcnow
from ..mail import messages, notify
from ..mail.sender import Mail
from ..models import Client, ConversationRow, Role, Tier, User
from .agents import slugify
from .demo import DemoUnavailable, verify_turnstile
from .errors import Conflict, Forbidden, Invalid, ServiceError
from .ratelimit import Limit, RateLimiter, client_key
from .security import create_handoff_token, create_password_setup_token, hash_password

logger = logging.getLogger(__name__)
HOUR, DAY = 3600, 86_400
limiter = RateLimiter()

# Dominios de email descartables mas comunes. No es una lista completa: frena el abuso facil.
DISPOSABLE_DOMAINS = frozenset({
    "10minutemail.com", "20minutemail.com", "anonbox.net", "dispostable.com", "emailondeck.com",
    "fakeinbox.com", "getnada.com", "guerrillamail.com", "guerrillamail.net", "maildrop.cc", "mailinator.com",
    "mailnesia.com", "mintemail.com", "mohmal.com", "sharklasers.com", "temp-mail.org", "tempmail.com",
    "tempmailo.com", "throwawaymail.com", "trashmail.com", "yopmail.com", "yopmail.net",
})


@dataclass(frozen=True)
class SignupData:
    company: str
    name: str
    email: str
    password: str
    plan: str = ""      # nombre del tier elegido en la landing
    card_token_id: str | None = None   # tarjeta tokenizada por el Card Payment Brick (plan pago con MP)


class EmailTaken(Conflict):
    default_code = "email_taken"


def ensure_enabled(s: Session) -> None:
    if not settings.signup_enabled or not settings.turnstile_secret_key or free_tier(s) is None:
        raise DemoUnavailable("El registro no está disponible en este momento. Escribinos y te damos de alta.",
                              "signup_unavailable")


def _unique_slug(s: Session, company: str) -> str:
    base = slugify(company)[:48]
    if base == "agente":
        base = "cliente"
    slug = base
    while s.scalar(select(exists().where(Client.slug == slug))):
        slug = f"{base}_{secrets.token_hex(2)}"
    return slug


def _reset_mail(user: User) -> Mail:
    token, expires = create_password_setup_token(user.id, user.password_hash)
    return messages.password_reset(email=user.email, name=user.name, setup_url=messages.password_setup_url(token),
                                   expires_at=expires)


def paid_tier(s: Session, plan: str) -> Tier | None:
    """El tier pago y publico que eligio en la landing (por nombre), si existe."""
    return next((t for t in public_tiers(s) if t.price_ars and t.name.lower() == plan.strip().lower()), None)


def _taken() -> EmailTaken:
    return EmailTaken("Ya hay una cuenta con ese email. Ingresá o recuperá tu clave.")


def _check_email(s: Session, email: str) -> None:
    if email.rsplit("@", 1)[-1] in DISPOSABLE_DOMAINS:
        raise Invalid("Usá el email de tu empresa o uno personal permanente", "disposable_email")
    if s.scalar(select(exists().where(User.email == email))):
        raise _taken()


def check_email(s: Session, email: str, ip: str) -> None:
    """Antes del paso del pago: que el email sirva para registrarse (no pedir la tarjeta para despues
    decir que ya tiene cuenta). Tope por IP."""
    limiter.consume(f"check:{client_key(ip)}", [Limit(settings.signup_check_ip_per_hour, HOUR)],
                    "Demasiados intentos. Probá más tarde.")
    _check_email(s, email.strip().lower())


def create_account(s: Session, data: SignupData) -> str:
    """Crea el cliente y su usuario con su clave (y, con un plan pago y Mercado Pago, la suscripcion: si MP
    rechaza la tarjeta no se crea nada); devuelve el link de un solo uso al dashboard. Los mails salen
    despues del commit."""
    email = data.email.strip().lower()
    _check_email(s, email)
    tier = paid_tier(s, data.plan)
    pay_now = tier is not None and mp.enabled()
    if pay_now and not data.card_token_id:
        raise Invalid("Faltan los datos de la tarjeta", "card_required")
    client = Client(name=data.company.strip(), slug=_unique_slug(s, data.company), tier=free_tier(s),
                    created_via="signup")
    s.add(client)
    s.flush()
    user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password), role=Role.client,
                client_id=client.id)
    s.add(user)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()   # el mismo email en paralelo
        raise _taken() from None
    mails, sub = [], None
    if pay_now:
        try:
            sub, mails = billing.subscribe_card(s, client, tier.id, data.card_token_id, user)
        except ServiceError:
            s.rollback()   # tarjeta rechazada o MP caido: no queda ni la cuenta
            raise
    try:
        s.commit()
    except Exception:
        s.rollback()
        if sub is not None and sub.mp_preapproval_id:
            _cancel_orphan(sub.mp_preapproval_id)
        raise
    logger.info("registro: cliente %s (%s)%s", client.slug, email, f", plan {tier.name}" if pay_now else "")
    notify.deliver([messages.account_ready(email=user.email, name=user.name, client_name=client.name,
                                           tier_name=client.tier.name), *mails])
    token = create_handoff_token(user.id, user.session_version)
    next_path = f"/plan?{urlencode({'tier': tier.name})}" if tier is not None and not pay_now else "/"
    query = urlencode({"token": token, "next": next_path})
    return f"{settings.app_url.rstrip('/')}/welcome?{query}"


def _cancel_orphan(preapproval_id: str) -> None:
    """La suscripcion se creo en MP pero la cuenta no se guardo: que MP no la siga debitando."""
    try:
        billing.mp_client().cancel(preapproval_id)
        logger.warning("registro: suscripcion %s cancelada en MP (no se guardo la cuenta)", preapproval_id)
    except ServiceError as e:
        logger.error("registro: no se pudo cancelar la suscripcion huerfana %s en MP: %s", preapproval_id, e.message)


async def signup(s: Session, data: SignupData, turnstile_token: str, ip: str) -> str:
    await asyncio.to_thread(ensure_enabled, s)
    key = f"signup:{client_key(ip)}"
    limiter.check(key, [Limit(settings.signup_ip_per_hour, HOUR), Limit(settings.signup_ip_per_day, DAY)],
                  "Demasiados registros desde esta conexión. Probá más tarde.")
    if not await verify_turnstile(turnstile_token, ip):
        raise Forbidden("No pudimos verificar que seas una persona. Recargá la página.", "captcha_failed")
    limiter.hit(key)
    return await asyncio.to_thread(create_account, s, data)


def password_reset(s: Session, email: str, ip: str) -> None:
    """Manda el link para crear una clave nueva si el email es de un usuario activo. Topes por IP y
    por email (no revela si existe: el tope por email cuenta igual)."""
    email = email.strip().lower()
    limiter.consume_all([
        (f"reset:ip:{client_key(ip)}", [Limit(settings.password_reset_ip_per_hour, HOUR)]),
        (f"reset:email:{email}", [Limit(settings.password_reset_email_per_hour, HOUR)]),
    ], "Demasiados pedidos. Probá de nuevo en un rato.")
    user = s.scalar(select(User).where(User.email == email))
    if user is not None and user.active:
        notify.deliver([_reset_mail(user)])


def purge_unactivated(s: Session, now: datetime.datetime | None = None) -> int:
    """Borra los clientes del registro que nadie activo: sin ningun ingreso (`last_login_at`) ni
    conversaciones, creados hace mas de PASSWORD_SETUP_HOURS (el link ya vencio)."""
    cutoff = (now or utcnow()) - datetime.timedelta(hours=settings.password_setup_hours)
    logged_in = select(User.id).where(User.client_id == Client.id, User.last_login_at.is_not(None))
    talked = select(ConversationRow.id).where(ConversationRow.client_id == Client.id)
    stale = list(s.scalars(select(Client).where(Client.created_via == "signup", Client.created_at < cutoff,
                                                ~exists(logged_in), ~exists(talked))))
    for client in stale:
        logger.info("registro: %s sin activar, se borra", client.slug)
        s.execute(delete(User).where(User.client_id == client.id))
        s.delete(client)
    return len(stale)

