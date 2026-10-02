"""Alta, versionado y archivo de agentes."""
import re
import unicodedata

from pydantic import ValidationError
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from ..agents.templates import blank_definition, template_data
from ..conversation.models import Workflow
from ..db import utcnow
from ..models import Agent, AgentVersion, Client, ConversationRow, WaAccount
from . import voices
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


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")[:64] or "agente"


def create_agent(s: Session, client: Client, name: str, slug: str | None, description: str,
                 definition: dict | None, template_id: str | None, user_id: str | None,
                 engine: str | None = None) -> Agent:
    """definition, o template_id (la plantilla de la UI), o ninguno: en blanco. engine pisa
    el de la definicion (es la misma con los dos motores)."""
    if definition is not None and template_id is not None:
        raise Invalid("Pasar definition o template_id, no los dos")
    if template_id is not None:
        try:
            definition = template_data(template_id)
        except KeyError:
            raise NotFound(f"Plantilla inexistente: {template_id}") from None
    elif definition is None:
        definition = blank_definition(client.name)
    if engine is not None:
        definition = {**definition, "engine": engine}
    slug = slug or slugify(name)
    if not SLUG_RE.fullmatch(slug):
        raise Invalid("slug: minusculas, numeros y _ (hasta 64)")
    if s.scalar(select(exists().where(Agent.client_id == client.id, Agent.slug == slug))):
        raise Conflict(f"El cliente ya tiene un agente {slug!r}")
    normalized = normalize_definition(definition, slug, 1)
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
    s.delete(agent)
