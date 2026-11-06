"""Panel del admin: /admin/api, admin_ops y aislamiento. Nada del admin se escribe en audit_log."""
import datetime
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, FORM_EJEMPLO, MANIFEST, PASSWORD
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from registros import admin_ops
from registros.db import utcnow
from registros.models import ApiKey, AuditLog, Charge, Tenant, User, UserSession

API = "/admin/api"
FORM = {
    "form_html": (FORM_EJEMPLO / "form.html").read_text(encoding="utf-8"),
    "schema": (FORM_EJEMPLO / "schema.json").read_text(encoding="utf-8"),
    "manifest": (FORM_EJEMPLO / "manifest.json").read_text(encoding="utf-8"),
}
ZERO = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def admin(make_admin, new_client):
    """Navegador con sesión de admin."""
    make_admin()
    c = new_client()
    r = c.post("/auth/login", json={"tenant": "admin", "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return c


@pytest.fixture
def uno(make_tenant):
    return make_tenant("uno")


@pytest.fixture
def dos(make_tenant):
    return make_tenant("dos")


def _audit_count(session, *, without_login: bool = True) -> int:
    session.expire_all()
    query = select(func.count()).select_from(AuditLog)
    if without_login:
        query = query.where(AuditLog.action.notin_(["login", "login_failed", "logout"]))
    return session.scalar(query)


def _routes(tenant_id: str, user_id: str = ZERO, key_id: str = ZERO, person_id: str = ZERO):
    return [
        ("get", f"{API}/tenants", None),
        ("post", f"{API}/tenants", {"slug": "nuevo", "name": "Nuevo", "charge_amount": "1"}),
        ("get", f"{API}/tenants/{tenant_id}", None),
        ("patch", f"{API}/tenants/{tenant_id}", {"name": "X"}),
        ("get", f"{API}/tenants/{tenant_id}/form", None),
        ("put", f"{API}/tenants/{tenant_id}/form", FORM),
        ("post", f"{API}/tenants/{tenant_id}/users", {"email": "x@x.com", "password": "una-clave-larga"}),
        ("put", f"{API}/tenants/{tenant_id}/users/{user_id}/password", {"password": "una-clave-larga"}),
        ("put", f"{API}/tenants/{tenant_id}/users/{user_id}/active", {"active": False}),
        ("post", f"{API}/tenants/{tenant_id}/keys", {"scope": "read", "name": "x"}),
        ("delete", f"{API}/tenants/{tenant_id}/keys/{key_id}", None),
        ("get", f"{API}/tenants/{tenant_id}/persons", None),
        ("get", f"{API}/tenants/{tenant_id}/persons/{person_id}", None),
    ]


def _call(client, method, path, body):
    return client.request(method.upper(), path, json=body) if body is not None else client.request(method.upper(), path)


# --- Acceso ---


def test_sin_sesion_401_y_cliente_404_en_todas_las_rutas(client, new_client, uno, make_user, login, session):
    make_user(uno)
    cliente = new_client()
    assert login(cliente, uno).status_code == 200
    for method, path, body in _routes(uno.id):
        assert _call(client, method, path, body).status_code == 401, path
        r = _call(cliente, method, path, body)
        assert r.status_code == 404, path
        assert r.json() == {"detail": "Not Found"}  # igual que una ruta que no existe
    # Ni un cambio del cliente pasó.
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(Tenant)) == 1
    assert session.get(Tenant, uno.id).name == "Uno"


def test_cliente_con_cuerpo_invalido_tambien_404(new_client, uno, make_user, login):
    make_user(uno)
    cliente = new_client()
    login(cliente, uno)
    assert cliente.post(f"{API}/tenants", json={"basura": 1}).status_code == 404


def test_sesion_vencida_401(admin, session):
    session.execute(update(UserSession).values(expires_at=utcnow() - datetime.timedelta(minutes=1)))
    session.commit()
    assert admin.get(f"{API}/tenants").status_code == 401


def test_admin_desactivado_pierde_la_sesion(admin, session):
    session.execute(update(User).where(User.email == ADMIN_EMAIL).values(active=False))
    session.commit()
    assert admin.get(f"{API}/tenants").status_code == 401


def test_origin_ajeno_403(admin):
    r = admin.post(f"{API}/tenants", json={"slug": "nuevo", "name": "N", "charge_amount": "1"},
                   headers={"Origin": "https://malo.example"})
    assert r.status_code == 403


def test_admin_va_a_admin_desde_las_paginas_de_fichas(admin):
    for path in ("/personas", "/personas/nueva", f"/personas/{ZERO}", "/c/abc"):
        r = admin.get(path, follow_redirects=False)
        assert (r.status_code, r.headers["location"]) == (303, "/admin"), path


def test_login_vuelve_a_rutas_del_admin(client):
    tid = "11111111-1111-1111-1111-111111111111"
    for path in ("/admin", f"/admin/espacios/{tid}", f"/admin/espacios/{tid}/fichas",
                 f"/admin/espacios/{tid}/fichas/{tid}"):
        assert f'data-next="{path}"' in client.get(f"/login?next={path}").text, path
    for path in ("/admin/api/tenants", "/admin//malo.example", f"/admin/espacios/{tid}/otra"):
        assert 'data-next="/personas"' in client.get(f"/login?next={path}").text, path


# --- Tenants ---


def test_alta_lista_detalle_y_edicion(admin, make_person, session):
    r = admin.post(f"{API}/tenants", json={"slug": "nuevo", "name": " Nuevo ", "charge_amount": 1500.5,
                                           "currency": "USD", "is_admin": True})
    assert r.status_code == 201
    tenant = r.json()
    assert (tenant["slug"], tenant["name"], tenant["charge_amount"], tenant["currency"], tenant["has_form"]) == \
        ("nuevo", "Nuevo", "1500.50", "USD", False)
    session.expire_all()
    row = session.get(Tenant, tenant["id"])
    assert row.is_admin is False

    row.manifest = MANIFEST
    session.commit()
    make_person(row)
    lista = admin.get(f"{API}/tenants").json()
    assert [t["slug"] for t in lista] == ["nuevo"]  # el admin no está en la lista
    assert (lista[0]["persons_active"], lista[0]["users_active"], lista[0]["keys_active"]) == (1, 0, 0)

    r = admin.patch(f"{API}/tenants/{tenant['id']}", json={"name": "Otro nombre", "charge_amount": "10",
                                                            "slug": "cambiado", "is_admin": True})
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["charge_amount"], r.json()["slug"]) == ("Otro nombre", "10.00", "nuevo")
    session.expire_all()
    assert session.get(Tenant, tenant["id"]).is_admin is False
    detail = admin.get(f"{API}/tenants/{tenant['id']}").json()
    assert detail["users"] == [] and detail["keys"] == []


@pytest.mark.parametrize("slug", ["admin", "A", "a", "-uno", "con espacio", "Mayus", "x" * 81, "uno_dos", "é"])
def test_slug_invalido(admin, slug, session):
    r = admin.post(f"{API}/tenants", json={"slug": slug, "name": "N", "charge_amount": "1"})
    assert r.status_code == 422
    assert session.scalar(select(func.count()).select_from(Tenant)) == 1  # solo el admin


@pytest.mark.parametrize("amount", ["-1", "NaN", "Infinity", "abc", "10000000000", "1.001", "", "1e20"])
def test_monto_invalido(admin, amount):
    r = admin.post(f"{API}/tenants", json={"slug": "nuevo", "name": "N", "charge_amount": amount})
    assert r.status_code == 422, amount


@pytest.mark.parametrize("field, value", [("currency", "ars"), ("currency", "PESO"), ("name", ""), ("name", "x" * 201),
                                          ("name", "a\x00b")])
def test_nombre_y_moneda_invalidos(admin, field, value):
    body = {"slug": "nuevo", "name": "N", "charge_amount": "1", field: value}
    assert admin.post(f"{API}/tenants", json=body).status_code == 422


def test_monto_maximo(admin):
    r = admin.post(f"{API}/tenants", json={"slug": "nuevo", "name": "N", "charge_amount": "9999999999.99"})
    assert r.status_code == 201


def test_alta_repetida_409(admin, uno):
    r = admin.post(f"{API}/tenants", json={"slug": "uno", "name": "N", "charge_amount": "1"})
    assert r.status_code == 409


def test_alta_simultanea_del_mismo_slug_un_201_y_un_409(admin, new_client, session):
    login = {"tenant": "admin", "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    clients = [new_client() for _ in range(4)]
    for c in clients:
        assert c.post("/auth/login", json=login).status_code == 200
    barrier = threading.Barrier(len(clients))

    def alta(c):
        barrier.wait()
        return c.post(f"{API}/tenants", json={"slug": "carrera", "name": "N", "charge_amount": "1"}).status_code

    with ThreadPoolExecutor(len(clients)) as pool:
        codes = sorted(pool.map(alta, clients))
    assert codes.count(201) == 1 and set(codes) <= {201, 409}


def test_tenant_admin_404_en_sus_rutas(admin, session):
    admin_tenant = session.scalar(select(Tenant).where(Tenant.is_admin))
    user = session.scalar(select(User).where(User.tenant_id == admin_tenant.id))
    for method, path, body in _routes(admin_tenant.id, user_id=user.id):
        if path == f"{API}/tenants":
            continue
        assert _call(admin, method, path, body).status_code == 404, path
    # No se le crean usuarios ni claves y su usuario sigue igual.
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(User).where(User.tenant_id == admin_tenant.id)) == 1
    assert session.scalar(select(func.count()).select_from(ApiKey)) == 0
    assert admin.get(f"{API}/tenants").status_code == 200  # sigue con sesión


def test_id_invalido_404(admin):
    assert admin.get(f"{API}/tenants/no-es-un-id").status_code == 404
    assert admin.get(f"{API}/tenants/{ZERO}").status_code == 404


# --- Formulario ---


def test_formulario_carga_baja_y_rehace_fichas(admin, make_tenant, make_person, session):
    tenant = make_tenant("uno", manifest={**MANIFEST, "contact_phone_paths": []})
    make_person(tenant, celular="351 000 0001", contactos=["351 000 0002"])
    assert admin.get(f"{API}/tenants/{tenant.id}/form").status_code == 404  # sin formulario

    r = admin.put(f"{API}/tenants/{tenant.id}/form", json=FORM)
    assert (r.status_code, r.json()) == (200, {"persons_updated": 1})
    bajado = admin.get(f"{API}/tenants/{tenant.id}/form").json()
    assert bajado["form_html"] == FORM["form_html"]
    assert json.loads(bajado["schema"]) == json.loads(FORM["schema"])
    # Lo bajado se puede volver a subir tal cual.
    assert admin.put(f"{API}/tenants/{tenant.id}/form", json=bajado).status_code == 200
    assert admin.get(f"{API}/tenants").json()[0]["has_form"] is True


@pytest.mark.parametrize("field, value", [
    ("manifest", '{"name": "x"}'),
    ("manifest", "no es json"),
    ("manifest", "[]"),
    ("manifest", '{"name": NaN}'),
    ("schema", '{"type": "no-existe"}'),
    ("schema", '{"a": "\\u0000"}'),
    ("schema", '{"a": "\\ud800"}'),
    ("schema", "[" * 5000 + "]" * 5000),
    ("schema", '{"a": "' + "x" * (256 * 1024) + '"}'),
    ("form_html", "<p>\x00</p>"),
    ("form_html", "x" * (512 * 1024 + 1)),
    ("form_html", "\ud800"),
])
def test_formulario_invalido_no_cambia_nada(admin, uno, session, field, value):
    r = admin.put(f"{API}/tenants/{uno.id}/form", json={**FORM, field: value})
    assert r.status_code == 422, r.text
    session.expire_all()
    assert session.get(Tenant, uno.id).form_html is None


def test_cargas_simultaneas_del_formulario(admin, new_client, make_tenant, make_person, session):
    tenant = make_tenant("uno")
    for i in range(20):
        make_person(tenant, nombre=f"Persona {i}", celular=f"351 000 {i:04d}")
    login = {"tenant": "admin", "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    clients = [new_client() for _ in range(4)]
    for c in clients:
        c.post("/auth/login", json=login)
    barrier = threading.Barrier(len(clients))

    def carga(c):
        barrier.wait()
        return c.put(f"{API}/tenants/{tenant.id}/form", json=FORM).status_code

    with ThreadPoolExecutor(len(clients)) as pool:
        assert list(pool.map(carga, clients)) == [200] * len(clients)
    session.expire_all()
    assert session.get(Tenant, tenant.id).manifest == json.loads(FORM["manifest"])


# --- Usuarios ---


def test_usuarios_alta_clave_y_activo(admin, uno, new_client, login, session):
    r = admin.post(f"{API}/tenants/{uno.id}/users", json={"email": " Ana@Example.com ", "password": PASSWORD,
                                                         "is_admin": True})
    assert r.status_code == 201
    user = r.json()
    assert (user["email"], user["active"]) == ("ana@example.com", True)
    assert admin.post(f"{API}/tenants/{uno.id}/users",
                      json={"email": "ana@example.com", "password": PASSWORD}).status_code == 409

    persona = new_client()
    assert login(persona, uno).status_code == 200
    assert persona.get("/auth/me").status_code == 200

    # Nueva clave: cierra sus sesiones.
    url = f"{API}/tenants/{uno.id}/users/{user['id']}"
    assert admin.put(f"{url}/password", json={"password": "corta"}).status_code == 422
    assert admin.put(f"{url}/password", json={"password": "otra-clave-larga"}).status_code == 204
    assert persona.get("/auth/me").status_code == 401
    assert login(persona, uno, password="otra-clave-larga").status_code == 200

    # Desactivar: cierra sus sesiones y no entra; reactivar devuelve el login.
    assert admin.put(f"{url}/active", json={"active": False}).status_code == 204
    assert persona.get("/auth/me").status_code == 401
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id == user["id"])) == 0
    assert login(persona, uno, password="otra-clave-larga").status_code == 401
    assert admin.put(f"{url}/active", json={"active": True}).status_code == 204
    assert login(persona, uno, password="otra-clave-larga").status_code == 200

    detail = admin.get(f"{API}/tenants/{uno.id}").json()
    assert [(u["email"], u["active"]) for u in detail["users"]] == [("ana@example.com", True)]
    assert "password_hash" not in json.dumps(detail)


@pytest.mark.parametrize("body", [
    {"email": "sin-arroba", "password": PASSWORD},
    {"email": "a@" + "x" * 260, "password": PASSWORD},
    {"email": "a@b.c", "password": "corta"},
    {"email": "a@b.c", "password": "x" * 1025},
    {"email": "a\x00@b.c", "password": PASSWORD},
])
def test_usuario_invalido(admin, uno, body):
    assert admin.post(f"{API}/tenants/{uno.id}/users", json=body).status_code == 422


def test_error_no_repite_la_clave(admin, uno):
    r = admin.post(f"{API}/tenants/{uno.id}/users", json={"email": "a@b.c", "password": "sec-123"})
    assert r.status_code == 422 and "sec-123" not in r.text


def test_idor_usuario_y_clave_entre_tenants(admin, uno, dos, make_user, make_key, session):
    ajeno = make_user(dos, email="beto@example.com")
    make_key(dos)
    key_dos = session.scalar(select(ApiKey).where(ApiKey.tenant_id == dos.id))
    assert admin.put(f"{API}/tenants/{uno.id}/users/{ajeno.id}/password",
                     json={"password": "una-clave-larga"}).status_code == 404
    assert admin.put(f"{API}/tenants/{uno.id}/users/{ajeno.id}/active", json={"active": False}).status_code == 404
    assert admin.delete(f"{API}/tenants/{uno.id}/keys/{key_dos.id}").status_code == 404
    session.expire_all()
    assert session.get(User, ajeno.id).active is True
    assert session.get(ApiKey, key_dos.id).revoked_at is None


# --- Claves de la API ---


def test_clave_nueva_identifica_y_revocada_da_401(admin, uno, client, session):
    r = admin.post(f"{API}/tenants/{uno.id}/keys", json={"scope": "read", "name": "pre-call"})
    assert r.status_code == 201
    created = r.json()
    assert created["key"].startswith("reg_") and created["scope"] == "read"
    headers = {"Authorization": f"Bearer {created['key']}"}
    body = {"conversation_id": "7f3c1a52-0e4b-4a7e-9d10-3b2f8c6a1d90", "from": "+5493510000001"}
    assert client.post("/v1/identify", json=body, headers=headers).status_code == 200

    detail = admin.get(f"{API}/tenants/{uno.id}").json()
    assert [(k["name"], k["revoked_at"]) for k in detail["keys"]] == [("pre-call", None)]
    assert created["key"] not in json.dumps(detail)  # la clave no se vuelve a mostrar

    url = f"{API}/tenants/{uno.id}/keys/{created['id']}"
    assert admin.delete(url).status_code == 204
    assert admin.delete(url).status_code == 204  # idempotente
    assert client.post("/v1/identify", json=body, headers=headers).status_code == 401
    assert admin.get(f"{API}/tenants/{uno.id}").json()["keys"][0]["revoked_at"] is not None


@pytest.mark.parametrize("body", [{"scope": "admin", "name": "x"}, {"scope": "read", "name": ""},
                                  {"scope": "read", "name": "x" * 121}])
def test_clave_invalida(admin, uno, body, session):
    assert admin.post(f"{API}/tenants/{uno.id}/keys", json=body).status_code == 422
    assert session.scalar(select(func.count()).select_from(ApiKey)) == 0


# --- Fichas, solo lectura ---


def test_fichas_de_cualquier_espacio_sin_audit(admin, uno, dos, make_person, session):
    ana = make_person(uno, nombre="Ana Uno", celular="351 000 0001")
    beto = make_person(dos, nombre="Beto Dos")
    baja = make_person(uno, nombre="Baja Uno", active=False)
    session.add(Charge(tenant_id=uno.id, conversation_id="c1", person_id=ana.id, titular_name="Ana Uno",
                       amount=Decimal(1000), currency="ARS", from_phone="+5493510000001", operator_message="x"))
    session.commit()

    lista = admin.get(f"{API}/tenants/{uno.id}/persons", params={"q": "ana"}).json()
    assert [p["name"] for p in lista["items"]] == ["Ana Uno"] and lista["total"] == 1
    assert admin.get(f"{API}/tenants/{dos.id}/persons").json()["total"] == 1

    detalle = admin.get(f"{API}/tenants/{uno.id}/persons/{ana.id}").json()
    assert detalle["data"]["datos"]["nombre"] == "Ana Uno" and len(detalle["charges"]) == 1
    assert admin.get(f"{API}/tenants/{uno.id}/persons/{beto.id}").status_code == 404  # de otro espacio
    assert admin.get(f"{API}/tenants/{uno.id}/persons/{baja.id}").status_code == 404  # de baja
    assert admin.get(f"{API}/tenants/{uno.id}/persons", params={"per_page": 101}).status_code == 422
    # Solo lectura: no hay rutas de escritura de fichas.
    assert admin.put(f"{API}/tenants/{uno.id}/persons/{ana.id}", json={"data": {}}).status_code == 405
    assert _audit_count(session) == 0


def test_la_vista_del_cliente_sigue_auditando(new_client, uno, make_user, make_person, login, session):
    make_user(uno)
    ana = make_person(uno)
    c = new_client()
    login(c, uno)
    assert c.get(f"/panel/api/persons/{ana.id}").status_code == 200
    assert session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "person_view")) == 1


# --- Sin audit ---


def test_nada_del_admin_escribe_en_audit_log(admin, make_person, client, session):
    tenant = admin.post(f"{API}/tenants", json={"slug": "nuevo", "name": "N", "charge_amount": "1"}).json()
    tid = tenant["id"]
    admin.patch(f"{API}/tenants/{tid}", json={"charge_amount": "2"})
    admin.put(f"{API}/tenants/{tid}/form", json=FORM)
    user = admin.post(f"{API}/tenants/{tid}/users", json={"email": "a@b.c", "password": PASSWORD}).json()
    admin.put(f"{API}/tenants/{tid}/users/{user['id']}/password", json={"password": "otra-clave-larga"})
    admin.put(f"{API}/tenants/{tid}/users/{user['id']}/active", json={"active": False})
    key = admin.post(f"{API}/tenants/{tid}/keys", json={"scope": "charge", "name": "k"}).json()
    admin.delete(f"{API}/tenants/{tid}/keys/{key['id']}")
    person = make_person(session.get(Tenant, tid))
    admin.get(f"{API}/tenants/{tid}/persons")
    admin.get(f"{API}/tenants/{tid}/persons/{person.id}")
    admin.get(f"{API}/tenants")
    admin.get(f"{API}/tenants/{tid}")
    admin.get(f"{API}/tenants/{tid}/form")
    assert _audit_count(session) == 0
    assert _audit_count(session, without_login=False) == 1  # solo el login del admin


# --- admin_ops ---


def test_ops_create_admin_se_niega_con_un_admin_comun(session, make_tenant):
    make_tenant("admin")
    with pytest.raises(admin_ops.Conflict):
        admin_ops.ensure_admin(session, ADMIN_EMAIL, ADMIN_PASSWORD)
    session.rollback()
    assert session.scalar(select(func.count()).select_from(Tenant).where(Tenant.is_admin)) == 0


def test_ops_un_solo_tenant_admin(session, make_admin):
    make_admin()
    session.add(Tenant(slug="otro-admin", name="X", charge_amount=Decimal(0), is_admin=True))
    with pytest.raises(IntegrityError):  # índice único parcial
        session.commit()
    session.rollback()
