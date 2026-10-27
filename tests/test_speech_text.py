"""Normalizador de texto para el TTS (app/voice/speech_text.py)."""
import pytest

from app.voice.speech_text import number_words, to_speech

CASES = [
    # Números
    ("15.400", "quince mil cuatrocientos"),
    ("15.400,50", "quince mil cuatrocientos coma cincuenta"),
    ("3,5", "tres coma cinco"),
    ("3,05", "tres coma cero cinco"),
    ("1.5", "uno coma cinco"),
    ("1.000.000", "un millón"),
    ("2026", "dos mil veintiséis"),
    ("En 1990 éramos 500", "En mil novecientos noventa éramos quinientos"),
    ("Son 21 años", "Son veintiún años"),
    ("Pagás 1 cuota", "Pagás una cuota"),
    ("Entran 200 personas", "Entran doscientas personas"),
    ("1.000.000 personas", "un millón de personas"),
    ("Tengo 1", "Tengo uno"),
    # Plata
    ("$15.400", "quince mil cuatrocientos pesos"),
    ("$ 15.400,50", "quince mil cuatrocientos pesos con cincuenta centavos"),
    ("ARS 1.000", "mil pesos"),
    ("$1", "un peso"),
    ("$21", "veintiún pesos"),
    ("$1.000.000", "un millón de pesos"),
    ("US$ 20", "veinte dólares"),
    ("USD 20", "veinte dólares"),
    ("20 USD", "veinte dólares"),
    ("U$S 1", "un dólar"),
    # Horas
    ("11:30", "once y media"),
    ("11:15", "once y cuarto"),
    ("09:00", "nueve"),
    ("9:00", "nueve"),
    ("09:00 hs", "nueve"),
    ("16:45", "dieciséis y cuarenta y cinco"),
    ("10:05", "diez y cinco"),
    ("a las 1:00", "a las una"),
    ("de 9:00-18:00", "de nueve a dieciocho"),
    ("21 hs", "veintiuna horas"),
    ("21h", "veintiuna horas"),
    ("dura 1 h", "dura una hora"),
    ("de 9-18 hs", "de nueve a dieciocho horas"),
    ("de 9 a 18 hs", "de nueve a dieciocho horas"),
    ("10am y 8 pm", "diez de la mañana y ocho de la noche"),
    # Fechas
    ("05/11", "cinco de noviembre"),
    ("5/11/2026", "cinco de noviembre de dos mil veintiséis"),
    ("5/11/26", "cinco de noviembre de dos mil veintiséis"),
    ("2026-11-05", "cinco de noviembre de dos mil veintiséis"),
    ("1/11", "primero de noviembre"),
    ("el 31/12.", "el treinta y uno de diciembre."),
    # Porcentaje
    ("15%", "quince por ciento"),
    ("2,5 %", "dos coma cinco por ciento"),
    # Ordinales y grados
    ("1º piso", "primer piso"),
    ("el 1°", "el primero"),
    ("2da cuota", "segunda cuota"),
    ("3er turno", "tercer turno"),
    ("4to", "cuarto"),
    ("1ª vez", "primera vez"),
    ("25°C", "veinticinco grados"),
    ("hace 30°", "hace treinta grados"),
    ("N° 123", "número ciento veintitrés"),
    # Mails y URLs
    ("ana.gomez@acme.com.ar", "ana punto gomez arroba acme punto com punto ar"),
    ("juan_23-x@mail.com", "juan guion bajo dos tres guion x arroba mail punto com"),
    ("Escribí a ana@acme.com.", "Escribí a ana arroba acme punto com."),
    ("https://www.acme.com/turnos", "acme punto com barra turnos"),
    ("Entrá a https://acme.com.ar/turnos?x=1.", "Entrá a acme punto com punto ar barra turnos."),
    ("visitá www.acme.com", "visitá acme punto com"),
    ("visitá acme.com.ar.", "visitá acme punto com punto ar."),
    # Teléfonos
    ("+54 9 351 555-1234",
     "más cinco cuatro, nueve, tres cinco uno, cinco cinco cinco, uno dos tres cuatro"),
    ("3515551234", "tres cinco uno, cinco cinco cinco, uno dos tres cuatro"),
    ("4555-1234", "cuatro cinco cinco cinco, uno dos tres cuatro"),
    ("llamá al 0800-555-1234",
     "llamá al cero ocho cero cero, cinco cinco cinco, uno dos tres cuatro"),
    ("de 10-12", "de diez a doce"),
    ("2025-2026", "dos mil veinticinco a dos mil veintiséis"),
    # Códigos
    ("R-B5E16C", "erre, guion, be, cinco, e, uno, seis, ce"),
    ("Tu código es AB123.", "Tu código es a, be, uno, dos, tres."),
    # DNI
    ("DNI 30.111.222", "DNI treinta millones ciento once mil doscientos veintidós"),
    ("DNI: 30111222", "DNI: treinta millones ciento once mil doscientos veintidós"),
    # Símbolos y markdown
    ("Tom & Jerry", "Tom y Jerry"),
    ("2+2", "dos más dos"),
    ("promo 3x2", "promo tres por dos"),
    ("5 km", "cinco kilómetros"),
    ("1 kg", "un kilo"),
    ("marcá #9 o *9", "marcá numeral nueve o asterisco nueve"),
    ("**Hola** 😀 `listo`", "Hola listo"),
    ("# Turnos\n- lunes\n- martes", "Turnos lunes martes"),
    ("Mirá [la web](https://acme.com) 👍", "Mirá la web"),
    ("hola    che", "hola che"),
    # Texto común sin cambios
    ("Hola, ¿cómo estás? Soy Sofía de Atentina.", "Hola, ¿cómo estás? Soy Sofía de Atentina."),
    ("Acme S.A., Dr. Pérez, etc.", "Acme S.A., Dr. Pérez, etc."),
    # Ejemplo completo
    ("Tu turno es el 05/11 a las 11:30, cuesta $15.400,50. Escribí a ana.gomez@acme.com.ar",
     ("Tu turno es el cinco de noviembre a las once y media, cuesta quince mil cuatrocientos "
      "pesos con cincuenta centavos. Escribí a ana punto gomez arroba acme punto com punto ar")),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_to_speech(text, expected):
    assert to_speech(text) == expected


@pytest.mark.parametrize("text,_", CASES)
def test_idempotent(text, _):
    once = to_speech(text)
    assert to_speech(once) == once


@pytest.mark.parametrize("n,expected", [
    (0, "cero"), (1, "uno"), (21, "veintiuno"), (100, "cien"), (101, "ciento uno"),
    (500, "quinientos"), (1000, "mil"), (1100, "mil cien"), (21000, "veintiún mil"),
    (100000, "cien mil"), (1000001, "un millón uno"), (2500000, "dos millones quinientos mil"),
])
def test_number_words(n, expected):
    assert number_words(n) == expected


@pytest.mark.parametrize("language", ["en", "pt", "en-US", "pt_BR"])
def test_other_language_unchanged(language):
    text = "Call 3515551234 at 11:30, $15.400 **now**"
    assert to_speech(text, language) == text


@pytest.mark.parametrize("language", ["es", "es-AR", "ES", "es_AR"])
def test_spanish_variants(language):
    assert to_speech("15%", language) == "quince por ciento"


@pytest.mark.parametrize("fragment", [
    "", " ", "a las 11:", "$", "cuesta $", "05/", "https://", "ana@", "**", "+54",
    "R-", "15.", ",50", "DNI", "N°", "#", "-", "1/2/", "11:30-",
])
def test_fragment_safe(fragment):
    out = to_speech(fragment)
    assert isinstance(out, str)
    assert to_speech(out) == out
