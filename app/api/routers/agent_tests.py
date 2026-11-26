"""Casos de prueba de un agente: copias de conversaciones, chequeos y corridas (docs/features/CASOS_DE_PRUEBA.md).

Lectura con cualquier principal del cliente; escritura y corridas, solo Admin del cliente. Todo pasa por
`get_agent` y despues por `agent_id`: un caso o una conversacion de otro cliente o de otro agente da 404.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...agent_tests import cases as case_service
from ...agent_tests import runs as run_service
from ...models import AgentTestRun, ConversationRow
from ...services import agents as agents_service
from ...services.errors import Invalid, NotFound
from ..deps import DB, ClientAdminPrincipal, CurrentPrincipal, Limit, rate_limit
from ..schemas import (
    TestCaseCreateIn,
    TestCaseDetailOut,
    TestCaseOut,
    TestCasePreviewIn,
    TestCasePreviewOut,
    TestCaseRunSummary,
    TestCaseSummaryOut,
    TestCaseUpdateIn,
    TestRunCreateIn,
    TestRunOut,
)
from .agents import get_agent

router = APIRouter(tags=["agent-tests"])

# Un caso son hasta 10 repeticiones por variante: 30 corridas por hora por cliente.
_runs_limit = Depends(rate_limit("agent_test_runs", Limit(30, 3600), per="client",
                                 message="Demasiadas corridas de pruebas. Probá de nuevo en un rato."))

EXTERNAL_ERROR = "Los casos de prueba no aplican a tu propio agente (external)"


def _check_external(agent) -> None:
    if (agent.definition or {}).get("external"):
        raise Invalid(EXTERNAL_ERROR, "external_agent_not_supported")


def _conversation(db, agent, conversation_id: str) -> ConversationRow:
    """La conversacion del agente y su cliente; de otro cliente o de otro agente, 404."""
    row = db.get(ConversationRow, conversation_id)
    if row is None or row.client_id != agent.client_id or row.agent_id != agent.id:
        raise NotFound("Conversación inexistente")
    return row


def _variants_summary(run: AgentTestRun, case_id: str) -> list[dict]:
    result = next((r for r in (run.results or []) if r.get("case_id") == case_id), None)
    return [{"key": v.get("key"), "passed": v.get("passed", 0), "total": v.get("total", 0)}
            for v in (result or {}).get("variants", [])]


def _run_summary(run: AgentTestRun, case_id: str) -> TestCaseRunSummary:
    return TestCaseRunSummary(run_id=run.id, created_at=run.created_at,
                              variants=_variants_summary(run, case_id))


def _out(case, last_run: AgentTestRun | None = None, detail: bool = False):
    last = _run_summary(last_run, case.id) if last_run else None
    if detail:
        return TestCaseOut(id=case.id, client_id=case.client_id, agent_id=case.agent_id, name=case.name,
                           source_conversation_id=case.source_conversation_id,
                           source_message_index=case.source_message_index,
                           source_agent_version=case.source_agent_version, channel=case.channel,
                           known_failure=case.known_failure, checks=case.checks or [],
                           tool_results=case.tool_results or [], snapshot=case.snapshot,
                           created_at=case.created_at, updated_at=case.updated_at, last_run=last)
    return TestCaseSummaryOut(id=case.id, agent_id=case.agent_id, name=case.name, channel=case.channel,
                              known_failure=case.known_failure, created_at=case.created_at,
                              updated_at=case.updated_at, last_run=last)


@router.post("/agents/{agent_id}/test-cases/preview", response_model=TestCasePreviewOut)
def preview_case(agent_id: str, body: TestCasePreviewIn, p: CurrentPrincipal, db: DB):
    """Lo que se guardaria (la copia, sin trazas ni grabaciones), la respuesta original y los chequeos sugeridos."""
    agent = get_agent(db, p, agent_id)
    _check_external(agent)
    row = _conversation(db, agent, body.conversation_id)
    return case_service.preview(row, body.message_index)


@router.post("/agents/{agent_id}/test-cases", response_model=TestCaseDetailOut, status_code=201)
def create_case(agent_id: str, body: TestCaseCreateIn, p: ClientAdminPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    _check_external(agent)
    row = _conversation(db, agent, body.conversation_id)
    data = body.model_dump(exclude={"conversation_id", "message_index"})
    case = case_service.create(db, agent, row, body.message_index, data, p.id if p.kind == "user" else None)
    db.commit()
    detail = case_service.history(db, case.id)
    return TestCaseDetailOut(**_out(case, detail[0] if detail else None, detail=True).model_dump(),
                             history=[_run_summary(run, case.id) for run in detail])


@router.get("/agents/{agent_id}/test-cases", response_model=list[TestCaseSummaryOut])
def list_cases(agent_id: str, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    runs = case_service.last_runs(db, agent.id)
    return [_out(case, runs.get(case.id)) for case in case_service.list_for_agent(db, agent)]


@router.get("/agents/{agent_id}/test-cases/{case_id}", response_model=TestCaseDetailOut)
def read_case(agent_id: str, case_id: str, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    case = case_service.get_for_agent(db, agent, case_id)
    detail = case_service.history(db, case.id)
    return TestCaseDetailOut(**_out(case, detail[0] if detail else None, detail=True).model_dump(),
                             history=[_run_summary(run, case.id) for run in detail])


@router.patch("/agents/{agent_id}/test-cases/{case_id}", response_model=TestCaseDetailOut)
def update_case(agent_id: str, case_id: str, body: TestCaseUpdateIn, p: ClientAdminPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    case = case_service.get_for_agent(db, agent, case_id)
    case_service.update(db, case, body.model_dump(exclude_unset=True))
    db.commit()
    detail = case_service.history(db, case.id)
    return TestCaseDetailOut(**_out(case, detail[0] if detail else None, detail=True).model_dump(),
                             history=[_run_summary(run, case.id) for run in detail])


@router.delete("/agents/{agent_id}/test-cases/{case_id}", status_code=204)
def delete_case(agent_id: str, case_id: str, p: ClientAdminPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    case_service.delete(db, case_service.get_for_agent(db, agent, case_id))
    db.commit()


# ---------- corridas ----------

def _run_out(run: AgentTestRun) -> TestRunOut:
    return TestRunOut(id=run.id, client_id=run.client_id, agent_id=run.agent_id, status=run.status,
                      repetitions=run.repetitions, variants=run.variants or [], cases=run.cases or [],
                      results=run.results, done=run.done, total=run.total, input_tokens=run.input_tokens,
                      output_tokens=run.output_tokens, error=run.error, created_at=run.created_at,
                      started_at=run.started_at, finished_at=run.finished_at)


@router.post("/agents/{agent_id}/test-runs", response_model=TestRunOut, status_code=202,
             dependencies=[_runs_limit])
def create_run(agent_id: str, body: TestRunCreateIn, p: ClientAdminPrincipal, db: DB):
    """Encola una corrida: la version guardada y, con `definition`, los cambios sin guardar. `case_ids` sin mandar:
    todos los del agente; `draft_case`: un caso que no se guarda ("Probar ahora")."""
    agent = get_agent(db, p, agent_id)
    _check_external(agent)
    definition = None
    if body.definition is not None:
        definition = agents_service.normalize_definition(body.definition, agent.slug, agent.version + 1)
    draft = None
    if body.draft_case is not None:
        row = _conversation(db, agent, body.draft_case.conversation_id)
        data = body.draft_case.model_dump(exclude={"conversation_id", "message_index"})
        draft = case_service.draft(row, body.draft_case.message_index, data)
    run = run_service.create(db, agent, body.repetitions, definition, body.case_ids, draft,
                             p.id if p.kind == "user" else None)
    db.commit()
    return _run_out(run)


@router.get("/agents/{agent_id}/test-runs", response_model=list[TestRunOut])
def list_runs(agent_id: str, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    runs = db.scalars(select(AgentTestRun).where(AgentTestRun.agent_id == agent.id)
                      .order_by(AgentTestRun.created_at.desc())).all()
    return [_run_out(run) for run in runs]


@router.get("/agents/{agent_id}/test-runs/{run_id}", response_model=TestRunOut)
def read_run(agent_id: str, run_id: str, p: CurrentPrincipal, db: DB):
    agent = get_agent(db, p, agent_id)
    run = db.get(AgentTestRun, run_id)
    if run is None or run.agent_id != agent.id:
        raise NotFound("Corrida inexistente")
    return _run_out(run)
