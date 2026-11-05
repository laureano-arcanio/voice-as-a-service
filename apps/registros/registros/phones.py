"""Teléfono canónico, la clave con la que se busca una ficha.

Misma forma que la plataforma, reimplementada sin importarla: 54 más 10 dígitos para Argentina, sin
el 9 de celular. Un fijo y un celular de 10 dígitos no se distinguen."""
import re

MIN_DIGITS = 8
MAX_DIGITS = 20  # person_phones.phone es String(20)

# Característica argentina (11, o 3 y 4 dígitos que empiezan con 2 o 3), el 15 y el resto.
_WITH_15 = re.compile(r"(11|[23]\d{2,3})15(\d+)")


def _drop_15(national: str) -> str | None:
    """12 dígitos nacionales con el 15 tipeado después de la característica: los 10 sin el 15."""
    match = _WITH_15.fullmatch(national)
    return match.group(1) + match.group(2) if match else None


def canonical_phone(value: str | None) -> str:
    """Forma canónica para comparar. Vacío si no alcanza a ser un teléfono (o no entra en la columna)."""
    number = re.sub(r"\D", "", value or "")
    if not MIN_DIGITS <= len(number) <= MAX_DIGITS:
        return ""
    length = len(number)
    if length == 12 and number.startswith("54"):
        return number
    if length == 13 and number.startswith("549"):
        return "54" + number[3:]
    if length == 11 and number.startswith("0"):
        return "54" + number[1:]
    if length == 10:
        return "54" + number
    # La misma numeración con el 15 tipeado.
    for prefix, total in (("549", 15), ("54", 14), ("0", 13), ("", 12)):
        if length == total and number.startswith(prefix):
            national = _drop_15(number[len(prefix):])
            if national:
                return "54" + national
    return number
