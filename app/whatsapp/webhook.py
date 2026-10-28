"""Webhook de WhatsApp (Meta): challenge GET y eventos POST firmados.

/wa/webhook: nuestra app (WA_APP_SECRET, WA_VERIFY_TOKEN). /wa/webhook/<clave>: la app de Meta propia de un
cliente (cuenta own_app, docs/ARQUITECTURA.md), con su secret y su verify token."""
import hashlib
import hmac
import json
import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.deps import get_db
from ..config import settings
from ..models import WaAccount
from . import own_app
from .service import WhatsAppService, get_service

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


def _challenge(request: Request, token: str | None):
    q = request.query_params
    if (token and q.get("hub.mode") == "subscribe"
            and hmac.compare_digest(q.get("hub.verify_token", "").encode(), token.encode())):
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403)


@router.get("/webhook", include_in_schema=False)
def verify(request: Request):
    return _challenge(request, settings.wa_verify_token)


def _valid_signature(raw: bytes, header: str | None, secret: str | None = None) -> bool:
    secret = settings.wa_app_secret if secret is None else secret
    if not secret or not header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.encode(), expected.encode())


def _own_account(db: Session, key: str) -> WaAccount | None:
    return db.scalar(select(WaAccount).where(WaAccount.webhook_key == key))


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
    """Una linea por mensaje o status (object, phone_number_id, tipo y wamid) y por evento
    de la cuenta (field, event y WABA). Sin texto ni telefonos."""
    lines = []
    obj = payload.get("object") if isinstance(payload, dict) else None
    entries = payload.get("entry") if isinstance(payload, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        changes = entry.get("changes") if isinstance(entry, dict) else None
        for change in changes if isinstance(changes, list) else []:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            field = change.get("field")
            if field and field != "messages":
                lines.append(f"object={obj} field={field} event={value.get('event')} waba={entry.get('id')}")
                continue
            meta = value.get("metadata")
            pnid = meta.get("phone_number_id") if isinstance(meta, dict) else None
            for kind in ("messages", "statuses"):
                items = value.get(kind)
                for item in items if isinstance(items, list) else []:
                    wamid = item.get("id") if isinstance(item, dict) else None
                    lines.append(f"object={obj} phone_number_id={pnid} tipo={kind} wamid={wamid}")
    return lines or [f"object={obj} sin messages ni statuses"]


def _schedule(raw: bytes, service: WhatsAppService, account: WaAccount | None = None) -> Response:
    try:
        payload = json.loads(raw)
        if account is not None:
            payload = own_app.scoped_payload(payload, account)
        for line in _summarize(payload):
            logger.info("wa webhook: %s", line)
    except Exception:  # payload raro
        logger.warning("wa webhook: payload no interpretable (%d bytes)", len(raw))
        return Response(status_code=200)
    try:
        service.handle_payload(payload)
    except Exception:
        logger.exception("wa webhook: no se pudo agendar el payload")
    return Response(status_code=200)


@router.post("/webhook", include_in_schema=False)
async def receive(request: Request, service: Annotated[WhatsAppService, Depends(get_service)]):
    """200 siempre (salvo firma invalida): Meta reintenta ante un 5xx. El turno corre en
    segundo plano (service.handle_payload), sin esperar a la base ni al LLM."""
    raw = await _read_body(request)
    if not _valid_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403)
    return _schedule(raw, service)


@router.get("/webhook/{key}", include_in_schema=False)
def verify_own(key: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    account = _own_account(db, key)
    return _challenge(request, own_app.verify_token_for(account) if account else None)


@router.post("/webhook/{key}", include_in_schema=False)
async def receive_own(key: str, request: Request, db: Annotated[Session, Depends(get_db)],
                      service: Annotated[WhatsAppService, Depends(get_service)]):
    """Como /webhook, firmado con el app secret de esa cuenta, y solo con lo de su WABA y su numero."""
    raw = await _read_body(request)
    account = _own_account(db, key)
    secret = own_app.app_secret_for(account) if account else None
    if not secret or not _valid_signature(raw, request.headers.get("X-Hub-Signature-256"), secret):
        raise HTTPException(403)
    return _schedule(raw, service, account)
