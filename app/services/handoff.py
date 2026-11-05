"""Equipo del cliente y areas de derivacion (docs/features/EQUIPO_TELEFONIA.md).

- Miembros: nombre, telefono (para transferir una llamada; solo Argentina, porque Asterisk no marca
  otra cosa), si recibe avisos por WhatsApp a ese telefono (`whatsapp_notify`) y usuario opcional. Tope del
  tier: `max_team_members`.
- Areas: miembros en orden, horario semanal con dias cerrados, timbre por miembro, estrategia
  (`sequential` o `round_robin`), tecla de vuelta a la IA, mensajes, area siguiente fuera de horario o si
  nadie acepta, y envio (`delivery`: llamada o solo aviso por WhatsApp). `candidates` da a quien llamar ahora,
  en orden.
"""
import asyncio
import datetime
import json
import logging
import re
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import utcnow
from ..models import Agent, Client, HandoffArea, HandoffAreaMember, PhoneNumberMember, TeamMember, User, WaAccount
from . import limits as limits_service
from . import phones
from .errors import Conflict, Invalid, NotFound, QuotaExceeded

logger = logging.getLogger(__name__)

STRATEGIES = ("sequential", "round_robin")
FALLBACKS = ("take_message",)
ON_PERSON_HANGUP = ("resume", "end")
DELIVERIES = ("call", "whatsapp")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES = {"mon": "lunes", "tue": "martes", "wed": "miércoles", "thu": "jueves", "fri": "viernes",
             "sat": "sábados", "sun": "domingos"}
DEFAULT_TZ = "America/Argentina/Buenos_Aires"

# Mensajes por defecto (plan 4.7); cada area cambia los que quiera. Variables: {{area}}, {{persona}}, {{cliente}},
# {{resumen}}, {{horario}}, {{nombre}} y las que traiga el pre-call del agente.
DEFAULT_MESSAGES = {
    "transfer": "Te paso con {{area}}, un momento por favor.",
    "whisper": "Derivación de {{area}}: {{resumen}}. Marcá 1 para atender.",
    "no_answer": "No pude comunicarte con {{area}} en este momento. Si querés, te tomo el mensaje y te "
                 "contactan más tarde.",
    "busy": "En este momento {{area}} está ocupado. Podés volver a llamar en 10 minutos, o te tomo los datos "
            "y te contacta alguien del equipo.",
    "after_hours": "{{area}} atiende {{horario}}. Te tomo el mensaje y te contactan.",
    "resume": "¿Te puedo ayudar con algo más?",
    "goodbye": "Gracias por comunicarte, que tengas un buen día.",
    "post_call_failed": "No se pudo confirmar el registro.",
    "operator_ack": "Recibido. Estamos confirmando, te paso los datos en un momento.",
    "operator_contact": "Contacto: {{nombre}}, {{cliente}}. Motivo: {{resumen}}. Ya podés responderle desde tu "
                        "WhatsApp.",
    "accepted": "{{persona}} recibió tu pedido y te va a contactar. Lo que escribas acá también le llega.",
    "notified": "Ya le avisé a {{area}}. Te van a contactar.",
    "relay_failed": "No pude hacerle llegar tu mensaje a {{persona}}. Escribime de nuevo si necesitás avisarle a "
                    "otra persona.",
    "tap_wait": "Estamos confirmando, te paso los datos en un momento.",
    "tap_taken": "Ya la tomó {{persona}}.",
    "tap_closed": "Esta solicitud ya se cerró.",
}
# Salen antes de aceptar: un operador que no tomo el pedido no ve datos de la persona. _texts(contact=False) solo da estas
# variables, y validate_messages rechaza las demas en estos mensajes.
PRE_ACCEPT_MESSAGES = ("operator_ack", "tap_wait", "tap_taken", "tap_closed")
PRE_ACCEPT_VARIABLES = ("area", "persona", "horario")
MESSAGE_MAX = 500
_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
# Nombre de un parametro de plantilla: area, persona, cliente, resumen, horario o una variable del pre-call.
_TEMPLATE_PARAM = re.compile(r"[a-z][a-z0-9_]*")
WAIT_SECONDS_MIN, WAIT_SECONDS_MAX, WAIT_SECONDS_DEFAULT = 30, 3600, 120


# ---------- miembros ----------

def normalize_phone(raw: str | None, *, argentina: bool) -> str | None:
    if raw is None or not raw.strip():
        return None
    try:
        phone = phones.normalize_phone(raw)
    except ValueError as e:
        raise Invalid(f"Teléfono inválido ({raw}): {e}") from None
    if argentina and not phone.startswith("+54"):
        raise Invalid("Por ahora solo se puede derivar a teléfonos de Argentina")
    return phone


def _check_member(s: Session, client_id: str, member: TeamMember) -> None:
    # Solo con usuario del panel tambien: le suenan las entrantes directas ahi (docs/features/EQUIPO_TELEFONIA.md).
    if not member.phone and not member.user_id:
        raise Invalid("Cargá un teléfono o un usuario del panel")
    if member.user_id:
        user = s.get(User, member.user_id)
        if user is None or user.client_id != client_id:
            raise Invalid("El usuario no es de este cliente")


def list_members(s: Session, client_id: str | None) -> list[TeamMember]:
    q = select(TeamMember).order_by(TeamMember.name, TeamMember.id)
    if client_id is not None:
        q = q.where(TeamMember.client_id == client_id)
    return list(s.scalars(q))


def get_member(s: Session, client_id: str | None, member_id: str) -> TeamMember:
    member = s.get(TeamMember, member_id)
    if member is None or (client_id is not None and member.client_id != client_id):
        raise NotFound("Persona inexistente")
    return member


def create_member(s: Session, client: Client, *, name: str, phone: str | None = None,
                  user_id: str | None = None, active: bool = True, whatsapp_notify: bool = False) -> TeamMember:
    cap = limits_service.effective_limits(s, client).max_team_members
    if cap is not None:
        count = s.scalar(select(func.count()).select_from(TeamMember).where(TeamMember.client_id == client.id))
        if count >= cap:
            message = ("Tu plan no incluye derivación a personas" if cap == 0
                       else f"Tu plan incluye {cap} persona{'s' if cap != 1 else ''} en el equipo")
            raise QuotaExceeded(message, "team_members_limit")
    member = TeamMember(client_id=client.id, name=name.strip(), phone=normalize_phone(phone, argentina=True),
                        user_id=user_id or None, active=active, whatsapp_notify=whatsapp_notify)
    _check_member(s, client.id, member)
    s.add(member)
    s.flush()
    return member


def _no_nulls(changes: dict, nullable: set[str]) -> None:
    nulls = sorted(k for k, v in changes.items() if v is None and k not in nullable)
    if nulls:
        raise Invalid(f"No pueden ir vacíos: {', '.join(nulls)}")


def update_member(s: Session, member: TeamMember, **changes) -> TeamMember:
    _no_nulls(changes, {"phone", "user_id"})
    if "name" in changes:
        member.name = changes["name"].strip()
    if "phone" in changes:
        member.phone = normalize_phone(changes["phone"], argentina=True)
    if "user_id" in changes:
        member.user_id = changes["user_id"] or None
    if "active" in changes:
        member.active = bool(changes["active"])
    if "whatsapp_notify" in changes:
        member.whatsapp_notify = bool(changes["whatsapp_notify"])
    _check_member(s, member.client_id, member)
    s.flush()
    return member


def delete_member(s: Session, member: TeamMember) -> None:
    # Sale de sus areas y sus numeros (a mano: SQLite no aplica las FK) y de su lugar en el round robin; los
    # eventos quedan sin team_member_id.
    for row in s.scalars(select(HandoffAreaMember).where(HandoffAreaMember.member_id == member.id)):
        s.delete(row)
    for row in s.scalars(select(PhoneNumberMember).where(PhoneNumberMember.member_id == member.id)):
        s.delete(row)
    for area in s.scalars(select(HandoffArea).where(HandoffArea.last_member_id == member.id)):
        area.last_member_id = None
    s.delete(member)
    s.flush()


# ---------- horario ----------

def validate_schedule(raw: dict | None) -> dict | None:
    """El horario normalizado, o Invalid. None = atiende siempre."""
    if raw is None:
        return None
    tz = raw.get("tz") or DEFAULT_TZ
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise Invalid(f"Zona horaria desconocida: {tz}") from None
    week_in = raw.get("week") or {}
    unknown = set(week_in) - set(DAYS)
    if unknown:
        raise Invalid(f"Días desconocidos: {', '.join(sorted(unknown))} (usá {', '.join(DAYS)})")
    week: dict[str, list[list[str]]] = {}
    for day in DAYS:
        ranges = []
        for pair in week_in.get(day) or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not all(
                    isinstance(x, str) and _HHMM.match(x) for x in pair):
                raise Invalid(f"Horario inválido el {DAY_NAMES[day]}: usá [\"09:00\", \"18:00\"]")
            if pair[0] >= pair[1]:
                raise Invalid(f"Horario inválido el {DAY_NAMES[day]}: {pair[0]} tiene que ser antes que {pair[1]}")
            ranges.append([pair[0], pair[1]])
        ranges.sort()
        for (_, end), (start, _) in pairwise(ranges):
            if start < end:
                raise Invalid(f"Horarios superpuestos el {DAY_NAMES[day]}")
        if ranges:
            week[day] = ranges
    closed = []
    for d in raw.get("closed") or []:
        try:
            closed.append(datetime.date.fromisoformat(str(d)).isoformat())
        except ValueError:
            raise Invalid(f"Fecha inválida en los días cerrados: {d} (usá AAAA-MM-DD)") from None
    return {"tz": tz, "week": week, "closed": sorted(set(closed))}


def is_open(schedule: dict | None, now: datetime.datetime | None = None) -> bool:
    """Si el area atiende en `now` (UTC naive, como utcnow)."""
    if schedule is None:
        return True
    local = (now or utcnow()).replace(tzinfo=datetime.UTC).astimezone(ZoneInfo(schedule.get("tz") or DEFAULT_TZ))
    if local.date().isoformat() in (schedule.get("closed") or []):
        return False
    hhmm = local.strftime("%H:%M")
    ranges = (schedule.get("week") or {}).get(DAYS[local.weekday()]) or []
    return any(start <= hhmm < end for start, end in ranges)


DAY_SINGULAR = {"mon": "lunes", "tue": "martes", "wed": "miércoles", "thu": "jueves", "fri": "viernes",
                "sat": "sábado", "sun": "domingo"}


def describe_schedule(schedule: dict | None) -> str:
    """El horario para decirlo en voz, con los dias seguidos de igual horario juntos: "de lunes a viernes
    de 09:00 a 13:00 y de 16:00 a 20:00, los sábados de 09:00 a 13:00"."""
    if schedule is None:
        return "todos los días a toda hora"
    week = schedule.get("week") or {}
    groups: list[list[str]] = []   # dias seguidos con las mismas franjas
    for day in DAYS:
        if not week.get(day):
            continue
        prev = groups[-1][-1] if groups else None
        if prev and DAYS.index(prev) == DAYS.index(day) - 1 and week[prev] == week[day]:
            groups[-1].append(day)
        else:
            groups.append([day])
    parts = []
    for days in groups:
        hours = " y ".join(f"de {a} a {b}" for a, b in week[days[0]])
        if len(days) == 1:
            when = f"los {DAY_NAMES[days[0]]}"
        elif len(days) == 2:
            when = f"{DAY_SINGULAR[days[0]]} y {DAY_SINGULAR[days[1]]}"
        else:
            when = f"de {DAY_SINGULAR[days[0]]} a {DAY_SINGULAR[days[-1]]}"
        parts.append(f"{when} {hours}")
    return ", ".join(parts) or "con horario a confirmar"


# ---------- areas ----------

def validate_messages(raw: dict | None) -> dict:
    out = {}
    for key, text in (raw or {}).items():
        if key not in DEFAULT_MESSAGES:
            raise Invalid(f"Mensaje desconocido: {key} (son {', '.join(DEFAULT_MESSAGES)})")
        text = (text or "").strip()
        if len(text) > MESSAGE_MAX:
            raise Invalid(f"El mensaje {key} pasa de {MESSAGE_MAX} caracteres",
                          details=[{"path": f"messages.{key}", "message": f"Pasa de {MESSAGE_MAX} caracteres"}])
        if key in PRE_ACCEPT_MESSAGES and any(v not in PRE_ACCEPT_VARIABLES for v in _VAR.findall(text)):
            allowed = ", ".join(f"{{{{{v}}}}}" for v in PRE_ACCEPT_VARIABLES)
            # `errors` marca el campo (messages.<clave>) para la UI; `detail` nombra la clave para quien usa la API.
            what = f"todavía no lleva los datos de la persona: solo admite {allowed}"
            raise Invalid(f"El mensaje {key} {what}",
                          details=[{"path": f"messages.{key}", "message": what[0].upper() + what[1:]}])
        if text and text != DEFAULT_MESSAGES[key]:
            out[key] = text
    return out


def messages(area: HandoffArea) -> dict[str, str]:
    return DEFAULT_MESSAGES | (area.messages or {})


def render(text: str, /, **values: str) -> str:
    """Reemplaza {{variables}}; una que no venga queda vacia."""
    return re.sub(r"\s{2,}", " ", _VAR.sub(lambda m: str(values.get(m.group(1), "")), text)).strip()


def area_member_ids(s: Session, area_id: str) -> list[str]:
    return list(s.scalars(select(HandoffAreaMember.member_id).where(HandoffAreaMember.area_id == area_id)
                          .order_by(HandoffAreaMember.position)))


def list_areas(s: Session, client_id: str | None) -> list[HandoffArea]:
    q = select(HandoffArea).order_by(HandoffArea.name, HandoffArea.id)
    if client_id is not None:
        q = q.where(HandoffArea.client_id == client_id)
    return list(s.scalars(q))


def get_area(s: Session, client_id: str | None, area_id: str) -> HandoffArea:
    area = s.get(HandoffArea, area_id)
    if area is None or (client_id is not None and area.client_id != client_id):
        raise NotFound("Área inexistente")
    return area


def _set_members(s: Session, area: HandoffArea, member_ids: list[str]) -> None:
    if len(set(member_ids)) != len(member_ids):
        raise Invalid("Una persona aparece dos veces en el área")
    found = {m.id for m in s.scalars(select(TeamMember).where(
        TeamMember.id.in_(member_ids), TeamMember.client_id == area.client_id))} if member_ids else set()
    missing = [m for m in member_ids if m not in found]
    if missing:
        raise Invalid("Hay personas que no son del equipo de este cliente")
    for row in s.scalars(select(HandoffAreaMember).where(HandoffAreaMember.area_id == area.id)):
        s.delete(row)
    s.flush()
    for i, member_id in enumerate(member_ids):
        s.add(HandoffAreaMember(area_id=area.id, member_id=member_id, position=i))


def _template(raw, key: str) -> dict:
    """Una plantilla de `whatsapp`, normalizada. `params` va en orden: Meta los recibe por posicion."""
    if not isinstance(raw, dict):
        raise Invalid(f"whatsapp.{key}: tiene que tener name, language y params")
    name, language, params = raw.get("name"), raw.get("language"), raw.get("params") or []
    if not isinstance(name, str) or not name.strip() or not isinstance(language, str) or not language.strip():
        raise Invalid(f"whatsapp.{key}: indicá el nombre y el idioma de la plantilla")
    if not isinstance(params, list):
        raise Invalid(f"whatsapp.{key}.params: tiene que ser una lista")
    for param in params:
        if not isinstance(param, str) or not _TEMPLATE_PARAM.fullmatch(param):
            raise Invalid(f"whatsapp.{key}.params: {param!r} no es un nombre válido (minúsculas, números y _)")
    return {"name": name.strip(), "language": language.strip(), "params": params}


def validate_whatsapp(s: Session, client_id: str, raw: dict | None, delivery: str) -> dict | None:
    """El bloque `whatsapp` normalizado, o Invalid. La cuenta tiene que ser del cliente del area. El telefono de la
    persona (`cliente`) no sale antes de que acepte: solo lo lleva la plantilla de un area de aviso."""
    if raw is None:
        if delivery == "whatsapp":
            raise Invalid("Un área que avisa por WhatsApp necesita su cuenta y su plantilla")
        return None
    account = s.get(WaAccount, raw.get("account_id") or "")
    if account is None or account.client_id != client_id:
        raise Invalid("whatsapp.account_id: la cuenta no existe o es de otro cliente")
    out: dict = {"account_id": account.id}
    for key in ("template", "call_template"):
        if raw.get(key) is not None:
            out[key] = _template(raw[key], key)
    if "template" not in out and "call_template" not in out:
        raise Invalid("whatsapp: indicá al menos una plantilla")
    if delivery == "whatsapp" and "template" not in out:
        raise Invalid("whatsapp.template: un área que avisa por WhatsApp necesita su plantilla")
    wait = raw.get("wait_seconds")
    wait = WAIT_SECONDS_DEFAULT if wait is None else wait
    if isinstance(wait, bool) or not isinstance(wait, int) or not WAIT_SECONDS_MIN <= wait <= WAIT_SECONDS_MAX:
        raise Invalid(f"whatsapp.wait_seconds: entre {WAIT_SECONDS_MIN} y {WAIT_SECONDS_MAX}")
    out["wait_seconds"] = wait
    if "cliente" in out.get("call_template", {}).get("params", []):
        raise Invalid("whatsapp.call_template: no puede llevar cliente: el teléfono no sale antes de aceptar")
    if delivery == "call" and "cliente" in out.get("template", {}).get("params", []):
        raise Invalid("whatsapp.template: no puede llevar cliente en la rotación: el teléfono no sale antes de aceptar")
    return out


def _route_target(s: Session, area: HandoffArea, key: str, target_id: str | None) -> str | None:
    """El area siguiente: del mismo cliente y no ella misma. Los ciclos largos se cortan al derivar."""
    if not target_id:
        return None
    if target_id == area.id:
        raise Invalid(f"{key}: el área no puede pasar a sí misma")
    target = s.get(HandoffArea, target_id)
    if target is None or target.client_id != area.client_id:
        raise Invalid(f"{key}: el área no existe o es de otro cliente")
    return target.id


def _apply(s: Session, area: HandoffArea, changes: dict) -> None:
    if "name" in changes:
        name = (changes["name"] or "").strip()
        if not name:
            raise Invalid("El área necesita un nombre")
        area.name = name
    if "description" in changes:
        area.description = (changes["description"] or "").strip()
    if "active" in changes:
        area.active = bool(changes["active"])
    if "strategy" in changes:
        if changes["strategy"] not in STRATEGIES:
            raise Invalid(f"Estrategia desconocida (son {', '.join(STRATEGIES)})")
        area.strategy = changes["strategy"]
    if "ring_seconds" in changes:
        area.ring_seconds = int(changes["ring_seconds"])
    if "schedule" in changes:
        area.schedule = validate_schedule(changes["schedule"])
    if "fallback" in changes:
        if changes["fallback"] not in FALLBACKS:
            raise Invalid(f"Alternativa desconocida (son {', '.join(FALLBACKS)})")
        area.fallback = changes["fallback"]
    if "on_person_hangup" in changes:
        if changes["on_person_hangup"] not in ON_PERSON_HANGUP:
            raise Invalid(f"Opción desconocida si corta la persona (son {', '.join(ON_PERSON_HANGUP)})")
        area.on_person_hangup = changes["on_person_hangup"]
    if "return_digits" in changes:
        digits = changes["return_digits"] or ""
        if not re.fullmatch(r"[0-9#]{1,4}", digits) or digits == "1":
            # El 1 es el de aceptar la derivacion; el * lo toma la central de Anura (plan 11.2).
            raise Invalid("La tecla para volver a la IA: 1 a 4 dígitos o #, sin * y distinta de 1")
        area.return_digits = digits
    if "messages" in changes:
        area.messages = validate_messages(changes["messages"])
    for key in ("after_hours_area_id", "no_answer_area_id"):
        if key in changes:
            setattr(area, key, _route_target(s, area, key, changes[key]))
    if "delivery" in changes:
        if changes["delivery"] not in DELIVERIES:
            raise Invalid(f"Envío desconocido (son {', '.join(DELIVERIES)})")
        area.delivery = changes["delivery"]
    # Se valida junto: `cliente` y la plantilla obligatoria dependen de delivery.
    if "delivery" in changes or "whatsapp" in changes:
        area.whatsapp = validate_whatsapp(s, area.client_id, changes.get("whatsapp", area.whatsapp), area.delivery)


def _check_name(s: Session, area: HandoffArea) -> None:
    other = s.scalar(select(HandoffArea.id).where(
        HandoffArea.client_id == area.client_id, func.lower(HandoffArea.name) == area.name.lower(),
        HandoffArea.id != area.id))
    if other is not None:
        raise Conflict("Ya hay un área con ese nombre", "area_name_taken")


def create_area(s: Session, client_id: str, *, member_ids: list[str] | None = None, **fields) -> HandoffArea:
    area = HandoffArea(client_id=client_id, name="", messages={}, delivery="call")
    _apply(s, area, {"delivery": "call", **fields})
    if not area.name:
        raise Invalid("El área necesita un nombre")
    _check_name(s, area)
    s.add(area)
    s.flush()
    _set_members(s, area, member_ids or [])
    s.flush()
    return area


def update_area(s: Session, area: HandoffArea, *, member_ids: list[str] | None = None, **changes) -> HandoffArea:
    _no_nulls(changes, {"schedule", "messages", "description", "after_hours_area_id", "no_answer_area_id",
                        "whatsapp"})
    _apply(s, area, changes)
    _check_name(s, area)
    if member_ids is not None:
        _set_members(s, area, member_ids)
    s.flush()
    return area


def agents_using(s: Session, area: HandoffArea) -> list[str]:
    """Nombres de los agentes del cliente (sin archivar) cuya version vigente puede derivar a esta area."""
    rows = s.scalars(select(Agent).where(Agent.client_id == area.client_id, Agent.archived_at.is_(None)))
    return [a.name for a in rows
            if any(t.get("area_id") == area.id for t in ((a.definition or {}).get("handoff") or {}).get("areas") or [])]


def delete_area(s: Session, area: HandoffArea) -> None:
    """No se borra un area que usa un agente: su definicion quedaria con un area inexistente y no se podria
    guardar hasta sacarla. Tampoco una a la que pasa otra area: esa ruta se perderia sin aviso."""
    if used := agents_using(s, area):
        raise Conflict(f"El área la usan los agentes {', '.join(used)}: sacala de su derivación antes de borrarla",
                       "area_in_use")
    referencing = list(s.scalars(select(HandoffArea.name).where(
        HandoffArea.client_id == area.client_id, HandoffArea.id != area.id,
        or_(HandoffArea.after_hours_area_id == area.id, HandoffArea.no_answer_area_id == area.id))))
    if referencing:
        raise Conflict(f"Pasan a esta área: {', '.join(referencing)}. Cambialas antes de borrarla", "area_in_use")
    for row in s.scalars(select(HandoffAreaMember).where(HandoffAreaMember.area_id == area.id)):
        s.delete(row)
    s.delete(area)
    s.flush()


def hold_tracks() -> list[str]:
    """Temas de musica de espera: "default" (el de LiveKit Agents) y los .ogg de HOLD_MUSIC_DIR."""
    folder = settings.hold_music_dir
    files = sorted(f.stem for f in folder.glob("*.ogg") if re.fullmatch(r"[a-z0-9_-]{1,64}", f.stem)) \
        if folder.is_dir() else []
    return ["default", *[f for f in files if f != "default"]]


def check_agent_handoff(s: Session, client_id: str, handoff: dict | None) -> list[dict]:
    """Errores de workflow.handoff para el editor: cada area es del cliente del agente y el tema existe."""
    if not handoff:
        return []
    errors = []
    for i, target in enumerate(handoff.get("areas") or []):
        area = s.get(HandoffArea, target.get("area_id"))
        if area is None or area.client_id != client_id:
            errors.append({"path": f"handoff.areas.{i}.area_id", "message": "El área no existe o es de otro cliente"})
    track = (handoff.get("hold_music") or {}).get("track", "default")
    if track not in hold_tracks():
        errors.append({"path": "handoff.hold_music.track", "message": f"No hay un tema de espera {track!r}"})
    return errors


def call_areas(s: Session, client_id: str, handoff, channel: str = "voice") -> list[dict]:
    """Las areas de una llamada como las ve el LLM (Progress.handoff_areas): las activas del agente, con su
    horario y si fuera de horario pasan a otra (`redirects`). `handoff`: el HandoffConfig del agente. Por WhatsApp,
    solo las que tienen plantilla de rotacion o aviso."""
    out = []
    for target in handoff.areas if handoff else []:
        area = s.get(HandoffArea, target.area_id)
        if area is None or area.client_id != client_id or not area.active:
            continue
        if channel == "whatsapp" and not (area.whatsapp or {}).get("template"):
            continue
        out.append({"id": area.id, "name": area.name, "when": target.when or area.description,
                    "schedule": area.schedule, "schedule_text": describe_schedule(area.schedule),
                    "redirects": bool(area.after_hours_area_id)})
    return out


def find_area(areas: list[dict], name: str) -> dict | None:
    """El area que eligio el agente en transfer_call (uno de los nombres del enum de la herramienta)."""
    return next((a for a in areas if a["name"] == name), None)

def candidates(s: Session, area: HandoffArea, now: datetime.datetime | None = None) -> list[TeamMember]:
    """A quien llamar ahora, en orden: los miembros activos con telefono, si el area esta activa y en
    horario. Con round_robin, empieza por el siguiente al ultimo al que se le paso."""
    if not area.active or not is_open(area.schedule, now):
        return []
    ids = area_member_ids(s, area.id)
    by_id = {m.id: m for m in s.scalars(select(TeamMember).where(TeamMember.id.in_(ids)))}
    ordered = [by_id[i] for i in ids if i in by_id]
    ordered = [m for m in ordered if m.active and m.phone]
    if area.strategy == "round_robin" and area.last_member_id:
        ids = [m.id for m in ordered]
        if area.last_member_id in ids:
            k = ids.index(area.last_member_id) + 1
            ordered = ordered[k:] + ordered[:k]
    return ordered


# ---------- resumen para la persona que atiende ----------

# Espera del resumen del LLM: en voz el timbre suele tardar mas, asi que casi nunca espera.
SUMMARY_TIMEOUT = 4.0
FALLBACK_SUMMARY = "una consulta"
SUMMARY_SCHEMA = {"type": "object", "properties": {"resumen": {"type": "string"}}, "required": ["resumen"]}


def summary_messages(conversation: str) -> list[dict]:
    """Pedido al LLM del resumen para el whisper: quien llama y que necesita, en una frase."""
    return [{"role": "system", "content": (
                "Resumí la llamada para la persona del equipo que la va a atender, en una sola frase de hasta 15 "
                "palabras: quién llama (si dijo su nombre) y qué necesita. "
                'Respondé en JSON: {"resumen": "..."}')},
            {"role": "user", "content": conversation}]


async def summarize(llm, conversation: str) -> str:
    content, _ = await llm.structured(summary_messages(conversation), SUMMARY_SCHEMA, "resumen", thinking=False,
                                      max_tokens=200)
    return str(json.loads(content).get("resumen") or "")


async def safe_summary(llm, conversation: str, timeout: float | None = None) -> str:
    """El resumen con tope: si el LLM falla, tarda o no dice nada, FALLBACK_SUMMARY. No lanza."""
    try:
        text = await asyncio.wait_for(summarize(llm, conversation), SUMMARY_TIMEOUT if timeout is None else timeout)
    except Exception:
        logger.exception("derivacion: sin resumen")
        return FALLBACK_SUMMARY
    return text.strip() or FALLBACK_SUMMARY
