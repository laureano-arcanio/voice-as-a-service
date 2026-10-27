"""Herramientas de la plataforma (app/llm/platform_tools.py): end_call y transfer_call por function calling
nativo, y como las usa LLMClient.converse. El LLM es un cliente OpenAI falso con respuestas grabadas."""
import json

from app.agents.templates import load_reference
from app.conversation.models import AgentTurn, ConversationState, Message
from app.llm import platform_tools

from .test_classic_tools import Script, llm_with

AREAS = [{"id": "1", "name": "Ventas", "when": "Precios y visitas.", "schedule": None, "schedule_text": "siempre"},
         {"id": "2", "name": "Soporte", "when": "", "schedule": None, "schedule_text": ""}]


def state(channel="voice", areas=()) -> ConversationState:
    st = ConversationState(conversation_id="c", agent_id="sales_discovery", channel=channel, fields={},
                           messages=[Message(role="assistant", text="Hola, ¿en qué te ayudo?")])
    st.progress.handoff_areas = list(areas)
    return st


def names(tools: list[dict]) -> list[str]:
    return [t["function"]["name"] for t in tools]


# ---------- tools_for ----------

def test_end_call_always_and_transfer_only_in_a_call_with_areas():
    assert names(platform_tools.tools_for(state())) == ["end_call"]
    assert names(platform_tools.tools_for(state(areas=AREAS))) == ["end_call", "transfer_call"]
    # Por WhatsApp no se deriva una llamada, aunque haya areas.
    assert names(platform_tools.tools_for(state("whatsapp", AREAS))) == ["end_call"]


def test_end_call_parameters_by_agent_kind():
    ours = platform_tools.tools_for(state())[0]["function"]["parameters"]
    assert ours["properties"]["motivo"]["enum"] == ["terminada", "fuera_de_tema"] and ours["required"] == []
    # Tu propio agente: elige el resultado entre los de la definicion.
    external = platform_tools.tools_for(state(), outcomes=["venta", "sin_venta"])[0]["function"]["parameters"]
    assert external["properties"] == {"outcome": {"type": "string", "enum": ["venta", "sin_venta"],
                                                  "description": external["properties"]["outcome"]["description"]}}


def test_transfer_call_describes_each_area():
    transfer = platform_tools.tools_for(state(areas=AREAS))[1]["function"]
    assert transfer["parameters"]["properties"]["area"]["enum"] == ["Ventas", "Soporte"]
    assert transfer["parameters"]["required"] == ["area"]
    assert "Ventas (Precios y visitas): siempre, atiende ahora" in transfer["description"]


# ---------- apply ----------

def call(name: str, **args) -> dict:
    return {"name": name, "arguments": json.dumps(args)}


def test_apply_end_call():
    turn = AgentTurn(assistant_message="Chau.")
    assert platform_tools.apply(turn, [call("end_call")], state()) is None
    assert (turn.status, turn.end_reason, turn.handoff) == ("completed", None, None)
    off = AgentTurn(assistant_message="Esta línea es para consultas.")
    platform_tools.apply(off, [call("end_call", motivo="fuera_de_tema")], state())
    assert (off.status, off.end_reason) == ("completed", "off_topic")
    # Tu propio agente: devuelve el outcome que eligio.
    ext = AgentTurn(assistant_message="Listo.")
    assert platform_tools.apply(ext, [call("end_call", outcome="venta")], state()) == "venta"


def test_apply_transfer_call_and_end_wins():
    turn = AgentTurn(assistant_message="Te paso.")
    platform_tools.apply(turn, [call("transfer_call", area="Soporte")], state(areas=AREAS))
    assert (turn.status, turn.handoff) == ("active", "Soporte")
    both = AgentTurn(assistant_message="Chau.")
    platform_tools.apply(both, [call("transfer_call", area="Ventas"), call("end_call")], state(areas=AREAS))
    assert (both.status, both.handoff) == ("completed", None)
    # Sin areas en la conversacion, transfer_call no hace nada.
    none = AgentTurn(assistant_message="Te paso.")
    platform_tools.apply(none, [call("transfer_call", area="Ventas")], state())
    assert (none.status, none.handoff) == ("active", None)


def test_apply_ignores_bad_arguments_and_customer_tools():
    turn = AgentTurn(assistant_message="x")
    platform_tools.apply(turn, [{"name": "end_call", "arguments": "no es json"},
                                {"name": "consultar_turnos", "arguments": "{}"}], state(areas=AREAS))
    assert (turn.status, turn.end_reason) == ("completed", None)
    bad = AgentTurn(assistant_message="x")
    platform_tools.apply(bad, [{"name": "transfer_call", "arguments": '{"area": 3}'}], state(areas=AREAS))
    assert bad.handoff is None


# ---------- LLMClient.converse ----------

async def test_converse_ends_with_end_call_after_saying_the_goodbye():
    script = Script(("¡Gracias, que andes bien!", [("end_call", {"motivo": "terminada"})]))
    llm = llm_with(script)
    said = []
    turn = await llm.converse(load_reference("sales_discovery"), state(), "Nada más, chau.", on_message=said.append)
    assert "".join(said) == "¡Gracias, que andes bien!" and turn.assistant_message == "¡Gracias, que andes bien!"
    assert (turn.status, turn.end_reason) == ("completed", None)
    assert len(script.requests) == 1          # una herramienta de la plataforma no pide otra vuelta
    request = script.requests[0]
    assert names(request["tools"]) == ["end_call"] and request["tool_choice"] == "auto"
    assert "end_call" in turn.raw


async def test_converse_off_topic_end_call_without_streaming():
    script = Script(("Esta línea es para consultas de ventas.", [("end_call", {"motivo": "fuera_de_tema"})]))
    turn = await llm_with(script).converse(load_reference("sales_discovery"), state(), "Soy un choro.")
    assert (turn.status, turn.end_reason) == ("completed", "off_topic")
    assert turn.assistant_message == "Esta línea es para consultas de ventas."


async def test_converse_transfer_call():
    script = Script(("Te paso con Ventas, un momento.", [("transfer_call", {"area": "Ventas"})]))
    said = []
    turn = await llm_with(script).converse(load_reference("sales_discovery"), state(areas=AREAS),
                                           "Quiero hablar con alguien de ventas.", on_message=said.append)
    assert (turn.status, turn.handoff) == ("active", "Ventas")
    assert "".join(said) == "Te paso con Ventas, un momento."
    assert names(script.requests[0]["tools"]) == ["end_call", "transfer_call"]


async def test_converse_plain_reply_keeps_the_conversation_going():
    script = Script(("¿Cuántos empleados tienen?", []))
    turn = await llm_with(script).converse(load_reference("sales_discovery"), state(), "Somos una empresa.")
    assert (turn.status, turn.handoff, turn.end_reason) == ("active", None, None)
    assert turn.raw == "¿Cuántos empleados tienen?"
