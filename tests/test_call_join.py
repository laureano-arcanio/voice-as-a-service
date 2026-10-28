"""POST /calls/{id}/join: el cliente se conecta a su llamada de prueba (la de join_url)."""
import jwt

from app.config import settings
from app.models import CallStatus
from app.services import calls as call_service

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)


def test_join_test_call(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "demo_livekit_url", "wss://rtc.example.com")
    c = make_client(admin)
    user = client_user(api, admin, c)
    cid = user.post(f"{V1}/calls", json={"agent_id": make_agent(admin, c)["id"]}).json()["conversation_id"]
    r = user.post(f"{V1}/calls/{cid}/join")
    assert r.status_code == 200, r.text
    assert r.json()["livekit_url"] == "wss://rtc.example.com"
    claims = jwt.decode(r.json()["token"], options={"verify_signature": False})
    assert claims["video"]["room"] == f"call-{cid}" and claims["video"]["roomJoin"] and claims["sub"] == f"tester-call-{cid}"
    # Otro cliente no la ve; terminada ya no se puede.
    other = client_user(api, admin, make_client(admin, slug="otro"), email="x@otro.com")
    assert other.post(f"{V1}/calls/{cid}/join").status_code == 404
    with api.sessions() as s:
        call_service.update_call(s, cid, status=CallStatus.finalizada)
    assert (r := user.post(f"{V1}/calls/{cid}/join")).status_code == 409 and r.json()["code"] == "call_not_active"
