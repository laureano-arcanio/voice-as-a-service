"""Intentos de llamada de las campañas de voz (docs/features/CAMPANAS.md).

Lo usan el dialer (app/campaigns/dialer.py) y el worker de voz (app/voice/worker.py) para cerrar un
intento, asi la logica no vive en el worker:

- Resultado: del error SIP de `create_sip_participant` (`classify_error`) o de la llamada que se atendio.
- Cierre (`close_contact`): el contacto queda `done`, `retry` (otro intento a los `retry_minutes`, si el
  resultado esta en `retry_on` y quedan intentos) o `failed`. `done`: atendio, o terminó sin atender tras
  los reintentos, o la rechazó; `failed`: numero inexistente (`invalid`) o falla tecnica (`failed`).
- Campaña: pasa a `done` cuando no queda nada pendiente, en vuelo ni por reintentar; y se pausa si los
  ultimos N intentos cerrados fallaron (el trunk saliente se perdio tras reiniciar el host, Anura caido).
- Recuperacion: un `in_progress` cuya llamada ya no esta activa (reinicio o caida del worker) vuelve a `retry`.
- Seguimiento: al cerrar el ultimo intento con un resultado de `followup.after`, el contacto queda con
  `followup_status` `pending` y lo manda el sender de WhatsApp (app/whatsapp/sender.py).
- Baja: si el outcome de la conversacion esta marcado `no_contact` (conversation/models.py, Outcome),
  el telefono queda en contact_optouts (canal voice, source outcome): `apply_outcome_optout`.
- Webhook: cada contacto que termina, y la campaña que termina, se encolan (campaign_callbacks.py).

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama.
"""
from __future__ import annotations

import asyncio
import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.definitions import DefinitionSource
from ..config import settings
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    CallRow,
    Campaign,
    CampaignContact,
    ConversationRow,
)
from . import campaign_callbacks as callbacks
from . import campaigns as common
from . import contacts as contacts_service
from .quota import STALE_MARGIN_SECONDS
from .reports import Reports

# Codigo SIP -> resultado (plan, seccion 5). Lo que no esta aca (otro codigo, 5xx) es `failed`.
SIP_RESULTS = {486: "busy", 600: "busy", 408: "no_answer", 480: "no_answer", 487: "no_answer",
               404: "invalid", 484: "invalid", 604: "invalid", 403: "rejected", 603: "rejected"}
# Terminan `failed` (no `done`) cuando no se reintentan: el numero no existe o fallo la telefonia.
FAILED_RESULTS = ("invalid", "failed")


def sip_status(e: BaseException) -> int | None:
    """El codigo SIP del error de LiveKit (TwirpError, metadata `sip_status_code`), si lo trae."""
    raw = (getattr(e, "metadata", None) or {}).get("sip_status_code")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def classify_sip(status: int | None, *, timeout: bool = False) -> str:
    """El resultado de una llamada que no se atendio. `timeout`: el timbre vencio sin respuesta."""
    return "no_answer" if timeout else SIP_RESULTS.get(status, "failed")


def classify_error(e: BaseException) -> tuple[str, int | None]:
    """(resultado, codigo SIP) de lo que levanto `create_sip_participant`. Sin codigo SIP, un
    vencimiento (el `ringing_timeout` o el plazo del pedido) es `no_answer`; el resto, `failed`."""
    status = sip_status(e)
    timeout = status is None and (isinstance(e, asyncio.TimeoutError) or getattr(e, "code", None) == "deadline_exceeded")
    return classify_sip(status, timeout=timeout), status


def _remaining(s: Session, campaign_id: str) -> bool:
    return s.scalar(select(CampaignContact.id).where(
        CampaignContact.campaign_id == campaign_id,
        CampaignContact.status.in_(("pending", "in_progress", "retry"))).limit(1)) is not None


def finish_if_empty(s: Session, campaign: Campaign, now: datetime.datetime | None = None) -> bool:
    """La campaña en curso o pausada a la que no le queda nada pasa a `done`."""
    if campaign.status not in ("running", "paused") or _remaining(s, campaign.id):
        return False
    campaign.status, campaign.finished_at = "done", now or utcnow()
    callbacks.enqueue(s, campaign, "campaign.finished", now=campaign.finished_at)
    s.flush()
    return True


def failure_streak(s: Session, campaign_id: str, n: int) -> bool:
    """Si los ultimos `n` intentos que terminaron (el ultimo de cada contacto) fueron `failed`."""
    results = list(s.scalars(
        select(CampaignContact.result)
        .where(CampaignContact.campaign_id == campaign_id, CampaignContact.last_attempt_at.is_not(None),
               CampaignContact.status.in_(("done", "failed", "retry")), CampaignContact.result.is_not(None))
        .order_by(CampaignContact.last_attempt_at.desc()).limit(n)))
    return len(results) == n and all(r == "failed" for r in results)


def close_contact(s: Session, contact_id: str, result: str, *, error: dict | None = None,
                  conversation_id: str | None = None, now: datetime.datetime | None = None,
                  retry_at: datetime.datetime | None = None, check_streak: bool = True) -> CampaignContact | None:
    """Cierra el intento en vuelo del contacto con ese resultado. None si no estaba `in_progress`
    (ya lo cerro otro: el worker y el dialer pueden coincidir). `retry_at`: reintento en esa fecha
    en vez de a los `retry_minutes` (la recuperacion al arrancar)."""
    r = s.scalar(select(CampaignContact).where(CampaignContact.id == contact_id)
                 .with_for_update(of=CampaignContact))
    if r is None or r.status != "in_progress":
        return None
    c = s.get(Campaign, r.campaign_id)
    now = now or utcnow()
    r.result, r.error = result, error
    if conversation_id:
        r.conversation_id = conversation_id
    retry_on = c.retry_on if c.retry_on is not None else common.DEFAULT_RETRY_ON
    ended = c.status in ("done", "cancelled")      # una llamada en vuelo termino despues de cerrada la campaña: nadie la reintenta
    if result == "answered":
        r.status, r.next_attempt_at = "done", None
    elif not ended and result in retry_on and r.attempts < (c.max_attempts or common.DEFAULT_ATTEMPTS):
        minutes = c.retry_minutes or common.DEFAULT_RETRY_MINUTES
        r.status, r.next_attempt_at = "retry", retry_at or now + datetime.timedelta(minutes=minutes)
    else:
        r.status, r.next_attempt_at = ("failed" if result in FAILED_RESULTS else "done"), None
    if r.status != "retry":     # termino: seguimiento por WhatsApp si toca, y aviso al webhook
        if c.followup and c.status != "cancelled" and result in (c.followup.get("after") or ()):
            r.followup_status = "pending"
        callbacks.enqueue(s, c, "contact.finished", r, now)
    s.flush()
    if finish_if_empty(s, c, now):
        return r
    if (check_streak and result == "failed" and c.status == "running"
            and failure_streak(s, c.id, settings.call_campaign_failure_streak)):
        common.pause(s, c, f"Fallaron los últimos {settings.call_campaign_failure_streak} intentos seguidos: "
                           f"revisá la telefonía (trunk saliente, Anura)")
    return r


def close_attempt(s: Session, conversation_id: str, result: str, *, error: dict | None = None,
                  now: datetime.datetime | None = None) -> CampaignContact | None:
    """Cierra el intento de esa llamada, si es de una campaña (CallRow.campaign_contact_id)."""
    call = s.get(CallRow, conversation_id)
    if call is None or call.campaign_contact_id is None:
        return None
    return close_contact(s, call.campaign_contact_id, result, error=error, conversation_id=conversation_id, now=now)


def recover_in_progress(s: Session, now: datetime.datetime | None = None, grace_seconds: int = 0) -> int:
    """Los contactos `in_progress` de campañas de voz cuya llamada ya no esta activa (se reinicio la
    app o se cayo el worker sin cerrarla) vuelven a `retry`, ya. Si ni siquiera llego a marcar (no hay
    llamada desde el claim), el intento no se cuenta. `grace_seconds`: no toca los reclamados hace
    menos (el dialer los esta marcando). Devuelve cuantos."""
    now = now or utcnow()
    stale = now - datetime.timedelta(seconds=settings.call_max_duration_seconds + STALE_MARGIN_SECONDS)
    q = (select(CampaignContact).join(Campaign, Campaign.id == CampaignContact.campaign_id)
         .where(Campaign.channel == "voice", CampaignContact.status == "in_progress")
         .with_for_update(of=CampaignContact))
    n = 0
    for r in list(s.scalars(q)):
        if grace_seconds and r.last_attempt_at is not None and r.last_attempt_at > now - datetime.timedelta(seconds=grace_seconds):
            continue
        calls = select(CallRow.conversation_id).where(CallRow.campaign_contact_id == r.id)
        if s.scalar(calls.where(CallRow.status.in_(ACTIVE_CALL_STATUSES), CallRow.created_at >= stale).limit(1)):
            continue
        if r.last_attempt_at is None or s.scalar(calls.where(CallRow.created_at >= r.last_attempt_at).limit(1)) is None:
            r.attempts = max(r.attempts - 1, 0)     # el dialer no llego a llamar
        close_contact(s, r.id, "failed", error={"message": "Intento interrumpido: la llamada no terminó de registrarse"},
                      now=now, retry_at=now, check_streak=False)
        n += 1
    return n


def apply_outcome_optout(s: Session, conversation_id: str, definitions: DefinitionSource) -> bool:
    """Si la conversacion de un intento de campaña termino en un outcome `no_contact` (el contacto pidio
    que no lo llamen mas), el telefono queda en la lista de bajas de voz del cliente. True si lo agrego."""
    call = s.get(CallRow, conversation_id)
    conv = s.get(ConversationRow, conversation_id)
    if call is None or call.campaign_contact_id is None or conv is None:
        return False
    reports = Reports(s, definitions)
    outcome = reports.outcome(reports.workflow(conv), conv)
    r = s.get(CampaignContact, call.campaign_contact_id)
    if outcome is None or not outcome.no_contact or r is None:
        return False
    contacts_service.add_optout(s, conv.client_id, r.contact.phone, "voice", "outcome")
    return True


def goal_count(s: Session, campaign_id: str, definitions: DefinitionSource) -> int:
    """Contactos atendidos cuya conversacion (la del ultimo intento) llego al objetivo del agente
    (outcome con `goal`)."""
    reports = Reports(s, definitions)
    q = (select(ConversationRow).join(CampaignContact, CampaignContact.conversation_id == ConversationRow.id)
         .where(CampaignContact.campaign_id == campaign_id, CampaignContact.result == "answered"))
    n = 0
    for conv in s.scalars(q):
        outcome = reports.outcome(reports.workflow(conv), conv)
        n += bool(outcome and outcome.goal)
    return n

