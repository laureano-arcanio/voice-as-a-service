"""Acceso al panel del cliente: nunca queda un cliente sin un Admin activo (docs/features/EQUIPO_TELEFONIA.md).

Se toma el lock del cliente antes de contar: dos Admin que se bajan de rol a la vez se ordenan y el segundo
recibe 409 `last_admin` en vez de dejar al cliente sin nadie.
"""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Client, Role, User
from .errors import Conflict, Invalid
from .security import unusable_password_hash

ADMIN = "admin"
USER = "user"
CLIENT_ROLES = (ADMIN, USER)


def is_admin(user: User) -> bool:
    return user.role == Role.client and user.active and (user.client_role or USER) == ADMIN


def lock_client(s: Session, client_id: str) -> None:
    s.execute(select(Client.id).where(Client.id == client_id).with_for_update(key_share=True, of=Client))


def check_keeps_admin(s: Session, user: User, *, client_role: str | None, active: bool) -> None:
    """409 si el cambio deja al cliente sin Admin activo. `client_role`/`active` son los que quedarían.
    Para borrar, `active=False`."""
    if not is_admin(user):
        return          # un Usuario, o un Admin ya inactivo, no deja a nadie sin Admin
    if active and (client_role or USER) == ADMIN:
        return          # sigue siendo Admin
    lock_client(s, user.client_id)
    s.refresh(user)
    if not is_admin(user) or (active and (client_role or USER) == ADMIN):
        return          # otro pedido ya lo cambió: no hay nada que proteger
    other = s.scalar(select(func.count()).select_from(User).where(
        User.client_id == user.client_id, User.role == Role.client, User.client_role == ADMIN,
        User.active.is_(True), User.id != user.id))
    if not other:
        raise Conflict("El cliente no puede quedar sin un Admin activo", "last_admin")


def give_access(s: Session, member, email: str, client_role: str | None) -> User:
    """El usuario del panel de una persona del equipo: rol de cliente, sin clave, y la invitación va aparte."""
    if member.user_id:
        raise Invalid("Esta persona ya tiene acceso al panel: el email lo cambia en Perfil con un código",
                      "email_readonly")
    if client_role not in (None, *CLIENT_ROLES):
        raise Invalid(f"Rol desconocido (son {', '.join(CLIENT_ROLES)})")
    user = User(email=email.strip().lower(), name=member.name[:120],
                password_hash=unusable_password_hash(), role=Role.client, client_id=member.client_id,
                client_role=client_role or USER)
    s.add(user)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        raise Conflict("Ya hay una cuenta con ese email", "email_taken") from None
    member.user_id = user.id
    s.flush()
    return user
