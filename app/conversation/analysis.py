"""Cola de la extraccion final de una llamada de voz: el worker la marca al conectar y la corre `app` con
reintentos, para que el cierre de la llamada no dependa de un LLM lento y no se pierda si el proceso muere
(docs/ARQUITECTURA.md, "Analisis (extraccion)").

Estados en conversations.analysis_status:
- NULL: no corresponde (WhatsApp, texto, sin `analysis`, tu propio agente) o es anterior a la cola.
- armed: se armo con la llamada conectada. Si el worker muere, el loop lo toma al vencer next_at.
- pending: listo para correr, desde next_at.
- running: corriendo; si `app` muere, se retoma al vencer el lease, con un intento mas.
- done: los datos quedaron guardados. Final.
- failed: no se pudo correr, se agoto o fallo el modelo (JSON invalido, 400). Final: se puede re-analizar a mano.

Solo se reintenta una falla de transporte (timeout, conexion, 408/429/5xx): 3 intentos, inmediato, 30 s y 5 min.
Reintentar la salida del modelo seria un parche de modelo (AGENTS.md). Con `done` o `failed`, el post-call pasa a
`pending` (workflows.mark_ended): recien ahi ve lo extraido.
"""
import asyncio
import datetime
import logging
from collections.abc import Callable

import anthropic
import httpx
import openai
from sqlalchemy import or_, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import ConversationRow
from . import workflows
from .models import Workflow

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
# Espera tras cada falla de transporte; el tercero da failed.
BACKOFF = (datetime.timedelta(seconds=30), datetime.timedelta(minutes=5))
# La extraccion tardo 54 s con un modelo que razona (medido el 27-nov-2026). RUN_TIMEOUT < RUNNING_LEASE: una
# retoma no pisa a un proceso vivo.
RUN_TIMEOUT = 120.0
RUNNING_LEASE = datetime.timedelta(seconds=180)
BATCH = 20
ACTIVE = ("armed", "pending", "running")


def arm(sessions: sessionmaker[Session], conversation_id: str, workflow: Workflow) -> None:
    """La llamada se conecto: queda `armed` con vencimiento. Si el proceso muere, el loop la corre al vencer. Sin
    `analysis` o con tu propio agente, nada. No lanza: se llama con la persona ya conectada (voice/worker.py)."""
    try:
        if workflow.external is not None or workflow.analysis is None:
            return
        expires = utcnow() + datetime.timedelta(seconds=settings.call_max_duration_seconds
                                                + workflows.ARMED_MARGIN_SECONDS)
        with sessions() as s:
            s.execute(update(ConversationRow)
                      .where(ConversationRow.id == conversation_id, ConversationRow.analysis_status.is_(None))
                      .values(analysis_status="armed", analysis_next_at=expires))
            s.commit()
    except Exception:
        logger.exception("analisis %s: no se pudo armar", conversation_id)


def end(sessions: sessionmaker[Session], conversation_id: str) -> None:
    """La llamada termino: de armed a pending. Sin analisis (o si ya lo tomo el loop), el post-call pasa a pending
    como siempre. No lanza. Tiene que ser la ultima escritura del worker sobre la conversacion: el store reescribe
    fields, messages y progress enteros."""
    try:
        with sessions() as s:
            armed = s.execute(update(ConversationRow)
                              .where(ConversationRow.id == conversation_id,
                                     ConversationRow.analysis_status == "armed")
                              .values(analysis_status="pending", analysis_next_at=utcnow())).rowcount
            s.commit()
    except Exception:
        logger.exception("analisis %s: no se pudo marcar el fin", conversation_id)
        return
    if not armed:
        workflows.mark_ended(sessions, conversation_id)


def is_transient(e: Exception) -> bool:
    """Falla de transporte que se reintenta: timeout, conexion, 408/429/5xx. Un JSON invalido o un 400 del modelo
    no. La conexion de un cliente con su propio agente (BYOK) se cobra igual: ver ARQUITECTURA."""
    if isinstance(e, (TimeoutError, httpx.TransportError, OperationalError)):
        return True
    if isinstance(e, (openai.APIConnectionError, anthropic.APIConnectionError)):
        return True
    status = getattr(e, "status_code", None)
    return status in (408, 429) or (isinstance(status, int) and status >= 500)


def _claim(s: Session, row: ConversationRow, now: datetime.datetime) -> int | None:
    """Reclama la fila tal como se la vio. attempts entra en el WHERE: dos retomas ven el mismo estado y solo una
    gana. Devuelve el intento, o None si la tomo otro."""
    seen = row.analysis_attempts
    claimed = s.execute(update(ConversationRow)
                        .where(ConversationRow.id == row.id, ConversationRow.analysis_status == row.analysis_status,
                               ConversationRow.analysis_attempts == seen)
                        .values(analysis_status="running", analysis_attempts=seen + 1,
                                analysis_next_at=now + RUNNING_LEASE)).rowcount
    return seen + 1 if claimed else None


def _finish(sessions: sessionmaker[Session], conversation_id: str, attempt: int, status: str, *,
            next_at: datetime.datetime | None = None) -> bool:
    """Escribe el resultado solo si la fila sigue en este intento: el de un claim viejo se descarta."""
    with sessions() as s:
        written = s.execute(update(ConversationRow)
                            .where(ConversationRow.id == conversation_id,
                                   ConversationRow.analysis_status == "running",
                                   ConversationRow.analysis_attempts == attempt)
                            .values(analysis_status=status, analysis_next_at=next_at)).rowcount
        s.commit()
    return bool(written)


async def run_analysis(sessions: sessionmaker[Session], engine, conversation_id: str, *,
                       now: Callable[[], datetime.datetime] = utcnow) -> str | None:
    """Un intento. Devuelve el estado que quedo, o None si no le toco correr (otro lo reclamo, ya termino o sin
    analisis). Al terminar en `done` o `failed`, el post-call pasa a pending."""
    with sessions() as s:
        row = s.get(ConversationRow, conversation_id)
        if row is None or row.analysis_status not in ACTIVE:
            return None
        # Antes de su hora no corre: un `running` vigente es de otro proceso y un `pending` puede esperar un
        # reintento.
        if row.analysis_next_at is not None and row.analysis_next_at > now():
            return None
        if row.analysis_attempts >= MAX_ATTEMPTS:
            # Las retomas de `running` tambien cuentan: agotado, no se llama al LLM otra vez.
            written = s.execute(update(ConversationRow)
                                .where(ConversationRow.id == row.id,
                                       ConversationRow.analysis_status == row.analysis_status,
                                       ConversationRow.analysis_attempts == row.analysis_attempts)
                                .values(analysis_status="failed", analysis_next_at=None)).rowcount
            s.commit()
            if not written:
                return None
            logger.warning("analisis %s: sin intentos", conversation_id)
            workflows.mark_ended(sessions, conversation_id)
            return "failed"
        attempt = _claim(s, row, now())
        s.commit()
        if attempt is None:
            return None

    try:
        await engine.run_final_analysis(conversation_id, RUN_TIMEOUT)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        # Cada falla deja el id y el tipo: la extraccion del proceso de la llamada ya no existe.
        logger.warning("analisis %s: fallo el intento %d (%s): %s", conversation_id, attempt, type(e).__name__, e)
        status = "pending" if is_transient(e) and attempt < MAX_ATTEMPTS else "failed"
    else:
        status = "done"

    next_at = now() + BACKOFF[attempt - 1] if status == "pending" else None
    if not _finish(sessions, conversation_id, attempt, status, next_at=next_at):
        return None
    if status != "pending":
        workflows.mark_ended(sessions, conversation_id)
    return status


def due_ids(s: Session, now: datetime.datetime) -> list[str]:
    """Lo que le toca al loop: pending, armed vencido (murio el worker) y running vencido (murio `app`)."""
    return list(s.scalars(select(ConversationRow.id).where(
        ConversationRow.analysis_status.in_(ACTIVE),
        or_(ConversationRow.analysis_next_at <= now, ConversationRow.analysis_next_at.is_(None)))
        .order_by(ConversationRow.analysis_next_at).limit(BATCH)))


async def run_once(sessions: sessionmaker[Session], engine, now: Callable[[], datetime.datetime] = utcnow) -> None:
    with sessions() as s:
        ids = due_ids(s, now())
    # En paralelo: una extraccion lenta no frena a las demas, y una que lanza no rompe el lote.
    results = await asyncio.gather(*[run_analysis(sessions, engine, i, now=now) for i in ids],
                                   return_exceptions=True)
    for conversation_id, result in zip(ids, results):
        if isinstance(result, BaseException):
            logger.error("analisis %s: fallo", conversation_id, exc_info=result)


async def analysis_loop(interval: float | None = None) -> None:
    from ..db import get_sessionmaker
    from ..runtime import get_conversation_engine

    while True:
        await asyncio.sleep(interval or settings.analysis_tick_seconds)
        try:
            await run_once(get_sessionmaker(), get_conversation_engine())
        except Exception:
            logger.exception("analisis: fallo el barrido")
