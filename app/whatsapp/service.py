"""Del webhook al motor y de vuelta (docs/WHATSAPP_PLAN.md, seccion 2).

El webhook responde 200 al instante y deja el payload aca: handle_payload solo
parsea y agenda tareas en el loop de la app. Cada mensaje: dedupe por wamid
(unique de wa_messages, antes de agendar nada), cuenta por phone_number_id,
mensajes seguidos juntados en un turno (debounce), un turno a la vez por contacto
(lock), process_turn, envio por la Graph API y registro de wamids.

Topes: WA_MAX_TURN_CHARS por turno (lo que pase se descarta) y WA_MAX_TURNS por
conversacion (despues abre otra), para no pasar el largo de contexto del LLM.

Fin de una conversacion: el motor trabaja igual que en una llamada, y el equivalente del
corte es cerrar el hilo y llamar a engine.finish (la extraccion final del clasico). Pasa al
cerrarla desde el dashboard, al llegar al tope de turnos y al vencer (WA_SESSION_HOURS sin
mensajes del contacto: sweep, cada SWEEP_SECONDS).

Audios (audio.py): el entrante se baja, se transcribe y entra al turno como texto
marcado como nota de voz; la respuesta sale como nota de voz segun WA_AUDIO_REPLY,
y si falla el TTS, la conversion o el envio, sale en texto.

Eventos de la cuenta (fase 2): account_update (el cliente nos quito el acceso o Meta
dio de baja la WABA: la cuenta queda desconectada; DISABLED_UPDATE segun waba_ban_state),
phone_number_quality_update (limite de envio) y
message_template_status_update (solo log: la UI lista las plantillas en vivo). Un
token de cliente rechazado por Meta (190 o 401) tambien la desconecta y no se reintenta.

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
from ..conversation.models import ConversationState, TurnMedia
from ..conversation.store import ConversationStore
from ..db import utcnow
from ..llm.prompt import VOICE_NOTE_TAG
from ..models import Client, ConversationRow, WaAccount
from . import audio as audio_module
from . import campaigns, store
from .audio import AudioError, AudioTooLong
from .crypto import TokenKeyMissing
from .graph import GraphClient, GraphError, MediaTooLarge

logger = logging.getLogger(__name__)

MESSAGE_TYPES = {"text", "audio", "image", "document", "sticker", "video", "location"}
# Sin respuesta: una reaccion no es un mensaje, y system/unsupported los genera Meta.
SILENT_TYPES = {"reaction", "system", "unsupported", "ephemeral", "request_welcome"}
# Campos de webhook de la cuenta (no traen metadata.phone_number_id): se rutean por WABA.
ACCOUNT_EVENT_FIELDS = {"account_update", "phone_number_quality_update", "message_template_status_update"}
# account_update que dejan la cuenta desconectada: el cliente nos quito el acceso o Meta la dio de baja.
DISCONNECT_EVENTS = {"PARTNER_REMOVED", "PARTNER_APP_UNINSTALLED", "ACCOUNT_OFFBOARDED", "ACCOUNT_DELETED"}
# DISABLED_UPDATE depende de ban_info.waba_ban_state: DISABLE desconecta, REINSTATE reconecta
# lo que desconecto un DISABLE y SCHEDULE_FOR_DISABLE solo avisa (la WABA sigue andando).
DISABLED_REASON = "account_update DISABLED_UPDATE"


def _ban_states(value: dict) -> set[str]:
    """waba_ban_state: en los ejemplos de Meta es un texto; se acepta tambien una lista."""
    state = (value.get("ban_info") or {}).get("waba_ban_state") if isinstance(value.get("ban_info"), dict) else None
    states = state if isinstance(state, list) else [state]
    return {str(x).upper() for x in states if x}


@dataclass
class Item:
    """Un mensaje que espera su turno. voice_note: el texto es la transcripcion de un audio."""
    ts: int             # timestamp de Meta
    text: str
    wamid: str
    voice_note: bool = False


@dataclass
class Inbox:
    """Mensajes de un contacto que esperan su turno."""
    items: list[Item] = field(default_factory=list)
    contact_name: str | None = None
    timer_task: asyncio.Task | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # loop.time() de la ultima respuesta fija, por texto: cinco fotos dan una respuesta,
    # pero una foto no tapa el aviso de un audio que no se escucho.
    fixed_sent_at: dict[str, float] = field(default_factory=dict)
    pending_audio: int = 0      # audios bajandose o transcribiendose: el turno los espera

    def chars(self) -> int:
        return sum(len(item.text) for item in self.items)

    def take(self) -> list[Item]:
        items, self.items = self.items, []
        return items

    def idle(self, now: float, window: float) -> bool:
        return (not self.items and not self.lock.locked() and self.pending_audio == 0
                and (self.timer_task is None or self.timer_task.done())
                and all(now - at >= window for at in self.fixed_sent_at.values()))


@dataclass(frozen=True)
class AccountInfo:
    """Lo que se pasa entre tareas: valores, no objetos ORM (cada tarea abre su sesion)."""
    id: str
    client_id: str
    agent_id: str
    phone_number_id: str
    token: str
    own_token: bool = False     # token del cliente (Embedded Signup): si Meta lo rechaza, se desconecta


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


def _ordered(items: list[Item]) -> list[Item]:
    """En el orden de Meta: cada mensaje llega en su POST y pueden llegar desordenados.
    El timestamp es en segundos; con el mismo, queda el orden de llegada (sort estable)."""
    return sorted(items, key=lambda item: item.ts)


def _size(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
                 max_turn_chars: int = settings.wa_max_turn_chars, max_turns: int = settings.wa_max_turns,
                 audio=None):
        """audio: lo que transcribe y sintetiza (transcribe, synthesize_ogg); por defecto
        app/whatsapp/audio.py, un fake en los tests."""
        self.engine = engine
        self.audio = audio or audio_module
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
                if change.get("field") in ACCOUNT_EVENT_FIELDS:
                    waba_id = str(entry.get("id") or "")
                    self._spawn(self._on_account_event(str(change["field"]), waba_id, value))
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

    def end(self, conversation_id: str) -> None:
        """Fin de una conversacion ya cerrada en la base: lo mismo que el corte de una llamada."""
        self._spawn(self.engine.finish(conversation_id))

    async def sweep(self) -> int:
        """Cierra las conversaciones vencidas y les hace el fin (extraccion final del clasico)."""
        with self.sessions() as s:
            threads = store.expired_threads(s, utcnow(), self.session_hours)
            ended = [t.conversation_id for t in threads]
            for t in threads:
                store.close_thread(s, t)
            s.commit()
        for conversation_id in ended:
            self.end(conversation_id)
        return len(ended)

    async def drain(self) -> None:
        """Espera todas las tareas en curso, incluidas las que agenden otras (tests)."""
        while self._tasks:
            await asyncio.wait(list(self._tasks))
            # Los done callbacks (_done, que las saca de _tasks) corren en una vuelta del loop.
            await asyncio.sleep(0)

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
            try:
                token = store.token_for(account)
            except TokenKeyMissing:
                store.set_inbound(s, [wamid], status="error")
                s.commit()
                logger.error("wa: no se puede descifrar el token de la cuenta (WA_TOKEN_KEY) pnid=%s", pnid)
                return
            info = AccountInfo(account.id, account.client_id, account.agent_id, pnid, token,
                               store.has_own_token(account))

        key = (pnid, wa_id)
        inbox = self._inbox.setdefault(key, Inbox())
        if kind == "audio":
            await self._on_audio(info, wa_id, wamid, msg, contact_name, inbox)
            return
        if text is None:
            body = None if kind in SILENT_TYPES else settings.wa_unsupported_reply
            await self._fixed_reply(info, wa_id, wamid, body, inbox)
            return
        if campaigns.is_optout_text(text) and self._optout(info, wa_id):
            await self._fixed_reply(info, wa_id, wamid, settings.wa_optout_reply, inbox)
            return
        if self._over_cap(info, wamid, inbox):
            return
        inbox.items.append(Item(_stamp(msg), text, wamid))
        inbox.contact_name = contact_name or inbox.contact_name
        self._arm(info, wa_id, inbox)

    def _over_cap(self, info: AccountInfo, wamid: str, inbox: Inbox) -> bool:
        """Tope por turno: lo que pasa se descarta y el timer no se re-arma (el turno sale)."""
        if inbox.chars() < self.max_turn_chars:
            return False
        with self.sessions() as s:
            store.set_inbound(s, [wamid], status="ignored")
            s.commit()
        logger.info("wa: entrante ignorado (tope de caracteres) pnid=%s wamid=%s", info.phone_number_id, wamid)
        return True

    def _arm(self, info: AccountInfo, wa_id: str, inbox: Inbox) -> None:
        if inbox.timer_task is not None and not inbox.timer_task.done():
            inbox.timer_task.cancel()
        delay = 0 if inbox.chars() >= self.max_turn_chars else self.debounce_seconds
        inbox.timer_task = self._spawn(self._timer(info, wa_id, inbox, delay))

    async def _on_audio(self, info: AccountInfo, wa_id: str, wamid: str, msg: dict,
                        contact_name: str | None, inbox: Inbox) -> None:
        """Baja el audio, lo transcribe y lo suma al turno como nota de voz. Si es muy
        largo, no se entiende o falla el STT o Meta: respuesta fija, sin LLM."""
        if self._over_cap(info, wamid, inbox):
            return
        graph = self._graph(info.token)
        media = msg.get("audio") if isinstance(msg.get("audio"), dict) else {}
        max_bytes = settings.wa_audio_max_bytes
        text, body = "", None
        inbox.pending_audio += 1
        started = time.perf_counter()
        try:
            if not media.get("id"):
                raise GraphError("audio sin media id")
            # Sin phone_number_id: Meta lo usa para exigir que coincida con el numero que
            # *subio* el media, y este lo subio el cliente.
            meta = await graph.get_media(str(media["id"]))
            size = _size(meta.get("file_size"))
            if size is not None and size > max_bytes:
                raise MediaTooLarge(f"media de {size} bytes, tope {max_bytes}")
            if not meta.get("url"):
                raise GraphError("media sin url")
            data = await graph.download_media(str(meta["url"]), max_bytes)
            mime = str(meta.get("mime_type") or media.get("mime_type") or "")
            text = await self.audio.transcribe(data, mime)
            logger.info("wa: audio transcripto pnid=%s wamid=%s bytes=%d chars=%d ms=%d", info.phone_number_id,
                        wamid, len(data), len(text), round((time.perf_counter() - started) * 1000))
        except (AudioTooLong, MediaTooLarge) as e:
            body = settings.wa_audio_too_long_reply
            logger.info("wa: audio demasiado largo pnid=%s wamid=%s (%s)", info.phone_number_id, wamid, e)
        except (AudioError, GraphError) as e:
            if isinstance(e, GraphError):
                self._auth_failed(info, e)     # la respuesta fija igual falla y queda registrada
            body = settings.wa_audio_error_reply
            logger.warning("wa: audio sin transcribir pnid=%s wamid=%s error=%s code=%s", info.phone_number_id,
                           wamid, type(e).__name__, getattr(e, "code", None))
        finally:
            inbox.pending_audio -= 1
        if body is None and not text:
            body = settings.wa_audio_empty_reply
        if body is not None:
            await self._fixed_reply(info, wa_id, wamid, body, inbox)
            if inbox.items:
                self._arm(info, wa_id, inbox)    # un texto que esperaba a este audio
            return
        inbox.items.append(Item(_stamp(msg), text, wamid, voice_note=True))
        inbox.contact_name = contact_name or inbox.contact_name
        self._arm(info, wa_id, inbox)

    def _optout(self, info: AccountInfo, wa_id: str) -> bool:
        """Baja pedida en respuesta a una campaña: solo si este numero le mando alguna y no hay
        una conversacion en curso (ahi un "no gracias" es parte de la charla y responde el agente)."""
        with self.sessions() as s:
            if store.active_thread(s, info.id, wa_id, utcnow(), self.session_hours) is not None \
                    or not campaigns.got_campaign(s, info.id, wa_id):
                return False
            campaigns.add_optout(s, info.client_id, wa_id, "keyword")
            s.commit()
        logger.info("wa: baja de campañas pnid=%s", info.phone_number_id)
        return True

    def _why_ignore(self, s: Session, account: WaAccount | None, wa_id: str) -> str | None:
        if account is None:
            return "phone_number_id sin cuenta"
        if not account.active:
            return "cuenta inactiva"
        if account.status == "disconnected":
            return "cuenta desconectada"
        client = s.get(Client, account.client_id)
        if client is None or not client.active:
            # TODO: consumo por mensajes del tier (a definir en el plan); hoy solo se exige cliente activo.
            return "cliente inactivo"
        last = store.last_thread(s, account.id, wa_id)
        if last is not None and last.paused:
            return "conversacion pausada"
        return None

    async def _fixed_reply(self, info: AccountInfo, wa_id: str, wamid: str, body: str | None,
                           inbox: Inbox) -> None:
        """Imagen, audio que no se pudo transcribir, etc.: respuesta fija en texto, sin LLM,
        una por texto y ventana de debounce (body None: ninguna, ej. una reaccion). No entra en
        conversations.messages (escribir fuera del motor romperia el undo del turno)."""
        graph = self._graph(info.token)
        now = asyncio.get_running_loop().time()
        # Se decide antes de cualquier await: cinco fotos juntas dan una sola respuesta.
        last = inbox.fixed_sent_at.get(body) if body is not None else None
        reply = body is not None and (last is None or now - last >= self.debounce_seconds)
        if reply:
            inbox.fixed_sent_at[body] = now
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
        sent = await self._send(graph, info, wa_id, conversation_id, body)
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
        if inbox.pending_audio:
            return      # el audio que termine re-arma el timer: el turno sale con el audio
        # El turno va en otra tarea: re-armar el timer cancela solo la espera, nunca un turno en curso.
        self._spawn(self._flush(info, wa_id, inbox))

    async def _flush(self, info: AccountInfo, wa_id: str, inbox: Inbox) -> None:
        async with inbox.lock:
            if inbox.items:
                await self._turn(info, wa_id, inbox, _ordered(inbox.take()))
        key = (info.phone_number_id, wa_id)
        if self._inbox.get(key) is inbox and inbox.idle(asyncio.get_running_loop().time(), self.debounce_seconds):
            del self._inbox[key]

    def _text(self, items: list[Item]) -> str:
        """Si el turno mezcla texto escrito y audios, cada transcripcion lleva VOICE_NOTE_TAG
        en su linea: lo escrito no se trata como posible error de reconocimiento."""
        mixed = len({item.voice_note for item in items}) > 1
        return "\n".join(f"{VOICE_NOTE_TAG} {item.text}" if mixed and item.voice_note else item.text
                         for item in items)[:self.max_turn_chars]

    @staticmethod
    def _media(items: list[Item]) -> TurnMedia:
        """Modalidad del turno. user_voice_note: todo el mensaje es transcripcion (si se
        mezcla con texto, la marca va por linea en _text). La respuesta sale como nota de
        voz en mirror si hubo algun audio."""
        heard = any(item.voice_note for item in items)
        mode = settings.wa_audio_reply
        return TurnMedia(user_voice_note=bool(items) and all(item.voice_note for item in items),
                         reply_voice_note=mode == "always" or (mode == "mirror" and heard))

    def _full(self, s: Session, conversation_id: str) -> bool:
        row = s.get(ConversationRow, conversation_id)
        return row is not None and len(row.messages or []) >= 2 * self.max_turns

    async def _turn(self, info: AccountInfo, wa_id: str, inbox: Inbox, items: list[Item]) -> None:
        wamids = [item.wamid for item in items]
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
            ended = None
            if thread is None and (last := store.last_thread(s, info.id, wa_id)) and last.closed_at is None:
                # Vencida o en el tope y sin cerrar todavia: termina ahora, como un corte.
                store.close_thread(s, last)
                ended = last.conversation_id
            if thread is not None:
                conversation_id = thread.conversation_id
                store.touch_thread(s, conversation_id, now)
            else:
                # El cliente escribe primero: sin apertura, su mensaje es el turno 1. Si responde a
                # una campaña, la apertura es la plantilla que recibio, con el agente de la campaña.
                target = campaigns.reply_target(s, info.id, wa_id, now)
                try:
                    state = self._new_conversation(s, info, target)
                except KeyError:
                    store.set_inbound(s, wamids, status="ignored")
                    s.commit()
                    logger.warning("wa: el agente de la cuenta no existe o esta archivado pnid=%s",
                                   info.phone_number_id)
                    if ended:
                        self.end(ended)
                    return
                conversation_id = state.conversation_id
                # Conversacion e hilo en la misma transaccion.
                ConversationStore.add(s, state)
                store.add_thread(s, conversation_id=conversation_id, account=account, wa_id=wa_id,
                                 contact_name=inbox.contact_name)
                if target is not None:
                    campaigns.mark_replied(s, target.recipient_id, conversation_id, now)
            store.set_inbound(s, wamids, status="received", conversation_id=conversation_id)
            s.commit()
        if ended:
            self.end(ended)

        graph = self._graph(info.token)
        await self._mark_read(graph, info, wamids[-1])
        try:
            media = self._media(items)
            state, turn = await self.engine.process_turn(conversation_id, self._text(items), media=media)
            if inbox.items:
                # Llegaron mas mientras respondia el LLM: la respuesta no salio, se rehace
                # el turno con todo (una sola vez; lo que llegue despues va en el siguiente).
                self.engine.retract_last_turn(conversation_id)
                items = _ordered(items + inbox.take())
                wamids = [item.wamid for item in items]
                with self.sessions() as s:
                    store.set_inbound(s, wamids, status="received", conversation_id=conversation_id)
                    s.commit()
                await self._mark_read(graph, info, wamids[-1])
                media = self._media(items)
                state, turn = await self.engine.process_turn(conversation_id, self._text(items), media=media)
        except Exception:
            logger.exception("wa: fallo el turno pnid=%s wamid=%s", info.phone_number_id, wamids[-1])
            with self.sessions() as s:
                store.set_inbound(s, wamids, status="error")
                s.commit()
            return

        reply = turn.assistant_message.strip()[:settings.wa_max_reply_chars]
        sent = True
        if reply and media.reply_voice_note and len(reply) <= settings.wa_audio_max_reply_chars:
            sent = await self._send_audio(graph, info, wa_id, state, reply)
            if sent:
                self.engine.mark_voice_note(conversation_id)
            else:
                # Fallback: la misma respuesta en texto (puede quedar con numeros en palabras).
                sent = await self._send(graph, info, wa_id, conversation_id, reply)
        elif reply:
            sent = await self._send(graph, info, wa_id, conversation_id, reply)
        with self.sessions() as s:
            store.set_inbound(s, wamids, status="answered" if sent else "error")
            s.commit()

    def _new_conversation(self, s: Session, info: AccountInfo,
                          target: campaigns.ReplyTarget | None) -> ConversationState:
        """KeyError si el agente no existe o esta archivado. El de la campaña archivado: el del numero."""
        if target is not None and target.agent_id:
            try:
                return self.engine.new_conversation(target.agent_id, info.client_id, session=s, channel="whatsapp",
                                                    opening=target.opening)[0]
            except KeyError:
                logger.warning("wa: el agente de la campaña %s esta archivado: responde el del numero",
                               target.campaign_id)
        opening = target.opening if target is not None else False
        return self.engine.new_conversation(info.agent_id, info.client_id, session=s, channel="whatsapp",
                                            opening=opening)[0]

    def _auth_failed(self, info: AccountInfo, e: GraphError) -> bool:
        """Meta rechazo el token (190 o 401). Si es del cliente, la cuenta queda desconectada
        (los mensajes siguientes se ignoran); si es el global, solo se loguea. True si es
        un error de autenticacion."""
        if not e.is_auth_error:
            return False
        if not info.own_token:
            logger.error("wa: el token global (WA_ACCESS_TOKEN) fue rechazado pnid=%s code=%s",
                         info.phone_number_id, e.code)
            return True
        with self.sessions() as s:
            account = s.get(WaAccount, info.id)
            if account is not None and account.status != "disconnected":
                store.mark_status(s, account, "disconnected", f"token_invalid code={e.code}")
                s.commit()
                logger.warning("wa: cuenta desconectada (token rechazado) pnid=%s code=%s",
                               info.phone_number_id, e.code)
        return True

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
            self._auth_failed(info, e)
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

    async def _send_audio(self, graph: GraphClient, info: AccountInfo, wa_id: str,
                          state: ConversationState, body: str) -> bool:
        """Sintetiza la respuesta, la sube y la manda como nota de voz. False si algo falla
        (el que llama la manda en texto). Un fallo del TTS no llego a Meta: solo se loguea;
        uno de la subida o el envio queda como fila audio failed."""
        pnid, conversation_id = info.phone_number_id, state.conversation_id
        started = time.perf_counter()
        try:
            voice = audio_module.pick_voice(self.engine.workflow(state).agent.voice)
            ogg = await self.audio.synthesize_ogg(body, voice)
        except (AudioError, KeyError) as e:
            logger.warning("wa: nota de voz sin sintetizar, va en texto pnid=%s conversation=%s error=%s",
                           pnid, conversation_id, type(e).__name__)
            return False
        tts_ms = round((time.perf_counter() - started) * 1000)
        try:
            media_id = await graph.upload_media(pnid, ogg)
            data = await graph.send_audio(pnid, recipient(wa_id), media_id, voice=settings.wa_audio_voice_flag)
        except GraphError as e:
            logger.warning("wa: nota de voz no enviada, va en texto pnid=%s code=%s subcode=%s",
                           pnid, e.code, e.subcode)
            self._auth_failed(info, e)
            with self.sessions() as s:
                store.record_outbound(s, wamid=None, account_id=info.id, conversation_id=conversation_id,
                                      wa_id=wa_id, type="audio", status="failed",
                                      error={"code": e.code, "subcode": e.subcode, "message": e.message})
                s.commit()
            return False
        messages = data.get("messages")
        out_wamid = messages[0].get("id") if isinstance(messages, list) and messages else None
        with self.sessions() as s:
            store.record_outbound(s, wamid=out_wamid, account_id=info.id, conversation_id=conversation_id,
                                  wa_id=wa_id, type="audio", status="sent")
            s.commit()
        logger.info("wa: nota de voz enviada pnid=%s bytes=%d tts_ms=%d total_ms=%d", pnid, len(ogg), tts_ms,
                    round((time.perf_counter() - started) * 1000))
        return True

    # --- Eventos de la cuenta ---

    async def _on_account_event(self, field: str, waba_id: str, value: dict) -> None:
        event = str(value.get("event") or "")
        if field == "account_update":
            waba_id = str((value.get("waba_info") or {}).get("waba_id") or waba_id)
            with self.sessions() as s:
                accounts = store.accounts_by_waba(s, waba_id) if waba_id else []
                if event in DISCONNECT_EVENTS:
                    for account in accounts:
                        store.mark_status(s, account, "disconnected", f"account_update {event}")
                elif event == "DISABLED_UPDATE":
                    states = _ban_states(value)
                    for account in accounts:
                        if "DISABLE" in states:
                            store.mark_status(s, account, "disconnected", DISABLED_REASON)
                        elif "REINSTATE" in states and account.status == "disconnected" \
                                and account.status_reason == DISABLED_REASON:
                            store.mark_status(s, account, "connected")
                    logger.warning("wa: DISABLED_UPDATE waba=%s waba_ban_state=%s", waba_id, sorted(states))
                s.commit()
            logger.info("wa: account_update event=%s waba=%s cuentas=%d", event, waba_id, len(accounts))
        elif field == "phone_number_quality_update":
            number = store.digits(value.get("display_phone_number"))
            limit = value.get("current_limit")
            matched = 0
            with self.sessions() as s:
                for account in store.accounts_by_waba(s, waba_id) if waba_id and number else []:
                    if store.digits(account.display_phone_number) == number:
                        matched += 1
                        if limit:
                            account.messaging_limit = str(limit)[:32]
                s.commit()
            logger.info("wa: phone_number_quality_update event=%s waba=%s limit=%s cuentas=%d", event, waba_id,
                        limit, matched)
        else:   # message_template_status_update: la UI lista las plantillas en vivo
            logger.info("wa: message_template_status_update event=%s waba=%s template=%s name=%s reason=%s",
                        event, waba_id, value.get("message_template_id"), value.get("message_template_name"),
                        value.get("reason"))

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


SWEEP_SECONDS = 300


async def sweep_loop(interval: float = SWEEP_SECONDS) -> None:
    """Corre en la app (lifespan): termina las conversaciones de WhatsApp vencidas."""
    while True:
        await asyncio.sleep(interval)
        try:
            if n := await (await get_service()).sweep():
                logger.info("wa: %d conversaciones vencidas terminadas", n)
        except Exception:
            logger.exception("wa: fallo el barrido de conversaciones vencidas")
