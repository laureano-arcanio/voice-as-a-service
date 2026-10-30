"""Alta, versionado y archivo de agentes."""
import re
import unicodedata

from pydantic import ValidationError
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from ..agents.templates import blank_definition, fill_template, template_data
from ..conversation.models import Workflow
from ..db import utcnow
from ..models import (
    Agent,
    AgentVersion,
    Client,
    ConversationRow,
    LlmConnection,
    WaAccount,
    WaRoute,
)
from . import handoff, voices
from . import limits as limits_service
from . import tools as tools_service
from .errors import Conflict, Invalid, NotFound

SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_]{0,63}")
# Los errores de Workflow._consistent traen la ruta al principio del mensaje: "fields.x: ...".
MESSAGE_PATH_RE = re.compile(r"(?:Value error, )?([a-z_]+(?:\.[^:\n]+?)*): (.+)", re.S)


def validation_errors(e: ValidationError) -> list[dict]:
    """Errores de pydantic en un formato simple para el editor: ruta y mensaje."""
    out = []
    for err in e.errors():
        path, message = ".".join(str(p) for p in err["loc"]), err["msg"]
        if not path and (m := MESSAGE_PATH_RE.fullmatch(message)):
            path, message = m.groups()
        out.append({"path": path, "message": message})
    return out


def normalize_definition(raw: dict, slug: str, version: int) -> dict:
    """Valida la definicion y fija id (slug) y version. Invalid con los errores si no es valida."""
    data = {**raw, "id": slug, "version": version}
    try:
        workflow = Workflow.model_validate(data)
    except ValidationError as e:
        raise Invalid("La definicion del agente no es valida", "invalid_definition", validation_errors(e)) from None
    catalog = voices.catalog()
    if workflow.agent.voice and catalog and workflow.agent.voice not in catalog:
        raise Invalid("La definicion del agente no es valida", "invalid_definition",
                      [{"path": "agent.voice", "message": f"La voz {workflow.agent.voice!r} no esta en el catalogo del TTS"}])
    return workflow.model_dump(mode="json", exclude_none=True)


def _check_tools(s: Session, client_id: str, normalized: dict, agent_id: str | None = None) -> None:
    """Las herramientas del cliente existen, el plan las incluye y el agente tiene sus secretos (services/tools.py)."""
    tools_service.check_agent_tools(s, client_id, agent_id, normalized)


def _check_llm(s: Session, client_id: str, normalized: dict) -> None:
    """workflow.llm: cada conexion es del cliente del agente y esta vigente (la de otro cliente no sirve)."""
    errors = []
    for i, stage in enumerate((normalized.get("llm") or {}).get("stages") or []):
        if not (connection_id := stage.get("connection")):
            continue
        row = s.get(LlmConnection, connection_id)
        if row is None or row.client_id != client_id or row.revoked_at is not None:
            errors.append({"path": f"llm.stages.{i}.connection",
                           "message": "La conexion no existe, esta dada de baja o es de otro cliente"})
    if errors:
        raise Invalid("La definicion del agente no es valida", "invalid_definition", errors)


def _check_external(s: Session, client_id: str, normalized: dict) -> None:
    """Motor external: el plan lo incluye y la conexion es del cliente, vigente y compatible con OpenAI."""
    if not (external := normalized.get("external")):
        return
    limits_service.check_external_agent(s, client_id)
    row = s.get(LlmConnection, external.get("connection"))
    if row is None or row.client_id != client_id or row.revoked_at is not None:
        message = "La conexion no existe, esta dada de baja o es de otro cliente"
    elif row.kind != "openai_compatible":
        message = "El agente externo necesita una conexion compatible con OpenAI (la URL de tu endpoint)"
    else:
        return
    raise Invalid("La definicion del agente no es valida", "invalid_definition",
                  [{"path": "external.connection", "message": message}])


def _check_handoff(s: Session, client_id: str, normalized: dict) -> None:
    """workflow.handoff: las areas son del cliente del agente y el tema de espera existe."""
    if errors := handoff.check_agent_handoff(s, client_id, normalized.get("handoff")):
        raise Invalid("La definicion del agente no es valida", "invalid_definition", errors)


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")[:64] or "agente"


def create_agent(s: Session, client: Client, name: str, slug: str | None, description: str,
                 definition: dict | None, template_id: str | None, user_id: str | None,
                 voice: str | None = None) -> Agent:
    """definition, o template_id (la plantilla de la UI, con la empresa del cliente y la voz `voice` o la de la
    plantilla), o ninguno: en blanco."""
    if definition is not None and template_id is not None:
        raise Invalid("Pasar definition o template_id, no los dos")
    if voice is not None and (template_id is None or voice not in voices.catalog()):
        raise Invalid("voice va con template_id y tiene que ser una voz del catálogo (GET /voices)", "invalid_voice")
    if template_id is not None:
        try:
            definition = fill_template(template_data(template_id), client.name, voice)
        except KeyError:
            raise NotFound(f"Plantilla inexistente: {template_id}") from None
    elif definition is None:
        definition = blank_definition(client.name)
    slug = slug or slugify(name)
    if not SLUG_RE.fullmatch(slug):
        raise Invalid("slug: minusculas, numeros y _ (hasta 64)")
    if s.scalar(select(exists().where(Agent.client_id == client.id, Agent.slug == slug))):
        raise Conflict(f"El cliente ya tiene un agente {slug!r}")
    normalized = normalize_definition(definition, slug, 1)
    _check_tools(s, client.id, normalized)
    _check_llm(s, client.id, normalized)
    _check_external(s, client.id, normalized)
    _check_handoff(s, client.id, normalized)
    agent = Agent(client_id=client.id, name=name, slug=slug, description=description,
                  version=1, definition=normalized)
    s.add(agent)
    s.flush()
    s.add(AgentVersion(agent_id=agent.id, version=1, definition=normalized, created_by=user_id))
    return agent


def update_definition(s: Session, agent: Agent, definition: dict, user_id: str | None) -> Agent:
    """Version nueva si cambio algo; si es igual a la vigente, no hace nada."""
    # Lock del agente: dos ediciones a la vez no pueden crear la misma version.
    s.refresh(agent, with_for_update=True)
    current = {k: v for k, v in agent.definition.items() if k != "version"}
    normalized = normalize_definition(definition, agent.slug, agent.version + 1)
    _check_tools(s, agent.client_id, normalized, agent.id)
    _check_llm(s, agent.client_id, normalized)
    _check_external(s, agent.client_id, normalized)
    _check_handoff(s, agent.client_id, normalized)
    if {k: v for k, v in normalized.items() if k != "version"} == current:
        return agent
    agent.version += 1
    agent.definition = normalized
    s.add(AgentVersion(agent_id=agent.id, version=agent.version, definition=normalized, created_by=user_id))
    return agent


def set_archived(agent: Agent, archived: bool) -> None:
    agent.archived_at = (agent.archived_at or utcnow()) if archived else None


def delete_agent(s: Session, agent: Agent) -> None:
    """Solo sin conversaciones; si tiene historial, se archiva."""
    if s.scalar(select(func.count()).select_from(ConversationRow).where(ConversationRow.agent_id == agent.id)):
        raise Conflict("El agente tiene conversaciones: archivalo en vez de borrarlo", "agent_in_use")
    # wa_accounts.agent_id es RESTRICT: sin esto, IntegrityError (500) en PostgreSQL.
    if s.scalar(select(func.count()).select_from(WaAccount).where(WaAccount.agent_id == agent.id)):
        raise Conflict("El agente atiende un número de WhatsApp: conectá el número a otro agente", "agent_in_use")
    # Igual con wa_routes.agent_id (reglas de ruteo por contacto).
    if s.scalar(select(func.count()).select_from(WaRoute).where(WaRoute.agent_id == agent.id)):
        raise Conflict("El agente atiende contactos de un número de WhatsApp: quitá la regla de ruteo",
                       "agent_in_use")
    s.delete(agent)
