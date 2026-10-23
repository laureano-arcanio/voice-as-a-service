"""Google Calendar: un evento por recordatorio o reunion, en el calendario CRM_GCAL_CALENDAR_ID.

Auth con la cuenta de servicio de GA (ga.service_token). El calendario se comparte con ella con "Hacer
cambios en los eventos". Sin Google Workspace no puede invitar a otros: el evento es solo para el usuario,
con los avisos por evento (popup a la hora en los recordatorios, 30 min antes en las reuniones).
Cada cambio deja el recordatorio en gcal_state=pending; se sube enseguida desde la ruta y, si falla, lo
reintenta gcal_loop.
"""
import asyncio
import datetime
import logging
import time
import zoneinfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_sessionmaker
from ..models import Reminder
from . import ga

logger = logging.getLogger(__name__)
SCOPE = "https://www.googleapis.com/auth/calendar.events"
API = "https://www.googleapis.com/calendar/v3"
POPUP_MIN = {"reminder": 0, "meeting": 30}
MARK = {"done": "✓ ", "no_show": "✗ "}
_token_cache: tuple[float, str] | None = None


class GcalError(Exception):
    pass


def configured() -> bool:
    return bool(settings.gcal_calendar_id and (settings.gcal_credentials or settings.ga_credentials))


def _token() -> str:
    global _token_cache
    if _token_cache and time.monotonic() < _token_cache[0]:
        return _token_cache[1]
    try:
        tok = ga.service_token(settings.gcal_credentials or settings.ga_credentials, SCOPE)
    except ga.GaError as e:
        raise GcalError(str(e)) from e
    _token_cache = (time.monotonic() + 3000, tok)
    return tok


def _call(method: str, path: str, body: dict | None = None) -> httpx.Response:
    url = f"{API}/calendars/{settings.gcal_calendar_id}/events{path}"
    return httpx.request(method, url, json=body, headers={"Authorization": f"Bearer {_token()}"}, timeout=20)


def event_body(r: Reminder) -> dict:
    tz = zoneinfo.ZoneInfo(settings.send_timezone)
    start = r.starts_at.replace(tzinfo=datetime.UTC).astimezone(tz)
    lead, person = r.lead, r.person
    lines = [r.notes.strip()] if r.notes.strip() else []
    who = "" if not person else person.name + (f", {person.title}" if person.title else "")
    lines.append(f"Lead: {lead.name}" + (f" ({who})" if who else ""))
    contacts = [c for c in lead.contacts if c.status == "ok" and c.kind in ("phone", "whatsapp", "email")]
    if person:
        contacts.sort(key=lambda c: c.person_id != person.id)
    lines += [f"{c.kind}: {c.value}" for c in contacts[:4]]
    lines.append(f"Ficha en el CRM: {settings.crm_url}/#/leads/{lead.id}")
    body = {
        "summary": MARK.get(r.status, "") + r.title,
        "description": "\n".join(lines),
        "start": {"dateTime": start.isoformat(), "timeZone": settings.send_timezone},
        "end": {"dateTime": (start + datetime.timedelta(minutes=r.duration_min)).isoformat(),
                "timeZone": settings.send_timezone},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": POPUP_MIN[r.kind]}]},
        "extendedProperties": {"private": {"crm_reminder_id": str(r.id)}},
    }
    if r.location:
        body["location"] = r.location
    return body


def _check(resp: httpx.Response, *ok: int) -> httpx.Response:
    if resp.status_code >= 400 and resp.status_code not in ok:
        raise GcalError(f"{resp.status_code} {resp.text[:300]}")
    return resp


def sync(r: Reminder) -> None:
    """Sube el estado del recordatorio al calendario. No lanza: deja gcal_state ok, error u off."""
    if not configured():
        r.gcal_state = "off"
        return
    try:
        if r.status == "canceled":
            if r.gcal_event_id:
                _check(_call("DELETE", f"/{r.gcal_event_id}"), 404, 410)
                r.gcal_event_id = None
        else:
            resp = None
            if r.gcal_event_id:
                resp = _check(_call("PUT", f"/{r.gcal_event_id}", event_body(r)), 404, 410)
            if resp is None or resp.status_code in (404, 410):     # borrado a mano en Calendar: se recrea
                r.gcal_event_id = _check(_call("POST", "", event_body(r))).json()["id"]
        r.gcal_state, r.gcal_error = "ok", None
    except (GcalError, httpx.HTTPError, KeyError, ValueError) as e:
        r.gcal_state, r.gcal_error = "error", str(e)[:500]
        logger.warning("crm: Calendar, recordatorio %s: %s", r.id, e)


def sync_pending(s: Session, limit: int = 50) -> int:
    if not configured():
        return 0
    rs = s.scalars(select(Reminder).where(Reminder.gcal_state.in_(("pending", "error", "off")))
                   .order_by(Reminder.id).limit(limit)).all()
    for r in rs:
        sync(r)
        s.commit()
    return len(rs)


async def gcal_loop() -> None:
    if not configured():
        logger.info("crm: Calendar sin configurar (CRM_GCAL_CALENDAR_ID): los recordatorios quedan en el CRM")
        return
    while True:
        try:
            with get_sessionmaker()() as s:
                await asyncio.to_thread(sync_pending, s)
        except Exception:
            logger.exception("crm: sync de Calendar")
        await asyncio.sleep(settings.gcal_interval_seconds)
