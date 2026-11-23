"""Reportes de una campaña (docs/features/CAMPANAS.md), para los dos canales:

- `stats`: indicadores (tasa de contacto, duracion media, minutos, distribucion de resultados y
  atendidas por hora del dia).
- `report_csv`: una fila por contacto con su resultado, la conversacion y lo que capturo el agente.

Funciones sincronicas con la Session del que llama.
"""
import csv
import datetime
import io
import json
import re
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..conversation import variables
from ..models import CallRow, Campaign, CampaignContact, ConversationRow, WaMessage
from ..whatsapp import campaigns as wa
from . import campaigns as common
from .reports import iso, state_of

REPORT_COLUMNS = ["telefono", "nombre", "vars", "estado", "resultado", "intentos", "ultimo_intento",
                  "duracion_segundos", "campos", "seguimiento", "error", "conversation_id", "link"]
WA_RESULTS = ("sent", "delivered", "read", "replied")


def pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def _hour(dt, tz: ZoneInfo) -> int:
    """Hora local de una fecha UTC naive."""
    return dt.replace(tzinfo=datetime.UTC).astimezone(tz).hour


def _by_hour(events: list[tuple[Any, bool]], tz: ZoneInfo) -> list[dict]:
    """(fecha UTC, si llego a ser atendida o respondida) -> las 24 horas locales."""
    hours = [{"hour": h, "attempts": 0, "reached": 0} for h in range(24)]
    for at, reached in events:
        if at is not None:
            row = hours[_hour(at, tz)]
            row["attempts"] += 1
            row["reached"] += reached
    return hours


def stats(s: Session, c: Campaign) -> dict:
    tz = ZoneInfo(settings.billing_timezone)
    contacts = sum(common.progress(s, [c.id])[c.id].values())
    if c.channel == "voice":
        calls = s.execute(select(CallRow.created_at, CallRow.started_at, CallRow.duration_seconds)
                          .join(CampaignContact, CampaignContact.id == CallRow.campaign_contact_id)
                          .where(CampaignContact.campaign_id == c.id)).all()
        talked = [duration for _, started, duration in calls if started is not None]
        results = common.voice_results(s, [c.id])[c.id]
        attempts, reached = len(calls), len(talked)
        return {
            "campaign_id": c.id, "channel": c.channel, "contacts": contacts, "attempts": attempts,
            "reached": reached, "contact_rate": pct(reached, attempts),
            "avg_duration_seconds": round(sum(talked) / len(talked)) if talked else None,
            "minutes": common.minutes_used(s, c.id), "results": results,
            "by_hour": _by_hour([(created, started is not None) for created, started, _ in calls], tz),
            "timezone": settings.billing_timezone,
        }
    totals = wa.stats(s, [c.id])[c.id]
    sent_rows = s.execute(select(CampaignContact.sent_at, CampaignContact.replied_at)
                          .where(CampaignContact.campaign_id == c.id, CampaignContact.sent_at.is_not(None))).all()
    attempts, reached = totals["sent"], totals["replied"]
    return {
        "campaign_id": c.id, "channel": c.channel, "contacts": contacts, "attempts": attempts, "reached": reached,
        "contact_rate": pct(reached, attempts),
        "avg_duration_seconds": None, "minutes": None, "results": {k: totals[k] for k in WA_RESULTS},
        "by_hour": _by_hour([(sent, replied is not None) for sent, replied in sent_rows], tz),
        "timezone": settings.billing_timezone,
    }


# --- CSV ---

def _cell(value: Any) -> str:
    """Una celda de texto, a salvo de que Excel la tome por formula (=, @, o +/- que no sea un numero o telefono)."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "@", "\t", "\r") or (text[:1] in ("+", "-") and not re.fullmatch(r"[+-]?[\d\s().-]+", text)):
        return "'" + text
    return text


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str) if value else ""


def _error(error: dict | None) -> str:
    if not error:
        return ""
    return str(error.get("message") or _json(error))


def followup_shown(r: CampaignContact) -> str | None:
    """El estado del seguimiento por WhatsApp de un contacto de voz: pending, sent, replied, failed o skipped."""
    if r.followup_status is None:
        return None
    if r.followup_status == "sent" and r.replied_at is not None:
        return "replied"
    return "pending" if r.followup_status == "in_progress" else r.followup_status


def report_rows(s: Session, c: Campaign, contact_ids: list[str] | None = None) -> list[dict]:
    """Una fila por contacto, en orden de carga. `contact_ids`: solo esos (los campaign_contacts), para
    el webhook de un contacto."""
    whatsapp = c.channel == "whatsapp"
    q = (select(CampaignContact, WaMessage.status)
         .outerjoin(WaMessage, WaMessage.wamid == CampaignContact.wamid)
         .where(CampaignContact.campaign_id == c.id)
         .order_by(CampaignContact.created_at, CampaignContact.id))
    if contact_ids is not None:
        q = q.where(CampaignContact.id.in_(contact_ids))
    rows = s.execute(q).all()
    ids = [r.conversation_id for r, _ in rows if r.conversation_id]
    conversations = {conv.id: conv for conv in s.scalars(select(ConversationRow).where(ConversationRow.id.in_(ids)))} if ids else {}
    durations = dict(s.execute(select(CallRow.conversation_id, CallRow.duration_seconds)
                               .where(CallRow.conversation_id.in_(ids))).all()) if ids and not whatsapp else {}
    out = []
    for r, message_status in rows:
        conv = conversations.get(r.conversation_id)
        captured, summary, visible_variables = {}, None, {}
        if conv is not None:
            captured = {k: v for k, v in (conv.fields or {}).items() if v is not None}
            state = state_of(conv)
            summary, visible_variables = state.progress.summary, variables.visible(state)
        out.append({
            "campaign_contact_id": r.id,
            "followup_conversation_id": r.followup_conversation_id,
            "telefono": r.contact.phone, "nombre": r.contact.name,
            "vars": _json({k: v for k, v in (r.vars or {}).items() if k != "params"}),
            "estado": r.status,
            "resultado": wa.shown_result(r, message_status) if whatsapp else r.result,
            "intentos": r.attempts or (1 if r.sent_at else 0),
            "ultimo_intento": iso(r.sent_at if whatsapp else r.last_attempt_at),
            "duracion_segundos": durations.get(r.conversation_id, "") if not whatsapp else "",
            "campos": _json(captured),
            # Del análisis: el resumen y las variables visibles (las ocultas no salen del cliente).
            "summary": summary,
            "variables": visible_variables,
            "seguimiento": followup_shown(r),
            "error": _error(r.error),
            "conversation_id": r.conversation_id,
            "link": f"{settings.app_url.rstrip('/')}/calls/{r.conversation_id}" if r.conversation_id else "",
        })
    return out


def report_csv(s: Session, c: Campaign) -> str:
    """El reporte por contacto como CSV (UTF-8 con BOM, para que Excel respete los acentos)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(REPORT_COLUMNS)
    for row in report_rows(s, c):
        writer.writerow([_cell(row[col]) if col != "telefono" else row[col] for col in REPORT_COLUMNS])
    return "﻿" + buf.getvalue()
