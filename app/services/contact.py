"""Formulario de contacto de la landing: guarda el pedido y avisa por mail con Resend.

Usa la sesion de la demo (Turnstile) y su limitador por IP. Ver docs/LANDING.md.
"""
import asyncio
import logging
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ContactRequest
from ..models._common import new_id
from .demo import DAY, HOUR, limiter
from .ratelimit import Limit, client_key

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


@dataclass
class ContactData:
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    message: str = ""
    page: str = ""


def _one_line(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


def _recipients() -> list[str]:
    return [a.strip() for a in settings.contact_to.split(",") if a.strip()]


def _email(data: ContactData, ip: str) -> dict:
    who = data.company or data.name
    lines = [
        f"Pedido de demo desde atentina.com.ar{data.page}",
        "",
        f"Nombre: {data.name}",
        f"Empresa: {data.company or '-'}",
        f"Email: {data.email or '-'}",
        f"Teléfono: {data.phone or '-'}",
        f"IP: {ip}",
        "",
        "Mensaje:",
        data.message or "-",
    ]
    body = {
        "from": settings.contact_from,
        "to": _recipients(),
        "subject": _one_line(f"Pedido de demo: {who}", 120),
        "text": "\n".join(lines),
    }
    if data.email:
        body["reply_to"] = data.email
    return body


async def _send(row_id: str, body: dict) -> tuple[str, str | None, str | None]:
    """(email_status, email_id, email_error)."""
    if not settings.resend_api_key or not body["to"]:
        return "disabled", None, None
    headers = {"Authorization": f"Bearer {settings.resend_api_key}", "Idempotency-Key": row_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(RESEND_URL, json=body, headers=headers)
    except httpx.HTTPError as e:
        logger.warning("contacto %s: Resend no respondio: %s", row_id, e)
        return "failed", None, _one_line(str(e) or type(e).__name__, 255)
    if r.status_code >= 400:
        logger.warning("contacto %s: Resend %s: %s", row_id, r.status_code, r.text[:300])
        return "failed", None, _one_line(f"{r.status_code} {r.text}", 255)
    return "sent", r.json().get("id"), None


async def submit(s: Session, data: ContactData, ip: str) -> None:
    limiter.consume(f"contact:{client_key(ip)}",
                    [Limit(settings.contact_ip_per_hour, HOUR), Limit(settings.contact_ip_per_day, DAY)],
                    "Ya recibimos tus datos. Si necesitás algo más, escribinos por WhatsApp.")
    row_id = new_id()
    row = ContactRequest(id=row_id, name=data.name, company=data.company, email=data.email, phone=data.phone,
                         message=data.message, page=data.page, ip=ip)

    def save() -> None:
        s.add(row)
        s.commit()

    await asyncio.to_thread(save)
    status, email_id, error = await _send(row_id, _email(data, ip))

    def mark() -> None:
        row.email_status, row.email_id, row.email_error = status, email_id, error
        s.commit()

    await asyncio.to_thread(mark)
