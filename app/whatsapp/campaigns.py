"""Campañas salientes de WhatsApp (docs/WHATSAPP_PLAN.md, 5.5): una plantilla aprobada a
una lista de contactos, por un numero conectado. El envio lo hace sender.py, de a poco
(ritmo por minuto) y dentro del horario de la campaña.

- Contactos: por API (lista) o CSV. El telefono se normaliza al wa_id que manda Meta
  (Argentina: 549 + 10 digitos); los repetidos, invalidos o dados de baja no entran.
- Plantilla: se lee de Meta al crear la campaña y se guarda una copia del cuerpo. Solo
  variables en el cuerpo ({{1}}..{{n}}): encabezado de texto fijo, pie y botones fijos.
- Respuesta: el primer mensaje del contacto abre la conversacion con el cuerpo de la
  plantilla (con sus variables) como apertura, con el agente de la campaña o el del
  numero (service.py, _turn).
- Baja: un contacto de una campaña que escribe "baja", "no me interesa" o toca el boton
  de ese texto queda en wa_optouts del cliente y ninguna campaña le vuelve a escribir.

Funciones sincronicas con la Session del que llama; el commit lo hace el que llama.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import (
    Agent,
    WaAccount,
    WaCampaign,
    WaCampaignRecipient,
    WaMessage,
    WaOptout,
)
from ..services.errors import Conflict, Invalid, NotFound
from . import signup, store

PLACEHOLDER_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")
STATUSES = ("draft", "running", "paused", "done", "cancelled")
# Columnas del CSV (encabezado, sin importar mayusculas ni acentos).
PHONE_COLUMNS = {"telefono", "phone", "numero", "celular", "whatsapp", "wa_id", "movil"}
NAME_COLUMNS = {"nombre", "name"}
# Lo que se toma como pedido de baja: el mensaje entero, normalizado (sin acentos ni signos).
OPTOUT_TEXTS = {
    "baja", "stop", "no me interesa", "no gracias", "no me escriban", "no me escriban mas", "no me escribas",
    "no me escribas mas", "dar de baja", "darme de baja", "quiero darme de baja", "no quiero recibir mas mensajes",
    "no molestar", "basta", "desuscribir", "detener promociones", "stop promotions",
}


# --- Telefonos ---

def normalize_phone(raw: str) -> str:
    """El wa_id de un telefono, como lo manda Meta en los entrantes. ValueError si no se
    reconoce. Argentina sin codigo de pais (351 555-1234, 0351 5551234) o con 54 / 549;
    otro pais, con + o 00 adelante."""
    text = (raw or "").strip()
    international = text.startswith(("+", "00"))
    digits = re.sub(r"\D", "", text)
    if text.startswith("00"):
        digits = digits[2:]
    if not digits:
        raise ValueError("sin número")
    if digits.startswith("54") and (international or len(digits) in (12, 13)):
        national = digits[3:] if digits.startswith("549") else digits[2:]
        if len(national) != 10:
            raise ValueError("número argentino con largo inválido (código de área + número: 10 dígitos)")
        return "549" + national
    if international:
        if not 8 <= len(digits) <= 15:
            raise ValueError("número internacional con largo inválido")
        return digits
    digits = digits.removeprefix("0")
    if len(digits) == 10:
        return "549" + digits
    raise ValueError("formato no reconocido: código de área + número sin el 15 (351 555-1234), o +54 9 ...")


# --- Plantilla ---

def body_params(body: str) -> int:
    return len({int(n) for n in PLACEHOLDER_RE.findall(body)})


def render(body: str, params: list[str]) -> str:
    """El cuerpo con sus variables, como lo ve el contacto."""
    def sub(m: re.Match) -> str:
        i = int(m.group(1)) - 1
        return params[i] if 0 <= i < len(params) else m.group(0)
    return PLACEHOLDER_RE.sub(sub, body)


def clean_param(value: str) -> str:
    """Meta rechaza variables con saltos de linea, tabs o mas de 4 espacios seguidos."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


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


def _key(header: str) -> str:
    text = unicodedata.normalize("NFD", header or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_]", "", text.lower())


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


@dataclass
class Skipped:
    phone: str
    reason: str
    line: int | None = None


def add_recipients(s: Session, campaign: WaCampaign, rows: list[Row]) -> tuple[int, list[Skipped]]:
    """Suma contactos a una campaña en borrador o pausada. Se saltean los invalidos, los
    repetidos (en la lista o ya cargados), los dados de baja y los que no completan las
    variables de la plantilla. Las variables de mas se ignoran."""
    if campaign.status not in ("draft", "paused"):
        raise Conflict("Solo se suman contactos a una campaña en borrador o pausada")
    total = s.scalar(select(func.count()).select_from(WaCampaignRecipient)
                     .where(WaCampaignRecipient.campaign_id == campaign.id)) or 0
    existing = set(s.scalars(select(WaCampaignRecipient.wa_id).where(WaCampaignRecipient.campaign_id == campaign.id)))
    optouts = set(s.scalars(select(WaOptout.wa_id).where(WaOptout.client_id == campaign.client_id)))
    added, skipped = 0, []
    for row in rows:
        try:
            wa_id = normalize_phone(row.phone)
        except ValueError as e:
            skipped.append(Skipped(row.phone, str(e), row.line))
            continue
        params = [clean_param(p) for p in row.params][:campaign.template_params]
        if wa_id in existing:
            skipped.append(Skipped(row.phone, "repetido", row.line))
        elif wa_id in optouts:
            skipped.append(Skipped(row.phone, "pidió la baja", row.line))
        elif len(params) < campaign.template_params or not all(params):
            skipped.append(Skipped(row.phone, f"la plantilla tiene {campaign.template_params} variables: "
                                              f"faltan valores", row.line))
        elif total + added >= settings.wa_campaign_max_recipients:
            skipped.append(Skipped(row.phone, f"tope de {settings.wa_campaign_max_recipients} contactos "
                                              f"por campaña", row.line))
        else:
            s.add(WaCampaignRecipient(campaign_id=campaign.id, wa_id=wa_id, params=params,
                                      name=(row.name or None) and clean_param(row.name)[:128]))
            existing.add(wa_id)
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
           rate_per_minute: int, window_start: int, window_end: int, created_by: str | None) -> WaCampaign:
    check_agent(s, account.client_id, agent_id)
    check_window(window_start, window_end)
    campaign = WaCampaign(client_id=account.client_id, account_id=account.id, agent_id=agent_id, name=name.strip(),
                          template_name=template.name, template_language=template.language,
                          template_category=template.category, template_body=template.body,
                          template_params=template.params, status="draft", rate_per_minute=rate_per_minute,
                          window_start=window_start, window_end=window_end, created_by=created_by)
    s.add(campaign)
    s.flush()
    return campaign


def check_window(start: int, end: int) -> None:
    if not (0 <= start < end <= 24):
        raise Invalid("Horario inválido: la hora de inicio tiene que ser menor que la de fin")


EDITABLE = ("name", "agent_id", "rate_per_minute", "window_start", "window_end")


def update(s: Session, campaign: WaCampaign, **changes) -> WaCampaign:
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


def pending_count(s: Session, campaign_id: str) -> int:
    return s.scalar(select(func.count()).select_from(WaCampaignRecipient).where(
        WaCampaignRecipient.campaign_id == campaign_id, WaCampaignRecipient.status == "pending")) or 0


def start(s: Session, campaign: WaCampaign, account: WaAccount) -> None:
    if campaign.status not in ("draft", "paused"):
        raise Conflict("Solo se inicia una campaña en borrador o pausada")
    if not account.active or account.status != "connected":
        raise Conflict("El número de WhatsApp de la campaña no está activo y conectado")
    if campaign.agent_id is not None:
        agent = s.get(Agent, campaign.agent_id)
        if agent is None or agent.archived_at is not None:
            raise Conflict("El agente de la campaña está archivado: elegí otro")
    if pending_count(s, campaign.id) == 0:
        raise Conflict("La campaña no tiene contactos pendientes")
    campaign.status, campaign.status_reason = "running", None
    campaign.started_at = campaign.started_at or utcnow()
    s.flush()


def pause(s: Session, campaign: WaCampaign, reason: str | None = None) -> None:
    if campaign.status != "running":
        raise Conflict("La campaña no está en curso")
    campaign.status, campaign.status_reason = "paused", reason[:255] if reason else None
    s.flush()


def cancel(s: Session, campaign: WaCampaign) -> None:
    """Termina la campaña: los pendientes quedan salteados. Las respuestas siguen llegando."""
    if campaign.status in ("done", "cancelled"):
        raise Conflict("La campaña ya terminó")
    for r in s.scalars(select(WaCampaignRecipient).where(WaCampaignRecipient.campaign_id == campaign.id,
                                                         WaCampaignRecipient.status == "pending")):
        r.status, r.error = "skipped", {"message": "Campaña cancelada"}
    campaign.status, campaign.finished_at = "cancelled", utcnow()
    s.flush()


def delete(s: Session, campaign: WaCampaign) -> None:
    if campaign.status != "draft":
        raise Conflict("Solo se borra una campaña en borrador; si ya empezó, cancelala")
    s.delete(campaign)
    s.flush()


def list_campaigns(s: Session, client_id: str | None = None, account_id: str | None = None) -> list[WaCampaign]:
    q = select(WaCampaign).order_by(WaCampaign.created_at.desc())
    if client_id is not None:
        q = q.where(WaCampaign.client_id == client_id)
    if account_id is not None:
        q = q.where(WaCampaign.account_id == account_id)
    return list(s.scalars(q))


# --- Estado de cada contacto y totales ---

STATS_KEYS = ("total", "pending", "sent", "delivered", "read", "replied", "failed", "skipped", "opted_out")


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
    q = (select(WaCampaignRecipient.campaign_id, WaCampaignRecipient.status, WaMessage.status,
                WaCampaignRecipient.replied_at.is_not(None), WaOptout.wa_id.is_not(None), func.count())
         .join(WaCampaign, WaCampaign.id == WaCampaignRecipient.campaign_id)
         .outerjoin(WaMessage, WaMessage.wamid == WaCampaignRecipient.wamid)
         .outerjoin(WaOptout, (WaOptout.client_id == WaCampaign.client_id)
                    & (WaOptout.wa_id == WaCampaignRecipient.wa_id))
         .where(WaCampaignRecipient.campaign_id.in_(campaign_ids))
         .group_by(WaCampaignRecipient.campaign_id, WaCampaignRecipient.status, WaMessage.status,
                   WaCampaignRecipient.replied_at.is_not(None), WaOptout.wa_id.is_not(None)))
    for cid, status, msg_status, replied, opted_out, n in s.execute(q):
        st = out[cid]
        st["total"] += n
        if status in ("pending", "sending"):
            st["pending"] += n
        elif status == "skipped":
            st["skipped"] += n
        elif status == "failed" or msg_status == "failed":
            st["failed"] += n
        else:   # sent
            st["sent"] += n
            if msg_status in ("delivered", "read"):
                st["delivered"] += n
            if msg_status == "read":
                st["read"] += n
        if replied:
            st["replied"] += n
        if opted_out and status == "sent":
            st["opted_out"] += n
    return out


def recipients_page(s: Session, campaign_id: str, status: str | None, offset: int,
                    limit: int) -> tuple[list[tuple[WaCampaignRecipient, WaMessage | None]], int]:
    """Contactos de la campaña con su mensaje (estado de Meta), en orden de carga. status:
    pending, failed, replied... como shown_status (el filtro se aplica en SQL)."""
    q = (select(WaCampaignRecipient, WaMessage)
         .outerjoin(WaMessage, WaMessage.wamid == WaCampaignRecipient.wamid)
         .where(WaCampaignRecipient.campaign_id == campaign_id))
    r, m = WaCampaignRecipient, WaMessage
    sent = (r.status == "sent") & r.replied_at.is_(None)
    filters = {
        "pending": r.status.in_(("pending", "sending")),
        "skipped": r.status == "skipped",
        "failed": (r.status == "failed") | (sent & (m.status == "failed")),
        "sent": sent & ((m.status.is_(None)) | (m.status == "sent")),
        "delivered": sent & (m.status == "delivered"),
        "read": sent & (m.status == "read"),
        "replied": r.replied_at.is_not(None),
    }
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
    """La campaña a la que responde un contacto: la apertura y el agente de la conversacion."""
    recipient_id: str
    campaign_id: str
    agent_id: str | None
    opening: str


def reply_target(s: Session, account_id: str, wa_id: str, now: datetime.datetime) -> ReplyTarget | None:
    """El ultimo envio de una campaña de esta cuenta a este contacto, sin responder y dentro
    de WA_CAMPAIGN_REPLY_DAYS: su respuesta abre la conversacion con la plantilla."""
    since = now - datetime.timedelta(days=settings.wa_campaign_reply_days)
    row = s.execute(
        select(WaCampaignRecipient, WaCampaign)
        .join(WaCampaign, WaCampaign.id == WaCampaignRecipient.campaign_id)
        .where(WaCampaign.account_id == account_id, WaCampaignRecipient.wa_id == wa_id,
               WaCampaignRecipient.status == "sent", WaCampaignRecipient.replied_at.is_(None),
               WaCampaignRecipient.sent_at >= since)
        .order_by(WaCampaignRecipient.sent_at.desc()).limit(1)).first()
    if row is None:
        return None
    recipient, campaign = row
    return ReplyTarget(recipient_id=recipient.id, campaign_id=campaign.id, agent_id=campaign.agent_id,
                       opening=render(campaign.template_body, list(recipient.params or [])))


def mark_replied(s: Session, recipient_id: str, conversation_id: str | None, at: datetime.datetime) -> None:
    recipient = s.get(WaCampaignRecipient, recipient_id)
    if recipient is not None and recipient.replied_at is None:
        recipient.replied_at, recipient.conversation_id = at, conversation_id


def is_optout_text(text: str) -> bool:
    norm = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()
    norm = re.sub(r"[^a-z0-9 ]+", " ", norm)
    return re.sub(r"\s+", " ", norm).strip() in OPTOUT_TEXTS


def got_campaign(s: Session, account_id: str, wa_id: str) -> bool:
    """Si este numero le mando alguna campaña al contacto (la baja por texto solo vale ahi)."""
    return s.scalar(
        select(WaCampaignRecipient.id).join(WaCampaign, WaCampaign.id == WaCampaignRecipient.campaign_id)
        .where(WaCampaign.account_id == account_id, WaCampaignRecipient.wa_id == wa_id,
               WaCampaignRecipient.status == "sent").limit(1)) is not None


def is_opted_out(s: Session, client_id: str, wa_id: str) -> bool:
    return s.get(WaOptout, (client_id, wa_id)) is not None


def add_optout(s: Session, client_id: str, wa_id: str, source: str) -> WaOptout:
    optout = s.get(WaOptout, (client_id, wa_id))
    if optout is None:
        optout = WaOptout(client_id=client_id, wa_id=wa_id, source=source)
        s.add(optout)
        s.flush()
    return optout


def remove_optout(s: Session, client_id: str, wa_id: str) -> None:
    optout = s.get(WaOptout, (client_id, wa_id))
    if optout is None:
        raise NotFound("Ese número no está en la lista de bajas")
    s.delete(optout)
    s.flush()


def list_optouts(s: Session, client_id: str | None) -> list[WaOptout]:
    q = select(WaOptout).order_by(WaOptout.created_at.desc())
    if client_id is not None:
        q = q.where(WaOptout.client_id == client_id)
    return list(s.scalars(q))
