"""Asistente de primera vez (docs/features/PRIMERA_VEZ.md).

Mientras el cliente no tiene agentes, el panel muestra el asistente: rubro (y sitio), voz, y el agente
sale de la plantilla del rubro con la empresa y la voz elegidas. Despues, el usuario puede verificar su
celular con un codigo por WhatsApp y pedir que el agente lo llame (llamada de prueba, modo `celular`):
TRIAL_CALLS llamadas y TRIAL_CALL_SECONDS en total por cliente, no gastan minutos del plan.

El codigo no tiene tabla: como el del perfil (services/profile.py), la API devuelve un desafio firmado con el
celular y el usuario lo manda de vuelta con el codigo.
"""
import datetime
import logging
from dataclasses import dataclass

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from ..agents.templates import voice_name
from ..config import settings
from ..conversation.engine import ConversationEngine
from ..db import utcnow
from ..models import Agent, CallMode, CallRow, CallStatus, Client, User, WaAccount
from ..whatsapp.graph import GraphError
from ..whatsapp.service import recipient
from ..whatsapp.signup import graph_for
from ..whatsapp.store import token_for
from . import agents as agents_service
from . import calls as calls_service
from . import quota, voices
from .errors import Conflict, Forbidden, Invalid, NotFound, QuotaExceeded, ServiceError, Upstream
from .phones import has_whatsapp, normalize_phone, wa_id
from .profile import CODE_INVALID, HOUR, WINDOW, limiter
from .ratelimit import Limit
from .security import check_account_code, create_account_code_token, new_account_code

logger = logging.getLogger(__name__)
PURPOSE = "phone"


@dataclass(frozen=True)
class Industry:
    label: str
    template_id: str
    agent_label: str   # el nombre del agente: "<voz> · <agent_label>"


# El orden es el de la pantalla; "otro" es el asistente basico.
INDUSTRIES = {
    "salud": Industry("Salud y consultorios", "salud", "turnos"),
    "gimnasio": Industry("Gimnasios y clubes", "gimnasio", "atención"),
    "inmobiliaria": Industry("Inmobiliarias", "inmobiliaria", "consultas"),
    "gastronomia": Industry("Gastronomía", "gastronomia", "reservas"),
    "cobranzas": Industry("Cobranzas", "cobranzas", "cobranzas"),
    "otro": Industry("Otro rubro", "asistente", "atención"),
}


class Unavailable(ServiceError):
    status_code = 503
    default_code = "phone_verify_unavailable"


def verify_available() -> bool:
    return bool(settings.phone_verify_wa_number_id and settings.phone_verify_wa_template)


def has_agents(s: Session, client_id: str) -> bool:
    """Agentes sin archivar: sin ninguno, el panel muestra el asistente."""
    return bool(s.scalar(select(exists().where(Agent.client_id == client_id, Agent.archived_at.is_(None)))))


@dataclass
class TrialUsage:
    calls: int
    seconds: int


def trial_usage(s: Session, client_id: str) -> TrialUsage:
    """Llamadas de prueba al celular del cliente (sin las que rechazo el tier) y sus segundos, en total."""
    where = (CallRow.client_id == client_id, CallRow.mode == CallMode.celular, CallRow.status != CallStatus.rechazada)
    calls = s.scalar(select(func.count()).select_from(CallRow).where(*where)) or 0
    seconds = s.scalar(select(func.coalesce(func.sum(CallRow.duration_seconds), 0)).where(*where)) or 0
    return TrialUsage(int(calls), int(seconds))


def status(s: Session, client: Client, user: User | None) -> dict:
    usage = trial_usage(s, client.id)
    return {
        "has_agents": has_agents(s, client.id), "industry": client.industry or None, "website": client.website,
        "phone": user.phone if user else None,
        "phone_verified": bool(user and user.phone and user.phone_verified_at),
        "verify_available": verify_available(),
        "trial": {"calls_used": usage.calls, "calls_max": settings.trial_calls, "seconds_used": usage.seconds,
                  "seconds_max": settings.trial_call_seconds},
    }


def _website(raw: str) -> str:
    site = raw.strip()
    if site and "://" not in site:
        site = "https://" + site
    if len(site) > 200 or (site and (" " in site or "." not in site)):
        raise Invalid("El sitio no es válido, por ejemplo tuempresa.com.ar", "invalid_website")
    return site


def _unique_slug(s: Session, client_id: str, name: str) -> str:
    base = agents_service.slugify(name)[:60]
    slug, n = base, 1
    while s.scalar(select(exists().where(Agent.client_id == client_id, Agent.slug == slug))):
        n += 1
        slug = f"{base}_{n}"
    return slug


def create_first_agent(s: Session, client: Client, user_id: str | None, industry: str, voice: str,
                       website: str = "") -> Agent:
    """Guarda el rubro y el sitio del cliente y crea el agente de la plantilla del rubro con la voz elegida."""
    item = INDUSTRIES.get(industry)
    if item is None:
        raise Invalid(f"Rubro inexistente: {industry}", "invalid_industry")
    if voice not in voices.catalog():
        raise Invalid(f"Voz inexistente: {voice}", "invalid_voice")
    client.industry, client.website = industry, _website(website)
    name = f"{voice_name(voice)} · {item.agent_label}"
    agent = agents_service.create_agent(s, client, name, _unique_slug(s, client.id, name),
                                        f"Creado en el asistente de primera vez ({item.label}).", None,
                                        item.template_id, user_id, voice)
    logger.info("primera vez: cliente %s, rubro %s, voz %s", client.slug, industry, voice)
    return agent


# ---------- celular ----------

@dataclass
class CodeSent:
    challenge: str
    phone: str
    expires_at: datetime.datetime


def _require_user(user: User | None) -> User:
    if user is None or user.client_id is None:
        raise Forbidden("Solo un usuario del cliente verifica su celular y pide la llamada de prueba",
                        "client_user_only")
    return user


async def send_code(s: Session, user: User | None, raw_phone: str) -> CodeSent:
    """Manda el codigo por WhatsApp al celular. No lo guarda: queda en el desafio."""
    user = _require_user(user)
    if not verify_available():
        raise Unavailable("La verificación por WhatsApp todavía no está disponible.")
    try:
        phone = normalize_phone(raw_phone)
    except ValueError:
        raise Invalid("El celular no es válido: código de área y número, por ejemplo 11 5555-1234.",
                      "invalid_phone") from None
    if not has_whatsapp(phone):
        raise Invalid("Ese número es un fijo: poné un celular con WhatsApp.", "invalid_phone")
    limiter.consume(f"phone_code:send:{user.id}", [Limit(settings.account_code_sends_per_hour, HOUR)],
                    "Pediste muchos códigos. Probá de nuevo en un rato.")
    code = new_account_code()
    challenge, expires = create_account_code_token(user, PURPOSE, code, phone)
    pnid = settings.phone_verify_wa_number_id
    account = s.scalar(select(WaAccount).where(WaAccount.phone_number_id == pnid))
    token = token_for(account) if account is not None else settings.wa_access_token
    try:
        await graph_for(token).send_auth_code(pnid, recipient(wa_id(phone)), settings.phone_verify_wa_template,
                                              settings.phone_verify_wa_language, code)
    except GraphError as e:
        logger.warning("primera vez: codigo a %s no enviado: %s", phone, e.message)
        raise Upstream("No pudimos mandarte el código por WhatsApp. Revisá el número o probá en un rato.",
                       "whatsapp_failed") from None
    logger.info("primera vez: codigo por WhatsApp para el usuario %s", user.email)
    return CodeSent(challenge, phone, expires)


def confirm_code(s: Session, user: User | None, challenge: str, code: str) -> User:
    """Verifica el codigo y deja el celular del desafio como el del usuario, verificado."""
    user = _require_user(user)
    key = f"phone_code:try:{user.id}"
    limiter.consume(key, [Limit(settings.account_code_attempts_15m, WINDOW)],
                    "Demasiados intentos. Pedí un código nuevo en unos minutos.")
    payload = check_account_code(challenge, user, PURPOSE, code)
    if payload is None or not payload.get("new"):
        raise Invalid(CODE_INVALID, "invalid_code")
    limiter.reset(key)
    user.phone, user.phone_verified_at = payload["new"], utcnow()
    s.commit()
    return user


async def call_me(s: Session, engine: ConversationEngine, principal, user: User | None,
                  agent_id: str) -> calls_service.CallStarted:
    """El agente llama al celular verificado del usuario, dentro del cupo de prueba del cliente."""
    user = _require_user(user)
    if not (user.phone and user.phone_verified_at):
        raise Conflict("Primero verificá tu celular.", "phone_not_verified")
    agent = s.get(Agent, agent_id)
    if agent is None or agent.client_id != user.client_id:
        raise NotFound("Agente inexistente")
    usage = trial_usage(s, user.client_id)
    left = settings.trial_call_seconds - usage.seconds
    if usage.calls >= settings.trial_calls or left < 30:
        raise QuotaExceeded("Ya usaste las llamadas de prueba a tu celular. Con un plan pago, tu agente atiende "
                            "y llama de verdad.", "trial_calls")
    if quota.busy_channels(s) >= settings.anura_channels:
        raise QuotaExceeded("Las líneas están ocupadas. Probá en unos minutos.", "no_channel")
    return await calls_service.start_call(s, engine, principal, calls_service.CallRequest(
        agent_id=agent.id, phone=user.phone, trial=True, max_duration_seconds=left))

