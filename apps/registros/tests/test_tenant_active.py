"""Espacio desactivado: sin login, sin sesiones, /v1 en 403; el admin lo sigue viendo; reactivar."""
import threading
import time
import uuid
from urllib.parse import urlsplit

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from sqlalchemy import func, select

from registros import admin_ops
from registros.db import get_sessionmaker
from registros.auth import api_key_hash
from registros.models import ApiKey, Charge, Tenant, User, UserSession

API = "/admin/api"
PHONE = "+5493515551234"


def bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


def v1(client, path: str, key: str, **extra):
    body = {"conversation_id": str(uuid.uuid4()), "from": PHONE, **extra}
    return client.post(f"/v1/{path}", headers=bearer(key), json=body)


@pytest.fixture
def admin(make_admin, new_client):
    make_admin()
    c = new_client()
    r = c.post("/auth/login", json={"tenant": "admin", "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return c


@pytest.fixture
def uno(make_tenant, make_user, make_person):
    tenant = make_tenant("uno")
    make_user(tenant)
    make_person(tenant, celular=PHONE)
    return tenant


@pytest.fixture
def dos(make_tenant, make_user, make_person):
    tenant = make_tenant("dos")
    make_user(tenant)
    make_person(tenant, celular=PHONE)
    return tenant


def set_active(admin, tenant: Tenant, active: bool) -> None:
    r = admin.put(f"{API}/tenants/{tenant.id}/active", json={"active": active})
    assert r.status_code == 204, r.text


def sessions_of(session, tenant: Tenant) -> int:
    session.expire_all()
    count = session.scalar(select(func.count()).select_from(UserSession).join(User)
                           .where(User.tenant_id == tenant.id))
    session.commit()
    return count


def test_desactivar_corta_todo_y_reactivar_lo_devuelve(admin, uno, dos, new_client, login, make_key, session):
    read, charge = make_key(uno, "read"), make_key(uno, "charge")
    read_dos, charge_dos = make_key(dos, "read"), make_key(dos, "charge")
    revoked = make_key(uno, "read", key="reg_prueba_revocada")
    admin_ops.revoke_key(session, admin_ops.key_of(session, uno, _key_id(revoked)))
    session.commit()

    # Sesión abierta y link a una ficha antes de desactivar.
    browser = new_client()
    assert login(browser, uno).status_code == 200
    record = v1(browser, "identify", read).json()["record"]
    link_path = urlsplit(record.rsplit(" ", 1)[1]).path
    r = browser.get(link_path, follow_redirects=False)  # una ficha: redirige a ella
    assert r.status_code == 303 and r.headers["location"].startswith("/personas/")
    other = new_client()
    assert login(other, dos).status_code == 200
    assert sessions_of(session, uno) == 1

    set_active(admin, uno, False)

    assert sessions_of(session, uno) == 0
    assert login(new_client(), uno).status_code == 401
    assert browser.get("/panel/api/persons").status_code == 401
    for path in ("/personas", link_path):
        r = browser.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("/login")
    for path, key in (("identify", read), ("identify", charge), ("identify/select", read), ("charges", charge)):
        r = v1(browser, path, key, ref="r_0000")
        assert r.status_code == 403 and r.json() == {"detail": "Espacio desactivado"}, (path, r.text)
    # Clave revocada o inválida: sigue siendo 401.
    assert v1(browser, "identify", revoked).status_code == 401
    assert v1(browser, "identify", "reg_no_existe").status_code == 401
    assert _count_charges(session) == 0

    # El otro espacio sigue igual.
    assert other.get("/panel/api/persons").status_code == 200
    assert v1(other, "identify", read_dos).status_code == 200
    assert v1(other, "charges", charge_dos).status_code == 200

    # El admin sigue viendo configuración y fichas, y el estado.
    detail = admin.get(f"{API}/tenants/{uno.id}").json()
    assert detail["active"] is False
    assert {t["slug"]: t["active"] for t in admin.get(f"{API}/tenants").json()} == {"uno": False, "dos": True}
    assert admin.get(f"{API}/tenants/{uno.id}/persons").json()["total"] == 1
    assert admin.patch(f"{API}/tenants/{uno.id}", json={"name": "Uno bis"}).status_code == 200

    set_active(admin, uno, True)

    assert admin.get(f"{API}/tenants/{uno.id}").json()["active"] is True
    # Las sesiones no vuelven; el login y las claves no revocadas sí.
    assert browser.get("/panel/api/persons").status_code == 401
    assert login(browser, uno).status_code == 200
    assert browser.get("/panel/api/persons").status_code == 200
    assert v1(browser, "identify", read).status_code == 200
    assert v1(browser, "charges", charge).status_code == 200
    assert v1(browser, "identify", revoked).status_code == 401


def _key_id(key: str) -> str:
    with get_sessionmaker()() as s:
        return s.scalar(select(ApiKey.id).where(ApiKey.key_hash == api_key_hash(key)))


def _count_charges(session) -> int:
    session.expire_all()
    count = session.scalar(select(func.count()).select_from(Charge))
    session.commit()
    return count


def test_login_desactivado_cuenta_para_el_limite(admin, uno, new_client, login, session):
    set_active(admin, uno, False)
    for _ in range(5):
        assert login(new_client(), uno).status_code == 401
    assert login(new_client(), uno).status_code == 429


def test_sesion_de_un_login_en_carrera_se_rechaza(admin, uno, new_client, login, session):
    """Un login que pasó la verificación antes de desactivar deja una sesión: session_user la rechaza."""
    browser = new_client()
    assert login(browser, uno).status_code == 200
    with get_sessionmaker()() as s:
        s.get(Tenant, uno.id).active = False  # sin borrar sesiones, como una carrera
        s.commit()
    assert sessions_of(session, uno) == 1
    assert browser.get("/panel/api/persons").status_code == 401
    assert browser.get("/personas", follow_redirects=False).status_code == 303


def test_tenant_admin_y_cliente_404(admin, uno, new_client, login, session):
    admin_tenant = session.scalar(select(Tenant).where(Tenant.is_admin.is_(True)))
    r = admin.put(f"{API}/tenants/{admin_tenant.id}/active", json={"active": False})
    assert r.status_code == 404
    assert admin.put(f"{API}/tenants/no-es-uuid/active", json={"active": False}).status_code == 404
    client = new_client()
    assert login(client, uno).status_code == 200
    assert client.put(f"{API}/tenants/{uno.id}/active", json={"active": False}).status_code == 404
    assert new_client().put(f"{API}/tenants/{uno.id}/active", json={"active": False}).status_code == 401
    assert admin.put(f"{API}/tenants/{uno.id}/active", json={"active": "quizás"}).status_code == 422
    session.expire_all()
    assert session.get(Tenant, uno.id).active is True
    assert session.get(Tenant, admin_tenant.id).active is True


def test_cobro_durante_la_desactivacion_espera_y_da_403(uno, make_key, client, session):
    charge = make_key(uno, "charge")
    result = {}
    with get_sessionmaker()() as s:
        admin_ops.set_tenant_active(s, admin_ops.tenant_by_id(s, uno.id), False)  # FOR UPDATE, sin commit
        thread = threading.Thread(target=lambda: result.update(r=v1(client, "charges", charge)))
        thread.start()
        time.sleep(0.5)
        assert thread.is_alive()  # espera a la desactivación
        s.commit()
    thread.join(5)
    assert result["r"].status_code == 403
    assert _count_charges(session) == 0


def test_cobro_no_espera_a_editar_el_espacio(uno, make_key, client, session):
    """Editar o recargar el formulario (FOR NO KEY UPDATE) no frena los cobros."""
    charge = make_key(uno, "charge")
    result = {}
    with get_sessionmaker()() as s:
        admin_ops.tenant_by_id(s, uno.id, lock=True)
        thread = threading.Thread(target=lambda: result.update(r=v1(client, "charges", charge)))
        thread.start()
        thread.join(5)
        assert not thread.is_alive()  # terminó con la fila tomada
        s.rollback()
    assert result["r"].status_code == 200 and result["r"].json()["charged"] is True
