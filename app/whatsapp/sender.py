"""Envio de las campañas salientes (campaigns.py): un loop en la app que cada
WA_CAMPAIGN_TICK_SECONDS manda, por cada campaña en curso y dentro de su horario, lo que
le toca segun su ritmo (rate_per_minute, sin rafagas de mas de un minuto).

Cada envio: el contacto pasa a `sending` (commit) antes de llamar a Meta, asi un reinicio
en el medio no lo vuelve a mandar: al arrancar, los `sending` quedan `failed` con aviso.
Errores de Meta:
- token rechazado, cuenta bloqueada, plantilla pausada o deshabilitada, limite de spam:
  la campaña se pausa con el motivo y el contacto vuelve a pendiente;
- limite de envio momentaneo: el contacto vuelve a pendiente y la campaña espera un minuto;
- el resto (numero invalido, etc.): ese contacto queda `failed`.
Lo que Meta informa despues (entregado, leido, fallido) llega por el webhook a wa_messages.

Supone un solo worker de uvicorn, como service.py.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import time
from collections.abc import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import utcnow
from ..models import Client, WaAccount, WaCampaign, WaCampaignRecipient
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

    def recover(self) -> int:
        """Al arrancar: los que quedaron `sending` (reinicio en medio de un envio) pasan a
        `failed`. No se reenvian: Meta puede haberlos entregado."""
        with self.sessions() as s:
            rows = list(s.scalars(select(WaCampaignRecipient).where(WaCampaignRecipient.status == "sending")))
            for r in rows:
                r.status = "failed"
                r.error = {"message": "Envío interrumpido por un reinicio: puede haber llegado"}
            s.commit()
        return len(rows)

    async def aclose(self) -> None:
        for graph in self._graphs.values():
            await graph.aclose()
        self._graphs.clear()

    def _graph(self, token: str) -> GraphClient:
        if token not in self._graphs:
            self._graphs[token] = self._graph_factory(token)
        return self._graphs[token]

    async def tick(self) -> int:
        """Una vuelta: manda lo que toca de cada campaña en curso. Devuelve cuantos envio."""
        with self.sessions() as s:
            running = [c.id for c in s.scalars(select(WaCampaign).where(WaCampaign.status == "running"))]
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
        with self.sessions() as s:
            c = s.get(WaCampaign, campaign_id)
            if c is None or c.status != "running":
                return 0
            if not c.window_start <= self.hour() < c.window_end:
                self._forget(c.id)      # fuera de horario no acumula credito
                return 0
            if self._wait_until.get(c.id, 0) > self.clock():
                return 0
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
                return 0
            n = self._allowance(c)
            if n == 0:
                return 0
            batch = list(s.scalars(select(WaCampaignRecipient).where(
                WaCampaignRecipient.campaign_id == c.id, WaCampaignRecipient.status == "pending")
                .order_by(WaCampaignRecipient.created_at, WaCampaignRecipient.id).limit(n)))
            if not batch:
                if campaigns.pending_count(s, c.id) == 0 and not s.scalar(select(WaCampaignRecipient.id).where(
                        WaCampaignRecipient.campaign_id == c.id, WaCampaignRecipient.status == "sending").limit(1)):
                    c.status, c.finished_at = "done", utcnow()
                    s.commit()
                    logger.info("wa: campaña %s terminada", c.id)
                return 0
            info = {"campaign_id": c.id, "client_id": c.client_id, "account_id": account.id,
                    "pnid": account.phone_number_id, "own_token": store.has_own_token(account),
                    "template": c.template_name, "language": c.template_language}
            ids = [r.id for r in batch]
        sent = 0
        for recipient_id in ids:
            outcome = await self._send(info, token, recipient_id)
            self._credit[campaign_id] = self._credit.get(campaign_id, 1.0) - 1
            if outcome == "sent":
                sent += 1
            elif outcome == "stop":
                break
        return sent

    async def _send(self, info: dict, token: str, recipient_id: str) -> str:
        """sent, failed, skipped o stop (la campaña no sigue en esta vuelta)."""
        with self.sessions() as s:
            c = s.get(WaCampaign, info["campaign_id"])
            if c is None or c.status != "running":     # la pausaron o cancelaron en medio de la tanda
                return "stop"
            r = s.get(WaCampaignRecipient, recipient_id)
            if r is None or r.status != "pending":
                return "skipped"
            if campaigns.is_opted_out(s, info["client_id"], r.wa_id):
                r.status, r.error = "skipped", {"message": "El contacto pidió la baja"}
                s.commit()
                return "skipped"
            r.status = "sending"
            wa_id, params = r.wa_id, list(r.params or [])
            s.commit()
        try:
            data = await self._graph(token).send_template(info["pnid"], recipient(wa_id), info["template"],
                                                          info["language"], params)
        except GraphError as e:
            return self._failed(info, recipient_id, wa_id, e)
        messages = data.get("messages")
        wamid = messages[0].get("id") if isinstance(messages, list) and messages else None
        with self.sessions() as s:
            r = s.get(WaCampaignRecipient, recipient_id)
            r.status, r.wamid, r.sent_at, r.error = "sent", wamid, utcnow(), None
            store.record_outbound(s, wamid=wamid, account_id=info["account_id"], conversation_id=None, wa_id=wa_id,
                                  type="template", status="sent")
            s.commit()
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


async def campaign_loop() -> None:
    """Corre en la app (lifespan)."""
    sender = get_sender()
    try:
        if n := await asyncio.to_thread(sender.recover):
            logger.warning("wa: %d envíos de campaña interrumpidos quedaron como fallidos", n)
    except Exception:
        logger.exception("wa: fallo la recuperacion de envios de campaña")
    while True:
        await asyncio.sleep(settings.wa_campaign_tick_seconds)
        try:
            await sender.tick()
        except Exception:
            logger.exception("wa: fallo la vuelta de campañas")
