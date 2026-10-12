"""Entrega de lo que las apps quieren mandar (contrato v1.1, docs/APPS_PLAN.md): mensajes a terceros
del outbox (herramientas send, ya confirmadas) y avisos de los jobs a los operadores.

APPS_OUTBOX_MODE: simulate (default) no manda nada y lo registra como simulado; whatsapp manda un
texto por el numero del chat del operador. Fuera de la ventana de 24 h Meta rechaza el texto
(131047): para escribirle a alguien que no escribio hacen falta plantillas, que todavia no estan.
"""
import logging
import re

from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..models import App, WaAccount, WaThread
from ..whatsapp import store as wa_store
from ..whatsapp.graph import GraphClient, GraphError
from ..whatsapp.service import recipient
from . import client as app_client
from .registry import token_of

logger = logging.getLogger(__name__)
MAX_PER_CALL = 50


def wa_digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def account_of(s: Session, conversation_id: str | None) -> WaAccount | None:
    thread = s.get(WaThread, conversation_id) if conversation_id else None
    return s.get(WaAccount, thread.account_id) if thread else None


async def send_text(sessions: sessionmaker[Session], account_id: str | None, to: str, text: str,
                    conversation_id: str | None = None) -> dict:
    """{"estado": simulado | enviado | error, "detalle", "wamid"}. Sin numero (chat del dashboard), simula."""
    digits = wa_digits(to)
    if settings.apps_outbox_mode != "whatsapp" or account_id is None:
        return {"estado": "simulado", "detalle": "modo de prueba: no se envió", "wamid": None}
    if len(digits) < 8:
        return {"estado": "error", "detalle": "teléfono inválido", "wamid": None}
    with sessions() as s:
        account = s.get(WaAccount, account_id)
        token, pnid = wa_store.token_for(account), account.phone_number_id
    graph = GraphClient(token, settings.wa_graph_version)
    try:
        response = await graph.send_text(pnid, recipient(digits), text)
        wamid = (response.get("messages") or [{}])[0].get("id")
        estado, detalle = "enviado", None
    except GraphError as e:
        wamid, estado, detalle = None, "error", f"WhatsApp {getattr(e, 'code', '')}: {e}"[:255]
        logger.warning("apps: no se pudo enviar el mensaje de una app (%s)", getattr(e, "code", "?"))
    finally:
        await graph.aclose()
    with sessions() as s:
        wa_store.record_outbound(s, wamid=wamid, account_id=account_id, conversation_id=conversation_id,
                                 wa_id=digits, type="text", status="sent" if wamid else "failed",
                                 error=None if wamid else {"message": detalle})
        s.commit()
    return {"estado": estado, "detalle": detalle, "wamid": wamid}


async def deliver(sessions: sessionmaker[Session], app_id: str, items: list[dict],
                  conversation_id: str | None) -> list[dict]:
    """Entrega el outbox de una herramienta send y le avisa a la app cada resultado
    (POST /outbox/{ref}). Devuelve un resumen para el LLM."""
    with sessions() as s:
        app = s.get(App, app_id)
        base_url, token = app.base_url, token_of(app)
        account = account_of(s, conversation_id)
        account_id = account.id if account else None
    out = []
    for item in items[:MAX_PER_CALL]:
        ref, to, text = str(item.get("ref", "")), str(item.get("to", "")), str(item.get("text", ""))
        result = await send_text(sessions, account_id, to, text, conversation_id)
        try:
            await app_client.post_json(base_url, token, f"/outbox/{ref}", result)
        except app_client.AppError as e:
            logger.warning("apps: la app no registro la entrega %s: %s", ref, e)
        out.append({"ref": ref, "estado": result["estado"], **({"detalle": result["detalle"]} if result["detalle"] else {})})
    return out
