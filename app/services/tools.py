"""Herramientas del cliente y secretos de los agentes (docs/TOOLS_PLAN.md).

- Herramientas: del cliente, por slug. El plan dice cuantas (`max_tools`) y si pueden ser codigo
  (`code_tools`). Cambiar una sube su `revision`; borrarla falla si un agente vigente la usa.
- Secretos: de cada agente, cifrados (Fernet con WA_TOKEN_KEY, como las keys de llm_connections). No se
  devuelven nunca: solo el nombre y los ultimos 4. Al guardar un agente, cada secreto que piden sus
  herramientas tiene que existir en el agente.
"""
import logging
import re
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..conversation.models import ToolGrant, Workflow
from ..db import utcnow
from ..models import Agent, AgentSecret, Client, ClientTool, ToolVersion
from ..tools import schema as S
from ..tools.runtime import ToolContext, ToolResult, ToolSpec, run
from ..whatsapp import crypto
from . import limits as limits_service
from .errors import Conflict, Invalid, NotFound, QuotaExceeded

logger = logging.getLogger(__name__)

MAX_SECRETS_PER_AGENT = 50

CODE_TEMPLATE = '''/**
 * Herramienta de Atentina.
 * @param {object} input
 * @param {object} input.args     Lo que completa el agente, según "Parámetros".
 * @param {object} input.secrets  Los secretos que marcaste en "Secretos que usa" (del agente).
 * @param {object} input.call     La conversación: id, channel, mode, from, to, agent.
 * @param {object} input.vars     Lo que guardaron otras herramientas.
 * @returns Un objeto JSON: es lo que lee el agente.
 */
export default async function ({ args, secrets, call }) {
  const url = `https://api.ejemplo.com/clientes?dni=${encodeURIComponent(args.dni)}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${secrets.MI_TOKEN}` },
  });
  if (!res.ok) {
    return { ok: false, error: `La API respondió ${res.status}` };
  }
  const cliente = await res.json();
  console.log("cliente encontrado", cliente.id); // va a la traza, no al agente
  return { nombre: cliente.nombre, deuda: cliente.saldo };
}
'''
CODE_TEMPLATE_PARAMETERS = {"type": "object", "properties": {
    "dni": {"type": "string", "description": "DNI de la persona, sin puntos"}}, "required": ["dni"]}


_MESSAGE_PATH = re.compile(r"^([A-Za-z_][\w\-]*(?:\.[\w\-{}]+)*): (.+)$", re.S)


def _details(e: ValidationError, prefix: str = "definition") -> list[dict]:
    """Los errores con su ruta. Los validadores del modelo dicen la ruta exacta al principio del mensaje
    ("http.path: ..." con loc "http"): esa va a `path`, para marcar el campo en la UI."""
    out = []
    for err in e.errors():
        loc = [str(x) for x in err["loc"] if not str(x).startswith("function-after")]
        message = err["msg"].removeprefix("Value error, ")
        if (m := _MESSAGE_PATH.match(message)) and loc and m.group(1).split(".")[0] == loc[-1]:
            loc, message = loc[:-1] + m.group(1).split("."), m.group(2)
        elif (m := _MESSAGE_PATH.match(message)) and not loc:
            loc, message = m.group(1).split("."), m.group(2)
        path = ".".join(loc)
        out.append({"path": f"{prefix}.{path}" if path else prefix, "message": message})
    return out


def parse(tool_type: str, definition: dict) -> S.HttpTool | S.CodeTool:
    try:
        return S.parse(tool_type, definition)
    except ValidationError as e:
        raise Invalid("La herramienta no es valida", "invalid_tool", _details(e)) from None
    except ValueError as e:
        raise Invalid(str(e), "invalid_tool", [{"path": "type", "message": str(e)}]) from None


def spec_of(row: ClientTool) -> ToolSpec:
    return ToolSpec(slug=row.slug, type=row.type, revision=row.revision, tool=S.parse(row.type, row.definition))


# ---------- herramientas ----------

def list_tools(s: Session, client_id: str) -> list[ClientTool]:
    return list(s.scalars(select(ClientTool).where(ClientTool.client_id == client_id).order_by(ClientTool.slug)))


def get_tool(s: Session, client_id: str, slug: str) -> ClientTool:
    row = s.scalar(select(ClientTool).where(ClientTool.client_id == client_id, ClientTool.slug == slug))
    if row is None:
        raise NotFound(f"Herramienta inexistente: {slug}")
    return row


def used_by(s: Session, client_id: str) -> dict[str, list[dict]]:
    """slug -> agentes vigentes (no archivados) del cliente que la usan: [{id, slug, name}]."""
    out: dict[str, list[dict]] = {}
    for agent in s.scalars(select(Agent).where(Agent.client_id == client_id, Agent.archived_at.is_(None))):
        for grant in agent.definition.get("tools") or []:
            if slug := grant.get("tool"):
                out.setdefault(slug, []).append({"id": agent.id, "slug": agent.slug, "name": agent.name})
    return out


def check_plan(s: Session, client_id: str, tool_type: str, adding: bool = False) -> None:
    client = s.get(Client, client_id)
    if client is None:
        raise NotFound("Cliente inexistente")
    lim = limits_service.effective_limits(s, client)
    if lim.max_tools == 0:
        raise QuotaExceeded("Tu plan no incluye herramientas.", "tools_not_in_plan")
    if tool_type == "code" and not lim.code_tools:
        raise QuotaExceeded("Tu plan no incluye herramientas de código.", "code_tools_not_in_plan")
    if adding and lim.max_tools is not None:
        count = s.scalar(select(func.count()).select_from(ClientTool).where(ClientTool.client_id == client_id)) or 0
        if count >= lim.max_tools:
            raise QuotaExceeded(f"Tu plan incluye hasta {lim.max_tools} herramientas.", "tools_limit")


def _check_agents_have_secrets(s: Session, client_id: str, slug: str, tool: S.HttpTool | S.CodeTool) -> None:
    """Cambiar una herramienta para que pida un secreto nuevo no puede romper a los agentes que la usan."""
    needed = S.required_secrets(tool)
    if not needed:
        return
    problems = []
    for agent in used_by(s, client_id).get(slug, []):
        missing = needed - set(secret_names(s, agent["id"]))
        if missing:
            problems.append(f"{agent['name']} no tiene {', '.join(sorted(missing))}")
    if problems:
        raise Invalid("Hay agentes que usan la herramienta y no tienen sus secretos: " + "; ".join(problems)
                      + ". Cargalos en cada agente antes de guardar.", "missing_secret",
                      [{"path": "definition", "message": p} for p in problems])


def create_tool(s: Session, client_id: str, slug: str, tool_type: str, definition: dict,
                user_id: str | None) -> ClientTool:
    try:
        S.check_slug(slug)
    except ValueError as e:
        raise Invalid(str(e), "invalid_tool", [{"path": "slug", "message": str(e)}]) from None
    check_plan(s, client_id, tool_type, adding=True)
    tool = parse(tool_type, definition)
    if s.scalar(select(ClientTool.id).where(ClientTool.client_id == client_id, ClientTool.slug == slug)):
        raise Conflict(f"Ya hay una herramienta {slug!r}", "tool_slug_taken")
    row = ClientTool(client_id=client_id, slug=slug, type=tool_type, created_by=user_id,
                     definition=tool.model_dump(mode="json", by_alias=True, exclude_none=True))
    s.add(row)
    s.flush()
    _version(s, row, user_id)
    return row


def _version(s: Session, row: ClientTool, user_id: str | None) -> None:
    s.add(ToolVersion(tool_id=row.id, revision=row.revision, type=row.type, definition=row.definition,
                      created_by=user_id))


def versions(s: Session, row: ClientTool) -> list[ToolVersion]:
    """Las revisiones de la herramienta, la mas nueva primero."""
    return list(s.scalars(select(ToolVersion).where(ToolVersion.tool_id == row.id)
                          .order_by(ToolVersion.revision.desc())))


def update_tool(s: Session, row: ClientTool, tool_type: str, definition: dict,
                user_id: str | None = None) -> ClientTool:
    check_plan(s, row.client_id, tool_type, adding=False)
    tool = parse(tool_type, definition)
    dumped = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
    if dumped == row.definition and tool_type == row.type:
        return row
    _check_agents_have_secrets(s, row.client_id, row.slug, tool)
    row.type, row.definition = tool_type, dumped
    row.revision += 1
    _version(s, row, user_id)
    return row


def delete_tool(s: Session, row: ClientTool) -> None:
    if agents := used_by(s, row.client_id).get(row.slug):
        raise Conflict("La usan los agentes: " + ", ".join(a["name"] for a in agents) + ". Sacala de cada uno antes.",
                       "tool_in_use")
    s.delete(row)


# ---------- secretos ----------

def _agent_secrets(s: Session, agent_id: str) -> list[AgentSecret]:
    return list(s.scalars(select(AgentSecret).where(AgentSecret.agent_id == agent_id).order_by(AgentSecret.name)))


def secret_names(s: Session, agent_id: str) -> list[str]:
    return list(s.scalars(select(AgentSecret.name).where(AgentSecret.agent_id == agent_id)))


def list_secrets(s: Session, agent: Agent) -> list[dict]:
    """Sin valores. used_by: las herramientas del agente que lo piden."""
    needs: dict[str, list[str]] = {}
    for spec in agent_tool_specs(s, agent.client_id, agent.definition):
        for name in S.required_secrets(spec.tool):
            needs.setdefault(name, []).append(spec.slug)
    rows = _agent_secrets(s, agent.id)
    out = [{"name": r.name, "description": r.description, "last4": r.last4, "used_by": needs.get(r.name, []),
            "missing": False, "created_at": r.created_at, "updated_at": r.updated_at} for r in rows]
    have = {r.name for r in rows}
    out += [{"name": name, "description": "", "last4": "", "used_by": tools, "missing": True,
             "created_at": None, "updated_at": None} for name, tools in sorted(needs.items()) if name not in have]
    return out


def _check_secret(name: str, value: str | None) -> None:
    if not S.SECRET_RE.fullmatch(name):
        raise Invalid("name: mayúsculas, números y _ (ej. CRM_TOKEN)", "invalid_secret",
                      [{"path": "name", "message": "mayúsculas, números y _ (ej. CRM_TOKEN)"}])
    if value is not None and not (0 < len(value) <= S.MAX_SECRET_CHARS):
        raise Invalid(f"value: entre 1 y {S.MAX_SECRET_CHARS} caracteres", "invalid_secret",
                      [{"path": "value", "message": f"entre 1 y {S.MAX_SECRET_CHARS} caracteres"}])


def _last4(value: str) -> str:
    return value[-4:] if len(value) >= 12 else ""


def create_secret(s: Session, agent: Agent, name: str, value: str, description: str,
                  user_id: str | None) -> AgentSecret:
    _check_secret(name, value)
    if s.scalar(select(AgentSecret.id).where(AgentSecret.agent_id == agent.id, AgentSecret.name == name)):
        raise Conflict(f"El agente ya tiene el secreto {name}", "secret_name_taken")
    if len(secret_names(s, agent.id)) >= MAX_SECRETS_PER_AGENT:
        raise Invalid(f"Un agente puede tener hasta {MAX_SECRETS_PER_AGENT} secretos", "secrets_limit")
    row = AgentSecret(agent_id=agent.id, name=name, value_enc=crypto.encrypt(value), last4=_last4(value),
                      description=description.strip()[:255], created_by=user_id)
    s.add(row)
    s.flush()
    return row


def get_secret(s: Session, agent: Agent, name: str) -> AgentSecret:
    row = s.scalar(select(AgentSecret).where(AgentSecret.agent_id == agent.id, AgentSecret.name == name))
    if row is None:
        raise NotFound(f"El agente no tiene el secreto {name}")
    return row


def update_secret(s: Session, row: AgentSecret, value: str | None, description: str | None) -> AgentSecret:
    _check_secret(row.name, value)
    if value is not None:
        row.value_enc, row.last4 = crypto.encrypt(value), _last4(value)
    if description is not None:
        row.description = description.strip()[:255]
    row.updated_at = utcnow()
    return row


def delete_secret(s: Session, agent: Agent, row: AgentSecret) -> None:
    users = [spec.slug for spec in agent_tool_specs(s, agent.client_id, agent.definition)
             if row.name in S.required_secrets(spec.tool)]
    if users:
        raise Conflict(f"Lo usan las herramientas del agente: {', '.join(users)}", "secret_in_use")
    s.delete(row)


def secret_values(s: Session, agent_id: str) -> dict[str, str]:
    """Descifrados, para ejecutar. Un secreto que no se puede descifrar (otra WA_TOKEN_KEY) falta."""
    out = {}
    for row in _agent_secrets(s, agent_id):
        try:
            out[row.name] = crypto.decrypt(row.value_enc)
        except Exception:
            logger.warning("tools: no se pudo descifrar el secreto %s del agente %s", row.name, agent_id)
    return out


# ---------- agentes ----------

def _grants(definition: dict | Workflow) -> list[ToolGrant]:
    if isinstance(definition, Workflow):
        return definition.tools
    return [ToolGrant(tool=g["tool"]) for g in definition.get("tools") or [] if isinstance(g, dict) and g.get("tool")]


def agent_tool_specs(s: Session, client_id: str | None, definition: dict | Workflow) -> list[ToolSpec]:
    """Las herramientas del cliente que usa el agente, en su orden. Las que faltan se ignoran (se valida al
    guardar el agente)."""
    grants = _grants(definition)
    if not grants or client_id is None:
        return []
    rows = {r.slug: r for r in s.scalars(select(ClientTool).where(
        ClientTool.client_id == client_id, ClientTool.slug.in_([g.tool for g in grants])))}
    out = []
    for g in grants:
        if (row := rows.get(g.tool)) is None:
            continue
        try:
            out.append(spec_of(row))
        except (ValidationError, ValueError):
            logger.warning("tools: definicion invalida de %s (cliente %s)", row.slug, client_id)
    return out


def check_agent_tools(s: Session, client_id: str, agent_id: str | None, normalized: dict) -> None:
    """Al guardar un agente: cada herramienta existe, es del cliente, el plan la incluye y el agente tiene sus
    secretos."""
    entries = [(i, g) for i, g in enumerate(normalized.get("tools") or []) if g.get("tool")]
    if not entries:
        return
    client = s.get(Client, client_id)
    lim = limits_service.effective_limits(s, client) if client else None
    rows = {r.slug: r for r in s.scalars(select(ClientTool).where(ClientTool.client_id == client_id))}
    have = set(secret_names(s, agent_id)) if agent_id else set()
    errors = []
    for i, g in entries:
        row = rows.get(g["tool"])
        path = f"tools.{i}.tool"
        if row is None:
            errors.append({"path": path, "message": f"El cliente no tiene la herramienta {g['tool']!r}"})
            continue
        if lim is not None and (lim.max_tools == 0 or (row.type == "code" and not lim.code_tools)):
            errors.append({"path": path, "message": f"Tu plan no incluye la herramienta {row.slug!r} "
                                                    f"({'código' if row.type == 'code' else 'herramientas'})"})
            continue
        missing = S.required_secrets(spec_of(row).tool) - have
        if missing:
            errors.append({"path": path, "message": f"El agente no tiene los secretos {', '.join(sorted(missing))}: "
                                                    "cargalos en Secretos del agente"})
    if errors:
        raise Invalid("La definicion del agente no es valida", "invalid_definition", errors)


# ---------- prueba ----------

async def test_tool(s_factory, client_id: str, tool_type: str, definition: dict, args: dict, *,
                    slug: str = "prueba", revision: int = 0, agent_id: str | None = None,
                    secrets: dict[str, str] | None = None, call: dict | None = None) -> ToolResult:
    """Ejecuta una definicion (guardada o no) con los secretos del agente o con los del pedido (no se
    guardan)."""
    tool = parse(tool_type, definition)
    values = dict(secrets or {})
    agent_slug = ""
    if agent_id:
        with s_factory() as s:
            agent = s.get(Agent, agent_id)
            if agent is None or agent.client_id != client_id:
                raise NotFound("Agente inexistente")
            agent_slug = agent.slug
            values = {**secret_values(s, agent_id), **values}
    call = call or {}
    ctx = ToolContext(conversation_id=str(call.get("id") or "prueba"), channel=call.get("channel") or "voice",
                      mode=call.get("mode") or "prueba", from_=call.get("from"), to=call.get("to"),
                      agent_slug=agent_slug, secrets=values)
    spec = ToolSpec(slug=slug, type=tool_type, revision=revision, tool=tool)
    return await run(spec, args, ctx)


def record_test(s: Session, row: ClientTool, result: ToolResult) -> None:
    row.last_test_at = utcnow()
    row.last_test_ok = result.ok
    row.last_test_detail = ("ok" if result.ok else (result.error or "error"))[:255]


def describe(row: ClientTool, users: list[dict] | None = None) -> dict[str, Any]:
    try:
        tool = S.parse(row.type, row.definition)
        llm = S.openai_tool(row.slug, tool)
        needed = sorted(S.required_secrets(tool))
    except (ValidationError, ValueError):
        llm, needed = None, []
    return {"id": row.id, "slug": row.slug, "type": row.type, "definition": row.definition,
            "revision": row.revision, "secrets": needed, "llm_tool": llm, "used_by": users or [],
            "last_test_at": row.last_test_at, "last_test_ok": row.last_test_ok,
            "last_test_detail": row.last_test_detail, "created_at": row.created_at, "updated_at": row.updated_at}
