"""A quien le llega cada mail, desde la API. Todo es best effort: si Resend falla o no esta
configurado, la operacion que lo pidio (crear el cliente, asignar el numero) sigue."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Agent, Client, PhoneNumber, Role, User
from ..services import phone_numbers
from ..services.security import create_password_setup_token
from . import messages
from .sender import Mail, SendResult, send

logger = logging.getLogger(__name__)


def invite(user: User, client: Client) -> SendResult:
    """Mail con el link para crear la clave (de un solo uso, ver security.create_password_setup_token)."""
    token, expires = create_password_setup_token(user.id, user.password_hash)
    mail = messages.welcome(email=user.email, name=user.name, client_name=client.name, tier=client.tier,
                            setup_url=messages.password_setup_url(token), expires_at=expires)
    result = send(mail)
    if result.status == "sent":
        logger.info("alta de %s (%s): mail enviado, id %s", user.email, client.slug, result.id)
    return result


def number_assigned_mails(db: Session, number: PhoneNumber) -> list[Mail]:
    """Un mail por usuario activo del cliente dueño del numero (cada uno con su link al dashboard).
    Se arma antes de responder; el envio va aparte (`deliver`), sin la sesion de la base."""
    if number.client_id is None:
        return []
    client = db.get(Client, number.client_id)
    agent = db.get(Agent, number.agent_id) if number.agent_id else None
    used = phone_numbers.numbers_count(db, client.id)
    users = db.scalars(select(User).where(User.client_id == client.id, User.role == Role.client,
                                          User.active.is_(True)).order_by(User.email))
    return [messages.number_assigned(email=u.email, name=u.name, client_name=client.name, number=number.e164,
                                     label=number.label, agent_name=agent.name if agent else None,
                                     numbers_used=used, numbers_limit=client.tier.max_phone_numbers)
            for u in users]


def deliver(mails: list[Mail]) -> None:
    for mail in mails:
        result = send(mail)
        if result.status == "sent":
            logger.info("mail a %s enviado, id %s: %s", mail.to, result.id, mail.subject)
