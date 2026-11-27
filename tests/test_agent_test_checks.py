"""Chequeos deterministas de un caso de prueba (app/agent_tests/checks.py)."""
import pytest

from app.agent_tests import checks


def reply(text="", tool_calls=None, handoff=None, tool_results=None):
    return {"text": text, "tool_calls": tool_calls or [], "handoff": handoff, "tool_results": tool_results or []}


def fails(*checks_, **data):
    return checks.evaluate(checks.validate(list(checks_)), reply(**data))


# ---------- validate ----------

def test_validate_normaliza_y_acepta_los_ocho_tipos():
    clean = checks.validate([
        {"type": "usa_herramienta", "tool": " turnos ", "argumentos_contienen": " centro "},
        {"type": "no_usa_herramienta"},
        {"type": "no_usa_herramienta", "tool": "reservar"},
        {"type": "deriva_a", "area": " Administración "},
        {"type": "no_deriva"},
        {"type": "dice", "text": "  hay   lugar "},
        {"type": "no_dice", "text": "no hay"},
        {"type": "empieza_con", "text": "Para Castelli"},
        {"type": "datos_de_la_herramienta"},
    ])
    assert clean[0] == {"type": "usa_herramienta", "tool": "turnos", "argumentos_contienen": "centro"}
    assert clean[2] == {"type": "no_usa_herramienta", "tool": "reservar"}
    assert clean[3] == {"type": "deriva_a", "area": "Administración"}
    assert clean[5] == {"type": "dice", "text": "hay lugar"}
    assert checks.validate(None) == []


@pytest.mark.parametrize("raw, path", [
    ({"type": "otro"}, "checks.0.type"),
    ({"type": "usa_herramienta"}, "checks.0.tool"),
    ({"type": "deriva_a"}, "checks.0.area"),
    ({"type": "dice"}, "checks.0.text"),
    ({"type": "dice", "text": "   "}, "checks.0.text"),
    ({"type": "dice", "text": "x" * 501}, "checks.0.text"),
])
def test_validate_rechaza_con_la_ruta(raw, path):
    with pytest.raises(checks.CheckError) as e:
        checks.validate([raw])
    assert e.value.path == path
    assert str(e.value).startswith(path)


def test_validate_tope_de_chequeos():
    with pytest.raises(checks.CheckError) as e:
        checks.validate([{"type": "no_deriva"}] * 21)
    assert e.value.path == "checks"


# ---------- texto ----------

def test_dice_por_texto_y_por_lo_que_dice_el_tts():
    # "19:30" y "diecinueve treinta" coinciden en los dos sentidos.
    assert fails({"type": "dice", "text": "19:30"}, text="a las diecinueve treinta") == []
    assert fails({"type": "dice", "text": "diecinueve treinta"}, text="a las 19:30") == []


def test_dice_sin_tildes_ni_mayusculas():
    assert fails({"type": "dice", "text": "MAÑANA"}, text="mañana temprano") == []


def test_no_dice_no_confunde_cifras_dentro_de_otras():
    assert fails({"type": "no_dice", "text": "155"}, text="sale $1.550") == []
    assert fails({"type": "no_dice", "text": "155"}, text="son 15.500 pesos") == []
    # Pegada a letras tampoco.
    assert fails({"type": "no_dice", "text": "ala"}, text="palabra") == []


def test_no_dice_falla_con_span():
    out = fails({"type": "no_dice", "text": "130"}, text="Sale $130 por persona")
    assert len(out) == 1
    assert out[0]["span"] == "130"
    assert "Dijo" in out[0]["message"]


def test_empieza_con_con_signos_de_apertura():
    check = {"type": "empieza_con", "text": "Para Castelli"}
    assert fails(check, text="¡Para Castelli! Hay dos salidas.") == []
    assert len(fails(check, text="Entendí Castelli: para Castelli.")) == 1


# ---------- herramientas ----------

def test_usa_herramienta_y_argumentos():
    check = {"type": "usa_herramienta", "tool": "estrella_salidas", "argumentos_contienen": "castelli"}
    assert fails(check, tool_calls=[{"name": "estrella_salidas", "arguments": {"destino": "Castelli"}}]) == []
    assert fails(check, tool_calls=[{"name": "estrella_salidas", "arguments": '{"destino": "Charata"}'}])
    assert fails(check, tool_calls=[{"name": "otra", "arguments": {}}])


def test_no_usa_herramienta_sin_tool_falla_con_cualquier_llamada():
    assert fails({"type": "no_usa_herramienta"}, tool_calls=[{"name": "x", "arguments": {}}])
    assert fails({"type": "no_usa_herramienta"}, tool_calls=[]) == []
    assert fails({"type": "no_usa_herramienta", "tool": "x"},
                 tool_calls=[{"name": "x", "arguments": {}}])


# ---------- derivacion ----------

def test_deriva_a_y_no_deriva():
    assert fails({"type": "deriva_a", "area": "Administración"}, handoff="Administración") == []
    assert fails({"type": "deriva_a", "area": "Administración"}, handoff="Ventas")
    assert fails({"type": "deriva_a", "area": "Administración"}, handoff=None)
    assert fails({"type": "no_deriva"}, handoff="Ventas")
    assert fails({"type": "no_deriva"}, handoff=None) == []


# ---------- datos de la herramienta ----------

def test_datos_de_la_herramienta_importe_presente():
    check = {"type": "datos_de_la_herramienta"}
    assert fails(check, text="Sale $13.500.", tool_results=['{"precio": 13500}']) == []
    assert fails(check, text="Sale $ 980.", tool_results=['{"precio": 980}']) == []
    assert fails(check, text="Sale $1.250,50.", tool_results=['{"precio": 1250.5}']) == []


def test_datos_de_la_herramienta_importe_ausente_falla_con_span():
    out = fails({"type": "datos_de_la_herramienta"}, text="Sale $13.000.", tool_results=['{"precio": 13500}'])
    assert len(out) == 1
    assert out[0]["span"] == "$13.000"


def test_datos_de_la_herramienta_cifras_dentro_de_strings():
    check = {"type": "datos_de_la_herramienta"}
    results = ['{"salidas": [{"hora": "20:00:00", "precio": "13.500"}]}']
    assert fails(check, text="A las 20:00, $13.500.", tool_results=results) == []


def test_datos_de_la_herramienta_hora_sin_resultados_falla():
    out = fails({"type": "datos_de_la_herramienta"}, text="Sale a las 20:00.")
    assert len(out) == 1 and out[0]["span"] == "20:00"


def test_datos_de_la_herramienta_sin_datos_en_el_texto_pasa():
    assert fails({"type": "datos_de_la_herramienta"}, text="No hay salidas.") == []


# ---------- sugeridos ----------

def test_suggest():
    assert checks.suggest(reply(handoff="Ventas", tool_calls=[
        {"name": "turnos", "arguments": {}}, {"name": "turnos", "arguments": {}}],
        tool_results=["{}"])) == [
        {"type": "no_deriva"},
        {"type": "usa_herramienta", "tool": "turnos"},
        {"type": "datos_de_la_herramienta"},
    ]
    assert checks.suggest(reply()) == []
