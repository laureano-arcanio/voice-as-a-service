"""Panel: casos P1-P12 y F1-F15 que aplican (sin F9, F10 ni F14), aislamiento por tenant y link /c/<token>."""
import datetime
import json
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, FORM_EJEMPLO, PASSWORD
from sqlalchemy import func, select, update

from registros import auth, cli
from registros.db import utcnow
from registros.models import AuditLog, Charge, ConversationChoice, Person, PersonPhone, RecordLink, Tenant, UserSession
from registros.panel import pages

API = "/panel/api/persons"
SCHEMA = json.loads((FORM_EJEMPLO / "schema.json").read_text(encoding="utf-8"))
FORM_HTML = (FORM_EJEMPLO / "form.html").read_text(encoding="utf-8")
STATIC = Path(pages.__file__).parent / "static"

# Otro cliente, con otras rutas y otras opciones, sin una línea de código propia: filas variables,
# opciones "No sé" y "No aplica", titular distinto y un aviso sobre datos de alarma.
OTRO_FORM_HTML = """
<fieldset><legend>Paciente</legend>
  <label>Apellido y nombre <input name="paciente.nombre" required></label>
  <label>Teléfono <input name="paciente.telefono"></label>
  <label>Legajo <input name="paciente.legajo"></label>
  <label>¿Fuma? <select name="salud.fuma"><option>Sí</option><option>No</option><option>No sé</option></select></label>
</fieldset>
<fieldset><legend>Domicilio</legend>
  <p>No cargues aquí la contraseña de la alarma: se pide por teléfono.</p>
  <label>Código de alarma <input name="domicilio.alarma"></label>
</fieldset>
<fieldset><legend>Responsable de pago</legend><label>Titular <input name="pago.responsable"></label></fieldset>
<div data-repeat="medicacion" data-add-label="Agregar medicación"><template>
  <label>Droga <input name="medicacion[#].droga"></label>
  <label>Dosis <input name="medicacion[#].dosis"></label>
</template></div>
"""
OTRO_SCHEMA = {
    "type": "object",
    "required": ["paciente", "pago"],
    "properties": {
        "paciente": {
            "type": "object",
            "required": ["nombre", "legajo"],
            "properties": {
                "nombre": {"type": "string", "minLength": 1},
                "telefono": {"type": "string"},
                "legajo": {"type": "string"},
            },
        },
        "salud": {"type": "object", "properties": {"fuma": {"enum": ["Sí", "No", "No sé", "No aplica"]}}},
        "domicilio": {"type": "object", "properties": {"alarma": {"type": "string"}}},
        "pago": {"type": "object", "required": ["responsable"], "properties": {"responsable": {"type": "string"}}},
        "medicacion": {
            "type": "array",
            "items": {"type": "object", "required": ["droga"],
                      "properties": {"droga": {"type": "string"}, "dosis": {"type": "string"}}},
        },
    },
}
OTRO_MANIFEST = {
    "name": "paciente.nombre",
    "titular": "pago.responsable",
    "phone_paths": ["paciente.telefono"],
    "contact_phone_paths": [],
    "filters": ["paciente.legajo"],
}


def ficha(nombre: str = "Ana Prueba", **datos) -> dict:
    return {"datos": {"nombre": nombre, **datos}, "cobertura": {"titular": nombre}}


@pytest.fixture
def tenant_with_form(session, make_tenant):
    def make(slug: str = "uno", html: str = FORM_HTML, schema: dict = SCHEMA, manifest: dict | None = None) -> Tenant:
        tenant = make_tenant(slug, manifest=manifest)
        tenant.form_html, tenant.form_schema = html, schema
        session.commit()
        return tenant

    return make


@pytest.fixture
def uno(tenant_with_form):
    return tenant_with_form("uno")


@pytest.fixture
def dos(tenant_with_form):
    return tenant_with_form("dos", OTRO_FORM_HTML, OTRO_SCHEMA, OTRO_MANIFEST)


@pytest.fixture
def browser(new_client, make_user, login):
    """Navegador con sesión en ese tenant."""

    def make(tenant: Tenant, email: str = "ana@example.com"):
        make_user(tenant, email=email)
        client = new_client()
        assert login(client, tenant, email=email).status_code == 200
        return client

    return make


@pytest.fixture
def make_link(session):
    def make(tenant: Tenant, persons: list[Person], *, token: str = "tokenopaco123", conversation: str = "conv-1",
             expires: datetime.timedelta = datetime.timedelta(days=1)) -> str:
        session.add(RecordLink(token=token, tenant_id=tenant.id, conversation_id=conversation,
                               person_ids=[p.id for p in persons], expires_at=utcnow() + expires))
        session.commit()
        return f"/c/{token}"

    return make


def _no_redirect(client, path: str):
    return client.get(path, follow_redirects=False)


def _next_of(html: str) -> str:
    return re.search(r'data-next="([^"]*)"', html).group(1)


def _audits(session, action: str) -> list[AuditLog]:
    session.expire_all()
    return list(session.scalars(select(AuditLog).where(AuditLog.action == action)))


def _fields(response) -> dict[str, str]:
    assert response.status_code == 422, response.text
    return {item["field"]: item["message"] for item in response.json()["detail"]["fields"]}


# --- P1: login, cierre y sesión vencida ---


@pytest.mark.parametrize("path", ["/personas", "/personas/nueva", "/personas/11111111-1111-1111-1111-111111111111"])
def test_p1_pagina_sin_sesion_va_al_login_y_vuelve(client, path):
    r = _no_redirect(client, path)
    assert r.status_code == 303
    assert client.get(r.headers["location"]).status_code == 200
    assert _next_of(client.get(r.headers["location"]).text) == path


def test_p1_raiz_va_al_listado(client):
    assert _no_redirect(client, "/").headers["location"] == "/personas"


def test_p1_api_sin_sesion_da_401(client):
    assert client.get(API).status_code == 401
    assert client.post(API, json={"data": {}}).status_code == 401


def test_p1_login_correcto_e_incorrecto_abre_el_listado(client, uno, make_user, login):
    make_user(uno)
    assert login(client, uno, password="mala").status_code == 401
    assert _no_redirect(client, "/personas").status_code == 303
    assert login(client, uno).status_code == 200
    assert _no_redirect(client, "/personas").status_code == 200
    assert _no_redirect(client, "/login").headers["location"] == "/personas"


def test_p1_sesion_vencida_y_cierre_vuelven_al_login(browser, uno, session):
    client = browser(uno)
    assert client.get(API).status_code == 200
    session.execute(update(UserSession).values(expires_at=utcnow() - datetime.timedelta(seconds=1)))
    session.commit()
    assert _no_redirect(client, "/personas").status_code == 303
    assert client.get(API).status_code == 401


def test_p1_otro_origen_no_puede_escribir(browser, uno):
    client = browser(uno)
    r = client.post(API, json={"data": ficha()}, headers={"Origin": "https://malo.example"})
    assert r.status_code == 403


# --- next ---


@pytest.mark.parametrize("target", [
    "https://malo.example/",
    "//malo.example",
    "/\\malo.example",
    "/%2f%2fmalo.example",
    "http:/malo.example",
    "javascript:alert(1)",
    "/c/abc/../../malo",
    "/c/abc\nLocation: https://malo.example",
    "/auth/logout",
    "/personas/../login",
    "",
])
def test_next_externo_rechazado(client, uno, make_user, target):
    make_user(uno)
    r = client.get("/login", params={"next": target})
    assert _next_of(r.text) == "/personas"
    assert "malo.example" not in r.text


def test_next_externo_con_sesion_no_sale_del_sitio(browser, uno):
    r = _no_redirect(browser(uno), "/login?next=https://malo.example/")
    assert r.headers["location"] == "/personas"


def test_next_interno_se_conserva_escapado(client):
    assert _next_of(client.get("/login", params={"next": "/c/abc_-123"}).text) == "/c/abc_-123"


# --- Cabeceras y formulario ---


def test_paginas_con_csp_sin_inline_y_sin_cache(browser, uno):
    r = browser(uno).get("/personas/nueva")
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "unsafe-inline" not in csp and "form-action 'self'" in csp
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert not re.search(r"<script(?![^>]*\bsrc=)", r.text)
    assert " style=" not in r.text


@pytest.mark.parametrize("name", ["panel.js", "panel.css", "admin.js"])
def test_estaticos(client, name):
    r = client.get(f"/static/{name}")
    assert r.status_code == 200
    assert r.text == (STATIC / name).read_text(encoding="utf-8")


def test_el_js_no_arma_html_con_datos():
    # Una ficha se pinta con textContent: un nombre con marcado no se ejecuta nunca.
    for name in ("panel.js", "admin.js"):
        assert "innerHTML" not in (STATIC / name).read_text(encoding="utf-8")


def test_datos_de_tenant_y_usuario_escapados(session, browser, tenant_with_form):
    tenant = tenant_with_form("malo")
    tenant.name = "<script>alert(1)</script>"
    session.commit()
    r = browser(tenant).get("/personas")
    assert "<script>alert" not in r.text and "&lt;script&gt;alert" in r.text


def test_form_con_signo_pesos_no_rompe_la_pagina(browser, tenant_with_form):
    tenant = tenant_with_form("pesos", "<label>Monto en $USD ${x} <input name='datos.nombre'></label>")
    r = browser(tenant).get("/personas/nueva")
    assert r.status_code == 200 and "Monto en $USD ${x}" in r.text


def test_tenant_sin_formulario_lo_avisa(session, browser, make_tenant):
    tenant = make_tenant("nuevo")
    client = browser(tenant)
    assert "Falta el formulario" in client.get("/personas/nueva").text
    assert client.post(API, json={"data": ficha()}).status_code == 409
    assert client.get(API).json()["total"] == 0


# --- P2: otro tenant ---


@pytest.mark.parametrize("method, path, body", [
    ("GET", "{api}/{id}", None),
    ("PUT", "{api}/{id}", {"data": {"datos": {"nombre": "Pisada"}}, "version": 1}),
    ("PUT", "{api}/{id}/al-dia", {"al_dia": True}),
    ("DELETE", "{api}/{id}", None),
    ("GET", "/personas/{id}", None),
])
def test_p2_otro_tenant_da_404_y_no_cambia_nada(browser, uno, dos, make_person, session, method, path, body):
    person = make_person(uno, "Ana Ajena")
    client = browser(dos)
    r = client.request(method, path.format(api=API, id=person.id), json=body)
    assert r.status_code == 404
    assert "Ana Ajena" not in r.text
    session.expire_all()
    fresh = session.get(Person, person.id)
    assert (fresh.name, fresh.version, fresh.al_dia, fresh.active) == ("Ana Ajena", 1, False, True)
    assert _audits(session, "person_view") == []


def test_p2_listado_y_busqueda_no_cruzan(browser, uno, dos, make_person):
    make_person(uno, "Ana Ajena", celular="+5493510000001", documento="20000001")
    client = browser(dos)
    assert client.get(API).json() == {"total": 0, "page": 1, "per_page": 50, "items": []}
    for q in ("Ana", "+5493510000001", "20000001"):
        assert client.get(API, params={"q": q}).json()["total"] == 0


def test_p2_ficha_inexistente_y_ajena_responden_igual(browser, uno, dos, make_person):
    person = make_person(uno)
    client = browser(dos)
    ajena = client.get(f"{API}/{person.id}")
    nada = client.get(f"{API}/11111111-1111-1111-1111-111111111111")
    assert (ajena.status_code, ajena.json()) == (nada.status_code, nada.json())
    assert client.get(f"/personas/{person.id}").text == client.get("/personas/11111111-1111-1111-1111-111111111111").text


@pytest.mark.parametrize("bad", ["no-es-id", "x%00y", "a" * 300])
def test_id_raro_da_404(browser, uno, bad):
    client = browser(uno)
    assert client.get(f"{API}/{bad}").status_code == 404
    assert client.get(f"/personas/{bad}").status_code == 404


# --- P12: dos tenants con formularios distintos ---


def test_p12_cada_tenant_ve_su_formulario(browser, uno, dos):
    a, b = browser(uno), browser(dos)
    page_a, page_b = a.get("/personas/nueva").text, b.get("/personas/nueva").text
    assert 'name="datos.nombre"' in page_a and "paciente.nombre" not in page_a
    assert 'name="paciente.nombre"' in page_b and "datos.nombre" not in page_b


def test_p12_cada_tenant_valida_y_extrae_con_lo_suyo(browser, uno, dos, session):
    a, b = browser(uno), browser(dos)
    # La ficha de uno no vale en dos, y al revés.
    assert b.post(API, json={"data": ficha()}).status_code == 422
    assert a.post(API, json={"data": {"paciente": {"nombre": "x"}}}).status_code == 422

    r = b.post(API, json={"data": {"paciente": {"nombre": "Eva", "telefono": "351 15 000-0009", "legajo": "L-7"},
                                   "pago": {"responsable": "Raúl"}}})
    assert r.status_code == 201
    assert (r.json()["name"], r.json()["titular_name"]) == ("Eva", "Raúl")
    assert b.get(API, params={"q": "l7"}).json()["total"] == 1
    assert a.get(API).json()["total"] == 0
    assert session.scalar(select(PersonPhone.phone).where(PersonPhone.person_id == r.json()["id"])) == "543510000009"


def test_p12_tenant_nuevo_por_cli_sin_codigo(session, client, login, make_user):
    parser = cli.build_parser()
    cli.create_tenant(session, parser.parse_args(["create-tenant", "--slug", "nueva", "--name", "Nueva", "--amount", "5"]))
    cli.load_form(session, parser.parse_args(["load-form", "--tenant", "nueva", "--dir", str(FORM_EJEMPLO)]))
    tenant = session.scalar(select(Tenant).where(Tenant.slug == "nueva"))
    make_user(tenant)
    login(client, tenant)
    assert client.post(API, json={"data": ficha("Primera")}).status_code == 201
    assert client.get(API).json()["items"][0]["name"] == "Primera"


# --- P3, P4: listado ---


def test_p3_listado_vacio(browser, uno):
    client = browser(uno)
    assert client.get(API).json()["total"] == 0
    assert 'href="/personas/nueva"' in client.get("/personas").text


def test_p4_paginado(browser, uno, session, make_person):
    for i in range(55):
        session.add(Person(tenant_id=uno.id, name=f"Persona {i:02}", titular_name="T", data={}))
    session.commit()
    client = browser(uno)
    first = client.get(API).json()
    assert (first["total"], len(first["items"]), first["items"][0]["name"]) == (55, 50, "Persona 00")
    second = client.get(API, params={"page": 2}).json()
    assert [item["name"] for item in second["items"]] == [f"Persona {i}" for i in range(50, 55)]
    assert client.get(API, params={"page": 3}).json()["items"] == []
    assert len(client.get(API, params={"per_page": 10}).json()["items"]) == 10
    assert client.get(API, params={"per_page": 1000}).status_code == 422
    assert client.get(API, params={"page": 0}).status_code == 422


def test_el_listado_no_trae_los_datos_de_la_ficha(browser, uno, make_person):
    make_person(uno, documento="20000001", celular="+5493510000001")
    item = browser(uno).get(API).json()["items"][0]
    assert set(item) == {"id", "name", "titular_name", "al_dia", "al_dia_by", "al_dia_at", "updated_at"}


# --- P5, P6: filtros ---


@pytest.mark.parametrize("q", [
    "ana", "ANA GÓ", "gómez",                           # nombre, sin distinguir mayúsculas
    "20000001", "20.000.001", "20 000 001",             # documento normalizado
    "ab-12", "AB12",                                    # código normalizado
    "+5493515551234", "3515551234", "351 15 555-1234", "03515551234",  # teléfono canónico
    "+5493516667777",                                   # teléfono de contacto
])
def test_p5_filtros_normalizados_encuentran(browser, uno, make_person, q):
    make_person(uno, "Ana Gómez", celular="+5493515551234", contactos=["0351 666-7777"],
                documento="20.000.001", codigo="AB-12")
    make_person(uno, "Otra Persona", celular="+5493510000099", documento="30000000", codigo="ZZ")
    items = browser(uno).get(API, params={"q": q}).json()["items"]
    assert [item["name"] for item in items] == ["Ana Gómez"]


@pytest.mark.parametrize("q", ["%", "_", "\\", "'", "\x00", '"', "$.datos", "(", "[*]"])
def test_p5_busqueda_con_caracteres_especiales(browser, uno, make_person, q):
    make_person(uno, "Ana Prueba")
    r = browser(uno).get(API, params={"q": q})
    assert r.status_code == 200
    assert r.json()["total"] == (1 if q == "\x00" else 0)


def test_p5_busqueda_demasiado_larga(browser, uno):
    assert browser(uno).get(API, params={"q": "x" * 201}).status_code == 422


def test_p5_solo_busca_en_las_rutas_del_manifiesto(browser, uno, make_person):
    make_person(uno, "Ana", otro_dato_secreto="diabetes")
    assert browser(uno).get(API, params={"q": "diabetes"}).json()["total"] == 0


def test_p6_filtro_al_dia(browser, uno, make_person):
    make_person(uno, "Al Dia", al_dia=True)
    make_person(uno, "Debe")
    client = browser(uno)
    assert [i["name"] for i in client.get(API, params={"al_dia": "true"}).json()["items"]] == ["Al Dia"]
    assert [i["name"] for i in client.get(API, params={"al_dia": "false"}).json()["items"]] == ["Debe"]
    assert client.get(API).json()["total"] == 2
    assert client.get(API, params={"al_dia": "true", "q": "Debe"}).json()["total"] == 0


# --- P7: al día ---


def test_p7_marcar_y_desmarcar_con_autor_y_fecha(browser, uno, make_person, session):
    person = make_person(uno)
    client = browser(uno)
    url = f"{API}/{person.id}/al-dia"

    r = client.put(url, json={"al_dia": True}).json()
    assert r["al_dia"] is True and r["al_dia_by"] == "ana@example.com" and r["al_dia_at"].endswith("Z")
    detail = client.get(f"{API}/{person.id}").json()
    assert (detail["al_dia"], detail["al_dia_by"], detail["version"]) == (True, "ana@example.com", 1)
    assert client.get(API).json()["items"][0]["al_dia_by"] == "ana@example.com"

    other = browser(uno, email="beto@example.com")
    r = other.put(url, json={"al_dia": False}).json()
    assert (r["al_dia"], r["al_dia_by"]) == (False, "beto@example.com")
    assert {row.detail["al_dia"] for row in _audits(session, "person_al_dia")} == {True, False}


def test_p7_marcar_lo_mismo_no_cambia_el_autor(browser, uno, make_person, session):
    person = make_person(uno)
    url = f"{API}/{person.id}/al-dia"
    browser(uno).put(url, json={"al_dia": True})
    r = browser(uno, email="beto@example.com").put(url, json={"al_dia": True}).json()
    assert r["al_dia_by"] == "ana@example.com"
    assert len(_audits(session, "person_al_dia")) == 1


def test_p7_no_pisa_a_quien_esta_editando(browser, uno, make_person):
    person = make_person(uno)
    client = browser(uno)
    client.put(f"{API}/{person.id}/al-dia", json={"al_dia": True})
    r = client.put(f"{API}/{person.id}", json={"data": ficha("Editada"), "version": 1})
    assert r.status_code == 200 and r.json()["al_dia"] is True


def test_p7_valor_no_booleano(browser, uno, make_person):
    person = make_person(uno)
    assert browser(uno).put(f"{API}/{person.id}/al-dia", json={"al_dia": "quizas"}).status_code == 422


# --- P8, F12: edición y versión ---


def test_p8_version_vieja_da_409_y_no_pierde_nada(browser, uno, make_person, session):
    person = make_person(uno)
    a, b = browser(uno), browser(uno, email="beto@example.com")
    assert a.put(f"{API}/{person.id}", json={"data": ficha("De Ana"), "version": 1}).json()["version"] == 2
    r = b.put(f"{API}/{person.id}", json={"data": ficha("De Beto"), "version": 1})
    assert r.status_code == 409
    assert "De Beto" not in r.text
    session.expire_all()
    assert (session.get(Person, person.id).name, session.get(Person, person.id).version) == ("De Ana", 2)


def test_p8_dos_a_la_vez_gana_uno(browser, uno, make_person, session):
    person = make_person(uno)
    clients = [browser(uno, email=f"u{i}@example.com") for i in range(4)]

    def put(item):
        i, client = item
        return client.put(f"{API}/{person.id}", json={"data": ficha(f"U{i}"), "version": 1}).status_code

    with ThreadPoolExecutor(4) as pool:
        codes = sorted(pool.map(put, enumerate(clients)))
    assert codes == [200, 409, 409, 409]
    session.expire_all()
    assert session.get(Person, person.id).version == 2


def test_put_sin_version(browser, uno, make_person):
    person = make_person(uno)
    assert browser(uno).put(f"{API}/{person.id}", json={"data": ficha()}).status_code == 422


def test_f12_editar_actualiza_telefonos_y_audita_sin_datos(browser, uno, make_person, session):
    person = make_person(uno, celular="+5493510000001")
    client = browser(uno)
    data = ficha("Ana", celular="+5493510000002", documento="diabetes")
    r = client.put(f"{API}/{person.id}", json={"data": data, "version": 1})
    assert r.status_code == 200
    assert r.json()["data"] == data
    session.expire_all()
    phones = list(session.scalars(select(PersonPhone.phone).where(PersonPhone.person_id == person.id)))
    assert phones == ["543510000002"]
    row = _audits(session, "person_update")[0]
    assert row.detail == {"version": 2}


# --- P9: baja ---


def test_p9_baja_deja_de_verse_y_de_identificar(browser, uno, make_person, make_key, session):
    person = make_person(uno, "Ana", celular="+5493510000001")
    key = make_key(uno)
    client = browser(uno)
    assert client.delete(f"{API}/{person.id}").status_code == 204

    assert client.get(API).json()["total"] == 0
    assert client.get(f"{API}/{person.id}").status_code == 404
    assert client.get(f"/personas/{person.id}").status_code == 404
    assert client.put(f"{API}/{person.id}", json={"data": ficha(), "version": 1}).status_code == 404
    assert client.delete(f"{API}/{person.id}").status_code == 404
    session.expire_all()
    assert session.get(Person, person.id).active is False
    assert len(_audits(session, "person_delete")) == 1

    r = client.post("/v1/identify", json={"conversation_id": "7f3c0000-0000-4000-8000-000000000000",
                                          "from": "+5493510000001"},
                    headers={"Authorization": f"Bearer {key}"})
    assert (r.status_code, r.json()["status"]) == (200, "none")


def test_p9_la_baja_conserva_los_cobros(browser, uno, make_person, session):
    person = make_person(uno)
    session.add(Charge(tenant_id=uno.id, conversation_id="c1", person_id=person.id, titular_name="T", amount=Decimal("10"),
                       currency="ARS", from_phone="1", operator_message="ok"))
    session.commit()
    assert browser(uno).delete(f"{API}/{person.id}").status_code == 204
    assert session.scalar(select(func.count()).select_from(Charge)) == 1


# --- P10: cobros ---


def test_p10_cobros_de_la_persona_y_de_nadie_mas(browser, uno, make_person, session):
    person, other = make_person(uno, "Ana"), make_person(uno, "Otra")
    for conversation, target, amount in (("c1", person, "1500.50"), ("c2", other, "9.00")):
        session.add(Charge(tenant_id=uno.id, conversation_id=conversation, person_id=target.id, titular_name=target.name,
                           amount=Decimal(amount), currency="ARS", from_phone="543510000001",
                           operator_message=f"Cobro {conversation}"))
    session.commit()
    charges = browser(uno).get(f"{API}/{person.id}").json()["charges"]
    assert len(charges) == 1
    assert (charges[0]["amount"], charges[0]["currency"], charges[0]["status"], charges[0]["titular_name"],
            charges[0]["operator_message"]) == ("1500.50", "ARS", "simulated", "Ana", "Cobro c1")


# --- P11: auditoría ---


def test_p11_auditoria_de_cada_acceso_y_cambio(browser, uno, session):
    client = browser(uno)
    data = ficha("Ana", documento="20000001")
    person_id = client.post(API, json={"data": data}).json()["id"]
    client.get(f"{API}/{person_id}")
    client.put(f"{API}/{person_id}", json={"data": data, "version": 1})
    client.put(f"{API}/{person_id}/al-dia", json={"al_dia": True})
    client.delete(f"{API}/{person_id}")
    session.expire_all()
    rows = session.scalars(select(AuditLog).where(AuditLog.person_id == person_id).order_by(AuditLog.at)).all()
    assert [row.action for row in rows] == ["person_create", "person_view", "person_update", "person_al_dia",
                                            "person_delete"]
    assert all(row.tenant_id == uno.id and row.user_id for row in rows)
    assert not any("20000001" in str(row.detail) or "Ana" in str(row.detail) for row in rows)


# --- F: formulario ---


def test_f1_ficha_completa_con_secciones_anidadas_se_conserva(browser, dos):
    data = {
        "paciente": {"nombre": "Eva", "telefono": "+5493510000001", "legajo": "1"},
        "salud": {"fuma": "No"},
        "domicilio": {"alarma": "1234"},
        "pago": {"responsable": "Raúl"},
        "medicacion": [{"droga": "A", "dosis": "1"}, {"droga": "B"}],
    }
    client = browser(dos)
    person_id = client.post(API, json={"data": data}).json()["id"]
    assert client.get(f"{API}/{person_id}").json()["data"] == data


@pytest.mark.parametrize("value", ["No sé", "No aplica"])
def test_f2_no_se_y_no_aplica_se_aceptan(browser, dos, value):
    data = {"paciente": {"nombre": "Eva", "legajo": "1", "telefono": value}, "salud": {"fuma": value},
            "pago": {"responsable": "Raúl"}}
    r = browser(dos).post(API, json={"data": data})
    assert r.status_code == 201
    assert r.json()["data"]["paciente"]["telefono"] == value


def test_f2_opcion_fuera_de_la_lista(browser, dos):
    data = {"paciente": {"nombre": "Eva", "legajo": "1"}, "salud": {"fuma": "Tal vez"}, "pago": {"responsable": "R"}}
    r = browser(dos).post(API, json={"data": data})
    assert _fields(r) == {"salud.fuma": "Elegí una de las opciones"}
    assert "Tal vez" not in r.text


def test_f3_faltantes_error_por_campo(browser, dos):
    fields = _fields(browser(dos).post(API, json={"data": {"paciente": {"telefono": "+5493510000001"}}}))
    assert set(fields) == {"paciente.nombre", "paciente.legajo", "pago"}


def test_f3_campo_en_fila_variable(browser, dos):
    data = {"paciente": {"nombre": "Eva", "legajo": "1"}, "pago": {"responsable": "R"},
            "medicacion": [{"droga": "A"}, {"dosis": "2"}]}
    assert set(_fields(browser(dos).post(API, json={"data": data}))) == {"medicacion[1].droga"}


def test_f3_sin_nombre_aunque_el_schema_lo_permita(browser, tenant_with_form):
    tenant = tenant_with_form("libre", schema={"type": "object"})
    assert set(_fields(browser(tenant).post(API, json={"data": {"datos": {"nombre": "   "}}}))) == {"datos.nombre"}


def test_f3_el_error_no_repite_el_valor(browser, uno):
    r = browser(uno).post(API, json={"data": {"datos": {"nombre": "Ana", "documento": 20000001}}})
    assert set(_fields(r)) == {"datos.documento"}
    assert "20000001" not in r.text


@pytest.mark.parametrize("phone, canonical", [
    ("351 15 555-1234", "543515551234"),
    ("+54 9 351 555 1234", "543515551234"),
    ("03515551234", "543515551234"),
])
def test_f4_telefono_con_15_se_normaliza(browser, uno, session, phone, canonical):
    r = browser(uno).post(API, json={"data": ficha(celular=phone)})
    assert r.status_code == 201
    assert session.scalar(select(PersonPhone.phone).where(PersonPhone.person_id == r.json()["id"])) == canonical
    assert r.json()["data"]["datos"]["celular"] == phone


@pytest.mark.parametrize("phone", ["123", "1234567", "1" * 25])
def test_f4_telefono_invalido_error_por_campo(browser, uno, phone):
    fields = _fields(browser(uno).post(API, json={"data": ficha(celular=phone)}))
    assert list(fields) == ["datos.celular"]
    assert "teléfono" in fields["datos.celular"]


def test_f4_telefono_invalido_en_contacto_marca_la_fila(browser, uno):
    data = {**ficha(), "contactos": [{"telefono": "+5493510000001"}, {"telefono": "12"}]}
    assert list(_fields(browser(uno).post(API, json={"data": data}))) == ["contactos[1].telefono"]


def test_f5_telefono_repetido_se_permite_y_advierte(browser, uno, make_person):
    make_person(uno, "Ana Existente", celular="+5493510000001")
    client = browser(uno)
    r = client.post(API, json={"data": {**ficha("Beto"), "contactos": [{"telefono": "351 15 000-0001"}]}})
    assert r.status_code == 201
    warnings = r.json()["warnings"]
    assert [w["field"] for w in warnings] == ["contactos[0].telefono"]
    assert "Ana Existente" in warnings[0]["message"]
    # Guardarla de nuevo no la advierte contra sí misma.
    r2 = client.post(API, json={"data": ficha("Caro", celular="+5493510000099")})
    assert r2.json()["warnings"] == []
    again = client.put(f"{API}/{r2.json()['id']}", json={"data": ficha("Caro", celular="+5493510000099"), "version": 1})
    assert again.json()["warnings"] == []


def test_f5_una_ficha_de_baja_no_advierte(browser, uno, make_person):
    person = make_person(uno, "Dada De Baja", celular="+5493510000001")
    client = browser(uno)
    client.delete(f"{API}/{person.id}")
    assert client.post(API, json={"data": ficha("Beto", celular="+5493510000001")}).json()["warnings"] == []


def test_f5_el_telefono_de_otro_tenant_no_advierte(browser, uno, tenant_with_form, make_person):
    otro = tenant_with_form("tres")
    make_person(otro, "Secreta", celular="+5493510000001")
    r = browser(uno).post(API, json={"data": ficha("Beto", celular="+5493510000001")})
    assert r.json()["warnings"] == []


def test_f6_documento_repetido_se_permite_y_advierte_normalizado(browser, uno, make_person):
    make_person(uno, "Ana", documento="20.000.001")
    r = browser(uno).post(API, json={"data": ficha("Beto", documento="20000001")})
    assert r.status_code == 201
    assert [w["field"] for w in r.json()["warnings"]] == ["datos.documento"]
    assert "Ana" in r.json()["warnings"][0]["message"]


def test_f7_titular_distinto_de_la_persona(browser, uno):
    data = {"datos": {"nombre": "Hijo"}, "cobertura": {"titular": "Madre"}}
    r = browser(uno).post(API, json={"data": data}).json()
    assert (r["name"], r["titular_name"]) == ("Hijo", "Madre")


def test_f7_sin_titular_es_la_persona(browser, uno):
    r = browser(uno).post(API, json={"data": {"datos": {"nombre": "Ana"}}}).json()
    assert r["titular_name"] == "Ana"


def test_f8_filas_variables(browser, dos):
    filas = [{"droga": f"D{i}"} for i in range(30)]
    data = {"paciente": {"nombre": "Eva", "legajo": "1"}, "pago": {"responsable": "R"}, "medicacion": filas}
    client = browser(dos)
    r = client.post(API, json={"data": data})
    assert r.status_code == 201
    assert len(r.json()["data"]["medicacion"]) == 30
    menos = client.put(f"{API}/{r.json()['id']}", json={"data": {**data, "medicacion": filas[:1]}, "version": 1})
    assert len(menos.json()["data"]["medicacion"]) == 1


def test_f11_el_aviso_del_formulario_sale_de_la_base(browser, uno, dos):
    assert "contraseña de la alarma" in browser(dos).get("/personas/nueva").text
    assert "contraseña de la alarma" not in browser(uno).get("/personas/nueva").text


def test_f13_esquema_nuevo_no_rompe_fichas_viejas(browser, uno, session):
    client = browser(uno)
    person_id = client.post(API, json={"data": ficha("Vieja", documento="1")}).json()["id"]
    tenant = session.get(Tenant, uno.id)
    tenant.form_schema = {"type": "object", "required": ["campo_nuevo"]}
    session.commit()

    # Se sigue viendo y marcando; al guardar pide lo nuevo, sin perder la ficha.
    assert client.get(f"{API}/{person_id}").json()["data"]["datos"]["nombre"] == "Vieja"
    assert client.get(API).json()["total"] == 1
    assert client.put(f"{API}/{person_id}/al-dia", json={"al_dia": True}).status_code == 200
    r = client.put(f"{API}/{person_id}", json={"data": ficha("Vieja"), "version": 1})
    assert set(_fields(r)) == {"campo_nuevo"}
    assert client.get(f"{API}/{person_id}").json()["version"] == 1


def test_f15_carga_el_equipo_y_queda_quien(browser, uno, new_client):
    client = browser(uno)
    assert client.post(API, json={"data": ficha()}).json()["created_by"] == "ana@example.com"
    assert new_client().post(API, json={"data": ficha()}).status_code == 401


# --- Lo que jsonb no acepta ---


@pytest.mark.parametrize("raw", [
    '{"data": {"datos": {"nombre": "A\\u0000B"}}}',
    '{"data": {"datos": {"nombre": "A", "codigo": "\\ud800"}}}',
    '{"data": {"datos": {"nombre": "A"}, "x": Infinity}}',
    '{"data": {"datos": {"nombre": "A"}, "x": NaN}}',
])
def test_valor_que_jsonb_no_acepta_da_422(browser, uno, session, raw):
    r = browser(uno).post(API, content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert session.scalar(select(func.count()).select_from(Person)) == 0


def test_ficha_enorme_da_422(browser, uno):
    r = browser(uno).post(API, json={"data": ficha(codigo="x" * 300_000)})
    assert r.status_code == 422


def test_ficha_con_demasiados_niveles_da_422(browser, uno):
    data: dict = ficha()
    for _ in range(40):
        data = {"datos": data["datos"], "x": data}
    assert browser(uno).post(API, json={"data": data}).status_code == 422


@pytest.mark.parametrize("body", [{}, {"data": []}, {"data": "x"}])
def test_cuerpo_sin_objeto_data(browser, uno, body):
    assert browser(uno).post(API, json=body).status_code == 422


# --- Link /c/<token> ---


def test_link_sin_sesion_va_al_login_y_vuelve_a_la_ficha(client, uno, make_user, make_person, make_link, login):
    make_user(uno)
    person = make_person(uno)
    link = make_link(uno, [person])
    r = _no_redirect(client, link)
    assert r.status_code == 303
    assert "/login?next=" in r.headers["location"]
    assert _next_of(client.get(r.headers["location"]).text) == link
    login(client, uno)
    assert _no_redirect(client, link).headers["location"] == f"/personas/{person.id}"


def test_link_sin_sesion_no_delata_si_existe(client, uno, make_person, make_link):
    link = make_link(uno, [make_person(uno)])
    real, falso = _no_redirect(client, link), _no_redirect(client, "/c/noexistenoexiste")
    assert real.status_code == falso.status_code == 303
    assert real.headers["location"].split("next=")[0] == falso.headers["location"].split("next=")[0]


def test_link_con_una_ficha_la_abre_y_lo_audita(browser, uno, make_person, make_link, session):
    person = make_person(uno)
    client = browser(uno)
    link = make_link(uno, [person], token="tokenuno1234")
    assert _no_redirect(client, link).headers["location"] == f"/personas/{person.id}"
    row = _audits(session, "link_open")[0]
    assert (row.tenant_id, row.person_id, row.detail) == (uno.id, person.id, {"conversation_id": "conv-1"})
    assert "tokenuno1234" not in str(row.detail)


def test_link_de_otro_tenant_da_404_y_no_audita(browser, uno, dos, make_person, make_link, session):
    link = make_link(uno, [make_person(uno, "Ana Ajena")])
    client = browser(dos)
    r = _no_redirect(client, link)
    assert r.status_code == 404
    assert "Ana Ajena" not in r.text
    assert r.text == _no_redirect(client, "/c/noexistenoexiste").text
    assert _audits(session, "link_open") == []


def test_link_vencido_va_al_listado(browser, uno, make_person, make_link, session):
    link = make_link(uno, [make_person(uno)], expires=datetime.timedelta(seconds=-1))
    assert _no_redirect(browser(uno), link).headers["location"] == "/personas"
    assert _audits(session, "link_open") == []


def test_link_vencido_de_otro_tenant_sigue_siendo_404(browser, uno, dos, make_person, make_link):
    link = make_link(uno, [make_person(uno)], expires=datetime.timedelta(seconds=-1))
    assert _no_redirect(browser(dos), link).status_code == 404


def test_link_con_varias_muestra_solo_esas(browser, uno, make_person, make_link, session):
    a, b = make_person(uno, "Ana Uno"), make_person(uno, "Beto Dos")
    make_person(uno, "Caro Tres")
    r = _no_redirect(browser(uno), make_link(uno, [a, b]))
    assert r.status_code == 200
    assert "Ana Uno" in r.text and "Beto Dos" in r.text and "Caro Tres" not in r.text
    assert f'href="/personas/{a.id}"' in r.text
    assert {row.person_id for row in _audits(session, "link_open")} == {a.id, b.id}


def test_link_con_nombre_con_marcado_se_escapa(browser, uno, make_person, make_link):
    a, b = make_person(uno, "<img src=x onerror=y>"), make_person(uno, "Beto")
    r = _no_redirect(browser(uno), make_link(uno, [a, b]))
    assert "<img" not in r.text and "&lt;img" in r.text


def test_link_con_eleccion_abre_esa(browser, uno, make_person, make_link, session):
    a, b = make_person(uno, "Ana"), make_person(uno, "Beto")
    link = make_link(uno, [a, b])
    session.add(ConversationChoice(tenant_id=uno.id, conversation_id="conv-1", from_phone="1", refs={},
                                   person_id=b.id, expires_at=utcnow() + datetime.timedelta(hours=1)))
    session.commit()
    assert _no_redirect(browser(uno), link).headers["location"] == f"/personas/{b.id}"


def test_link_sin_eleccion_todavia_muestra_las_varias(browser, uno, make_person, make_link, session):
    a, b = make_person(uno, "Ana"), make_person(uno, "Beto")
    link = make_link(uno, [a, b])
    session.add(ConversationChoice(tenant_id=uno.id, conversation_id="conv-1", from_phone="1", refs={},
                                   person_id=None, expires_at=utcnow() + datetime.timedelta(hours=1)))
    session.commit()
    assert _no_redirect(browser(uno), link).status_code == 200


def test_link_con_una_de_baja_no_la_muestra(browser, uno, make_person, make_link):
    a, b, c = make_person(uno, "Ana"), make_person(uno, "Beto"), make_person(uno, "Caro", active=False)
    r = _no_redirect(browser(uno), make_link(uno, [a, b, c]))
    assert "Caro" not in r.text


def test_link_con_todas_de_baja_va_al_listado(browser, uno, make_person, make_link):
    link = make_link(uno, [make_person(uno, active=False)])
    assert _no_redirect(browser(uno), link).headers["location"] == "/personas"


def test_link_que_apunta_a_ficha_ajena_no_la_muestra(browser, uno, dos, make_person, make_link):
    # No debería poder crearse así, y aun así no cruza.
    ajena = make_person(dos, "Ajena")
    link = make_link(uno, [ajena])
    assert _no_redirect(browser(uno), link).headers["location"] == "/personas"


def test_link_con_token_raro_da_404(browser, uno):
    client = browser(uno)
    assert client.get("/c/x%00y").status_code == 404
    assert client.get(f"/c/{'a' * 200}").status_code == 404


def test_link_y_cookie_lax(client, uno, make_user, login):
    make_user(uno)
    r = login(client, uno)
    assert "samesite=lax" in r.headers["set-cookie"].lower()
    assert auth.SESSION_COOKIE in client.cookies
    assert PASSWORD not in r.text


# --- Páginas del admin ---

ZERO = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def admin_browser(make_admin, new_client):
    make_admin()
    client = new_client()
    r = client.post("/auth/login", json={"tenant": "admin", "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return client


def _admin_paths(tenant_id: str, person_id: str) -> list[str]:
    base = f"/admin/espacios/{tenant_id}"
    return ["/admin", base, f"{base}/fichas", f"{base}/fichas/{person_id}"]


def test_paginas_del_admin_con_admin(admin_browser, uno, make_person):
    person = make_person(uno, "Ana")
    for path in _admin_paths(uno.id, person.id):
        r = admin_browser.get(path)
        assert r.status_code == 200, path
        # Cargan admin.js y no el del panel de fichas.
        assert 'src="/static/admin.js"' in r.text and "panel.js" not in r.text
        csp = r.headers["content-security-policy"]
        assert "unsafe-inline" not in csp and "script-src" not in csp.replace("default-src 'self'", "")
        assert not re.search(r"<script(?![^>]*\bsrc=)", r.text) and " style=" not in r.text
        assert r.headers["cache-control"] == "no-store"


def test_paginas_del_admin_con_cliente_dan_404(browser, uno, dos, make_person):
    person = make_person(dos, "Ana")
    client = browser(uno)
    for path in _admin_paths(dos.id, person.id):
        r = client.get(path)
        assert r.status_code == 404, path
        assert "No encontramos esta página" in r.text and dos.slug not in r.text


def test_paginas_del_admin_sin_sesion_van_al_login_con_next(client, uno, make_person):
    person = make_person(uno, "Ana")
    for path in _admin_paths(uno.id, person.id):
        r = _no_redirect(client, path)
        assert r.status_code == 303
        assert r.headers["location"] == f"/login?next={path.replace('/', '%2F')}"


def test_admin_login_vuelve_a_la_pagina_del_admin(client, uno, make_admin):
    make_admin()
    path = f"/admin/espacios/{uno.id}"
    assert _next_of(client.get("/login", params={"next": path}).text) == path


def test_pagina_del_admin_de_algo_que_no_existe_da_404(admin_browser, uno, dos, make_person, make_admin, session):
    ajena = make_person(dos, "Ajena")
    admin_tenant = session.scalar(select(Tenant).where(Tenant.is_admin))
    assert admin_browser.get(f"/admin/espacios/{ZERO}").status_code == 404
    assert admin_browser.get("/admin/espacios/no-es-un-id").status_code == 404
    assert admin_browser.get(f"/admin/espacios/{admin_tenant.id}").status_code == 404  # el admin no se administra
    assert admin_browser.get(f"/admin/espacios/{uno.id}/fichas/{ZERO}").status_code == 404
    assert admin_browser.get(f"/admin/espacios/{uno.id}/fichas/{ajena.id}").status_code == 404  # ficha de otro espacio


def test_pagina_del_admin_con_ficha_de_baja_da_404(admin_browser, uno, make_person):
    baja = make_person(uno, "Baja", active=False)
    assert admin_browser.get(f"/admin/espacios/{uno.id}/fichas/{baja.id}").status_code == 404


def test_pagina_del_admin_no_escribe_audit(admin_browser, uno, make_person, session):
    person = make_person(uno, "Ana")
    session.expire_all()
    before = len(list(session.scalars(select(AuditLog).where(AuditLog.action.notin_(["login", "logout"])))))
    for path in _admin_paths(uno.id, person.id):
        admin_browser.get(path)
    session.expire_all()
    assert len(list(session.scalars(select(AuditLog).where(AuditLog.action.notin_(["login", "logout"]))))) == before


def test_nombre_del_espacio_escapado_en_paginas_del_admin(admin_browser, uno, session):
    uno.name = "<script>alert(1)</script>"
    session.commit()
    r = admin_browser.get(f"/admin/espacios/{uno.id}")
    assert "<script>alert" not in r.text and "&lt;script&gt;alert" in r.text


def test_paginas_del_cliente_siguen_con_panel_js(browser, uno):
    client = browser(uno)
    for path in ("/personas", "/personas/nueva"):
        r = client.get(path)
        assert 'src="/static/panel.js"' in r.text and "admin.js" not in r.text
    assert 'href="/personas"' in client.get("/personas").text
    assert 'src="/static/panel.js"' in client.get("/login").text


def test_admin_en_paginas_de_fichas_va_al_admin(admin_browser):
    for path in ("/personas", "/personas/nueva"):
        r = _no_redirect(admin_browser, path)
        assert r.status_code == 303 and r.headers["location"] == "/admin"
