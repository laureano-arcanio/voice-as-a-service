"""Herramientas, secretos y credenciales del cliente (docs/features/HERRAMIENTAS.md).

- Herramientas: del cliente, por slug. El plan dice cuantas (`max_tools`) y si pueden ser codigo
  (`code_tools`). Cambiar una sube su `revision`; borrarla falla si un agente vigente la usa.
- Secretos: del cliente (para todos sus agentes) y de un agente, que pisa al del cliente con el mismo nombre.
  Cifrados (Fernet con WA_TOKEN_KEY, como las keys de llm_connections) y no se devuelven nunca: solo el nombre
  y los ultimos 4. Al guardar un agente, cada secreto que piden sus herramientas tiene que estar en el cliente o
  en el agente.
- Credenciales: la autenticacion de una API (tipo, datos y el nombre del secreto con el valor), del cliente,
  para usarla en varias herramientas sin repetirla. Una herramienta la usa con auth {"type": "credential"}.
"""
import logging
import re
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..conversation.models import ToolGrant, Workflow
from ..db import utcnow
from ..models import (
    Agent,
    AgentSecret,
    Client,
    ClientSecret,
    ClientTool,
    Credential,
    ToolVersion,
)
from ..tools import schema as S
from ..tools.runtime import ToolContext, ToolResult, ToolSpec, run
from ..whatsapp import crypto
from . import limits as limits_service
from .errors import Conflict, Invalid, NotFound, QuotaExceeded

logger = logging.getLogger(__name__)

MAX_SECRETS_PER_AGENT = 50
MAX_SECRETS_PER_CLIENT = 100
MAX_CREDENTIALS_PER_CLIENT = 50

CODE_TEMPLATE = '''/**
 * Herramienta de Atentina.
 * @param {object} input
 * @param {object} input.args     Lo que completa el agente, según "Parámetros".
 * @param {object} input.secrets  Los secretos que marcaste en "Secretos que usa" (del cliente o del agente).
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


def spec_of(row: ClientTool, credentials: dict[str, S.Auth] | None = None) -> ToolSpec:
    """La herramienta lista para correr, con su credencial resuelta."""
    tool = S.resolve(S.parse(row.type, row.definition), credentials or {})
    return ToolSpec(slug=row.slug, type=row.type, revision=row.revision, tool=tool, tool_id=row.id)


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


def _check_agents_have_secrets(s: Session, client_id: str, slugs: list[str], needed: set[str]) -> None:
    """Cambiar una herramienta (o su credencial) para que pida un secreto nuevo no puede romper a los agentes que
    la usan: cada uno tiene que tenerlo, propio o del cliente."""
    if not needed:
        return
    users = used_by(s, client_id)
    agents = {a["id"]: a for slug in slugs for a in users.get(slug, [])}
    if not agents:
        return
    client_names = set(client_secret_names(s, client_id))
    problems = []
    for agent in agents.values():
        missing = needed - client_names - set(secret_names(s, agent["id"]))
        if missing:
            problems.append(f"{agent['name']} no tiene {', '.join(sorted(missing))}")
    if problems:
        raise Invalid("Hay agentes que la usan y no tienen sus secretos: " + "; ".join(problems)
                      + ". Cargalos en Secretos (para todos los agentes) o en cada agente antes de guardar.",
                      "missing_secret", [{"path": "definition", "message": p} for p in problems])


def _check_credential(s: Session, client_id: str, tool: S.HttpTool | S.CodeTool) -> S.HttpTool | S.CodeTool:
    """La credencial que usa la herramienta existe y su header no choca con los de la herramienta. Devuelve la
    herramienta resuelta."""
    slug = S.credential_of(tool)
    if slug is None:
        return tool
    creds = credentials_map(s, client_id)
    if slug not in creds:
        raise Invalid(f"No existe la credencial {slug!r}", "invalid_tool",
                      [{"path": "definition.http.auth.credential", "message": f"No existe la credencial {slug!r}"}])
    resolved = S.resolve(tool, creds)
    header = resolved.http.auth.header_name()
    if header and header.lower() in {h.lower() for h in resolved.http.headers}:
        message = f"ya lo pone la credencial {slug}"
        raise Invalid(f"http.headers.{header}: {message}", "invalid_tool",
                      [{"path": f"definition.http.headers.{header}", "message": message}])
    return resolved


def create_tool(s: Session, client_id: str, slug: str, tool_type: str, definition: dict,
                user_id: str | None) -> ClientTool:
    try:
        S.check_slug(slug)
    except ValueError as e:
        raise Invalid(str(e), "invalid_tool", [{"path": "slug", "message": str(e)}]) from None
    check_plan(s, client_id, tool_type, adding=True)
    tool = parse(tool_type, definition)
    _check_credential(s, client_id, tool)
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
    resolved = _check_credential(s, row.client_id, tool)
    _check_agents_have_secrets(s, row.client_id, [row.slug], S.required_secrets(resolved))
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


def _client_secrets(s: Session, client_id: str) -> list[ClientSecret]:
    return list(s.scalars(select(ClientSecret).where(ClientSecret.client_id == client_id).order_by(ClientSecret.name)))


def secret_names(s: Session, agent_id: str) -> list[str]:
    """Los propios del agente."""
    return list(s.scalars(select(AgentSecret.name).where(AgentSecret.agent_id == agent_id)))


def client_secret_names(s: Session, client_id: str) -> list[str]:
    return list(s.scalars(select(ClientSecret.name).where(ClientSecret.client_id == client_id)))


def _tool_needs(s: Session, client_id: str) -> dict[str, set[str]]:
    """slug de cada herramienta del cliente -> los secretos que pide (con su credencial resuelta)."""
    creds = credentials_map(s, client_id)
    out = {}
    for row in list_tools(s, client_id):
        try:
            out[row.slug] = S.required_secrets(spec_of(row, creds).tool)
        except (ValidationError, ValueError):
            out[row.slug] = set()
    return out


def list_secrets(s: Session, agent: Agent) -> list[dict]:
    """Los secretos que ve el agente, sin valores: los propios (`source` agent; `overrides` si pisan uno del
    cliente), los del cliente que piden sus herramientas (`source` client) y los que faltan (`missing`).
    used_by: las herramientas del agente que lo piden."""
    needs: dict[str, list[str]] = {}
    for spec in agent_tool_specs(s, agent.client_id, agent.definition):
        for name in S.required_secrets(spec.tool):
            needs.setdefault(name, []).append(spec.slug)
    own = _agent_secrets(s, agent.id)
    client = {r.name: r for r in _client_secrets(s, agent.client_id)} if agent.client_id else {}
    out = [{"name": r.name, "description": r.description, "last4": r.last4, "used_by": needs.get(r.name, []),
            "missing": False, "source": "agent", "overrides": r.name in client,
            "created_at": r.created_at, "updated_at": r.updated_at} for r in own]
    have = {r.name for r in own}
    for name, tools in sorted(needs.items()):
        if name in have:
            continue
        if (r := client.get(name)) is not None:
            out.append({"name": name, "description": r.description, "last4": r.last4, "used_by": tools,
                        "missing": False, "source": "client", "overrides": False,
                        "created_at": r.created_at, "updated_at": r.updated_at})
        else:
            out.append({"name": name, "description": "", "last4": "", "used_by": tools, "missing": True,
                        "source": None, "overrides": False, "created_at": None, "updated_at": None})
    return out


def list_client_secrets(s: Session, client_id: str) -> list[dict]:
    """Los del cliente, sin valores, con quien los usa: herramientas, credenciales y los agentes que tienen su
    propio valor. Tambien los que piden las herramientas y faltan (`missing`)."""
    tools: dict[str, list[str]] = {}
    for slug, names in _tool_needs(s, client_id).items():
        for name in names:
            tools.setdefault(name, []).append(slug)
    creds: dict[str, list[str]] = {}
    for c in list_credentials(s, client_id):
        if secret := (c.auth or {}).get("secret"):
            creds.setdefault(secret, []).append(c.slug)
    overrides: dict[str, list[dict]] = {}
    for name, agent_id, agent_name in s.execute(
            select(AgentSecret.name, Agent.id, Agent.name).join(Agent, Agent.id == AgentSecret.agent_id)
            .where(Agent.client_id == client_id, Agent.archived_at.is_(None)).order_by(Agent.name)):
        overrides.setdefault(name, []).append({"id": agent_id, "name": agent_name})
    rows = _client_secrets(s, client_id)

    def one(name: str, r: ClientSecret | None) -> dict:
        return {"name": name, "description": r.description if r else "", "last4": r.last4 if r else "",
                "missing": r is None, "used_by": tools.get(name, []), "credentials": creds.get(name, []),
                "agents": overrides.get(name, []), "created_at": r.created_at if r else None,
                "updated_at": r.updated_at if r else None}

    have = {r.name for r in rows}
    return [one(r.name, r) for r in rows] + [one(name, None) for name in sorted(set(tools) | set(creds))
                                             if name not in have]


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


def update_secret(s: Session, row: AgentSecret | ClientSecret, value: str | None,
                  description: str | None) -> AgentSecret | ClientSecret:
    _check_secret(row.name, value)
    if value is not None:
        row.value_enc, row.last4 = crypto.encrypt(value), _last4(value)
    if description is not None:
        row.description = description.strip()[:255]
    row.updated_at = utcnow()
    return row


def delete_secret(s: Session, agent: Agent, row: AgentSecret) -> None:
    """Sin el propio, el agente usa el del cliente; si el cliente no lo tiene y una herramienta lo pide, 409."""
    if agent.client_id and row.name in client_secret_names(s, agent.client_id):
        s.delete(row)
        return
    users = [spec.slug for spec in agent_tool_specs(s, agent.client_id, agent.definition)
             if row.name in S.required_secrets(spec.tool)]
    if users:
        raise Conflict(f"Lo usan las herramientas del agente: {', '.join(users)}", "secret_in_use")
    s.delete(row)


def create_client_secret(s: Session, client_id: str, name: str, value: str, description: str,
                         user_id: str | None) -> ClientSecret:
    _check_secret(name, value)
    if s.scalar(select(ClientSecret.id).where(ClientSecret.client_id == client_id, ClientSecret.name == name)):
        raise Conflict(f"Ya hay un secreto {name}", "secret_name_taken")
    if len(client_secret_names(s, client_id)) >= MAX_SECRETS_PER_CLIENT:
        raise Invalid(f"Un cliente puede tener hasta {MAX_SECRETS_PER_CLIENT} secretos", "secrets_limit")
    row = ClientSecret(client_id=client_id, name=name, value_enc=crypto.encrypt(value), last4=_last4(value),
                       description=description.strip()[:255], created_by=user_id)
    s.add(row)
    s.flush()
    return row


def get_client_secret(s: Session, client_id: str, name: str) -> ClientSecret:
    row = s.scalar(select(ClientSecret).where(ClientSecret.client_id == client_id, ClientSecret.name == name))
    if row is None:
        raise NotFound(f"No hay un secreto {name}")
    return row


def delete_client_secret(s: Session, client_id: str, row: ClientSecret) -> None:
    """409 si lo usa una credencial, o una herramienta de un agente que no tiene su propio valor."""
    creds = [c.slug for c in list_credentials(s, client_id) if (c.auth or {}).get("secret") == row.name]
    if creds:
        raise Conflict(f"Lo usan las credenciales: {', '.join(creds)}", "secret_in_use")
    needs = _tool_needs(s, client_id)
    problems = []
    for slug, agents in used_by(s, client_id).items():
        if row.name not in needs.get(slug, set()):
            continue
        problems += [f"{a['name']} ({slug})" for a in agents if row.name not in secret_names(s, a["id"])]
    if problems:
        raise Conflict(f"Lo usan los agentes: {', '.join(sorted(set(problems)))}", "secret_in_use")
    s.delete(row)


def promote_secret(s: Session, agent: Agent, row: AgentSecret, user_id: str | None) -> int:
    """Pasa un secreto del agente al cliente (para todos los agentes): lo crea en el cliente con el mismo valor y
    borra el del agente y el de los otros agentes que tienen el mismo valor. 409 si el cliente ya tiene uno con
    otro valor. Devuelve cuantos agentes dejaron de tener el propio."""
    value = crypto.decrypt(row.value_enc)
    existing = s.scalar(select(ClientSecret).where(ClientSecret.client_id == agent.client_id,
                                                   ClientSecret.name == row.name))
    if existing is not None and crypto.decrypt(existing.value_enc) != value:
        raise Conflict(f"El cliente ya tiene {row.name} con otro valor: si es el mismo dato, reemplazá uno de los "
                       "dos; si no, dejalo en el agente.", "secret_name_taken")
    if existing is None:
        create_client_secret(s, agent.client_id, row.name, value, row.description, user_id)
    moved = 0
    for other in s.scalars(select(AgentSecret).join(Agent, Agent.id == AgentSecret.agent_id).where(
            Agent.client_id == agent.client_id, AgentSecret.name == row.name)):
        try:
            same = crypto.decrypt(other.value_enc) == value
        except Exception:
            same = False
        if same:
            s.delete(other)
            moved += 1
    return moved


def _decrypt_all(rows: list, owner: str) -> dict[str, str]:
    out = {}
    for row in rows:
        try:
            out[row.name] = crypto.decrypt(row.value_enc)
        except Exception:
            logger.warning("tools: no se pudo descifrar el secreto %s de %s", row.name, owner)
    return out


def client_secret_values(s: Session, client_id: str) -> dict[str, str]:
    return _decrypt_all(_client_secrets(s, client_id), f"el cliente {client_id}")


def secret_values(s: Session, agent_id: str) -> dict[str, str]:
    """Los del cliente del agente, pisados por los del agente; descifrados, para ejecutar. Un secreto que no se
    puede descifrar (otra WA_TOKEN_KEY) falta."""
    client_id = s.scalar(select(Agent.client_id).where(Agent.id == agent_id))
    base = client_secret_values(s, client_id) if client_id else {}
    return {**base, **_decrypt_all(_agent_secrets(s, agent_id), f"el agente {agent_id}")}


# ---------- credenciales ----------

def list_credentials(s: Session, client_id: str) -> list[Credential]:
    return list(s.scalars(select(Credential).where(Credential.client_id == client_id).order_by(Credential.name)))


def credentials_map(s: Session, client_id: str | None) -> dict[str, S.Auth]:
    """slug -> Auth, para resolver las herramientas. Una invalida se ignora (la herramienta falla al correr)."""
    if client_id is None:
        return {}
    out = {}
    for c in list_credentials(s, client_id):
        try:
            out[c.slug] = S.credential_auth(c.auth)
        except (ValidationError, ValueError):
            logger.warning("tools: credencial invalida %s (cliente %s)", c.slug, client_id)
    return out


def get_credential(s: Session, client_id: str, slug: str) -> Credential:
    row = s.scalar(select(Credential).where(Credential.client_id == client_id, Credential.slug == slug))
    if row is None:
        raise NotFound(f"Credencial inexistente: {slug}")
    return row


def credential_users(s: Session, client_id: str) -> dict[str, list[str]]:
    """slug de la credencial -> herramientas que la usan."""
    out: dict[str, list[str]] = {}
    for row in list_tools(s, client_id):
        try:
            slug = S.credential_of(S.parse(row.type, row.definition))
        except (ValidationError, ValueError):
            continue
        if slug:
            out.setdefault(slug, []).append(row.slug)
    return out


def _dump_auth(auth: S.Auth) -> dict:
    out = auth.model_dump(mode="json", by_alias=True, exclude_none=True)
    if auth.type != "oauth2_client_credentials":
        out.pop("client_auth", None)
    return out


def _parse_credential_auth(auth: dict) -> S.Auth:
    try:
        return S.credential_auth(auth)
    except ValidationError as e:
        raise Invalid("La credencial no es valida", "invalid_credential", _details(e, "auth")) from None
    except ValueError as e:
        raise Invalid(str(e), "invalid_credential", [{"path": "auth.type", "message": str(e)}]) from None


def _store_value(s: Session, client_id: str, name: str, value: str | None, description: str,
                 user_id: str | None) -> None:
    """El valor que viene con la credencial va al secreto del cliente (lo crea o lo reemplaza)."""
    if value is None:
        if name not in client_secret_names(s, client_id):
            raise Invalid(f"value: falta el valor del secreto {name}", "invalid_credential",
                          [{"path": "value", "message": "Escribí el valor"}])
        return
    existing = s.scalar(select(ClientSecret).where(ClientSecret.client_id == client_id, ClientSecret.name == name))
    if existing is None:
        create_client_secret(s, client_id, name, value, description, user_id)
    else:
        update_secret(s, existing, value, None)


def create_credential(s: Session, client_id: str, slug: str, name: str, description: str, auth: dict,
                      value: str | None, user_id: str | None) -> Credential:
    """value: el token, la key, la clave o el client secret; se guarda en el secreto del cliente `auth.secret`.
    Sin value, ese secreto ya tiene que existir."""
    check_plan(s, client_id, "http")
    try:
        S.check_slug(slug)
    except ValueError as e:
        raise Invalid(str(e), "invalid_credential", [{"path": "slug", "message": str(e)}]) from None
    parsed = _parse_credential_auth(auth)
    if s.scalar(select(Credential.id).where(Credential.client_id == client_id, Credential.slug == slug)):
        raise Conflict(f"Ya hay una credencial {slug!r}", "credential_slug_taken")
    if len(list_credentials(s, client_id)) >= MAX_CREDENTIALS_PER_CLIENT:
        raise Invalid(f"Un cliente puede tener hasta {MAX_CREDENTIALS_PER_CLIENT} credenciales", "credentials_limit")
    _store_value(s, client_id, parsed.secret or "", value, name, user_id)
    row = Credential(client_id=client_id, slug=slug, name=name.strip()[:120], description=description.strip()[:255],
                     auth=_dump_auth(parsed), created_by=user_id)
    s.add(row)
    s.flush()
    return row


def update_credential(s: Session, row: Credential, name: str, description: str, auth: dict, value: str | None,
                      user_id: str | None) -> Credential:
    """Rige desde ya en todas las herramientas que la usan."""
    parsed = _parse_credential_auth(auth)
    _store_value(s, row.client_id, parsed.secret or "", value, name, user_id)
    tools = credential_users(s, row.client_id).get(row.slug, [])
    for slug in tools:
        h = S.parse("http", get_tool(s, row.client_id, slug).definition).http
        header = parsed.header_name()
        if header and header.lower() in {x.lower() for x in h.headers}:
            raise Invalid(f"auth: la herramienta {slug} ya tiene el header {header}", "invalid_credential",
                          [{"path": "auth", "message": f"La herramienta {slug} ya tiene el header {header}"}])
    _check_agents_have_secrets(s, row.client_id, tools, parsed.secret_names())
    row.name, row.description = name.strip()[:120], description.strip()[:255]
    row.auth = _dump_auth(parsed)
    row.updated_at = utcnow()
    return row


def delete_credential(s: Session, row: Credential) -> None:
    if tools := credential_users(s, row.client_id).get(row.slug):
        raise Conflict(f"La usan las herramientas: {', '.join(tools)}. Cambiá su autenticación antes.",
                       "credential_in_use")
    s.delete(row)


def describe_credential(row: Credential, users: list[str] | None = None,
                        secrets: set[str] | None = None) -> dict[str, Any]:
    auth = row.auth or {}
    return {"id": row.id, "slug": row.slug, "name": row.name, "description": row.description,
            "type": auth.get("type", ""), "auth": auth, "secret": auth.get("secret", ""),
            "secret_set": secrets is None or auth.get("secret") in secrets, "used_by": users or [],
            "created_at": row.created_at, "updated_at": row.updated_at}


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
    creds = credentials_map(s, client_id)
    out = []
    for g in grants:
        if (row := rows.get(g.tool)) is None:
            continue
        try:
            out.append(spec_of(row, creds))
        except (ValidationError, ValueError):
            logger.warning("tools: definicion invalida de %s (cliente %s)", row.slug, client_id)
    return out


def check_agent_tools(s: Session, client_id: str, agent_id: str | None, normalized: dict) -> None:
    """Al guardar un agente: cada herramienta existe, es del cliente, el plan la incluye y sus secretos estan (en
    el cliente o en el agente)."""
    entries = [(i, g) for i, g in enumerate(normalized.get("tools") or []) if g.get("tool")]
    if not entries:
        return
    client = s.get(Client, client_id)
    lim = limits_service.effective_limits(s, client) if client else None
    rows = {r.slug: r for r in s.scalars(select(ClientTool).where(ClientTool.client_id == client_id))}
    have = set(client_secret_names(s, client_id)) | (set(secret_names(s, agent_id)) if agent_id else set())
    creds = credentials_map(s, client_id)
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
        spec = spec_of(row, creds)
        if (cred := S.credential_of(spec.tool)) is not None:
            errors.append({"path": path, "message": f"La herramienta {row.slug!r} usa la credencial {cred!r}, que no "
                                                    "existe"})
            continue
        missing = S.required_secrets(spec.tool) - have
        if missing:
            errors.append({"path": path, "message": f"Faltan los secretos {', '.join(sorted(missing))}: cargalos en "
                                                    "Secretos (para todos los agentes) o en el agente"})
    if errors:
        raise Invalid("La definicion del agente no es valida", "invalid_definition", errors)


# ---------- prueba ----------

async def test_tool(s_factory, client_id: str, tool_type: str, definition: dict, args: dict, *,
                    slug: str = "prueba", revision: int = 0, agent_id: str | None = None,
                    secrets: dict[str, str] | None = None, call: dict | None = None) -> ToolResult:
    """Ejecuta una definicion (guardada o no) con los secretos del cliente, pisados por los del agente (si viene
    agent_id) y por los del pedido (no se guardan)."""
    tool = parse(tool_type, definition)
    agent_slug = ""
    with s_factory() as s:
        tool = S.resolve(tool, credentials_map(s, client_id))
        values = client_secret_values(s, client_id)
        if agent_id:
            agent = s.get(Agent, agent_id)
            if agent is None or agent.client_id != client_id:
                raise NotFound("Agente inexistente")
            agent_slug = agent.slug
            values = {**values, **_decrypt_all(_agent_secrets(s, agent_id), f"el agente {agent_id}")}
    values = {**values, **(secrets or {})}
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


def describe(row: ClientTool, users: list[dict] | None = None,
             credentials: dict[str, S.Auth] | None = None) -> dict[str, Any]:
    """secrets: los que pide, con la credencial resuelta (credentials)."""
    try:
        tool = S.resolve(S.parse(row.type, row.definition), credentials or {})
        llm = S.openai_tool(row.slug, tool)
        needed = sorted(S.required_secrets(tool))
    except (ValidationError, ValueError):
        llm, needed = None, []
    return {"id": row.id, "slug": row.slug, "type": row.type, "definition": row.definition,
            "revision": row.revision, "secrets": needed, "llm_tool": llm, "used_by": users or [],
            "last_test_at": row.last_test_at, "last_test_ok": row.last_test_ok,
            "last_test_detail": row.last_test_detail, "created_at": row.created_at, "updated_at": row.updated_at}
