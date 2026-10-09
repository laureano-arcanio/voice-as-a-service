"""Envio de las campañas salientes (campaigns.py): un loop en la app que cada
WA_CAMPAIGN_TICK_SECONDS manda, por cada campaña en curso y dentro de su horario, lo que
le toca segun su ritmo (rate_per_minute, sin rafagas de mas de un minuto).

Cada envio: el contacto pasa a `sending` con un reclamo atomico (UPDATE ... WHERE status =
'pending', claimed_at) y commit antes de llamar a Meta: dos procesos no mandan el mismo, y un
reinicio en el medio no lo vuelve a mandar. recover() pasa a `failed` (con aviso) solo los
`sending` con claimed_at viejo (SENDING_STALE_SECONDS): uno fresco es un envio en curso.
Errores de Meta:
- token rechazado, cuenta bloqueada, plantilla pausada o deshabilitada, limite de spam:
  la campaña se pausa con el motivo y el contacto vuelve a pendiente;
- limite de envio momentaneo: el contacto vuelve a pendiente y la campaña espera un minuto;
- el resto (numero invalido, etc.): ese contacto queda `failed`.
Lo que Meta informa despues (entregado, leido, fallido) llega por el webhook a wa_messages.

El loop corre solo en el lider (services/leader.py); la base va en hilos (H07).
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import time
from collections.abc import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import Client, WaAccount, WaCampaign, WaCampaignRecipient
from ..services.leader import Leader, every
from . import campaigns, store
from .crypto import TokenKeyMissing
from .graph import GraphClient, GraphError
from .service import recipient

logger = logging.getLogger(__name__)

# Meta: limite momentaneo (de la app, del numero o de pares); se reintenta despues.
RETRY_CODES = {4, 80007, 130429, 131056}
# Meta: no tiene sentido seguir mandando hasta que alguien mire. 131031 cuenta bloqueada,
# 131042 problema de pago, 131048 limite por spam, 132001 la plantilla no existe, 132015 y
# 132016 plantilla pausada o deshabilitada (calidad), 368 bloqueo por politicas.
PAUSE_CODES = {131031, 131042, 131048, 132001, 132015, 132016, 368}
BACKOFF_SECONDS = 60.0
# Un `sending` con claimed_at mas viejo quedo colgado (el proceso cayo en el envio). Meta
# responde en segundos (TIMEOUT de graph.py: 15 s).
SENDING_STALE_SECONDS = 300
RECOVER_SECONDS = 60
# Motivo de la pausa, para quien mira la campaña (el codigo va al final).
PAUSE_REASONS = {
    131031: "Meta bloqueó la cuenta de WhatsApp Business",
    131042: "Meta rechazó el cobro: revisá el medio de pago en WhatsApp Manager",
    131048: "Meta frenó los envíos por posible spam (muchos bloqueos o denuncias)",
    132001: "La plantilla ya no existe en Meta",
    132015: "Meta pausó la plantilla por baja calidad (bloqueos o denuncias)",
    132016: "Meta deshabilitó la plantilla",
    368: "Meta bloqueó temporalmente la cuenta por sus políticas",
}


def local_hour(now: datetime.datetime | None = None) -> int:
    tz = ZoneInfo(settings.billing_timezone)
    return (now.astimezone(tz) if now else datetime.datetime.now(tz)).hour


class CampaignSender:
    def __init__(self, sessions: sessionmaker[Session],
                 graph_factory: Callable[[str], GraphClient] | None = None,
                 hour: Callable[[], int] = local_hour, clock: Callable[[], float] = time.monotonic):
        self.sessions = sessions
        self._graph_factory = graph_factory or (lambda token: GraphClient(token, version=settings.wa_graph_version))
        self._graphs: dict[str, GraphClient] = {}
        self.hour = hour
        self.clock = clock
        self._credit: dict[str, float] = {}
        self._last: dict[str, float] = {}
        self._wait_until: dict[str, float] = {}

    def recover(self, stale_seconds: float = SENDING_STALE_SECONDS) -> int:
        """Los que quedaron `sending` hace mas de stale_seconds (el proceso cayo en medio de un
        envio) pasan a `failed`. No se reenvian: Meta puede haberlos entregado. Los frescos son
        envios en curso (de este u otro proceso) y no se tocan."""
        before = utcnow() - datetime.timedelta(seconds=stale_seconds)
        with self.sessions() as s:
            n = s.execute(update(WaCampaignRecipient).where(
                WaCampaignRecipient.status == "sending",
                or_(WaCampaignRecipient.claimed_at.is_(None), WaCampaignRecipient.claimed_at < before))
                .values(status="failed", error={"message": "Envío interrumpido por un reinicio: puede haber llegado"})
                .execution_options(synchronize_session=False)).rowcount
            s.commit()
        return n

    async def aclose(self) -> None:
        for graph in self._graphs.values():
            await graph.aclose()
        self._graphs.clear()

    def _graph(self, token: str) -> GraphClient:
        if token not in self._graphs:
            self._graphs[token] = self._graph_factory(token)
        return self._graphs[token]

    def _running(self) -> list[str]:
        with self.sessions() as s:
            return [c.id for c in s.scalars(select(WaCampaign).where(WaCampaign.status == "running"))]

    async def tick(self) -> int:
        """Una vuelta: manda lo que toca de cada campaña en curso. Devuelve cuantos envio."""
        running = await asyncio.to_thread(self._running)
        for gone in set(self._last) - set(running):
            self._forget(gone)
        sent = 0
        for campaign_id in running:
            try:
                sent += await self._run(campaign_id)
            except Exception:
                logger.exception("wa: fallo el envio de la campaña %s", campaign_id)
        return sent

    def _forget(self, campaign_id: str) -> None:
        for d in (self._credit, self._last, self._wait_until):
            d.pop(campaign_id, None)

    def _allowance(self, c: WaCampaign) -> int:
        """Cuantos le tocan ahora: credito que crece a rate_per_minute, con tope de un minuto."""
        now = self.clock()
        last = self._last.get(c.id)
        elapsed = settings.wa_campaign_tick_seconds if last is None else now - last
        self._last[c.id] = now
        credit = min(float(c.rate_per_minute), self._credit.get(c.id, 0.0) + c.rate_per_minute * elapsed / 60)
        self._credit[c.id] = credit
        return int(credit)

    async def _run(self, campaign_id: str) -> int:
        batch = await asyncio.to_thread(self._batch, campaign_id)
        if batch is None:
            return 0
        info, token, ids = batch
        sent = 0
        for recipient_id in ids:
            outcome = await self._send(info, token, recipient_id)
            self._credit[campaign_id] = self._credit.get(campaign_id, 1.0) - 1
            if outcome == "sent":
                sent += 1
            elif outcome == "stop":
                break
        return sent

    def _batch(self, campaign_id: str) -> tuple[dict, str, list[str]] | None:
        """Sincronico: los pendientes que le tocan ahora a la campaña, o None. Pausa la
        campaña si el numero o el cliente no pueden mandar, y la cierra si no queda nada."""
        with self.sessions() as s:
            c = s.get(WaCampaign, campaign_id)
            if c is None or c.status != "running":
                return None
            if not c.window_start <= self.hour() < c.window_end:
                self._forget(c.id)      # fuera de horario no acumula credito
                return None
            if self._wait_until.get(c.id, 0) > self.clock():
                return None
            account = s.get(WaAccount, c.account_id)
            client = s.get(Client, c.client_id)
            problem = (None if account and account.active and account.status == "connected"
                       else "El número de WhatsApp está inactivo o desconectado")
            if problem is None and (client is None or not client.active):
                problem = "El cliente está inactivo"
            token = None
            if problem is None:
                try:
                    token = store.token_for(account)
                except TokenKeyMissing:
                    problem = "No se puede descifrar el token de la cuenta (WA_TOKEN_KEY)"
            if problem:
                campaigns.pause(s, c, problem)
                s.commit()
                logger.warning("wa: campaña %s pausada: %s", c.id, problem)
                return None
            n = self._allowance(c)
            if n == 0:
                return None
            batch = list(s.scalars(select(WaCampaignRecipient).where(
                WaCampaignRecipient.campaign_id == c.id, WaCampaignRecipient.status == "pending")
                .order_by(WaCampaignRecipient.created_at, WaCampaignRecipient.id).limit(n)))
            if not batch:
                if campaigns.pending_count(s, c.id) == 0 and not s.scalar(select(WaCampaignRecipient.id).where(
                        WaCampaignRecipient.campaign_id == c.id, WaCampaignRecipient.status == "sending").limit(1)):
                    c.status, c.finished_at = "done", utcnow()
                    s.commit()
                    logger.info("wa: campaña %s terminada", c.id)
                return None
            info = {"campaign_id": c.id, "client_id": c.client_id, "account_id": account.id,
                    "pnid": account.phone_number_id, "own_token": store.has_own_token(account),
                    "template": c.template_name, "language": c.template_language}
            return info, token, [r.id for r in batch]

    def _claim(self, info: dict, recipient_id: str) -> tuple[str, list] | str:
        """Sincronico: reclamo atomico pending -> sending (commit). (wa_id, params) para mandar,
        o el resultado si no hay que mandar: stop, skipped."""
        with self.sessions() as s:
            c = s.get(WaCampaign, info["campaign_id"])
            if c is None or c.status != "running":     # la pausaron o cancelaron en medio de la tanda
                return "stop"
            r = s.get(WaCampaignRecipient, recipient_id)
            if r is None or r.status != "pending":
                return "skipped"
            pending = (WaCampaignRecipient.id == recipient_id, WaCampaignRecipient.status == "pending")
            if campaigns.is_opted_out(s, info["client_id"], r.wa_id):
                s.execute(update(WaCampaignRecipient).where(*pending)
                          .values(status="skipped", error={"message": "El contacto pidió la baja"})
                          .execution_options(synchronize_session=False))
                s.commit()
                return "skipped"
            # Otro proceso pudo tomarlo entre la lectura y aca: solo manda el que lo reclama.
            n = s.execute(update(WaCampaignRecipient).where(*pending)
                          .values(status="sending", claimed_at=utcnow())
                          .execution_options(synchronize_session=False)).rowcount
            s.commit()
            return (r.wa_id, list(r.params or [])) if n == 1 else "skipped"

    def _sent(self, info: dict, recipient_id: str, wa_id: str, wamid: str | None) -> None:
        with self.sessions() as s:
            r = s.get(WaCampaignRecipient, recipient_id)
            r.status, r.wamid, r.sent_at, r.error = "sent", wamid, utcnow(), None
            store.record_outbound(s, wamid=wamid, account_id=info["account_id"], conversation_id=None, wa_id=wa_id,
                                  type="template", status="sent")
            s.commit()

    async def _send(self, info: dict, token: str, recipient_id: str) -> str:
        """sent, failed, skipped o stop (la campaña no sigue en esta vuelta)."""
        claimed = await asyncio.to_thread(self._claim, info, recipient_id)
        if isinstance(claimed, str):
            return claimed
        wa_id, params = claimed
        try:
            data = await self._graph(token).send_template(info["pnid"], recipient(wa_id), info["template"],
                                                          info["language"], params)
        except GraphError as e:
            return await asyncio.to_thread(self._failed, info, recipient_id, wa_id, e)
        messages = data.get("messages")
        wamid = messages[0].get("id") if isinstance(messages, list) and messages else None
        await asyncio.to_thread(self._sent, info, recipient_id, wa_id, wamid)
        return "sent"

    def _failed(self, info: dict, recipient_id: str, wa_id: str, e: GraphError) -> str:
        error = {"code": e.code, "subcode": e.subcode, "message": e.message}
        logger.warning("wa: plantilla de campaña no enviada campaign=%s pnid=%s code=%s subcode=%s",
                       info["campaign_id"], info["pnid"], e.code, e.subcode)
        with self.sessions() as s:
            r = s.get(WaCampaignRecipient, recipient_id)
            if e.is_auth_error or e.code in PAUSE_CODES or e.code in RETRY_CODES:
                r.status = "pending"
                if e.code in RETRY_CODES:
                    self._wait_until[info["campaign_id"]] = self.clock() + BACKOFF_SECONDS
                else:
                    c = s.get(WaCampaign, info["campaign_id"])
                    if c is not None and c.status == "running":
                        reason = ("Meta rechazó el token de la cuenta: hay que volver a conectarla" if e.is_auth_error
                                  else PAUSE_REASONS.get(e.code, f"Meta: {e.message}"))
                        campaigns.pause(s, c, f"{reason} (código {e.code})")
                    if e.is_auth_error and info["own_token"]:
                        account = s.get(WaAccount, info["account_id"])
                        store.mark_status(s, account, "disconnected", f"token_invalid code={e.code}")
                s.commit()
                return "stop"
            r.status, r.error = "failed", error
            store.record_outbound(s, wamid=None, account_id=info["account_id"], conversation_id=None, wa_id=wa_id,
                                  type="template", status="failed", error=error)
            s.commit()
        return "failed"


_sender: CampaignSender | None = None


def get_sender() -> CampaignSender:
    global _sender
    if _sender is None:
        from ..db import get_sessionmaker
        _sender = CampaignSender(get_sessionmaker())
    return _sender


async def campaign_loop(leader: Leader | None = None) -> None:
    """Corre en la app (lifespan), solo en el lider: envia cada WA_CAMPAIGN_TICK_SECONDS y
    pasa a failed los envios colgados (al arrancar y cada RECOVER_SECONDS)."""
    sender = get_sender()
    last_recover = -RECOVER_SECONDS

    async def run():
        nonlocal last_recover
        if time.monotonic() - last_recover >= RECOVER_SECONDS:
            last_recover = time.monotonic()
            if n := await asyncio.to_thread(sender.recover):
                logger.warning("wa: %d envíos de campaña interrumpidos quedaron como fallidos", n)
        await sender.tick()

    await every(leader, settings.wa_campaign_tick_seconds, run, "wa: vuelta de campañas")
