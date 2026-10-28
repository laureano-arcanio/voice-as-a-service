"""Campañas salientes de WhatsApp (docs/features/WHATSAPP.md): una plantilla aprobada a
una lista de contactos, por un numero conectado. El envio lo hace sender.py, de a poco
(ritmo por minuto) y dentro del horario de la campaña.

- Contactos: por API (lista) o CSV. Cada uno es un contacto de la agenda del cliente
  (services/contacts.py; se crea si falta) y el telefono se normaliza a E.164 (services/phones.py;
  el wa_id que manda Meta es el mismo numero sin el +). Los repetidos, invalidos, archivados o
  dados de baja no entran.
- Plantilla: se lee de Meta al crear la campaña y se guarda una copia del cuerpo. Solo
  variables en el cuerpo ({{1}}..{{n}}): encabezado de texto fijo, pie y botones fijos.
- Respuesta: el primer mensaje del contacto abre la conversacion con el cuerpo de la
  plantilla (con sus variables) como apertura, con el agente de la campaña o el del
  numero (service.py, _turn).
- Baja: un contacto de una campaña que escribe "baja", "no me interesa" o toca el boton
  de ese texto queda en contact_optouts (canal whatsapp) del cliente y ninguna campaña le vuelve
  a escribir.
- Variables: por dato del contacto (template_param_names, {{1}} = nombre...) o
  posicionales (vars["params"]).
- Estado, plan y horario comunes a los dos canales: services/campaigns.py. Las tablas son las de todas las campañas (campaigns, campaign_contacts): aca solo las de
  channel 'whatsapp'. Estados de un contacto: pending, in_progress (en vuelo), done con result
  'sent' (Meta lo acepto), failed y skipped.

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    Agent,
    Campaign,
    CampaignContact,
    Client,
    Contact,
    ContactOptout,
    WaAccount,
    WaMessage,
)
from ..services import campaigns as common
from ..services import contacts, limits, phones
from ..services.campaigns import (
    Skipped,
    check_window,
    contact_vars,
    param_values,
)
from ..services.contacts import NAME_COLUMNS, PHONE_COLUMNS
from ..services.contacts import header_key as _key
from ..services.errors import Conflict, Invalid
from . import signup, store

PLACEHOLDER_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")
STATUSES = ("draft", "scheduled", "running", "paused", "done", "cancelled")
CHANNEL = "whatsapp"
# Lo que se toma como pedido de baja: el mensaje entero, normalizado (sin acentos ni signos).
OPTOUT_TEXTS = {
    "baja", "stop", "no me interesa", "no gracias", "no me escriban", "no me escriban mas", "no me escribas",
    "no me escribas mas", "dar de baja", "darme de baja", "quiero darme de baja", "no quiero recibir mas mensajes",
    "no molestar", "basta", "desuscribir", "detener promociones", "stop promotions",
}


# --- Telefonos ---

def normalize_phone(raw: str) -> str:
    """El wa_id de un telefono, como lo manda Meta en los entrantes: el E.164 sin el +
    (services/phones.py). ValueError si no se reconoce."""
    return phones.wa_id(phones.normalize_phone(raw))


# --- Plantilla ---

def body_params(body: str) -> int:
    return len({int(n) for n in PLACEHOLDER_RE.findall(body)})


def render(body: str, params: list[str]) -> str:
    """El cuerpo con sus variables, como lo ve el contacto."""
    def sub(m: re.Match) -> str:
        i = int(m.group(1)) - 1
        return params[i] if 0 <= i < len(params) else m.group(0)
    return PLACEHOLDER_RE.sub(sub, body)


clean_param = common.clean_param


@dataclass(frozen=True)
class TemplateInfo:
    name: str
    language: str
    category: str
    body: str
    params: int


def template_info(templates: list[dict], name: str, language: str) -> TemplateInfo:
    """La plantilla aprobada de la lista de Meta. Invalid si no esta, no esta aprobada o
    usa algo que la campaña no sabe completar (variables fuera del cuerpo, encabezado con
    imagen o documento)."""
    found = next((t for t in templates if t.get("name") == name and t.get("language") == language), None)
    if found is None:
        raise Invalid(f"No existe la plantilla {name} ({language}) en la cuenta de WhatsApp")
    if str(found.get("status") or "").upper() != "APPROVED":
        raise Invalid(f"La plantilla {name} no está aprobada por Meta (estado: {found.get('status')})")
    body = ""
    for c in found.get("components") or []:
        if not isinstance(c, dict):
            continue
        kind = str(c.get("type") or "").upper()
        if kind == "BODY":
            body = str(c.get("text") or "")
        elif kind == "HEADER":
            if str(c.get("format") or "TEXT").upper() != "TEXT":
                raise Invalid("Las campañas todavía no mandan plantillas con imagen, video o documento")
            if "{{" in str(c.get("text") or ""):
                raise Invalid("Las campañas todavía no completan variables en el encabezado")
        elif kind == "BUTTONS":
            for b in c.get("buttons") or []:
                if isinstance(b, dict) and "{{" in str(b.get("url") or ""):
                    raise Invalid("Las campañas todavía no completan variables en los botones")
    if not body:
        raise Invalid(f"La plantilla {name} no tiene cuerpo")
    return TemplateInfo(name=name, language=language, category=str(found.get("category") or "").upper(),
                        body=body, params=body_params(body))


async def fetch_template(s: Session, account: WaAccount, name: str, language: str) -> TemplateInfo:
    return template_info(await signup.list_templates(s, account), name, language)


# --- Contactos ---

@dataclass
class Row:
    phone: str
    name: str | None
    params: list[str]
    line: int | None = None     # fila del CSV (1 = encabezado)


def parse_csv(text: str) -> list[Row]:
    """CSV con encabezado: una columna de telefono (telefono, celular, phone...), una de
    nombre opcional, y las demas, en orden, son las variables {{1}}, {{2}}... (el nombre
    tambien cuenta si esta entre ellas). Separador coma o punto y coma. Invalid si no hay
    columna de telefono."""
    text = (text or "").lstrip("﻿")
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, [])
    keys = [_key(h) for h in header]
    phone_col = next((i for i, k in enumerate(keys) if k in PHONE_COLUMNS), None)
    if phone_col is None:
        raise Invalid("El CSV necesita un encabezado con una columna telefono (o celular, phone, whatsapp)")
    name_col = next((i for i, k in enumerate(keys) if k in NAME_COLUMNS), None)
    var_cols = [i for i in range(len(keys)) if i != phone_col]
    rows = []
    for line, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        def cell(i: int, values: list[str] = values) -> str:
            return values[i].strip() if i < len(values) else ""
        rows.append(Row(phone=cell(phone_col), name=(cell(name_col) or None) if name_col is not None else None,
                        params=[cell(i) for i in var_cols], line=line))
    return rows


def add_recipients(s: Session, campaign: Campaign, rows: list[Row]) -> tuple[int, list[Skipped]]:
    """Suma contactos con sus variables a una campaña en borrador o pausada. Cada uno es un contacto
    de la agenda (se crea si falta). Se saltean los invalidos, los repetidos (en la lista o ya
    cargados), los archivados, los dados de baja y los que no completan las variables de la
    plantilla. Las variables de mas se ignoran. Una fila sin variables las toma del contacto, si
    la campaña tiene param_names. (Desde la agenda: services/campaigns.py, add_contacts.)"""
    if campaign.status not in ("draft", "paused"):
        raise Conflict("Solo se suman contactos a una campaña en borrador o pausada")
    client = s.get(Client, campaign.client_id)
    effective = limits.effective_limits(s, client)
    total = s.scalar(select(func.count()).select_from(CampaignContact)
                     .where(CampaignContact.campaign_id == campaign.id)) or 0
    existing = set(s.scalars(select(Contact.phone).join(CampaignContact, CampaignContact.contact_id == Contact.id)
                             .where(CampaignContact.campaign_id == campaign.id)))
    optouts = contacts.opted_out_phones(s, campaign.client_id, CHANNEL)
    room = limits.campaign_contacts_room(effective, total, settings.wa_campaign_max_recipients)
    agenda_room = limits.contacts_room(s, campaign.client_id, effective)    # contactos nuevos que entran
    added, skipped = 0, []
    normalized: list[tuple[Row, str | ValueError]] = []
    for row in rows:
        try:
            normalized.append((row, phones.normalize_phone(row.phone)))
        except ValueError as e:
            normalized.append((row, e))
    known = contacts.find(s, campaign.client_id, [phone for _, phone in normalized if isinstance(phone, str)])
    for row, phone in normalized:
        if isinstance(phone, ValueError):
            skipped.append(Skipped(row.phone, str(phone), row.line))
            continue
        contact = known.get(phone)
        params = [clean_param(p) for p in row.params][:campaign.template_params]
        if not any(params) and campaign.template_param_names:
            name = (row.name or None) and clean_param(row.name)[:128]
            params = param_values(contact or contacts.new_contact(campaign.client_id, phone, "campaign", name=name),
                                  campaign.template_param_names)
        if phone in existing:
            skipped.append(Skipped(row.phone, "repetido", row.line))
        elif contact is not None and contact.archived_at is not None:
            skipped.append(Skipped(row.phone, "contacto archivado", row.line))
        elif phone in optouts:
            skipped.append(Skipped(row.phone, "pidió la baja", row.line))
        elif not phones.has_whatsapp(phone):
            skipped.append(Skipped(row.phone, "es un teléfono fijo: no tiene WhatsApp", row.line))
        elif len(params) < campaign.template_params or not all(params):
            skipped.append(Skipped(row.phone, f"la plantilla tiene {campaign.template_params} variables: "
                                              f"faltan valores", row.line))
        elif added >= room:
            skipped.append(Skipped(row.phone, f"tope de {total + room} contactos por campaña", row.line))
        elif contact is None and agenda_room is not None and agenda_room <= 0:
            skipped.append(Skipped(row.phone, "tope de contactos de la agenda del plan", row.line))
        else:
            name = (row.name or None) and clean_param(row.name)[:128]
            if contact is None:
                contact = contacts.new_contact(campaign.client_id, phone, "campaign", name=name or None)
                s.add(contact)
                known[phone] = contact
                if agenda_room is not None:
                    agenda_room -= 1
            s.add(CampaignContact(campaign_id=campaign.id, contact=contact, vars=contact_vars(contact, params)))
            existing.add(phone)
            added += 1
    if added and campaign.status == "done":
        campaign.status = "paused"
    s.flush()
    return added, skipped


# --- Campañas ---

def check_agent(s: Session, client_id: str, agent_id: str | None) -> None:
    if agent_id is not None:
        store.check_agent(s, client_id, agent_id)


def create(s: Session, *, account: WaAccount, name: str, template: TemplateInfo, agent_id: str | None,
           rate_per_minute: int, window_start: int, window_end: int, created_by: str | None,
           param_names: list[str] | None = None, weekdays: list[int] | None = None,
           starts_at: datetime.datetime | None = None, ends_at: datetime.datetime | None = None,
           purpose: str | None = None) -> Campaign:
    """Campaña en borrador. param_names: el dato de cada contacto que completa {{1}}..{{n}}."""
    common.check_channel(s, account.client_id, CHANNEL)
    check_agent(s, account.client_id, agent_id)
    check_window(window_start, window_end)
    common.check_schedule(starts_at, ends_at)
    common.check_purpose(purpose)
    campaign = Campaign(client_id=account.client_id, channel=CHANNEL, account_id=account.id, agent_id=agent_id,
                        purpose=purpose, name=name.strip(), template_name=template.name, template_language=template.language,
                        template_category=template.category, template_body=template.body,
                        template_params=template.params, template_param_names=common.clean_param_names(
                            param_names, template.params), status="draft", rate_per_minute=rate_per_minute,
                        window_start=window_start, window_end=window_end, weekdays=common.clean_weekdays(weekdays),
                        starts_at=starts_at, ends_at=ends_at, created_by=created_by)
    s.add(campaign)
    s.flush()
    return campaign


EDITABLE = ("name", "agent_id", "rate_per_minute", "window_start", "window_end")


def update(s: Session, campaign: Campaign, **changes) -> Campaign:
    if campaign.status in ("done", "cancelled"):
        raise Conflict("La campaña ya terminó")
    unknown = set(changes) - set(EDITABLE)
    if unknown:
        raise Invalid(f"Campos no editables: {', '.join(sorted(unknown))}")
    if "agent_id" in changes:
        check_agent(s, campaign.client_id, changes["agent_id"])
    check_window(changes.get("window_start", campaign.window_start), changes.get("window_end", campaign.window_end))
    for key, value in changes.items():
        setattr(campaign, key, value.strip() if key == "name" else value)
    s.flush()
    return campaign


def start(s: Session, campaign: Campaign, account: WaAccount, *, registry_checked: bool = False) -> None:
    """Inicia o retoma el envio: la cuenta conectada, el agente vigente y lo que permite el plan
    (services/campaigns.py, start). Con starts_at futuro queda programada."""
    if campaign.status not in ("draft", "paused"):
        raise Conflict("Solo se inicia una campaña en borrador o pausada")
    if not account.active or account.status != "connected":
        raise Conflict("El número de WhatsApp de la campaña no está activo y conectado")
    if campaign.agent_id is not None:
        agent = s.get(Agent, campaign.agent_id)
        if agent is None or agent.archived_at is not None:
            raise Conflict("El agente de la campaña está archivado: elegí otro")
    common.start(s, campaign, registry_checked=registry_checked)


pause = common.pause
pending_count = common.pending_count


cancel = common.cancel
delete = common.delete


def list_campaigns(s: Session, client_id: str | None = None, account_id: str | None = None) -> list[Campaign]:
    q = select(Campaign).where(Campaign.channel == CHANNEL).order_by(Campaign.created_at.desc())
    if client_id is not None:
        q = q.where(Campaign.client_id == client_id)
    if account_id is not None:
        q = q.where(Campaign.account_id == account_id)
    return list(s.scalars(q))


# --- Seguimiento por WhatsApp de una campaña de voz (plan, seccion 6) ---

def followup_config(s: Session, client_id: str, account: WaAccount, template: TemplateInfo, *, after: list[str],
                    params: list[str], agent_id: str | None) -> dict:
    """El `followup` de una campaña de voz, validado: el plan lo incluye, la cuenta es del cliente y esta
    conectada, la plantilla esta aprobada y `params` (el dato del contacto de cada {{n}}) la completa. Se
    guarda una copia del cuerpo: es la apertura de la conversacion si el contacto responde."""
    limits.check_campaign_followup(common.effective(s, client_id))
    if account.client_id != client_id:
        raise Invalid("El número de WhatsApp del seguimiento no es de este cliente")
    if not account.active or account.status != "connected":
        raise Conflict("El número de WhatsApp del seguimiento no está activo y conectado")
    check_agent(s, client_id, agent_id)
    after = list(dict.fromkeys(after or common.DEFAULT_FOLLOWUP_AFTER))
    bad = [r for r in after if r not in common.FOLLOWUP_AFTER]
    if bad:
        raise Invalid(f"followup.after: resultados inexistentes o que no corresponden: {', '.join(bad)}")
    names = common.clean_param_names(params, template.params) or []
    if template.params and not names:
        raise Invalid(f"La plantilla tiene {template.params} variables: indicá followup.params (el dato de cada "
                      f"contacto que completa cada una)")
    return {"after": after, "account_id": account.id, "template_name": template.name,
            "template_language": template.language, "template_category": template.category,
            "template_body": template.body, "template_params": template.params, "params": names,
            "agent_id": agent_id}


def followup_values(campaign: Campaign, r: CampaignContact) -> list[str]:
    """Los valores de {{1}}..{{n}} de la plantilla del seguimiento para un contacto (de su `vars`)."""
    return common.vars_values(r.vars, (campaign.followup or {}).get("params") or [])


# --- Estado de cada contacto y totales ---

STATS_KEYS = ("total", "pending", "sent", "delivered", "read", "replied", "failed", "skipped", "opted_out")


def wa_status(r: CampaignContact) -> str:
    """El estado de un contacto en los terminos de WhatsApp: pending, sending (en vuelo), sent
    (Meta lo acepto), failed o skipped."""
    if r.status == "done":
        return "sent"
    return {"in_progress": "sending", "retry": "pending"}.get(r.status, r.status)


def shown_status(status: str, message_status: str | None, replied: bool) -> str:
    """Lo que se muestra de un contacto: el de la campaña, avanzado con lo que informo
    Meta por el webhook (entregado, leido o fallido despues de aceptado) y la respuesta."""
    if replied:
        return "replied"
    if status == "sent" and message_status in ("delivered", "read", "failed"):
        return message_status
    return "pending" if status == "sending" else status


def stats(s: Session, campaign_ids: list[str]) -> dict[str, dict[str, int]]:
    """Totales por campaña. Cada contacto cuenta en un estado (shown_status); sent, delivered
    y read son acumulativos (uno leido tambien fue entregado y enviado), replied cuenta
    aparte y opted_out son los que pidieron la baja despues."""
    out = {cid: dict.fromkeys(STATS_KEYS, 0) for cid in campaign_ids}
    if not campaign_ids:
        return out
    r = CampaignContact
    q = (select(r.campaign_id, r.status, WaMessage.status, r.replied_at.is_not(None), func.count())
         .outerjoin(WaMessage, WaMessage.wamid == r.wamid)
         .where(r.campaign_id.in_(campaign_ids))
         .group_by(r.campaign_id, r.status, WaMessage.status, r.replied_at.is_not(None)))
    for cid, status, msg_status, replied, n in s.execute(q):
        st = out[cid]
        st["total"] += n
        if status in ("pending", "in_progress", "retry"):
            st["pending"] += n
        elif status == "skipped":
            st["skipped"] += n
        elif status == "failed" or msg_status == "failed":
            st["failed"] += n
        else:   # done: Meta lo acepto
            st["sent"] += n
            if msg_status in ("delivered", "read"):
                st["delivered"] += n
            if msg_status == "read":
                st["read"] += n
        if replied:
            st["replied"] += n
    # Los que recibieron la campaña y despues pidieron la baja (de WhatsApp o de todos los canales).
    opted_out = (select(ContactOptout.phone).where(
        ContactOptout.client_id == Campaign.client_id, ContactOptout.phone == Contact.phone,
        ContactOptout.channel.in_((CHANNEL, "all"))).exists())
    q = (select(r.campaign_id, func.count()).join(Campaign, Campaign.id == r.campaign_id)
         .join(Contact, Contact.id == r.contact_id)
         .where(r.campaign_id.in_(campaign_ids), r.status == "done", r.result == "sent", opted_out)
         .group_by(r.campaign_id))
    for cid, n in s.execute(q):
        out[cid]["opted_out"] = n
    return out


def status_filters() -> dict:
    """Condiciones SQL de cada estado mostrado (shown_status), sobre CampaignContact y el WaMessage
    de su wamid (outer join)."""
    r, m = CampaignContact, WaMessage
    sent = (r.status == "done") & r.replied_at.is_(None)
    return {
        "pending": r.status.in_(("pending", "in_progress", "retry")),
        "skipped": r.status == "skipped",
        "failed": (r.status == "failed") | (sent & (m.status == "failed")),
        "sent": sent & ((m.status.is_(None)) | (m.status == "sent")),
        "delivered": sent & (m.status == "delivered"),
        "read": sent & (m.status == "read"),
        "replied": r.replied_at.is_not(None),
    }


def shown_result(r: CampaignContact, message_status: str | None) -> str | None:
    """El resultado de un contacto, avanzado con lo que informo Meta: sent, delivered, read, replied
    o failed. None si todavia no se envio (o se salteo)."""
    if r.status == "failed":
        return "failed"
    if r.status != "done":
        return None
    return shown_status("sent", message_status, r.replied_at is not None)


def recipients_page(s: Session, campaign_id: str, status: str | None, offset: int,
                    limit: int) -> tuple[list[tuple[CampaignContact, WaMessage | None]], int]:
    """Contactos de la campaña con su mensaje (estado de Meta), en orden de carga. status:
    pending, failed, replied... como shown_status (el filtro se aplica en SQL)."""
    r, m = CampaignContact, WaMessage
    q = select(r, m).outerjoin(m, m.wamid == r.wamid).where(r.campaign_id == campaign_id)
    filters = status_filters()
    if status:
        if status not in filters:
            raise Invalid(f"Estado inválido: {status}")
        q = q.where(filters[status])
    total = s.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = s.execute(q.order_by(r.created_at, r.id).offset(offset).limit(limit)).all()
    return [(row[0], row[1]) for row in rows], total


# --- Respuestas y bajas ---

@dataclass(frozen=True)
class ReplyTarget:
    """La campaña a la que responde un contacto: la apertura y el agente de la conversacion.
    `sent_at`: cuando se mando (para quedarse con el mas reciente)."""
    recipient_id: str
    campaign_id: str
    agent_id: str | None
    opening: str
    sent_at: datetime.datetime | None = None


def _followup_sent(s: Session, account_id: str, wa_id: str, since: datetime.datetime | None = None,
                   unanswered: bool = False) -> list[tuple[CampaignContact, Campaign]]:
    """Los seguimientos por WhatsApp de campañas de voz que mando esta cuenta a este contacto, el mas
    reciente primero. `since`: dentro de ese plazo; `unanswered`: los que no respondio."""
    r = CampaignContact
    q = (select(r, Campaign).join(Campaign, Campaign.id == r.campaign_id).join(Contact, Contact.id == r.contact_id)
         .where(Campaign.channel == "voice", Contact.phone == phones.from_wa_id(wa_id), r.followup_status == "sent")
         .order_by(r.followup_sent_at.desc()).limit(20))
    if since is not None:
        q = q.where(r.followup_sent_at >= since)
    if unanswered:
        q = q.where(r.replied_at.is_(None))
    # La cuenta esta en el JSON del seguimiento: se compara aca, no en SQL (portable).
    return [(row, c) for row, c in s.execute(q).all() if (c.followup or {}).get("account_id") == account_id]


def reply_target(s: Session, account_id: str, wa_id: str, now: datetime.datetime) -> ReplyTarget | None:
    """El ultimo envio de una campaña de esta cuenta a este contacto, sin responder y dentro
    de WA_CAMPAIGN_REPLY_DAYS: su respuesta abre la conversacion con la plantilla. Puede ser la
    plantilla de una campaña de WhatsApp o el seguimiento de una de voz: gana la mas reciente."""
    since = now - datetime.timedelta(days=settings.wa_campaign_reply_days)
    r = CampaignContact
    row = s.execute(
        select(r, Campaign)
        .join(Campaign, Campaign.id == r.campaign_id)
        .join(Contact, Contact.id == r.contact_id)
        .where(Campaign.account_id == account_id, Contact.phone == phones.from_wa_id(wa_id),
               r.status == "done", r.result == "sent", r.replied_at.is_(None), r.sent_at >= since)
        .order_by(r.sent_at.desc()).limit(1)).first()
    target = None
    if row is not None:
        recipient, campaign = row
        target = ReplyTarget(recipient_id=recipient.id, campaign_id=campaign.id, agent_id=campaign.agent_id,
                             opening=render(campaign.template_body, recipient.params), sent_at=recipient.sent_at)
    for recipient, campaign in _followup_sent(s, account_id, wa_id, since, unanswered=True)[:1]:
        if target is None or recipient.followup_sent_at > target.sent_at:
            f = campaign.followup or {}
            target = ReplyTarget(recipient_id=recipient.id, campaign_id=campaign.id,
                                 agent_id=f.get("agent_id") or campaign.agent_id,
                                 opening=render(f.get("template_body") or "", followup_values(campaign, recipient)),
                                 sent_at=recipient.followup_sent_at)
    return target


def mark_replied(s: Session, recipient_id: str, conversation_id: str | None, at: datetime.datetime) -> None:
    """Registra la respuesta. En el seguimiento de una campaña de voz, la conversacion va aparte
    (`followup_conversation_id`): `conversation_id` sigue siendo la del ultimo intento de llamada."""
    recipient = s.get(CampaignContact, recipient_id)
    if recipient is None or recipient.replied_at is not None:
        return
    recipient.replied_at = at
    campaign = s.get(Campaign, recipient.campaign_id)
    if campaign is not None and campaign.channel == "voice":
        recipient.followup_conversation_id = conversation_id
    else:
        recipient.conversation_id = conversation_id


def is_campaign_conversation(s: Session, conversation_id: str) -> bool:
    """Si la conversacion la abrio la respuesta a una campaña (su agente no se pisa con una
    regla de ruteo por contacto mientras siga abierta)."""
    return s.scalar(select(CampaignContact.id)
                    .where(or_(CampaignContact.conversation_id == conversation_id,
                               CampaignContact.followup_conversation_id == conversation_id)).limit(1)) is not None


def is_optout_text(text: str) -> bool:
    norm = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()
    norm = re.sub(r"[^a-z0-9 ]+", " ", norm)
    return re.sub(r"\s+", " ", norm).strip() in OPTOUT_TEXTS


def got_campaign(s: Session, account_id: str, wa_id: str) -> bool:
    """Si este numero le mando alguna campaña al contacto, o el seguimiento de una de voz (la baja
    por texto solo vale ahi)."""
    return s.scalar(
        select(CampaignContact.id).join(Campaign, Campaign.id == CampaignContact.campaign_id)
        .join(Contact, Contact.id == CampaignContact.contact_id)
        .where(Campaign.account_id == account_id, Contact.phone == phones.from_wa_id(wa_id),
               CampaignContact.status == "done", CampaignContact.result == "sent").limit(1)) is not None \
        or bool(_followup_sent(s, account_id, wa_id))


# La baja de WhatsApp es un contact_optouts del canal whatsapp; el wa_id es el E.164 sin el +.

def is_opted_out(s: Session, client_id: str, wa_id: str) -> bool:
    return contacts.is_opted_out(s, client_id, phones.from_wa_id(wa_id), CHANNEL)


def add_optout(s: Session, client_id: str, wa_id: str, source: str) -> ContactOptout:
    return contacts.add_optout(s, client_id, phones.from_wa_id(wa_id), CHANNEL, source)


def remove_optout(s: Session, client_id: str, wa_id: str) -> None:
    contacts.remove_optout(s, client_id, phones.from_wa_id(wa_id), CHANNEL)


def list_optouts(s: Session, client_id: str | None) -> list[ContactOptout]:
    return contacts.list_optouts(s, client_id, CHANNEL)
