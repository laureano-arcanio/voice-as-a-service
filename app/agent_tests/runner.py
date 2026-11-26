"""Corre un caso de prueba contra una variante del agente, sin tocar nada real (docs/features/CASOS_DE_PRUEBA.md).

Por caso, variante y repeticion arma el estado grabado en memoria (sin `process_turn`: no guarda la conversacion, no
extrae y no deja filas en `tool_runs`), resuelve el LLM de la version probada con un `LLMResolver` propio (una falla
de un proveedor BYOK no abre el circuito de las llamadas en vivo) y ejecuta las herramientas con `RecordedTools`, que
devuelve lo grabado y nunca llama a `run`. Despues corre los chequeos deterministas y guarda la respuesta.

El horario de las areas se congela a la hora del mensaje grabado: si el caso se tomo en una llamada fuera de
horario, el LLM ve "cerrada ahora" aunque la corrida sea en horario de atencion.
"""
import asyncio
import datetime
import json
import logging
import time

from ..config import settings
from ..conversation.engine import _use_last_reply
from ..conversation.models import ConversationState, Message, Progress, ToolSettings, Workflow
from ..llm.resolver import LLMResolver
from ..services import handoff as handoff_service
from ..services import tools as tools_service
from ..tools.conversation import TurnTools
from ..tools.runtime import ToolContext
from .checks import evaluate

logger = logging.getLogger(__name__)

TURN_TIMEOUT = 90        # segundos por turno; uno colgado no frena la cola
NOT_RECORDED = json.dumps({"ok": False, "error": "sin resultado grabado en el caso"}, ensure_ascii=False)


class RecordedTools(TurnTools):
    """Las herramientas del turno, simuladas: devuelve el k-esimo resultado grabado de ese nombre. No llama a
    `run`, no registra en `tool_runs` y no lee secretos (ToolContext vacio)."""

    def __init__(self, *, recorded: dict[str, list[str]], used: list[dict], **kwargs):
        super().__init__(**kwargs)
        self.recorded = recorded
        self.used = used
        self._seen: dict[str, int] = {}

    async def _one(self, call_id: str, name: str, raw_args: str, on_message=None) -> str:
        index = self._seen.get(name, 0)
        self._seen[name] = index + 1
        results = self.recorded.get(name) or []
        result = results[index] if index < len(results) else None
        out = result if result is not None else NOT_RECORDED
        self.used.append({"name": name, "arguments": raw_args or "{}", "result": out,
                          "recorded": result is not None})
        return out


def _info(llm) -> dict:
    info = getattr(llm, "info", None)
    return info() if callable(info) else {"model": getattr(llm, "model", None)}


def _when(snapshot: dict) -> datetime.datetime:
    """La hora del mensaje grabado (UTC naive), para congelar el horario de las areas."""
    raw = snapshot.get("user_message_at")
    if not raw:
        messages = snapshot.get("messages") or []
        raw = (messages[-1] or {}).get("at") if messages else None
    raw = raw or (snapshot.get("progress") or {}).get("started_at")
    if raw:
        try:
            value = datetime.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            return value.astimezone(datetime.UTC).replace(tzinfo=None) if value.tzinfo else value
        except ValueError:
            pass
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _freeze(areas: list[dict], when: datetime.datetime) -> list[dict]:
    """Abierta a esa hora: sin horario (atiende siempre); cerrada: una semana vacia, para que diga "cerrada ahora"."""
    out = []
    for area in areas:
        open_now = handoff_service.is_open(area.get("schedule"), when)
        out.append({**area, "schedule": None if open_now else {"week": {}}})
    return out


def _load_specs(sessions, client_id: str | None, workflow: Workflow) -> tuple[list, list[str]]:
    with sessions() as s:
        return tools_service.load_agent_tools(s, client_id, workflow)


def _load_areas(sessions, client_id: str | None, workflow: Workflow, channel: str) -> list[dict]:
    if workflow.handoff is None or not workflow.handoff.areas:
        return []
    with sessions() as s:
        return handoff_service.call_areas(s, client_id, workflow.handoff, channel)


def _state(agent: dict, case: dict, variant: dict) -> ConversationState:
    snapshot = case.get("snapshot") or {}
    progress = Progress.model_validate(snapshot.get("progress") or {})
    progress.system_prompt = None
    progress.handoff_areas = _freeze(case.get("areas") or [], _when(snapshot)) if snapshot.get("handoff") else []
    return ConversationState(
        conversation_id=f"agenttest-{case['id']}"[:64], agent_id=agent["id"],
        agent_version=variant["version"], client_id=agent["client_id"],
        channel=snapshot.get("channel") or "voice", status="active", fields={},
        messages=[Message.model_validate(m) for m in snapshot.get("messages") or []], progress=progress)


def _recorded(case: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for item in case.get("tool_results") or []:
        out.setdefault(item.get("name") or "", []).append(item.get("result") or "")
    return out


async def _repetition(agent: dict, case: dict, variant: dict, prepared: dict, engine, resolver: LLMResolver,
                      sem: asyncio.Semaphore) -> dict:
    errors = list(prepared.get("load_errors") or [])
    state = _state(agent, case, variant)
    used: list[dict] = []
    tools = None
    if prepared["specs"]:
        tools = RecordedTools(recorded=_recorded(case), used=used, specs=prepared["specs"], ctx=ToolContext(),
                              settings=prepared["workflow"].tool_settings or ToolSettings(),
                              voice=state.channel == "voice", sessions=None, client_id=None, agent_id=None)
    turn_no = 1 + sum(m.role == "user" for m in state.messages)
    out = {"text": "", "tool_calls": [], "handoff": None, "status": None, "failures": [], "error": None,
           "ms": 0, "input_tokens": 0, "output_tokens": 0, "llm": {}, "tools": []}
    started = time.perf_counter()
    llm = None
    try:
        llm = resolver.for_turn(prepared["workflow"], turn_no, agent["client_id"])
        async with sem:
            turn = await asyncio.wait_for(
                llm.converse(prepared["workflow"], state, case.get("snapshot", {}).get("user_message") or "",
                             on_message=lambda _text: None, tools=tools), timeout=TURN_TIMEOUT)
        _use_last_reply(turn, state)
        out.update(text=turn.assistant_message, handoff=turn.handoff, status=turn.status,
                   input_tokens=turn.input_tokens or 0, output_tokens=turn.output_tokens or 0,
                   llm=_info(llm))
    except asyncio.TimeoutError:
        errors.append(f"el turno paso los {TURN_TIMEOUT} s")
        out["llm"] = _info(llm) if llm is not None else {}
    except Exception as e:      # una repeticion que falla no rompe la corrida
        logger.info("casos de prueba: fallo una repeticion de %s: %s", case.get("id"), e)
        errors.append(f"{type(e).__name__}: {e}")
        out["llm"] = _info(llm) if llm is not None else {}
    out["ms"] = round((time.perf_counter() - started) * 1000)
    out["tools"] = used
    out["tool_calls"] = [{"name": u["name"], "arguments": u["arguments"]} for u in used]
    reply = {"text": out["text"], "tool_calls": out["tool_calls"], "handoff": out["handoff"],
             "tool_results": [u["result"] for u in used]}
    out["failures"] = evaluate(case.get("checks") or [], reply)
    if errors:
        out["error"] = "; ".join(errors)
    out["passed"] = not out["failures"] and not errors
    return out


async def execute(run: dict, agent: dict, cases: dict[str, dict], engine, sessions, progress=None) -> dict:
    """Corre todas las variantes de todos los casos. progress: callback async con el parcial."""
    variants = run.get("variants") or []
    repetitions = int(run.get("repetitions") or 5)
    sem = asyncio.Semaphore(max(1, settings.agent_tests_concurrency))
    # Un resolver propio: el de las llamadas en vivo no se entera de las fallas de un BYOK de las pruebas.
    resolver = LLMResolver(engine.llm, engine.store.sessions)
    results, done = [], 0
    input_tokens = output_tokens = 0
    tool_revisions: dict[str, int] = {}
    total = max(1, len(run.get("cases") or []) * len(variants) * repetitions)
    for entry in run.get("cases") or []:
        case = cases.get(entry["id"]) or {"missing": True}
        item = {"case_id": entry["id"], "name": entry.get("name") or case.get("name") or "",
                "known_failure": bool(entry.get("known_failure")), "variants": []}
        prepared_all = []
        for variant in variants:
            try:
                workflow = (Workflow.model_validate(variant["definition"]) if variant.get("definition")
                            else Workflow.model_validate(agent["definition"]))
                prepared = {"workflow": workflow, "specs": [], "load_errors": []}
                if not case.get("missing"):
                    specs, load_errors = await asyncio.to_thread(_load_specs, sessions, agent["client_id"], workflow)
                    prepared["specs"] = specs
                    prepared["load_errors"] = [f"la herramienta no se cargó: {e}" for e in load_errors]
                    areas = await asyncio.to_thread(_load_areas, sessions, agent["client_id"], workflow,
                                                    (case.get("snapshot") or {}).get("channel") or "voice")
                    case = {**case, "areas": areas}
                    for spec in specs:
                        tool_revisions.setdefault(spec.slug, spec.revision)
            except Exception as e:
                prepared = {"workflow": None, "specs": [], "load_errors": [f"{type(e).__name__}: {e}"]}
            prepared_all.append(prepared)

        # Las repeticiones de esta unidad corren juntas, con el semaforo del run: como mucho N turnos al LLM.
        for variant, prepared in zip(variants, prepared_all):
            if prepared["workflow"] is None:
                reps = [_error_rep(prepared["load_errors"][0]) for _ in range(repetitions)]
            else:
                reps = await asyncio.gather(*[
                    _repetition(agent, case, variant, prepared, engine, resolver, sem)
                    for _ in range(repetitions)])
            passed = sum(1 for r in reps if r["passed"])
            errors_n = sum(1 for r in reps if r["error"])
            item["variants"].append({"key": variant["key"], "version": variant["version"], "passed": passed,
                                     "total": repetitions, "errors": errors_n, "repetitions": reps})
            for rep in reps:
                input_tokens += rep["input_tokens"]
                output_tokens += rep["output_tokens"]
            done += repetitions
            if progress is not None:
                await progress({"done": min(done, total), "total": total, "results": [*results, item],
                                "input_tokens": input_tokens, "output_tokens": output_tokens,
                                "tool_revisions": tool_revisions})
        results.append(item)
    return {"results": results, "input_tokens": input_tokens, "output_tokens": output_tokens,
            "tool_revisions": tool_revisions, "total": total}


def _error_rep(message: str) -> dict:
    return {"text": "", "tool_calls": [], "handoff": None, "status": None, "failures": [],
            "error": message, "ms": 0, "input_tokens": 0, "output_tokens": 0, "llm": {}, "tools": [],
            "passed": False}
