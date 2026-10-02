from fastapi import APIRouter
from sqlalchemy import select

from ...agents.templates import template_data, template_ids
from ...conversation.models import Workflow
from ...llm.prompt import build_classic_system, render_workflow, system_prompt
from ...models import Agent, AgentVersion, User
from ...services import agents as service
from ...services.errors import Invalid, NotFound
from ..deps import DB, AdminPrincipal, CurrentPrincipal, scoped_client_id
from ..schemas import (
    AgentCreate,
    AgentDetail,
    AgentOut,
    AgentUpdate,
    AgentVersionOut,
    DefinitionIn,
    PromptIn,
    PromptOut,
    TemplateOut,
    ValidationOut,
)
from .clients import get_client

router = APIRouter(tags=["agents"])


def _out(agent: Agent, detail: bool = False) -> AgentOut:
    d = agent.definition
    data = {"id": agent.id, "client_id": agent.client_id, "name": agent.name, "slug": agent.slug,
            "description": agent.description, "version": agent.version, "archived": agent.archived_at is not None,
            "engine": d.get("engine", "structured"), "voice": (d.get("agent") or {}).get("voice"),
            "created_at": agent.created_at, "updated_at": agent.updated_at}
    return AgentDetail(**data, definition=d) if detail else AgentOut(**data)


def get_agent(db, p, agent_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or not p.can_access(agent.client_id):
        raise NotFound("Agente inexistente")
    return agent


@router.get("/agents/schema", response_model=dict)
def definition_schema(_: CurrentPrincipal):
    """JSON Schema de la definicion de un agente (para el editor de la UI)."""
    return Workflow.model_json_schema()


@router.post("/agents/validate", response_model=ValidationOut)
def validate_definition(body: DefinitionIn, _: CurrentPrincipal):
    """Valida una definicion sin guardarla. id y version los pone la app."""
    try:
        service.normalize_definition(body.definition, body.definition.get("id") or "borrador", 1)
    except Invalid as e:
        return ValidationOut(valid=False, errors=e.details or [{"path": "", "message": e.message}])
    return ValidationOut(valid=True)


@router.post("/agents/prompt", response_model=PromptOut)
def preview_prompt(body: PromptIn, _: AdminPrincipal):
    """El prompt que arma el motor con esta definicion (sin guardarla): el system prompt sale
    siempre de la definicion. classic: todo el agente en el prompt de sistema; structured: un
    prompt de sistema fijo y la definicion en cada turno."""
    w = Workflow.model_validate(service.normalize_definition(body.definition, body.definition.get("id") or "borrador", 1))
    if w.engine == "classic":
        return PromptOut(engine=w.engine, system=build_classic_system(w, body.channel))
    return PromptOut(engine=w.engine, system=system_prompt(body.channel), workflow=render_workflow(w))


@router.get("/agent-templates", response_model=list[TemplateOut])
def list_templates(_: CurrentPrincipal):
    out = []
    for tid in template_ids():
        w = Workflow.model_validate(template_data(tid))
        out.append(TemplateOut(id=tid, engine=w.engine, agent=f"{w.agent.name}, {w.agent.role}", voice=w.agent.voice,
                               objective=w.objective.description.strip()))
    return out


@router.get("/agent-templates/{template_id}", response_model=dict)
def get_template(template_id: str, _: CurrentPrincipal):
    try:
        return template_data(template_id)
    except KeyError:
        raise NotFound("Plantilla inexistente") from None


@router.get("/agents", response_model=list[AgentOut])
def list_agents(p: CurrentPrincipal, db: DB, client_id: str | None = None, include_archived: bool = False):
    q = select(Agent).order_by(Agent.name)
    if cid := scoped_client_id(p, client_id):
        q = q.where(Agent.client_id == cid)
    if not include_archived:
        q = q.where(Agent.archived_at.is_(None))
    return [_out(a) for a in db.scalars(q)]


@router.post("/agents", response_model=AgentDetail, status_code=201)
def create_agent(body: AgentCreate, p: AdminPrincipal, db: DB):
    client = get_client(db, p, body.client_id)
    agent = service.create_agent(db, client, body.name, body.slug, body.description, body.definition,
                                 body.template_id, p.id if p.kind == "user" else None, body.engine)
    db.commit()
    return _out(agent, detail=True)


@router.get("/agents/{agent_id}", response_model=AgentDetail)
def read_agent(agent_id: str, p: CurrentPrincipal, db: DB):
    return _out(get_agent(db, p, agent_id), detail=True)


@router.patch("/agents/{agent_id}", response_model=AgentDetail)
def update_agent(agent_id: str, body: AgentUpdate, p: AdminPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if "archived" in data:
        service.set_archived(agent, data.pop("archived"))
    for k, v in data.items():
        setattr(agent, k, v)
    db.commit()
    return _out(agent, detail=True)


@router.put("/agents/{agent_id}/definition", response_model=AgentDetail)
def update_definition(agent_id: str, body: DefinitionIn, p: AdminPrincipal, db: DB):
    """Guarda la definicion como version nueva (si cambio). Las llamadas en curso
    siguen con la version con que empezaron."""
    agent = service.update_definition(db, get_agent(db, p, agent_id), body.definition,
                                      p.id if p.kind == "user" else None)
    db.commit()
    return _out(agent, detail=True)


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str, p: AdminPrincipal, db: DB):
    service.delete_agent(db, get_agent(db, p, agent_id))
    db.commit()


@router.get("/agents/{agent_id}/versions", response_model=list[AgentVersionOut])
def list_versions(agent_id: str, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    rows = db.execute(select(AgentVersion, User.email).outerjoin(User, User.id == AgentVersion.created_by)
                      .where(AgentVersion.agent_id == agent.id).order_by(AgentVersion.version.desc()))
    return [AgentVersionOut(version=v.version, created_at=v.created_at, created_by=v.created_by,
                            created_by_email=email) for v, email in rows]


@router.get("/agents/{agent_id}/versions/{version}", response_model=AgentVersionOut)
def read_version(agent_id: str, version: int, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    v = db.get(AgentVersion, (agent.id, version))
    if v is None:
        raise NotFound("Versión inexistente")
    author = db.get(User, v.created_by) if v.created_by else None
    return AgentVersionOut.model_validate(v).model_copy(update={"created_by_email": author.email if author else None})
