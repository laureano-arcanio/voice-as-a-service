import datetime
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import PASSWORD
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from registros import auth
from registros.audit import record
from registros.db import tenant_get, utcnow
from registros.models import ApiKey, AuditLog, Charge, Person, PersonPhone, User, UserSession


def _login_failures(session) -> int:
    session.expire_all()
    return session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "login_failed"))


# --- Login ---


def test_login_correcto_abre_sesion_con_cookie_lax(client, make_tenant, make_user, login):
    tenant = make_tenant()
    make_user(tenant)
    r = login(client, tenant)
    assert r.status_code == 200
    assert r.json() == {"email": "ana@example.com", "tenant": {"slug": "uno", "name": "Uno"}}
    cookie = r.headers["set-cookie"].lower()
    assert "samesite=lax" in cookie and "httponly" in cookie
    assert client.get("/auth/me").status_code == 200


def test_el_token_de_la_cookie_no_se_guarda(client, make_tenant, make_user, login, session):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    token = client.cookies[auth.SESSION_COOKIE]
    assert session.get(UserSession, token) is None
    assert session.scalar(select(func.count()).select_from(UserSession)) == 1


@pytest.mark.parametrize("email, password", [
    ("ana@example.com", "otra-clave"),
    ("nadie@example.com", PASSWORD),
])
def test_login_incorrecto_da_lo_mismo_sin_decir_que_fallo(client, make_tenant, make_user, login, email, password):
    tenant = make_tenant()
    make_user(tenant)
    r = login(client, tenant, email=email, password=password)
    assert r.status_code == 401
    assert r.json() == {"detail": "Correo o clave incorrectos"}
    assert auth.SESSION_COOKIE not in client.cookies
    assert client.get("/auth/me").status_code == 401


def test_el_correo_no_distingue_mayusculas(client, make_tenant, make_user, login):
    tenant = make_tenant()
    make_user(tenant)
    assert login(client, tenant, email=" ANA@example.com ").status_code == 200


def test_usuario_inactivo_no_entra_y_pierde_la_sesion(client, make_tenant, make_user, login, session):
    tenant = make_tenant()
    make_user(tenant, email="baja@example.com", active=False)
    assert login(client, tenant, email="baja@example.com").status_code == 401

    user = make_user(tenant)
    assert login(client, tenant).status_code == 200
    session.execute(update(User).where(User.id == user.id).values(active=False))
    session.commit()
    assert client.get("/auth/me").status_code == 401


def test_sesion_vencida(client, make_tenant, make_user, login, session):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    session.execute(update(UserSession).values(expires_at=utcnow() - datetime.timedelta(seconds=1)))
    session.commit()
    assert client.get("/auth/me").status_code == 401
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(UserSession)) == 0


def test_logout_revoca_la_sesion_aunque_se_guarde_la_cookie(client, make_tenant, make_user, login, session):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    token = client.cookies[auth.SESSION_COOKIE]
    assert client.post("/auth/logout").status_code == 204
    client.cookies.set(auth.SESSION_COOKIE, token)
    assert client.get("/auth/me").status_code == 401
    assert session.scalar(select(AuditLog.action).where(AuditLog.action == "logout")) == "logout"


def test_rotar_el_secreto_invalida_las_sesiones(client, make_tenant, make_user, login, monkeypatch):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    monkeypatch.setattr(auth.settings, "session_secret", "otro-secreto")
    assert client.get("/auth/me").status_code == 401


def test_sin_secreto_no_hay_login(client, make_tenant, make_user, login, monkeypatch):
    tenant = make_tenant()
    make_user(tenant)
    monkeypatch.setattr(auth.settings, "session_secret", "")
    assert login(client, tenant).status_code == 503


# --- Límite de intentos ---


def _fail(browser, tenant, login, times, email="ana@example.com"):
    return [login(browser, tenant, email=email, password="mala").status_code for _ in range(times)]


def test_cinco_fallidos_bloquean_el_correo_aun_con_la_clave_correcta(client, make_tenant, make_user, login, session):
    tenant = make_tenant()
    make_user(tenant)
    assert _fail(client, tenant, login, 5) == [401] * 5
    r = login(client, tenant)
    assert r.status_code == 429
    assert r.headers["retry-after"] == "900"
    assert _login_failures(session) == 5  # el rechazado no suma


def test_el_limite_vence_a_los_15_minutos(client, make_tenant, make_user, login, session):
    tenant = make_tenant()
    make_user(tenant)
    _fail(client, tenant, login, 5)
    assert login(client, tenant).status_code == 429
    session.execute(update(AuditLog).values(at=utcnow() - datetime.timedelta(minutes=15, seconds=1)))
    session.commit()
    assert login(client, tenant).status_code == 200


def test_cuatro_fallidos_todavia_dejan_entrar(client, make_tenant, make_user, login):
    tenant = make_tenant()
    make_user(tenant)
    _fail(client, tenant, login, 4)
    assert login(client, tenant).status_code == 200


def test_el_limite_es_por_correo(client, make_tenant, make_user, login):
    tenant = make_tenant()
    make_user(tenant)
    make_user(tenant, email="otra@example.com")
    _fail(client, tenant, login, 5)
    assert login(client, tenant).status_code == 429
    assert login(client, tenant, email="otra@example.com").status_code == 200


def test_el_limite_cuenta_correos_sin_usuario_y_mayusculas(client, make_tenant, login):
    tenant = make_tenant()
    results = [login(client, tenant, email=e, password="mala").status_code
               for e in ("x@example.com", "X@example.com", " x@EXAMPLE.com", "x@example.com", "x@example.com",
                         "x@example.com")]
    assert results == [401] * 5 + [429]


def test_login_contra_tenant_inexistente_tambien_cuenta(client, make_tenant, make_user, session):
    tenant = make_tenant()
    make_user(tenant)
    body = {"tenant": "no-existe", "email": "ana@example.com", "password": PASSWORD}
    assert [client.post("/auth/login", json=body).status_code for _ in range(5)] == [401] * 5
    assert client.post("/auth/login", json={**body, "tenant": tenant.slug}).status_code == 429


def test_en_paralelo_no_se_verifican_mas_de_cinco_claves(make_tenant, make_user, new_client, session):
    tenant = make_tenant()
    make_user(tenant)
    body = {"tenant": tenant.slug, "email": "ana@example.com", "password": "mala"}

    with ThreadPoolExecutor(7) as pool:
        codes = list(pool.map(lambda _: new_client().post("/auth/login", json=body).status_code, range(20)))
    # Bajo ataque puede rechazar de más, nunca verificar de más.
    assert codes.count(401) <= 5
    assert codes.count(401) + codes.count(429) == 20
    assert _login_failures(session) == codes.count(401)


def test_clave_enorme_se_rechaza_sin_verificar(client, make_tenant, login, session):
    tenant = make_tenant()
    r = login(client, tenant, password="x" * 2000)
    assert r.status_code == 422
    assert _login_failures(session) == 0


# JSON crudo: "\u0000" y un surrogate suelto llegan así al servidor, y Postgres no los guarda.
@pytest.mark.parametrize("tenant_slug, email", [
    (r"a\u0000b", "ana@example.com"),
    ("uno", r"a\u0000@example.com"),
    (r"\ud800", "ana@example.com"),
    ("uno", r"\ud800@example.com"),
])
def test_login_con_caracteres_que_la_base_no_guarda_da_422(client, make_tenant, make_user, session, tenant_slug, email):
    make_user(make_tenant())
    body = f'{{"tenant":"{tenant_slug}","email":"{email}","password":"{PASSWORD}"}}'
    r = client.post("/auth/login", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert "input" not in r.text
    assert _login_failures(session) == 0


@pytest.mark.parametrize("password", [r"x\u0000y", r"\ud800"])
def test_clave_con_caracteres_raros_no_da_500(client, make_tenant, make_user, session, password):
    # La clave no va a la base: el NUL es un intento fallido más, y el surrogate no llega a argon2.
    make_user(make_tenant())
    body = f'{{"tenant":"uno","email":"ana@example.com","password":"{password}"}}'
    r = client.post("/auth/login", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code in (401, 422)
    assert auth.SESSION_COOKIE not in client.cookies


# --- CSRF ---


@pytest.mark.parametrize("headers, status", [
    ({"Origin": "https://malo.example"}, 403),
    ({"Origin": "null"}, 403),
    ({"Origin": "http://registros.test.malo.example"}, 403),
    ({"Sec-Fetch-Site": "cross-site"}, 403),
    ({"Sec-Fetch-Site": "same-site"}, 403),
    ({"Origin": "http://registros.test"}, 200),   # REGISTROS_PUBLIC_URL
    ({"Origin": "http://testserver"}, 200),       # mismo Host
    ({"Sec-Fetch-Site": "same-origin"}, 200),
    ({}, 200),                                    # sin navegador
])
def test_login_valida_el_origen(client, make_tenant, make_user, headers, status):
    tenant = make_tenant()
    make_user(tenant)
    body = {"tenant": tenant.slug, "email": "ana@example.com", "password": PASSWORD}
    assert client.post("/auth/login", json=body, headers=headers).status_code == status


def test_pedido_de_otro_origen_con_sesion_no_cierra_nada(client, make_tenant, make_user, login):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    assert client.post("/auth/logout", headers={"Origin": "https://malo.example"}).status_code == 403
    assert client.get("/auth/me").status_code == 200


def test_get_no_exige_origen(client, make_tenant, make_user, login):
    tenant = make_tenant()
    make_user(tenant)
    login(client, tenant)
    assert client.get("/auth/me", headers={"Origin": "https://malo.example"}).status_code == 200


def test_con_authorization_no_aplica_el_origen(client):
    # Lo rechaza la autenticación de quien corresponda, no el CSRF.
    r = client.post("/v1/no-existe", headers={"Origin": "https://malo.example", "Authorization": "Bearer x"})
    assert r.status_code != 403


# --- Aislamiento por tenant ---


def test_usuario_de_otro_tenant_no_entra_a_este(client, make_tenant, make_user, login):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    make_user(uno)
    assert login(client, dos).status_code == 401


def test_mismo_correo_en_dos_tenants_son_dos_usuarios(new_client, make_tenant, make_user, login):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    make_user(uno, password="clave-de-uno")
    make_user(dos, password="clave-de-dos")
    a, b = new_client(), new_client()
    assert login(a, uno, password="clave-de-uno").status_code == 200
    assert login(b, dos, password="clave-de-dos").status_code == 200
    assert a.get("/auth/me").json()["tenant"]["slug"] == "uno"
    assert b.get("/auth/me").json()["tenant"]["slug"] == "dos"


def test_tenant_get_no_devuelve_filas_de_otro_tenant(session, make_tenant, make_person):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    person = make_person(uno)
    assert tenant_get(session, Person, uno.id, person.id).id == person.id
    assert tenant_get(session, Person, dos.id, person.id) is None
    assert tenant_get(session, Person, uno.id, "no-existe") is None


@pytest.mark.parametrize("build", [
    lambda dos, person: PersonPhone(tenant_id=dos, person_id=person, phone="543510000009", relation="contacto"),
    lambda dos, person: Charge(tenant_id=dos, conversation_id="c", person_id=person, titular_name="x", amount=1,
                               currency="ARS", from_phone="1", operator_message="x"),
])
def test_la_base_rechaza_una_fila_que_apunta_a_una_ficha_ajena(session, make_tenant, make_person, build):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    person = make_person(uno)
    session.add(build(dos.id, person.id))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_el_audit_de_un_login_queda_en_su_tenant(client, make_tenant, make_user, login, session):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    user = make_user(uno)
    login(client, uno)
    login(client, dos, password="mala")
    rows = {row.action: row for row in session.scalars(select(AuditLog))}
    assert (rows["login"].tenant_id, rows["login"].user_id) == (uno.id, user.id)
    assert (rows["login_failed"].tenant_id, rows["login_failed"].user_id) == (dos.id, None)
    assert PASSWORD not in str(rows["login"].detail)


def test_audit_record_con_ficha(session, make_tenant, make_user, make_person):
    tenant = make_tenant()
    user, person = make_user(tenant), make_person(tenant)
    record(session, tenant.id, "person_view", user_id=user.id, person_id=person.id, detail={"via": "link"})
    session.commit()
    row = session.scalar(select(AuditLog).where(AuditLog.action == "person_view"))
    assert (row.tenant_id, row.user_id, row.person_id, row.detail) == (tenant.id, user.id, person.id, {"via": "link"})


# --- Claves de la API ---


@pytest.fixture
def key_app():
    """App mínima con las dependencias que usa la API."""
    probe = FastAPI()

    @probe.get("/read")
    def read(caller: auth.Reader):
        return {"tenant": caller.tenant_id, "scope": caller.scope}

    @probe.get("/charge")
    def charge(caller: auth.Charger):
        return {"tenant": caller.tenant_id}

    return TestClient(probe)


def _bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


def test_alcances(key_app, make_tenant, make_key):
    tenant = make_tenant()
    read, charge = make_key(tenant, "read"), make_key(tenant, "charge")
    assert key_app.get("/read", headers=_bearer(read)).json() == {"tenant": tenant.id, "scope": "read"}
    assert key_app.get("/read", headers=_bearer(charge)).status_code == 200
    assert key_app.get("/charge", headers=_bearer(charge)).json() == {"tenant": tenant.id}
    assert key_app.get("/charge", headers=_bearer(read)).status_code == 403


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer no-existe"}, {"Authorization": "Basic x"},
                                     {"Authorization": "Bearer "}])
def test_sin_clave_valida_401(key_app, headers):
    assert key_app.get("/read", headers=headers).status_code == 401


def test_clave_revocada_401(key_app, make_tenant, make_key, session):
    key = make_key(make_tenant())
    assert key_app.get("/read", headers=_bearer(key)).status_code == 200
    session.execute(update(ApiKey).values(revoked_at=utcnow()))
    session.commit()
    assert key_app.get("/read", headers=_bearer(key)).status_code == 401


def test_la_clave_identifica_a_su_tenant(key_app, make_tenant, make_key):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    assert key_app.get("/read", headers=_bearer(make_key(uno))).json()["tenant"] == uno.id
    assert key_app.get("/read", headers=_bearer(make_key(dos))).json()["tenant"] == dos.id
