import pytest

from registros.phones import canonical_phone

CANONICAL = "543515551234"


@pytest.mark.parametrize("raw", [
    "+54 351 555 1234",        # +54
    "+54 9 351 555-1234",      # +549
    "5493515551234",
    "0351 555 1234",           # con 0
    "351 555 1234",            # solo 10 dígitos
    "(0351) 15 555-1234",      # con 15 y 0
    "351 15 555 1234",         # con 15
    "+54 351 15 555 1234",     # con 54 y 15
    "+54 9 351 15 555 1234",   # con 549 y 15
])
def test_las_formas_de_un_mismo_celular_dan_lo_mismo(raw):
    assert canonical_phone(raw) == CANONICAL


@pytest.mark.parametrize("raw, expected", [
    ("11 15 5555 1234", "541155551234"),      # característica de 2
    ("2966 15 12 3456", "542966123456"),      # de 4
    ("11 15 15 12 3456", "541115123456"),     # el número sigue con 15
])
def test_15_con_cada_largo_de_caracteristica(raw, expected):
    assert canonical_phone(raw) == expected


def test_fijo_se_canoniza_igual_que_un_celular_de_diez_digitos():
    assert canonical_phone("0351 422-1234") == "543514221234"
    assert canonical_phone("+54 351 422 1234") == "543514221234"


@pytest.mark.parametrize("raw", ["", None, "   ", "abc", "1234567", "+54", "1" * 21])
def test_sin_telefono(raw):
    assert canonical_phone(raw) == ""


def test_ocho_digitos_ya_es_un_telefono():
    assert canonical_phone("42211234") == "42211234"


@pytest.mark.parametrize("raw", ["+44 15 3412 3456", "+1 212 555 1234", "+55 11 91234 5678"])
def test_un_numero_extranjero_no_se_toca(raw):
    assert canonical_phone(raw) == "".join(c for c in raw if c.isdigit())
