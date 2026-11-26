"""Cola de las corridas de casos de prueba (docs/features/CASOS_DE_PRUEBA.md), como el Estudio: una corrida a la
vez, en la app. Al arrancar, las que estaban en curso pasan a fallidas (o a canceladas, si tenian el pedido): no se
repiten tokens."""
import asyncio
import contextlib
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import get_sessionmaker, utcnow
from ..models import Agent, AgentTestCase, AgentTestRun
from . import runner
from ..services import errors

logger = logging.getLogger(__name__)

QUEUED, RUNNING, DONE, FAILED, CANCELLED = "queued", "running", "done", "failed", "cancelled"
ACTIVE = (QUEUED, RUNNING)
MAX_RUNS = 30
RESTART_ERROR = "se reinició la app"


def _same(left: dict, right: dict) -> bool:
    strip = lambda data: {k: v for k, v in (data or {}).items() if k != "version"}   # noqa: E731
    return strip(left) == strip(right)


class RunInProgress(errors.Conflict):
    """Ya hay una corrida activa del agente. Lleva su id: la ruta responde el 409 con `run_id` y la UI la abre."""

    def __init__(self, run_id: str | None):
        super().__init__("Ya hay una corrida de pruebas en curso para este agente", "test_run_in_progress")
        self.run_id = run_id


def create(s: Session, agent: Agent, repetitions: int, definition: dict | None, case_ids: list[str] | None,
           draft: dict | None, user_id: str | None) -> AgentTestRun:
    """Arma la corrida: las variantes (publicada y, si la definicion cambia, los cambios sin guardar) y la copia
    de nombre y chequeos de cada caso. `draft`: un caso sin guardar ("Probar ahora")."""
    if not 1 <= repetitions <= 10:
        raise errors.Invalid("repeticiones: de 1 a 10", "invalid_repetitions")
    if case_ids is None:
        rows = list(s.scalars(select(AgentTestCase).where(AgentTestCase.agent_id == agent.id)
                              .order_by(AgentTestCase.created_at.desc())))
    else:
        ids = list(dict.fromkeys(case_ids))
        rows = list(s.scalars(select(AgentTestCase).where(AgentTestCase.agent_id == agent.id,
                                                          AgentTestCase.id.in_(ids)))) if ids else []
        found = {row.id for row in rows}
        if missing := [i for i in ids if i not in found]:
            raise errors.NotFound(f"Caso de prueba inexistente: {missing[0]}")
    cases = [{"id": row.id, "name": row.name, "checks": row.checks or [],
              "known_failure": bool(row.known_failure)} for row in rows]
    if draft is not None:
        cases.append(draft)
    if not cases:
        raise errors.Invalid("El agente no tiene casos de prueba", "no_test_cases")

    variants = [{"key": "publicada", "version": agent.version}]
    if definition is not None and not _same(definition, agent.definition):
        variants.append({"key": "borrador", "version": agent.version + 1, "definition": definition})
    active = s.scalar(select(AgentTestRun).where(AgentTestRun.agent_id == agent.id,
                                                 AgentTestRun.status.in_(ACTIVE)))
    if active is not None:
        raise RunInProgress(active.id)
    run = AgentTestRun(client_id=agent.client_id, agent_id=agent.id, status=QUEUED, repetitions=repetitions,
                       variants=variants, cases=cases, results=None, done=0,
                       total=len(cases) * len(variants) * repetitions, input_tokens=0, output_tokens=0,
                       tool_revisions=None, created_by=user_id)
    s.add(run)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        # Otra peticion gano la carrera: se busca la activa despues del rollback (puede haber terminado ya).
        active = s.scalar(select(AgentTestRun).where(AgentTestRun.agent_id == agent.id,
                                                     AgentTestRun.status.in_(ACTIVE)))
        raise RunInProgress(active.id if active is not None else None) from None
    # Se guardan las ultimas MAX_RUNS de cada agente (las viejas se borran; no estan en curso).
    old = list(s.scalars(select(AgentTestRun).where(AgentTestRun.agent_id == agent.id,
                                                    AgentTestRun.status.notin_(ACTIVE))
                         .order_by(AgentTestRun.created_at.desc()).offset(MAX_RUNS - 1)))
    for row in old:
        s.delete(row)
    return run


def load(sessions: sessionmaker[Session], run_id: str) -> dict | None:
    """Todo lo que necesita el runner: la corrida, el agente y los casos (los sin guardar incluidos)."""
    with sessions() as s:
        run = s.get(AgentTestRun, run_id)
        if run is None:
            return None
        agent = s.get(Agent, run.agent_id)
        if agent is None:
            return None
        cases: dict[str, dict] = {}
        for entry in run.cases or []:
            if entry.get("id") == "draft":
                cases["draft"] = entry
                continue
            row = s.get(AgentTestCase, entry.get("id"))
            if row is None or row.agent_id != run.agent_id:
                cases[entry.get("id")] = {"missing": True, "name": entry.get("name")}
                continue
            cases[row.id] = {"id": row.id, "name": row.name, "checks": row.checks or [],
                             "known_failure": bool(row.known_failure), "snapshot": row.snapshot,
                             "tool_results": row.tool_results or []}
        return {"run": {"id": run.id, "repetitions": run.repetitions, "variants": run.variants,
                        "cases": run.cases or [], "total": run.total},
                "agent": {"id": agent.id, "client_id": agent.client_id, "version": agent.version,
                          "definition": agent.definition},
                "cases": cases}


def claim(sessions: sessionmaker[Session]) -> str | None:
    """La corrida mas vieja en cola, ya en `running`. SKIP LOCKED por si hay dos procesos."""
    with sessions() as s:
        run = s.scalar(select(AgentTestRun).where(AgentTestRun.status == QUEUED)
                       .order_by(AgentTestRun.created_at).limit(1).with_for_update(skip_locked=True))
        if run is None:
            return None
        run.status, run.started_at = RUNNING, utcnow()
        s.commit()
        return run.id


def requeue_interrupted(sessions: sessionmaker[Session]) -> int:
    """Las que estaban corriendo cuando se reinicio la app no se repiten: con pedido de cancelacion quedan
    `cancelled`; si no, fallidas (los tokens ya se gastaron)."""
    with sessions() as s:
        rows = list(s.scalars(select(AgentTestRun).where(AgentTestRun.status == RUNNING)))
        for run in rows:
            if run.cancel_requested_at is not None:
                run.status, run.finished_at = CANCELLED, utcnow()
            else:
                run.status, run.error, run.finished_at = FAILED, RESTART_ERROR, utcnow()
        s.commit()
        return len(rows)


def summarize(results: list | None) -> list[dict]:
    """`[{case_id, variants: [{key, passed, total}]}]`: el `pasa X/N` de cada variante, sin las respuestas."""
    return [{"case_id": item.get("case_id"),
             "variants": [{"key": v.get("key"), "passed": v.get("passed", 0), "total": v.get("total", 0)}
                          for v in item.get("variants") or []]}
            for item in results or []]


def update_progress(sessions: sessionmaker[Session], run_id: str, data: dict) -> None:
    with sessions() as s:
        run = s.get(AgentTestRun, run_id)
        if run is None:
            return
        run.done = data.get("done", run.done)
        run.results = data.get("results", run.results)
        run.summary = summarize(run.results)
        run.input_tokens = data.get("input_tokens", run.input_tokens)
        run.output_tokens = data.get("output_tokens", run.output_tokens)
        run.tool_revisions = data.get("tool_revisions", run.tool_revisions)
        s.commit()


def finish(sessions: sessionmaker[Session], run_id: str, result: dict) -> None:
    """Cierra la corrida: `cancelled` con lo que alcanzo a correr, o `done` con todo (los turnos en curso terminan)."""
    with sessions() as s:
        run = s.get(AgentTestRun, run_id)
        if run is None:
            return
        run.results = result.get("results")
        run.summary = summarize(run.results)
        run.input_tokens = result.get("input_tokens", 0)
        run.output_tokens = result.get("output_tokens", 0)
        run.tool_revisions = result.get("tool_revisions") or None
        if result.get("cancelled"):
            run.done, run.status = result.get("done", run.done), CANCELLED
        else:
            run.done, run.status = run.total, DONE
        run.finished_at = utcnow()
        s.commit()


def cancel_requested(sessions: sessionmaker[Session], run_id: str) -> bool:
    """Si la corrida tiene pedido de cancelacion, o si su fila ya no existe (se borro el agente)."""
    with sessions() as s:
        run = s.get(AgentTestRun, run_id)
        return run is None or run.cancel_requested_at is not None


def cancel(run: AgentTestRun) -> None:
    """Sobre la fila ya bloqueada: en cola se termina en el acto; en curso se pide (la cola deja de mandar turnos y
    los que ya estan en el LLM terminan). Una terminada no cambia."""
    if run.status == QUEUED:
        run.status, run.finished_at = CANCELLED, utcnow()
    elif run.status == RUNNING and run.cancel_requested_at is None:
        run.cancel_requested_at = utcnow()


async def _watch(sessions: sessionmaker[Session], run_id: str, stop: asyncio.Event) -> None:
    """Prende `stop` cuando la corrida tiene pedido de cancelacion: mira en seguida y despues cada tick."""
    while not stop.is_set():
        try:
            if await asyncio.to_thread(cancel_requested, sessions, run_id):
                stop.set()
                return
        except Exception:
            logger.exception("casos de prueba: no se pudo mirar el pedido de cancelacion de %s", run_id)
        await asyncio.sleep(settings.agent_tests_tick_seconds)


def fail(sessions: sessionmaker[Session], run_id: str, message: str) -> None:
    with sessions() as s:
        run = s.get(AgentTestRun, run_id)
        if run is None:
            return
        run.status, run.error, run.finished_at = FAILED, message[:2000], utcnow()
        s.commit()


async def process(sessions: sessionmaker[Session], run_id: str) -> None:
    """Corre la corrida con su vigia de cancelacion: los turnos que ya estan en el LLM terminan; no se mandan mas."""
    from ..runtime import get_conversation_engine

    data = await asyncio.to_thread(load, sessions, run_id)
    if data is None:
        return
    engine = get_conversation_engine()
    stop = asyncio.Event()
    watcher = asyncio.create_task(_watch(sessions, run_id, stop))

    async def progress(payload: dict) -> None:
        await asyncio.to_thread(update_progress, sessions, run_id, payload)

    try:
        result = await runner.execute(data["run"], data["agent"], data["cases"], engine, sessions, progress, stop)
        await asyncio.to_thread(finish, sessions, run_id, result)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("casos de prueba: fallo la corrida %s", run_id)
        await asyncio.to_thread(fail, sessions, run_id, f"{type(e).__name__}: {e}")
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher


async def agent_tests_loop() -> None:
    """En la app (lifespan): una corrida a la vez, para no competir con las llamadas en vivo."""
    sessions = get_sessionmaker()
    while True:
        try:
            await asyncio.to_thread(requeue_interrupted, sessions)
            break
        except Exception:
            logger.exception("casos de prueba: no se pudieron marcar las corridas interrumpidas")
            await asyncio.sleep(settings.agent_tests_tick_seconds)
    while True:
        await asyncio.sleep(settings.agent_tests_tick_seconds)
        try:
            while run_id := await asyncio.to_thread(claim, sessions):
                await process(sessions, run_id)
        except Exception:
            logger.exception("casos de prueba: fallo la vuelta de la cola")
