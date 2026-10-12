"""Avisos programados de las apps (contrato v1.1, docs/APPS_PLAN.md): a la hora del manifest,
POST /jobs/{name}; si la app devuelve un mensaje, va a los operadores activos del cliente (con el
link de la vista si trae una), por app/apps/outbox.send_text (simulado o WhatsApp).

Una corrida por dia y job: la reclama el unique de app_job_runs antes de llamar a la app. Si la
hora ya paso hace mas de WINDOW (la app se registro tarde, o app estuvo caida), ese dia no corre.
"""
import asyncio
import datetime
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import get_sessionmaker
from ..models import App, AppJobRun, WaOperator
from . import client as app_client
from . import links, outbox
from .registry import manifest_of, token_of

logger = logging.getLogger(__name__)
WINDOW = datetime.timedelta(hours=2)


def local_now() -> datetime.datetime:
    return datetime.datetime.now(ZoneInfo(settings.assistant_timezone))


def due(job, now: datetime.datetime) -> bool:
    if job.dias and now.isoweekday() not in job.dias:
        return False
    hour, minute = map(int, job.hora.split(":"))
    at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return at <= now < at + WINDOW


async def run_job(sessions: sessionmaker[Session], app_id: str, job: str) -> dict:
    """Llama al job y entrega el aviso. {"message", "url", "entregas": [{wa_id, estado}]}."""
    with sessions() as s:
        app = s.get(App, app_id)
        base_url, token, client_id = app.base_url, token_of(app), app.client_id
    out = await app_client.post_json(base_url, token, f"/jobs/{job}", {}, actor=f"job:{job}")
    message, view = (out.get("message") or "").strip(), out.get("view")
    result: dict = {"message": message or None, "url": None, "entregas": []}
    if not message or client_id is None:
        return result
    if view and view.get("name"):
        with sessions() as s:
            try:
                result["url"], _ = links.create_link(s, s.get(App, app_id), view["name"], view.get("params") or {},
                                                     f"job:{job}")
                s.commit()
            except Exception as e:  # noqa: BLE001 - sin link, el aviso sale igual
                logger.warning("apps: el job %s pidio una vista que no se pudo abrir: %s", job, e)
        if result["url"]:
            message = f"{message}\n\n{result['url']}"
    with sessions() as s:
        operators = [(op.account_id, op.wa_id) for op in s.scalars(
            select(WaOperator).where(WaOperator.client_id == client_id, WaOperator.active.is_(True)))]
    for account_id, wa_id in operators:
        sent = await outbox.send_text(sessions, account_id, wa_id, message)
        result["entregas"].append({"wa_id": wa_id, "estado": sent["estado"]})
    return result


def _claim(sessions: sessionmaker[Session], app_id: str, job: str, day: datetime.date) -> str | None:
    with sessions() as s:
        run = AppJobRun(app_id=app_id, job=job, run_on=day)
        s.add(run)
        try:
            s.commit()
        except IntegrityError:
            return None
        return run.id


def _finish(sessions: sessionmaker[Session], run_id: str, status: str, detail: str | None) -> None:
    with sessions() as s:
        run = s.get(AppJobRun, run_id)
        run.status, run.detail = status, (detail or "")[:2000] or None
        s.commit()


async def tick(sessions: sessionmaker[Session], now: datetime.datetime | None = None) -> int:
    """Corre los jobs que tocan; devuelve cuantos corrio."""
    now = now or local_now()
    with sessions() as s:
        apps = [(a.id, manifest_of(a).jobs) for a in s.scalars(
            select(App).where(App.client_id.is_not(None), App.status == "ok"))]
    ran = 0
    for app_id, jobs in apps:
        for job in jobs:
            if not due(job, now) or (run_id := _claim(sessions, app_id, job.name, now.date())) is None:
                continue
            ran += 1
            try:
                result = await run_job(sessions, app_id, job.name)
                status = "enviado" if result["message"] else "sin_novedades"
                _finish(sessions, run_id, status, result["message"])
            except Exception as e:  # noqa: BLE001 - un job roto no corta el resto
                logger.warning("apps: fallo el job %s: %s", job.name, e)
                _finish(sessions, run_id, "error", str(e))
    return ran


async def jobs_loop(interval: float | None = None) -> None:
    interval = interval or settings.apps_jobs_seconds
    while True:
        await asyncio.sleep(interval)
        try:
            await tick(get_sessionmaker())
        except Exception:
            logger.exception("apps: fallo el barrido de jobs")
