"""Contrato de /v1: identificación por teléfono y cobro simulado."""
import datetime
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from urllib.parse import urlsplit

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from registros.db import utcnow
from registros.models import ApiKey, Charge, ConversationChoice, Person, RecordLink

PHONE = "+5493515551234"
CANONICAL = "543515551234"
OTHER_PHONE = "+5493515559999"
IDENTIFY_FIELDS = {"status", "name", "al_dia", "candidates", "record", "operator_note"}
SELECT_FIELDS = {"status", "name", "al_dia", "record", "operator_note"}


def conv() -> str:
    return str(uuid.uuid4())


def bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture
def tenant(make_tenant):
    return make_tenant()


@pytest.fixture
def read_key(tenant, make_key):
    return make_key(tenant, "read")


@pytest.fixture
def charge_key(tenant, make_key):
    return make_key(tenant, "charge")


def identify(client, key, conversation_id, phone=PHONE):
    r = client.post("/v1/identify", headers=bearer(key), json={"conversation_id": conversation_id, "from": phone})
    assert r.status_code == 200, r.text
    assert set(r.json()) == IDENTIFY_FIELDS
    return r.json()


def choose(client, key, conversation_id, ref, phone=PHONE):
    r = client.post("/v1/identify/select", headers=bearer(key),
                    json={"conversation_id": conversation_id, "from": phone, "ref": ref})
    assert r.status_code == 200, r.text
    assert set(r.json()) == SELECT_FIELDS
    return r.json()


def charge(client, key, conversation_id, phone=PHONE):
    r = client.post("/v1/charges", headers=bearer(key), json={"conversation_id": conversation_id, "from": phone})
    assert r.status_code == 200, r.text
    return r.json()


def refs_of(candidates: str) -> dict[str, str]:
    """{etiqueta: ref} de "María G. (r_1b2c); Juan G. (r_3d4e)"."""
    pairs = (item.rsplit(" (", 1) for item in candidates.split("; "))
    return {label: ref.rstrip(")") for label, ref in pairs}


def charges(session) -> list[Charge]:
    session.expire_all()
    rows = list(session.scalars(select(Charge)))
    session.commit()
    return rows


def token_of(record: str) -> str:
    return urlsplit(record.rsplit(" ", 1)[1]).path.removeprefix("/c/")


def link(session, token: str) -> RecordLink:
    session.expire_all()
    row = session.get(RecordLink, token)
    session.commit()
    return row


# --- Identidad ---


def test_titular(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE, al_dia=True)
    data = identify(client, read_key, conv())
    assert data["status"] == "single"
    assert data["name"] == "María Gómez"
    assert data["al_dia"] is True
    assert data["candidates"] is None
    assert data["operator_note"] == "María Gómez, titular, al día"
    assert data["record"].startswith("Ficha: http://registros.test/c/")


def test_titular_que_no_esta_al_dia(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE)
    data = identify(client, read_key, conv())
    assert data["al_dia"] is False
    assert data["operator_note"] == "María Gómez, titular, no está al día"


def test_contacto(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", contactos=[PHONE])
    data = identify(client, read_key, conv())
    assert data["status"] == "single"
    assert data["name"] == "Contacto de María Gómez"
    assert data["operator_note"] == "Contacto de María Gómez, no está al día"


@pytest.mark.parametrize("phone", ["+543515551234", "03515551234", "3515551234", "5493515551234"])
def test_identifica_con_cualquier_forma_del_numero(client, read_key, tenant, make_person, phone):
    make_person(tenant, "María Gómez", celular=PHONE)
    assert identify(client, read_key, conv(), phone)["status"] == "single"


def test_desconocido(client, read_key, tenant, session):
    data = identify(client, read_key, conv(), OTHER_PHONE)
    assert data == {"status": "none", "name": None, "al_dia": None, "candidates": None,
                    "record": "Sin ficha", "operator_note": "Sin ficha"}
    assert session.scalar(select(func.count()).select_from(RecordLink)) == 0


@pytest.mark.parametrize("phone", ["", None, "anonymous", "1234567"])
def test_vacio_u_oculto(client, read_key, tenant, make_person, phone):
    make_person(tenant, "María Gómez", celular=PHONE)
    assert identify(client, read_key, conv(), phone) == {
        "status": "no_number", "name": None, "al_dia": None, "candidates": None,
        "record": "Sin teléfono", "operator_note": "Sin teléfono"}


def test_sin_campo_from(client, read_key, tenant):
    r = client.post("/v1/identify", headers=bearer(read_key), json={"conversation_id": conv()})
    assert (r.status_code, r.json()["status"]) == (200, "no_number")


def test_ficha_de_baja_no_se_encuentra(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE, active=False)
    assert identify(client, read_key, conv())["status"] == "none"


def test_baja_no_cuenta_entre_varias(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE, active=False)
    assert identify(client, read_key, conv())["name"] == "María Gómez"


def test_prueba_sin_datos_y_sin_fila(client, read_key, tenant, make_person, session):
    make_person(tenant, "María Gómez", celular=PHONE)
    assert identify(client, read_key, "prueba") == {
        "status": "test", "name": None, "al_dia": None, "candidates": None, "record": None, "operator_note": None}
    assert session.scalar(select(func.count()).select_from(RecordLink)) == 0
    assert session.scalar(select(func.count()).select_from(ConversationChoice)) == 0


# --- Lista permitida ---


def test_ninguna_respuesta_lleva_datos_de_la_ficha(client, read_key, charge_key, tenant, make_person):
    secretos = {"documento": "20123456", "diagnostico": "Asma severa", "codigo": "COD-77"}
    make_person(tenant, "María Gómez", celular=PHONE, **secretos)
    make_person(tenant, "Juan Gómez", celular=PHONE, **secretos)
    make_person(tenant, "Solo Una", celular=OTHER_PHONE, contactos=["+5493515550000"], **secretos)
    multi = conv()
    listed = identify(client, read_key, multi)
    selected = choose(client, read_key, multi, refs_of(listed["candidates"])["Juan G."])
    single = identify(client, read_key, conv(), OTHER_PHONE)
    charged = charge(client, charge_key, multi)
    assert set(charged) == {"charged", "operator_message"}
    text = json.dumps([listed, selected, single, charged], ensure_ascii=False)
    for forbidden in [*secretos.values(), PHONE, CANONICAL, "3515551234", "3515559999", "3515550000"]:
        assert forbidden not in text


def test_error_de_validacion_no_repite_lo_recibido(client, read_key):
    r = client.post("/v1/identify", headers=bearer(read_key), json={"conversation_id": conv(), "from": PHONE * 20})
    assert r.status_code == 422
    assert "351555" not in r.text


# --- Varias fichas ---


def test_varias_fichas_lista_limitada(client, read_key, tenant, make_person):
    for nombre in ["Ana Uno", "Beto Dos", "Carla Tres", "Dani Cuatro", "Eva Cinco"]:
        make_person(tenant, nombre, celular=PHONE, documento="20123456")
    data = identify(client, read_key, conv())
    assert data["status"] == "multiple"
    assert data["name"] is None and data["al_dia"] is None
    assert data["operator_note"] == "Teléfono en 5 fichas, sin elegir todavía"
    assert data["record"].startswith("Este teléfono está en 5 fichas: http://registros.test/c/")
    assert set(refs_of(data["candidates"])) == {"Ana U.", "Beto D.", "Carla T.", "Dani C.", "Eva C."}
    assert all(ref.startswith("r_") for ref in refs_of(data["candidates"]).values())


def test_mas_de_cinco_sin_lista_y_sin_cobro(client, read_key, charge_key, tenant, make_person, session):
    for i in range(6):
        make_person(tenant, f"Persona {i}", celular=PHONE)
    conversation_id = conv()
    data = identify(client, read_key, conversation_id)
    assert data["status"] == "too_many"
    assert data["candidates"] is None
    assert "6 fichas" in data["record"]
    assert len(link(session, token_of(data["record"])).person_ids) == 6
    assert charge(client, charge_key, conversation_id) == {
        "charged": False, "operator_message": "Este teléfono está en 6 fichas y no se eligió ninguna: no se cobró."}


def test_elegir_cobra_a_esa(client, read_key, charge_key, tenant, make_person, session):
    make_person(tenant, "María Gómez", celular=PHONE, al_dia=True)
    juan = make_person(tenant, "Juan Gómez", celular=PHONE, titular="Juan Titular", al_dia=False)
    conversation_id = conv()
    refs = refs_of(identify(client, read_key, conversation_id)["candidates"])
    selected = choose(client, read_key, conversation_id, refs["Juan G."])
    assert selected["status"] == "selected"
    assert selected["name"] == "Juan Gómez"
    assert selected["al_dia"] is False
    assert selected["operator_note"] == "Juan Gómez, no está al día"
    assert charge(client, charge_key, conversation_id) == {
        "charged": True, "operator_message": "Cobro registrado al titular Juan Titular, que no está al día."}
    assert [row.person_id for row in charges(session)] == [juan.id]


def test_vale_la_ultima_eleccion(client, read_key, charge_key, tenant, make_person, session):
    maria = make_person(tenant, "María Gómez", celular=PHONE, al_dia=True)
    make_person(tenant, "Juan Gómez", celular=PHONE, al_dia=True)
    conversation_id = conv()
    refs = refs_of(identify(client, read_key, conversation_id)["candidates"])
    choose(client, read_key, conversation_id, refs["Juan G."])
    choose(client, read_key, conversation_id, refs["María G."])
    charge(client, charge_key, conversation_id)
    assert [row.person_id for row in charges(session)] == [maria.id]


def test_sin_elegir_no_cobra(client, read_key, charge_key, tenant, make_person, session):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE)
    conversation_id = conv()
    identify(client, read_key, conversation_id)
    assert charge(client, charge_key, conversation_id) == {
        "charged": False, "operator_message": "Este teléfono está en 2 fichas y no se eligió ninguna: no se cobró."}
    assert charges(session) == []


def test_identify_despues_de_elegir_no_reabre_la_lista(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE)
    conversation_id = conv()
    first = identify(client, read_key, conversation_id)
    choose(client, read_key, conversation_id, refs_of(first["candidates"])["Juan G."])
    again = identify(client, read_key, conversation_id)
    assert again["status"] == "single"
    assert again["name"] == "Juan Gómez"
    assert token_of(again["record"]) == token_of(first["record"])


def test_misma_conversacion_reutiliza_refs_y_token(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE)
    conversation_id = conv()
    assert identify(client, read_key, conversation_id) == identify(client, read_key, conversation_id)


def test_identify_simultaneos_dan_las_mismas_refs(client, read_key, tenant, make_person, session):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE)
    conversation_id = conv()
    barrier = threading.Barrier(5)

    def call(_):
        barrier.wait()
        return identify(client, read_key, conversation_id)

    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(call, range(5)))
    assert all(result == results[0] for result in results)
    assert session.scalar(select(func.count()).select_from(RecordLink)) == 1


# --- ref ---


@pytest.fixture
def listed(client, read_key, tenant, make_person):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE)
    conversation_id = conv()
    refs = refs_of(identify(client, read_key, conversation_id)["candidates"])
    return conversation_id, refs["Juan G."]


NULL_SELECT = {"status": "invalid", "name": None, "al_dia": None, "record": None, "operator_note": None}


def test_ref_inventada(client, read_key, listed):
    assert choose(client, read_key, listed[0], "r_zzzz") == NULL_SELECT


def test_ref_de_otra_conversacion(client, read_key, tenant, make_person, listed):
    assert choose(client, read_key, conv(), listed[1]) == NULL_SELECT
    # Otra conversación con la misma lista tiene sus propias refs. Son al azar: puede repetirse una.
    otra = conv()
    if listed[1] not in refs_of(identify(client, read_key, otra)["candidates"]).values():
        assert choose(client, read_key, otra, listed[1]) == NULL_SELECT


def test_ref_de_otro_from(client, read_key, listed):
    assert choose(client, read_key, listed[0], listed[1], OTHER_PHONE) == NULL_SELECT


def test_ref_con_from_vacio(client, read_key, listed):
    assert choose(client, read_key, listed[0], listed[1], "") == NULL_SELECT


def test_ref_vencida(client, read_key, charge_key, listed, session):
    session.execute(update(ConversationChoice).values(expires_at=utcnow() - datetime.timedelta(seconds=1)))
    session.commit()
    assert choose(client, read_key, listed[0], listed[1]) == NULL_SELECT
    assert charge(client, charge_key, listed[0])["charged"] is False


def test_ref_de_ficha_dada_de_baja(client, read_key, listed, session):
    session.execute(update(Person).where(Person.name == "Juan Gómez").values(active=False))
    session.commit()
    assert choose(client, read_key, listed[0], listed[1]) == NULL_SELECT


def test_select_prueba(client, read_key, listed):
    assert choose(client, read_key, "prueba", listed[1])["status"] == "test"


def test_identify_cambia_de_from_invalida_las_refs(client, read_key, tenant, make_person, listed):
    make_person(tenant, "Otra Uno", celular=OTHER_PHONE)
    make_person(tenant, "Otra Dos", celular=OTHER_PHONE)
    identify(client, read_key, listed[0], OTHER_PHONE)
    assert choose(client, read_key, listed[0], listed[1]) == NULL_SELECT


# --- Cobro ---


def test_cobro_sin_identify_previo(client, charge_key, tenant, make_person, session):
    person = make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    conversation_id = conv()
    assert charge(client, charge_key, conversation_id) == {
        "charged": True, "operator_message": "Cobro registrado al titular Juan Pérez."}
    [row] = charges(session)
    assert row.person_id == person.id
    assert row.conversation_id == conversation_id
    assert row.amount == Decimal("1000.00")
    assert row.currency == "ARS"
    assert row.status == "simulated"
    assert row.from_phone == CANONICAL
    assert row.titular_name == "Juan Pérez"


def test_siempre_al_titular(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Hijo Pérez", celular=PHONE, titular="Juan Pérez", al_dia=True)
    assert charge(client, charge_key, conv())["operator_message"] == "Cobro registrado al titular Juan Pérez."
    assert charges(session)[0].titular_name == "Juan Pérez"


def test_repeticion_mismo_cobro_y_misma_respuesta(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    conversation_id = conv()
    first = charge(client, charge_key, conversation_id)
    assert charge(client, charge_key, conversation_id) == first
    assert len(charges(session)) == 1


def test_mayusculas_en_el_id_no_cobran_dos_veces(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    conversation_id = conv()
    charge(client, charge_key, conversation_id)
    charge(client, charge_key, conversation_id.upper())
    assert len(charges(session)) == 1


def test_llamadas_simultaneas_un_solo_cobro(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    conversation_id = conv()
    barrier = threading.Barrier(6)

    def call(_):
        barrier.wait()
        return charge(client, charge_key, conversation_id)

    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(call, range(6)))
    assert results == [{"charged": True, "operator_message": "Cobro registrado al titular Juan Pérez."}] * 6
    assert len(charges(session)) == 1


def test_el_doble_cobro_falla_por_constraint(tenant, make_person, session):
    person = make_person(tenant, "Juan Pérez", celular=PHONE)
    conversation_id = conv()
    values = dict(tenant_id=tenant.id, conversation_id=conversation_id, person_id=person.id, titular_name="Juan Pérez",
                  amount=Decimal("1"), currency="ARS", from_phone=CANONICAL, operator_message="x")
    session.add(Charge(**values))
    session.commit()
    session.add(Charge(**values))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("phone", [OTHER_PHONE, "", None, "1234567", "anonymous"])
def test_sin_ficha_no_guarda_fila(client, charge_key, tenant, make_person, session, phone):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    conversation_id = conv()
    expected = {"charged": False, "operator_message": "Sin ficha para este teléfono: no se cobró."}
    assert charge(client, charge_key, conversation_id, phone) == expected
    assert charges(session) == []


def test_un_no_cobro_se_recalcula_si_despues_se_puede(client, charge_key, tenant, make_person, session):
    conversation_id = conv()
    assert charge(client, charge_key, conversation_id)["charged"] is False
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    assert charge(client, charge_key, conversation_id)["charged"] is True
    assert len(charges(session)) == 1


def test_no_esta_al_dia_cobra_y_lo_dice(client, charge_key, tenant, make_person, session):
    person = make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=False)
    conversation_id = conv()
    expected = {"charged": True, "operator_message": "Cobro registrado al titular Juan Pérez, que no está al día."}
    assert charge(client, charge_key, conversation_id) == expected
    # Ponerse al día después no cambia la respuesta de la repetición.
    session.execute(update(Person).where(Person.id == person.id).values(al_dia=True))
    session.commit()
    assert charge(client, charge_key, conversation_id) == expected
    assert len(charges(session)) == 1


def test_contacto_con_una_sola_ficha_cobra_y_lo_dice(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Paciente", titular="Juan Pérez", contactos=[PHONE], al_dia=True)
    assert charge(client, charge_key, conv()) == {
        "charged": True,
        "operator_message": "Cobro registrado al titular Juan Pérez, por teléfono cargado como contacto."}
    assert len(charges(session)) == 1


def test_contacto_que_no_esta_al_dia_dice_las_dos_cosas(client, charge_key, tenant, make_person):
    make_person(tenant, "Paciente", titular="Juan Pérez", contactos=[PHONE], al_dia=False)
    conversation_id = conv()
    expected = {"charged": True, "operator_message":
                "Cobro registrado al titular Juan Pérez, que no está al día, por teléfono cargado como contacto."}
    assert charge(client, charge_key, conversation_id) == expected
    assert charge(client, charge_key, conversation_id) == expected


def test_contacto_elegido_lo_dice(client, read_key, charge_key, tenant, make_person):
    make_person(tenant, "Paciente Uno", titular="Juan Pérez", contactos=[PHONE], al_dia=True)
    make_person(tenant, "Paciente Dos", contactos=[PHONE], al_dia=True)
    conversation_id = conv()
    refs = refs_of(identify(client, read_key, conversation_id)["candidates"])
    choose(client, read_key, conversation_id, refs["Paciente U."])
    assert charge(client, charge_key, conversation_id)["operator_message"] == (
        "Cobro registrado al titular Juan Pérez, por teléfono cargado como contacto.")


def test_prueba_no_cobra_ni_guarda_fila(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    assert charge(client, charge_key, "prueba") == {
        "charged": False, "test": True, "operator_message": "Prueba: no se cobró."}
    assert charges(session) == []


def test_ficha_de_baja_no_cobra(client, charge_key, tenant, make_person, session):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True, active=False)
    assert charge(client, charge_key, conv()) == {
        "charged": False, "operator_message": "Sin ficha para este teléfono: no se cobró."}
    assert charges(session) == []


def test_ficha_elegida_de_baja_no_cobra_a_la_otra(client, read_key, charge_key, listed, session):
    conversation_id, ref = listed
    choose(client, read_key, conversation_id, ref)
    session.execute(update(Person).where(Person.name == "Juan Gómez").values(active=False))
    session.commit()
    assert charge(client, charge_key, conversation_id) == {
        "charged": False, "operator_message": "La ficha elegida está de baja: no se cobró."}
    assert charges(session) == []


def test_eleccion_cuenta_aunque_venzan_las_refs(client, read_key, charge_key, listed, session):
    conversation_id, ref = listed
    choose(client, read_key, conversation_id, ref)
    session.execute(update(ConversationChoice).values(expires_at=utcnow() - datetime.timedelta(seconds=1)))
    session.commit()
    assert charge(client, charge_key, conversation_id)["charged"] is True


def test_eleccion_no_vale_para_otro_from(client, read_key, charge_key, tenant, make_person, listed, session):
    conversation_id, ref = listed
    choose(client, read_key, conversation_id, ref)
    otra = make_person(tenant, "Otra Persona", celular=OTHER_PHONE, al_dia=True)
    charge(client, charge_key, conversation_id, OTHER_PHONE)
    assert [row.person_id for row in charges(session)] == [otra.id]


def test_monto_del_tenant(client, make_tenant, make_key, make_person, session):
    tenant = make_tenant("caro", amount="2500.50")
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    charge(client, make_key(tenant, "charge"), conv())
    assert charges(session)[0].amount == Decimal("2500.50")


# --- Link ---


def test_link_sin_datos_personales(client, read_key, tenant, make_person, session):
    person = make_person(tenant, "María Gómez", celular=PHONE, documento="20123456")
    conversation_id = conv()
    record = identify(client, read_key, conversation_id)["record"]
    url = urlsplit(record.removeprefix("Ficha: "))
    token = url.path.removeprefix("/c/")
    assert len(token) == 32 and int(token, 16) >= 0  # 128 bits
    assert not url.query and not url.fragment
    for dato in ("Mar", "Gomez", "Gómez", "20123456", CANONICAL, person.id, conversation_id):
        assert dato not in record.removeprefix("Ficha: http://registros.test")
    assert link(session, token).person_ids == [person.id]


def test_mismo_token_en_la_misma_conversacion(client, read_key, tenant, make_person, session):
    make_person(tenant, "María Gómez", celular=PHONE)
    conversation_id = conv()
    first = identify(client, read_key, conversation_id)["record"]
    assert identify(client, read_key, conversation_id)["record"] == first
    assert identify(client, read_key, conv())["record"] != first
    assert session.scalar(select(func.count()).select_from(RecordLink)) == 2


def test_select_actualiza_el_link(client, read_key, tenant, make_person, session):
    maria = make_person(tenant, "María Gómez", celular=PHONE)
    juan = make_person(tenant, "Juan Gómez", celular=PHONE)
    conversation_id = conv()
    listed = identify(client, read_key, conversation_id)
    token = token_of(listed["record"])
    assert set(link(session, token).person_ids) == {maria.id, juan.id}
    selected = choose(client, read_key, conversation_id, refs_of(listed["candidates"])["Juan G."])
    assert token_of(selected["record"]) == token
    assert link(session, token).person_ids == [juan.id]


def test_link_vence_a_los_30_dias(client, read_key, tenant, make_person, session):
    make_person(tenant, "María Gómez", celular=PHONE)
    token = token_of(identify(client, read_key, conv())["record"])
    left = link(session, token).expires_at - utcnow()
    assert datetime.timedelta(days=29, hours=23) < left <= datetime.timedelta(days=30)


# --- Caracteres que la base no guarda ---


def post_raw(client, path: str, key: str, body: str):
    """JSON crudo: "\u0000" y un surrogate suelto llegan así al servidor."""
    return client.post(path, headers={**bearer(key), "Content-Type": "application/json"}, content=body)


@pytest.mark.parametrize("path", ["/v1/identify", "/v1/identify/select", "/v1/charges"])
@pytest.mark.parametrize("field, raw, status", [
    # No es un UUID: es la prueba del panel, no guarda nada.
    ("conversation_id", r"a\u0000b", 200),
    # canonical_phone se queda con los dígitos.
    ("from", r"\u0000", 200),
    ("from", r"+54935\u000015551234", 200),
    # pydantic no acepta un surrogate suelto como texto.
    ("conversation_id", r"\ud800", 422),
    ("from", r"\ud800", 422),
])
def test_v1_con_caracteres_que_la_base_no_guarda(client, charge_key, tenant, make_person, path, field, raw, status):
    make_person(tenant, "Ana Prueba", celular=PHONE)
    values = {"conversation_id": conv(), "from": PHONE, "ref": "r_0000", field: raw}
    body = "{" + ",".join(f'"{name}":"{value}"' for name, value in values.items()) + "}"
    r = post_raw(client, path, charge_key, body)
    assert r.status_code == status, r.text


def test_ref_con_surrogate_da_422(client, read_key, listed):
    body = f'{{"conversation_id":"{listed[0]}","from":"{PHONE}","ref":"\\ud800"}}'
    assert post_raw(client, "/v1/identify/select", read_key, body).status_code == 422


def test_ref_con_nul_es_invalida(client, read_key, listed):
    body = f'{{"conversation_id":"{listed[0]}","from":"{PHONE}","ref":"{listed[1]}\\u0000"}}'
    r = post_raw(client, "/v1/identify/select", read_key, body)
    assert r.status_code == 200
    assert r.json() == NULL_SELECT


# --- Claves y alcance ---


def test_clave_read_recibe_403_en_cobros(client, read_key, tenant, make_person, session):
    make_person(tenant, "Juan Pérez", celular=PHONE, al_dia=True)
    r = client.post("/v1/charges", headers=bearer(read_key), json={"conversation_id": conv(), "from": PHONE})
    assert r.status_code == 403
    assert charges(session) == []


def test_clave_charge_tambien_lee(client, charge_key, tenant, make_person):
    make_person(tenant, "Juan Pérez", celular=PHONE)
    assert identify(client, charge_key, conv())["status"] == "single"


@pytest.mark.parametrize("path", ["/v1/identify", "/v1/identify/select", "/v1/charges"])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer inexistente"}, {"Authorization": "Basic x"}])
def test_sin_clave_valida_401(client, path, headers):
    body = {"conversation_id": conv(), "from": PHONE, "ref": "r_1"}
    assert client.post(path, headers=headers, json=body).status_code == 401


@pytest.mark.parametrize("path", ["/v1/identify", "/v1/identify/select", "/v1/charges"])
def test_json_invalido_422(client, charge_key, path):
    headers = {**bearer(charge_key), "Content-Type": "application/json"}
    assert client.post(path, headers=headers, content="{no es json").status_code == 422
    assert client.post(path, headers=bearer(charge_key), json={"from": PHONE}).status_code == 422


def test_select_sin_ref_422(client, read_key):
    r = client.post("/v1/identify/select", headers=bearer(read_key), json={"conversation_id": conv(), "from": PHONE})
    assert r.status_code == 422


def test_clave_de_otro_tenant_no_lee_nada(client, read_key, tenant, make_tenant, make_key, make_person):
    make_person(tenant, "María Gómez", celular=PHONE)
    make_person(tenant, "Juan Gómez", celular=PHONE)
    otro = make_tenant("otro")
    otra_read, otra_charge = make_key(otro, "read"), make_key(otro, "charge")
    conversation_id = conv()
    ref = next(iter(refs_of(identify(client, read_key, conversation_id)["candidates"]).values()))

    assert identify(client, otra_read, conv())["status"] == "none"
    assert choose(client, otra_read, conversation_id, ref) == NULL_SELECT
    assert identify(client, otra_read, conversation_id)["status"] == "none"
    assert charge(client, otra_charge, conversation_id)["charged"] is False


def test_misma_conversacion_en_dos_tenants_no_se_cruza(client, make_tenant, make_key, make_person, session):
    uno, dos = make_tenant("uno"), make_tenant("dos")
    persona_uno = make_person(uno, "Ana Uno", celular=PHONE, al_dia=True)
    persona_dos = make_person(dos, "Ana Dos", celular=PHONE, al_dia=True)
    conversation_id = conv()
    assert charge(client, make_key(uno, "charge"), conversation_id)["operator_message"].endswith("Ana Uno.")
    assert charge(client, make_key(dos, "charge"), conversation_id)["operator_message"].endswith("Ana Dos.")
    assert {row.person_id for row in charges(session)} == {persona_uno.id, persona_dos.id}


def test_clave_revocada_401(client, read_key, session):
    session.execute(update(ApiKey).values(revoked_at=utcnow()))
    session.commit()
    r = client.post("/v1/identify", headers=bearer(read_key), json={"conversation_id": conv(), "from": PHONE})
    assert r.status_code == 401
