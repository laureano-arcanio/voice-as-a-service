"""Reglas de seleccion de `scripts/dev/tests_afectados.py`, con un mapa y un diff falsos.

El script corre en el host con el python3 del sistema y no importa app/; estos tests
llaman a `elegir` directo, con el texto de los archivos de test falso, para no depender
del mapa real ni de los archivos del repo.
"""
import pytest

from scripts.dev.tests_afectados import contar, elegir

# Mapa falso: dos tests pesados y uno liviano; dialer lo ejecutan los dos primeros.
MAPA = {
    "generado": "2026-01-01T00:00:00+00:00",
    "commit": "abc123",
    "segundos": {
        "tests/test_a.py": 30.0,
        "tests/test_b.py": 30.0,
        "tests/test_liviano.py": 10.0,
        "tests/test_handoff.py": 5.0,
    },
    "fuentes": {
        "app/voice/handoff.py": ["tests/test_handoff.py"],
        "app/campaigns/dialer.py": ["tests/test_a.py", "tests/test_b.py"],
    },
}

TEXTOS = {
    "tests/test_referencia.json.py": "test que usa app/agents/reference/sales_discovery.json",
    "tests/test_otro.py": "no menciona nada del diff",
}


def es_todo(res: tuple) -> bool:
    tests, motivo, _ = res
    return tests == [] and motivo is not None


def test_archivo_central_da_todo():
    assert es_todo(elegir({"app/models/handoff.py"}, MAPA, TEXTOS))
    assert es_todo(elegir({"tests/conftest.py"}, MAPA, TEXTOS))
    assert es_todo(elegir({"requirements.txt"}, MAPA, TEXTOS))


def test_py_fuera_del_mapa_da_todo():
    assert es_todo(elegir({"app/nuevo.py"}, MAPA, TEXTOS))
    # scripts/ tambien: el mapa solo registra lo que ejecutan los tests
    assert es_todo(elegir({"scripts/dev/tests_afectados.py"}, MAPA, TEXTOS))


def test_sin_mapa_da_todo():
    assert es_todo(elegir({"app/voice/handoff.py"}, None, TEXTOS))


def test_py_mapeado_da_sus_tests():
    tests, motivo, motivos = elegir({"app/voice/handoff.py"}, MAPA, TEXTOS)
    assert (tests, motivo) == (["tests/test_handoff.py"], None)
    assert motivos["tests/test_handoff.py"] == ["ejecuta app/voice/handoff.py"]


def test_test_cambiado_o_nuevo_entra():
    tests, _, _ = elegir({"tests/test_nuevo.py"}, MAPA, TEXTOS)
    assert tests == ["tests/test_nuevo.py"]


def test_json_de_referencia_los_tests_que_lo_mencionan():
    tests, motivo, motivos = elegir({"app/agents/reference/sales_discovery.json"}, MAPA, TEXTOS)
    assert (tests, motivo) == (["tests/test_referencia.json.py"], None)
    assert motivos["tests/test_referencia.json.py"] == ["menciona app/agents/reference/sales_discovery.json"]


def test_migracion_da_su_test_migration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_migration_0042.py").write_text("def test_x(): ...")
    tests, motivo, motivos = elegir({"migrations/versions/0042_nuevo_campo.py"}, MAPA, TEXTOS)
    assert (tests, motivo) == (["tests/test_migration_0042.py"], None)
    assert motivos["tests/test_migration_0042.py"] == ["migracion migrations/versions/0042_nuevo_campo.py"]


def test_migracion_sin_test_ni_mapa_da_todo():
    assert es_todo(elegir({"migrations/versions/0043_otro.py"}, MAPA, TEXTOS))


def test_seleccion_muy_grande_da_todo():
    # test_a + test_b = 60 s de 75 (80 %): conviene la suite completa
    assert es_todo(elegir({"app/campaigns/dialer.py"}, MAPA, TEXTOS))


def test_seleccion_chica_pasa():
    tests, motivo, _ = elegir({"app/voice/handoff.py", "tests/test_liviano.py"}, MAPA, TEXTOS)
    assert (tests, motivo) == (["tests/test_handoff.py", "tests/test_liviano.py"], None)


def test_seleccion_vacia_da_todo():
    # solo un doc que nadie menciona: sin selección no hay atajo
    assert es_todo(elegir({"docs/DESARROLLO.md"}, MAPA, TEXTOS))


def test_contar():
    assert contar([]) == 0


def test_contar_archivo_real(tmp_path):
    d = tmp_path / "tests"
    d.mkdir()
    p = d / "test_x.py"
    p.write_text("def test_uno(): ...\nasync def test_dos(): ...\n")
    assert contar([str(p)]) == 2
