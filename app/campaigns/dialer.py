"""Dialer de las campañas de voz (docs/features/CAMPANAS.md): cada
CALL_CAMPAIGN_TICK_SECONDS, por cada campaña `running`, marca los contactos que le tocan.

Cada vuelta activa las programadas cuyo starts_at llego y termina las que pasaron ends_at
(services/campaigns.py, roll_schedule). Por campaña:
- Fuera del horario o de los dias permitidos no hace nada (no acumula credito).
- Cupo = min(concurrency (la de la campaña, con el tope del plan vigente) - en curso, credito de rate_per_minute, parte de lo que queda del
  CALL_CAMPAIGN_MAX_CONCURRENT). "En curso" son los contactos `in_progress`. El tope global se reparte
  con equidad: las campañas van por turno (primero la que hace mas que no marca) y cada una toma, a lo
  sumo, su parte de los lugares libres (libres / campañas que faltan), asi una con mucha concurrencia no
  deja sin servicio a las demas.
- Toma `pending`/`retry` con next_attempt_at vencido con FOR UPDATE SKIP LOCKED y los pasa a `in_progress`
  (commit) antes de llamar: con dos copias de la app no hay doble marcado, y un reinicio en el medio
  no los pierde (recover). Los de baja (contact_optouts) o archivados se saltean.
- Llama a services/calls.start_call (con los limites del tier, como cualquier saliente). El worker
  cierra el intento al terminar (services/campaign_calls.py).
  - Sin lugar por concurrencia: el contacto vuelve a `pending` sin gastar el intento y la campaña espera.
  - Sin minutos, tope de llamadas o cliente inactivo, o el agente o el numero ya no estan: vuelve a
    `pending` y la campaña se pausa con el motivo.
  - Numero invalido: ese contacto queda `failed` (`invalid`). Falla del despacho: intento `failed`.
- N intentos `failed` seguidos pausan la campaña (campaign_calls.close_contact).
- Tampoco marca en feriados (CAMPAIGN_HOLIDAYS): `in_window` de voz los cuenta como fuera de horario.

Supone un solo worker de uvicorn, como el sender (el credito vive en memoria); el claim con SKIP LOCKED
cubre una copia de mas.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import time
from collections.abc import Callable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..conversation.engine import ConversationEngine
from ..db import utcnow
from ..models import Campaign, CampaignContact, Client, Role
from ..runtime import get_conversation_engine
from ..services import calls as call_service
from ..services import campaign_callbacks as callbacks
from ..services import campaign_calls
from ..services import campaigns as common
from ..services import contacts as contacts_service
from ..services.errors import Conflict, Invalid, NotFound, QuotaExceeded, Upstream
from ..services.security import Principal

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = 10.0      # sin lugar por concurrencia: la campaña espera antes de volver a probar
RECOVER_EVERY_SECONDS = 60.0
RECOVER_GRACE_SECONDS = 120     # no se recupera lo que se reclamo hace menos (se esta marcando)


class Dialer:
    def __init__(self, sessions: sessionmaker[Session],
                 engine: Callable[[], ConversationEngine] = get_conversation_engine,
                 now: Callable[[], datetime.datetime] = utcnow, clock: Callable[[], float] = time.monotonic,
                 start_call=call_service.start_call):
        self.sessions = sessions
        self._engine = engine
        self.now = now          # UTC naive: ventanas, programacion y reintentos
        self.clock = clock      # monotonico: ritmo
        self._start_call = start_call
        self._credit: dict[str, float] = {}
        self._last: dict[str, float] = {}
        self._wait_until: dict[str, float] = {}
        self._dialed_at: dict[str, int] = {}      # numero de turno de la ultima vez que cada campaña tomo contactos
        self._turn = 0
        self._recovered_at: float | None = None

    def recover(self, grace_seconds: int = 0) -> int:
        """Al arrancar (y cada tanto): los intentos en vuelo cuya llamada ya no esta activa vuelven a `retry`."""
        with self.sessions() as s:
            n = campaign_calls.recover_in_progress(s, self.now(), grace_seconds)
            s.commit()
        return n

    async def tick(self) -> int:
        """Una vuelta: marca lo que toca de cada campaña en curso. Devuelve cuantas llamadas inicio."""
        if self._recovered_at is None or self.clock() - self._recovered_at >= RECOVER_EVERY_SECONDS:
            self._recovered_at = self.clock()
            try:
                if n := await asyncio.to_thread(self.recover, RECOVER_GRACE_SECONDS):
                    logger.warning("campañas de voz: %d intentos sin llamada activa vuelven a reintento", n)
            except Exception:
                logger.exception("campañas de voz: fallo la recuperacion de intentos")
        with self.sessions() as s:
            if common.roll_schedule(s, ("voice",), self.now()):      # programadas que arrancan, vencidas que terminan
                s.commit()
            running = [c.id for c in s.scalars(select(Campaign).where(Campaign.channel == "voice",
                                                                      Campaign.status == "running")
                                               .order_by(Campaign.created_at, Campaign.id))]
        for gone in (set(self._last) | set(self._dialed_at)) - set(running):
            self._forget(gone)
        running.sort(key=lambda cid: self._dialed_at.get(cid, 0))     # estable: el turno es de la que hace mas que no marca
        started = 0
        for i, campaign_id in enumerate(running):
            try:
                started += await self._run(campaign_id, len(running) - i)
            except Exception:
                logger.exception("campañas de voz: fallo la campaña %s", campaign_id)
        return started

    def _forget(self, campaign_id: str) -> None:
        for d in (self._credit, self._last, self._wait_until, self._dialed_at):
            d.pop(campaign_id, None)

    def _allowance(self, c: Campaign) -> int:
        """Cuantas le tocan por ritmo: credito que crece a rate_per_minute, con tope de un minuto."""
        now = self.clock()
        last = self._last.get(c.id)
        elapsed = settings.call_campaign_tick_seconds if last is None else now - last
        self._last[c.id] = now
        credit = min(float(c.rate_per_minute), self._credit.get(c.id, 0.0) + c.rate_per_minute * elapsed / 60)
        self._credit[c.id] = credit
        return int(credit)

    def _claim(self, campaign_id: str, left: int = 1) -> list[str]:
        """Pasa a `in_progress` los contactos que toca marcar y devuelve sus ids. `left`: campañas que
        faltan en esta vuelta, contando esta (reparte el tope global)."""
        with self.sessions() as s:
            c = s.get(Campaign, campaign_id)
            if c is None or c.status != "running":
                return []
            now = self.now()
            if not common.in_window(c, now):
                self._forget(c.id)      # fuera de horario o de los dias permitidos no acumula credito
                return []
            client = s.get(Client, c.client_id)
            if client is None or not client.active:
                common.pause(s, c, "El cliente está inactivo")
                s.commit()
                return []
            # El plan se mira en cada vuelta, no solo al iniciar: si bajo despues, rige el tope nuevo.
            concurrency = c.concurrency or 1
            cap = common.effective(s, c.client_id).max_campaign_concurrency
            if cap is not None:
                if cap < 1:
                    common.pause(s, c, "Tu plan no incluye llamadas simultáneas en campañas")
                    s.commit()
                    return []
                concurrency = min(concurrency, cap)
            allowance = self._allowance(c)
            if self._wait_until.get(c.id, 0) > self.clock():
                return []
            running = CampaignContact.status == "in_progress"
            mine = s.scalar(select(func.count()).select_from(CampaignContact)
                            .where(CampaignContact.campaign_id == c.id, running)) or 0
            overall = s.scalar(select(func.count()).select_from(CampaignContact)
                               .join(Campaign, Campaign.id == CampaignContact.campaign_id)
                               .where(Campaign.channel == "voice", running)) or 0
            free = settings.call_campaign_max_concurrent - overall
            room = min(concurrency - mine, -(-free // max(left, 1)), allowance)      # -(-a // b): a/b redondeado para arriba
            if room <= 0:
                return []
            due = or_(CampaignContact.next_attempt_at.is_(None), CampaignContact.next_attempt_at <= now)
            rows = list(s.scalars(
                select(CampaignContact)
                .where(CampaignContact.campaign_id == c.id, CampaignContact.status.in_(("pending", "retry")), due)
                .order_by(func.coalesce(CampaignContact.next_attempt_at, CampaignContact.created_at),
                          CampaignContact.id)
                .limit(room).with_for_update(skip_locked=True, of=CampaignContact)))
            optouts = contacts_service.opted_out_phones(s, c.client_id, "voice") if rows else set()
            ids = []
            for r in rows:
                if r.contact.archived_at is not None:     # lo archivaron despues de cargarlo
                    r.status = "skipped"
                    r.error = {"message": "El contacto fue archivado", "reason": "contact_archived"}
                    callbacks.enqueue(s, c, "contact.finished", r, now)
                elif r.contact.phone in optouts:
                    r.status, r.error = "skipped", {"message": "El contacto pidió la baja", "reason": "optout"}
                    callbacks.enqueue(s, c, "contact.finished", r, now)
                else:
                    r.status, r.attempts, r.last_attempt_at, r.next_attempt_at = "in_progress", r.attempts + 1, now, None
                    ids.append(r.id)
            if not rows or not ids:
                campaign_calls.finish_if_empty(s, c, now)
            s.commit()
            # Los salteados no gastan credito de ritmo; los que se van a marcar, si.
            self._credit[c.id] = self._credit.get(c.id, 0.0) - len(ids)
            if ids:
                self._turn += 1
                self._dialed_at[c.id] = self._turn
            return ids

    async def _run(self, campaign_id: str, left: int = 1) -> int:
        started = 0
        for contact_id in await asyncio.to_thread(self._claim, campaign_id, left):
            if await self._dial(campaign_id, contact_id):
                started += 1
        return started

    def _release(self, s: Session, campaign_id: str, contact_id: str) -> None:
        """El contacto vuelve a `pending` sin gastar el intento (la llamada no se llego a marcar)."""
        r = s.get(CampaignContact, contact_id)
        if r is not None and r.status == "in_progress":
            r.status, r.attempts = "pending", max(r.attempts - 1, 0)
        self._credit[campaign_id] = self._credit.get(campaign_id, 0.0) + 1

    def _pause(self, s: Session, c: Campaign, reason: str) -> None:
        if c.status == "running":
            common.pause(s, c, reason)
            logger.warning("campañas de voz: campaña %s pausada: %s", c.id, reason)

    async def _dial(self, campaign_id: str, contact_id: str) -> bool:
        """Inicia la llamada de un contacto reclamado. True si se despacho."""
        with self.sessions() as s:
            c = s.get(Campaign, campaign_id)
            r = s.get(CampaignContact, contact_id)
            if c is None or r is None or r.status != "in_progress":
                return False
            if c.status != "running":      # la pausaron o cancelaron en medio de la tanda
                self._release(s, campaign_id, contact_id)
                s.commit()
                return False
            req = call_service.CallRequest(
                agent_id=c.agent_id, phone=r.contact.phone, from_number_id=c.from_number_id, voice=c.voice,
                campaign_contact_id=r.id, vars=r.vars)
            principal = Principal(kind="campaign", id=c.id, role=Role.client, client_id=c.client_id)
            try:
                await self._start_call(s, self._engine(), principal, req)
                return True
            except QuotaExceeded as e:
                s.rollback()
                self._release(s, campaign_id, contact_id)
                if e.code == "concurrency_limit":
                    self._wait_until[campaign_id] = self.clock() + BACKOFF_SECONDS
                else:
                    self._pause(s, s.get(Campaign, campaign_id), e.message)
            except (Conflict, NotFound) as e:      # el agente se archivo, el numero de origen ya no esta...
                s.rollback()
                self._release(s, campaign_id, contact_id)
                self._pause(s, s.get(Campaign, campaign_id), e.message)
            except Invalid as e:
                s.rollback()
                if e.code == "invalid_phone":
                    campaign_calls.close_contact(s, contact_id, "invalid", error={"message": e.message}, now=self.now())
                else:
                    self._release(s, campaign_id, contact_id)
                    self._pause(s, s.get(Campaign, campaign_id), e.message)
            except Upstream as e:      # no se pudo despachar el worker: la llamada ya quedo fallida
                s.rollback()
                campaign_calls.close_contact(s, contact_id, "failed", error={"message": e.message, "reason": "dispatch_failed"},
                                             now=self.now())
            except Exception:
                logger.exception("campañas de voz: fallo el intento del contacto %s", contact_id)
                s.rollback()
                campaign_calls.close_contact(s, contact_id, "failed", error={"message": "Error interno al iniciar la llamada"},
                                             now=self.now())
            s.commit()
        return False


_dialer: Dialer | None = None


def get_dialer() -> Dialer:
    global _dialer
    if _dialer is None:
        from ..db import get_sessionmaker
        _dialer = Dialer(get_sessionmaker())
    return _dialer
