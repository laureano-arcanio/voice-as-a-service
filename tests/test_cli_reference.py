"""make agents-reference: pasa a los agentes de atentina el prompt, el primer mensaje, las variables y el analisis de la
referencia sin tocar el resto de su version vigente."""
import pytest
from sqlalchemy import select

from app.agents.templates import reference_data
from app.cli import _client, agents_reference, reference_merge, seed
from app.models import Agent, AgentVersion, Client
from app.services import agents as agent_service

SLUG = "atentina_comercial"


def agent_of(s, client_slug="atentina", slug=SLUG) -> Agent:
    return s.scalar(select(Agent).join(Client, Client.id == Agent.client_id)
                    .where(Client.slug == client_slug, Agent.slug == slug))


def versions(s, agent) -> int:
    return s.query(AgentVersion).filter_by(agent_id=agent.id).count()


@pytest.fixture
def old(sessions, monkeypatch):
    """atentina con sus agentes sembrados, y el comercial editado a mano: prompt viejo, otra voz, grabacion y email."""
    monkeypatch.delenv("ANURA_DID", raising=False)
    with sessions() as s:
        seed(s)
        agent = agent_of(s)
        edited = {**agent.definition, "prompt": "Prompt viejo.", "first_message": "Hola viejo.",
                  "record_audio": True, "call_summary_email": True,
                  "agent": {**agent.definition["agent"], "voice": "belen"}}
        edited.pop("variables", None)
        agent_service.update_definition(s, agent, edited, None)
        # Otro cliente con un agente del mismo slug: no se toca.
        other = _client(s, "otro")
        agent_service.create_agent(s, other, name="Comercial", slug=SLUG, description="x",
                                   definition={**reference_data(SLUG), "prompt": "Del otro cliente."},
                                   template_id=None, user_id=None)
        s.commit()
    return sessions


def test_dry_run_shows_the_diff_and_writes_nothing(old, capsys):
    with old() as s:
        before = agent_of(s)
        version, count = before.version, versions(s, before)
        assert agents_reference(s, apply=False, slug=SLUG) == 1
        s.rollback()
        after = agent_of(s)
        assert (after.version, versions(s, after), after.definition["prompt"]) == (version, count, "Prompt viejo.")
    out = capsys.readouterr().out
    assert "-    Prompt viejo." in out and "+    # Identidad" in out and "sin --apply" in out


def test_apply_replaces_the_content_and_keeps_the_rest(old):
    ref = reference_data(SLUG)
    with old() as s:
        version = agent_of(s).version
        assert agents_reference(s, apply=True, slug=SLUG) == 1
        agent = agent_of(s)
        d = agent.definition
        assert agent.version == version + 1 and versions(s, agent) == version + 1
        assert d["prompt"] == ref["prompt"] and d["first_message"] == ref["first_message"]
        assert [f["name"] for f in d["analysis"]["fields"]] == [f["name"] for f in ref["analysis"]["fields"]]
        assert [o["id"] for o in d["analysis"]["outcomes"]] == [o["id"] for o in ref["analysis"]["outcomes"]]
        assert [v["name"] for v in d["variables"]] == [v["name"] for v in ref["variables"]]
        # Lo que el cliente edito, intacto.
        assert d["agent"]["voice"] == "belen" and d["record_audio"] is True and d["call_summary_email"] is True


def test_second_run_does_nothing(old, capsys):
    with old() as s:
        agents_reference(s, apply=True, slug=SLUG)
        version = agent_of(s).version
        assert agents_reference(s, apply=True) == 0
        assert agent_of(s).version == version
    assert "ya es igual" in capsys.readouterr().out


def test_other_client_with_the_same_slug_is_not_touched(old):
    with old() as s:
        agents_reference(s, apply=True)
        other = agent_of(s, "otro")
        assert other.definition["prompt"] == "Del otro cliente." and other.version == 1


def test_only_reference_agents_and_unknown_slug(old):
    with old() as s, pytest.raises(SystemExit):
        agents_reference(s, apply=False, slug="loadtest")


def test_merge_keeps_tools_handoff_and_workflows():
    ref = reference_data("landing_turnos")
    current = {"id": "turnos", "version": 3, "agent": {"name": "Viejo", "language": "es-AR", "voice": "lucia"},
               "prompt": "x", "first_message": "y", "tools": [{"tool": "agendar"}], "handoff": {"areas": []},
               "workflows": {"pre_call": {"tool": "buscar"}}, "llm": {"stages": [{"from_turn": 1}]},
               "analysis": {"fields": []}, "first_message_audio": True, "first_message_delay_ms": 900}
    merged = reference_merge(current, ref)
    assert merged["prompt"] == ref["prompt"] and merged["agent"] == {**ref["agent"], "voice": "lucia"}
    assert {k: merged[k] for k in ("tools", "handoff", "workflows", "llm", "first_message_audio",
                                   "first_message_delay_ms")} == {k: current[k] for k in (
        "tools", "handoff", "workflows", "llm", "first_message_audio", "first_message_delay_ms")}


MINE = ("atentina_comercial", "berlin_signup", "demo_booking", "sales_discovery",
        "landing_cobranzas", "landing_reclamos", "landing_turnos")


@pytest.mark.parametrize("rid", MINE)
def test_reference_is_written_in_the_current_form(rid):
    """Reescritos a mano: sin claves viejas, con el prompt por secciones y cada {{variable}} declarada o del sistema."""
    import re

    from app.agents.templates import load_reference
    from app.conversation import legacy
    data = reference_data(rid)
    assert not legacy.is_legacy(data) and not {"objective", "conversation", "knowledge", "fields", "completion"} & set(data)
    assert "role" not in data["agent"] and data["first_message"]
    assert all(f"# {title}" in data["prompt"] for title in ("Identidad", "Objetivo", "Datos a obtener", "Cómo conversar",
                                                           "Información", "Cierre"))
    used = set(re.findall(r"\{\{\s*([\w.]+)\s*\}\}", data["prompt"] + data["first_message"]))
    declared = {v["name"] for v in data.get("variables", [])}
    assert all(name in declared or name.startswith("call.") for name in used)
    wf = load_reference(rid)
    assert wf.analysis_fields and wf.outcomes and not wf.outcomes[-1].when
    assert all("question" not in f.model_dump() for f in wf.analysis_fields.values())
