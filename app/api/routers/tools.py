"""Herramientas del cliente (llamadas a APIs y codigo), sus secretos (del cliente y de cada agente) y sus
credenciales (docs/TOOLS_PLAN.md). Las gestiona el cliente (desde el panel, con una API key `calls` o por el MCP)
o un admin. Los secretos se guardan cifrados y nunca se devuelven."""
from contextlib import nullcontext

from fastapi import APIRouter, Depends

from ...config import settings
from ...services import tools as svc
from ...tools import schema as tool_schema
from ..deps import DB, CurrentPrincipal, Limit, rate_limit
from ..schemas import (
    AgentSecretIn,
    AgentSecretOut,
    AgentSecretPatch,
    ClientSecretOut,
    CredentialIn,
    CredentialOut,
    CredentialUpdate,
    SecretPromoteOut,
    ToolDraftTestIn,
    ToolIn,
    ToolOut,
    ToolTemplateOut,
    ToolTestIn,
    ToolTestOut,
    ToolUpdate,
    ToolVersionOut,
)
from .agents import get_agent
from .clients import get_client

router = APIRouter(tags=["tools"])
_test_limit = Depends(rate_limit("tool_tests", Limit(30, 60), per="client",
                                 message="Demasiadas pruebas de herramientas. Probá en un minuto."))


def _out(db, row, used: dict[str, list[dict]]) -> ToolOut:
    return ToolOut(**svc.describe(row, used.get(row.slug, []), svc.credentials_map(db, row.client_id)))


def _test_out(result) -> ToolTestOut:
    return ToolTestOut(ok=result.ok, status=result.status, ms=result.ms, data=result.data, error=result.error,
                       llm=result.llm, request=result.request, logs=result.logs, assigned=result.assigned)


@router.get("/tools/schema", response_model=dict)
def tools_schema(_: CurrentPrincipal):
    """JSON Schema de `definition` por tipo (http y code), para validar o armar una herramienta."""
    return {"http": tool_schema.HttpTool.model_json_schema(by_alias=True),
            "code": tool_schema.CodeTool.model_json_schema(by_alias=True)}


@router.get("/tools/code-template", response_model=ToolTemplateOut)
def code_template(_: CurrentPrincipal):
    """La funcion de ejemplo con la que arranca una herramienta de codigo."""
    return ToolTemplateOut(code=svc.CODE_TEMPLATE, parameters=svc.CODE_TEMPLATE_PARAMETERS)


@router.get("/clients/{client_id}/tools", response_model=list[ToolOut])
def list_tools(client_id: str, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    used = svc.used_by(db, client.id)
    return [_out(db, row, used) for row in svc.list_tools(db, client.id)]


@router.post("/clients/{client_id}/tools", response_model=ToolOut, status_code=201)
def create_tool(client_id: str, body: ToolIn, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    row = svc.create_tool(db, client.id, body.slug, body.type, body.definition,
                          p.id if p.kind == "user" else None)
    db.commit()
    return _out(db, row, {})


@router.get("/clients/{client_id}/tools/{slug}", response_model=ToolOut)
def get_tool(client_id: str, slug: str, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    return _out(db, svc.get_tool(db, client.id, slug), svc.used_by(db, client.id))


@router.put("/clients/{client_id}/tools/{slug}", response_model=ToolOut)
def update_tool(client_id: str, slug: str, body: ToolUpdate, p: CurrentPrincipal, db: DB):
    """Reemplaza la definicion; si cambio, sube `revision`. Rige desde ya para todos los agentes que la usan."""
    client = get_client(db, p, client_id)
    row = svc.update_tool(db, svc.get_tool(db, client.id, slug), body.type, body.definition,
                          p.id if p.kind == "user" else None)
    db.commit()
    return _out(db, row, svc.used_by(db, client.id))


@router.get("/clients/{client_id}/tools/{slug}/versions", response_model=list[ToolVersionOut])
def tool_versions(client_id: str, slug: str, p: CurrentPrincipal, db: DB):
    """Cada revision con su definicion, la mas nueva primero (la traza de una llamada dice con cual corrio)."""
    client = get_client(db, p, client_id)
    return svc.versions(db, svc.get_tool(db, client.id, slug))


@router.delete("/clients/{client_id}/tools/{slug}", status_code=204)
def delete_tool(client_id: str, slug: str, p: CurrentPrincipal, db: DB):
    """409 (tool_in_use) si un agente vigente la usa."""
    client = get_client(db, p, client_id)
    svc.delete_tool(db, svc.get_tool(db, client.id, slug))
    db.commit()


@router.post("/clients/{client_id}/tools/{slug}/test", response_model=ToolTestOut, dependencies=[_test_limit])
async def test_tool(client_id: str, slug: str, body: ToolTestIn, p: CurrentPrincipal, db: DB):
    """La ejecuta de verdad (llama a la API o corre el codigo) con los secretos del cliente, pisados por los del
    agente (agent_id) y los del pedido. No pide confirmacion. Deja el resultado en la ficha."""
    client = get_client(db, p, client_id)
    row = svc.get_tool(db, client.id, slug)
    result = await svc.test_tool(lambda: nullcontext(db), client.id, row.type, row.definition, body.args,
                                 slug=row.slug, revision=row.revision, agent_id=body.agent_id,
                                 secrets=body.secrets, call=body.call)
    svc.record_test(db, row, result)
    db.commit()
    return _test_out(result)


@router.post("/clients/{client_id}/tools/test", response_model=ToolTestOut, dependencies=[_test_limit])
async def test_draft(client_id: str, body: ToolDraftTestIn, p: CurrentPrincipal, db: DB):
    """Lo mismo con una definicion sin guardar (el boton Probar del editor)."""
    client = get_client(db, p, client_id)
    svc.check_plan(db, client.id, body.type)
    result = await svc.test_tool(lambda: nullcontext(db), client.id, body.type, body.definition, body.args,
                                 agent_id=body.agent_id, secrets=body.secrets, call=body.call)
    return _test_out(result)


# ---------- secretos del cliente ----------

def _client_secret(db, client_id: str, name: str) -> ClientSecretOut:
    return next(ClientSecretOut(**x) for x in svc.list_client_secrets(db, client_id) if x["name"] == name)


@router.get("/clients/{client_id}/secrets", response_model=list[ClientSecretOut])
def list_client_secrets(client_id: str, p: CurrentPrincipal, db: DB):
    """Sin valores, para todos los agentes del cliente. Con quien los usa y los que faltan (missing: true)."""
    client = get_client(db, p, client_id)
    return svc.list_client_secrets(db, client.id)


@router.post("/clients/{client_id}/secrets", response_model=ClientSecretOut, status_code=201)
def create_client_secret(client_id: str, body: AgentSecretIn, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    svc.check_plan(db, client.id, "http")
    svc.create_client_secret(db, client.id, body.name, body.value, body.description,
                             p.id if p.kind == "user" else None)
    db.commit()
    return _client_secret(db, client.id, body.name)


@router.patch("/clients/{client_id}/secrets/{name}", response_model=ClientSecretOut)
def update_client_secret(client_id: str, name: str, body: AgentSecretPatch, p: CurrentPrincipal, db: DB):
    """Reemplaza el valor o la descripcion. Rige en todos los agentes que no tienen su propio valor."""
    client = get_client(db, p, client_id)
    svc.update_secret(db, svc.get_client_secret(db, client.id, name), body.value, body.description)
    db.commit()
    return _client_secret(db, client.id, name)


@router.delete("/clients/{client_id}/secrets/{name}", status_code=204)
def delete_client_secret(client_id: str, name: str, p: CurrentPrincipal, db: DB):
    """409 (secret_in_use) si lo usa una credencial o una herramienta de un agente sin su propio valor."""
    client = get_client(db, p, client_id)
    svc.delete_client_secret(db, client.id, svc.get_client_secret(db, client.id, name))
    db.commit()


# ---------- credenciales ----------

def _credential(db, row) -> CredentialOut:
    users = svc.credential_users(db, row.client_id).get(row.slug, [])
    return CredentialOut(**svc.describe_credential(row, users, set(svc.client_secret_names(db, row.client_id))))


@router.get("/clients/{client_id}/credentials", response_model=list[CredentialOut])
def list_credentials(client_id: str, p: CurrentPrincipal, db: DB):
    """La autenticacion de las APIs del cliente, sin valores, con las herramientas que la usan."""
    client = get_client(db, p, client_id)
    users = svc.credential_users(db, client.id)
    secrets = set(svc.client_secret_names(db, client.id))
    return [svc.describe_credential(row, users.get(row.slug, []), secrets) for row in svc.list_credentials(db, client.id)]


@router.post("/clients/{client_id}/credentials", response_model=CredentialOut, status_code=201)
def create_credential(client_id: str, body: CredentialIn, p: CurrentPrincipal, db: DB):
    """Con `value`, el valor se guarda en el secreto del cliente `auth.secret`."""
    client = get_client(db, p, client_id)
    row = svc.create_credential(db, client.id, body.slug, body.name, body.description, body.auth, body.value,
                                p.id if p.kind == "user" else None)
    db.commit()
    return _credential(db, row)


@router.get("/clients/{client_id}/credentials/{slug}", response_model=CredentialOut)
def get_credential(client_id: str, slug: str, p: CurrentPrincipal, db: DB):
    client = get_client(db, p, client_id)
    return _credential(db, svc.get_credential(db, client.id, slug))


@router.put("/clients/{client_id}/credentials/{slug}", response_model=CredentialOut)
def update_credential(client_id: str, slug: str, body: CredentialUpdate, p: CurrentPrincipal, db: DB):
    """Rige desde ya en todas las herramientas que la usan."""
    client = get_client(db, p, client_id)
    row = svc.update_credential(db, svc.get_credential(db, client.id, slug), body.name, body.description,
                                body.auth, body.value, p.id if p.kind == "user" else None)
    db.commit()
    return _credential(db, row)


@router.delete("/clients/{client_id}/credentials/{slug}", status_code=204)
def delete_credential(client_id: str, slug: str, p: CurrentPrincipal, db: DB):
    """409 (credential_in_use) si una herramienta la usa. El secreto con el valor queda."""
    client = get_client(db, p, client_id)
    svc.delete_credential(db, svc.get_credential(db, client.id, slug))
    db.commit()


# ---------- secretos de un agente ----------

@router.get("/agents/{agent_id}/secrets", response_model=list[AgentSecretOut])
def list_secrets(agent_id: str, p: CurrentPrincipal, db: DB):
    """Sin valores. Los propios del agente (pisan a los del cliente), los del cliente que usan sus herramientas
    (source: client) y los que faltan (missing: true)."""
    return svc.list_secrets(db, get_agent(db, p, agent_id))


@router.post("/agents/{agent_id}/secrets", response_model=AgentSecretOut, status_code=201)
def create_secret(agent_id: str, body: AgentSecretIn, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    svc.create_secret(db, agent, body.name, body.value, body.description, p.id if p.kind == "user" else None)
    db.commit()
    return next(x for x in svc.list_secrets(db, agent) if x["name"] == body.name)


@router.patch("/agents/{agent_id}/secrets/{name}", response_model=AgentSecretOut)
def update_secret(agent_id: str, name: str, body: AgentSecretPatch, p: CurrentPrincipal, db: DB):
    """Reemplaza el valor o la descripcion. No crea version del agente."""
    agent = get_agent(db, p, agent_id)
    svc.update_secret(db, svc.get_secret(db, agent, name), body.value, body.description)
    db.commit()
    return next(x for x in svc.list_secrets(db, agent) if x["name"] == name)


@router.post("/agents/{agent_id}/secrets/{name}/promote", response_model=SecretPromoteOut)
def promote_secret(agent_id: str, name: str, p: CurrentPrincipal, db: DB):
    """Pasa el secreto al cliente (para todos los agentes) y borra el propio de este agente y de los otros que
    tienen el mismo valor. 409 (secret_name_taken) si el cliente ya tiene uno con otro valor."""
    agent = get_agent(db, p, agent_id)
    moved = svc.promote_secret(db, agent, svc.get_secret(db, agent, name), p.id if p.kind == "user" else None)
    db.commit()
    return SecretPromoteOut(moved=moved)


@router.delete("/agents/{agent_id}/secrets/{name}", status_code=204)
def delete_secret(agent_id: str, name: str, p: CurrentPrincipal, db: DB):
    """Sin el propio, el agente usa el del cliente. 409 (secret_in_use) si una herramienta del agente lo usa y el
    cliente no lo tiene."""
    agent = get_agent(db, p, agent_id)
    svc.delete_secret(db, agent, svc.get_secret(db, agent, name))
    db.commit()


# El sandbox de codigo esta configurado (TOOLS_RUNNER_URL): para que la UI avise si no.
@router.get("/tools/status", response_model=dict)
def tools_status(_: CurrentPrincipal):
    return {"code_runner": bool(settings.tools_runner_url)}
