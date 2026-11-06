"""Base de prueba y fábricas. Corre con el Postgres de compose.test.yaml (make registros-test)."""
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from registros.auth import api_key_hash, hash_password
from registros.db import Base, get_engine, get_sessionmaker
from registros.main import app
from registros.manifest import parse_manifest, sync_person
from registros.models import ApiKey, Person, Tenant, User

ROOT = Path(__file__).resolve().parent.parent
FORM_EJEMPLO = ROOT / "tests" / "fixtures" / "form_ejemplo"
PASSWORD = "clave-de-prueba"
MANIFEST = {
    "name": "datos.nombre",
    "titular": "cobertura.titular",
    "phone_paths": ["datos.celular", "datos.otro_telefono"],
    "contact_phone_paths": ["contactos[*].telefono"],
    "filters": ["datos.documento", "datos.codigo"],
}


def alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


@pytest.fixture(scope="session", autouse=True)
def migrated():
    command.upgrade(alembic_config(), "head")


@pytest.fixture(autouse=True)
def clean_db(migrated):
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def session():
    with get_sessionmaker()() as s:
        yield s


@pytest.fixture
def client():
    """Un navegador sin sesión. Cada uso de new_client es otro navegador."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def new_client():
    clients = []

    def make() -> TestClient:
        c = TestClient(app)
        clients.append(c)
        return c

    yield make
    for c in clients:
        c.close()


@pytest.fixture
def make_tenant(session):
    def make(slug: str = "uno", amount: str = "1000.00", manifest: dict | None = None) -> Tenant:
        tenant = Tenant(slug=slug, name=slug.capitalize(), charge_amount=Decimal(amount),
                        manifest=manifest if manifest is not None else MANIFEST)
        session.add(tenant)
        session.commit()
        return tenant

    return make


@pytest.fixture
def make_user(session):
    def make(tenant: Tenant, email: str = "ana@example.com", password: str = PASSWORD, active: bool = True) -> User:
        user = User(tenant_id=tenant.id, email=email, password_hash=hash_password(password), active=active)
        session.add(user)
        session.commit()
        return user

    return make


@pytest.fixture
def make_key(session):
    def make(tenant: Tenant, scope: str = "read", key: str | None = None) -> str:
        key = key or f"reg_prueba_{tenant.slug}_{scope}"
        session.add(ApiKey(tenant_id=tenant.id, key_hash=api_key_hash(key), scope=scope, name=scope))
        session.commit()
        return key

    return make


@pytest.fixture
def make_person(session):
    """Ficha con sus teléfonos según el manifiesto del tenant."""

    def make(tenant: Tenant, nombre: str = "Ana Prueba", celular: str | None = None, titular: str | None = None,
             contactos: list[str] | None = None, al_dia: bool = False, active: bool = True, **datos) -> Person:
        data = {
            "datos": {"nombre": nombre, **({"celular": celular} if celular else {}), **datos},
            "cobertura": {"titular": titular or nombre},
            "contactos": [{"telefono": phone} for phone in contactos or []],
        }
        person = Person(tenant_id=tenant.id, name="", titular_name="", data=data, al_dia=al_dia, active=active)
        session.add(person)
        sync_person(session, person, parse_manifest(tenant.manifest))
        session.commit()
        return person

    return make


@pytest.fixture
def login():
    def do(browser: TestClient, tenant: Tenant, email: str = "ana@example.com", password: str = PASSWORD):
        return browser.post("/auth/login", json={"tenant": tenant.slug, "email": email, "password": password})

    return do


ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "clave-del-admin-larga"


@pytest.fixture
def make_admin(session):
    """Tenant admin y su usuario, como create-admin."""
    def make(email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> User:
        from registros import admin_ops

        user, _ = admin_ops.ensure_admin(session, email, password)
        session.commit()
        return user

    return make
