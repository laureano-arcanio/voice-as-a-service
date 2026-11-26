"""Casos de prueba de un agente: la copia de una conversacion hasta un turno del usuario, con los resultados de
herramienta de ese turno y los chequeos deterministas (docs/features/CASOS_DE_PRUEBA.md).

El caso nunca ejecuta la herramienta: guarda lo que recibio el modelo. La corrida la hace
app/agent_tests/runner.py contra la version guardada o contra la definicion sin guardar.
"""
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session, load_only

from ..conversation.models import Message
from ..db import utcnow
from ..llm.prompt import TRUNCATED
from ..models import AgentTestCase, AgentTestRun, ConversationRow
from ..services import errors
from .checks import validate as validate_checks

MAX_CASES = 30
MAX_MESSAGES = 200
MAX_SNAPSHOT_BYTES = 256 * 1024
MAX_TOOL_RESULTS = 20
MAX_RESULT_CHARS = 50_000
# Lo que no se guarda del mensaje: la traza del LLM y la grabacion.
_DROP = {"llm", "recording"}


def _messages(row: ConversationRow, index: int) -> list[dict]:
    """Los mensajes crudos de la conversacion (dicts, como los guarda el store)."""
    return list(row.messages or [])


def _clean(message: dict) -> dict:
    return Message.model_validate(message).model_dump(mode="json", exclude=_DROP)


def _trace_outputs(message: dict) -> list[str]:
    """Las salidas de las herramientas de la traza del turno, en el orden en que corrieron."""
    return [t.get("output") or "" for t in (message.get("llm") or []) if t.get("kind") == "herramienta"]


def tool_results_of(message: dict | None) -> list[dict]:
    """`{name, arguments, result}` de las herramientas del turno. Si el resultado guardado se recorto, se toma la
    salida completa de la traza (mismo orden)."""
    tools = (message or {}).get("tools") or []
    outputs = _trace_outputs(message or {})
    out = []
    for i, tool in enumerate(tools[:MAX_TOOL_RESULTS]):
        result = str(tool.get("result") or "")
        if result.endswith(TRUNCATED) and i < len(outputs) and outputs[i]:
            result = outputs[i]
        out.append({"name": tool.get("name") or "", "arguments": tool.get("arguments") or "",
                    "result": result[:MAX_RESULT_CHARS]})
    return out


def _progress(row: ConversationRow) -> dict:
    """El espacio de variables sin las que asigno una herramienta despues del turno (no estaban en el prompt)."""
    progress = row.progress or {}
    sources = progress.get("variable_sources") or {}
    all_variables = progress.get("variables") or {}
    # Sin fuente (conversaciones viejas) no es de una herramienta: se conserva.
    keep = {k for k, source in sources.items() if not str(source).startswith("tool:")}
    keep |= set(all_variables) - set(sources)
    variables = {k: v for k, v in all_variables.items() if k in keep}
    hidden = [k for k in (progress.get("hidden_variables") or []) if k in keep]
    call = progress.get("call") or {}
    return {"variables": variables, "hidden_variables": hidden,
            "variable_sources": {k: v for k, v in sources.items() if k in keep},
            "call": call, "started_at": progress.get("started_at"),
            "caller_phone": progress.get("caller_phone"),
            "channel": row.channel or "voice",
            "handoff": bool(progress.get("handoff_areas")) or call.get("mode") == "api",
            "test_workflows": bool(progress.get("test_workflows"))}


def _check_index(row: ConversationRow, index: int) -> dict:
    messages = _messages(row, index)
    if not (0 <= index < len(messages)):
        raise errors.Invalid(f"El mensaje {index} no existe en la conversación", "invalid_message_index")
    message = messages[index]
    if message.get("role") != "user" or message.get("handoff_leg"):
        raise errors.Invalid("El mensaje tiene que ser del usuario, fuera de un tramo derivado",
                             "invalid_message_index")
    return message


def _reply_of(messages: list[dict], index: int) -> dict:
    """Lo que contesto el agente despues del turno del usuario: texto, herramientas, derivacion y resultados."""
    reply = messages[index + 1] if index + 1 < len(messages) else None
    if reply is None or reply.get("role") != "assistant":
        reply = None
    tools = tool_results_of(reply)
    return {"text": (reply or {}).get("text") or "",
            "tool_calls": [{"name": t["name"], "arguments": t["arguments"]} for t in tools],
            "handoff": (reply or {}).get("handoff"),
            "tool_results": [t["result"] for t in tools]}


def preview(row: ConversationRow, index: int) -> dict:
    """La copia que se guardaria, la respuesta original y los chequeos sugeridos. No guarda nada."""
    message = _check_index(row, index)
    messages = _messages(row, index)
    if index > MAX_MESSAGES:
        raise errors.Invalid(f"Hasta {MAX_MESSAGES} mensajes en el caso", "too_many_messages")
    reply = _reply_of(messages, index)
    progress = _progress(row)
    snapshot = {"messages": [_clean(m) for m in messages[:index]],
                "user_message": message.get("text") or "",
                "user_message_at": message.get("at"),
                "progress": progress,
                "channel": row.channel or "voice",
                "handoff": progress["handoff"]}
    from .checks import suggest
    return {"snapshot": snapshot, "reply": reply, "checks": suggest(reply)}


def draft(row: ConversationRow, index: int, data: dict) -> dict:
    """Un caso sin guardar ("Probar ahora"): mismo snapshot y validaciones que crear, sin la tabla."""
    previewed = preview(row, index)
    snapshot = _body_snapshot(data, previewed)
    tool_results = (_normalize_tool_results(data.get("tool_results"))
                    if data.get("tool_results") is not None
                    else tool_results_of(_reply_message(row, index)))
    try:
        checks = validate_checks(data.get("checks"))
    except ValueError as e:
        raise errors.Invalid("Los chequeos no son válidos", "invalid_checks",
                             [{"path": getattr(e, "path", "checks"),
                               "message": getattr(e, "message", str(e))}]) from None
    _check_size(snapshot, tool_results)
    return {"id": "draft", "name": (data.get("name") or "Caso de prueba").strip()[:200],
            "checks": checks, "known_failure": bool(data.get("known_failure")),
            "snapshot": snapshot, "tool_results": tool_results}


def _body_snapshot(data: dict, previewed: dict) -> dict:
    """Lo que manda el pedido pisa el snapshot generado (messages, user_message, tool_results)."""
    snapshot = dict(previewed["snapshot"])
    if data.get("messages") is not None:
        if len(data["messages"]) > MAX_MESSAGES:
            raise errors.Invalid(f"Hasta {MAX_MESSAGES} mensajes en el caso", "too_many_messages")
        snapshot["messages"] = [_clean(m) for m in data["messages"]]
    if data.get("user_message") is not None:
        snapshot["user_message"] = str(data["user_message"])
    return snapshot


def _normalize_tool_results(items) -> list[dict]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise errors.Invalid("tool_results tiene que ser una lista", "invalid_tool_results")
    if len(items) > MAX_TOOL_RESULTS:
        raise errors.Invalid(f"Hasta {MAX_TOOL_RESULTS} resultados de herramienta", "too_many_tool_results")
    out = []
    for item in items:
        if not isinstance(item, dict):
            raise errors.Invalid("Cada resultado tiene que ser {name, arguments, result}", "invalid_tool_results")
        result = item.get("result")
        if not isinstance(result, str):
            result = json.dumps(result, ensure_ascii=False)
        if len(result) > MAX_RESULT_CHARS:
            raise errors.Invalid(f"Cada resultado hasta {MAX_RESULT_CHARS} caracteres", "tool_result_too_large")
        out.append({"name": str(item.get("name") or ""), "arguments": item.get("arguments") or "", "result": result})
    return out


def _check_size(snapshot: dict, tool_results: list[dict]) -> None:
    raw = json.dumps({"snapshot": snapshot, "tool_results": tool_results}, ensure_ascii=False).encode()
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise errors.Invalid(f"El caso pasa de {MAX_SNAPSHOT_BYTES // 1024} KB", "case_too_large")


def count_for_agent(s: Session, agent_id: str) -> int:
    return s.scalar(select(func.count()).select_from(AgentTestCase)
                    .where(AgentTestCase.agent_id == agent_id)) or 0


def create(s: Session, agent, row: ConversationRow, index: int, data: dict, user_id: str | None) -> AgentTestCase:
    """Crea el caso desde la conversacion. data: name, checks, known_failure y, opcionales, messages, user_message
    y tool_results que pisan lo generado."""
    if count_for_agent(s, agent.id) >= MAX_CASES:
        raise errors.Invalid(f"El agente ya tiene {MAX_CASES} casos de prueba", "too_many_cases")
    previewed = preview(row, index)
    snapshot = _body_snapshot(data, previewed)
    tool_results = (_normalize_tool_results(data.get("tool_results"))
                    if data.get("tool_results") is not None
                    else tool_results_of(_reply_message(row, index)))
    try:
        checks = validate_checks(data.get("checks"))
    except ValueError as e:
        raise errors.Invalid("Los chequeos no son válidos", "invalid_checks",
                             [{"path": getattr(e, "path", "checks"), "message": getattr(e, "message", str(e))}]) from None
    _check_size(snapshot, tool_results)
    case = AgentTestCase(client_id=agent.client_id, agent_id=agent.id,
                         name=(data.get("name") or "Caso de prueba").strip()[:200],
                         source_conversation_id=row.id, source_message_index=index,
                         source_agent_version=row.agent_version, channel=row.channel or "voice",
                         snapshot=snapshot, tool_results=tool_results, checks=checks,
                         known_failure=bool(data.get("known_failure")), created_by=user_id)
    s.add(case)
    s.flush()
    return case


def _reply_message(row: ConversationRow, index: int) -> dict | None:
    messages = row.messages or []
    reply = messages[index + 1] if index + 1 < len(messages) else None
    return reply if reply and reply.get("role") == "assistant" else None


def update(s: Session, case: AgentTestCase, data: dict) -> AgentTestCase:
    """PATCH: nombre, chequeos, falla conocida y lo grabado (messages, user_message, tool_results)."""
    if "name" in data and data["name"] is not None:
        case.name = str(data["name"]).strip()[:200] or case.name
    if "known_failure" in data and data["known_failure"] is not None:
        case.known_failure = bool(data["known_failure"])
    if "checks" in data:
        try:
            case.checks = validate_checks(data["checks"])
        except ValueError as e:
            raise errors.Invalid("Los chequeos no son válidos", "invalid_checks",
                                 [{"path": getattr(e, "path", "checks"),
                                   "message": getattr(e, "message", str(e))}]) from None
    snapshot = dict(case.snapshot or {})
    if "messages" in data and data["messages"] is not None:
        if len(data["messages"]) > MAX_MESSAGES:
            raise errors.Invalid(f"Hasta {MAX_MESSAGES} mensajes en el caso", "too_many_messages")
        snapshot["messages"] = [_clean(m) for m in data["messages"]]
    if "user_message" in data and data["user_message"] is not None:
        snapshot["user_message"] = str(data["user_message"])
    tool_results = _normalize_tool_results(data["tool_results"]) if "tool_results" in data \
        else case.tool_results or []
    case.snapshot = snapshot
    case.tool_results = tool_results
    _check_size(snapshot, tool_results)
    case.updated_at = utcnow()
    return case


def get_for_agent(s: Session, agent, case_id: str) -> AgentTestCase:
    case = s.get(AgentTestCase, case_id)
    if case is None or case.agent_id != agent.id or case.client_id != agent.client_id:
        raise errors.NotFound("Caso de prueba inexistente")
    return case


def list_for_agent(s: Session, agent) -> list[AgentTestCase]:
    return list(s.scalars(select(AgentTestCase).where(AgentTestCase.agent_id == agent.id)
                          .order_by(AgentTestCase.created_at.desc())))


def last_runs(s: Session, agent_id: str) -> dict[str, AgentTestRun]:
    """La ultima corrida de cada caso (la que lo incluyo), para el `pasa X/N` de la lista. Solo el resumen."""
    out: dict[str, AgentTestRun] = {}
    runs = s.scalars(select(AgentTestRun).where(AgentTestRun.agent_id == agent_id,
                                                AgentTestRun.status == "done")
                     .options(load_only(AgentTestRun.id, AgentTestRun.created_at, AgentTestRun.cases,
                                        AgentTestRun.summary))
                     .order_by(AgentTestRun.created_at.desc()))
    for run in runs:
        for case in run.cases or []:
            out.setdefault(case.get("id"), run)
    return out


def history(s: Session, agent_id: str, case_id: str, limit: int = 20) -> list[AgentTestRun]:
    """Las corridas del agente que incluyeron el caso, de la mas nueva a la mas vieja. Solo el resumen."""
    runs = s.scalars(select(AgentTestRun).where(AgentTestRun.agent_id == agent_id,
                                                AgentTestRun.status == "done")
                     .options(load_only(AgentTestRun.id, AgentTestRun.created_at, AgentTestRun.cases,
                                        AgentTestRun.summary))
                     .order_by(AgentTestRun.created_at.desc()))
    return [r for r in runs if any(c.get("id") == case_id for c in (r.cases or []))][:limit]


def delete(s: Session, case: AgentTestCase) -> None:
    s.delete(case)
