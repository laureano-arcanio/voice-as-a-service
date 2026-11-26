"""Chequeos deterministas de un caso de prueba (docs/features/CASOS_DE_PRUEBA.md).

Un chequeo es `{type, ...}`; `validate` los normaliza y `evaluate` los corre contra la respuesta de una
repeticion (`reply = {text, tool_calls, handoff, tool_results}`). Cada falla es `{check, message, span?}`; `span`
es el texto del LLM que la provoca, cuando hay uno, para resaltarlo en la UI.

| Tipo | Campos | Pasa cuando |
|---|---|---|
| `usa_herramienta` | `tool`, `argumentos_contienen?` | el turno llamo a `tool` y (si viene) sus argumentos contienen el texto |
| `no_usa_herramienta` | `tool?` | no llamo a esa herramienta (sin `tool`: a ninguna) |
| `deriva_a` | `area` | el turno derivo a esa area |
| `no_deriva` | | el turno no derivo |
| `dice` | `text` | el texto del LLM (o como lo dice el TTS) contiene `text` |
| `no_dice` | `text` | no lo contiene |
| `empieza_con` | `text` | el texto del LLM empieza con `text` (salvo signos de apertura) |
| `datos_de_la_herramienta` | | toda hora `H:MM` y todo importe `$N` del texto esta entre los resultados que recibio el modelo |

El texto se compara sin tildes, en minusculas y con los espacios colapsados. Una coincidencia no vale pegada a una
letra o un digito, ni a un `.`/`,` seguido de digito ("130" no esta en "1.130" ni en "130.000"). `datos_de_la_
herramienta` recorre el JSON de los resultados (numeros y cifras dentro de strings, en formato argentino y plano):
lo dicho en palabras no se controla. Son reglas de la plataforma: no hay nada de un cliente ni de un modelo.
"""
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from ..voice.speech_text import to_speech

MAX_CHECKS = 20
MAX_TEXT = 500
MAX_NAME = 200
MAX_TOOL = 64
CHECK_TYPES = ("usa_herramienta", "no_usa_herramienta", "deriva_a", "no_deriva", "dice", "no_dice", "empieza_con",
               "datos_de_la_herramienta")
# Campos de texto de cada tipo, en el orden de la validacion.
TEXT_FIELDS = {"dice": ("text",), "no_dice": ("text",), "empieza_con": ("text",)}
NAME_FIELDS = {"usa_herramienta": ("tool",), "no_usa_herramienta": ("tool",), "deriva_a": ("area",)}
TIME_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?::\d{2})?(?!\d)")
# Un importe escrito con $: $13.500, $ 980, $1.250,50.
MONEY_RE = re.compile(r"\$\s?(\d+(?:[.,]\d+)*)")
DIGITS_RE = re.compile(r"\d+(?:[.,]\d+)*")
_NUM_TOKEN_RE = re.compile(r"^-?\d[\d.,]*$")


class CheckError(ValueError):
    """Un chequeo invalido: `path` es `checks.<i>.<campo>` y `message` dice que pasa."""

    def __init__(self, path: str, message: str):
        self.path, self.message = path, message
        super().__init__(f"{path}: {message}")


def _fold(text: str) -> tuple[str, list[int]]:
    """Texto comparable (sin tildes, minusculas, espacios colapsados) y el indice original de cada caracter."""
    out: list[str] = []
    index: list[int] = []
    for i, ch in enumerate(text or ""):
        base = "".join(c for c in unicodedata.normalize("NFD", ch)
                       if unicodedata.category(c) != "Mn").lower()
        for c in base:
            if c.isspace():
                if out and out[-1] == " ":
                    continue
                out.append(" ")
            else:
                out.append(c)
            index.append(i)
    while out and out[0] == " ":
        out.pop(0)
        index.pop(0)
    while out and out[-1] == " ":
        out.pop()
        index.pop()
    return "".join(out), index


def _normal(text: str) -> str:
    return _fold(text)[0]


def _boundary(folded: str, start: int, end: int) -> bool:
    """La coincidencia no esta pegada a letra o digito, ni a un `.`/`,` seguido de digito ("1.130", "130.000")."""
    before = folded[start - 1] if start > 0 else ""
    after = folded[end] if end < len(folded) else ""
    if before and before.isalnum():
        return False
    if after and after.isalnum():
        return False
    if before in ".," and start >= 2 and folded[start - 2].isdigit():
        return False
    if after in ".," and end + 1 < len(folded) and folded[end + 1].isdigit():
        return False
    return True


def _find(folded: str, needle: str) -> int | None:
    """Indice de la primera coincidencia valida, o None."""
    if not needle:
        return None
    start = folded.find(needle)
    while start != -1:
        end = start + len(needle)
        if _boundary(folded, start, end):
            return start
        start = folded.find(needle, start + 1)
    return None


def _speech(text: str) -> str:
    try:
        return _normal(to_speech(text or ""))
    except Exception:
        return _normal(text)


def _matches(reply_text: str, expected: str) -> tuple[int, int] | None:
    """(inicio, fin) en el texto original de la primera coincidencia, directa o como la dice el TTS."""
    folded, index = _fold(reply_text)
    needle = _normal(expected)
    start = _find(folded, needle)
    if start is not None:
        end = start + len(needle)
        return index[start], index[end - 1] + 1
    spoken_reply, spoken_index = _fold(to_speech(reply_text or ""))
    spoken = _speech(expected)
    start = _find(spoken_reply, spoken)
    if start is not None:
        # El indice es del texto pasado por el TTS: se devuelve el texto original entero, sin marcar.
        return 0, len(reply_text or "")
    return None


def _starts(reply_text: str, expected: str) -> bool:
    folded, _ = _fold(reply_text)
    folded = folded.lstrip("¡¿\"'“”‘’(¡!.,;: ")
    return bool(folded) and folded.startswith(_normal(expected).lstrip("¡¿\"'“”‘’(¡!.,;: "))


def _json_value(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None
    return None


def _call_args(call: dict) -> dict | None:
    return _json_value(call.get("arguments"))


def _as_decimal(text: str, mode: str) -> Decimal | None:
    """``mode``: "ar" (punto de miles, coma decimal) o "plain" (coma de miles, punto decimal)."""
    token = (text or "").strip()
    if not token or not _NUM_TOKEN_RE.fullmatch(token):
        return None
    try:
        if mode == "ar":
            return Decimal(token.replace(".", "").replace(",", "."))
        return Decimal(token.replace(",", ""))
    except InvalidOperation:
        return None


def _numbers_in(value, numbers: set[Decimal], times: set[tuple[int, int]]) -> None:
    """Suma al conjunto los numeros del JSON y las cifras dentro de sus strings, en los dos formatos."""
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float, Decimal)):
        try:
            numbers.add(Decimal(str(value)))
        except InvalidOperation:
            pass
        return
    if isinstance(value, str):
        for m in DIGITS_RE.finditer(value):
            for mode in ("ar", "plain"):
                if (number := _as_decimal(m.group(0), mode)) is not None:
                    numbers.add(number)
        for m in TIME_RE.finditer(value):
            times.add((int(m.group(1)), int(m.group(2))))
        return
    if isinstance(value, dict):
        for item in value.values():
            _numbers_in(item, numbers, times)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _numbers_in(item, numbers, times)


def _tool_data(results: list[str]) -> tuple[set[Decimal], set[tuple[int, int]]]:
    numbers: set[Decimal] = set()
    times: set[tuple[int, int]] = set()
    for raw in results or []:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            data = raw
        _numbers_in(data, numbers, times)
    return numbers, times


# ----------.validate ----------

def _text(value, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CheckError(path, "falta el texto")
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > MAX_TEXT:
        raise CheckError(path, f"hasta {MAX_TEXT} caracteres")
    return value


def _name(value, path: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CheckError(path, f"falta {field}")
    value = value.strip()
    limit = MAX_TOOL if field == "tool" else MAX_NAME
    if len(value) > limit:
        raise CheckError(path, f"hasta {limit} caracteres")
    return value


def validate(checks) -> list[dict]:
    """Normaliza la lista de chequeos. ValueError (CheckError) con `checks.<i>.<campo>` si uno no vale."""
    if checks is None:
        return []
    if not isinstance(checks, list):
        raise CheckError("checks", "tiene que ser una lista")
    if len(checks) > MAX_CHECKS:
        raise CheckError("checks", f"hasta {MAX_CHECKS} chequeos")
    out = []
    for i, raw in enumerate(checks):
        if not isinstance(raw, dict):
            raise CheckError(f"checks.{i}", "tiene que ser un objeto")
        kind = raw.get("type")
        if kind not in CHECK_TYPES:
            raise CheckError(f"checks.{i}.type", f"tipo desconocido: {kind!r}")
        check = {"type": kind}
        for field in TEXT_FIELDS.get(kind, ()):
            check[field] = _text(raw.get(field), f"checks.{i}.{field}")
        for field in NAME_FIELDS.get(kind, ()):
            if kind == "no_usa_herramienta" and raw.get(field) in (None, ""):
                continue
            check[field] = _name(raw.get(field), f"checks.{i}.{field}", field)
        if kind == "usa_herramienta" and raw.get("argumentos_contienen") not in (None, ""):
            check["argumentos_contienen"] = _text(raw.get("argumentos_contienen"),
                                                  f"checks.{i}.argumentos_contienen")
        out.append(check)
    return out


# ---------- evaluate ----------

def _call_names(reply: dict) -> list[dict]:
    return [c for c in (reply.get("tool_calls") or []) if isinstance(c, dict) and c.get("name")]


def _fail(check: dict, message: str, span: str | None = None) -> dict:
    out = {"check": check, "message": message}
    if span:
        out["span"] = span
    return out


def _tool_used(reply: dict, tool: str) -> bool:
    return any(c["name"] == tool for c in _call_names(reply))


def _check_one(check: dict, reply: dict, numbers: set[Decimal], times: set[tuple[int, int]]) -> dict | None:
    kind = check["type"]
    text = reply.get("text") or ""
    calls = _call_names(reply)
    handoff = reply.get("handoff")
    if kind == "usa_herramienta":
        tool = check["tool"]
        used = [c for c in calls if c["name"] == tool]
        if not used:
            return _fail(check, f"No usó la herramienta {tool!r}")
        wanted = check.get("argumentos_contienen")
        if wanted:
            found = False
            for call in used:
                args = _call_args(call)
                raw = json.dumps(args, ensure_ascii=False, sort_keys=True) if args is not None \
                    else str(call.get("arguments") or "")
                if _normal(wanted) in _normal(raw):
                    found = True
                    break
            if not found:
                return _fail(check, f"Los argumentos de {tool!r} no contienen {wanted!r}")
        return None
    if kind == "no_usa_herramienta":
        tool = check.get("tool")
        if tool:
            if _tool_used(reply, tool):
                return _fail(check, f"Usó la herramienta {tool!r}")
        elif calls:
            names = ", ".join(sorted({c["name"] for c in calls}))
            return _fail(check, f"Usó herramientas: {names}")
        return None
    if kind == "deriva_a":
        if handoff != check["area"]:
            if handoff:
                return _fail(check, f"Derivó a {handoff!r}, no a {check['area']!r}")
            return _fail(check, f"No derivó a {check['area']!r}")
        return None
    if kind == "no_deriva":
        return _fail(check, f"Derivó a {handoff!r}") if handoff else None
    if kind in ("dice", "no_dice"):
        span = _matches(text, check["text"])
        if kind == "dice":
            return None if span else _fail(check, f"No dijo {check['text']!r}")
        return _fail(check, f"Dijo {check['text']!r}", text[span[0]:span[1]]) if span else None
    if kind == "empieza_con":
        return None if _starts(text, check["text"]) else _fail(check, f"No empieza con {check['text']!r}")
    if kind == "datos_de_la_herramienta":
        failures = []
        for m in TIME_RE.finditer(text):
            found = (int(m.group(1)), int(m.group(2)))
            if found not in times:
                failures.append(_fail(check, f"La hora {m.group(0)!r} no está en el resultado de la herramienta",
                                      m.group(0)))
        for m in MONEY_RE.finditer(text):
            value = _as_decimal(m.group(1), "ar")
            if value is None:
                continue
            if value not in numbers:
                failures.append(_fail(check, f"El importe {m.group(0)!r} no está en el resultado de la herramienta",
                                      m.group(0)))
        # Una sola falla por chequeo: la primera hora o importe que no figura.
        return failures[0] if failures else None
    return None


def evaluate(checks: list[dict], reply: dict) -> list[dict]:
    """Las fallas de los chequeos contra una repeticion: `{check, message, span?}`."""
    numbers, times = _tool_data(list(reply.get("tool_results") or []))
    out = []
    for check in checks or []:
        if failure := _check_one(check, reply, numbers, times):
            out.append(failure)
    return out


def suggest(reply: dict) -> list[dict]:
    """Los chequeos que sugiere una respuesta: derivo, uso herramientas y sus datos."""
    out: list[dict] = []
    if reply.get("handoff"):
        out.append({"type": "no_deriva"})
    names = []
    for call in _call_names(reply):
        if call["name"] not in names:
            names.append(call["name"])
    for name in names:
        out.append({"type": "usa_herramienta", "tool": name})
    if names and reply.get("tool_results"):
        out.append({"type": "datos_de_la_herramienta"})
    return out
