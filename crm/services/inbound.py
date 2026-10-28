"""Respuestas por mail (docs/features/CRM.md).

Cloudflare reenvia la casilla a Resend Receiving (subdominio); este loop lee los recibidos cada
CRM_INBOUND_INTERVAL_SECONDS, los asocia a un lead (hilo, direccion, dominio), los clasifica con el LLM
local y aplica al lead lo que corresponde segun la intencion (la etapa la decide este codigo, no el LLM).
Sin lead queda en la bandeja "sin asignar". Cada respuesta real se avisa por mail a CRM_NOTIFY_TO.

LLM (scratch/crm-inbound/, 22-oct-2026, Gemma 4 26B): con el JSON forzado por esquema se colgaba en
espacios (3 de 5); con el JSON pedido en el prompt, 8 de 9 bien, 0,5 a 0,9 s y ~100 tokens.
"""
import asyncio
import datetime
import html
import json
import logging
import re
import time

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import local_today, settings
from ..db import get_sessionmaker, naive_utc, utcnow
from ..models import Activity, ContactPoint, InboundEmail, Lead, Message
from . import leads as L
from . import messages as M
from . import reminders as R
from . import resend

logger = logging.getLogger(__name__)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
FREE_MAIL = {"gmail.com", "hotmail.com", "outlook.com", "live.com", "yahoo.com", "yahoo.com.ar",
             "icloud.com", "hotmail.com.ar", "outlook.com.ar", "live.com.ar", "fibertel.com.ar"}
# Donde empieza el mail citado: "El jue, 22 oct 2026 a las 10:00, X (<x@y>) escribió:" (a veces en dos
# lineas), "On ... wrote:", "-----Mensaje original-----", o un bloque "De: ...".
QUOTE = re.compile(r"\n\s*(?:(?:El|On)\s[^\n]*(?:\n[^\n]*)?(?:escribi[oó]|wrote):|-{3,}\s*(?:Mensaje original|"
                   r"Original Message)|_{5,}|De:\s[^\n]+\n\s*(?:Enviado|Fecha|Sent):|From:\s[^\n]+\n\s*(?:Sent|Date):)",
                   re.IGNORECASE)

INTENTS = {
    "interesado": "Interesado", "agendar": "Quiere hablar", "pide_info": "Pide información",
    "derivado": "Deriva a otra persona", "mas_adelante": "Más adelante", "no_interesa": "No le interesa",
    "baja": "Pide la baja", "autorespuesta": "Autorespuesta", "otro": "Otro",
}

SYSTEM = """Clasificás la respuesta de una empresa a un mail de prospección de Atentina (agentes de voz con IA). Hoy es {hoy}.
Devolvé SOLO un objeto JSON en una línea, sin texto ni markdown, con estas claves:
- "intencion": una de
  "interesado" (quiere avanzar o saber más), "agendar" (propone o acepta día y hora para hablar),
  "pide_info" (hace una pregunta o pide material), "derivado" (indica otra persona o email para hablar),
  "mas_adelante" (ahora no, pero deja la puerta abierta), "no_interesa" (no le interesa, sin pedir la baja),
  "baja" (pide explícitamente no recibir más mails), "autorespuesta" (fuera de oficina, acuse automático), "otro".
- "resumen": una frase en español.
- "proxima_accion": qué debería hacer Laureano, una frase corta, o "".
- "fecha": fecha y hora ISO que proponen o hasta cuándo no están, o "".
- "contacto_nombre", "contacto_cargo", "contacto_email": la persona a la que derivan, o "".
- "confianza": de 0 a 1."""


# --- Texto y encabezados ---

def email_of(value: str | None) -> str:
    m = EMAIL.search(value or "")
    return m.group(0).lower() if m else ""


def html_to_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", h)
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


def strip_quoted(text: str) -> str:
    """Solo lo que escribio: sin el mail citado ni las lineas con '>'."""
    m = QUOTE.search("\n" + text)
    if m:
        text = ("\n" + text)[:m.start()]
    lines = [x for x in text.splitlines() if not x.lstrip().startswith(">")]
    return "\n".join(lines).strip()


def norm_headers(h) -> dict:
    """Encabezados con nombre en minuscula; Resend los da como objeto (o lista de {name, value})."""
    if isinstance(h, list):
        h = {x.get("name", ""): x.get("value", "") for x in h if isinstance(x, dict)}
    out = {}
    for k, v in (h or {}).items():
        out[str(k).lower()] = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
    return out


def is_auto(headers: dict) -> bool:
    """Autorespuesta por encabezados (RFC 3834 y los de Exchange)."""
    return (headers.get("auto-submitted", "no").lower() != "no" or "x-autoreply" in headers
            or "x-autorespond" in headers or headers.get("precedence", "").lower() in ("auto_reply", "bulk", "junk")
            or headers.get("x-auto-response-suppress", "").lower() in ("all", "oof"))


# --- Asociar ---

def match(s: Session, headers: dict, from_email: str) -> tuple[Lead | None, str]:
    """El lead de una respuesta: por el hilo (In-Reply-To/References contra lo que mandamos), por la
    direccion del remitente o por su dominio (si no es de correo gratuito)."""
    ids = re.findall(r"<[^<>\s]+>", f"{headers.get('in-reply-to', '')} {headers.get('references', '')}")
    if ids:
        m = s.scalar(select(Message).where(Message.direction == "out", Message.message_id.in_(ids))
                     .order_by(Message.sent_at.desc()))
        if m:
            return m.lead, "hilo"
    if from_email:
        leads = set(s.scalars(select(ContactPoint.lead_id).where(
            ContactPoint.kind == "email", func.lower(ContactPoint.value) == from_email)))
        if len(leads) == 1:
            return s.get(Lead, leads.pop()), "dirección"
        domain = from_email.split("@")[1]
        lead = s.scalar(select(Lead).where(Lead.domain == domain)) if domain not in FREE_MAIL else None
        if lead:
            return lead, "dominio"
    return None, "sin match"


def ignore_reason(from_email: str) -> str | None:
    local, _, domain = from_email.partition("@")
    own = {d.strip().lower() for d in settings.own_domains.split(",") if d.strip()}
    if not from_email:
        return "sin remitente"
    if domain in own or any(domain.endswith("." + d) for d in own):
        return "copia nuestra"
    if local in ("mailer-daemon", "postmaster") or local.startswith("bounce"):
        return "rebote (lo ven los eventos)"
    return None


# --- LLM ---

def classify(subject: str, text: str) -> dict:
    """Intencion y datos de la respuesta, del LLM local. Lanza si no responde o no devuelve el JSON."""
    if not settings.llm_model:
        raise RuntimeError("sin CRM_LLM_MODEL / VLLM_LLM_MODEL")
    body = {"model": settings.llm_model, "temperature": 0, "max_tokens": 400,
            "messages": [{"role": "system", "content": SYSTEM.format(hoy=local_today().isoformat())},
                         {"role": "user", "content": f"Asunto: {subject}\n\n{text[:4000]}"}]}
    r = httpx.post(f"{settings.llm_url}/chat/completions", json=body, timeout=60,
                   headers={"Authorization": f"Bearer {settings.llm_api_key}"})
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"sin JSON: {raw[:200]}")
    a = json.loads(m.group(0))
    if a.get("intencion") not in INTENTS:
        raise ValueError(f"intencion desconocida: {a.get('intencion')}")
    out = {k: str(a.get(k) or "").strip() for k in ("intencion", "resumen", "proxima_accion", "fecha",
                                                     "contacto_nombre", "contacto_cargo", "contacto_email")}
    try:
        out["confianza"] = max(0.0, min(1.0, float(a.get("confianza", 0))))
    except (TypeError, ValueError):
        out["confianza"] = 0.0
    return out


def _date(value: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _has_time(value: str) -> bool:
    """'2026-10-27T11:00' si; '2026-10-27' o medianoche (el LLM la pone cuando no dicen hora), no."""
    try:
        return len(value) > 10 and datetime.datetime.fromisoformat(value).time() != datetime.time(0)
    except ValueError:
        return False


def apply(s: Session, lead: Lead, a: dict, from_email: str) -> list[str]:
    """Lo que la intencion cambia en el lead, ademas de lo que ya hizo record_inbound. Devuelve que se hizo."""
    done = []
    intent, when = a["intencion"], _date(a["fecha"])
    if intent in ("no_interesa", "baja") and L.set_stage(s, lead, "no_interesa", "sistema",
                                                          f"{lead.stage} → no_interesa (respuesta)"):
        done.append("etapa: no le interesa")
    if intent == "baja":
        lead.do_not_contact = True
        if from_email:
            L.block(s, from_email, "opt_out", "pidió la baja respondiendo")
        done.append("no contactar y a la blocklist")
    if intent == "derivado":
        email = email_of(a["contacto_email"])
        name = a["contacto_nombre"]
        if email:
            L.add_contact(s, lead, {"kind": "email", "value": email, "label": "persona" if name else "area",
                                    "person": name or None}, require_source=False)
            done.append(f"contacto nuevo: {email}")
        elif name:
            L.add_person(s, lead, {"name": name})
            done.append(f"persona nueva: {name}")
        if name and a["contacto_cargo"]:
            L.add_person(s, lead, {"name": name, "title": a["contacto_cargo"]})
    if a["proxima_accion"] and intent not in ("no_interesa", "baja"):
        day = when or (local_today() + datetime.timedelta(days=90) if intent == "mas_adelante" else local_today())
        if settings.reminders_from_replies:
            # Con hora ("el martes a las 11") a esa hora; si no, a la de CRM_REMINDER_HOUR
            at = a["fecha"] if when and _has_time(a["fecha"]) else day.isoformat()
            r = R.create(s, lead, {"starts_at": at, "title": a["proxima_accion"],
                                   "notes": f"De la respuesta: {a['resumen']}"}, "sistema")
            done.append(f"recordatorio: {r.title} ({at.replace('T', ' ')[:16]})")
        else:
            lead.next_action, lead.next_action_at = a["proxima_accion"][:500], day
            done.append(f"próxima acción: {lead.next_action} ({day.isoformat()})")
    return done


# --- Procesar ---

def ingest(s: Session, data: dict) -> InboundEmail:
    """Guarda un recibido de Resend y lo procesa: lo ignora, lo deja sin asignar o lo asigna a su lead."""
    headers = norm_headers(data.get("headers"))
    text = data.get("text") or html_to_text(data.get("html") or "")
    to = data.get("to") or []
    ib = InboundEmail(resend_id=data["id"], from_addr=(data.get("from") or "")[:300],
                      to_addr=(", ".join(to) if isinstance(to, list) else str(to))[:300],
                      subject=(data.get("subject") or "")[:300], text=text, headers=headers,
                      received_at=naive_utc(datetime.datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")))
                      if data.get("created_at") else utcnow(), status="unassigned")
    s.add(ib)
    from_email = email_of(ib.from_addr)
    reason = ignore_reason(from_email)
    if reason:
        ib.status, ib.reason = "ignored", reason
        s.flush()
        return ib
    lead, how = match(s, headers, from_email)
    if not lead:
        ib.reason = how
        s.flush()
        notify(ib, None, None)
        return ib
    handle(s, ib, lead, how)
    return ib


def handle(s: Session, ib: InboundEmail, lead: Lead, how: str) -> Message:
    """Registra la respuesta en el lead, la clasifica, aplica la intencion y avisa."""
    from_email = email_of(ib.from_addr)
    auto = is_auto(ib.headers or {})
    analysis: dict = {"status": "ok"}
    own = strip_quoted(ib.text) or ib.text
    if not auto:
        try:
            analysis |= classify(ib.subject, own)
        except Exception as e:  # noqa: BLE001 - sin LLM la respuesta se registra igual
            logger.warning("crm: no se pudo clasificar la respuesta %s: %s", ib.resend_id, e)
            analysis = {"status": "error", "error": str(e)[:300]}
        auto = analysis.get("intencion") == "autorespuesta"
    else:
        analysis |= {"intencion": "autorespuesta", "resumen": "Autorespuesta (por encabezados).", "confianza": 1.0}
    m = M.record_inbound(s, lead, from_addr=ib.from_addr, subject=ib.subject or "(sin asunto)", text=ib.text,
                         at=ib.received_at, by="sistema", auto=auto)
    m.resend_id = ib.resend_id
    applied: list[str] = []
    if analysis["status"] == "ok":
        if auto:
            when = _date(analysis.get("fecha", ""))
            if when:
                lead.next_action, lead.next_action_at = "Volver a escribir: estaba fuera de la oficina", when
                applied.append(f"próxima acción el {when.isoformat()}")
        elif analysis["confianza"] < settings.llm_min_confidence or analysis["intencion"] == "otro":
            analysis["status"] = "low_confidence"
        else:
            applied = apply(s, lead, analysis, from_email)
    analysis["applied"] = applied
    analysis["matched_by"] = how
    m.analysis = analysis
    ib.status, ib.reason, ib.lead_id = "assigned", how, lead.id
    s.flush()
    ib.message_id = m.id
    label = INTENTS.get(analysis.get("intencion", ""), "sin analizar")
    note = {"ok": f"Respuesta clasificada por el LLM: {label}.",
            "low_confidence": f"Respuesta: el LLM no está seguro ({label}); revisarla.",
            "error": "Respuesta sin analizar (el LLM no respondió)."}[analysis["status"]]
    if analysis.get("resumen"):
        note += f" {analysis['resumen']}"
    if applied:
        note += " Aplicado: " + "; ".join(applied) + "."
    s.add(Activity(lead_id=lead.id, kind="note", text=note, data={"message_id": m.id}, created_by="sistema"))
    s.flush()
    if not auto:
        notify(ib, lead, analysis)
    return m


def notify(ib: InboundEmail, lead: Lead | None, analysis: dict | None) -> None:
    """Aviso a CRM_NOTIFY_TO. Va directo (no por la cola de prospeccion ni su tope diario). Si falla, se loguea."""
    if not settings.notify_to:
        return
    a = analysis or {}
    label = INTENTS.get(a.get("intencion", ""), "sin analizar")
    if lead:
        subject = f"Respondió {lead.name}: {label}"
        link = f"{settings.crm_url}/#/leads/{lead.id}"
    else:
        subject = f"Respuesta sin asignar de {email_of(ib.from_addr) or ib.from_addr}"
        link = f"{settings.crm_url}/#/"
    lines = [f"De: {ib.from_addr}", f"Asunto: {ib.subject}"]
    if a.get("resumen"):
        lines.append(f"Resumen: {a['resumen']}")
    if a.get("status") == "low_confidence":
        lines.append("El LLM no está seguro: revisala.")
    if a.get("status") == "error":
        lines.append("Sin analizar: el LLM no respondió.")
    if a.get("applied"):
        lines.append("Aplicado: " + "; ".join(a["applied"]))
    if not lead:
        lines.append("No se encontró el lead: asignala desde el Tablero.")
    text = "\n".join(lines) + f"\n\n{link}\n\n---\n\n{strip_quoted(ib.text) or ib.text}"
    try:
        resend.send(idempotency_key=f"crm-aviso-{ib.resend_id}", from_addr=settings.mail_from,
                    to=settings.notify_to, subject=subject[:300], text=text, in_reply_to=None, bcc=None)
    except resend.ResendError as e:
        logger.warning("crm: aviso de respuesta %s: %s", ib.resend_id, e)


def assign(s: Session, ib: InboundEmail, lead: Lead) -> Message:
    """Una de la bandeja "sin asignar", a mano: se procesa como si se hubiera encontrado el lead."""
    return handle(s, ib, lead, "a mano")


def poll(s: Session) -> int:
    """Lee los recibidos nuevos de Resend (del mas viejo al mas nuevo) y los procesa. Devuelve cuantos."""
    seen = set(s.scalars(select(InboundEmail.resend_id)))
    new, after = [], None
    for _ in range(10):
        d = resend.list_received(after)
        batch = d.get("data") or []
        fresh = [x for x in batch if x["id"] not in seen]
        new += fresh
        if len(fresh) < len(batch) or not d.get("has_more") or not batch:
            break
        after = batch[-1]["id"]
    n = 0
    for i, x in enumerate(sorted(new, key=lambda x: x.get("created_at") or "")):
        if i:
            time.sleep(0.6)   # Resend: 2 pedidos por segundo
        try:
            ingest(s, resend.get_received(x["id"]))
            s.commit()
            n += 1
        except Exception:
            s.rollback()
            logger.exception("crm: recibido %s", x["id"])
    return n


async def inbound_loop() -> None:
    while True:
        try:
            with get_sessionmaker()() as s:
                n = await asyncio.to_thread(poll, s)
                if n:
                    logger.info("crm: %s mails recibidos", n)
        except Exception:
            logger.exception("crm: recibidos de Resend")
        await asyncio.sleep(settings.inbound_interval_seconds)
