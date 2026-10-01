"""Del webhook al motor y de vuelta (docs/WHATSAPP_PLAN.md, seccion 2).

El webhook responde 200 al instante y deja el payload aca: handle_payload solo
parsea y agenda tareas en el loop de la app. Cada mensaje: dedupe por wamid
(unique de wa_messages, antes de agendar nada), cuenta por phone_number_id,
mensajes seguidos juntados en un turno (debounce), un turno a la vez por contacto
(lock), process_turn, envio por la Graph API y registro de wamids.

Topes: WA_MAX_TURN_CHARS por turno (lo que pase se descarta) y WA_MAX_TURNS por
conversacion (despues abre otra), para no pasar el largo de contexto del LLM.

Todo en memoria del proceso (inbox, lock, debounce): supone un solo worker de
uvicorn. Si se reinicia `app`, lo pendiente se pierde y esos entrantes quedan
`received` sin respuesta.

Sin texto, telefonos ni tokens en los logs: solo phone_number_id y wamid.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..conversation.store import ConversationStore
from ..db import utcnow
from ..models import Client, ConversationRow, WaAccount
from . import store
from .graph import GraphClient, GraphError

logger = logging.getLogger(__name__)

MESSAGE_TYPES = {"text", "audio", "image", "document", "sticker", "video", "location"}
# Sin respuesta: una reaccion no es un mensaje, y system/unsupported los genera Meta.
SILENT_TYPES = {"reaction", "system", "unsupported", "ephemeral", "request_welcome"}


@dataclass
class Inbox:
    """Mensajes de texto de un contacto que esperan su turno: (timestamp de Meta, texto, wamid)."""
    items: list[tuple[int, str, str]] = field(default_factory=list)
    contact_name: str | None = None
    timer_task: asyncio.Task | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    unsupported_sent_at: float | None = None   # loop.time() de la ultima respuesta fija

    def chars(self) -> int:
        return sum(len(text) for _, text, _ in self.items)

    def take(self) -> list[tuple[int, str, str]]:
        items, self.items = self.items, []
        return items

    def idle(self, now: float, window: float) -> bool:
        return (not self.items and not self.lock.locked()
                and (self.timer_task is None or self.timer_task.done())
                and (self.unsupported_sent_at is None or now - self.unsupported_sent_at >= window))


@dataclass(frozen=True)
class AccountInfo:
    """Lo que se pasa entre tareas: valores, no objetos ORM (cada tarea abre su sesion)."""
    id: str
    client_id: str
    agent_id: str
    phone_number_id: str
    token: str


def recipient(wa_id: str) -> str:
    """Destino para enviar a un wa_id. Los celulares de Argentina llegan como 549 + 10
    dígitos, pero la lista de destinatarios de prueba los tiene sin el 9 y Meta rechaza
    con 131030; sin el 9 Meta los entrega al mismo contacto (probado el 1-oct-2026)."""
    if wa_id.startswith("549") and len(wa_id) == 13 and wa_id.isdigit():
        return "54" + wa_id[3:]
    return wa_id


def _ts(value) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromtimestamp(int(value), datetime.UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _stamp(msg: dict) -> int:
    try:
        return int(msg.get("timestamp"))
    except (TypeError, ValueError):
        return int(time.time())


def _ordered(items: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    """En el orden de Meta: cada mensaje llega en su POST y pueden llegar desordenados.
    El timestamp es en segundos; con el mismo, queda el orden de llegada (sort estable)."""
    return sorted(items, key=lambda item: item[0])


def _text_of(msg: dict) -> str | None:
    """Texto del mensaje: el de un text, o el titulo del boton o la opcion elegida."""
    kind = msg.get("type")
    if kind == "text":
        body = (msg.get("text") or {}).get("body")
    elif kind == "button":
        body = (msg.get("button") or {}).get("text")
    elif kind == "interactive":
        inter = msg.get("interactive") or {}
        body = (inter.get("button_reply") or inter.get("list_reply") or {}).get("title")
    else:
        return None
    return body.strip() if isinstance(body, str) and body.strip() else None


def _error_of(item: dict) -> dict | None:
    errors = item.get("errors")
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return None
    e = errors[0]
    return {"code": e.get("code"), "subcode": (e.get("error_data") or {}).get("subcode"),
            "message": e.get("message") or e.get("title") or ""}


class WhatsAppService:
    def __init__(self, engine: ConversationEngine, sessions: sessionmaker[Session],
                 graph_factory: Callable[[str], GraphClient] | None = None,
                 debounce_seconds: float = settings.wa_debounce_seconds,
                 session_hours: int = settings.wa_session_hours,
                 max_turn_chars: int = settings.wa_max_turn_chars, max_turns: int = settings.wa_max_turns):
        self.engine = engine
        self.sessions = sessions
        self.debounce_seconds = debounce_seconds
        self.session_hours = session_hours
        self.max_turn_chars = max_turn_chars
        self.max_turns = max_turns
        self._graph_factory = graph_factory or (lambda token: GraphClient(token, version=settings.wa_graph_version))
        self._graphs: dict[str, GraphClient] = {}
        self._tasks: set[asyncio.Task] = set()      # referencias: que el GC no junte tareas en curso
        self._inbox: dict[tuple[str, str], Inbox] = {}

    # --- Entrada ---

    def handle_payload(self, payload: dict) -> None:
        """Sincronico y rapido: no toca la base ni la red; agenda una tarea por mensaje y
        status, en el orden del payload."""
        if not isinstance(payload, dict):
            return
        for entry in payload.get("entry") or []:
            for change in (entry.get("changes") or []) if isinstance(entry, dict) else []:
                value = change.get("value") if isinstance(change, dict) else None
                if not isinstance(value, dict):
                    continue
                pnid = str((value.get("metadata") or {}).get("phone_number_id") or "")
                if not pnid:
                    continue
                names = {c.get("wa_id"): (c.get("profile") or {}).get("name")
                         for c in value.get("contacts") or [] if isinstance(c, dict)}
                for msg in value.get("messages") or []:
                    if isinstance(msg, dict) and msg.get("id") and msg.get("from"):
                        self._spawn(self._on_message(pnid, msg, names.get(msg.get("from"))))
                for st in value.get("statuses") or []:
                    if isinstance(st, dict) and st.get("id") and st.get("status"):
                        self._spawn(self._on_status(pnid, st))

    async def drain(self) -> None:
        """Espera todas las tareas en curso, incluidas las que agenden otras (tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def aclose(self) -> None:
        for graph in self._graphs.values():
            await graph.aclose()
        self._graphs.clear()

    def _spawn(self, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._done)
        return task

    def _done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("wa: tarea fallida: %s", type(task.exception()).__name__,
                         exc_info=task.exception())

    def _graph(self, token: str) -> GraphClient:
        if token not in self._graphs:
            self._graphs[token] = self._graph_factory(token)
        return self._graphs[token]

    # --- Mensajes ---

    async def _on_message(self, pnid: str, msg: dict, contact_name: str | None) -> None:
        wamid, wa_id = str(msg["id"]), str(msg["from"])
        kind = msg.get("type") or "other"
        text = _text_of(msg)
        kind_db = "text" if text is not None else (kind if kind in MESSAGE_TYPES else "other")
        with self.sessions() as s:
            account = store.account_by_pnid(s, pnid)
            if not store.record_inbound(s, wamid=wamid, account_id=account.id if account else None,
                                        wa_id=wa_id, type=kind_db, meta_ts=_ts(msg.get("timestamp"))):
                logger.info("wa: wamid repetido, se descarta pnid=%s wamid=%s", pnid, wamid)
                return
            reason = self._why_ignore(s, account, wa_id)
            if reason:
                store.set_inbound(s, [wamid], status="ignored")
                s.commit()
                logger.info("wa: entrante ignorado (%s) pnid=%s wamid=%s", reason, pnid, wamid)
                return
            info = AccountInfo(account.id, account.client_id, account.agent_id, pnid, store.token_for(account))

        key = (pnid, wa_id)
        inbox = self._inbox.setdefault(key, Inbox())
        if text is None:
            await self._unsupported(info, wa_id, wamid, kind, inbox)
            return
        if inbox.chars() >= self.max_turn_chars:
            # Tope por turno: lo que pasa se descarta y el timer no se re-arma (el turno sale).
            with self.sessions() as s:
                store.set_inbound(s, [wamid], status="ignored")
                s.commit()
            logger.info("wa: entrante ignorado (tope de caracteres) pnid=%s wamid=%s", pnid, wamid)
            return
        inbox.items.append((_stamp(msg), text, wamid))
        inbox.contact_name = contact_name or inbox.contact_name
        if inbox.timer_task is not None and not inbox.timer_task.done():
            inbox.timer_task.cancel()
        delay = 0 if inbox.chars() >= self.max_turn_chars else self.debounce_seconds
        inbox.timer_task = self._spawn(self._timer(info, wa_id, inbox, delay))

    def _why_ignore(self, s: Session, account: WaAccount | None, wa_id: str) -> str | None:
        if account is None:
            return "phone_number_id sin cuenta"
        if not account.active:
            return "cuenta inactiva"
        client = s.get(Client, account.client_id)
        if client is None or not client.active:
            # TODO: consumo por mensajes del tier (a definir en el plan); hoy solo se exige cliente activo.
            return "cliente inactivo"
        last = store.last_thread(s, account.id, wa_id)
        if last is not None and last.paused:
            return "conversacion pausada"
        return None

    async def _unsupported(self, info: AccountInfo, wa_id: str, wamid: str, kind: str, inbox: Inbox) -> None:
        """Audio, imagen, etc.: respuesta fija sin LLM, una por ventana de debounce. No entra
        en conversations.messages (escribir fuera del motor romperia el undo del turno)."""
        graph = self._graph(info.token)
        now = asyncio.get_running_loop().time()
        # Se decide antes de cualquier await: cinco fotos juntas dan una sola respuesta.
        reply = kind not in SILENT_TYPES and (inbox.unsupported_sent_at is None
                                              or now - inbox.unsupported_sent_at >= self.debounce_seconds)
        if reply:
            inbox.unsupported_sent_at = now
        await self._mark_read(graph, info, wamid)
        if not reply:
            with self.sessions() as s:
                store.set_inbound(s, [wamid], status="ignored")
                s.commit()
            self._prune(now)
            return
        with self.sessions() as s:
            thread = store.active_thread(s, info.id, wa_id, utcnow(), self.session_hours)
            conversation_id = thread.conversation_id if thread else None
        sent = await self._send(graph, info, wa_id, conversation_id, settings.wa_unsupported_reply)
        with self.sessions() as s:
            store.set_inbound(s, [wamid], status="answered" if sent else "error", conversation_id=conversation_id)
            s.commit()
        self._prune(now)

    def _prune(self, now: float) -> None:
        if len(self._inbox) > 256:
            for key in [k for k, ib in self._inbox.items() if ib.idle(now, self.debounce_seconds)]:
                del self._inbox[key]

    async def _timer(self, info: AccountInfo, wa_id: str, inbox: Inbox, delay: float) -> None:
        await asyncio.sleep(delay)
        # El turno va en otra tarea: re-armar el timer cancela solo la espera, nunca un turno en curso.
        self._spawn(self._flush(info, wa_id, inbox))

    async def _flush(self, info: AccountInfo, wa_id: str, inbox: Inbox) -> None:
        async with inbox.lock:
            if inbox.items:
                await self._turn(info, wa_id, inbox, _ordered(inbox.take()))
        key = (info.phone_number_id, wa_id)
        if self._inbox.get(key) is inbox and inbox.idle(asyncio.get_running_loop().time(), self.debounce_seconds):
            del self._inbox[key]

    def _text(self, items: list[tuple[int, str, str]]) -> str:
        return "\n".join(text for _, text, _ in items)[:self.max_turn_chars]

    def _full(self, s: Session, conversation_id: str) -> bool:
        row = s.get(ConversationRow, conversation_id)
        return row is not None and len(row.messages or []) >= 2 * self.max_turns

    async def _turn(self, info: AccountInfo, wa_id: str, inbox: Inbox, items: list[tuple[int, str, str]]) -> None:
        wamids = [wamid for _, _, wamid in items]
        now = utcnow()
        with self.sessions() as s:
            account = s.get(WaAccount, info.id)
            if account is None or not account.active:     # desactivada mientras esperaba
                store.set_inbound(s, wamids, status="ignored")
                s.commit()
                return
            thread = store.active_thread(s, info.id, wa_id, now, self.session_hours)
            if thread is not None and self._full(s, thread.conversation_id):
                thread = None       # tope de turnos: sigue en otra, como si hubiera vencido
            if thread is not None:
                conversation_id = thread.conversation_id
                store.touch_thread(s, conversation_id, now)
            else:
                # El cliente escribe primero: sin apertura, su mensaje es el turno 1.
                try:
                    state, _ = self.engine.new_conversation(info.agent_id, info.client_id, session=s,
                                                            channel="whatsapp", opening=False)
                except KeyError:
                    store.set_inbound(s, wamids, status="ignored")
                    s.commit()
                    logger.warning("wa: el agente de la cuenta no existe o esta archivado pnid=%s",
                                   info.phone_number_id)
                    return
                conversation_id = state.conversation_id
                # Conversacion e hilo en la misma transaccion.
                ConversationStore.add(s, state)
                store.add_thread(s, conversation_id=conversation_id, account=account, wa_id=wa_id,
                                 contact_name=inbox.contact_name)
            store.set_inbound(s, wamids, status="received", conversation_id=conversation_id)
            s.commit()

        graph = self._graph(info.token)
        await self._mark_read(graph, info, wamids[-1])
        try:
            _, turn = await self.engine.process_turn(conversation_id, self._text(items))
            if inbox.items:
                # Llegaron mas mientras respondia el LLM: la respuesta no salio, se rehace
                # el turno con todo (una sola vez; lo que llegue despues va en el siguiente).
                self.engine.retract_last_turn(conversation_id)
                items = _ordered(items + inbox.take())
                wamids = [wamid for _, _, wamid in items]
                with self.sessions() as s:
                    store.set_inbound(s, wamids, status="received", conversation_id=conversation_id)
                    s.commit()
                await self._mark_read(graph, info, wamids[-1])
                _, turn = await self.engine.process_turn(conversation_id, self._text(items))
        except Exception:
            logger.exception("wa: fallo el turno pnid=%s wamid=%s", info.phone_number_id, wamids[-1])
            with self.sessions() as s:
                store.set_inbound(s, wamids, status="error")
                s.commit()
            return

        reply = turn.assistant_message.strip()[:settings.wa_max_reply_chars]
        sent = await self._send(graph, info, wa_id, conversation_id, reply) if reply else True
        with self.sessions() as s:
            store.set_inbound(s, wamids, status="answered" if sent else "error")
            s.commit()

    async def _mark_read(self, graph: GraphClient, info: AccountInfo, wamid: str) -> None:
        try:
            await graph.mark_read(info.phone_number_id, wamid)
        except GraphError as e:
            logger.warning("wa: mark_read fallo pnid=%s wamid=%s code=%s", info.phone_number_id, wamid, e.code)

    async def _send(self, graph: GraphClient, info: AccountInfo, wa_id: str,
                    conversation_id: str | None, body: str) -> bool:
        """Manda un texto y lo registra. Si Meta lo rechaza (ej. 131047, fuera de la
        ventana de 24 h) se guarda el error y no se reintenta."""
        try:
            data = await graph.send_text(info.phone_number_id, recipient(wa_id), body)
        except GraphError as e:
            logger.warning("wa: envio fallido pnid=%s code=%s subcode=%s", info.phone_number_id, e.code, e.subcode)
            with self.sessions() as s:
                store.record_outbound(s, wamid=None, account_id=info.id, conversation_id=conversation_id,
                                      wa_id=wa_id, type="text", status="failed",
                                      error={"code": e.code, "subcode": e.subcode, "message": e.message})
                s.commit()
            return False
        messages = data.get("messages")
        out_wamid = messages[0].get("id") if isinstance(messages, list) and messages else None
        with self.sessions() as s:
            store.record_outbound(s, wamid=out_wamid, account_id=info.id, conversation_id=conversation_id,
                                  wa_id=wa_id, type="text", status="sent")
            s.commit()
        return True

    # --- Statuses ---

    async def _on_status(self, pnid: str, st: dict) -> None:
        kwargs = {"wamid": str(st["id"]), "status": str(st["status"]), "error": _error_of(st),
                  "meta_ts": _ts(st.get("timestamp")), "wa_id": str(st.get("recipient_id") or "")}
        for attempt in (1, 2):
            with self.sessions() as s:
                account = store.account_by_pnid(s, pnid)
                store.apply_status(s, account_id=account.id if account else None, **kwargs)
                try:
                    s.commit()
                    return
                except IntegrityError:      # otro registro del mismo wamid en el medio: se reintenta como update
                    s.rollback()
        logger.warning("wa: status sin registrar pnid=%s wamid=%s", pnid, kwargs["wamid"])


_service: WhatsAppService | None = None


async def get_service() -> WhatsAppService:
    """Async a proposito: corre en el loop y no en el threadpool, asi dos webhooks
    simultaneos al arrancar no crean dos servicios (cada uno con su inbox y su lock)."""
    global _service
    if _service is None:
        from ..db import get_sessionmaker
        from ..runtime import get_conversation_engine

        _service = WhatsAppService(get_conversation_engine(), get_sessionmaker())
    return _service
