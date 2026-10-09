"""Contenido de cada mail. Funciones puras: reciben los datos y devuelven un `Mail`."""
import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from ..config import settings
from ..models import Tier
from . import layout as L
from .sender import Mail


def dashboard_url(email: str) -> str:
    """Login con el email prellenado (si ya hay sesion, la pantalla va directo al inicio)."""
    return f"{settings.app_url.rstrip('/')}/login?{urlencode({'email': email})}"


def password_setup_url(token: str) -> str:
    return f"{settings.app_url.rstrip('/')}/set-password?{urlencode({'token': token})}"


def _count(n: int | None) -> str:
    return "Sin límite" if n is None else f"{n:,}".replace(",", ".")


def _when(moment: datetime.datetime) -> str:
    """'12/10 a las 15:30' en la hora de facturacion (Argentina). `moment` en UTC."""
    local = moment.replace(tzinfo=moment.tzinfo or datetime.UTC).astimezone(ZoneInfo(settings.billing_timezone))
    return f"{local:%d/%m} a las {local:%H:%M}"


def _greeting(name: str) -> str:
    first = name.strip().split(" ")[0] if name.strip() else ""
    return f"Hola {first}," if first else "Hola,"


def tier_rows(tier: Tier) -> list[tuple[str, str]]:
    return [
        ("Llamadas simultáneas", _count(tier.max_concurrent_calls)),
        ("Minutos entrantes por mes", _count(tier.inbound_minutes)),
        ("Minutos salientes por mes", _count(tier.outbound_minutes)),
        ("Números de teléfono", _count(tier.max_phone_numbers)),
    ]


def welcome(*, email: str, name: str, client_name: str, tier: Tier, setup_url: str,
            expires_at: datetime.datetime) -> Mail:
    """Cuenta nueva: link para crear la clave, plan contratado y link al dashboard."""
    dash = dashboard_url(email)
    hours = settings.password_setup_hours
    subject = "Activá tu cuenta de Atentina"
    html = L.render(
        subject,
        f"Creá tu clave para ingresar al dashboard de {client_name}.",
        [
            L.heading("Activá tu cuenta"),
            L.paragraph(_greeting(name)),
            L.paragraph("Creamos la cuenta de ", L.strong(client_name), " en Atentina. "
                        "Para empezar, creá tu clave de acceso:"),
            L.button(setup_url, "Crear mi clave"),
            L.paragraph(f"El link vale {hours} horas (hasta el {_when(expires_at)}) y se usa una sola vez. "
                        f"Si vence, escribinos a {settings.support_email} y te mandamos otro.", muted=True),
            L.steps([
                "Creá tu clave con el botón de arriba.",
                L.Safe(f"Ingresá al dashboard con este email: {L.strong(email)}."),
                "Armá tu agente o elegí uno de la plantilla, y probalo con una llamada de prueba.",
            ]),
            L.details(f"Tu plan: {tier.name}", tier_rows(tier), note=tier.description or None),
            L.paragraph("Cuando ya tengas tu clave, ingresá siempre desde ", L.link(dash, "el dashboard"), "."),
        ],
        f"Recibiste este email porque se creó una cuenta en Atentina con {email}. "
        "Si no lo esperabas, ignoralo: sin crear la clave, nadie puede ingresar.")
    lines = [
        subject, "",
        _greeting(name), "",
        f"Creamos la cuenta de {client_name} en Atentina. Para empezar, creá tu clave de acceso:",
        setup_url, "",
        (f"El link vale {hours} horas (hasta el {_when(expires_at)}) y se usa una sola vez. "
         f"Si vence, escribinos a {settings.support_email} y te mandamos otro."), "",
        "Qué tenés que hacer:",
        "1. Creá tu clave con el link de arriba.",
        f"2. Ingresá al dashboard con este email: {email}.",
        "3. Armá tu agente o elegí uno de la plantilla, y probalo con una llamada de prueba.", "",
        f"Tu plan: {tier.name}",
        *([tier.description] if tier.description else []),
        *(f"- {label}: {value}" for label, value in tier_rows(tier)), "",
        f"Cuando ya tengas tu clave, ingresá siempre desde el dashboard: {dash}", "",
        f"Atentina · {settings.site_url} · {settings.support_email}",
    ]
    return Mail(email, subject, html, "\n".join(lines))


def number_assigned(*, email: str, name: str, client_name: str, number: str, label: str, agent_name: str | None,
                    numbers_used: int, numbers_limit: int | None) -> Mail:
    """Numero asignado al cliente: el numero, quien lo atiende y cuanto del plan se usa."""
    dash = dashboard_url(email)
    subject = f"Te asignamos el número {number}"
    usage = f"{numbers_used} de {_count(numbers_limit)}" if numbers_limit is not None else f"{numbers_used} (sin límite)"
    rows: list[tuple[str, object]] = [("Número", number)]
    if label:
        rows.append(("Etiqueta", label))
    rows += [("Lo atiende", agent_name or "Todavía sin agente"), ("Números de tu plan en uso", usage)]
    if agent_name:
        next_step = f"Las llamadas que entren a este número las atiende {agent_name}."
        next_text = next_step
    else:
        next_step = ("Hasta que elijas qué agente lo atiende, las llamadas a este número no se responden. "
                     "Ingresá a Mi cuenta, buscá el número y elegí el agente.")
        next_text = next_step
    html = L.render(
        subject,
        f"{number} ya es parte de la cuenta de {client_name}.",
        [
            L.heading("Tenés un número nuevo"),
            L.paragraph(_greeting(name)),
            L.paragraph("Asignamos el número ", L.strong(number), " a ", L.strong(client_name), "."),
            L.details("Tu número", rows),
            L.paragraph(next_step),
            L.button(dash, "Ir al dashboard"),
        ],
        f"Recibiste este email porque {email} es usuario de {client_name} en Atentina.")
    lines = [
        subject, "",
        _greeting(name), "",
        f"Asignamos el número {number} a {client_name}.", "",
        *(f"- {label}: {value}" for label, value in rows), "",
        next_text, "",
        f"Dashboard: {dash}", "",
        f"Atentina · {settings.site_url} · {settings.support_email}",
    ]
    return Mail(email, subject, html, "\n".join(lines))
