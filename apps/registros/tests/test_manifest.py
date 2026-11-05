import json

import pytest
from conftest import FORM_EJEMPLO, MANIFEST
from sqlalchemy import select

from registros.manifest import ManifestError, names_of, parse_manifest, phones_of, sync_person, values_at
from registros.models import Person, PersonPhone


def test_el_manifiesto_de_ejemplo_es_valido():
    manifest = parse_manifest(json.loads((FORM_EJEMPLO / "manifest.json").read_text()))
    assert manifest.contact_phone_paths == ("contactos[*].telefono",)


@pytest.mark.parametrize("change", [
    {"name": ""},
    {"name": None},
    {"titular": "a..b"},
    {"phone_paths": []},
    {"phone_paths": "datos.celular"},
    {"contact_phone_paths": [1]},
    {"filters": ["a b"]},
])
def test_manifiesto_invalido(change):
    with pytest.raises(ManifestError):
        parse_manifest({**MANIFEST, **change})


def test_valores_por_ruta():
    data = {"a": {"b": 1}, "l": [{"t": "x"}, {"t": None}, {"o": "y"}, "suelto"], "n": "no es lista"}
    assert values_at(data, "a.b") == [1]
    assert values_at(data, "l[*].t") == ["x"]
    assert values_at(data, "n[*].t") == []
    assert values_at(data, "a.falta.mas") == []


def test_telefonos_del_titular_y_de_contactos_segun_el_manifiesto():
    data = {
        "datos": {"celular": "+549 351 000-0001", "otro_telefono": "0351 15 000-0002"},
        "contactos": [{"telefono": "351 000 0003"}, {"telefono": "123"}, {"telefono": None}, {"telefono": True}],
        # Fuera del manifiesto: no cuenta.
        "medico": {"telefono": "351 000 0004"},
    }
    assert phones_of(parse_manifest(MANIFEST), data) == {
        "543510000001": "titular",
        "543510000002": "titular",
        "543510000003": "contacto",
    }


def test_sin_rutas_de_contacto_no_se_toman_contactos():
    data = {"datos": {"celular": "351 000 0001"}, "contactos": [{"telefono": "351 000 0003"}]}
    manifest = parse_manifest({**MANIFEST, "contact_phone_paths": []})
    assert phones_of(manifest, data) == {"543510000001": "titular"}


def test_telefono_en_las_dos_rutas_cuenta_como_titular():
    data = {"datos": {"celular": "351 000 0001"}, "contactos": [{"telefono": "+54 9 351 000 0001"}]}
    assert phones_of(parse_manifest(MANIFEST), data) == {"543510000001": "titular"}


def test_sin_titular_cargado_la_persona_es_el_titular():
    manifest = parse_manifest(MANIFEST)
    assert names_of(manifest, {"datos": {"nombre": " Ana "}}) == ("Ana", "Ana")
    assert names_of(manifest, {"datos": {"nombre": "Ana"}, "cobertura": {"titular": "Beto"}}) == ("Ana", "Beto")


def test_sync_reemplaza_los_telefonos_de_la_ficha(session, make_tenant, make_person):
    tenant = make_tenant()
    person = make_person(tenant, celular="351 000 0001", contactos=["351 000 0002"])

    def phones() -> dict:
        rows = session.scalars(select(PersonPhone).where(PersonPhone.person_id == person.id))
        return {row.phone: row.relation for row in rows}

    assert phones() == {"543510000001": "titular", "543510000002": "contacto"}

    person = session.get(Person, person.id)
    # El contacto pasa a titular, y el titular anterior se va.
    person.data = {"datos": {"nombre": "Ana Prueba", "celular": "351 000 0002"}}
    sync_person(session, person, parse_manifest(MANIFEST))
    session.commit()
    assert phones() == {"543510000002": "titular"}
