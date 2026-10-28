"""Herramientas del cliente en el motor (docs/features/HERRAMIENTAS.md): function calling nativo (streaming, vueltas,
tope por turno, frases de voz, confirmacion en la descripcion, vars, traza). El LLM es un cliente OpenAI falso
con respuestas grabadas; la herramienta llama de verdad a la API falsa."""
import json
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from app.agents.definitions import DbDefinitions
from app.agents.templates import reference_data
from app.config import settings
from app.conversation.engine import ConversationEngine
from app.conversation.store import ConversationStore
from app.llm.client import LLMClient
from scripts.tools import mock_api

from .test_api import V1, admin, make_client  # noqa: F401  (admin: fixture)
from .tools_mock import mock_api_url, mock_server  # noqa: F401  (fixtures)


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls, reasoning_content=None, reasoning=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def tc(index, id=None, name=None, arguments=None):
    return SimpleNamespace(index=index, id=id, function=SimpleNamespace(name=name, arguments=arguments))


class Script:
    """Respuestas en orden: ("texto", [(nombre, argumentos), ...])."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    async def create(self, **request):
        self.requests.append(json.loads(json.dumps(request, default=str)))
        text, calls = self.replies.pop(0)
        chunks = []
        for i in range(0, len(text), 7):
            chunks.append(chunk(content=text[i:i + 7]))
        for n, (name, args) in enumerate(calls):
            raw = json.dumps(args, ensure_ascii=False)
            chunks.append(chunk(tool_calls=[tc(n, id=f"call_{n}", name=name, arguments=raw[:5])]))
            chunks.append(chunk(tool_calls=[tc(n, arguments=raw[5:])]))
        if not request.get("stream"):
            message = SimpleNamespace(content=text, reasoning_content=None, tool_calls=[
                SimpleNamespace(id=f"call_{n}", function=SimpleNamespace(name=name, arguments=json.dumps(args)))
                for n, (name, args) in enumerate(calls)] or None)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        async def stream():
            for c in chunks:
                yield c
        return stream()


def llm_with(script: Script) -> LLMClient:
    llm = LLMClient("http://localhost:1/v1", "x", "m")
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=script))
    llm.derive = lambda **kw: llm           # el resolver deriva uno por agente: que siga siendo el falso
    return llm


def turnos_tool(base, **extra):
    return {"slug": "consultar_turnos", "type": "http", "definition": {
        "description": "Busca turnos libres de una sucursal para una fecha.",
        "messages": {"start": "Dame un segundo que me fijo."},
        "assign": [{"var": "sucursal_nombre", "path": "sucursal.nombre"}],
        "http": {"method": "GET", "url": base + "/sucursales/{sucursal}/turnos",
                 "path": {"sucursal": {"type": "string", "enum": ["centro", "norte"], "description": "Sucursal"}},
                 "query": {"fecha": {"type": "string", "description": "AAAA-MM-DD", "required": True}},
                 "auth": {"type": "bearer", "secret": "MOCK_TOKEN"}}, **extra}}


def reservar_tool(base):
    return {"slug": "reservar_turno", "type": "http", "definition": {
        "description": "Reserva un turno libre. Pedí confirmación antes.", "confirm": True,
        "http": {"method": "POST", "url": base + "/reservas", "auth": {"type": "bearer", "secret": "MOCK_TOKEN"},
                 "body": {"type": "object", "required": ["fecha", "hora", "nombre"], "properties": {
                     "sucursal": {"type": "string", "value": "centro"},
                     "fecha": {"type": "string", "description": "AAAA-MM-DD"},
                     "hora": {"type": "string", "description": "HH:MM"},
                     "nombre": {"type": "string", "description": "Nombre de la persona"}}}}}}


def setup(api, admin, base, script, tools=("consultar_turnos",), turnos_extra=None, **definition_extra):
    c = make_client(admin, max_tools=None)
    for t in (turnos_tool(base, **(turnos_extra or {})), reservar_tool(base)):
        assert admin.post(f"{V1}/clients/{c['id']}/tools", json=t).status_code == 201
    definition = reference_data("demo_booking")
    agent = admin.post(f"{V1}/agents", json={"client_id": c["id"], "name": "Turnos", "slug": "turnos",
                                             "definition": definition}).json()
    admin.post(f"{V1}/agents/{agent['id']}/secrets", json={"name": "MOCK_TOKEN", "value": mock_api.TOKEN})
    r = admin.put(f"{V1}/agents/{agent['id']}/definition",
                  json={"definition": {**agent["definition"], "tools": [{"tool": t} for t in tools],
                                       **definition_extra}})
    assert r.status_code == 200, r.text
    engine = ConversationEngine(llm_with(script), ConversationStore(api.sessions), DbDefinitions(api.sessions))
    state, _ = engine.start_conversation(agent["id"], c["id"])
    return engine, state.conversation_id


async def test_classic_calls_the_tool_and_answers_with_the_result(api, admin, mock_api_url):
    script = Script(("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-05"})]),
                    ("Tengo libre a las 10, 11:30 y 16.", []))
    engine, cid = setup(api, admin, mock_api_url, script)
    said = []
    state, turn = await engine.process_turn(cid, "¿Tienen turno el 5 de noviembre en el centro?", on_message=said.append)
    # La frase de inicio suena mientras se ejecuta, y despues la respuesta con el dato.
    assert said[0] == "Dame un segundo que me fijo."
    assert "".join(said[1:]) == "Tengo libre a las 10, 11:30 y 16."
    assert turn.assistant_message == "Tengo libre a las 10, 11:30 y 16."
    first, second = script.requests
    # Las de la plataforma (end_call) y las del cliente, en el mismo pedido.
    assert [t["function"]["name"] for t in first["tools"]] == ["end_call", "consultar_turnos"]
    assert first["tool_choice"] == "auto"
    tool_msg = second["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_0"
    assert json.loads(tool_msg["content"])["data"]["turnos"] == ["10:00", "11:30", "16:00"]
    assert second["messages"][-2]["tool_calls"][0]["function"]["name"] == "consultar_turnos"
    assert mock_api.RECEIVED[-1]["query"] == {"fecha": "2026-11-05"}
    # Traza: el turno y la herramienta (sin el token); vars para las siguientes.
    trace = state.messages[-1].llm
    assert [t["kind"] for t in trace] == ["turno", "herramienta"]
    assert trace[1]["tool"]["slug"] == "consultar_turnos" and trace[1]["tool"]["ok"] is True
    assert mock_api.TOKEN not in json.dumps(trace)
    assert state.progress.tool_vars == {"sucursal_nombre": "Sucursal Centro"}


async def test_the_model_speaking_first_skips_the_start_phrase(api, admin, mock_api_url):
    script = Script(("Ya me fijo. ", [("consultar_turnos", {"sucursal": "norte", "fecha": "2026-11-05"})]),
                    ("A las 15.", []))
    engine, cid = setup(api, admin, mock_api_url, script)
    said = []
    _, turn = await engine.process_turn(cid, "¿Y en el norte?", on_message=said.append)
    assert "Dame un segundo" not in "".join(said) and turn.assistant_message == "Ya me fijo. A las 15."


async def test_round_cap_ends_the_turn_with_the_limit_message(api, admin, mock_api_url):
    """Al llegar a tool_settings.max_calls_per_turn el turno termina con limit_message (dicho por la
    plataforma), sin otra vuelta forzada al modelo."""
    call = ("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-06"})])
    script = Script(call, call, call)
    engine, cid = setup(api, admin, mock_api_url, script,
                        tool_settings={"max_calls_per_turn": 2, "limit_message": "No pude con eso."})
    said = []
    state, turn = await engine.process_turn(cid, "turnos", on_message=said.append)
    assert len(script.requests) == 3 and all(r["tool_choice"] == "auto" for r in script.requests)
    assert len([r for r in mock_api.RECEIVED if r["path"].endswith("/turnos")]) == 2
    assert said[-1] == "No pude con eso." and turn.assistant_message == "No pude con eso."
    assert turn.status == "active"
    control = [t for t in state.messages[-1].llm if t["kind"] == "control"]
    assert control and control[0]["input"] == "consultar_turnos" and "2 vueltas" in control[0]["output"]


async def test_confirm_only_goes_in_the_description_and_the_call_runs(api, admin, mock_api_url):
    """Sin confirmacion de plataforma: confirm agrega una frase a la descripcion y, si el modelo la llama, se
    ejecuta en el momento (el modelo decide cuando)."""
    args = {"fecha": "2026-11-05", "hora": "11:30", "nombre": "Ana"}
    script = Script(("", [("reservar_turno", args)]), ("Listo, quedó reservado.", []))
    engine, cid = setup(api, admin, mock_api_url, script, tools=("consultar_turnos", "reservar_turno"))
    state, turn = await engine.process_turn(cid, "Sí, reservame el de las 11:30, soy Ana.", on_message=lambda t: None)
    tools = {t["function"]["name"]: t["function"]["description"] for t in script.requests[0]["tools"]}
    assert "confirmá con la persona" in tools["reservar_turno"]
    assert "confirmá con la persona" not in tools["consultar_turnos"]
    assert all('{"ok": true, "data": ...}' in tools[n] for n in ("reservar_turno", "consultar_turnos"))
    assert [r["path"] for r in mock_api.RECEIVED] == ["/reservas"]
    assert json.loads(script.requests[1]["messages"][-1]["content"])["data"]["estado"] == "confirmada"
    assert turn.assistant_message == "Listo, quedó reservado."


async def test_same_call_twice_in_a_turn_runs_twice(api, admin, mock_api_url):
    """Sin cache por turno: dos llamadas iguales se ejecutan las dos (protege el Idempotency-Key)."""
    call = ("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-05"})])
    script = Script(call, call, ("A las 10.", []))
    engine, cid = setup(api, admin, mock_api_url, script)
    await engine.process_turn(cid, "turnos", on_message=lambda t: None)
    assert len([r for r in mock_api.RECEIVED if r["path"].endswith("/turnos")]) == 2


async def test_failed_tool_phrase_is_said_by_the_platform(api, admin, mock_api_url):
    """messages.failed la dice la plataforma por el TTS; el modelo recibe solo el error."""
    script = Script(("", [("consultar_turnos", {"sucursal": "centro", "fecha": "2026-11-05"})]),
                    ("Probemos más tarde.", []))
    engine, cid = setup(api, admin, mock_api_url, script, turnos_extra={
        "messages": {"start": "Dame un segundo que me fijo.", "failed": "No pude consultar los turnos."}})
    with api.sessions() as s:
        from app.models import AgentSecret
        s.query(AgentSecret).delete()
        s.commit()
    engine.tools._secrets.clear()
    said = []
    await engine.process_turn(cid, "¿Turnos?", on_message=said.append)
    result = json.loads(script.requests[1]["messages"][-1]["content"])
    assert result["ok"] is False and "MOCK_TOKEN" in result["error"]
    assert "No pude consultar los turnos." not in json.dumps(result, ensure_ascii=False)
    assert said[:2] == ["Dame un segundo que me fijo.", "No pude consultar los turnos."]


async def test_without_customer_tools_only_the_platform_ones_go(api, admin, mock_api_url):
    script = Script(("Hola.", []))
    engine, cid = setup(api, admin, mock_api_url, script, tools=())
    await engine.process_turn(cid, "hola", on_message=lambda t: None)
    assert [t["function"]["name"] for t in script.requests[0]["tools"]] == ["end_call"]
