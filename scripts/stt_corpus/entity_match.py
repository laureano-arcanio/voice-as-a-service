"""Acierto por entidad para el corpus de entities.py: si el STT dejo bien el
dato completo (email, telefono, DNI, direccion), escriba como lo escriba.

Lleva la transcripcion y la referencia a la misma forma canonica:
- numeros dictados de cualquier forma a digitos: "doce treinta y cuatro",
  "uno dos tres cuatro", "mil doscientos treinta y cuatro" y "1.234" dan 1234;
  los numeros seguidos se pegan, salvo que los separe una coma;
- ordinales a "3o" ("tercero", "3°", "3ro"): asi no se pegan a la altura;
- letras deletreadas a letras ("ele" -> l, "be larga" -> b, "doble ele" -> ll);
- "arroba", "punto", "guion bajo/medio" a @ . _ -;
- abreviaturas de direcciones ("Av." -> avenida, "Bv." -> bulevar).
Los mapeos se aplican igual a los dos lados, asi que no generan errores falsos.
"""
import re
import unicodedata

_UNITS = {w: i for i, w in enumerate("cero uno dos tres cuatro cinco seis siete ocho nueve".split())}
_TEENS = {w: 10 + i for i, w in enumerate(
    "diez once doce trece catorce quince dieciseis diecisiete dieciocho diecinueve".split())}
_TEENS |= {"veinti" + w: 20 + i for i, w in enumerate("_ uno dos tres cuatro cinco seis siete ocho nueve".split()) if i}
_TEENS |= {"veintiun": 21, "veintiuna": 21}
_TENS = {w: 10 * i for i, w in enumerate("_ _ veinte treinta cuarenta cincuenta sesenta setenta ochenta noventa".split()) if i > 1}
_HUNDREDS = {"cien": 100, "ciento": 100, "quinientos": 500, "quinientas": 500}
_HUNDREDS |= {p + s: 100 * i for i, p in enumerate("_ _ dos tres cuatro _ seis sete ocho nove".split())
              if i > 1 and p != "_" for s in ("cientos", "cientas")}
_MULT = {"mil": 1000, "millon": 10**6, "millones": 10**6}

_LETTERS = {"a": "a", "be": "b", "ce": "c", "de": "d", "e": "e", "efe": "f", "ge": "g", "hache": "h", "i": "i",
            "jota": "j", "ka": "k", "ele": "l", "eme": "m", "ene": "n", "eñe": "ñ", "o": "o", "pe": "p",
            "cu": "q", "erre": "r", "ere": "r", "ese": "s", "te": "t", "u": "u", "ve": "v", "uve": "v",
            "equis": "x", "ye": "y", "zeta": "z", "seta": "z"}
_TWO_WORDS = {("be", "larga"): "b", ("be", "alta"): "b", ("ve", "corta"): "v", ("ve", "baja"): "v",
              ("i", "latina"): "i", ("i", "griega"): "y", ("doble", "ve"): "w", ("doble", "u"): "w",
              ("guion", "bajo"): "_", ("guion", "medio"): "-",
              # La letra ya escrita con su aclaracion: "y griega", "v corta", "b larga", "doble v".
              ("y", "griega"): "y", ("v", "corta"): "v", ("v", "baja"): "v", ("b", "larga"): "b",
              ("b", "alta"): "b", ("doble", "v"): "w"}
_SYMBOLS = {"arroba": "@", "punto": ".", "guion": "-"}
_ORDINALS = {"primero": 1, "primer": 1, "segundo": 2, "tercero": 3, "tercer": 3, "cuarto": 4, "quinto": 5,
             "sexto": 6, "septimo": 7, "octavo": 8, "noveno": 9, "decimo": 10}
_ABBREV = {"av": "avenida", "avda": "avenida", "bv": "bulevar", "bvar": "bulevar", "boulevard": "bulevar",
           "gral": "general", "pje": "pasaje", "esq": "esquina", "dpto": "departamento", "depto": "departamento",
           "dto": "departamento"}
# Relleno en direcciones: "piso 3, departamento B" y "3, B" dicen lo mismo.
_ADDRESS_FILLER = {"piso", "departamento", "barrio", "numero", "nro", "n", "altura", "codigo", "postal", "cp", ","}


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn" or c == "̃")  # conserva la ñ
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"(\d)\s?[°º]|(\d)(?:ro|ero|er|do|to|mo|vo|no)\b", lambda m: (m[1] or m[2]) + "o", text)
    text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", text)  # 35.456.789 -> 35456789
    text = re.sub(r"\.(?=\s|$)", " ", text)  # punto de fin de frase o de abreviatura ("Av.")
    text = re.sub(r"([@._-])", r" \1 ", text)  # juan.perez@gmail.com -> juan . perez @ gmail . com
    return re.findall(r"[\w@._-]+|,", text)


def _numbers(tokens: list[str]) -> list[str]:
    """Palabras de numeros a digitos, componiendo como se dice en castellano.
    Un numero nuevo empieza cuando la palabra no puede seguir al anterior:
    "doce treinta" son 12 y 30, "ciento treinta" es 130."""
    out, cur = [], None  # cur: [total, segmento < 1000, ultima clase, espera unidad tras "y"]

    def flush():
        nonlocal cur
        if cur:
            out.append(str(cur[0] + cur[1]))
        cur = None

    def start():
        nonlocal cur
        flush()
        cur = [0, 0, "start", False]

    for i, t in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if t.isdigit():
            if cur and cur[2] == "mult" and cur[1] == 0 and len(t) <= 3:  # "35 millones 456 mil 789"
                cur[1], cur[2] = int(t), "digits"
            elif nxt in _MULT:
                start()
                cur[1], cur[2] = int(t), "digits"
            else:
                flush()
                out.append(t)  # tal cual: conserva ceros a la izquierda ("0351")
        elif t == "cero":
            flush()
            out.append("0")
        elif t in ("un", "una") and (nxt in _MULT or cur and cur[3]):  # "un millón", "ochenta y una"
            if not (cur and cur[3]):
                start()
            cur[1], cur[2], cur[3] = cur[1] + 1, "unit", False
        elif t in _MULT:
            if cur and cur[2] != "mult" and (cur[1] or cur[2] == "start"):
                cur[:] = [cur[0] + max(cur[1], 1) * _MULT[t], 0, "mult", False]
            else:
                start()
                cur[:] = [_MULT[t], 0, "mult", False]
        elif t in _HUNDREDS:
            if not (cur and cur[2] == "mult"):
                start()
            cur[1], cur[2] = _HUNDREDS[t], "hund"
        elif t in _TENS:
            if not (cur and cur[2] in ("hund", "mult")):
                start()
            cur[1], cur[2] = cur[1] + _TENS[t], "tens"
        elif t == "y" and cur and cur[2] == "tens" and (nxt in _UNITS and nxt != "cero" or nxt in ("un", "una")):
            cur[3] = True
        elif t in _UNITS or t in _TEENS:
            if not (cur and (cur[3] and t in _UNITS or cur[2] in ("hund", "mult") and not cur[3])):
                start()
            cur[1], cur[2], cur[3] = cur[1] + _UNITS.get(t, _TEENS.get(t)), "unit", False
        else:
            flush()
            out.append(t)
    flush()
    merged = []  # numeros seguidos, un solo numero: "12" "34" -> "1234"
    for t in out:
        if t.isdigit() and merged and merged[-1].isdigit():
            merged[-1] += t
        else:
            merged.append(t)
    return merged


def canon(text: str) -> list[str]:
    tokens, out, i = _tokens(text), [], 0
    while i < len(tokens):
        t, nxt = tokens[i], tokens[i + 1] if i + 1 < len(tokens) else ""
        if (t, nxt) in _TWO_WORDS:
            out.append(_TWO_WORDS[t, nxt])
            i += 2
        elif t == "doble" and nxt in _LETTERS:  # "doble ele" -> ll
            out.append(_LETTERS[nxt] * 2)
            i += 2
        else:
            out.append(_SYMBOLS.get(t) or _ABBREV.get(t) or (f"{_ORDINALS[t]}o" if t in _ORDINALS else t))
            i += 1
    return [_LETTERS.get(t, t) for t in _numbers(out)]


def _compact_find(tokens: list[str], target: str) -> bool:
    """target (ej. un email) armado con tokens pegados, empezando en un token y
    sin que siga pegado a otro . @ _ -: "es perez@..." no sirve para "sperez@..."."""
    for start in range(len(tokens)):
        acc = ""
        for end in range(start, len(tokens)):
            acc += tokens[end]
            if acc == target and (end + 1 == len(tokens) or tokens[end + 1] not in ".@_-"):
                return True
            if not target.startswith(acc):
                break
    return False


def _contains(tokens: list[str], sub: list[str]) -> bool:
    return bool(sub) and any(tokens[i:i + len(sub)] == sub for i in range(len(tokens) - len(sub) + 1))


def _address(text: str) -> list[str]:
    # El ordinal ya no se pega a la altura: "3o" y "3" (piso 3, 3° piso) son lo mismo.
    return [t[:-1] if re.fullmatch(r"\d+o", t) else t for t in canon(text)
            if t not in _ADDRESS_FILLER and t not in ".@_-"]


def match(category: str, hyp: str, expected: str, core: str = "") -> tuple[bool, bool]:
    """(dato completo bien, nucleo bien). En direcciones el nucleo es calle +
    altura; en el resto es el mismo dato."""
    if category == "email":
        # Comas y guiones de deletreo ("ele, a, erre", "L-A-R") no son parte del email.
        tokens = [t for t in canon(hyp) if t != ","]
        tokens = [t for i, t in enumerate(tokens) if not (t == "-" and 0 < i < len(tokens) - 1
                                                         and len(tokens[i - 1]) == 1 and len(tokens[i + 1]) == 1)]
        ok = _compact_find(tokens, expected.lower())
        return ok, ok
    if category in ("telefono", "dni"):
        ok = "".join(t for t in canon(hyp) if t.isdigit()) == expected
        return ok, ok
    tokens = _address(hyp)
    return _contains(tokens, _address(expected)), _contains(tokens, _address(core or expected))
