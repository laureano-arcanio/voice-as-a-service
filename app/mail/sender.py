"""Envio por Resend (https://resend.com/docs/api-reference/emails/send-email).

Un fallo de Resend nunca corta la operacion que lo pidio: se devuelve el resultado y se loguea.
"""
import logging
from dataclasses import dataclass

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    html: str
    text: str


@dataclass(frozen=True)
class SendResult:
    status: str                 # sent, failed o disabled (sin RESEND_API_KEY)
    id: str | None = None       # id del mail en Resend
    error: str | None = None


def send(mail: Mail, idempotency_key: str | None = None) -> SendResult:
    if not settings.resend_api_key:
        logger.info("mail a %s no enviado (sin RESEND_API_KEY): %s", mail.to, mail.subject)
        return SendResult("disabled")
    headers = {"Authorization": f"Bearer {settings.resend_api_key}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    body = {"from": settings.mail_from, "to": [mail.to], "subject": mail.subject, "html": mail.html,
            "text": mail.text}
    try:
        r = httpx.post(RESEND_URL, json=body, headers=headers, timeout=10)
    except httpx.HTTPError as e:
        logger.warning("mail a %s: Resend no respondio: %s", mail.to, e)
        return SendResult("failed", error=(str(e) or type(e).__name__)[:255])
    if r.status_code >= 400:
        logger.warning("mail a %s: Resend %s: %s", mail.to, r.status_code, r.text[:300])
        return SendResult("failed", error=f"{r.status_code} {r.text}"[:255])
    return SendResult("sent", id=r.json().get("id"))
