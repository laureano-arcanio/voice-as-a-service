"""El loop de las campañas salientes (corre en la app, lifespan): uno solo, que delega por canal
al sender de WhatsApp (cada WA_CAMPAIGN_TICK_SECONDS) y al dialer de voz (cada CALL_CAMPAIGN_TICK_SECONDS)."""
import asyncio
import logging
import time

from ..config import settings
from ..whatsapp.sender import get_sender
from .dialer import get_dialer

logger = logging.getLogger(__name__)


async def campaign_loop() -> None:
    sender, dialer = get_sender(), get_dialer()
    try:
        if n := await asyncio.to_thread(sender.recover):
            logger.warning("wa: %d envíos de campaña interrumpidos quedaron como fallidos", n)
    except Exception:
        logger.exception("wa: fallo la recuperacion de envios de campaña")
    try:
        if n := await asyncio.to_thread(dialer.recover):
            logger.warning("campañas de voz: %d intentos interrumpidos vuelven a reintento", n)
    except Exception:
        logger.exception("campañas de voz: fallo la recuperacion de intentos")
    last_wa = float("-inf")
    while True:
        await asyncio.sleep(min(settings.wa_campaign_tick_seconds, settings.call_campaign_tick_seconds))
        if time.monotonic() - last_wa >= settings.wa_campaign_tick_seconds:
            last_wa = time.monotonic()
            try:
                await sender.tick()
            except Exception:
                logger.exception("wa: fallo la vuelta de campañas")
        try:
            await dialer.tick()
        except Exception:
            logger.exception("campañas de voz: fallo la vuelta del dialer")
