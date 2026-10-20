"""Resumen por email despues de cada llamada, para el cliente.

- Lo prende cada agente (`Workflow.call_summary_email`) y el cliente lo apaga para todos sus agentes
  desde Mi cuenta (`clients.call_emails`). Destinos: `clients.call_emails_to`; vacio, sus usuarios activos.
- El worker (app/voice/worker.py) deja la llamada `pending` al terminar (`mark_pending`): llamadas
  entrantes, salientes sueltas y por el link, que llegaron a conectarse. Las de campaña no (tienen su
  reporte y su webhook), ni las de prueba o el loadtest.
- Un loop de `app` (main.py) las manda por Resend, con la sesion de la base afuera del envio. El
  interruptor del cliente y los destinos se miran al enviar. Si Resend falla, reintenta con espera
  (BACKOFF); la Idempotency-Key por llamada y destino evita el duplicado a quien ya le llego.
"""
import asyncio
import dataclasses
import datetime
import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..agents.definitions import DefinitionSource
from ..config import settings
from ..conversation.models import Workflow
from ..db import utcnow
from ..models import Agent, CallMode, CallRow, CallStatus, Client, ConversationRow, PhoneNumber, Role, User
from . import messages
from .sender import Mail, send

logger = logging.getLogger(__name__)

MODES = (CallMode.entrante, CallMode.saliente, CallMode.web)
# Espera desde el fin de la llamada para cada intento (el primero, ya).
BACKOFF = (datetime.timedelta(0), datetime.timedelta(minutes=1), datetime.timedelta(minutes=10),
           datetime.timedelta(hours=1))
BATCH = 50


def mark_pending(s: Session, call: CallRow, workflow: Workflow, connected: bool) -> None:
    """Al terminar la llamada (worker): la deja para el loop si el agente lo tiene prendido."""
    if (workflow.call_summary_email and connected and call.status == CallStatus.finalizada
            and call.mode in MODES and call.campaign_contact_id is None and call.client_id is not None):
        call.summary_email = "pending"


def recipients(s: Session, client: Client) -> list[str]:
    if client.call_emails_to:
        return list(client.call_emails_to)
    return list(s.scalars(select(User.email).where(User.client_id == client.id, User.role == Role.client,
                                                   User.active.is_(True)).order_by(User.email)))


def _value(value: object) -> str:
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def build(s: Session, definitions: DefinitionSource, call: CallRow, client: Client) -> Mail | None:
    """El mail, sin destino (`to` vacio). None si la conversacion ya no esta."""
    from ..services.reports import Reports

    conv = s.get(ConversationRow, call.conversation_id)
    if conv is None:
        return None
    reports = Reports(s, definitions)
    workflow = reports.workflow(conv)
    outcome = reports.outcome(workflow, conv)
    agent = s.get(Agent, conv.agent_id) if conv.agent_id else None
    number = s.get(PhoneNumber, call.phone_number_id) if call.phone_number_id else None
    specs = sorted(workflow.fields.items(), key=lambda kv: kv[1].priority) if workflow else []
    # El telefono: el de la llamada o, en las del link (sin numero), el que dio la persona (dato tipo phone).
    phone = call.phone or next((conv.fields[name] for name, spec in specs
                                if spec.type == "phone" and conv.fields.get(name)), None)
    fields = [(spec.label or spec.description.strip(), _value(conv.fields[name]))
              for name, spec in specs if conv.fields.get(name) is not None
              and not (spec.type == "phone" and conv.fields[name] == phone)]
    speaker = workflow.agent.name if workflow else "Agente"
    transcript, used, truncated = [], 0, False
    for m in conv.messages:
        text = (m.get("text") or "").strip()
        if not text:
            continue
        if used + len(text) > settings.call_summary_transcript_chars:
            truncated = True
            break
        used += len(text)
        transcript.append((speaker if m.get("role") == "assistant" else "Contacto", text))
    return messages.call_summary(
        to="", client_name=client.name, agent_name=agent.name if agent else speaker, mode=call.mode,
        phone=phone, client_number=number.e164 if number else None,
        started_at=call.started_at or call.created_at, duration_seconds=call.duration_seconds,
        outcome=outcome.label if outcome else None, fields=fields, transcript=transcript, truncated=truncated,
        call_url=f"{settings.app_url.rstrip('/')}/calls/{conv.id}")


def due(call: CallRow, now: datetime.datetime) -> bool:
    wait = BACKOFF[min(call.summary_email_attempts, len(BACKOFF) - 1)]
    return now >= (call.ended_at or call.created_at) + wait


def prepare(s: Session, definitions: DefinitionSource, call: CallRow) -> tuple[Mail | None, list[str]]:
    """El mail y sus destinos; (None, []) si no corresponde (apagado en el cliente, sin destinos)."""
    client = s.get(Client, call.client_id)
    to = recipients(s, client) if client is not None and client.active and client.call_emails else []
    mail = build(s, definitions, call, client) if to else None
    return mail, (to if mail else [])


def record(call: CallRow, statuses: set[str], recipients_count: int) -> None:
    """Resultado de un intento (los estados de cada destino)."""
    if "failed" in statuses:
        call.summary_email_attempts += 1
        if call.summary_email_attempts >= len(BACKOFF):
            call.summary_email = "failed"
            logger.warning("resumen de la llamada %s: no se pudo enviar", call.conversation_id)
        return
    call.summary_email = "disabled" if statuses == {"disabled"} else "sent"
    if call.summary_email == "sent":
        logger.info("resumen de la llamada %s enviado a %d destinos", call.conversation_id, recipients_count)


def run_once(sessions: sessionmaker[Session], definitions: DefinitionSource,
             now: Callable[[], datetime.datetime] = utcnow) -> None:
    with sessions() as s:
        ids = list(s.scalars(select(CallRow.conversation_id).where(CallRow.summary_email == "pending")
                             .order_by(CallRow.ended_at).limit(BATCH)))
    for conversation_id in ids:
        with sessions() as s:
            call = s.get(CallRow, conversation_id)
            if call is None or call.summary_email != "pending" or not due(call, now()):
                continue
            mail, to = prepare(s, definitions, call)
            if mail is None:
                call.summary_email = "skipped"
                s.commit()
                continue
        # El envio, sin la sesion abierta (Resend puede tardar hasta su timeout por destino).
        statuses = {send(dataclasses.replace(mail, to=address),
                         idempotency_key=f"call-summary/{conversation_id}/{address}").status for address in to}
        with sessions() as s:
            record(s.get(CallRow, conversation_id), statuses, len(to))
            s.commit()


async def call_summary_loop(interval: float | None = None) -> None:
    from ..db import get_sessionmaker
    from ..runtime import get_conversation_engine

    while True:
        await asyncio.sleep(interval or settings.call_summary_tick_seconds)
        try:
            await asyncio.to_thread(run_once, get_sessionmaker(), get_conversation_engine().definitions)
        except Exception:
            logger.exception("resumen de llamadas: fallo el barrido")
