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


def password_setup_url(token: str, next_path: str | None = None) -> str:
    """next_path: ruta del dashboard a la que va despues de crear la clave (la UI solo acepta rutas propias)."""
    query = {"token": token, **({"next": next_path} if next_path else {})}
    return f"{settings.app_url.rstrip('/')}/set-password?{urlencode(query)}"


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


def money(amount: int) -> str:
    """$ 99.000"""
    return f"$ {amount:,}".replace(",", ".")


def day(d: datetime.date) -> str:
    return f"{d:%d/%m/%Y}"


def _footer() -> str:
    return f"Atentina · {settings.site_url} · {settings.support_email}"


def _simple(*, to: str, subject: str, preheader: str, title: str, name: str | None,
            paragraphs: list[str], rows: list[tuple[str, object]] | None = None, rows_title: str = "",
            note: str | None = None, button: tuple[str, str] | None = None, after: list[str] = (),
            reason: str) -> Mail:
    """Mail de texto corrido: saludo, parrafos, un cuadro de datos opcional, boton y parrafos finales."""
    content = [L.heading(title)]
    if name is not None:
        content.append(L.paragraph(_greeting(name)))
    content += [L.paragraph(p) for p in paragraphs]
    if rows:
        content.append(L.details(rows_title, rows, note=note))
    if button:
        content.append(L.button(button[0], button[1]))
    content += [L.paragraph(p, muted=True) for p in after]
    lines = [subject, ""]
    if name is not None:
        lines += [_greeting(name), ""]
    lines += [x for p in paragraphs for x in (p, "")]
    if rows:
        lines += [rows_title, *(f"- {label}: {value}" for label, value in rows)]
        lines += [note, ""] if note else [""]
    if button:
        lines += [f"{button[1]}: {button[0]}", ""]
    lines += [x for p in after for x in (p, "")]
    lines.append(_footer())
    return Mail(to, subject, L.render(subject, preheader, content, reason), "\n".join(lines))


def password_reset(*, email: str, name: str, setup_url: str, expires_at: datetime.datetime,
                   existing_signup: bool = False) -> Mail:
    """Link para crear una clave nueva. existing_signup: lo pidio un registro con un email que ya tiene cuenta."""
    hours = settings.password_setup_hours
    first = ("Alguien intentó crear una cuenta de Atentina con este email, pero ya tenés una. "
             "Si fuiste vos, ingresá con tu clave o creá una nueva:" if existing_signup
             else "Pediste crear una clave nueva para ingresar a Atentina:")
    return _simple(
        to=email, subject="Ya tenés una cuenta en Atentina" if existing_signup else "Creá una clave nueva",
        preheader="Link para crear tu clave de Atentina.", title="Creá tu clave", name=name,
        paragraphs=[first], button=(setup_url, "Crear una clave nueva"),
        after=[f"El link vale {hours} horas (hasta el {_when(expires_at)}) y se usa una sola vez. "
               "Tu clave actual sigue valiendo hasta que crees la nueva.",
               "Si no lo pediste, ignorá este mail."],
        reason=f"Recibiste este email porque se pidió una clave para {email} en Atentina.")


def bank_rows() -> list[tuple[str, str]]:
    """BANK_TRANSFER_INFO: una linea por dato, 'Etiqueta: valor'."""
    rows = []
    for line in settings.bank_transfer_info.replace("\\n", "\n").splitlines():
        label, sep, value = line.partition(":")
        if line.strip():
            rows.append((label.strip(), value.strip()) if sep else ("", line.strip()))
    return rows


def transfer_requested(*, email: str, name: str, client_name: str, tier: Tier, amount: int) -> Mail:
    """Al cliente: como pagar el plan por transferencia."""
    return _simple(
        to=email, subject=f"Cómo pagar el plan {tier.name}",
        preheader=f"Transferí {money(amount)} y mandanos el comprobante.", title="Pagá tu plan", name=name,
        paragraphs=[f"Para activar el plan {tier.name} en {client_name}, transferí {money(amount)} "
                    "a esta cuenta:"],
        rows=[*bank_rows(), ("Monto", money(amount))], rows_title="Datos para la transferencia",
        after=[f"Después mandá el comprobante a {settings.support_email}. Activamos el plan apenas "
               "confirmamos el pago y te avisamos por mail."],
        reason=f"Recibiste este email porque {email} pidió el plan {tier.name} en Atentina.")


def transfer_requested_admin(*, to: str, client_name: str, user_email: str, tier: Tier, amount: int,
                             client_url: str) -> Mail:
    return _simple(
        to=to, subject=f"Pedido de plan por transferencia: {client_name}",
        preheader=f"{client_name} pidió el plan {tier.name}.", title="Pedido de plan", name=None,
        paragraphs=[f"{client_name} ({user_email}) pidió el plan {tier.name} por transferencia. "
                    "Cuando llegue el comprobante, registrá el pago desde la ficha del cliente."],
        rows=[("Cliente", client_name), ("Plan", tier.name), ("Monto", money(amount))], rows_title="Pedido",
        button=(client_url, "Abrir la ficha"),
        reason="Aviso interno de Atentina.")


def payment_recorded(*, email: str, name: str, client_name: str, tier: Tier, amount: int,
                     period_end: datetime.date) -> Mail:
    return _simple(
        to=email, subject=f"Recibimos tu pago: plan {tier.name}",
        preheader=f"Tu plan {tier.name} está activo hasta el {day(period_end)}.", title="Pago recibido", name=name,
        paragraphs=[f"Recibimos el pago de {client_name}. El plan {tier.name} está activo."],
        rows=[("Plan", tier.name), ("Monto", money(amount)), ("Activo hasta", day(period_end))], rows_title="Tu plan",
        button=(f"{settings.app_url.rstrip('/')}/plan", "Ver mi plan"),
        reason=f"Recibiste este email porque {email} es usuario de {client_name} en Atentina.")


def renewal_reminder(*, email: str, name: str, client_name: str, tier: Tier, amount: int,
                     period_end: datetime.date) -> Mail:
    return _simple(
        to=email, subject=f"Tu plan {tier.name} vence el {day(period_end)}",
        preheader=f"Transferí {money(amount)} para renovarlo.", title="Renová tu plan", name=name,
        paragraphs=[f"El plan {tier.name} de {client_name} está pago hasta el {day(period_end)}. "
                    f"Para renovarlo un mes más, transferí {money(amount)} a esta cuenta:"],
        rows=[*bank_rows(), ("Monto", money(amount))], rows_title="Datos para la transferencia",
        after=[f"Después mandá el comprobante a {settings.support_email}."],
        reason=f"Recibiste este email porque {email} es usuario de {client_name} en Atentina.")


def payment_overdue(*, email: str, name: str, client_name: str, tier: Tier, grace_until: datetime.date) -> Mail:
    return _simple(
        to=email, subject=f"No registramos el pago del plan {tier.name}",
        preheader=f"Tu plan sigue activo hasta el {day(grace_until)}.", title="Tu plan venció", name=name,
        paragraphs=[f"El plan {tier.name} de {client_name} venció y no registramos el pago. "
                    f"Lo mantenemos activo hasta el {day(grace_until)}; después la cuenta pasa al plan gratuito."],
        button=(f"{settings.app_url.rstrip('/')}/plan", "Ver cómo pagar"),
        after=[f"Si ya pagaste, mandá el comprobante a {settings.support_email}."],
        reason=f"Recibiste este email porque {email} es usuario de {client_name} en Atentina.")


def downgraded(*, email: str, name: str, client_name: str, old_tier: str, new_tier: str,
               suspended: list[str], release_on: datetime.date | None) -> Mail:
    paragraphs = [f"La cuenta de {client_name} pasó del plan {old_tier} al {new_tier}."]
    if suspended:
        paragraphs.append(
            f"Tu nuevo plan no incluye {'estos números' if len(suspended) > 1 else 'este número'}: "
            f"{', '.join(suspended)}. Quedan reservados sin atender llamadas hasta el {day(release_on)}; "
            "si volvés a un plan pago antes, los recuperás.")
    return _simple(
        to=email, subject=f"Tu cuenta pasó al plan {new_tier}",
        preheader=f"{client_name} ahora está en el plan {new_tier}.", title="Cambio de plan", name=name,
        paragraphs=paragraphs, button=(f"{settings.app_url.rstrip('/')}/plan", "Ver los planes"),
        reason=f"Recibiste este email porque {email} es usuario de {client_name} en Atentina.")


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
