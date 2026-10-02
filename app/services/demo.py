import asyncio
import datetime
import secrets
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.definitions import DefinitionSource
from ..config import settings
from ..conversation.engine import ConversationEngine
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    Agent,
    CallMode,
    CallRow,
    Client,
    ConversationRow,
    Role,
)
from . import calls, livekit, quota, tts
from .errors import Forbidden, Invalid, NotFound, QuotaExceeded, ServiceError, Upstream
from .ratelimit import Limit, RateLimiter, client_key
from .reports import Reports
from .security import Principal

SESSION_AUDIENCE = "atentina-demo"
CALL_AUDIENCE = "atentina-demo-call"
SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
RESULT_TTL = datetime.timedelta(hours=2)
TOKEN_MARGIN_SECONDS = 120
TTS_CACHE_ENTRIES = 32
TTS_CACHE_MAX_BYTES = 2_000_000
HOUR, DAY = 3600, 86_400

limiter = RateLimiter()
_tts_cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()


class DemoUnavailable(ServiceError):
    status_code = 503
    default_code = "demo_unavailable"


class SessionRequired(ServiceError):
    status_code = 401
    default_code = "session_required"


@dataclass
class DemoCall:
    conversation_id: str
    room: str
    livekit_url: str
    token: str
    max_duration_seconds: int
    result_token: str


def ensure_enabled() -> None:
    if not settings.turnstile_secret_key:
        raise DemoUnavailable("La demo no está disponible en este momento")


def allowed_origins() -> list[str]:
    return [o.strip().rstrip("/") for o in settings.demo_allowed_origins.split(",") if o.strip()]


def _encode(claims: dict, ttl: datetime.timedelta) -> str:
    now = datetime.datetime.now(datetime.UTC)
    return jwt.encode({**claims, "iat": now, "exp": now + ttl}, settings.auth_secret, algorithm="HS256")


def _decode(token: str | None, audience: str) -> dict | None:
    if not token:
        return None
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=["HS256"], audience=audience,
                          options={"require": ["exp", "aud"]})
    except jwt.PyJWTError:
        return None


async def verify_turnstile(token: str, ip: str | None) -> bool:
    data = {"secret": settings.turnstile_secret_key, "response": token, "idempotency_key": str(uuid.uuid4())}
    if ip:
        data["remoteip"] = ip
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(SITEVERIFY_URL, data=data)
            r.raise_for_status()
    except httpx.HTTPError as e:
        raise Upstream("No se pudo verificar el captcha") from e
    return bool(r.json().get("success"))


async def create_session(turnstile_token: str, ip: str) -> tuple[str, int]:
    ensure_enabled()
    key = f"session:{client_key(ip)}"
    limiter.check(key, [Limit(settings.demo_ip_sessions_per_hour, HOUR)], "Demasiados intentos. Probá más tarde.")
    if not await verify_turnstile(turnstile_token, ip):
        raise Forbidden("No pudimos verificar que seas una persona. Recargá la página.", "captcha_failed")
    limiter.hit(key)
    ttl = datetime.timedelta(minutes=settings.demo_session_minutes)
    return _encode({"aud": SESSION_AUDIENCE, "sid": secrets.token_urlsafe(12)}, ttl), int(ttl.total_seconds())


def require_session(token: str | None) -> str:
    ensure_enabled()
    claims = _decode(token, SESSION_AUDIENCE)
    if claims is None:
        raise SessionRequired("La sesión de la demo venció. Volvé a intentar.")
    return claims["sid"]


def _day_start(now: datetime.datetime) -> datetime.datetime:
    tz = ZoneInfo(settings.billing_timezone)
    local = now.replace(tzinfo=datetime.UTC).astimezone(tz)
    start = datetime.datetime.combine(local.date(), datetime.time(), tz)
    return start.astimezone(datetime.UTC).replace(tzinfo=None)


def demo_agent_slugs() -> list[str]:
    return [a.strip() for a in settings.demo_agents.split(",") if a.strip()]


def _demo_agent(s: Session, slug: str) -> tuple[str, str, tuple[str, ...]]:
    """(agente, cliente, todos los agentes de la demo). Solo los de DEMO_AGENTS: el cliente es
    el de Atentina y tiene otros agentes que no se pueden llamar desde internet."""
    client = s.scalar(select(Client).where(Client.slug == settings.demo_client))
    if client is None or not client.active:
        raise DemoUnavailable("La demo no está disponible en este momento")
    demo_agents = {a.slug: a.id for a in s.scalars(select(Agent).where(
        Agent.client_id == client.id, Agent.slug.in_(demo_agent_slugs()), Agent.archived_at.is_(None)))}
    if slug not in demo_agents:
        raise NotFound("Agente inexistente")
    group = tuple(demo_agents.values())
    now = utcnow()
    start = _day_start(now)
    used = quota.used_seconds(s, client.id, CallMode.prueba, start, start + datetime.timedelta(days=1), now,
                              agent_ids=group)
    if used >= settings.demo_daily_minutes * 60:
        raise QuotaExceeded("Por hoy se terminaron las llamadas de prueba. Volvé mañana.", "daily_budget")
    return demo_agents[slug], client.id, group


async def start_call(s: Session, engine: ConversationEngine, agent_slug: str, voice: str | None,
                     ip: str) -> DemoCall:
    key = f"call:{client_key(ip)}"
    limiter.check(key, [Limit(settings.demo_ip_calls_per_hour, HOUR), Limit(settings.demo_ip_calls_per_day, DAY)],
                  "Llegaste al límite de llamadas de prueba. Probá más tarde.")
    agent_id, client_id, group = await asyncio.to_thread(_demo_agent, s, agent_slug)
    principal = Principal("demo", settings.demo_client, Role.client, client_id)
    started = await calls.start_call(s, engine, principal, calls.CallRequest(
        agent_id=agent_id, voice=voice, max_duration_seconds=settings.demo_call_max_seconds,
        join_timeout_seconds=settings.demo_join_timeout_seconds, group_agent_ids=group,
        group_max_concurrent=settings.demo_max_concurrent_calls))
    limiter.hit(key)
    ttl = datetime.timedelta(seconds=settings.demo_join_timeout_seconds + settings.demo_call_max_seconds
                             + TOKEN_MARGIN_SECONDS)
    token = livekit.participant_token(started.room, f"visitante-{started.conversation_id[:8]}", "Visitante", ttl)
    return DemoCall(
        conversation_id=started.conversation_id, room=started.room,
        livekit_url=settings.demo_livekit_url or settings.livekit_url, token=token,
        max_duration_seconds=settings.demo_call_max_seconds,
        result_token=_encode({"aud": CALL_AUDIENCE, "sub": started.conversation_id}, RESULT_TTL))


def call_result(s: Session, definitions: DefinitionSource, conversation_id: str, token: str | None) -> dict:
    claims = _decode(token, CALL_AUDIENCE)
    if claims is None or claims.get("sub") != conversation_id:
        raise SessionRequired("Sin acceso a esta llamada")
    conv = s.get(ConversationRow, conversation_id)
    call = s.get(CallRow, conversation_id)
    if conv is None or call is None:
        raise NotFound("Llamada inexistente")
    reports = Reports(s, definitions)
    workflow = reports.workflow(conv)
    outcome = reports.outcome(workflow, conv)
    specs = sorted(workflow.fields.items(), key=lambda kv: kv[1].priority) if workflow else []
    return {
        "final": call.status not in ACTIVE_CALL_STATUSES,
        "status": call.status,
        "ended_reason": call.ended_reason,
        "duration_seconds": call.duration_seconds,
        "agent_name": workflow.agent.name if workflow else "",
        "completed": conv.status == "completed",
        "outcome": None if outcome is None else {"label": outcome.label, "goal": outcome.goal},
        "fields": [{"name": name, "label": spec.label or name.replace("_", " ").capitalize(), "type": spec.type,
                    "value": conv.fields.get(name)} for name, spec in specs],
        "messages": [{"role": m["role"], "text": m["text"]} for m in conv.messages or []],
    }


def _cache_put(key: tuple[str, str], audio: bytes) -> None:
    if len(audio) > TTS_CACHE_MAX_BYTES:
        return
    _tts_cache[key] = audio
    _tts_cache.move_to_end(key)
    while len(_tts_cache) > TTS_CACHE_ENTRIES:
        _tts_cache.popitem(last=False)


async def synthesize(voice: str, text: str, ip: str) -> AsyncIterator[bytes]:
    text = " ".join(text.split())
    if len(text) > settings.demo_tts_max_chars:
        raise Invalid(f"El texto puede tener hasta {settings.demo_tts_max_chars} caracteres")
    key = (voice.strip().lower(), text)
    limiter.consume(f"tts:{client_key(ip)}", [Limit(settings.demo_ip_tts_per_hour, HOUR)],
                    "Llegaste al límite de pruebas de voz. Probá más tarde.")
    cached = _tts_cache.get(key)
    if cached is not None:
        _tts_cache.move_to_end(key)

        async def replay() -> AsyncIterator[bytes]:
            yield cached

        return replay()
    stream = await tts.preview(*key)

    async def caching() -> AsyncIterator[bytes]:
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
            yield chunk
        _cache_put(key, b"".join(chunks))

    return caching()
