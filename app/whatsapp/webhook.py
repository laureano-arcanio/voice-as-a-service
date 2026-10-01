"""Webhook de WhatsApp (Meta): challenge GET y eventos POST firmados."""
import hashlib
import hmac
import json
import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wa", tags=["whatsapp"])

MAX_BODY_BYTES = 1024 * 1024  # 1 MiB; los eventos de Meta pesan unos pocos KB
_VERIFY_TOKEN_RE = re.compile(r"(hub[._]verify_token=)[^&\s]*")


class RedactVerifyToken(logging.Filter):
    """Tapa hub.verify_token en el access log de uvicorn (Meta lo manda en la query del GET)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(_VERIFY_TOKEN_RE.sub(r"\1***", a) if isinstance(a, str) else a
                                for a in record.args)
        return True


def install_logging() -> None:
    """Sin config de logging, los info de app.whatsapp se pierden (root en WARNING, sin handler)."""
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactVerifyToken) for f in access.filters):
        access.addFilter(RedactVerifyToken())
    log = logging.getLogger("app.whatsapp")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
        log.addHandler(handler)
    log.setLevel(logging.INFO)


@router.get("/webhook", include_in_schema=False)
def verify(request: Request):
    q = request.query_params
    token = settings.wa_verify_token
    if (token and q.get("hub.mode") == "subscribe"
            and hmac.compare_digest(q.get("hub.verify_token", "").encode(), token.encode())):
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403)


def _valid_signature(raw: bytes, header: str | None) -> bool:
    secret = settings.wa_app_secret
    if not secret or not header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.encode(), expected.encode())


async def _read_body(request: Request) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(413)
    raw = b""
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_BODY_BYTES:
            raise HTTPException(413)
    return raw


def _summarize(payload) -> list[str]:
    """Una linea por cambio: object, phone_number_id, tipo y wamid. Sin texto ni telefonos."""
    lines = []
    obj = payload.get("object") if isinstance(payload, dict) else None
    entries = payload.get("entry") if isinstance(payload, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        changes = entry.get("changes") if isinstance(entry, dict) else None
        for change in changes if isinstance(changes, list) else []:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            meta = value.get("metadata")
            pnid = meta.get("phone_number_id") if isinstance(meta, dict) else None
            for kind in ("messages", "statuses"):
                items = value.get(kind)
                for item in items if isinstance(items, list) else []:
                    wamid = item.get("id") if isinstance(item, dict) else None
                    lines.append(f"object={obj} phone_number_id={pnid} tipo={kind} wamid={wamid}")
    return lines or [f"object={obj} sin messages ni statuses"]


@router.post("/webhook", include_in_schema=False)
async def receive(request: Request):
    raw = await _read_body(request)
    if not _valid_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403)
    try:
        payload = json.loads(raw)
        for line in _summarize(payload):
            logger.info("wa webhook: %s", line)
    except Exception:  # payload raro: Meta reintenta ante un 5xx, no queremos eso
        logger.warning("wa webhook: payload no interpretable (%d bytes)", len(raw))
    # TODO fase 1: encolar el mensaje y responder con process_turn (docs/WHATSAPP_PLAN.md).
    return Response(status_code=200)
