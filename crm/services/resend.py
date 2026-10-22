"""Cliente de Resend: enviar (con encabezados de hilo) y leer el estado de un envio."""
import html
import re

import httpx

from ..config import settings

API = "https://api.resend.com"
LINK = re.compile(r"https://atentina\.com\.ar/\?\S+")


class ResendError(Exception):
    pass


def to_html(text: str) -> str:
    """Parrafos y el link largo con UTM como "atentina.com.ar" (como en los envios de octubre)."""
    out = []
    for p in text.split("\n\n"):
        seg, last = [], 0
        for m in LINK.finditer(p):
            seg.append(html.escape(p[last:m.start()]))
            seg.append(f'<a href="{html.escape(m.group(0))}">atentina.com.ar</a>')
            last = m.end()
        seg.append(html.escape(p[last:]))
        out.append("<p>" + "".join(seg).replace("\n", "<br>") + "</p>")
    return "".join(out)


def _headers() -> dict:
    if not settings.resend_api_key:
        raise ResendError("falta CRM_RESEND_API_KEY")
    return {"Authorization": f"Bearer {settings.resend_api_key}", "User-Agent": "atentina-crm"}


def send(*, idempotency_key: str, from_addr: str, to: str, subject: str, text: str,
         in_reply_to: str | None, bcc: str | None) -> str:
    body = {"from": from_addr, "to": [to], "subject": subject, "text": text, "html": to_html(text)}
    if bcc:
        body["bcc"] = [bcc]
    if in_reply_to:
        body["headers"] = {"In-Reply-To": in_reply_to, "References": in_reply_to}
    try:
        r = httpx.post(f"{API}/emails", json=body, headers=_headers() | {"Idempotency-Key": idempotency_key},
                       timeout=20)
    except httpx.HTTPError as e:
        raise ResendError(str(e) or type(e).__name__) from e
    if r.status_code >= 400:
        raise ResendError(f"{r.status_code} {r.text[:300]}")
    return r.json()["id"]


def get(resend_id: str) -> dict:
    """{last_event, message_id?, created_at, ...}"""
    try:
        r = httpx.get(f"{API}/emails/{resend_id}", headers=_headers(), timeout=20)
    except httpx.HTTPError as e:
        raise ResendError(str(e) or type(e).__name__) from e
    if r.status_code >= 400:
        raise ResendError(f"{r.status_code} {r.text[:300]}")
    return r.json()


def list_sent(limit_pages: int = 50) -> list[dict]:
    """Historial completo de lo enviado (lo usa el importador)."""
    out, after = [], None
    for _ in range(limit_pages):
        q = "?limit=100" + (f"&after={after}" if after else "")
        r = httpx.get(f"{API}/emails{q}", headers=_headers(), timeout=30)
        if r.status_code >= 400:
            raise ResendError(f"{r.status_code} {r.text[:300]}")
        d = r.json()
        out += d["data"]
        if not d.get("has_more") or not d["data"]:
            break
        after = d["data"][-1]["id"]
    return out


def list_received(after: str | None = None) -> dict:
    """Recibidos (Resend Receiving), del mas nuevo al mas viejo: {data: [{id, from, subject, created_at}], has_more}."""
    q = "?limit=100" + (f"&after={after}" if after else "")
    try:
        r = httpx.get(f"{API}/emails/receiving{q}", headers=_headers(), timeout=30)
    except httpx.HTTPError as e:
        raise ResendError(str(e) or type(e).__name__) from e
    if r.status_code >= 400:
        raise ResendError(f"{r.status_code} {r.text[:300]}")
    return r.json()


def get_received(resend_id: str) -> dict:
    """Un recibido entero: from, to, subject, text, html, headers (objeto), message_id, created_at."""
    try:
        r = httpx.get(f"{API}/emails/receiving/{resend_id}", headers=_headers(), timeout=30)
    except httpx.HTTPError as e:
        raise ResendError(str(e) or type(e).__name__) from e
    if r.status_code >= 400:
        raise ResendError(f"{r.status_code} {r.text[:300]}")
    return r.json()
