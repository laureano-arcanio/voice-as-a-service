"""Barrido periodico del cobro, en la app (lifespan, como el de WhatsApp): vencimientos, gracia,
recordatorios, numeros suspendidos que vuelven al inventario y registros sin activar."""
import asyncio
import logging

from ..db import get_sessionmaker
from ..mail import notify
from ..services import signup
from . import service

logger = logging.getLogger(__name__)


def run_once() -> None:
    with get_sessionmaker()() as s:
        mails = service.tick(s)
        purged = signup.purge_unactivated(s)
        s.commit()
    if purged:
        logger.info("billing: %d registros sin activar borrados", purged)
    notify.deliver(mails)


async def billing_loop(interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(run_once)
        except Exception:
            logger.exception("billing: fallo el barrido")
