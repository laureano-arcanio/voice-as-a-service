"""Operaciones del administrador, compartidas por la CLI y la API /admin/api.

Validan y cambian la sesión; no hacen commit, no imprimen y no escriben en audit_log (decisión del usuario:
nada de lo que hace el admin queda registrado). Los mensajes de error no repiten claves ni contraseñas.
"""
import json
import re
from decimal import Decimal, InvalidOperation

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import hash_password, new_api_key, normalize_email
from .db import tenant_get, utcnow
from .manifest import ManifestError, parse_manifest, sync_person
from .models import SCOPES, ApiKey, Person, Tenant, User, UserSession

ADMIN_SLUG = "admin"
ADMIN_NAME = "Administración"
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,79}")
CURRENCY_RE = re.compile(r"[A-Z]{3}")
ID_RE = re.compile(r"[0-9a-f-]{36}")
# Numeric(12, 2): hasta 10 dígitos enteros.
MAX_AMOUNT = Decimal("9999999999.99")
NAME_MAX = 200
EMAIL_MAX = 254
KEY_NAME_MAX = 120
PASSWORD_MIN = 8
ADMIN_PASSWORD_MIN = 12
PASSWORD_MAX = 1024
FORM_HTML_MAX_BYTES = 512 * 1024
FORM_JSON_MAX_BYTES = 256 * 1024
FORM_JSON_MAX_DEPTH = 64


class OpsError(Exception):
    """Dato inválido (la API responde 422)."""
    status = 422


class Conflict(OpsError):
    status = 409


class NotFound(OpsError):
    status = 404


# --- Validaciones ---


def _text(value: str, field: str, max_len: int) -> str:
    value = (value or "").strip()
    if not value or len(value) > max_len or "\x00" in value:
        raise OpsError(f"{field}: entre 1 y {max_len} caracteres")
    return value


def check_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug or "") or slug == ADMIN_SLUG:
        raise OpsError("Slug inválido: minúsculas, números y guiones, de 2 a 80, sin empezar por guion y distinto de admin")
    return slug


def check_amount(value) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise OpsError("El monto tiene que ser un número") from None
    if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
        raise OpsError(f"El monto tiene que estar entre 0 y {MAX_AMOUNT}")
    if amount.as_tuple().exponent < -2:
        raise OpsError("El monto admite hasta 2 decimales")
    return amount


def check_currency(value: str) -> str:
    if not CURRENCY_RE.fullmatch(value or ""):
        raise OpsError("Moneda inválida: tres letras mayúsculas (ARS)")
    return value


def check_email(value: str) -> str:
    email = normalize_email(value or "")
    if "@" not in email or len(email) > EMAIL_MAX or "\x00" in email:
        raise OpsError("Correo inválido")
    return email


def check_password(value: str, min_len: int = PASSWORD_MIN) -> str:
    if not min_len <= len(value or "") <= PASSWORD_MAX or "\x00" in value:
        raise OpsError(f"La clave necesita entre {min_len} y {PASSWORD_MAX} caracteres")
    return value


# --- Tenants ---


def tenant_by_id(s: Session, tenant_id: str, *, lock: bool = False) -> Tenant:
    """Tenant administrable: el admin no está entre ellos."""
    tenant = None
    if ID_RE.fullmatch(tenant_id or ""):
        query = select(Tenant).where(Tenant.id == tenant_id, Tenant.is_admin.is_(False))
        if lock:
            # NO KEY UPDATE: no espera a los cobros en curso (FOR KEY SHARE en auth.charge_caller).
            query = query.with_for_update(key_share=True).execution_options(populate_existing=True)
        tenant = s.scalar(query)
    if tenant is None:
        raise NotFound("No existe ese tenant")
    return tenant


def tenant_by_slug(s: Session, slug: str) -> Tenant:
    tenant = s.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.is_admin.is_(False)))
    if tenant is None:
        raise NotFound(f"No existe el tenant {slug}")
    return tenant


def set_tenant_active(s: Session, tenant: Tenant, active: bool) -> None:
    """Desactivar corta el login, las sesiones (se borran) y la API /v1 (403). Toma la fila con FOR UPDATE:
    espera a los cobros en curso y los que lleguen después dan 403. Reactivar revive las claves no revocadas;
    las sesiones no vuelven."""
    tenant = s.scalar(select(Tenant).where(Tenant.id == tenant.id).with_for_update()
                      .execution_options(populate_existing=True))
    tenant.active = active
    if not active:
        s.execute(delete(UserSession).where(
            UserSession.user_id.in_(select(User.id).where(User.tenant_id == tenant.id))))


def create_tenant(s: Session, slug: str, name: str, amount, currency: str = "ARS") -> Tenant:
    slug = check_slug(slug)
    tenant = Tenant(slug=slug, name=_text(name, "Nombre", NAME_MAX), charge_amount=check_amount(amount),
                    currency=check_currency(currency))
    if s.scalar(select(Tenant.id).where(Tenant.slug == slug)):
        raise Conflict(f"Ya existe el tenant {slug}")
    s.add(tenant)
    s.flush()
    return tenant


def update_tenant(s: Session, tenant: Tenant, *, name: str | None = None, amount=None,
                  currency: str | None = None) -> Tenant:
    """El slug no se edita. El monto nuevo rige para los cobros siguientes."""
    if name is not None:
        tenant.name = _text(name, "Nombre", NAME_MAX)
    if amount is not None:
        tenant.charge_amount = check_amount(amount)
    if currency is not None:
        tenant.currency = check_currency(currency)
    return tenant


def _storable_text(text: str, file: str, max_bytes: int) -> None:
    """Lo que Postgres no guarda en text ni en jsonb (NUL, mitades de surrogate) da 422 y no 500."""
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise OpsError(f"{file}: caracteres inválidos") from None
    if size > max_bytes or "\x00" in text:
        raise OpsError(f"{file}: hasta {max_bytes // 1024} KB, sin caracteres nulos")


def _storable_value(value, file: str, depth: int = 0) -> None:
    """Los escapes \\u0000 y \\ud800 aparecen recién al decodificar el JSON."""
    if depth > FORM_JSON_MAX_DEPTH:
        raise OpsError(f"{file}: demasiados niveles")
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise OpsError(f"{file}: caracteres inválidos") from None
        if "\x00" in value:
            raise OpsError(f"{file}: caracteres inválidos")
    elif isinstance(value, dict):
        for key, item in value.items():
            _storable_value(key, file, depth + 1)
            _storable_value(item, file, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _storable_value(item, file, depth + 1)


def _reject_constant(name: str):
    raise ValueError(f"{name} no es JSON válido")


def _json_text(text: str, file: str) -> dict:
    _storable_text(text, file, FORM_JSON_MAX_BYTES)
    try:
        value = json.loads(text, parse_constant=_reject_constant)
    except ValueError as e:
        raise OpsError(f"{file}: JSON inválido: {e}") from None
    except RecursionError:
        raise OpsError(f"{file}: demasiados niveles") from None
    _storable_value(value, file)
    if not isinstance(value, dict):
        raise OpsError(f"{file}: tiene que ser un objeto JSON")
    return value


def load_form(s: Session, tenant: Tenant, form_html: str, schema_text: str, manifest_text: str) -> int:
    """Carga el formulario y rehace nombres y teléfonos de las fichas, porque el manifiesto decide de dónde
    salen. Bloquea la fila del tenant: dos cargas a la vez no se pisan. Devuelve cuántas fichas rehízo."""
    _storable_text(form_html, "form.html", FORM_HTML_MAX_BYTES)
    schema = _json_text(schema_text, "schema.json")
    raw_manifest = _json_text(manifest_text, "manifest.json")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        raise OpsError(f"schema.json inválido: {e.message}") from None
    try:
        manifest = parse_manifest(raw_manifest)
    except ManifestError as e:
        raise OpsError(f"manifest.json inválido: {e}") from None
    tenant = tenant_by_id(s, tenant.id, lock=True)
    tenant.form_html, tenant.form_schema, tenant.manifest = form_html, schema, raw_manifest
    persons = list(s.scalars(select(Person).where(Person.tenant_id == tenant.id)))
    for person in persons:
        sync_person(s, person, manifest)
    return len(persons)


# --- Usuarios ---


def _close_sessions(s: Session, user: User) -> None:
    s.execute(delete(UserSession).where(UserSession.user_id == user.id))


def user_of(s: Session, tenant: Tenant, user_id: str) -> User:
    user = tenant_get(s, User, tenant.id, user_id) if ID_RE.fullmatch(user_id or "") else None
    if user is None:
        raise NotFound("No existe ese usuario")
    return user


def create_user(s: Session, tenant: Tenant, email: str, password: str, *, min_len: int = PASSWORD_MIN) -> User:
    email = check_email(email)
    check_password(password, min_len)
    if s.scalar(select(User.id).where(User.tenant_id == tenant.id, User.email == email)):
        raise Conflict("Ya existe un usuario con ese correo")
    user = User(tenant_id=tenant.id, email=email, password_hash=hash_password(password))
    s.add(user)
    s.flush()
    return user


def set_password(s: Session, user: User, password: str, *, min_len: int = PASSWORD_MIN) -> None:
    """Cambia la clave y cierra sus sesiones."""
    check_password(password, min_len)
    user.password_hash = hash_password(password)
    _close_sessions(s, user)


def set_user(s: Session, tenant: Tenant, email: str, password: str, *,
             min_len: int = PASSWORD_MIN) -> tuple[User, bool]:
    """Crea el usuario o, si ya existe, le cambia la clave y le cierra las sesiones. (usuario, creado)."""
    email = check_email(email)
    check_password(password, min_len)
    user = s.scalar(select(User).where(User.tenant_id == tenant.id, User.email == email))
    if user is None:
        return create_user(s, tenant, email, password, min_len=min_len), True
    set_password(s, user, password, min_len=min_len)
    return user, False


def set_user_active(s: Session, user: User, active: bool) -> None:
    """Desactivar cierra sus sesiones."""
    user.active = active
    if not active:
        _close_sessions(s, user)


# --- Claves de la API ---


def key_of(s: Session, tenant: Tenant, key_id: str) -> ApiKey:
    key = tenant_get(s, ApiKey, tenant.id, key_id) if ID_RE.fullmatch(key_id or "") else None
    if key is None:
        raise NotFound("No existe esa clave")
    return key


def create_key(s: Session, tenant: Tenant, scope: str, name: str) -> tuple[ApiKey, str]:
    """(fila, clave). La clave se muestra una vez; en la base queda el hash."""
    if scope not in SCOPES:
        raise OpsError(f"Alcance inválido: {' o '.join(SCOPES)}")
    name = _text(name, "Nombre de la clave", KEY_NAME_MAX)
    key, key_hash = new_api_key()
    row = ApiKey(tenant_id=tenant.id, key_hash=key_hash, scope=scope, name=name)
    s.add(row)
    s.flush()
    return row, key


def revoke_key(s: Session, key: ApiKey) -> None:
    """Idempotente: una clave ya revocada conserva su fecha."""
    if key.revoked_at is None:
        key.revoked_at = utcnow()


# --- Tenant admin (solo CLI) ---


def ensure_admin(s: Session, email: str, password: str) -> tuple[User, bool]:
    """Crea el tenant admin si falta y crea o resetea su usuario (clave de 12 o más, cierra sesiones).
    Se niega si ya hay un tenant `admin` común: no se le dan poderes a un tenant de cliente."""
    email = check_email(email)
    check_password(password, ADMIN_PASSWORD_MIN)
    tenant = s.scalar(select(Tenant).where(Tenant.is_admin.is_(True)))
    if tenant is None:
        if s.scalar(select(Tenant.id).where(Tenant.slug == ADMIN_SLUG)):
            raise Conflict("Ya existe un tenant admin común: renombralo o borralo antes de crear el administrador")
        tenant = Tenant(slug=ADMIN_SLUG, name=ADMIN_NAME, charge_amount=Decimal(0), is_admin=True)
        s.add(tenant)
        s.flush()
    return set_user(s, tenant, email, password, min_len=ADMIN_PASSWORD_MIN)
