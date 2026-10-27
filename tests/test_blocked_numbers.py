"""Numeros bloqueados (no se atienden), corte de una llamada desde la API y corte del agente en una
llamada fuera de tema (llamada 07381a4d)."""
import pytest

from app.conversation.engine import ConversationEngine
from app.conversation.models import AgentTurn
from app.llm import platform_tools
from app.models import CallRow, CallStatus
from app.services import calls as call_service
from app.services import livekit
from app.services.errors import Forbidden

from .helpers import FakeLLM, turn_and_extract
from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
)

DID = "+541152630861"


def inbound_setup(admin):
    c = make_client(admin)
    agent = make_agent(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": DID, "agent_id": agent["id"]})
    return c


# ---------- numeros bloqueados ----------

def test_blocked_caller_is_not_answered(api, admin):
    c = inbound_setup(admin)
    # Anura manda el caller sin el 9 y el admin lo tipea como sea: se comparan normalizados.
    r = admin.post(f"{V1}/blocked-numbers", params={"client_id": c["id"]},
                   json={"phone": "351 377-5197", "note": "broma"})
    assert r.status_code == 201 and r.json()["phone"] == "+5493513775197"
    with api.sessions() as s, pytest.raises(Forbidden) as e:
        call_service.start_inbound(s, api.engine, DID, "+543513775197")
    assert e.value.code == "blocked_number"
    rejected = admin.get(f"{V1}/calls", params={"status": "rechazada"}).json()["items"]
    assert [x["ended_reason"] for x in rejected] == ["blocked_number"]
    # Por WhatsApp llega el wa_id (sin +).
    with api.sessions() as s, pytest.raises(Forbidden):
        call_service.start_inbound(s, api.engine, DID, None, wa_id="5493513775197")
    # Otro numero entra normal.
    with api.sessions() as s:
        call_service.start_inbound(s, api.engine, DID, "+5491100000000")

    assert admin.delete(f"{V1}/blocked-numbers/+5493513775197", params={"client_id": c["id"]}).status_code == 204
    with api.sessions() as s:
        call_service.start_inbound(s, api.engine, DID, "+543513775197")


def test_blocked_numbers_are_per_client(api, admin):
    acme = inbound_setup(admin)
    other = make_client(admin, slug="otro")
    admin.post(f"{V1}/blocked-numbers", params={"client_id": other["id"]}, json={"phone": "+5493513775197"})
    with api.sessions() as s:
        call_service.start_inbound(s, api.engine, DID, "+543513775197")   # bloqueado en otro cliente
    user = client_user(api, admin, acme)
    assert user.post(f"{V1}/blocked-numbers", json={"phone": "3513775197"}).status_code == 201
    assert [b["phone"] for b in user.get(f"{V1}/blocked-numbers").json()] == ["+5493513775197"]
    assert user.get(f"{V1}/blocked-numbers", params={"client_id": other["id"]}).status_code == 403
    assert admin.post(f"{V1}/blocked-numbers", json={"phone": "3513775197"}).status_code == 422   # sin cliente
    assert user.post(f"{V1}/blocked-numbers", json={"phone": "12"}).status_code == 422


# ---------- corte desde la API ----------

@pytest.fixture
def rooms(monkeypatch):
    deleted: list[str] = []
    existing = {"exists": True}

    async def fake_delete(room):
        deleted.append(room)
        return existing["exists"]

    monkeypatch.setattr(livekit, "delete_room", fake_delete)
    return deleted, existing


def test_hang_up_live_call(api, admin, rooms):
    deleted, _ = rooms
    c = inbound_setup(admin)
    with api.sessions() as s:
        cid = call_service.start_inbound(s, api.engine, DID, "+5491100000000").conversation_id
        call_service.update_call(s, cid, status=CallStatus.en_curso, room="anura-_+5491100000000_abc")
    r = admin.post(f"{V1}/calls/{cid}/hangup")
    assert r.status_code == 200 and r.json()["ended_reason"] == "hangup_by_user"
    assert deleted == ["anura-_+5491100000000_abc"]
    # El worker cierra la llamada (finalize) y conserva el motivo; ya no se puede cortar de nuevo.
    with api.sessions() as s:
        call_service.update_call(s, cid, status=CallStatus.finalizada)
    assert admin.post(f"{V1}/calls/{cid}/hangup").status_code == 409
    # Otro cliente no la ve.
    other = client_user(api, admin, make_client(admin, slug="otro"), email="x@otro.com")
    assert other.post(f"{V1}/calls/{cid}/hangup").status_code == 404
    assert c


def test_hang_up_without_room_closes_the_stale_call(api, admin, rooms):
    deleted, existing = rooms
    existing["exists"] = False
    agent = make_agent(admin, make_client(admin))
    cid = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()["conversation_id"]
    assert admin.post(f"{V1}/calls/{cid}/hangup").status_code == 200
    assert deleted == [f"call-{cid}"]     # sin room guardada: la que arma prepare_call
    with api.sessions() as s:
        call = s.get(CallRow, cid)
        assert call.status == CallStatus.finalizada and call.ended_reason == "hangup_by_user"


# ---------- corte del agente: fuera de tema ----------

def test_end_call_off_topic_ends_the_turn():
    """end_call con motivo fuera_de_tema: termina y marca off_topic; con terminada, solo termina."""
    from app.conversation.models import ConversationState

    state = ConversationState(conversation_id="c", agent_id="a", fields={})
    turn = AgentTurn(assistant_message="Esta línea es para consultas. ¡Chau!")
    platform_tools.apply(turn, [{"name": "end_call", "arguments": '{"motivo": "fuera_de_tema"}'}], state)
    assert turn.status == "completed" and turn.end_reason == "off_topic"
    normal = AgentTurn(assistant_message="¡Gracias!")
    platform_tools.apply(normal, [{"name": "end_call", "arguments": '{"motivo": "terminada"}'}], state)
    assert normal.status == "completed" and normal.end_reason is None


def test_end_call_offers_off_topic_reason():
    from app.conversation.models import ConversationState

    tool = platform_tools.tools_for(ConversationState(conversation_id="c", agent_id="a", fields={}))[0]
    assert tool["function"]["name"] == "end_call"
    assert tool["function"]["parameters"]["properties"]["motivo"]["enum"] == ["terminada", "fuera_de_tema"]


async def test_off_topic_outcome_survives_extraction(store):
    llm = FakeLLM(AgentTurn(assistant_message="Esta línea es para consultas. ¡Chau!", status="completed",
                            end_reason="off_topic"),
                  extractions=[{"contact_name": "Joel"}])
    engine = ConversationEngine(llm, store)
    state, _ = engine.start_conversation("berlin_signup")
    state, _ = await turn_and_extract(engine, state.conversation_id, "Soy un choro, me llamo Joel.")
    assert state.status == "completed" and state.progress.outcome == "fuera_de_tema"
    assert state.fields["contact_name"] == "Joel"
