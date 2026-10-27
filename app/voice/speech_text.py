"""Texto del LLM -> texto para el TTS (español rioplatense).

El LLM escribe normal ("el 05/11 a las 11:30, $15.400,50") y la voz lo tiene
que decir en palabras. Esto reemplaza las reglas del prompt por código
determinista. Se aplica por oración ya completa, sin estado; con un fragmento
no rompe. Es idempotente: lo que ya está en palabras no cambia.

`to_speech(text, language)`: con un idioma que no es español ("en", "pt")
devuelve el texto tal cual (las reglas son de es-AR).

Convenciones y ambigüedades (una por línea):
- Números: punto = miles y coma = decimal ("15.400,50"); un punto seguido de
  1, 2 o 4+ cifras ("1.5") se lee como decimal.
- Decimales: "coma" y la parte decimal como número, con sus ceros a la
  izquierda como "cero" ("3,05" -> "tres coma cero cinco").
- Un número de 8 o más cifras seguidas sin puntos es un teléfono, no una
  cantidad: "10000000" se lee cifra por cifra (las cantidades van con puntos).
- Años: "2026" es un número más ("dos mil veintiséis").
- Género: "1"/"21"/"200" toman la forma del sustantivo que sigue, por
  heurística ("una cuota", "veintiún años", "doscientas personas"); sin
  sustantivo, masculino ("uno", "cuatrocientos").
- Plata: "$", "ARS" -> pesos; "US$", "U$S", "USD" -> dólares; "€", "EUR" ->
  euros; centavos con "con ... centavos"; "un millón de pesos".
- Horas "HH:MM": la hora en femenino ("la una", "veintiuna"); :00 solo la
  hora, :15 "y cuarto", :30 "y media", el resto "y <minutos>" ("diez y
  cinco"); un "hs" después se descarta.
- "21 hs"/"21h": "veintiuna horas" (1 -> "una hora"); "9-18 hs" -> "nueve a
  dieciocho horas". "10am"/"8 pm" -> "de la mañana/tarde/noche".
- Fechas: "d/m", "d/m/aaaa", "d/m/aa" (20aa) y ISO "aaaa-mm-dd"; el día 1 es
  "primero". Una barra entre números que forman fecha válida es fecha (así
  "1/2" es "primero de febrero", no un medio).
- Ordinales "1º", "1ª", "2da", "3er", "4to" del 1 al 10 en palabras
  ("segunda", "tercer"); más de 10, el cardinal. "°" con 10 o menos es
  ordinal; con más, o con "C", son grados.
- Mails: "punto", "arroba", "guion", "guion bajo"; las cifras de a una.
- URLs: sin "https://" ni "www."; "punto" y "barra"; la query y el "#" se
  descartan.
- Teléfonos ("+54 9 351 555-1234", "3515551234"): cifra por cifra, "más"
  por el "+", agrupadas como vienen escritas (coma entre grupos); seguidas,
  en grupos de 3 con los últimos 4 juntos.
- DNI: el número después de "DNI" como cantidad ("treinta millones ciento
  once mil doscientos veintidós"), con o sin puntos.
- Códigos que mezclan letras y cifras ("R-B5E16C", "AB123"): letra por
  letra con su nombre, separadas por coma.
- Rangos "9-18" -> "nueve a dieciocho"; "2+2" -> "más"; "3x2" -> "tres por
  dos"; "&" -> "y"; "#9" -> "numeral nueve"; "*9" -> "asterisco nueve".
- Se sacan markdown (**, __, #, viñetas, `), los links quedan en su texto,
  emojis afuera y espacios colapsados.
"""
import re

# --- Números a palabras ---------------------------------------------------

_UNITS = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
    "veintinueve"
]
_TENS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta",
         7: "setenta", 8: "ochenta", 9: "noventa"}
_HUNDREDS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos",
             5: "quinientos", 6: "seiscientos", 7: "setecientos",
             8: "ochocientos", 9: "novecientos"}
_DIGITS = _UNITS[:10]


def _ending(words: str, form: str) -> str:
    """Ajusta el "uno" final: form "m" (uno), "a" (un, apócope), "f" (una)."""
    if form == "a":
        if words.endswith("veintiuno"):
            return words[:-9] + "veintiún"
        if words.endswith("uno"):
            return words[:-3] + "un"
    elif form == "f" and words.endswith("uno"):
        return words[:-3] + "una"
    return words


def _below_1000(n: int, form: str = "m") -> str:
    if n == 100:
        return "cien"
    parts = []
    h, rest = divmod(n, 100)
    if h:
        hw = _HUNDREDS[h]
        parts.append(hw.replace("ientos", "ientas") if form == "f" else hw)
    if rest:
        if rest < 30:
            w = _UNITS[rest]
        else:
            t, u = divmod(rest, 10)
            w = _TENS[t] + (" y " + _UNITS[u] if u else "")
        parts.append(_ending(w, form))
    return " ".join(parts) or "cero"


def number_words(n: int, form: str = "m") -> str:
    """Cardinal en palabras. form: "m" uno, "a" un (antes de sustantivo), "f" una."""
    if n < 0:
        return "menos " + number_words(-n, form)
    if n >= 10**12:
        return " ".join(_DIGITS[int(d)] for d in str(n))
    if n < 1000:
        return _below_1000(n, form)
    millions, rest = divmod(n, 10**6)
    thousands, units = divmod(rest, 1000)
    parts = []
    if millions:
        parts.append("un millón" if millions == 1
                     else _below_1000(millions, "a") + " millones")
    if thousands:
        tf = "f" if form == "f" else "m"
        tw = "mil" if thousands == 1 else _ending(_below_1000(thousands, tf), "a") + " mil"
        parts.append(tw)
    if units:
        parts.append(_below_1000(units, form))
    return " ".join(parts)


def _digits_words(s: str) -> str:
    return " ".join(_DIGITS[int(d)] for d in s if d.isdigit())


def _decimal_words(dec: str) -> str:
    """Parte decimal: ceros a la izquierda como "cero", el resto como número."""
    zeros = len(dec) - len(dec.lstrip("0"))
    rest = dec[zeros:]
    words = ["cero"] * zeros
    if rest:
        words.append(number_words(int(rest)))
    return " ".join(words)


def _parse_num(s: str) -> tuple[int, str]:
    """"15.400,50" -> (15400, "50"); "1.5" -> (1, "5"); "2026" -> (2026, "")."""
    if "," in s:
        ip, dec = s.split(",", 1)
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        ip, dec = s, ""
    elif "." in s:
        ip, dec = s.split(".", 1)
    else:
        ip, dec = s, ""
    return int(ip.replace(".", "") or "0"), dec


def _num_words(s: str, form: str = "m") -> str:
    ip, dec = _parse_num(s)
    if dec:
        return number_words(ip) + " coma " + _decimal_words(dec)
    return number_words(ip, form)


# Número argentino: miles con punto y decimales con coma (o punto suelto).
_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?(?!\d)|\d+(?:[.,]\d+)?"
_B = r"(?<![\w.,])"  # que no esté pegado a otra palabra o número
_E = r"(?![\w]|[.,]\d)"

# --- Género por el sustantivo que sigue -----------------------------------

_FUNCTION = {
    "de", "del", "a", "al", "y", "e", "o", "u", "en", "con", "por", "para", "sin",
    "que", "es", "son", "ciento", "coma", "más", "menos", "hasta", "desde", "entre",
    "sobre", "ni", "la", "las", "el", "los", "lo", "un", "una", "mil", "millones",
    "millón", "punto", "barra", "guion", "arroba"
}
_FEM = {"vez", "veces", "noche", "noches", "clase", "clases", "parte", "partes",
        "gente", "llave", "llaves", "calle", "calles", "fuente", "tarde",
        "tardes", "sede", "sedes", "red", "redes", "imagen", "imágenes", "mujer",
        "mujeres", "ley", "flor", "flores", "cuota", "cuotas", "unidad",
        "unidades"}
_MASC_A = {"día", "días", "mapa", "mapas", "problema", "problemas", "programa",
           "programas", "sistema", "sistemas", "tema", "temas", "idioma",
           "idiomas", "clima", "plan", "planeta", "dilema", "esquema", "drama",
           "pijama", "sofá", "sofás", "papá", "papás", "cometa", "poema"}


def _gender(word: str | None) -> str:
    """"f", "a" (masculino ante sustantivo) o "m" (sin sustantivo)."""
    if not word:
        return "m"
    w = word.lower()
    if w in _FUNCTION:
        return "m"
    if w in _FEM:
        return "f"
    if w in _MASC_A:
        return "a"
    if w.endswith(("a", "as", "ión", "iones", "dad", "dades", "tud", "tudes")):
        return "f"
    return "a"


# --- Letras -----------------------------------------------------------------

_LETTERS = {
    "a": "a", "b": "be", "c": "ce", "d": "de", "e": "e", "f": "efe", "g": "ge",
    "h": "hache", "i": "i", "j": "jota", "k": "ka", "l": "ele", "m": "eme",
    "n": "ene", "ñ": "eñe", "o": "o", "p": "pe", "q": "cu", "r": "erre",
    "s": "ese", "t": "te", "u": "u", "v": "ve", "w": "doble ve", "x": "equis",
    "y": "ye", "z": "zeta", "-": "guion", "_": "guion bajo", ".": "punto",
    "/": "barra",
}


def _spell(code: str) -> str:
    out = []
    for ch in code:
        if ch.isdigit():
            out.append(_DIGITS[int(ch)])
        elif ch.lower() in _LETTERS:
            out.append(_LETTERS[ch.lower()])
    return ", ".join(out)


# --- Limpieza ---------------------------------------------------------------

_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:[^)\s]+)\)")
_MD_HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]+", re.MULTILINE)
_MD_BULLET = re.compile(r"^[ \t]*[-*•·][ \t]+", re.MULTILINE)
_MD_MARKS = re.compile(r"\*\*|__|`+|~~")
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U0000FE0F\U0000200D\U000020E3]+"
)

# --- Mails y URLs -----------------------------------------------------------

_EMAIL = re.compile(r"(?<![\w.])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TLDS = ("com|ar|net|org|io|gob|gov|edu|app|ai|co|info|dev|me|tv|es|uy|cl|mx|"
         "br|py|bo|pe|us|online|site|store|shop|tech|biz|la|xyz")
_URL = re.compile(
    rf"(?:https?://|www\.)[^\s<>()]+"
    rf"|(?<![\w@.])(?:[a-z0-9-]+\.)+(?:{_TLDS})\b(?:/[^\s<>()]*)?",
    re.IGNORECASE,
)
_TRAIL = ".,;:!?)»\"'"
_WORD_CHUNK = re.compile(r"[^\W\d_]+|\d+|[._\-+/=~]")
_SEP_WORDS = {".": "punto", "_": "guion bajo", "-": "guion", "+": "más",
              "/": "barra", "=": "igual", "~": "virgulilla"}


def _say_chunks(s: str) -> str:
    out = []
    for tok in _WORD_CHUNK.findall(s):
        if tok.isdigit():
            out.append(_digits_words(tok))
        elif tok in _SEP_WORDS:
            out.append(_SEP_WORDS[tok])
        else:
            out.append(tok)
    return " ".join(out)


def _email(m: re.Match) -> str:
    local, domain = m.group(0).split("@", 1)
    return _say_chunks(local) + " arroba " + _say_chunks(domain)


def _url(m: re.Match) -> str:
    raw = m.group(0)
    tail = ""
    while raw and raw[-1] in _TRAIL:
        tail = raw[-1] + tail
        raw = raw[:-1]
    s = re.sub(r"^https?://", "", raw, flags=re.IGNORECASE)
    s = re.sub(r"^www\.", "", s, flags=re.IGNORECASE)
    s = re.split(r"[?#]", s, 1)[0].rstrip("/")
    return _say_chunks(s) + tail


# --- Números con contexto ---------------------------------------------------

_NRO = re.compile(r"(?<!\w)(?:[Nn][º°]|[Nn]ro\.?|[Nn]úm\.?)\s?(?=\d)")
_DNI = re.compile(r"\b(D\.?N\.?I\.?:?\s*(?:n[úu]mero\s*)?)(\d{1,3}(?:\.\d{3}){1,2}|\d{7,8})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_DATE = re.compile(r"(?<![\d/.,])(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?(?![\d/])")
_PHONE_PLUS = re.compile(r"\+\d[\d \-]{6,}\d")
_PHONE = re.compile(r"(?<![\d.,])\d{2,}(?:[ \-]\d{2,})*-\d{2,}(?:[ \-]\d{2,})*(?![\d.,]\d)|(?<![\d.,])\d{8,}(?![\d,]|\.\d)")
_TIME = re.compile(
    r"\b([01]?\d|2[0-4]):([0-5]\d)(?:\s?(?:-|a)\s?([01]?\d|2[0-4]):([0-5]\d))?"
    r"(?:\s?(?:hs|hrs|h)\b\.?)?"
)
_HOURS = re.compile(r"\b(?:([01]?\d|2[0-4])\s?(-|a)\s?)?([01]?\d|2[0-4])\s?(?:hs|hrs|h)\b\.?")
_AMPM = re.compile(r"\b(1[0-2]|0?\d)\s?([ap])\.?\s?m\.?(?![\w])", re.IGNORECASE)
_MONEY = re.compile(
    rf"(US\$|U\$S|u\$s|USD|ARS|EUR|\$|€)\s?({_NUM})(?!\d)"
    rf"|{_B}({_NUM})\s?(USD|ARS|EUR|€)(?!\w)"
)
_PERCENT = re.compile(rf"{_B}({_NUM})\s?%")
_ORDINAL = re.compile(
    r"\b(\d{1,2})(?:([º°ª])(C\b)?|\.?(er|ra|ro|da|do|ta|to|va|vo|na|no|ma|mo)\b)"
    r"(?=\s+([^\W\d_]+))?"
)
_UNITS_RE = re.compile(rf"{_B}({_NUM})\s?(km|kg|cm|mm|ml|lts?|m2|m²|m³|m3|gr)(?!\w)")
_MULT = re.compile(r"(?<![\w.,])(\d+)\s?[x×]\s?(\d+)(?![\w])")
_PLUS = re.compile(r"(\d)\s?\+\s?(?=\d)")
_RANGE = re.compile(r"(?<![\w.,/-])(\d+)\s?-\s?(?=\d+(?![\w/-]))")
_CODE = re.compile(
    r"(?<![\w-])(?=[A-Za-z0-9-]*\d)(?=[A-Za-z0-9-]*[A-Za-z])"
    r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*(?![\w-])"
)
_KEYPAD = re.compile(r"([#*])\s?(\d+)(?!\d)")
_NUMBER = re.compile(rf"{_B}({_NUM}){_E}(?:(\s+)([^\W\d_]+))?")

_MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre"
]
_ORD = ["primer", "segund", "tercer", "cuart", "quint", "sext", "séptim", "octav", "noven", "décim"]
_CURRENCY = {"$": ("peso", "pesos"), "ARS": ("peso", "pesos"),
             "US$": ("dólar", "dólares"), "U$S": ("dólar", "dólares"),
             "u$s": ("dólar", "dólares"), "USD": ("dólar", "dólares"),
             "EUR": ("euro", "euros"), "€": ("euro", "euros")}


def _date_words(d: int, m: int, y: str | None) -> str | None:
    if not (1 <= d <= 31 and 1 <= m <= 12):
        return None
    out = ("primero" if d == 1 else number_words(d)) + " de " + _MONTHS[m - 1]
    if y:
        year = int(y) + (2000 if len(y) == 2 else 0)
        out += " de " + number_words(year)
    return out


def _date(m: re.Match) -> str:
    return _date_words(int(m.group(1)), int(m.group(2)), m.group(3)) or m.group(0)


def _iso_date(m: re.Match) -> str:
    return _date_words(int(m.group(3)), int(m.group(2)), m.group(1)) or m.group(0)


def _hour_words(h: int) -> str:
    return number_words(h, "f")


def _clock(h: int, mi: int) -> str:
    out = _hour_words(h)
    if mi == 15:
        return out + " y cuarto"
    if mi == 30:
        return out + " y media"
    if mi:
        return out + " y " + number_words(mi)
    return out


def _time(m: re.Match) -> str:
    out = _clock(int(m.group(1)), int(m.group(2)))
    if m.group(3):
        out += " a " + _clock(int(m.group(3)), int(m.group(4)))
    return out


def _hours(m: re.Match) -> str:
    h = int(m.group(3))
    unit = "hora" if h == 1 and not m.group(1) else "horas"
    out = _hour_words(h) + " " + unit
    if m.group(1):
        out = _hour_words(int(m.group(1))) + " a " + out
    return out


def _ampm(m: re.Match) -> str:
    h = int(m.group(1))
    if m.group(2).lower() == "a":
        part = "de la mañana" if h != 12 else "de la noche"
    elif h == 12:
        part = "del mediodía"
    else:
        part = "de la tarde" if h <= 7 else "de la noche"
    return _hour_words(h) + " " + part


def _phone_groups(s: str) -> str:
    out = []
    if s.startswith("+"):
        out.append("más")
        s = s[1:]
    groups = [g for g in re.split(r"[ \-]+", s) if g]
    if len(groups) == 1 and len(groups[0]) >= 8:
        g = groups[0]
        head, last = g[:-4], g[-4:]
        groups = [head[i:i + 3] for i in range(0, len(head), 3)] + [last]
    words = ", ".join(_digits_words(g) for g in groups)
    return (out[0] + " " + words) if out else words


def _phone(m: re.Match) -> str:
    raw = m.group(0)
    groups = re.split(r"[ \-]+", raw)
    if sum(len(g) for g in groups) < 8:
        return raw
    if len(groups) == 2 and all(re.fullmatch(r"(?:19|20)\d\d", g) for g in groups):
        return raw  # rango de años: "2025-2026"
    return _phone_groups(raw)


def _money(m: re.Match) -> str:
    sym, num = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
    one, many = _CURRENCY[sym]
    ip, dec = _parse_num(num)
    words = number_words(ip, "a")
    if ip == 1:
        unit = one
    elif words.endswith(("millón", "millones")):
        unit = "de " + many
    else:
        unit = many
    out = words + " " + unit
    cents = int((dec + "0")[:2]) if dec else 0
    if cents:
        out += " con " + number_words(cents, "a") + (" centavo" if cents == 1 else " centavos")
    return out


def _ordinal(m: re.Match) -> str:
    n = int(m.group(1))
    sym, celsius, suf = m.group(2), m.group(3), m.group(4)
    if sym == "°" and (celsius or n > 10):
        return number_words(n) + (" grado" if n == 1 else " grados")
    if not 1 <= n <= 10:
        return number_words(n)
    stem = _ORD[n - 1]
    if n in (1, 3) and (suf == "er" or (suf in (None, "ro") and sym != "ª"
                                         and _gender(m.group(5)) == "a")):
        return stem  # primer piso, tercer turno
    fem = sym == "ª" or (suf is not None and suf.endswith("a"))
    return stem + ("a" if fem else "o")


_UNIT_NAMES = {"km": "kilómetros", "kg": "kilos", "cm": "centímetros",
               "mm": "milímetros", "ml": "mililitros", "lt": "litros",
               "lts": "litros", "m2": "metros cuadrados", "m²": "metros cuadrados",
               "m3": "metros cúbicos", "m³": "metros cúbicos", "gr": "gramos"}
_UNIT_ONE = {"kilómetros": "kilómetro", "kilos": "kilo", "centímetros": "centímetro",
             "milímetros": "milímetro", "mililitros": "mililitro", "litros": "litro",
             "metros cuadrados": "metro cuadrado", "metros cúbicos": "metro cúbico",
             "gramos": "gramo"}


def _unit(m: re.Match) -> str:
    name = _UNIT_NAMES[m.group(2)]
    ip, dec = _parse_num(m.group(1))
    if ip == 1 and not dec:
        return "un " + _UNIT_ONE[name]
    return _num_words(m.group(1), "a") + " " + name


def _number(m: re.Match) -> str:
    num, space, word = m.group(1), m.group(2) or "", m.group(3) or ""
    form = _gender(word)
    words = _num_words(num, form)
    if word and form != "m" and words.endswith(("millón", "millones")):
        words += " de"
    return words + space + word


def to_speech(text: str, language: str = "es") -> str:
    """Texto listo para el TTS. Con un idioma que no es español, sin cambios."""
    if not text or re.split(r"[-_]", (language or "").lower())[0] != "es":
        return text
    s = _MD_LINK.sub(r"\1", text)
    s = _MD_HEADING.sub("", s)
    s = _MD_BULLET.sub("", s)
    s = _MD_MARKS.sub("", s)
    s = _EMOJI.sub("", s)

    s = _EMAIL.sub(_email, s)
    s = _URL.sub(_url, s)
    s = _NRO.sub("número ", s)
    s = _DNI.sub(lambda m: m.group(1) + number_words(int(m.group(2).replace(".", ""))), s)
    s = _ISO_DATE.sub(_iso_date, s)
    s = _PHONE_PLUS.sub(lambda m: _phone_groups(m.group(0)), s)
    s = _PHONE.sub(_phone, s)
    s = _DATE.sub(_date, s)
    s = _TIME.sub(_time, s)
    s = _HOURS.sub(_hours, s)
    s = _AMPM.sub(_ampm, s)
    s = _MONEY.sub(_money, s)
    s = _PERCENT.sub(lambda m: _num_words(m.group(1)) + " por ciento", s)
    s = _ORDINAL.sub(_ordinal, s)
    s = _UNITS_RE.sub(_unit, s)
    s = _MULT.sub(r"\1 por \2", s)
    s = _PLUS.sub(r"\1 más ", s)
    s = _CODE.sub(lambda m: _spell(m.group(0)), s)
    s = _RANGE.sub(r"\1 a ", s)
    s = _KEYPAD.sub(lambda m: ("numeral " if m.group(1) == "#" else "asterisco ")
                    + _digits_words(m.group(2)), s)
    s = _NUMBER.sub(_number, s)

    s = s.replace("&", " y ").replace("*", "").replace("#", "")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([,.;:!?])", r"\1", s)
    return s.strip()


# Fin de una oracion en un texto que llega por partes: puntuacion seguida de un espacio o salto de linea
# (sin espacio, "11.30" o "ana.gomez@" no cortan).
_SENTENCE_END = re.compile(r"[.!?;:…]\s+|\n")


async def speech_stream(chunks, language: str = "es"):
    """El texto del LLM en streaming, normalizado por oracion: junta hasta un fin de oracion y la entrega con
    to_speech (el TTS de LiveKit ya agrupa por oracion, asi que no suma espera)."""
    buffer = ""
    async for chunk in chunks:
        buffer += chunk
        cut = None
        for m in _SENTENCE_END.finditer(buffer):
            cut = m.end()
        if cut is not None:
            yield to_speech(buffer[:cut], language) + " "
            buffer = buffer[cut:]
    if buffer.strip():
        yield to_speech(buffer, language)
