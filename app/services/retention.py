"""Retencion de datos por tier, con override por cliente (effective_retention_days).

Cada RETENTION_SWEEP_INTERVAL_SECONDS, en el lider (services/leader.py), para cada cliente
con dias de retencion:
- Conversaciones sin actividad (updated_at) desde antes del corte: sin mensajes ni datos, el
  progreso solo con el resultado (lo usan las estadisticas) y purged_at. En la misma tanda,
  el telefono del otro lado de su llamada (call_logs.phone) y el numero y nombre del contacto
  de su hilo de WhatsApp quedan enmascarados (***1234: los ultimos 4 digitos, para reconocer
  la fila en el historial). La fila de llamada queda (modo, estado, duracion): es la base del
  consumo y la facturacion.
- WhatsApp: el cuerpo y el numero de los mensajes (wa_messages) de las cuentas del cliente.
- Campañas terminadas o canceladas antes del corte (y fuera de WA_CAMPAIGN_REPLY_DAYS): nombre
  y variables de cada destinatario (params: montos, nombres). El numero del destinatario
  queda: sin el, un "baja" por texto no se reconoce (got_campaign).
Sin dias (NULL en cliente y tier): no se borra nada.

Se conserva siempre: la lista de bajas (wa_optouts: a quien no escribirle), los errores de
Meta (codigos) y las filas de facturacion. De la plataforma (sin cliente): los entrantes de
WhatsApp sin cuenta (pnid desconocido) pierden cuerpo y numero a los RETENTION_ORPHAN_WA_DAYS.

Idempotente: solo toca lo que no esta purgado o enmascarado, en tandas con commit.
Por updated_at y no por created_at: un chat largo que sigue activo no se borra en el medio.
"""
from __future__ import annotations

import asyncio
import datetime
import logging

from sqlalchemy import String, cast, func, literal, null, or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import (
    CallRow,
    Client,
    ConversationRow,
    WaAccount,
    WaCampaign,
    WaCampaignRecipient,
    WaMessage,
    WaThread,
    effective_retention_days,
)
from .leader import Leader, every

logger = logging.getLogger(__name__)

BATCH = 500
MASK = "***"


def _masked(col):
    """***1234 en SQL (SQLite y PostgreSQL): los ultimos 4 caracteres del numero."""
    return literal(MASK, String).concat(func.substr(col, func.length(col) - 3))


def _not_masked(col):
    return ~col.startswith(MASK)


def _purge_conversations(s: Session, client_id: str, before: datetime.datetime, now: datetime.datetime) -> int:
    rows = list(s.scalars(select(ConversationRow).where(
        ConversationRow.client_id == client_id, ConversationRow.purged_at.is_(None),
        ConversationRow.updated_at < before).limit(BATCH)))
    for row in rows:
        outcome = (row.progress or {}).get("outcome") if isinstance(row.progress, dict) else None
        row.messages, row.fields = [], {}
        row.progress = {"outcome": outcome} if outcome else {}
        row.purged_at = now
        # Sube la version (H08): un guardado del motor con la version vieja da conflicto en vez
        # de pisar la purga.
        row.version = ConversationRow.version + 1
    if rows:
        ids = [r.id for r in rows]
        s.execute(update(WaThread).where(WaThread.conversation_id.in_(ids))
                  .values(contact_name=None, wa_id=_masked(WaThread.wa_id)).execution_options(synchronize_session=False))
        s.execute(update(CallRow).where(CallRow.conversation_id.in_(ids), CallRow.phone.is_not(None),
                                        _not_masked(CallRow.phone))
                  .values(phone=_masked(CallRow.phone)).execution_options(synchronize_session=False))
    s.commit()
    return len(rows)


def _purge_campaigns(s: Session, accounts, before: datetime.datetime, now: datetime.datetime) -> int:
    """Nombre y variables de los destinatarios de campañas ya terminadas. No antes de
    WA_CAMPAIGN_REPLY_DAYS: la respuesta del contacto abre la conversacion con la plantilla
    armada con sus params (campaigns.reply_target)."""
    cutoff = min(before, now - datetime.timedelta(days=settings.wa_campaign_reply_days))
    ended = select(WaCampaign.id).where(WaCampaign.account_id.in_(accounts),
                                        WaCampaign.status.in_(("done", "cancelled")),
                                        WaCampaign.finished_at < cutoff)
    # params vacio es '[]' como texto en las dos bases (JSON en SQLite, JSONB en PostgreSQL).
    n = s.execute(update(WaCampaignRecipient).where(
        WaCampaignRecipient.campaign_id.in_(ended),
        or_(WaCampaignRecipient.name.is_not(None), cast(WaCampaignRecipient.params, String) != "[]"))
        .values(name=None, params=[]).execution_options(synchronize_session=False)).rowcount
    s.commit()
    return n


def purge(sessions: sessionmaker[Session], now: datetime.datetime | None = None) -> dict[str, int]:
    """Una pasada sobre todos los clientes. Sincronico (va en un hilo). Devuelve lo borrado."""
    now = now or utcnow()
    totals = {"conversations": 0, "wa_bodies": 0, "campaign_recipients": 0, "wa_orphans": 0}
    with sessions() as s:
        clients = [(c.id, effective_retention_days(c)) for c in s.scalars(select(Client))]
    for client_id, days in clients:
        if not days:
            continue
        before = now - datetime.timedelta(days=days)
        while True:
            with sessions() as s:
                n = _purge_conversations(s, client_id, before, now)
            totals["conversations"] += n
            if n < BATCH:
                break
        with sessions() as s:
            accounts = select(WaAccount.id).where(WaAccount.client_id == client_id)
            totals["wa_bodies"] += s.execute(
                update(WaMessage).where(WaMessage.account_id.in_(accounts), WaMessage.created_at < before,
                                        or_(WaMessage.body.is_not(None), _not_masked(WaMessage.wa_id)))
                .values(body=null(), wa_id=_masked(WaMessage.wa_id))
                .execution_options(synchronize_session=False)).rowcount
            s.commit()
            totals["campaign_recipients"] += _purge_campaigns(s, accounts, before, now)
    with sessions() as s:
        # Entrantes sin cuenta (pnid desconocido): de nadie, con tope de la plataforma.
        before = now - datetime.timedelta(days=settings.retention_orphan_wa_days)
        totals["wa_orphans"] = s.execute(
            update(WaMessage).where(WaMessage.account_id.is_(None), WaMessage.created_at < before,
                                    or_(WaMessage.body.is_not(None), _not_masked(WaMessage.wa_id)))
            .values(body=null(), wa_id=_masked(WaMessage.wa_id))
            .execution_options(synchronize_session=False)).rowcount
        s.commit()
    return totals


async def retention_loop(leader: Leader | None = None, interval: float | None = None) -> None:
    """Corre en la app (lifespan), solo en el lider. La primera pasada, un minuto despues de
    arrancar (no compite con la recuperacion de WhatsApp)."""
    from ..db import get_sessionmaker

    async def run():
        totals = await asyncio.to_thread(purge, get_sessionmaker())
        if any(totals.values()):
            logger.warning("retencion: %d conversaciones anonimizadas, %d mensajes de WhatsApp, %d destinatarios "
                           "de campañas y %d entrantes sin cuenta borrados", totals["conversations"],
                           totals["wa_bodies"], totals["campaign_recipients"], totals["wa_orphans"])

    await every(leader, interval or settings.retention_sweep_interval_seconds, run, "retencion", first_delay=60)
