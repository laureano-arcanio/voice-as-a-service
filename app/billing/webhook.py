"""Webhook de Mercado Pago para las suscripciones: POST firmado (x-signature) con el id del recurso.

Nunca se confia en el cuerpo: se responde 200 y se vuelve a pedir el recurso a MP (`service.sync`).
Topicos: subscription_preapproval (la suscripcion), subscription_authorized_payment (una cuota) y
payment (el pago de una cuota). Lo que no es de una suscripcion nuestra se ignora.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..db import get_sessionmaker
from ..mail import notify
from ..services.errors import ServiceError
from . import mp, service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mp/billing", tags=["billing"])
MAX_BODY_BYTES = 64 * 1024
_tasks: set[asyncio.Task] = set()


def install_logging() -> None:
    """Como app.whatsapp: sin handler propio, los info de app.billing se pierden."""
    log = logging.getLogger("app.billing")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
        log.addHandler(handler)
    log.setLevel(logging.INFO)


def _preapproval_id(topic: str, data_id: str) -> str | None:
    api = service.mp_client()
    if topic in ("subscription_preapproval", "preapproval"):
        return data_id
    if topic == "subscription_authorized_payment":
        return api.authorized_payment(data_id).get("preapproval_id")
    if topic == "payment":
        data = (api.payment(data_id).get("point_of_interaction") or {}).get("transaction_data") or {}
        return data.get("subscription_id")
    return None


def process(topic: str, data_id: str) -> None:
    try:
        preapproval_id = _preapproval_id(topic, data_id)
        if not preapproval_id:
            return
        with get_sessionmaker()() as s:
            sub = service.by_preapproval(s, preapproval_id)
            if sub is None:
                logger.info("mp webhook: %s %s no es de una suscripcion nuestra", topic, data_id)
                return
            mails = service.sync(s, sub)
            s.commit()
        notify.deliver(mails)
    except ServiceError as e:
        logger.warning("mp webhook: %s %s: %s", topic, data_id, e.message)
    except Exception:
        logger.exception("mp webhook: fallo procesando %s %s", topic, data_id)


@router.post("/webhook", include_in_schema=False)
async def webhook(request: Request):
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(413)
    raw = await request.body()
    try:
        body = json.loads(raw) if raw else {}
    except ValueError:
        body = {}
    q = request.query_params
    data_id = str(q.get("data.id") or (body.get("data") or {}).get("id") or q.get("id") or "")
    topic = str(q.get("type") or body.get("type") or q.get("topic") or body.get("topic") or "")
    if not mp.valid_signature(request.headers.get("x-signature"), request.headers.get("x-request-id"),
                              data_id or None):
        logger.warning("mp webhook: firma invalida (%s %s)", topic, data_id)
        raise HTTPException(401)
    if data_id and topic:
        # MP espera la respuesta en pocos segundos; lo demas va aparte.
        task = asyncio.create_task(asyncio.to_thread(process, topic, data_id))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    return Response(status_code=200)
