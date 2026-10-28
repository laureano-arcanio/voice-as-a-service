"""Campañas salientes, lo que es comun a WhatsApp y voz (docs/LLAMADAS_SALIENTES_PLAN.md, 3.3, 3.4 y 7).

- Estado: draft -> scheduled o running (start) -> paused (pause, o sola por un problema) ->
  done (sin pendientes, o pasado ends_at) o cancelled. Iniciar valida el plan (services/limits.py).
- Contactos: salen de la agenda (services/contacts.py). Al agregarlos, `vars` guarda una copia de sus
  datos (la campaña no cambia si despues se edita el contacto) y, en WhatsApp, los valores de las
  variables de la plantilla: por nombre de atributo (`template_param_names`) o posicionales.
- Seguimiento: conteos por estado y resultado, ritmo real y minutos de voz, para el polling.
- WhatsApp (plantilla, envio, entregado y leido): app/whatsapp/campaigns.py y sender.py. Voz: aca se
  crea, se valida y se arma la lista; las llamadas las hace el dialer (app/campaigns/dialer.py) y el
  cierre de cada intento, services/campaign_calls.py.

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama.
"""
from __future__ import annotations

import datetime
import logging
import math
import re
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import (
    Agent,
    CallRow,
    Campaign,
    CampaignContact,
    Client,
    Contact,
    PhoneNumber,
)
from . import campaign_callbacks as callbacks
from . import contacts as contacts_service
from . import limits as limits_service
from . import phones, voices
from .errors import Conflict, Invalid, NotFound

logger = logging.getLogger(__name__)

CHANNELS = ("whatsapp", "voice")
PROGRESS_KEYS = ("pending", "in_progress", "retry", "done", "failed", "skipped")
VOICE_RESULTS = ("answered", "no_answer", "busy", "voicemail", "invalid", "rejected", "failed")
# Reintentos por default de una campaña de voz (plan, 3.3).
DEFAULT_ATTEMPTS, DEFAULT_RETRY_MINUTES = 3, 60
DEFAULT_RETRY_ON = ["no_answer", "busy", "voicemail", "failed"]
ETA_WINDOW_MINUTES = 15
PURPOSES = ("comercial", "cobranza", "turnos", "aviso")
# Resultados de una llamada que no se atendio: despues de cualquiera de ellos se puede mandar el seguimiento.
FOLLOWUP_AFTER = tuple(r for r in VOICE_RESULTS if r != "answered")
DEFAULT_FOLLOWUP_AFTER = ["no_answer", "busy", "voicemail"]


@dataclass
class Skipped:
    phone: str
    reason: str
    line: int | None = None     # fila del CSV (1 = encabezado)


@dataclass
class Candidate:
    """Un contacto a sumar: el de la agenda, y como vino (telefono y fila) para informar el motivo."""
    contact: Contact
    raw: str
    line: int | None = None


# --- Horario y programacion ---

def local_hour(now: datetime.datetime | None = None) -> int:
    tz = ZoneInfo(settings.billing_timezone)
    return (now.astimezone(tz) if now else datetime.datetime.now(tz)).hour


def local_weekday(now: datetime.datetime | None = None) -> int:
    """Dia de la semana en billing_timezone: 0 = lunes ... 6 = domingo."""
    tz = ZoneInfo(settings.billing_timezone)
    return (now.astimezone(tz) if now else datetime.datetime.now(tz)).weekday()


def holidays() -> frozenset[datetime.date]:
    """Los feriados de CAMPAIGN_HOLIDAYS (YYYY-MM-DD separados por coma). Uno mal escrito se ignora, con aviso."""
    out = set()
    for raw in settings.campaign_holidays.split(","):
        if raw := raw.strip():
            try:
                out.add(datetime.date.fromisoformat(raw))
            except ValueError:
                logger.warning("CAMPAIGN_HOLIDAYS: %r no es una fecha YYYY-MM-DD, se ignora", raw)
    return frozenset(out)


def local_date(now: datetime.datetime | None = None) -> datetime.date:
    tz = ZoneInfo(settings.billing_timezone)
    return (now.astimezone(tz) if now else datetime.datetime.now(tz)).date()


def in_window(c: Campaign, now: datetime.datetime | None = None) -> bool:
    """Si ahora (UTC) cae en el horario y los dias permitidos de la campaña. Las de voz tampoco
    llaman en feriados (CAMPAIGN_HOLIDAYS)."""
    aware = now.replace(tzinfo=datetime.UTC) if now else None
    if c.channel == "voice" and local_date(aware) in holidays():
        return False
    return (c.window_start <= local_hour(aware) < c.window_end
            and (c.weekdays is None or local_weekday(aware) in c.weekdays))


def check_window(start: int, end: int) -> None:
    if not (0 <= start < end <= 24):
        raise Invalid("Horario inválido: la hora de inicio tiene que ser menor que la de fin")


def clean_weekdays(weekdays: list[int] | None) -> list[int] | None:
    """Dias permitidos (0 = lunes ... 6 = domingo), sin repetir y en orden; None o vacio: todos."""
    if not weekdays:
        return None
    if any(isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 6 for d in weekdays):
        raise Invalid("Días inválidos: van de 0 (lunes) a 6 (domingo)")
    days = sorted(set(weekdays))
    return None if len(days) == 7 else days


def check_schedule(starts_at: datetime.datetime | None, ends_at: datetime.datetime | None,
                   now: datetime.datetime | None = None) -> None:
    """starts_at y ends_at en UTC naive."""
    now = now or utcnow()
    if ends_at is not None and ends_at <= now:
        raise Invalid("ends_at tiene que ser futuro")
    if starts_at is not None and ends_at is not None and ends_at <= starts_at:
        raise Invalid("ends_at tiene que ser posterior a starts_at")


def launch_status(c: Campaign, now: datetime.datetime | None = None) -> str:
    """Al iniciar: scheduled si todavia no llego starts_at, running si ya."""
    now = now or utcnow()
    return "scheduled" if c.starts_at is not None and c.starts_at > now else "running"


# --- Plan ---

def effective(s: Session, client_id: str) -> limits_service.Limits:
    client = s.get(Client, client_id)
    if client is None:
        raise NotFound("Cliente inexistente")
    return limits_service.effective_limits(s, client)


def check_channel(s: Session, client_id: str, channel: str) -> None:
    limits_service.check_campaign_channel(effective(s, client_id), channel)


# --- Variables ---

def clean_param(value: Any) -> str:
    """Meta rechaza variables con saltos de linea, tabs o mas de 4 espacios seguidos."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\s+", " ", str(value if value is not None else "")).strip()


def param_value(contact: Contact, name: str) -> str:
    """El dato del contacto que se llama `name`: nombre, telefono, email o external_id
    (sin importar mayusculas ni acentos). Vacio si no lo tiene."""
    key = contacts_service.attribute_key(name)
    fixed = {"nombre": contact.name, "name": contact.name, "telefono": contact.phone, "phone": contact.phone,
             "email": contact.email, "external_id": contact.external_id}
    if key in fixed:
        return clean_param(fixed[key])
    return ""


def param_values(contact: Contact, names: list[str]) -> list[str]:
    return [param_value(contact, n) for n in names]


def vars_values(vars_: dict, names: list[str]) -> list[str]:
    """Como param_values, pero de la copia de datos que guarda la campaña (`vars`): el seguimiento
    usa lo que se cargo al armar la lista, no la ficha de hoy."""
    aliases = {"name": "nombre", "phone": "telefono"}
    normalized = {contacts_service.attribute_key(str(k)): v for k, v in (vars_ or {}).items() if k != "params"}
    out = []
    for name in names:
        key = contacts_service.attribute_key(name)
        out.append(clean_param(normalized.get(key, normalized.get(aliases.get(key, key)))))
    return out


def clean_param_names(names: list[str] | None, expected: int) -> list[str] | None:
    """Los datos del contacto de {{1}}..{{n}}: tantos como variables tiene la plantilla."""
    names = [str(n).strip() for n in names or []]
    if not names:
        return None
    if len(names) != expected:
        raise Invalid(f"La plantilla tiene {expected} variables y param_names tiene {len(names)}")
    if any(not n or len(n) > 64 for n in names):
        raise Invalid("param_names: cada nombre va de 1 a 64 caracteres")
    return names


def contact_vars(contact: Contact, params: list[str] | None = None) -> dict:
    """Copia de los datos del contacto para la campaña: nombre, telefono, email e id externo con
    esos nombres, y `params` (valores de {{1}}..{{n}} de la plantilla)."""
    out: dict[str, Any] = {}
    for key, value in (("nombre", contact.name), ("telefono", contact.phone), ("email", contact.email),
                       ("external_id", contact.external_id)):
        if value:
            out[key] = value
    if params is not None:
        out["params"] = params
    return out


# --- Crear y editar ---

def check_agent(s: Session, client_id: str, agent_id: str) -> None:
    agent = s.get(Agent, agent_id)
    if agent is None or agent.client_id != client_id:
        raise NotFound("Agente inexistente para este cliente")
    if agent.archived_at is not None:
        raise Invalid("El agente esta archivado")


def check_from_number(s: Session, client_id: str, number_id: str | None) -> None:
    if number_id is None:
        return
    number = s.get(PhoneNumber, number_id)
    if number is None or number.client_id != client_id:
        raise NotFound("Número de origen inexistente")
    if number.suspended_at is not None:
        raise Invalid("El número de origen está suspendido")


def check_voice(*, concurrency: int, max_attempts: int, retry_minutes: int, retry_on: list[str]) -> None:
    if concurrency < 1:
        raise Invalid("concurrency: al menos 1 (1 = una llamada por vez)")
    if max_attempts < 1:
        raise Invalid("max_attempts: al menos 1")
    if retry_minutes < 1:
        raise Invalid("retry_minutes: al menos 1")
    bad = [r for r in retry_on if r not in VOICE_RESULTS or r == "answered"]
    if bad:
        raise Invalid(f"retry_on: resultados que no se reintentan o inexistentes: {', '.join(bad)}")


def check_purpose(purpose: str | None) -> None:
    if purpose is not None and purpose not in PURPOSES:
        raise Invalid(f"purpose: {', '.join(PURPOSES)}")


def check_registry(campaign: Campaign, confirmed: bool, now: datetime.datetime) -> None:
    """Una campaña comercial se inicia solo con la confirmacion de que la lista se filtro contra el
    Registro No Llame (Ley 26.951). Se guarda cuando se confirmo y no se vuelve a pedir al retomarla."""
    if campaign.purpose != "comercial" or campaign.no_call_confirmed_at is not None:
        return
    if not confirmed:
        raise Invalid("Una campaña comercial se inicia confirmando que la lista se filtró contra el Registro "
                      "No Llame (no_call_registry_checked)", "no_call_confirmation_required")
    campaign.no_call_confirmed_at = now


def create_voice(s: Session, *, client_id: str, name: str, agent_id: str | None, rate_per_minute: int,
                 window_start: int, window_end: int, weekdays: list[int] | None,
                 starts_at: datetime.datetime | None, ends_at: datetime.datetime | None,
                 from_number_id: str | None, voice: str | None, concurrency: int, max_attempts: int | None,
                 retry_minutes: int | None, retry_on: list[str] | None, created_by: str | None,
                 purpose: str | None = None, followup: dict | None = None) -> Campaign:
    """Campaña de voz en borrador. El agente es obligatorio (llama el, no hay plantilla ni numero de
    WhatsApp que lo traiga). Se valida el plan: canal habilitado y concurrencia."""
    limits = effective(s, client_id)
    limits_service.check_campaign_channel(limits, "voice")
    limits_service.check_campaign_concurrency(limits, concurrency)
    if agent_id is None:
        raise Invalid("Una campaña de voz necesita agent_id")
    check_agent(s, client_id, agent_id)
    check_from_number(s, client_id, from_number_id)
    check_window(window_start, window_end)
    check_schedule(starts_at, ends_at)
    attempts = max_attempts if max_attempts is not None else DEFAULT_ATTEMPTS
    minutes = retry_minutes if retry_minutes is not None else DEFAULT_RETRY_MINUTES
    on = list(dict.fromkeys(retry_on)) if retry_on is not None else list(DEFAULT_RETRY_ON)
    check_voice(concurrency=concurrency, max_attempts=attempts, retry_minutes=minutes, retry_on=on)
    if voice is not None and voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}", "invalid_voice")
    check_purpose(purpose)
    if followup is not None:
        limits_service.check_campaign_followup(limits)
    campaign = Campaign(client_id=client_id, channel="voice", agent_id=agent_id, name=name.strip(), purpose=purpose,
                        followup=followup,
                        status="draft", rate_per_minute=rate_per_minute, window_start=window_start,
                        window_end=window_end, weekdays=clean_weekdays(weekdays), starts_at=starts_at,
                        ends_at=ends_at, from_number_id=from_number_id, voice=voice, concurrency=concurrency,
                        max_attempts=attempts, retry_minutes=minutes, retry_on=on, created_by=created_by)
    s.add(campaign)
    s.flush()
    return campaign


COMMON_EDITABLE = ("name", "agent_id", "rate_per_minute", "window_start", "window_end", "weekdays", "starts_at",
                   "ends_at", "purpose")
VOICE_EDITABLE = ("from_number_id", "voice", "concurrency", "max_attempts", "retry_minutes", "retry_on", "followup")


def update(s: Session, campaign: Campaign, changes: dict) -> Campaign:
    """Edita la campaña (no la terminada). agent_id null en WhatsApp: responde el agente del numero.
    Los campos de voz, solo en una campaña de voz."""
    if campaign.status in ("done", "cancelled"):
        raise Conflict("La campaña ya terminó")
    editable = COMMON_EDITABLE + (VOICE_EDITABLE if campaign.channel == "voice" else ())
    unknown = set(changes) - set(editable)
    if unknown:
        raise Invalid(f"Campos no editables: {', '.join(sorted(unknown))}")
    if "agent_id" in changes and changes["agent_id"] is not None:
        check_agent(s, campaign.client_id, changes["agent_id"])
    if campaign.channel == "voice" and changes.get("agent_id", campaign.agent_id) is None:
        raise Invalid("Una campaña de voz necesita agent_id")
    if "from_number_id" in changes:
        check_from_number(s, campaign.client_id, changes["from_number_id"])
    check_window(changes.get("window_start", campaign.window_start), changes.get("window_end", campaign.window_end))
    check_schedule(changes.get("starts_at", campaign.starts_at), changes.get("ends_at", campaign.ends_at))
    if "purpose" in changes:
        check_purpose(changes["purpose"])
        if changes["purpose"] != campaign.purpose and campaign.status in ("running", "scheduled"):
            raise Conflict("Pausá la campaña para cambiar su finalidad (purpose)")
    if changes.get("followup") is not None:
        limits_service.check_campaign_followup(effective(s, campaign.client_id))
    if campaign.channel == "voice":
        check_voice(concurrency=changes.get("concurrency", campaign.concurrency),
                    max_attempts=changes.get("max_attempts", campaign.max_attempts),
                    retry_minutes=changes.get("retry_minutes", campaign.retry_minutes),
                    retry_on=changes.get("retry_on", campaign.retry_on))
        if "concurrency" in changes:
            limits_service.check_campaign_concurrency(effective(s, campaign.client_id), changes["concurrency"])
        if changes.get("voice") is not None and changes["voice"] not in voices.catalog():
            raise Invalid(f"Voz inexistente: {changes['voice']}", "invalid_voice")
    for key, value in changes.items():
        if key == "name":
            value = value.strip()
        elif key == "weekdays":
            value = clean_weekdays(value)
        elif key == "retry_on":
            value = list(dict.fromkeys(value))
        elif key == "purpose" and value != campaign.purpose:
            campaign.no_call_confirmed_at = None      # otra finalidad, otra confirmacion
        setattr(campaign, key, value)
    s.flush()
    return campaign


# --- Contactos ---

def contact_count(s: Session, campaign_id: str) -> int:
    return s.scalar(select(func.count()).select_from(CampaignContact)
                    .where(CampaignContact.campaign_id == campaign_id)) or 0


def pending_count(s: Session, campaign_id: str) -> int:
    return s.scalar(select(func.count()).select_from(CampaignContact).where(
        CampaignContact.campaign_id == campaign_id, CampaignContact.status == "pending")) or 0


def open_count(s: Session, campaign_id: str) -> int:
    """Contactos que aun tienen algo por hacer: pendientes, en vuelo o por reintentar."""
    return s.scalar(select(func.count()).select_from(CampaignContact).where(
        CampaignContact.campaign_id == campaign_id,
        CampaignContact.status.in_(("pending", "in_progress", "retry")))) or 0


def add_contacts(s: Session, campaign: Campaign, candidates: list[Candidate]) -> tuple[int, list[Skipped]]:
    """Suma contactos de la agenda a una campaña en borrador o pausada. Se saltean, con el motivo,
    los repetidos, archivados, dados de baja del canal, los fijos en WhatsApp, los que no completan
    las variables de la plantilla y los que pasan el tope de contactos del plan."""
    if campaign.status not in ("draft", "paused"):
        raise Conflict("Solo se suman contactos a una campaña en borrador o pausada")
    whatsapp = campaign.channel == "whatsapp"
    names = campaign.template_param_names
    if whatsapp and campaign.template_params and not names:
        raise Invalid(f"La plantilla tiene {campaign.template_params} variables: indicá param_names (el dato "
                      f"de cada contacto que completa cada una) o cargá los valores con recipients")
    limits = effective(s, campaign.client_id)
    existing = set(s.scalars(select(CampaignContact.contact_id).where(CampaignContact.campaign_id == campaign.id)))
    optouts = contacts_service.opted_out_phones(s, campaign.client_id, campaign.channel)
    total = len(existing)
    room = limits_service.campaign_contacts_room(limits, total, settings.wa_campaign_max_recipients)
    added, skipped = 0, []
    for cand in candidates:
        contact = cand.contact
        params = param_values(contact, names) if whatsapp and names else None
        if contact.id in existing:
            skipped.append(Skipped(cand.raw, "repetido", cand.line))
        elif contact.archived_at is not None:
            skipped.append(Skipped(cand.raw, "contacto archivado", cand.line))
        elif contact.phone in optouts:
            skipped.append(Skipped(cand.raw, "pidió la baja", cand.line))
        elif whatsapp and not phones.has_whatsapp(contact.phone):
            skipped.append(Skipped(cand.raw, "es un teléfono fijo: no tiene WhatsApp", cand.line))
        elif params is not None and not all(params):
            skipped.append(Skipped(cand.raw, f"la plantilla tiene {campaign.template_params} variables: "
                                             f"faltan valores", cand.line))
        elif added >= room:
            skipped.append(Skipped(cand.raw, f"tope de {total + room} contactos por campaña", cand.line))
        else:
            s.add(CampaignContact(campaign_id=campaign.id, contact=contact, vars=contact_vars(contact, params)))
            existing.add(contact.id)
            added += 1
    if added and campaign.status == "done":
        campaign.status = "paused"
    s.flush()
    return added, skipped


def contacts_by_ids(s: Session, client_id: str, ids: list[str]) -> list[Candidate | Skipped]:
    """Los contactos del cliente con esos ids, en orden; los que no existen vuelven como Skipped."""
    found: dict[str, Contact] = {}
    unique = list(dict.fromkeys(ids))
    for i in range(0, len(unique), contacts_service.CHUNK):
        for c in s.scalars(select(Contact).where(Contact.client_id == client_id,
                                                 Contact.id.in_(unique[i:i + contacts_service.CHUNK]))):
            found[c.id] = c
    return [Candidate(found[i], found[i].phone) if i in found else Skipped(i, "contacto inexistente")
            for i in unique]


def contacts_from_rows(s: Session, client_id: str, rows: list[contacts_service.ContactRow],
                       source: str) -> tuple[list[Candidate], list[Skipped]]:
    """Carga las filas en la agenda (upsert por telefono) y devuelve los contactos para la campaña.
    Las filas invalidas o que no entran por el tope de la agenda vuelven como Skipped."""
    result = contacts_service.upsert(s, client_id, rows, source=source)
    skipped = [Skipped(x.phone, x.reason, x.line) for x in result.invalid]
    valid = []
    for row in rows:
        try:
            valid.append((row, phones.normalize_phone(row.phone)))
        except ValueError:
            continue
    known = contacts_service.find(s, client_id, [phone for _, phone in valid])
    return [Candidate(known[phone], row.phone, row.line) for row, phone in valid if phone in known], skipped


# --- Estado ---

def start(s: Session, campaign: Campaign, now: datetime.datetime | None = None, *,
          registry_checked: bool = False) -> None:
    """Inicia una campaña en borrador o retoma una pausada, con lo que el plan permite. Quien llama
    ya valido lo propio del canal (cuenta y plantilla de WhatsApp, agente y numero de voz).
    `registry_checked`: la confirmacion del Registro No Llame que piden las campañas comerciales."""
    if campaign.status not in ("draft", "paused"):
        raise Conflict("Solo se inicia una campaña en borrador o pausada")
    now = now or utcnow()
    if campaign.ends_at is not None and campaign.ends_at <= now:
        raise Conflict("Ya pasó la fecha de fin de la campaña (ends_at)")
    check_registry(campaign, registry_checked, now)
    # El cliente se bloquea: dos campañas iniciadas a la vez no pueden pasarse del cupo mensual.
    client = s.scalar(select(Client).where(Client.id == campaign.client_id).with_for_update(key_share=True, of=Client))
    if client is None:
        raise NotFound("Cliente inexistente")
    limits_service.check_campaign_start(s, campaign, limits_service.effective_limits(s, client), now)
    if open_count(s, campaign.id) == 0:      # retomar una con solo reintentos o intentos en vuelo es valido
        raise Conflict("La campaña no tiene contactos pendientes")
    campaign.status, campaign.status_reason = launch_status(campaign, now), None
    campaign.started_at = campaign.started_at or now
    s.flush()


def check_startable(s: Session, campaign: Campaign) -> None:
    """Lo propio de una campaña de voz para iniciarla: agente vigente y numero de origen."""
    if campaign.agent_id is None:
        raise Conflict("La campaña no tiene agente")
    agent = s.get(Agent, campaign.agent_id)
    if agent is None or agent.archived_at is not None:
        raise Conflict("El agente de la campaña está archivado: elegí otro")
    if campaign.from_number_id is not None:
        number = s.get(PhoneNumber, campaign.from_number_id)
        if number is None or number.client_id != campaign.client_id or number.suspended_at is not None:
            raise Conflict("El número de origen de la campaña ya no está disponible: elegí otro")


def pause(s: Session, campaign: Campaign, reason: str | None = None) -> None:
    if campaign.status not in ("running", "scheduled"):
        raise Conflict("La campaña no está en curso")
    campaign.status, campaign.status_reason = "paused", reason[:255] if reason else None
    s.flush()


def skip_open(s: Session, campaign_id: str, message: str) -> None:
    """Los pendientes (y los reintentos) quedan salteados, y los seguimientos por WhatsApp sin mandar tambien."""
    for r in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == campaign_id,
                                                     CampaignContact.status.in_(("pending", "retry")))):
        r.status, r.error = "skipped", {"message": message}
    for r in s.scalars(select(CampaignContact).where(CampaignContact.campaign_id == campaign_id,
                                                     CampaignContact.followup_status == "pending")):
        r.followup_status, r.followup_error = "skipped", {"message": message}


def cancel(s: Session, campaign: Campaign) -> None:
    """Termina la campaña: los pendientes quedan salteados. Las respuestas siguen llegando."""
    if campaign.status in ("done", "cancelled"):
        raise Conflict("La campaña ya terminó")
    skip_open(s, campaign.id, "Campaña cancelada")
    campaign.status, campaign.finished_at = "cancelled", utcnow()
    callbacks.enqueue(s, campaign, "campaign.finished")
    s.flush()


def delete(s: Session, campaign: Campaign) -> None:
    if campaign.status != "draft":
        raise Conflict("Solo se borra una campaña en borrador; si ya empezó, cancelala")
    s.delete(campaign)
    s.flush()


def roll_schedule(s: Session, channels: tuple[str, ...], now: datetime.datetime | None = None) -> int:
    """Programacion: las `scheduled` cuyo starts_at llego pasan a `running`, y las que pasaron
    ends_at (programadas, en curso o pausadas) terminan con sus pendientes salteados. Devuelve
    cuantas cambio. Lo corre el loop de cada canal."""
    now = now or utcnow()
    changed = 0
    open_ = ("scheduled", "running", "paused")
    for c in s.scalars(select(Campaign).where(Campaign.channel.in_(channels), Campaign.status.in_(open_),
                                              Campaign.ends_at.is_not(None), Campaign.ends_at <= now)):
        skip_open(s, c.id, "Terminó el plazo de la campaña (ends_at)")
        c.status, c.status_reason, c.finished_at = "done", "Terminó el plazo de la campaña", now
        callbacks.enqueue(s, c, "campaign.finished", now=now)
        changed += 1
    for c in s.scalars(select(Campaign).where(Campaign.channel.in_(channels), Campaign.status == "scheduled",
                                              Campaign.starts_at <= now)):
        c.status = "running"
        changed += 1
    s.flush()
    return changed


# --- Seguimiento ---

def progress(s: Session, campaign_ids: list[str]) -> dict[str, dict[str, int]]:
    """Contactos por estado de cada campaña, con `total`."""
    out = {cid: dict.fromkeys(PROGRESS_KEYS, 0) for cid in campaign_ids}
    if campaign_ids:
        q = (select(CampaignContact.campaign_id, CampaignContact.status, func.count())
             .where(CampaignContact.campaign_id.in_(campaign_ids))
             .group_by(CampaignContact.campaign_id, CampaignContact.status))
        for cid, status, n in s.execute(q):
            out[cid][status] = n
    return out


def voice_results(s: Session, campaign_ids: list[str]) -> dict[str, dict[str, int]]:
    """Contactos por resultado de la llamada de cada campaña de voz."""
    out = {cid: dict.fromkeys(VOICE_RESULTS, 0) for cid in campaign_ids}
    if campaign_ids:
        q = (select(CampaignContact.campaign_id, CampaignContact.result, func.count())
             .where(CampaignContact.campaign_id.in_(campaign_ids), CampaignContact.result.is_not(None))
             .group_by(CampaignContact.campaign_id, CampaignContact.result))
        for cid, result, n in s.execute(q):
            if result in out[cid]:
                out[cid][result] = n
    return out


def followup_counts(s: Session, campaign_ids: list[str]) -> dict[str, dict[str, int]]:
    """Seguimiento por WhatsApp de cada campaña de voz: contactos por estado. `sent` incluye a los que
    respondieron (`replied`), como en WhatsApp."""
    out = {cid: {"pending": 0, "sent": 0, "replied": 0, "failed": 0, "skipped": 0} for cid in campaign_ids}
    if campaign_ids:
        q = (select(CampaignContact.campaign_id, CampaignContact.followup_status,
                    CampaignContact.replied_at.is_not(None), func.count())
             .where(CampaignContact.campaign_id.in_(campaign_ids), CampaignContact.followup_status.is_not(None))
             .group_by(CampaignContact.campaign_id, CampaignContact.followup_status,
                       CampaignContact.replied_at.is_not(None)))
        for cid, status, replied, n in s.execute(q):
            row = out[cid]
            row["pending" if status in ("pending", "in_progress") else status] += n
            if status == "sent" and replied:
                row["replied"] += n
    return out


def percent(prog: dict[str, int]) -> float:
    """Lo que ya no espera nada (terminado, fallido o salteado), sobre el total."""
    total = sum(prog.values())
    return round(100 * (prog["done"] + prog["failed"] + prog["skipped"]) / total, 1) if total else 0.0


def eta_minutes(s: Session, c: Campaign, prog: dict[str, int], now: datetime.datetime | None = None) -> int | None:
    """Minutos que faltan al ritmo real de los ultimos 15 (contactos que terminaron, enviados o
    llamados). None si no esta en curso o todavia no hay ritmo."""
    if c.status != "running":
        return None
    remaining = prog["pending"] + prog["in_progress"] + prog["retry"]
    if remaining == 0:
        return 0
    now = now or utcnow()
    since = now - datetime.timedelta(minutes=ETA_WINDOW_MINUTES)
    at = func.coalesce(CampaignContact.last_attempt_at, CampaignContact.sent_at)
    n = s.scalar(select(func.count()).select_from(CampaignContact).where(
        CampaignContact.campaign_id == c.id, CampaignContact.status.in_(("done", "failed")), at >= since)) or 0
    if n == 0:
        return None
    # Una campaña que empezo hace poco se mide desde que empezo (al menos un minuto).
    span = ETA_WINDOW_MINUTES
    if c.started_at is not None:
        span = min(span, max((now - c.started_at).total_seconds() / 60, 1.0))
    return math.ceil(remaining / (n / span))


def minutes_used(s: Session, campaign_id: str) -> float:
    """Minutos de llamada de la campaña (voz), de todos sus intentos."""
    seconds = s.scalar(select(func.coalesce(func.sum(CallRow.duration_seconds), 0))
                       .join(CampaignContact, CampaignContact.id == CallRow.campaign_contact_id)
                       .where(CampaignContact.campaign_id == campaign_id)) or 0
    return round(seconds / 60, 1)
