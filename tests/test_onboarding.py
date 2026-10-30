"""Asistente de primera vez (docs/features/PRIMERA_VEZ.md): celular del registro, primer agente por rubro y
voz, codigo por WhatsApp y llamadas de prueba al celular (modo celular, sin minutos del plan)."""
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import CallMode, CallRow, CallStatus, Client, User
from app.services import onboarding
from app.services.profile import limiter

from .test_api import V1, admin, client_user, make_client  # noqa: F401  (admin: fixture)
from .test_billing import landing, plans, register  # noqa: F401  (fixtures)
from .test_mail import outbox  # noqa: F401  (fixture)


class FakeGraph:
    def __init__(self):
        self.sent = []

    def client(self, token):
        graph = self

        class C:
            async def send_auth_code(self, pnid, to, name, language, code):
                graph.sent.append({"pnid": pnid, "to": to, "name": name, "code": code})
                return {"messages": [{"id": "wamid.1"}]}
        return C()


@pytest.fixture
def wa(monkeypatch):
    graph = FakeGraph()
    monkeypatch.setattr(onboarding, "graph_for", graph.client)
    monkeypatch.setattr(settings, "phone_verify_wa_number_id", "123")
    monkeypatch.setattr(settings, "phone_verify_wa_template", "codigo")
    limiter.reset()
    return graph


@pytest.fixture
def ana(api, admin):  # noqa: F811
    client = make_client(admin)
    return client, client_user(api, admin, client)


def test_signup_keeps_the_phone(landing):  # noqa: F811
    assert register(landing, phone="351 555-1234").status_code == 201
    with landing.sessions() as s:
        user = s.scalar(select(User).where(User.email == "rosa@example.com"))
        assert user.phone == "+5493515551234" and user.phone_verified_at is None
    bad = register(landing, email="otra@example.com", phone="123456")
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_phone"


def test_first_agent_from_industry_and_voice(api, ana):
    client, user = ana
    status = user.get(f"{V1}/onboarding").json()
    assert status["has_agents"] is False and status["industry"] is None
    assert [i["id"] for i in user.get(f"{V1}/onboarding/industries").json()][-1] == "otro"
    r = user.post(f"{V1}/onboarding/agent", json={"industry": "gimnasio", "voice": "lucas", "website": "acme.com"})
    assert r.status_code == 201, r.text
    agent = r.json()
    assert agent["name"] == "Lucas · atención" and agent["voice"] == "lucas"
    assert "Acme" in agent["definition"]["conversation"]["opening"]
    status = user.get(f"{V1}/onboarding").json()
    assert status["has_agents"] is True and status["industry"] == "gimnasio" and status["website"] == "https://acme.com"
    # Otra vez el mismo rubro y voz (archivo el primero): slug distinto.
    assert user.post(f"{V1}/onboarding/agent", json={"industry": "gimnasio", "voice": "lucas"}).status_code == 201
    assert user.post(f"{V1}/onboarding/agent", json={"industry": "minería", "voice": "lucas"}).status_code == 422
    assert user.post(f"{V1}/onboarding/agent", json={"industry": "salud", "voice": "nadie"}).status_code == 422


def test_phone_code_by_whatsapp(api, ana, wa):
    _, user = ana
    sent = user.post(f"{V1}/onboarding/phone/code", json={"phone": "11 5555-1234"})
    assert sent.status_code == 200, sent.text
    assert sent.json()["phone"] == "+5491155551234" and wa.sent[0]["to"] == "541155551234"
    code = wa.sent[0]["code"]
    challenge = sent.json()["challenge"]
    bad = user.post(f"{V1}/onboarding/phone/verify", json={"challenge": challenge, "code": "000000" if code != "000000" else "111111"})
    assert bad.status_code == 422
    ok = user.post(f"{V1}/onboarding/phone/verify", json={"challenge": challenge, "code": code})
    assert ok.status_code == 200 and ok.json()["phone_verified"] is True and ok.json()["phone"] == "+5491155551234"


def test_phone_code_needs_whatsapp_configured(api, ana):
    _, user = ana
    r = user.post(f"{V1}/onboarding/phone/code", json={"phone": "11 5555-1234"})
    assert r.status_code == 503 and r.json()["code"] == "phone_verify_unavailable"
    assert user.get(f"{V1}/onboarding").json()["verify_available"] is False


def test_call_me_trial_quota(api, ana, admin, monkeypatch):  # noqa: F811
    client, user = ana
    agent = user.post(f"{V1}/onboarding/agent", json={"industry": "salud", "voice": "sofia"}).json()
    assert user.post(f"{V1}/onboarding/call-me", json={"agent_id": agent["id"]}).status_code == 409
    with api.sessions() as s:
        u = s.scalar(select(User).where(User.email == "ana@acme.com"))
        u.phone, u.phone_verified_at = "+5491155551234", u.created_at
        s.commit()
    monkeypatch.setattr(settings, "trial_calls", 2)
    r = user.post(f"{V1}/onboarding/call-me", json={"agent_id": agent["id"]})
    assert r.status_code == 201, r.text
    assert r.json()["mode"] == "celular" and r.json()["join_url"] is None
    meta = api.dispatched[-1]
    assert meta["trial"] is True and meta["phone"] == "+5491155551234"
    assert meta["max_duration_seconds"] == settings.trial_call_seconds
    with api.sessions() as s:   # termino: 100 s
        row = s.get(CallRow, r.json()["conversation_id"])
        row.status, row.duration_seconds = CallStatus.finalizada, 100
        s.commit()
    r = user.post(f"{V1}/onboarding/call-me", json={"agent_id": agent["id"]})
    assert r.status_code == 201 and api.dispatched[-1]["max_duration_seconds"] == settings.trial_call_seconds - 100
    with api.sessions() as s:
        s.get(CallRow, r.json()["conversation_id"]).status = CallStatus.finalizada
        s.commit()
    r = user.post(f"{V1}/onboarding/call-me", json={"agent_id": agent["id"]})
    assert r.status_code == 429 and r.json()["code"] == "trial_calls"
    status = user.get(f"{V1}/onboarding").json()["trial"]
    assert status["calls_used"] == 2 and status["seconds_used"] == 100
    # No gasta minutos del plan ni la puede pedir un admin.
    assert admin.post(f"{V1}/onboarding/call-me", json={"agent_id": agent["id"]}).status_code in (403, 422)
    with api.sessions() as s:
        assert s.get(Client, client["id"]) is not None
        modes = s.scalars(select(CallRow.mode).where(CallRow.client_id == client["id"])).all()
        assert set(modes) == {CallMode.celular}
