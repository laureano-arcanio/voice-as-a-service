from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ...models import Client, Role, User
from ...services.errors import Conflict, Invalid, NotFound
from ...services.security import hash_password
from ..deps import DB, AdminPrincipal
from ..schemas import UserIn, UserOut, UserUpdate
from .clients import get_client

router = APIRouter(prefix="/users", tags=["users"])


def _get(db, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("Usuario inexistente")
    return user


def _out(user: User, client_name: str | None) -> UserOut:
    return UserOut.model_validate(user).model_copy(update={"client_name": client_name})


def _client_name(db, user: User) -> str | None:
    client = db.get(Client, user.client_id) if user.client_id else None
    return client.name if client else None


@router.get("", response_model=list[UserOut])
def list_users(_: AdminPrincipal, db: DB, client_id: str | None = None):
    q = select(User, Client.name).outerjoin(Client, Client.id == User.client_id).order_by(User.email)
    if client_id:
        q = q.where(User.client_id == client_id)
    return [_out(u, name) for u, name in db.execute(q)]


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserIn, p: AdminPrincipal, db: DB):
    if body.role == Role.client:
        if not body.client_id:
            raise Invalid("Un usuario de cliente necesita client_id")
        get_client(db, p, body.client_id)
    elif body.client_id:
        raise Invalid("Un admin no pertenece a un cliente")
    user = User(email=body.email.lower(), name=body.name, password_hash=hash_password(body.password),
                role=body.role, client_id=body.client_id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        raise Conflict(f"Ya existe un usuario {body.email}") from None
    return _out(user, _client_name(db, user))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, p: AdminPrincipal, db: DB):
    user = _get(db, user_id)
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if user.id == p.id and data.get("active") is False:
        raise Invalid("No podés desactivar tu propio usuario")
    if password := data.pop("password", None):
        user.password_hash = hash_password(password)
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    return _out(user, _client_name(db, user))


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, p: AdminPrincipal, db: DB):
    user = _get(db, user_id)
    if user.id == p.id:
        raise Invalid("No podés borrar tu propio usuario")
    db.delete(user)
    db.commit()
