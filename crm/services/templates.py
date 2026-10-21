"""Plantillas: reemplazo de {{variables}}, sin motor de plantillas.

Variables: saludo ("Hola, Pablo:" o "Hola:"), nombre (de pila, o vacio), empresa, link (el sitio
con las UTM del mail). Si el destinatario es una persona con nombre y la plantilla tiene
`body_personal` (tuteo), se usa esa; si no, `body` (a "ustedes").
"""
import re
from urllib.parse import urlencode

from ..config import settings
from ..models import Campaign, ContactPoint, Lead, Template
from .errors import Invalid

VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")
KNOWN = {"saludo", "nombre", "empresa", "link"}


def variables(text: str) -> set[str]:
    return set(VAR.findall(text or ""))


def check(t: Template) -> None:
    unknown = (variables(t.subject) | variables(t.body) | variables(t.body_personal or "")) - KNOWN
    if unknown:
        raise Invalid(f"variables desconocidas: {', '.join(sorted(unknown))} (validas: "
                      f"{', '.join(sorted(KNOWN))})", field="body")


def utm_campaign(campaign: Campaign | None, kind: str) -> str:
    slug = campaign.slug if campaign else "crm"
    if kind == "follow_up":
        # Convencion de octubre: canales4 -> follow_up_canales_4.
        return "follow_up_" + re.sub(r"(\D)(\d+)$", r"\1_\2", slug)
    return slug


def link(lead: Lead, campaign: Campaign | None, kind: str) -> str:
    q = {"utm_source": "email", "utm_campaign": utm_campaign(campaign, kind), "utm_content": lead.slug}
    return settings.site_url + "?" + urlencode(q)


def first_name(contact: ContactPoint | None) -> str:
    if contact and contact.label == "persona" and contact.person and contact.person.name:
        name = re.sub(r"^(cra?\.|dra?\.|lic\.|ing\.|sr\.|sra\.)\s*", "", contact.person.name.strip(),
                      flags=re.IGNORECASE)
        return name.split()[0] if name else ""
    return ""


def render(t: Template, lead: Lead, contact: ContactPoint | None, campaign: Campaign | None,
           kind: str) -> tuple[str, str]:
    """(asunto, texto)."""
    check(t)
    nombre = first_name(contact)
    body = t.body_personal if (nombre and t.body_personal) else t.body
    vals = {"saludo": f"Hola, {nombre}:" if nombre else "Hola:", "nombre": nombre, "empresa": lead.name,
            "link": link(lead, campaign, kind)}
    sub = lambda text: VAR.sub(lambda m: vals[m.group(1)], text)
    return sub(t.subject).strip(), sub(body).strip()
