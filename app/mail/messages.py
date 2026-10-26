"""Contenido de cada mail. Funciones puras: reciben los datos y devuelven un `Mail`."""
import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from ..config import settings
from ..legal import Version
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


def password_reset(*, email: str, name: str, setup_url: str, expires_at: datetime.datetime) -> Mail:
    """Link para crear una clave nueva ("olvidé mi clave")."""
    hours = settings.password_setup_hours
    first = "Pediste crear una clave nueva para ingresar a Atentina:"
    return _simple(
        to=email, subject="Creá una clave nueva",
        preheader="Link para crear tu clave de Atentina.", title="Creá tu clave", name=name,
        paragraphs=[first], button=(setup_url, "Crear una clave nueva"),
        after=[f"El link vale {hours} horas (hasta el {_when(expires_at)}) y se usa una sola vez. "
               "Tu clave actual sigue valiendo hasta que crees la nueva.",
               "Si no lo pediste, ignorá este mail."],
        reason=f"Recibiste este email porque se pidió una clave para {email} en Atentina.")


def account_code(*, email: str, name: str, code: str, expires_at: datetime.datetime,
                 new_email: str | None = None) -> Mail:
    """Codigo para cambiar la clave o (con new_email) el email de ingreso, desde el perfil."""
    what = f"cambiar tu email de ingreso a {new_email}" if new_email else "cambiar tu clave"
    subject = f"Tu código de Atentina: {code}"
    until = f"Vale {settings.account_code_minutes} minutos (hasta el {_when(expires_at)}) y se usa una sola vez."
    warning = "Si no lo pediste, no lo compartas con nadie y cambiá tu clave: alguien entró con tu cuenta."
    html = L.render(
        subject, f"Código para {what}.",
        [L.heading("Tu código"), L.paragraph(_greeting(name)),
         L.paragraph(f"Para {what}, ingresá este código en el dashboard:"), L.code(code),
         L.paragraph(until, muted=True), L.paragraph(warning, muted=True)],
        f"Recibiste este email porque se pidió un cambio en la cuenta {email} de Atentina.")
    lines = [subject, "", _greeting(name), "", f"Para {what}, ingresá este código en el dashboard:", "", code, "",
             until, "", warning, "", _footer()]
    return Mail(email, subject, html, "\n".join(lines))


def _legal_moment(moment: datetime.datetime) -> str:
    """'25/10/2026 15:30 (hora de Argentina)'. `moment` en UTC."""
    local = moment.replace(tzinfo=moment.tzinfo or datetime.UTC).astimezone(ZoneInfo(settings.billing_timezone))
    return f"{local:%d/%m/%Y %H:%M} (hora de Argentina)"


def _legal_rows(accepted: list[Version], moment: datetime.datetime) -> list[tuple[str, object]]:
    return [*((v.doc.title, f"versión {v.version}") for v in accepted), ("Fecha", _legal_moment(moment))]


def _legal_after(accepted: list[Version]) -> list[str]:
    """Links permanentes y huella de cada version: con eso se puede probar que texto se acepto."""
    return [f"{v.doc.title}, versión {v.version}: {v.url} (huella SHA-256 {v.sha256})" for v in accepted]


def legal_accepted(*, email: str, name: str, client_name: str, accepted: list[Version],
                   accepted_at: datetime.datetime) -> Mail:
    """Confirmacion de la aceptacion en el panel (CCyC art. 1108: confirmar por via electronica y sin demora)."""
    return _simple(
        to=email, subject="Aceptaste las condiciones de Atentina",
        preheader="Confirmación de las versiones que aceptaste.", title="Confirmación de tu aceptación", name=name,
        paragraphs=[f"Registramos que aceptaste, como usuario de {client_name}, estas versiones:"],
        rows=_legal_rows(accepted, accepted_at), rows_title="Aceptación",
        after=[*_legal_after(accepted),
               "Guardá este mail: es tu constancia. Podés darte de baja o arrepentirte en "
               f"{settings.site_url.rstrip('/')}/baja y {settings.site_url.rstrip('/')}/arrepentimiento."],
        reason=f"Recibiste este email porque {email} aceptó las condiciones de Atentina.")


CONSUMER_KINDS = {"revocation": "arrepentimiento", "cancellation": "baja"}


def consumer_request_received(*, email: str, name: str, kind: str, code: str,
                              created_at: datetime.datetime) -> Mail:
    """Al que uso el boton de arrepentimiento o de baja: su codigo de tramite (Disp. 954/2025)."""
    what = CONSUMER_KINDS[kind]
    detail = ("Te devolvemos lo pagado por el mismo medio de pago y te avisamos cuando esté hecho."
              if kind == "revocation" else
              "Damos de baja el plan: no se renueva y te avisamos cuando esté hecho.")
    return _simple(
        to=email, subject=f"Recibimos tu pedido de {what}: {code}",
        preheader=f"Tu código de trámite es {code}.", title=f"Pedido de {what} recibido", name=name,
        paragraphs=[f"Recibimos tu pedido de {what}. {detail}"],
        rows=[("Código de trámite", code), ("Fecha", _legal_moment(created_at))], rows_title="Tu pedido",
        after=[f"Si tenés que agregar algo, respondé a {settings.support_email} con el código."],
        reason=f"Recibiste este email porque se pidió el {what} del servicio de Atentina con {email}.")


def consumer_request_admin(*, to: str, kind: str, code: str, name: str, email: str, company: str, message: str,
                           client_url: str | None) -> Mail:
    what = CONSUMER_KINDS[kind]
    return _simple(
        to=to, subject=f"Pedido de {what}: {company or name} ({code})",
        preheader=f"{name} pidió el {what}.", title=f"Pedido de {what}", name=None,
        paragraphs=[f"{name} ({email}) usó el botón de {what}. Resolvelo y marcá el pedido como hecho "
                    "(PATCH /api/v1/consumer-requests/{id})."
                    + (" Si es arrepentimiento, devolvé lo pagado." if kind == "revocation" else "")],
        rows=[("Código", code), ("Empresa", company or "-"), ("Mensaje", message or "-")], rows_title="Pedido",
        button=(client_url, "Abrir la ficha del cliente") if client_url else None,
        reason="Aviso interno de Atentina.")


def account_ready(*, email: str, name: str, client_name: str, tier_name: str | None = None,
                  accepted: list[Version] = (), accepted_at: datetime.datetime | None = None) -> Mail:
    """Registro desde la landing: la cuenta ya esta creada (la clave la eligio en el formulario). Con `accepted`,
    lleva tambien la confirmacion de la aceptacion de las condiciones (CCyC art. 1108)."""
    dash = dashboard_url(email)
    plan = (f"en el plan {tier_name}" if tier_name and tier_name.lower() != "free" else "en el plan gratuito")
    later = ("" if tier_name and tier_name.lower() != "free"
             else " Cuando necesites números de teléfono o más minutos, elegí un plan en la sección Plan.")
    return _simple(
        to=email, subject="Tu cuenta de Atentina está lista",
        preheader=f"Ya podés armar el agente de {client_name}.", title="Tu cuenta está lista", name=name,
        paragraphs=[f"Creamos la cuenta de {client_name} en Atentina, {plan}.",
                    "Para empezar, armá tu agente o elegí uno de la plantilla y probalo con una llamada de prueba."
                    + later],
        button=(dash, "Ir al dashboard"),
        rows=_legal_rows(list(accepted), accepted_at) if accepted else None, rows_title="Lo que aceptaste",
        after=[f"Ingresá siempre con este email ({email}) y la clave que elegiste. Si no la recordás, "
               "usá «Olvidé mi clave» en el ingreso.", *_legal_after(list(accepted))],
        reason=f"Recibiste este email porque se creó una cuenta en Atentina con {email}. "
               f"Si no fuiste vos, escribinos a {settings.support_email}.")


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


CALL_MODES = {"entrante": "Entrante", "saliente": "Saliente", "web": "Por el link para llamar"}


def _duration(seconds: int) -> str:
    minutes, secs = divmod(max(seconds, 0), 60)
    return f"{minutes} min {secs:02d} s" if minutes else f"{secs} s"


def call_summary(*, to: str, client_name: str, agent_name: str, mode: str, phone: str | None,
                 client_number: str | None, started_at: datetime.datetime, duration_seconds: int,
                 outcome: str | None, fields: list[tuple[str, str]], transcript: list[tuple[str, str]],
                 truncated: bool, call_url: str, context: str | None = None) -> Mail:
    """Resumen de una llamada para el cliente (app/mail/call_summary.py): datos, resultado y transcripcion."""
    # phone: el de la llamada o, por el link, el que dio la persona (None si no lo dio).
    who = phone or "número oculto"
    web = f"Llamada por el link de {phone} a {agent_name}" if phone else f"Llamada por el link a {agent_name}"
    subject = {"saliente": f"Llamada de {agent_name} a {who}", "web": web}.get(mode, f"Llamada de {who} a {agent_name}")
    label = {"entrante": "Llamó", "saliente": "Destino"}.get(mode, "Teléfono")
    rows: list[tuple[str, object]] = [("Agente", agent_name), ("Tipo", CALL_MODES.get(mode, mode)),
                                      (label, phone or ("No lo dio" if mode == "web" else "Número oculto"))]
    if client_number:
        rows.append(("Tu número", client_number))
    rows += [("Fecha", _when(started_at)), ("Duración", _duration(duration_seconds)),
             ("Resultado", outcome or "Sin resultado (no completó los datos)")]
    note = "La transcripción sigue en el dashboard." if truncated else None
    reason = (f"Recibiste este email porque {client_name} tiene prendido el resumen de llamadas de {agent_name} "
              "en Atentina. Para dejar de recibirlo, apagalo en Mi cuenta.")
    content = [L.heading("Resumen de la llamada"), L.details("La llamada", rows)]
    if context:     # llamada suelta: con que motivo se llamo
        content.append(L.details("Motivo del llamado", [], note=context))
    if fields:
        content.append(L.details("Datos que tomó el agente", fields))
    if transcript:
        content.append(L.transcript("Conversación", transcript, note=note))
    content.append(L.button(call_url, "Ver la llamada"))
    lines = [subject, "", "La llamada", *(f"- {label}: {value}" for label, value in rows), ""]
    if context:
        lines += ["Motivo del llamado", context, ""]
    if fields:
        lines += ["Datos que tomó el agente", *(f"- {label}: {value}" for label, value in fields), ""]
    if transcript:
        lines += ["Conversación", *(f"{speaker}: {text}" for speaker, text in transcript), ""]
        lines += [note, ""] if note else []
    lines += [f"Ver la llamada: {call_url}", "", reason, "", _footer()]
    preheader = f"{outcome or 'Sin resultado'} · {_duration(duration_seconds)}"
    return Mail(to, subject, L.render(subject, preheader, content, reason), "\n".join(lines))
