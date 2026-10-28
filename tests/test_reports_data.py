"""Datos de los reportes (docs/features/REPORTES.md): resultado, objetivo y conversion de cada conversacion,
tokens del LLM por turno, tool_runs, historial de las cuentas de WhatsApp y el backfill. LLM falso."""
import datetime
from types import SimpleNamespace

from sqlalchemy import select

from app.agents.templates import ReferenceDefinitions
from app.cli import reports_backfill
from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn, ConversationState, Extraction, Progress
from app.conversation.workflow import conversion, outcome_goal
from app.llm import anthropic_client
from app.models import ConversationRow, ToolRun, WaAccount, WaAccountStatusLog

from .helpers import BASE, FakeLLM, start_with, turn_and_extract
from .test_classic_tools import Script, llm_with, setup
from .test_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_service import make_wa, send
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)


def state_of(status="active", outcome=None, preloaded=(), **fields) -> ConversationState:
    return ConversationState(conversation_id="c", agent_id="sales_discovery", status=status, fields=fields,
                             progress=Progress(outcome=outcome, preloaded=list(preloaded)))


def test_conversion(workflow):
    assert conversion(workflow, state_of()) == "empty"
    # Los precargados (el telefono de la llamada) no son datos capturados.
    assert conversion(workflow, state_of(preloaded=["contact_name"], contact_name="Juan")) == "empty"
    assert conversion(workflow, state_of(contact_name="Juan", company_name="")) == "partial"
    full = {**BASE, "wants_demo": False}
    assert conversion(workflow, state_of("completed", "no_demo", **full)) == "complete"
    # Activa, o terminada incompleta o fuera de tema: no es completa aunque tenga todos los datos.
    assert conversion(workflow, state_of("active", None, **full)) == "partial"
    assert conversion(workflow, state_of("completed", "incompleta", **full)) == "partial"
    assert conversion(workflow, state_of("completed", "fuera_de_tema")) == "empty"
    # Con un resultado que no es el de los datos pero faltan obligatorios: parcial.
    assert conversion(workflow, state_of("completed", "no_demo", contact_name="Juan")) == "partial"
    assert outcome_goal(workflow, "demo") is True and outcome_goal(workflow, "no_demo") is False
    assert outcome_goal(workflow, "incompleta") is False and outcome_goal(workflow, None) is None


def row(store, cid) -> ConversationRow:
    with store.sessions() as s:
        return s.get(ConversationRow, cid)


async def test_engine_saves_outcome_conversion_and_tokens(store):
    llm = FakeLLM(AgentTurn(assistant_message="Listo.", status="completed", input_tokens=120, output_tokens=8),
                  extractions=[{"wants_demo": True, "email": "juan@acme.com"}])
    original = llm.extract

    async def extract(workflow, state):
        result = await original(workflow, state)
        return Extraction(fields=result.fields, raw=result.raw, input_tokens=300, output_tokens=20)
    llm.extract = extract
    engine = ConversationEngine(llm, store)
    cid = start_with(engine, **BASE)
    r = row(store, cid)
    assert (r.conversion, r.outcome, r.goal, r.llm_input_tokens) == ("partial", None, None, 0)
    state, _ = await turn_and_extract(engine, cid, "Sí, a juan arroba acme punto com.")
    r = row(store, cid)
    assert (r.outcome, r.goal, r.conversion) == ("demo", True, "complete")
    assert (r.llm_input_tokens, r.llm_output_tokens) == (420, 28)
    trace = state.messages[-1].llm
    assert [(t["kind"], t["input_tokens"], t["output_tokens"]) for t in trace] == [("turno", 120, 8),
                                                                                  ("extraccion", 300, 20)]


async def test_incomplete_and_empty_conversation(store):
    engine = ConversationEngine(FakeLLM(AgentTurn(assistant_message="Chau.", status="completed"),
                                        extractions=[{}]), store)
    cid = start_with(engine)
    await turn_and_extract(engine, cid, "Número equivocado.")
    r = row(store, cid)
    # Sin datos el resultado es el default (no_demo) y no cumple el objetivo; sin usage del proveedor, 0 tokens.
    assert (r.outcome, r.goal, r.conversion, r.llm_input_tokens) == ("no_demo", False, "empty", 0)


async def test_openai_stream_usage(store):
    """El usage llega en el ultimo chunk (stream_options.include_usage), sin choices."""
    script = Script(("Hola, ¿en qué te ayudo?", []))
    original = script.create

    async def create(**request):
        stream = await original(**request)

        async def with_usage():
            async for c in stream:
                yield c
            yield SimpleNamespace(choices=[], usage=SimpleNamespace(prompt_tokens=50, completion_tokens=7))
        return with_usage()
    script.create = create
    engine = ConversationEngine(llm_with(script), store)
    cid = start_with(engine)
    _, turn = await engine.process_turn(cid, "Hola", on_message=lambda _: None)
    assert script.requests[0]["stream_options"] == {"include_usage": True}
    assert (turn.input_tokens, turn.output_tokens) == (50, 7)
    assert row(store, cid).llm_input_tokens == 50


def test_anthropic_usage_counts_the_cache():
    message = SimpleNamespace(usage=SimpleNamespace(input_tokens=10, cache_creation_input_tokens=5,
                                                    cache_read_input_tokens=100, output_tokens=9))
    assert anthropic_client.usage_of(message) == (115, 9)
    assert anthropic_client.usage_of(SimpleNamespace()) == (0, 0)


async def test_tool_runs_are_recorded(api, admin, mock_api_url):
    script = Script(("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-05"}),
                          ("consultar_turnos", {"sucursal": "oeste", "fecha": "2026-11-05"})]),
                    ("Tengo libre a las 10.", []))
    engine, cid = setup(api, admin, mock_api_url, script)
    await engine.process_turn(cid, "¿Tienen turno el 5 de noviembre?", on_message=lambda _: None)
    with api.sessions() as s:
        runs = list(s.scalars(select(ToolRun).order_by(ToolRun.ok.desc())))
        conv = s.get(ConversationRow, cid)
    assert [(r.slug, r.type, r.ok) for r in runs] == [("consultar_turnos", "http", True),
                                                      ("consultar_turnos", "http", False)]
    ok, failed = runs
    assert ok.tool_id and ok.conversation_id == cid and ok.agent_id == conv.agent_id
    assert ok.client_id == conv.client_id and ok.status_code == 200 and ok.error == "" and ok.ms >= 0
    assert failed.error and len(failed.error) <= 255


async def test_tool_run_failure_does_not_break_the_turn(api, admin, mock_api_url, caplog, monkeypatch):
    script = Script(("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-05"})]),
                    ("Tengo libre a las 10.", []))
    engine, cid = setup(api, admin, mock_api_url, script)

    def broken(**_):
        raise RuntimeError("base caida")
    monkeypatch.setattr("app.models.ToolRun", broken)
    _, turn = await engine.process_turn(cid, "¿Turno el 5?", on_message=lambda _: None)
    assert turn.assistant_message == "Tengo libre a las 10."
    assert "no se pudo registrar" in caplog.text


def status_log(sessions, account_id) -> list[tuple]:
    with sessions() as s:
        return [(r.status, r.quality_rating, r.messaging_limit) for r in s.scalars(
            select(WaAccountStatusLog).where(WaAccountStatusLog.account_id == account_id)
            .order_by(WaAccountStatusLog.at, WaAccountStatusLog.id))]


async def test_wa_account_status_log(sessions):
    w = make_wa(sessions)
    assert status_log(sessions, w.account_id) == [("connected", None, None)]
    with sessions() as s:
        waba = s.get(WaAccount, w.account_id).waba_id

    def event(field, value):
        return {"object": "whatsapp_business_account",
                "entry": [{"id": waba, "time": 1, "changes": [{"field": field, "value": value}]}]}
    quality = event("phone_number_quality_update", {"display_phone_number": "15550000000", "event": "UPGRADE",
                                                    "current_limit": "TIER_10K"})
    await send(w, quality)
    await send(w, quality)      # sin cambio: sin fila nueva
    await send(w, event("account_update", {"event": "PARTNER_REMOVED", "waba_info": {"waba_id": waba}}))
    with sessions() as s:       # otro campo de la cuenta no deja historial
        s.get(WaAccount, w.account_id).name = "Otro"
        s.commit()
    log = status_log(sessions, w.account_id)
    assert log[1:] == [("connected", None, "TIER_10K"), ("disconnected", None, "TIER_10K")]


def test_reports_backfill(sessions):
    old = datetime.datetime(2026, 9, 1, 12, 0)
    full = {**BASE, "wants_demo": True, "email": "juan@acme.com"}
    with sessions() as s:
        s.add_all([
            # Anterior a progress.outcome: el resultado se calcula con los datos.
            ConversationRow(id="a", legacy_workflow_id="sales_discovery", status="completed", fields=full,
                            messages=[], progress={}, created_at=old, updated_at=old),
            ConversationRow(id="b", agent_id="sales_discovery", agent_version=1, status="active",
                            fields={"contact_name": "Ana"}, messages=[], progress={}, created_at=old, updated_at=old),
            ConversationRow(id="c", agent_id="sales_discovery", agent_version=1, status="completed", fields={},
                            messages=[], progress={"outcome": "fuera_de_tema"}, created_at=old, updated_at=old),
            # Ya tiene conversion: no se toca.
            ConversationRow(id="d", agent_id="sales_discovery", agent_version=1, status="completed", fields={},
                            messages=[], progress={}, conversion="partial", created_at=old, updated_at=old),
        ])
        s.commit()
        assert reports_backfill(s, batch=2, definitions=ReferenceDefinitions()) == 3
        assert reports_backfill(s, batch=2, definitions=ReferenceDefinitions()) == 0
        s.expire_all()
        got = {r.id: (r.outcome, r.goal, r.conversion, r.updated_at) for r in s.scalars(select(ConversationRow))}
    assert got == {"a": ("demo", True, "complete", old), "b": (None, None, "partial", old),
                   "c": ("fuera_de_tema", False, "empty", old), "d": (None, None, "partial", old)}
