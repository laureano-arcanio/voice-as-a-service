"""Post-call del agente: una herramienta oculta al modelo que corre una vez por conversacion, durable, con el patron
del resumen por email (app/mail/call_summary.py). El worker o WhatsApp marcan en la base y lo ejecuta un loop de `app`:
el worker puede morir con la llamada.

Estados en conversations.post_call_status:
- NULL: no corresponde o todavia no.
- armed: se cumplio la condicion y la llamada sigue. Si el worker muere, el loop lo toma al vencer next_at.
- pending: listo para correr, desde next_at.
- running: corriendo; si `app` muere, se retoma al vencer next_at, con la misma Idempotency-Key.
- done: la herramienta respondio 2xx, diga lo que diga. Final.
- failed: respondio otra cosa, no se pudo ejecutar o se agotaron los reintentos de transporte. Final.

Solo se reintenta una falla de transporte (timeout, conexion, 429, 5xx): 4 intentos en 11 minutos. Si la app del
cliente respondio, nunca se repite.
"""
import asyncio
import datetime
import logging
from collections.abc import Callable

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import CallMode, ConversationRow, WaThread
from ..services import events
from ..tools.conversation import NOT_EXECUTABLE, is_transport, workflow_event_data
from ..tools.runtime import ToolResult
from .models import Workflow

logger = logging.getLogger(__name__)

# Modos sin post-call: pruebas del panel, carga y la llamada de prueba al celular.
NO_POST_CALL_MODES = {CallMode.prueba.value, CallMode.loadtest.value, CallMode.celular.value}
MAX_ATTEMPTS = 4
# Espera tras cada falla de transporte; la cuarta da failed.
BACKOFF = (datetime.timedelta(0), datetime.timedelta(minutes=1), datetime.timedelta(minutes=10))
# Una herramienta tarda hasta 91 s mas su token. RUN_TIMEOUT < RUNNING_LEASE: una retoma no pisa a un proceso vivo.
RUN_TIMEOUT = 150.0
RUNNING_LEASE = datetime.timedelta(seconds=180)
# Por texto, sin aceptacion: lo que puede tardar engine.finish antes de pasar a pending.
TEXT_END_LEASE = datetime.timedelta(seconds=60)
ARMED_MARGIN_SECONDS = 600
BATCH = 50
NOTE_MAX_CHARS = 1000


def _post_call(workflow: Workflow):
    return workflow.workflows.post_call if workflow.workflows else None


def arm(sessions: sessionmaker[Session], conversation_id: str, mode, workflow: Workflow, *,
        only_when: str | None = None) -> None:
    """Se cumplio la condicion, con la llamada en curso. Sin post-call o en un modo sin post-call, nada. only_when:
    solo si el agente tiene esa condicion. No lanza: se llama con la persona ya conectada (voice/handoff.py)."""
    try:
        post_call = _post_call(workflow)
        if post_call is None or getattr(mode, "value", mode) in NO_POST_CALL_MODES:
            return
        if only_when is not None and post_call.when != only_when:
            return
        expires = utcnow() + datetime.timedelta(seconds=settings.call_max_duration_seconds + ARMED_MARGIN_SECONDS)
        with sessions() as s:
            s.execute(update(ConversationRow)
                      .where(ConversationRow.id == conversation_id, ConversationRow.post_call_status.is_(None))
                      .values(post_call_status="armed", post_call_next_at=expires))
            s.commit()
    except Exception:
        logger.exception("post-call %s: no se pudo armar", conversation_id)


def arm_text_end(s: Session, conversation_id: str, workflow: Workflow) -> None:
    """`always` por texto, sin aceptacion: en la transaccion que cierra el hilo y antes de engine.finish. Despues,
    mark_ended lo pasa a pending; si `app` se recrea en esa ventana, lo toma el loop. Sin commit."""
    post_call = _post_call(workflow)
    if post_call is None or post_call.when != "always":
        return
    s.execute(update(ConversationRow)
              .where(ConversationRow.id == conversation_id, ConversationRow.post_call_status.is_(None))
              .values(post_call_status="armed", post_call_next_at=utcnow() + TEXT_END_LEASE))


def mark_ended(sessions: sessionmaker[Session], conversation_id: str) -> None:
    """La conversacion termino y la extraccion ya corrio: de armed a pending. No lanza: si falla, armed vence."""
    try:
        with sessions() as s:
            s.execute(update(ConversationRow)
                      .where(ConversationRow.id == conversation_id, ConversationRow.post_call_status == "armed")
                      .values(post_call_status="pending", post_call_next_at=utcnow()))
            s.commit()
    except Exception:
        logger.exception("post-call %s: no se pudo marcar el fin", conversation_id)


def _note(result: ToolResult, channel: str) -> str | None:
    """La nota para el operador, solo por texto: `operator_message` si es un texto no vacio. Es lo unico que se
    guarda de la respuesta."""
    message = result.data.get("operator_message") if isinstance(result.data, dict) else None
    if channel != "whatsapp" or not isinstance(message, str) or not message.strip():
        return None
    return message.strip()[:NOTE_MAX_CHARS]


def _claim(s: Session, row: ConversationRow, now: datetime.datetime) -> int | None:
    """Reclama la fila tal como se la vio. attempts entra en el WHERE: dos retomas de un mismo `running` ven el mismo
    estado y solo una puede ganar. Devuelve el intento, o None si la tomo otro."""
    seen = row.post_call_attempts
    claimed = s.execute(update(ConversationRow)
                        .where(ConversationRow.id == row.id, ConversationRow.post_call_status == row.post_call_status,
                               ConversationRow.post_call_attempts == seen)
                        .values(post_call_status="running", post_call_attempts=seen + 1,
                                post_call_next_at=now + RUNNING_LEASE)).rowcount
    return seen + 1 if claimed else None


def _finish(sessions: sessionmaker[Session], conversation_id: str, attempt: int, status: str, *,
            next_at: datetime.datetime | None = None, note: str | None = None,
            event: dict | None = None) -> bool:
    """Escribe el resultado solo si la fila sigue en este intento: el de un claim viejo se descarta, sin evento."""
    with sessions() as s:
        row = s.get(ConversationRow, conversation_id)
        written = s.execute(update(ConversationRow)
                            .where(ConversationRow.id == conversation_id, ConversationRow.post_call_status == "running",
                                   ConversationRow.post_call_attempts == attempt)
                            .values(post_call_status=status, post_call_next_at=next_at,
                                    **({"post_call_note": note} if note is not None else {}))).rowcount
        if not written:
            return False
        if event is not None and row is not None and row.client_id:
            events.record(s, row.client_id, "workflow.post_call", conversation_id=conversation_id, **event)
        s.commit()
    return True


async def run_post_call(sessions: sessionmaker[Session], engine, conversation_id: str, *,
                        actor: str | None = None, now: Callable[[], datetime.datetime] = utcnow) -> str | None:
    """Un intento. Devuelve el estado que quedo, o None si no le toco correr (otro lo reclamo, ya terminado o sin
    post-call pendiente). Si algo lanza, la fila queda en `running` hasta que vence y se retoma con el mismo tope."""
    with sessions() as s:
        row = s.get(ConversationRow, conversation_id)
        if row is None or row.post_call_status not in ("armed", "pending", "running"):
            return None
        # Antes de su hora no corre: un `running` vigente es de otro proceso y un `pending` puede esperar un reintento.
        if row.post_call_next_at is not None and row.post_call_next_at > now():
            return None
        if row.post_call_attempts >= MAX_ATTEMPTS:
            # Las retomas de `running` tambien cuentan: agotado, no se ejecuta otra vez.
            failed = s.execute(update(ConversationRow)
                               .where(ConversationRow.id == row.id,
                                      ConversationRow.post_call_status == row.post_call_status,
                                      ConversationRow.post_call_attempts == row.post_call_attempts)
                               .values(post_call_status="failed", post_call_next_at=None)).rowcount
            if failed and row.client_id:
                events.record(s, row.client_id, "workflow.post_call", conversation_id=conversation_id, ok=False,
                              status=None, ms=0, slug="", reason="max_attempts")
            s.commit()
            return "failed" if failed else None
        attempt = _claim(s, row, now())
        s.commit()
        if attempt is None:
            return None
        if actor is None:
            wa_id = s.scalar(select(WaThread.wa_id).where(WaThread.conversation_id == conversation_id))
            actor = f"wa:{wa_id}" if wa_id else None

    try:
        state = engine.store.get(conversation_id)
        workflow = engine.workflow(state)
        post_call = _post_call(workflow)
    except (KeyError, AttributeError):      # sin conversacion o sin la version del agente
        state = post_call = None
    if post_call is None:
        logger.warning("post-call %s: el agente ya no lo tiene", conversation_id)
        event = {"ok": False, "status": None, "ms": 0, "slug": "", "reason": NOT_EXECUTABLE}
        return "failed" if _finish(sessions, conversation_id, attempt, "failed", event=event) else None

    try:
        result = await asyncio.wait_for(
            engine.tools.run_workflow(workflow, state, post_call.tool, actor, "post_call", emit=False), RUN_TIMEOUT)
    except asyncio.TimeoutError:
        result = ToolResult(ok=False, error="timeout", transport=True, ms=round(RUN_TIMEOUT * 1000))
    event = workflow_event_data(post_call.tool, result)

    if result.ok:
        status, next_at = "done", None
        note = _note(result, state.channel)
    elif is_transport(result) and attempt < MAX_ATTEMPTS:
        status, next_at, note = "pending", now() + BACKOFF[attempt - 1], None
    else:
        status, next_at, note = "failed", None, None
    return status if _finish(sessions, conversation_id, attempt, status, next_at=next_at, note=note,
                             event=event) else None


def due_ids(s: Session, now: datetime.datetime) -> list[str]:
    """Lo que le toca al loop: pending, armed vencido (murio el worker) y running vencido (murio `app`)."""
    return list(s.scalars(select(ConversationRow.id).where(
        ConversationRow.post_call_status.in_(("pending", "armed", "running")),
        or_(ConversationRow.post_call_next_at <= now, ConversationRow.post_call_next_at.is_(None)))
        .order_by(ConversationRow.post_call_next_at).limit(BATCH)))


async def run_once(sessions: sessionmaker[Session], engine, now: Callable[[], datetime.datetime] = utcnow) -> None:
    with sessions() as s:
        ids = due_ids(s, now())
    # En paralelo: una herramienta lenta no frena a las demas, y una que lanza no rompe el lote.
    results = await asyncio.gather(*[run_post_call(sessions, engine, i, now=now) for i in ids], return_exceptions=True)
    for conversation_id, result in zip(ids, results):
        if isinstance(result, BaseException):
            logger.error("post-call %s: fallo", conversation_id, exc_info=result)


async def post_call_loop(interval: float | None = None) -> None:
    from ..db import get_sessionmaker
    from ..runtime import get_conversation_engine

    while True:
        await asyncio.sleep(interval or settings.workflow_tick_seconds)
        try:
            await run_once(get_sessionmaker(), get_conversation_engine())
        except Exception:
            logger.exception("post-call: fallo el barrido")
