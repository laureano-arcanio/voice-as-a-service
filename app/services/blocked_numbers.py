"""Numeros bloqueados por cliente: sus llamadas entrantes (por linea o de WhatsApp) se cortan sin
atender y quedan como rechazadas con `blocked_number` (services/calls.start_inbound). Las salientes
no cambian: para no llamar a alguien estan las bajas (services/contacts.py)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BlockedNumber
from . import phones
from .errors import NotFound


def normalize(raw: str | None) -> str | None:
    """El E.164 de un telefono como llega (caller de Anura, wa_id de Meta o tipeado); None si no se reconoce."""
    try:
        return phones.normalize_phone(raw or "")
    except ValueError:
        return None


def add(s: Session, client_id: str, phone: str, note: str = "", created_by: str | None = None) -> BlockedNumber:
    """Bloquea el telefono (E.164). Si ya estaba, actualiza la nota si viene una."""
    row = s.get(BlockedNumber, (client_id, phone))
    if row is None:
        row = BlockedNumber(client_id=client_id, phone=phone, note=note, created_by=created_by)
        s.add(row)
    elif note:
        row.note = note
    s.flush()
    return row


def remove(s: Session, client_id: str, phone: str) -> None:
    row = s.get(BlockedNumber, (client_id, phone))
    if row is None:
        raise NotFound("Ese número no está bloqueado")
    s.delete(row)
    s.flush()


def list_blocked(s: Session, client_id: str | None) -> list[BlockedNumber]:
    q = select(BlockedNumber).order_by(BlockedNumber.created_at.desc(), BlockedNumber.phone)
    if client_id is not None:
        q = q.where(BlockedNumber.client_id == client_id)
    return list(s.scalars(q))


def is_blocked(s: Session, client_id: str, *raw_phones: str | None) -> bool:
    """Si alguno de los telefonos (el caller de la linea, el wa_id de WhatsApp) esta bloqueado."""
    numbers = {n for n in map(normalize, raw_phones) if n}
    return bool(numbers) and s.scalar(select(BlockedNumber.phone).where(
        BlockedNumber.client_id == client_id, BlockedNumber.phone.in_(numbers)).limit(1)) is not None
