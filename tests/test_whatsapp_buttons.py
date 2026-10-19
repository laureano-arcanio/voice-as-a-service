"""Links a vistas de apps como botón de WhatsApp (cta_url, 16-oct-2026)."""
from app.whatsapp import buttons

HOST = "apps.atentina.com.ar"
PERFIL = f"https://{HOST}/sugym/sugym-gestion/perfil/?alumno_id=131&editar=1&k=tzf65nRvmUUq8pSp2GseKtGAo2mr_8-x"
ALTA = f"https://{HOST}/sugym/sugym-gestion/alta/?nombre=Rigoberto&apellido=Zapata&k=dqgfB-GrFg"


def test_sin_links_o_sin_host_no_cambia():
    assert buttons.extract("Hola, ¿qué necesitás?", HOST) == ("Hola, ¿qué necesitás?", [])
    assert buttons.extract(f"Mirá {PERFIL}", "") == (f"Mirá {PERFIL}", [])
    otro = "Mirá https://atentina.com.ar/precios"
    assert buttons.extract(otro, HOST) == (otro, [])


def test_un_link_en_su_linea():
    body = f"Registré la asistencia de Olga Bergagna. No tiene plan asignado.\n{PERFIL}"
    text, links = buttons.extract(body, HOST)
    assert text == "Registré la asistencia de Olga Bergagna. No tiene plan asignado."
    assert [(x.url, x.client, x.app, x.view) for x in links] == [(PERFIL, "sugym", "sugym-gestion", "perfil")]


def test_un_link_en_una_frase_deja_la_frase():
    text, links = buttons.extract(f"Registré a Olga. Asignale el plan en su perfil: {PERFIL}.", HOST)
    assert text == "Registré a Olga. Asignale el plan en su perfil" and links[0].url == PERFIL


def test_varios_links_en_lista_son_rotulos():
    otro = PERFIL.replace("131", "132")
    body = f"Anoté a las dos. No tienen plan:\n- Anahi Revelante: {PERFIL}\n- *Mercedes Londero*: {otro}"
    text, links = buttons.extract(body, HOST)
    assert text == "Anoté a las dos. No tienen plan:"
    assert [(x.line, x.url) for x in links] == [("Anahi Revelante", PERFIL), ("Mercedes Londero", otro)]


def test_link_solo_y_rotulo_corto():
    text, links = buttons.extract(ALTA, HOST)
    assert text == "" and links[0].view == "alta"
    assert buttons.label("Estadísticas del mes") == "Estadísticas del mes"
    assert len(buttons.label("Un título larguísimo de vista")) == 20
