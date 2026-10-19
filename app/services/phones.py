"""Telefonos: una sola normalizacion a E.164 (+549351..., con el +) para los dos canales
(docs/LLAMADAS_SALIENTES_PLAN.md, 3.1). Contactos, campañas y bajas guardan este formato; el
`wa_id` que manda Meta es el mismo numero sin el +.

Argentina sin codigo de pais, o con 54 sin el 9, se toma como celular (+549...): un fijo
con codigo de area no se distingue de un celular, y los celulares son lo que se carga."""
import re

ARGENTINA = "+54"
ARGENTINA_MOBILE = "+549"


def normalize_phone(raw: str) -> str:
    """El telefono en E.164. ValueError si no se reconoce. Argentina sin codigo de pais
    (351 555-1234, 0351 5551234) o con 54 / 549; otro pais, con + o 00 adelante."""
    text = (raw or "").strip()
    international = text.startswith(("+", "00"))
    digits = re.sub(r"\D", "", text)
    if text.startswith("00"):
        digits = digits[2:]
    if not digits:
        raise ValueError("sin número")
    if digits.startswith("54") and (international or len(digits) in (12, 13)):
        national = digits[3:] if digits.startswith("549") else digits[2:]
        if len(national) != 10:
            raise ValueError("número argentino con largo inválido (código de área + número: 10 dígitos)")
        return "+549" + national
    if international:
        if not 8 <= len(digits) <= 15:
            raise ValueError("número internacional con largo inválido")
        return "+" + digits
    digits = digits.removeprefix("0")
    if len(digits) == 10:
        return "+549" + digits
    raise ValueError("formato no reconocido: código de área + número sin el 15 (351 555-1234), o +54 9 ...")


def wa_id(phone: str) -> str:
    """El id de WhatsApp (el que manda Meta) de un E.164: el mismo numero sin el +."""
    return phone.removeprefix("+")


def from_wa_id(value: str) -> str:
    """El E.164 de un wa_id de Meta."""
    return "+" + value.removeprefix("+")


def has_whatsapp(phone: str) -> bool:
    """Un fijo argentino (+54 sin el 9) no tiene WhatsApp; el resto se asume que si."""
    return not phone.startswith(ARGENTINA) or phone.startswith(ARGENTINA_MOBILE)
