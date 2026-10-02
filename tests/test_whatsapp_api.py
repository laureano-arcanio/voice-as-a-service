"""WhatsApp fase 1 en la API: cuentas (admin) y conversaciones de WhatsApp en el
listado, el detalle y los indicadores del dashboard."""
import pytest

from app.conversation.models import Message
from app.conversation.store import ConversationStore
from app.models import Role, User, WaAccount, WaMessage
from app.services.security import hash_password
from app.whatsapp import store

from .test_api import ADMIN, V1, client_user, make_agent, make_client

PNID = "100000000000002"
WA_ID = "5493510000000"
SECRET = "EAAG-token-secreto-del-cliente"


@pytest.fixture(autouse=True)
def token_key(monkeypatch):
    """Los tokens de las cuentas se guardan cifrados: sin clave, el alta con token da 503."""
    from cryptography.fernet import Fernet

    from app.config import settings
    monkeypatch.setattr(settings, "wa_token_key", Fernet.generate_key().decode())


def account_body(client, agent, **extra):
    return {"client_id": client["id"], "agent_id": agent["id"], "phone_number_id": PNID,
            "waba_id": "200000000000003", "display_phone_number": "+1 555 145 6632", "name": "Prueba", **extra}


@pytest.fixture
def admin(api):
    with api.sessions() as s:
        s.add(User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role=Role.admin))
        s.commit()
    return api.login(*ADMIN)


@pytest.fixture
def setup(api, admin):
    c = make_client(admin)
    agent = make_agent(admin, c, template="demo_booking")
    r = admin.post(f"{V1}/whatsapp/accounts", json=account_body(c, agent, access_token=SECRET))
    assert r.status_code == 201, r.text
    return c, agent, r.json()


def wa_conversation(api, account_id: str, failed_error: dict | None = None) -> str:
    """Una conversacion de WhatsApp como la deja el service: sin apertura, con hilo."""
    with api.sessions() as s:
        account = s.get(WaAccount, account_id)
        state, _ = api.engine.new_conversation(account.agent_id, account.client_id, s, channel="whatsapp",
                                               opening=False)
        state.messages = [Message(role="user", text="hola"), Message(role="assistant", text="¡Hola!")]
        ConversationStore.add(s, state)
        store.add_thread(s, conversation_id=state.conversation_id, account=account, wa_id=WA_ID,
                         contact_name="Juan")
        if failed_error:
            store.record_outbound(s, wamid=None, account_id=account.id, conversation_id=state.conversation_id,
                                  wa_id=WA_ID, type="text", status="failed", error=failed_error)
        s.commit()
        return state.conversation_id


def test_account_crud_never_returns_token(api, admin, setup):
    _, agent, acc = setup
    assert acc["has_token"] is True and acc["active"] is True
    assert acc["client_name"] == "Acme" and acc["agent_name"] == "Ventas"
    assert SECRET not in str(acc) and "access_token" not in acc

    listed = admin.get(f"{V1}/whatsapp/accounts").json()
    assert [a["id"] for a in listed] == [acc["id"]] and SECRET not in str(listed)
    assert admin.get(f"{V1}/whatsapp/accounts", params={"client_id": "otro"}).json() == []

    upd = admin.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"name": "Turnos", "access_token": ""}).json()
    assert upd["name"] == "Turnos" and upd["has_token"] is False
    with api.sessions() as s:
        assert s.get(WaAccount, acc["id"]).access_token is None

    # null en columnas NOT NULL: sin cambio.
    same = admin.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"agent_id": None, "name": None}).json()
    assert same["agent_id"] == agent["id"] and same["name"] == "Turnos"

    off = admin.post(f"{V1}/whatsapp/accounts/{acc['id']}/deactivate").json()
    assert off["active"] is False
    on = admin.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"active": True}).json()
    assert on["active"] is True
    assert admin.patch(f"{V1}/whatsapp/accounts/nada", json={"name": "x"}).status_code == 404


def test_account_validation(api, admin, setup):
    c, agent, acc = setup
    # phone_number_id repetido.
    r = admin.post(f"{V1}/whatsapp/accounts", json=account_body(c, agent))
    assert r.status_code == 409
    # Solo digitos.
    assert admin.post(f"{V1}/whatsapp/accounts",
                      json=account_body(c, agent, phone_number_id="+5491100")).status_code == 422
    # Agente de otro cliente.
    other = make_client(admin, "otro")
    theirs = make_agent(admin, other)
    r = admin.post(f"{V1}/whatsapp/accounts", json=account_body(c, theirs, phone_number_id="999"))
    assert r.status_code in (404, 422)
    r = admin.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"agent_id": theirs["id"]})
    assert r.status_code in (404, 422)
    # Agente archivado.
    archived = make_agent(admin, c, template="sales_discovery", name="Viejo")
    admin.patch(f"{V1}/agents/{archived['id']}", json={"archived": True})
    r = admin.post(f"{V1}/whatsapp/accounts", json=account_body(c, archived, phone_number_id="998"))
    assert r.status_code == 422


def test_client_user_manages_only_own_accounts(api, admin, setup):
    """Fase 2: el usuario del cliente ve y edita sus cuentas (agente, nombre, activa); el
    token, el numero visible y el alta manual quedan para admin."""
    c, agent, acc = setup
    user = client_user(api, admin, c)
    listed = user.get(f"{V1}/whatsapp/accounts").json()
    assert [a["id"] for a in listed] == [acc["id"]] and SECRET not in str(listed)
    assert user.get(f"{V1}/whatsapp/accounts", params={"client_id": "otro"}).status_code == 403
    assert user.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"name": "x"}).json()["name"] == "x"
    assert user.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"access_token": "t"}).status_code == 403
    assert user.patch(f"{V1}/whatsapp/accounts/{acc['id']}",
                      json={"display_phone_number": "+54"}).status_code == 403
    assert user.post(f"{V1}/whatsapp/accounts", json=account_body(c, agent, phone_number_id="9")).status_code == 403
    assert user.post(f"{V1}/whatsapp/accounts/{acc['id']}/deactivate").json()["active"] is False
    assert api.client.get(f"{V1}/whatsapp/accounts").status_code == 401
    key = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "crm"}).json()["key"]
    assert [a["id"] for a in api.client.get(f"{V1}/whatsapp/accounts",
                                            headers={"Authorization": f"Bearer {key}"}).json()] == [acc["id"]]

    # Otro cliente no la ve ni la toca (404, no 403: no se revela que existe).
    other = client_user(api, admin, make_client(admin, slug="otro"), email="b@otro.com")
    assert other.get(f"{V1}/whatsapp/accounts").json() == []
    assert other.patch(f"{V1}/whatsapp/accounts/{acc['id']}", json={"name": "y"}).status_code == 404
    assert other.post(f"{V1}/whatsapp/accounts/{acc['id']}/deactivate").status_code == 404


def test_whatsapp_conversation_in_list_detail_and_stats(api, admin, setup):
    c, agent, acc = setup
    error = {"code": 131047, "subcode": None, "message": "Re-engagement"}
    cid = wa_conversation(api, acc["id"], failed_error=error)
    test_call = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()["conversation_id"]
    api_conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]

    page = admin.get(f"{V1}/calls", params={"mode": "whatsapp"}).json()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["id"] == cid and item["mode"] == "whatsapp" and item["phone"] == WA_ID
    assert item["status"] is None and item["duration_seconds"] == 0 and item["latency_avg"] is None

    only_api = admin.get(f"{V1}/calls", params={"mode": "api"}).json()
    assert [i["id"] for i in only_api["items"]] == [api_conv]
    assert {i["id"] for i in admin.get(f"{V1}/calls").json()["items"]} == {cid, test_call, api_conv}
    # Los filtros de estado son de llamadas: WhatsApp no tiene.
    live = admin.get(f"{V1}/calls", params={"status": ["pendiente", "en_curso"]}).json()["items"]
    assert cid not in {i["id"] for i in live}

    detail = admin.get(f"{V1}/calls/{cid}").json()
    assert detail["call"] is None
    wa = detail["whatsapp"]
    assert wa["wa_id"] == WA_ID and wa["contact_name"] == "Juan"
    assert wa["business_number"] == "+1 555 145 6632" and wa["account_id"] == acc["id"]
    assert wa["failed_messages"] == 1 and wa["last_error"]["code"] == 131047
    assert detail["messages"][0]["role"] == "user"
    assert admin.get(f"{V1}/calls/{test_call}").json()["whatsapp"] is None

    stats = admin.get(f"{V1}/stats", params={"client_id": c["id"]}).json()
    assert stats["total"] == 3 and stats["calls"] == 1 and stats["whatsapp"] == 1


def test_client_user_sees_its_whatsapp_conversations(api, admin, setup):
    c, _, acc = setup
    cid = wa_conversation(api, acc["id"])
    user = client_user(api, admin, c)
    assert user.get(f"{V1}/calls", params={"mode": "whatsapp"}).json()["total"] == 1
    assert user.get(f"{V1}/calls/{cid}").json()["whatsapp"]["failed_messages"] == 0
    other = make_client(admin, "otro")
    outsider = client_user(api, admin, other, email="otro@otro.com")
    assert outsider.get(f"{V1}/calls/{cid}").status_code == 404
    with api.sessions() as s:
        assert s.query(WaMessage).count() == 0


def test_api_turn_on_whatsapp_conversation_is_409(api, admin, setup):
    _, _, acc = setup
    cid = wa_conversation(api, acc["id"])
    r = admin.post(f"{V1}/conversations/{cid}/turns", json={"message": "hola"})
    assert r.status_code == 409 and r.json()["code"] == "whatsapp_conversation"


def test_delete_agent_or_client_with_whatsapp_account_is_409(api, admin, setup):
    # En PostgreSQL wa_accounts tiene FK RESTRICT: sin el chequeo seria un 500.
    c, agent, _ = setup
    assert admin.delete(f"{V1}/agents/{agent['id']}").status_code == 409
    assert admin.delete(f"{V1}/clients/{c['id']}").status_code == 409


def test_close_whatsapp_conversation(api, admin, setup):
    c, _, acc = setup
    cid = wa_conversation(api, acc["id"])
    assert admin.get(f"{V1}/calls/{cid}").json()["whatsapp"]["closed_at"] is None
    other = make_client(admin, "otro")
    outsider = client_user(api, admin, other, email="otro@otro.com")
    assert outsider.post(f"{V1}/whatsapp/threads/{cid}/close").status_code == 404
    # El usuario del cliente la puede cerrar; cerrar dos veces no cambia la fecha.
    user = client_user(api, admin, c)
    assert user.post(f"{V1}/whatsapp/threads/{cid}/close").status_code == 204
    closed = admin.get(f"{V1}/calls/{cid}").json()["whatsapp"]["closed_at"]
    assert closed is not None
    assert admin.post(f"{V1}/whatsapp/threads/{cid}/close").status_code == 204
    assert admin.get(f"{V1}/calls/{cid}").json()["whatsapp"]["closed_at"] == closed
    assert admin.post(f"{V1}/whatsapp/threads/no-existe/close").status_code == 404
