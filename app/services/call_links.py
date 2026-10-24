"""Link publico para llamar a un agente desde el navegador (docs/LINK_LLAMADA_PLAN.md).

- Del cliente: uno activo por agente, con el tope del tier (`max_call_links`); se pausa, se
  regenera (revoca y crea otro con la misma config) o se revoca.
- Publico (https://<CALL_LINK_HOST>/<token>): la pagina lee `public_view` y la llamada arranca con
  `start_call` (Turnstile, limites por IP, cupo diario y concurrencia del link, y los del tier). Es una
  llamada `web`: consume minutos entrantes.
- Imagen (opcional): se recorta al cuadrado, se achica a 512 px y se recodifica (PNG si tiene
  transparencia, si no JPEG) en CALL_LINK_IMAGES_DIR; la sirve la API publica del link.
- Los errores publicos no hablan del plan ni de minutos (quien llama no es el cliente): `busy` (429),
  `ip_limit` (429), `unavailable` (503) y 404. El motivo real queda en el log.
"""
import asyncio
import datetime
import io
import logging
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..db import utcnow
from ..models import (
    ACTIVE_CALL_STATUSES,
    Agent,
    CallLink,
    CallRow,
    CallStatus,
    Client,
    Role,
)
from . import calls, livekit, quota
from . import demo as demo_service
from . import limits as limits_service
from .errors import Conflict, Forbidden, Invalid, NotFound, QuotaExceeded, ServiceError
from .ratelimit import Limit, RateLimiter, client_key
from .security import Principal

logger = logging.getLogger(__name__)

HOUR, DAY = 3600, 86_400
TOKEN_BYTES = 9          # 12 caracteres de base64url, 72 bits
TOKEN_MARGIN_SECONDS = 120
# Lo que se puede cambiar de un link (PATCH): textos, topes y pausa.
EDITABLE = ("display_name", "company_name", "subtitle", "max_call_seconds", "max_concurrent", "daily_minutes",
            "paused")
# Codigos de QuotaExceeded que se le dicen a quien llama como "ocupado" (el resto, "no disponible").
BUSY_CODES = {"concurrency_limit", "link_concurrency_limit", "link_global_limit"}
# Imagen: lo que se acepta y como se guarda.
IMAGE_MAX_BYTES = 5 * 1024 * 1024    # el mismo de app/api/http.py (BodyLimitMiddleware)
IMAGE_MAX_PIXELS = 40_000_000     # antes de decodificar: corta las "bombas" de descompresion
IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}
IMAGE_SIZE = 512
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg"}

limiter = RateLimiter()


class LinkUnavailable(ServiceError):
    status_code = 503
    default_code = "unavailable"


class LinkBusy(ServiceError):
    status_code = 429
    default_code = "busy"


UNAVAILABLE = "Este canal no está disponible en este momento."
BUSY = "Todas las líneas están ocupadas. Probá en unos minutos."


def enabled() -> bool:
    """La pagina publica necesita Turnstile (las dos claves) y la URL de LiveKit para navegadores."""
    return bool(settings.turnstile_secret_key and settings.turnstile_site_key
                and (settings.demo_livekit_url or settings.livekit_url))


def base_url() -> str:
    if settings.call_link_base_url:
        return settings.call_link_base_url.rstrip("/")
    panel = next((o.strip().rstrip("/") for o in settings.app_origins.split(",") if o.strip()), "")
    return f"{panel}/llamar"


def url_for_token(token: str) -> str:
    return f"{base_url()}/{token}"


def url(link: CallLink) -> str:
    return url_for_token(link.token)


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def image_url(link: CallLink) -> str | None:
    """Por la API publica del link (pasa por el host `llamar.`); `v` cambia con cada imagen."""
    if not link.image:
        return None
    return f"/api/v1/public/call-links/{link.token}/image?v={Path(link.image).stem[:8]}"


def absolute_url(path: str) -> str:
    """Un path de la API publica con el origen de los links (og:image tiene que ser absoluta)."""
    parsed = urlparse(base_url())
    return f"{parsed.scheme}://{parsed.netloc}{path}"


# ---------- del cliente ----------

def for_agent(s: Session, agent_id: str) -> CallLink | None:
    return s.scalar(select(CallLink).where(CallLink.agent_id == agent_id, CallLink.revoked_at.is_(None)))


def urls_by_agent(s: Session, agent_ids: list[str]) -> dict[str, str]:
    """URL del link activo de cada agente que tiene uno (para la lista de agentes)."""
    if not agent_ids:
        return {}
    links = s.scalars(select(CallLink).where(CallLink.agent_id.in_(agent_ids), CallLink.revoked_at.is_(None)))
    return {link.agent_id: url(link) for link in links}


def active_count(s: Session, client_id: str) -> int:
    return s.scalar(select(func.count()).select_from(CallLink).where(
        CallLink.client_id == client_id, CallLink.revoked_at.is_(None))) or 0


def _check_seconds(value: int | None) -> None:
    if value is not None and value > settings.call_max_duration_seconds:
        raise Conflict(f"La duración máxima no puede pasar de {settings.call_max_duration_seconds} segundos",
                       "max_call_seconds")


def create(s: Session, agent: Agent, user_id: str | None, **fields) -> CallLink:
    if agent.archived_at is not None:
        raise Conflict("El agente está archivado")
    if for_agent(s, agent.id) is not None:
        raise Conflict("El agente ya tiene un link", "call_link_exists")
    client = s.get(Client, agent.client_id)
    cap = limits_service.effective_limits(s, client).max_call_links
    if cap is not None and active_count(s, client.id) >= cap:
        message = ("Tu plan no incluye links para llamar" if cap == 0
                   else f"Tu plan incluye {cap} link{'s' if cap != 1 else ''} para llamar")
        raise QuotaExceeded(message, "call_links_limit")
    values = {k: v for k, v in fields.items() if k in EDITABLE and v is not None}
    _check_seconds(values.get("max_call_seconds"))
    values.setdefault("max_call_seconds", min(settings.call_link_default_seconds, settings.call_max_duration_seconds))
    link = CallLink(client_id=agent.client_id, agent_id=agent.id, token=new_token(), created_by=user_id, **values)
    s.add(link)
    s.flush()
    return link


def update(s: Session, link: CallLink, fields: dict) -> CallLink:
    """`fields`: solo lo que vino en el pedido (un None explicito en un tope lo deja sin tope)."""
    for key, value in fields.items():
        if key not in EDITABLE:
            continue
        if key in ("display_name", "company_name", "subtitle"):
            value = (value or "").strip()
        if key in ("max_call_seconds", "paused") and value is None:
            continue
        if key == "max_call_seconds":
            _check_seconds(value)
        setattr(link, key, value)
    s.flush()
    return link


def rotate(s: Session, link: CallLink, user_id: str | None) -> CallLink:
    """Revoca el link y crea otro con la misma config: el viejo deja de andar (404)."""
    link.revoked_at = utcnow()
    s.flush()
    new = CallLink(client_id=link.client_id, agent_id=link.agent_id, token=new_token(), created_by=user_id,
                   image=link.image, **{k: getattr(link, k) for k in EDITABLE})
    s.add(new)
    s.flush()
    return new


def revoke(s: Session, link: CallLink) -> None:
    link.revoked_at = utcnow()
    s.flush()
    _drop_image(s, link.image)


# ---------- imagen ----------

def _encode_image(data: bytes) -> tuple[bytes, str]:
    """Recorte cuadrado al centro, hasta IMAGE_SIZE px, recodificada (no queda nada del archivo original)."""
    if len(data) > IMAGE_MAX_BYTES:
        raise Invalid("La imagen pasa de 5 MB", "image_too_large")
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in IMAGE_FORMATS:
                raise Invalid("La imagen tiene que ser PNG, JPG o WebP", "image_format")
            if img.width * img.height > IMAGE_MAX_PIXELS:
                raise Invalid("La imagen es demasiado grande", "image_too_large")
            img = ImageOps.exif_transpose(img)
            side = min(IMAGE_SIZE, img.width, img.height)
            alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
            img = ImageOps.fit(img.convert("RGBA" if alpha else "RGB"), (side, side), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            if alpha:
                img.save(out, "PNG", optimize=True)
                return out.getvalue(), ".png"
            img.save(out, "JPEG", quality=88, progressive=True)
            return out.getvalue(), ".jpg"
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise Invalid("No pudimos leer la imagen. Probá con un PNG o JPG.", "image_invalid") from None


def image_path(link: CallLink) -> Path | None:
    if not link.image:
        return None
    path = settings.call_link_images_dir / link.image
    return path if path.is_file() else None


def _drop_image(s: Session, name: str | None) -> None:
    """Borra el archivo si ningun link activo lo usa (regenerar el link comparte la imagen)."""
    if not name:
        return
    in_use = s.scalar(select(func.count()).select_from(CallLink).where(
        CallLink.image == name, CallLink.revoked_at.is_(None))) or 0
    if not in_use:
        (settings.call_link_images_dir / name).unlink(missing_ok=True)


def set_image(s: Session, link: CallLink, data: bytes) -> CallLink:
    content, ext = _encode_image(data)
    name = f"{secrets.token_hex(16)}{ext}"
    settings.call_link_images_dir.mkdir(parents=True, exist_ok=True)
    (settings.call_link_images_dir / name).write_bytes(content)
    old, link.image = link.image, name
    s.flush()
    _drop_image(s, old)
    return link


def remove_image(s: Session, link: CallLink) -> CallLink:
    old, link.image = link.image, None
    s.flush()
    _drop_image(s, old)
    return link


@dataclass
class LinkUsage:
    calls_today: int
    seconds_today: int
    seconds_month: int


def _link_seconds(s: Session, link_id: str, start: datetime.datetime, now: datetime.datetime) -> int:
    in_period = (CallRow.call_link_id == link_id, CallRow.started_at >= start)
    done = s.scalar(select(func.coalesce(func.sum(CallRow.duration_seconds), 0))
                    .where(*in_period, CallRow.status.notin_(ACTIVE_CALL_STATUSES))) or 0
    running = s.scalars(select(CallRow.started_at).where(*in_period, CallRow.status.in_(ACTIVE_CALL_STATUSES)))
    return int(done) + sum(max(int((now - t).total_seconds()), 0) for t in running)


def usage(s: Session, link: CallLink, now: datetime.datetime | None = None) -> LinkUsage:
    """Llamadas y segundos de este link (no suma los links anteriores del agente, ya revocados)."""
    now = now or utcnow()
    day = quota.period_start("day", now)
    calls_today = s.scalar(select(func.count()).select_from(CallRow).where(
        CallRow.call_link_id == link.id, CallRow.created_at >= day,
        CallRow.status != CallStatus.rechazada)) or 0
    return LinkUsage(calls_today=calls_today, seconds_today=_link_seconds(s, link.id, day, now),
                     seconds_month=_link_seconds(s, link.id, quota.period_start("month", now), now))


# ---------- publico ----------

@dataclass
class PublicView:
    token: str
    display_name: str
    company_name: str
    subtitle: str
    image_url: str | None
    max_call_seconds: int
    records_audio: bool
    available: bool


@dataclass
class LinkCall:
    livekit_url: str
    token: str
    max_call_seconds: int


def _resolve(s: Session, token: str) -> tuple[CallLink, Agent, Client]:
    link = s.scalar(select(CallLink).where(CallLink.token == token, CallLink.revoked_at.is_(None)))
    agent = s.get(Agent, link.agent_id) if link else None
    client = s.get(Client, link.client_id) if link else None
    if link is None or agent is None or client is None or agent.archived_at is not None:
        raise NotFound("Este link ya no está activo.", "link_not_found")
    return link, agent, client


def public_view(s: Session, token: str) -> PublicView:
    link, agent, client = _resolve(s, token)
    definition = agent.definition or {}
    return PublicView(
        token=link.token,
        display_name=link.display_name or (definition.get("agent") or {}).get("name") or agent.name,
        company_name=link.company_name or client.name,
        subtitle=link.subtitle,
        image_url=image_url(link),
        max_call_seconds=link.max_call_seconds,
        records_audio=bool(definition.get("record_audio")),
        available=enabled() and client.active and not link.paused,
    )


def public_image(s: Session, token: str) -> Path:
    link, _, _ = _resolve(s, token)
    path = image_path(link)
    if path is None:
        raise NotFound("El link no tiene imagen", "image_not_found")
    return path


def _check_daily(s: Session, link: CallLink) -> None:
    if link.daily_minutes is None:
        return
    now = utcnow()
    if _link_seconds(s, link.id, quota.period_start("day", now), now) >= link.daily_minutes * 60:
        raise QuotaExceeded("Cupo diario del link agotado", "link_daily_minutes")


async def start_call(s: Session, engine: ConversationEngine, token: str, turnstile_token: str, ip: str) -> LinkCall:
    if not enabled():
        raise LinkUnavailable(UNAVAILABLE, "unavailable")
    key = f"call:{client_key(ip)}:{token}"
    limiter.check(key, [Limit(settings.call_link_ip_calls_per_hour, HOUR),
                        Limit(settings.call_link_ip_calls_per_day, DAY)],
                  "Hiciste varias llamadas seguidas. Probá más tarde.")
    link, agent, client = await asyncio.to_thread(_resolve, s, token)
    if link.paused or not client.active:
        raise LinkUnavailable(UNAVAILABLE, "unavailable")
    if not await demo_service.verify_turnstile(turnstile_token, ip):
        raise Forbidden("No pudimos verificar que seas una persona. Recargá la página.", "captcha_failed")
    principal = Principal("link", link.id, Role.client, link.client_id)
    try:
        await asyncio.to_thread(_check_daily, s, link)
        started = await calls.start_call(s, engine, principal, calls.CallRequest(
            agent_id=agent.id, max_duration_seconds=link.max_call_seconds,
            join_timeout_seconds=settings.call_link_join_timeout_seconds,
            call_link_id=link.id, link_max_concurrent=link.max_concurrent))
    except QuotaExceeded as e:
        logger.info("link %s (cliente %s): llamada rechazada (%s)", link.id, client.slug, e.code)
        if e.code in BUSY_CODES:
            raise LinkBusy(BUSY) from None
        raise LinkUnavailable(UNAVAILABLE) from None
    limiter.hit(key)
    ttl = datetime.timedelta(seconds=settings.call_link_join_timeout_seconds + link.max_call_seconds
                             + TOKEN_MARGIN_SECONDS)
    lk_token = livekit.participant_token(started.room, f"web-{started.conversation_id[:8]}", "Visitante", ttl)
    return LinkCall(livekit_url=settings.demo_livekit_url or settings.livekit_url, token=lk_token,
                    max_call_seconds=link.max_call_seconds)

