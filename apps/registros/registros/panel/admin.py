"""API del admin (/admin/api): tenants, formulario, usuarios, claves y fichas en solo lectura.

- Solo usuarios del tenant admin (AdminUser): sin sesión, 401; un usuario de cliente, 404.
- Ninguna ruta opera sobre el tenant admin ni acepta is_admin: los admin se crean por CLI (create-admin).
- Nada de lo que hace el admin se escribe en audit_log (decisión del usuario).
"""
import contextlib
import json
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from .. import admin_ops
from ..admin_ops import OpsError
from ..auth import AdminUser, DbSession
from ..models import ApiKey, Person, Tenant, User
from .persons import (
    PAGE_SIZE_DEFAULT,
    PageQ,
    PerPageQ,
    SearchQ,
    _money,
    _when,
    person_detail,
    search_persons,
)

router = APIRouter(prefix="/admin/api")

# Topes del cuerpo; las validaciones finas (bytes, formato) están en admin_ops.
TEXT_MAX = 1024
FORM_TEXT_MAX = admin_ops.FORM_HTML_MAX_BYTES


@contextlib.contextmanager
def _ops(s: Session):
    """Errores de admin_ops a HTTP. Dos altas iguales a la vez: la segunda choca en la base y da 409, no 500."""
    try:
        yield
    except OpsError as e:
        s.rollback()
        raise HTTPException(e.status, str(e)) from None
    except IntegrityError:
        s.rollback()
        raise HTTPException(409, "En conflicto con un dato existente") from None
    except DataError:
        s.rollback()
        raise HTTPException(422, "Dato inválido") from None


def _tenant(s: Session, tenant_id: str, *, lock: bool = False) -> Tenant:
    with _ops(s):
        return admin_ops.tenant_by_id(s, tenant_id, lock=lock)


def _tenant_out(tenant: Tenant) -> dict:
    return {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "charge_amount": _money(tenant.charge_amount),
        "currency": tenant.currency,
        "active": tenant.active,
        "has_form": tenant.form_html is not None and tenant.form_schema is not None and tenant.manifest is not None,
        "created_at": _when(tenant.created_at),
    }


def _user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "active": user.active, "created_at": _when(user.created_at)}


def _key_out(key: ApiKey) -> dict:
    return {"id": key.id, "name": key.name, "scope": key.scope, "created_at": _when(key.created_at),
            "revoked_at": _when(key.revoked_at)}


def _count(model, *conditions):
    return (select(func.count()).select_from(model).where(model.tenant_id == Tenant.id, *conditions)
            .correlate(Tenant).scalar_subquery())


# --- Cuerpos (sin is_admin ni slug editable) ---


class TenantIn(BaseModel):
    slug: str = Field(max_length=TEXT_MAX)
    name: str = Field(max_length=TEXT_MAX)
    charge_amount: Decimal | str
    currency: str = Field(default="ARS", max_length=TEXT_MAX)


class TenantPatch(BaseModel):
    name: str | None = Field(default=None, max_length=TEXT_MAX)
    charge_amount: Decimal | str | None = None
    currency: str | None = Field(default=None, max_length=TEXT_MAX)


class FormIn(BaseModel):
    """Los tres archivos como texto: lo que devuelve GET se puede volver a subir."""
    form_html: str = Field(max_length=FORM_TEXT_MAX)
    schema_: str = Field(alias="schema", max_length=admin_ops.FORM_JSON_MAX_BYTES)
    manifest: str = Field(max_length=admin_ops.FORM_JSON_MAX_BYTES)


class UserIn(BaseModel):
    email: str = Field(max_length=TEXT_MAX)
    password: str = Field(max_length=admin_ops.PASSWORD_MAX)


class PasswordIn(BaseModel):
    password: str = Field(max_length=admin_ops.PASSWORD_MAX)


class ActiveIn(BaseModel):
    active: bool


class KeyIn(BaseModel):
    scope: str = Field(max_length=TEXT_MAX)
    name: str = Field(max_length=TEXT_MAX)


# --- Tenants ---


@router.get("/tenants")
def list_tenants(_: AdminUser, s: DbSession) -> list[dict]:
    rows = s.execute(
        select(Tenant,
               _count(User, User.active).label("users_active"),
               _count(ApiKey, ApiKey.revoked_at.is_(None)).label("keys_active"),
               _count(Person, Person.active).label("persons_active"))
        .where(Tenant.is_admin.is_(False))
        .order_by(Tenant.slug)
    )
    return [{**_tenant_out(row.Tenant), "users_active": row.users_active, "keys_active": row.keys_active,
             "persons_active": row.persons_active} for row in rows]


@router.post("/tenants", status_code=201)
def create_tenant(body: TenantIn, _: AdminUser, s: DbSession) -> dict:
    with _ops(s):
        tenant = admin_ops.create_tenant(s, body.slug, body.name, body.charge_amount, body.currency)
        s.commit()
    return _tenant_out(tenant)


@router.get("/tenants/{tenant_id}")
def read_tenant(tenant_id: str, _: AdminUser, s: DbSession) -> dict:
    tenant = _tenant(s, tenant_id)
    users = s.scalars(select(User).where(User.tenant_id == tenant.id).order_by(User.email))
    keys = s.scalars(select(ApiKey).where(ApiKey.tenant_id == tenant.id).order_by(ApiKey.created_at, ApiKey.id))
    return {**_tenant_out(tenant), "users": [_user_out(u) for u in users], "keys": [_key_out(k) for k in keys]}


@router.patch("/tenants/{tenant_id}")
def update_tenant(tenant_id: str, body: TenantPatch, _: AdminUser, s: DbSession) -> dict:
    tenant = _tenant(s, tenant_id, lock=True)
    with _ops(s):
        admin_ops.update_tenant(s, tenant, name=body.name, amount=body.charge_amount, currency=body.currency)
        s.commit()
    return _tenant_out(tenant)


@router.get("/tenants/{tenant_id}/form")
def read_form(tenant_id: str, _: AdminUser, s: DbSession) -> dict:
    tenant = _tenant(s, tenant_id)
    if tenant.form_html is None or tenant.form_schema is None or tenant.manifest is None:
        raise HTTPException(404, "Este tenant todavía no tiene formulario cargado")
    return {
        "form_html": tenant.form_html,
        "schema": json.dumps(tenant.form_schema, ensure_ascii=False, indent=2),
        "manifest": json.dumps(tenant.manifest, ensure_ascii=False, indent=2),
    }


@router.put("/tenants/{tenant_id}/form")
def load_form(tenant_id: str, body: FormIn, _: AdminUser, s: DbSession) -> dict:
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        count = admin_ops.load_form(s, tenant, body.form_html, body.schema_, body.manifest)
        s.commit()
    return {"persons_updated": count}


@router.put("/tenants/{tenant_id}/active", status_code=204)
def set_tenant_active(tenant_id: str, body: ActiveIn, _: AdminUser, s: DbSession) -> Response:
    """Desactivar: sin login ni sesiones y /v1 da 403. Reactivar revive las claves no revocadas."""
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        admin_ops.set_tenant_active(s, tenant, body.active)
        s.commit()
    return Response(status_code=204)


# --- Usuarios ---


@router.post("/tenants/{tenant_id}/users", status_code=201)
def create_user(tenant_id: str, body: UserIn, _: AdminUser, s: DbSession) -> dict:
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        user = admin_ops.create_user(s, tenant, body.email, body.password)
        s.commit()
    return _user_out(user)


@router.put("/tenants/{tenant_id}/users/{user_id}/password", status_code=204)
def set_password(tenant_id: str, user_id: str, body: PasswordIn, _: AdminUser, s: DbSession) -> Response:
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        admin_ops.set_password(s, admin_ops.user_of(s, tenant, user_id), body.password)
        s.commit()
    return Response(status_code=204)


@router.put("/tenants/{tenant_id}/users/{user_id}/active", status_code=204)
def set_user_active(tenant_id: str, user_id: str, body: ActiveIn, _: AdminUser, s: DbSession) -> Response:
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        admin_ops.set_user_active(s, admin_ops.user_of(s, tenant, user_id), body.active)
        s.commit()
    return Response(status_code=204)


# --- Claves de la API ---


@router.post("/tenants/{tenant_id}/keys", status_code=201)
def create_key(tenant_id: str, body: KeyIn, _: AdminUser, s: DbSession) -> dict:
    """`key` sale solo en esta respuesta; en la base queda el hash."""
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        row, key = admin_ops.create_key(s, tenant, body.scope, body.name)
        s.commit()
    return {"id": row.id, "key": key, "scope": row.scope, "name": row.name}


@router.delete("/tenants/{tenant_id}/keys/{key_id}", status_code=204)
def revoke_key(tenant_id: str, key_id: str, _: AdminUser, s: DbSession) -> Response:
    tenant = _tenant(s, tenant_id)
    with _ops(s):
        admin_ops.revoke_key(s, admin_ops.key_of(s, tenant, key_id))
        s.commit()
    return Response(status_code=204)


# --- Fichas, solo lectura y sin audit ---


@router.get("/tenants/{tenant_id}/persons")
def list_persons(
    tenant_id: str,
    _: AdminUser,
    s: DbSession,
    q: SearchQ = "",
    al_dia: bool | None = None,
    page: PageQ = 1,
    per_page: PerPageQ = PAGE_SIZE_DEFAULT,
) -> dict:
    tenant = _tenant(s, tenant_id)
    return search_persons(s, tenant.id, q, al_dia, page, per_page)


@router.get("/tenants/{tenant_id}/persons/{person_id}")
def read_person(tenant_id: str, person_id: str, _: AdminUser, s: DbSession) -> dict:
    tenant = _tenant(s, tenant_id)
    return person_detail(s, tenant.id, person_id)[1]
