"""Conciliacion de las llamadas activas de la base con las rooms de LiveKit.

Si el worker de voz se cae (o lo reinician) a mitad de una llamada, su shutdown callback no
corre y la fila queda en pendiente/sonando/en_curso: ocupa lugar hasta el tope de duracion
+ margen (services/quota.py) y despues, sin esto, quedaria asi para siempre. Cada
LIVEKIT_RECONCILE_INTERVAL_SECONDS se cierran las activas cuya room ya no existe:

- Las que arrancaron (started_at) quedan finalizadas con ended_reason "room_gone" y una
  duracion best-effort: de started_at al ultimo guardado de la conversacion, sin pasar el
  tope del cliente. Asi el consumo no desaparece ni se infla.
- Las que no arrancaron (pendiente o sonando), fallidas.

Room de cada llamada: las que despacha la app se llaman call-<conversation_id>
(services/calls.py); las entrantes las crea la dispatch rule (anura-<algo>) y el worker les
pone {"conversation_id": ...} en la metadata (room_metadata). Mientras haya una room
entrante sin esa metadata (el worker no llego a marcarla o fallo), no se cierra ninguna
entrante: no se sabe cual es.
"""
import asyncio
import datetime
import json
import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from livekit import api

from ..config import settings
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    CallMode,
    CallRow,
    CallStatus,
    Client,
    ConversationRow,
    effective_max_call_seconds,
)
from .leader import Leader, every

logger = logging.getLogger(__name__)

CALL_ROOM_PREFIX = "call-"
# Una activa mas nueva que esto no se toca: la room puede estar creandose (el commit de
# la fila va antes del despacho a LiveKit) o el worker todavia no marco la entrante.
MIN_AGE_SECONDS = 120
# Una room sin conversation_id mas nueva que esto es una entrante que el worker esta por
# marcar; mas vieja, una que no se pudo marcar.
UNTAGGED_GRACE_SECONDS = 60
ROOM_GONE_REASON = "room_gone"


def room_metadata(conversation_id: str) -> str:
    """Metadata que el worker pone en la room de una entrante."""
    return json.dumps({"conversation_id": conversation_id})


def room_conversation(room) -> str | None:
    """conversation_id de una room de LiveKit (por nombre o por metadata), o None."""
    if room.name.startswith(CALL_ROOM_PREFIX):
        return room.name[len(CALL_ROOM_PREFIX):]
    try:
        value = json.loads(room.metadata or "{}").get("conversation_id")
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def _candidates(s: Session, now: datetime.datetime) -> list[CallRow]:
    old = now - datetime.timedelta(seconds=MIN_AGE_SECONDS)
    return list(s.scalars(select(CallRow).where(
        CallRow.status.in_(ACTIVE_CALL_STATUSES), CallRow.created_at < old)))


def _close(s: Session, conversation_id: str, now: datetime.datetime) -> bool:
    """Cierra la llamada si sigue activa (el worker pudo cerrarla mientras tanto)."""
    call = s.get(CallRow, conversation_id)
    if call is None or call.status not in ACTIVE_CALL_STATUSES:
        return False
    if call.started_at is not None:
        client = s.get(Client, call.client_id) if call.client_id else None
        conv = s.get(ConversationRow, conversation_id)
        last = max(call.started_at, conv.updated_at if conv is not None and conv.updated_at else call.started_at)
        seconds = min(int((min(last, now) - call.started_at).total_seconds()), effective_max_call_seconds(client))
        values = {"status": CallStatus.finalizada, "ended_reason": ROOM_GONE_REASON, "duration_seconds": seconds,
                  "ended_at": call.started_at + datetime.timedelta(seconds=seconds)}
    else:
        values = {"status": CallStatus.fallida, "ended_reason": ROOM_GONE_REASON, "ended_at": now,
                  "error": "La room de LiveKit ya no existe (se cayo el worker antes de empezar)"}
    # Condicional: si el worker la cerro entre el SELECT y aca, gana el worker.
    done = s.execute(update(CallRow).where(CallRow.conversation_id == conversation_id,
                                           CallRow.status.in_(ACTIVE_CALL_STATUSES)).values(**values)).rowcount
    s.commit()
    return bool(done)


def _close_orphans(sessions, live: set[str], inbound_blocked: bool) -> list[str]:
    closed = []
    now = utcnow()
    with sessions() as s:
        orphans = [c.conversation_id for c in _candidates(s, now)
                   if c.conversation_id not in live and not (inbound_blocked and c.mode == CallMode.entrante)]
        for conversation_id in orphans:
            if _close(s, conversation_id, now):
                closed.append(conversation_id)
    return closed


async def reconcile_once(sessions, livekit_api) -> list[str]:
    """Una pasada: cierra las activas sin room y devuelve sus conversation_id.
    livekit_api: un api.LiveKitAPI abierto (o algo con .room.list_rooms). Si LiveKit no
    responde, levanta la excepcion sin tocar nada."""
    rooms = (await livekit_api.room.list_rooms(api.ListRoomsRequest())).rooms
    live: set[str] = set()
    untagged_old = False
    now = datetime.datetime.now(datetime.UTC).timestamp()
    for room in rooms:
        conversation_id = room_conversation(room)
        if conversation_id is not None:
            live.add(conversation_id)
        elif not room.creation_time or now - room.creation_time > UNTAGGED_GRACE_SECONDS:
            untagged_old = True     # sin creation_time: por las dudas, como vieja
    if untagged_old:
        logger.info("conciliacion: hay rooms sin conversation_id; no se cierran entrantes en esta pasada")
    closed = await asyncio.to_thread(_close_orphans, sessions, live, untagged_old)
    for conversation_id in closed:
        logger.warning("llamada %s: activa sin room en LiveKit, cerrada (%s)", conversation_id, ROOM_GONE_REASON)
    return closed


async def reconcile_loop(sessions, livekit_api=None, interval: float | None = None,
                         leader: Leader | None = None) -> None:
    """reconcile_once cada `interval` s (LIVEKIT_RECONCILE_INTERVAL_SECONDS) hasta que se
    cancele, solo en el lider (con leader=None, siempre). Un error (LiveKit o la base) se
    registra y se reintenta en la vuelta siguiente. Sin livekit_api abre uno con
    LIVEKIT_URL/KEY/SECRET en cada pasada, como services/livekit.dispatch_call."""
    async def run():
        if livekit_api is not None:
            await reconcile_once(sessions, livekit_api)
            return
        async with api.LiveKitAPI(url=settings.livekit_url, api_key=settings.livekit_api_key,
                                  api_secret=settings.livekit_api_secret) as lkapi:
            await reconcile_once(sessions, lkapi)

    await every(leader, interval or settings.livekit_reconcile_interval_seconds, run,
                "conciliacion de llamadas con LiveKit")
