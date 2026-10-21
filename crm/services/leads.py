"""Leads: normalizacion, alta o actualizacion por dominio, etapa y blocklist."""
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import STAGES, Activity, Block, ContactPoint, Lead, Person, Source
from .errors import Invalid

EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


# Hosts compartidos: una pagina ahi no identifica a la empresa (no sirven de clave de dedupe).
SHARED_HOSTS = {"facebook.com", "instagram.com", "linkedin.com", "linktr.ee", "wa.me", "sites.google.com",
                "google.com", "x.com", "twitter.com", "youtube.com", "wixsite.com", "blogspot.com",
                "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.ar"}


def norm_domain(value: str | None) -> str | None:
    """`https://www.Empresa.com.ar/contacto` -> `empresa.com.ar`. Hosts compartidos -> None."""
    if not value:
        return None
    v = value.strip().lower()
    v = re.sub(r"^[a-z]+://", "", v).split("/")[0].split("?")[0].split(":")[0]
    v = v.removeprefix("www.").removeprefix("m.")
    if not v or v in SHARED_HOSTS or any(v.endswith("." + h) for h in SHARED_HOSTS):
        return None
    return v


def norm_value(kind: str, value: str) -> str:
    v = value.strip()
    if kind == "email":
        v = v.lower()
        if not EMAIL.match(v):
            raise Invalid(f"email invalido: {value!r}", field="value")
    elif kind in ("phone", "whatsapp"):
        digits = re.sub(r"[^\d+]", "", v)
        if len(re.sub(r"\D", "", digits)) < 6:
            raise Invalid(f"telefono invalido: {value!r}", field="value")
        v = digits
    return v


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "lead"


def unique_slug(s: Session, base: str) -> str:
    slug, n = base, 2
    while s.scalar(select(Lead.id).where(Lead.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def is_blocked(s: Session, email: str) -> Block | None:
    email = email.lower()
    domain = email.split("@")[-1]
    return s.scalar(select(Block).where(Block.value.in_([email, domain])))


def block(s: Session, value: str, reason: str, note: str | None = None) -> Block:
    value = value.strip().lower()
    b = s.scalar(select(Block).where(Block.value == value))
    if not b:
        b = Block(value=value, reason=reason, note=note)
        s.add(b)
        s.flush()
    return b


def set_stage(s: Session, lead: Lead, stage: str, by: str = "usuario", note: str | None = None) -> bool:
    if stage not in STAGES:
        raise Invalid(f"etapa desconocida: {stage}", field="stage")
    if lead.stage == stage:
        return False
    s.add(Activity(lead_id=lead.id, kind="stage_change", text=note or f"{lead.stage} → {stage}",
                   data={"from": lead.stage, "to": stage}, created_by=by))
    lead.stage, lead.stage_changed_at = stage, utcnow()
    return True


def primary_email(lead: Lead) -> ContactPoint | None:
    emails = [c for c in lead.contacts if c.kind == "email" and c.status == "ok"]
    return next((c for c in emails if c.is_primary), emails[0] if emails else None)


def add_source(s: Session, lead: Lead, url: str | None, seen_at=None, title=None, note=None) -> Source | None:
    if not url:
        return None
    src = next((x for x in lead.sources if x.url == url), None)
    if not src:
        src = Source(lead_id=lead.id, url=url, seen_at=seen_at, title=title, note=note)
        s.add(src)
        lead.sources.append(src)
        s.flush()
    return src


def add_person(s: Session, lead: Lead, data: dict) -> Person:
    name = data["name"].strip()
    p = next((x for x in lead.people if x.name.lower() == name.lower()), None)
    src = add_source(s, lead, data.get("source_url"), data.get("source_seen_at"))
    if not p:
        p = Person(lead_id=lead.id, name=name)
        s.add(p)
        lead.people.append(p)
    for f in ("title", "is_decision_maker", "linkedin_url", "notes"):
        if data.get(f) is not None:
            setattr(p, f, data[f])
    if src:
        p.source_id = src.id
    s.flush()
    return p


def add_contact(s: Session, lead: Lead, data: dict, require_source: bool) -> ContactPoint:
    kind = data["kind"]
    value = norm_value(kind, data["value"])
    if require_source and not data.get("source_url") and kind in ("email", "phone", "whatsapp"):
        raise Invalid(f"{value}: falta source_url (solo datos publicados, con su fuente)",
                      field="source_url")
    src = add_source(s, lead, data.get("source_url"), data.get("source_seen_at"))
    c = next((x for x in lead.contacts if x.kind == kind and x.value == value), None)
    if not c:
        c = ContactPoint(lead_id=lead.id, kind=kind, value=value)
        s.add(c)
        lead.contacts.append(c)
    for f in ("label", "verified_at", "status"):
        if data.get(f) is not None:
            setattr(c, f, data[f])
    if kind == "email" and is_blocked(s, value):
        c.status = "bounced"
    if data.get("person"):
        c.person_id = add_person(s, lead, {"name": data["person"]}).id
    if src:
        c.source_id = src.id
    if data.get("is_primary"):
        for other in lead.contacts:
            if other.kind == kind:
                other.is_primary = other is c
    s.flush()
    return c


LEAD_FIELDS = ("name", "legal_name", "website", "description", "kind", "industry", "country",
               "province", "city", "next_action", "next_action_at", "do_not_contact", "notes",
               "legacy_ref")


def upsert(s: Session, data: dict, by: str, require_source: bool) -> tuple[Lead, bool]:
    """Alta o actualizacion por dominio (o por slug si no tiene web). Suma personas, contactos y
    fuentes sin borrar lo que ya estaba. Devuelve (lead, creado)."""
    domain = norm_domain(data.get("domain") or data.get("website"))
    lead = None
    if domain:
        lead = s.scalar(select(Lead).where(Lead.domain == domain))
    if not lead and data.get("slug"):
        lead = s.scalar(select(Lead).where(Lead.slug == data["slug"]))
    created = lead is None
    if created:
        if not data.get("name"):
            raise Invalid("falta name", field="name")
        slug = data.get("slug") or unique_slug(s, slugify(data["name"]))
        lead = Lead(slug=slug, name=data["name"], domain=domain, created_by=by, tags=[],
                    stage=data.get("stage") or "nuevo")
        s.add(lead)
        s.flush()
    elif domain and not lead.domain:
        lead.domain = domain
    for f in LEAD_FIELDS:
        if data.get(f) is not None:
            setattr(lead, f, data[f])
    if data.get("tags"):
        lead.tags = sorted(set(lead.tags or []) | set(data["tags"]))
    for src in data.get("sources") or []:
        add_source(s, lead, src["url"], src.get("seen_at"), src.get("title"), src.get("note"))
    for p in data.get("people") or []:
        add_person(s, lead, p)
    for c in data.get("contacts") or []:
        add_contact(s, lead, c, require_source)
    if not created and data.get("stage") and data["stage"] != lead.stage:
        set_stage(s, lead, data["stage"], by)
    s.flush()
    return lead, created
