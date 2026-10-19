"""Entrega del webhook de las campañas (docs/LLAMADAS_SALIENTES_PLAN.md, seccion 8).

Una tarea aparte del loop de las campañas (main.py): un webhook lento o caido no frena el envio ni el
marcado. Cada CAMPAIGN_CALLBACK_TICK_SECONDS toma los eventos pendientes de la cola (campaign_callbacks,
services/campaign_callbacks.py) y hace un POST firmado por cada uno:

- Cuerpo JSON: `event`, `delivery_id` (el mismo en los reintentos), `created_at`, `campaign` y, en los
  eventos por contacto, `contact` con los campos del reporte (services/campaign_reports.py). El de la
  campaña que termina lleva `progress`, `results` y los indicadores (`stats`).
- Headers: `X-Atentina-Event`, `X-Atentina-Delivery` y `X-Atentina-Signature: sha256=<hmac del cuerpo>`.
- Exito: cualquier 2xx. Sin respuesta, error o otro codigo: reintento con espera creciente
  (30 s, 2 min, 10 min, 1 h, 6 h) hasta CAMPAIGN_CALLBACK_MAX_ATTEMPTS; despues queda `failed`.
- No sigue redirecciones. Resuelve el host al entregar, exige una IP publica y se conecta a esa IP
  (SNI y Host originales): ver services/campaign_callbacks.py.
- El evento se reclama (se corre su proximo intento) antes de enviarlo: con dos copias de la app, o un
  reinicio en el medio, no se entrega dos veces a la vez.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..agents.definitions import DefinitionSource
from ..config import settings
from ..db import utcnow
from ..models import Campaign, CampaignCallback
from ..runtime import get_conversation_engine
from ..services import campaign_callbacks as callbacks
from ..services import campaign_reports
from ..services import campaigns as common
from ..services.reports import iso
from ..whatsapp.crypto import TokenKeyMissing

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = (30, 120, 600, 3600, 21600)
BATCH = 20
CONCURRENCY = 5
LEASE_SECONDS = 120     # lo que tiene para entregarse un evento reclamado antes de que otro lo tome


def backoff(attempts: int) -> datetime.timedelta:
    """Espera antes del intento que sigue a `attempts` fallidos."""
    return datetime.timedelta(seconds=BACKOFF_SECONDS[min(attempts, len(BACKOFF_SECONDS)) - 1])


def payload(s: Session, row: CampaignCallback, c: Campaign, definitions: DefinitionSource) -> dict:
    """El cuerpo del POST de un evento."""
    body = {"event": row.event, "delivery_id": row.id, "created_at": iso(row.created_at),
            "campaign": {"id": c.id, "name": c.name, "channel": c.channel, "status": c.status,
                         "status_reason": c.status_reason, "purpose": c.purpose}}
    if row.campaign_contact_id is not None:
        rows = campaign_reports.report_rows(s, c, definitions, [row.campaign_contact_id])
        body["contact"] = rows[0] if rows else None
    else:
        progress = common.progress(s, [c.id])[c.id]
        body["campaign"].update({
            "total": sum(progress.values()), "progress": progress, "percent": common.percent(progress),
            "started_at": iso(c.started_at), "finished_at": iso(c.finished_at),
            "stats": campaign_reports.stats(s, c, definitions)})
    return body


class CallbackDispatcher:
    def __init__(self, sessions: sessionmaker[Session], definitions: Callable[[], DefinitionSource] | None = None,
                 now: Callable[[], datetime.datetime] = utcnow, client_factory: Callable[[], httpx.AsyncClient] | None = None,
                 resolve: Callable[[str, int | None], str] = callbacks.resolve_public):
        self.sessions = sessions
        self._definitions = definitions or (lambda: get_conversation_engine().definitions)
        self.now = now
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(
            timeout=settings.campaign_callback_timeout_seconds, follow_redirects=False))
        self._resolve = resolve

    def _claim(self) -> list[str]:
        """Los eventos que toca entregar; quedan reclamados (su proximo intento, dentro de LEASE_SECONDS)."""
        now = self.now()
        with self.sessions() as s:
            rows = list(s.scalars(
                select(CampaignCallback)
                .where(CampaignCallback.status == "pending", CampaignCallback.next_attempt_at <= now)
                .order_by(CampaignCallback.next_attempt_at, CampaignCallback.created_at, CampaignCallback.id)
                .limit(BATCH)
                .with_for_update(skip_locked=True)))
            for r in rows:
                r.next_attempt_at = now + datetime.timedelta(seconds=LEASE_SECONDS)
            s.commit()
            return [r.id for r in rows]

    def _prepare(self, callback_id: str) -> tuple[str, bytes, dict[str, str]] | None:
        """(url, cuerpo, headers) del evento, o None si ya no hay nada que entregar (queda registrado)."""
        with self.sessions() as s:
            row = s.get(CampaignCallback, callback_id)
            if row is None or row.status != "pending":
                return None
            c = s.get(Campaign, row.campaign_id)
            secret = None
            try:
                secret = callbacks.secret_of(c) if c is not None and c.callback_url else None
            except TokenKeyMissing as e:      # WA_TOKEN_KEY ausente o cambiada
                self._fail(s, row, f"No se pudo descifrar el secreto: {e}"[:255], final=True)
                return None
            if c is None or not c.callback_url or not secret:
                self._fail(s, row, "La campaña ya no tiene webhook", final=True)
                return None
            body = json.dumps(payload(s, row, c, self._definitions()), ensure_ascii=False, separators=(",", ":"),
                              default=str).encode()
            headers = {"Content-Type": "application/json", "User-Agent": "atentina-webhook/1",
                       "X-Atentina-Event": row.event, "X-Atentina-Delivery": row.id,
                       callbacks.SIGNATURE_HEADER: callbacks.sign(secret, body)}
            return c.callback_url, body, headers

    def _fail(self, s: Session, row: CampaignCallback, error: str, status_code: int | None = None,
              final: bool = False) -> None:
        row.attempts += 1
        row.last_error, row.last_status_code = error[:255], status_code
        if final or row.attempts >= settings.campaign_callback_max_attempts:
            row.status = "failed"
            logger.warning("webhook de campaña %s: evento %s (%s) sin entregar: %s", row.campaign_id, row.id,
                           row.event, error)
        else:
            row.next_attempt_at = self.now() + backoff(row.attempts)
        s.commit()

    def _record(self, callback_id: str, status_code: int | None, error: str | None) -> None:
        with self.sessions() as s:
            row = s.get(CampaignCallback, callback_id)
            if row is None:
                return
            if error is None:
                row.status, row.attempts, row.delivered_at = "sent", row.attempts + 1, self.now()
                row.last_status_code, row.last_error = status_code, None
                s.commit()
            else:
                self._fail(s, row, error, status_code)

    async def _deliver(self, client: httpx.AsyncClient, callback_id: str) -> bool:
        prepared = await asyncio.to_thread(self._prepare, callback_id)
        if prepared is None:
            return False
        url, body, headers = prepared
        parsed = urlparse(url)
        status_code, error, extensions = None, None, {}
        try:
            if not settings.campaign_callback_allow_private:
                ip = await asyncio.to_thread(self._resolve, parsed.hostname or "", parsed.port)
                host = f"[{ip}]" if ":" in ip else ip
                url = parsed._replace(netloc=host + (f":{parsed.port}" if parsed.port else "")).geturl()
                headers["Host"] = parsed.netloc
                extensions["sni_hostname"] = parsed.hostname
            response = await client.post(url, content=body, headers=headers, extensions=extensions)
            status_code = response.status_code
            if not 200 <= status_code < 300:
                error = f"El webhook respondió {status_code}"
        except ValueError as e:      # host privado o que no resuelve
            error = f"Host no permitido: {e}"
        except httpx.HTTPError as e:
            error = f"{type(e).__name__}: {e}"[:255] or type(e).__name__
        await asyncio.to_thread(self._record, callback_id, status_code, error)
        return error is None

    async def tick(self) -> int:
        """Una vuelta: entrega lo pendiente. Devuelve cuantos eventos se entregaron."""
        ids = await asyncio.to_thread(self._claim)
        if not ids:
            return 0
        sem = asyncio.Semaphore(CONCURRENCY)

        async def one(client: httpx.AsyncClient, callback_id: str) -> bool:
            async with sem:
                try:
                    return await self._deliver(client, callback_id)
                except Exception:
                    logger.exception("webhook de campaña: fallo el evento %s", callback_id)
                    return False

        async with self._client_factory() as client:
            return sum(await asyncio.gather(*(one(client, i) for i in ids)))


_dispatcher: CallbackDispatcher | None = None


def get_dispatcher() -> CallbackDispatcher:
    global _dispatcher
    if _dispatcher is None:
        from ..db import get_sessionmaker
        _dispatcher = CallbackDispatcher(get_sessionmaker())
    return _dispatcher


async def callback_loop() -> None:
    """Corre en la app (lifespan), aparte de campaign_loop."""
    dispatcher = get_dispatcher()
    while True:
        await asyncio.sleep(settings.campaign_callback_tick_seconds)
        try:
            await dispatcher.tick()
        except Exception:
            logger.exception("webhook de campaña: fallo la vuelta de entrega")

