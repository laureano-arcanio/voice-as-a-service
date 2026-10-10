"""Registro autoservicio desde la landing (POST /api/v1/demo/signup) y "olvidé mi clave".

El registro crea el cliente en el tier Free (publico, precio 0) y su usuario sin clave, y manda el
link para crearla: solo el dueño del email puede activar la cuenta. Siempre responde lo mismo,
exista o no el email (no revela quien tiene cuenta): a un email registrado le llega un link para
crear una clave nueva. Los registros que nadie activo se borran a las PASSWORD_SETUP_HOURS.
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

from ..billing.service import free_tier
from ..config import settings
from ..db import utcnow
from ..mail import messages, notify
from ..mail.sender import Mail
from ..models import Client, ConversationRow, Role, User
from .agents import slugify
from .demo import DemoUnavailable, verify_turnstile
from .errors import Forbidden, Invalid
from .ratelimit import Limit, RateLimiter, client_key
from .security import create_password_setup_token, unusable_password_hash

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
    plan: str = ""      # tier elegido en la landing: el link de activacion termina en /plan?tier=...


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


def _reset_mail(user: User, existing_signup: bool) -> Mail:
    token, expires = create_password_setup_token(user.id, user.password_hash)
    return messages.password_reset(email=user.email, name=user.name, setup_url=messages.password_setup_url(token),
                                   expires_at=expires, existing_signup=existing_signup)


def create_account(s: Session, data: SignupData) -> None:
    """Crea el cliente y su usuario, o avisa al dueño del email si ya tiene cuenta. Manda el mail
    despues del commit."""
    email = data.email.strip().lower()
    if email.rsplit("@", 1)[-1] in DISPOSABLE_DOMAINS:
        raise Invalid("Usá el email de tu empresa o uno personal permanente", "disposable_email")
    user = s.scalar(select(User).where(User.email == email))
    if user is not None:
        if user.active:
            notify.deliver([_reset_mail(user, existing_signup=True)])
        return
    tier = free_tier(s)
    client = Client(name=data.company.strip(), slug=_unique_slug(s, data.company), tier=tier, created_via="signup")
    s.add(client)
    s.flush()
    user = User(email=email, name=data.name.strip(), password_hash=unusable_password_hash(), role=Role.client,
                client_id=client.id)
    s.add(user)
    try:
        s.commit()
    except IntegrityError:
        # Otro registro con el mismo email (o slug) en paralelo: lo resolvio ese.
        s.rollback()
        return
    logger.info("registro: cliente %s (%s)", client.slug, email)
    notify.invite(user, client, next_path=f"/plan?{urlencode({'tier': data.plan})}" if data.plan else None)


async def signup(s: Session, data: SignupData, turnstile_token: str, ip: str) -> None:
    await asyncio.to_thread(ensure_enabled, s)
    key = f"signup:{client_key(ip)}"
    limiter.check(key, [Limit(settings.signup_ip_per_hour, HOUR), Limit(settings.signup_ip_per_day, DAY)],
                  "Demasiados registros desde esta conexión. Probá más tarde.")
    if not await verify_turnstile(turnstile_token, ip):
        raise Forbidden("No pudimos verificar que seas una persona. Recargá la página.", "captcha_failed")
    limiter.hit(key)
    await asyncio.to_thread(create_account, s, data)


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
        notify.deliver([_reset_mail(user, existing_signup=False)])


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

