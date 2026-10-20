"""Resumen por email de cada llamada (app/mail/call_summary.py): bandera del agente, interruptor y destinos
del cliente, el envio con reintentos y el contenido."""
import datetime

import pytest

from app.agents.templates import reference_data
from app.db import utcnow
from app.mail import call_summary
from app.mail.sender import SendResult
from app.models import CallMode, CallRow, CallStatus, ConversationRow
from app.conversation.models import Workflow

from .test_api import V1, admin, client_user, make_agent, make_client  # noqa: F401  (admin: fixture)


class FakeResend(list):
    """Lo que se manda; `results`: lo que contesta cada envio, en orden (sin mas, `sent`)."""

    def __init__(self):
        super().__init__()
        self.results: list[SendResult] = []

    def __call__(self, mail, idempotency_key=None):
        self.append((mail, idempotency_key))
        return self.results.pop(0) if self.results else SendResult("sent", id="re_1")


@pytest.fixture
def resend(monkeypatch):
    fake = FakeResend()
    monkeypatch.setattr("app.mail.call_summary.send", fake)
    return fake


def agent_with_summary(admin, client, on=True):
    return make_agent(admin, client, definition={**reference_data("sales_discovery"), "call_summary_email": on})


def finished_call(api, admin, agent, phone="+54 9 11 5555-1234", **call_values) -> str:
    """Una saliente terminada, con datos y conversacion, como la deja el worker."""
    conv_id = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": phone}).json()["conversation_id"]
    ended = utcnow() - datetime.timedelta(seconds=5)
    with api.sessions() as s:
        conv = s.get(ConversationRow, conv_id)
        conv.fields = {**conv.fields, "contact_name": "Juan Pérez", "company_name": "Logística Sur"}
        conv.messages = [*conv.messages, {"role": "user", "text": "Hola, soy Juan de Logística Sur."},
                         {"role": "assistant", "text": "Gracias Juan, te contactamos."}]
        call = s.get(CallRow, conv_id)
        values = {"status": CallStatus.finalizada, "started_at": ended - datetime.timedelta(seconds=95),
                  "ended_at": ended, "duration_seconds": 95, **call_values}
        for k, v in values.items():
            setattr(call, k, v)
        call_summary.mark_pending(s, call, Workflow.model_validate(agent["definition"]), connected=True)
        s.commit()
    return conv_id


def status(api, conv_id) -> tuple[str | None, int]:
    with api.sessions() as s:
        call = s.get(CallRow, conv_id)
        return call.summary_email, call.summary_email_attempts


def run(api, now=None):
    call_summary.run_once(api.sessions, api.engine.definitions, now=now or utcnow)


# ---------- quien queda pendiente ----------

@pytest.mark.parametrize(("mode", "connected", "campaign", "on", "expected"), [
    (CallMode.entrante, True, False, True, "pending"),
    (CallMode.saliente, True, False, True, "pending"),
    (CallMode.web, True, False, True, "pending"),
    (CallMode.prueba, True, False, True, None),
    (CallMode.loadtest, True, False, True, None),
    (CallMode.saliente, False, False, True, None),     # no atendio
    (CallMode.saliente, True, True, True, None),       # campaña: tiene su reporte y su webhook
    (CallMode.entrante, True, False, False, None),     # el agente no lo tiene prendido
])
def test_mark_pending(mode, connected, campaign, on, expected):
    workflow = Workflow.model_validate({**reference_data("sales_discovery"), "call_summary_email": on})
    call = CallRow(conversation_id="c", client_id="x", mode=mode, status=CallStatus.finalizada,
                   campaign_contact_id="cc" if campaign else None)
    call_summary.mark_pending(None, call, workflow, connected=connected)
    assert call.summary_email == expected


def test_definition_flag_defaults_off():
    assert Workflow.model_validate(reference_data("sales_discovery")).call_summary_email is False


# ---------- envio ----------

def test_sends_summary_to_client_users(api, admin, resend):
    c = make_client(admin)
    client_user(api, admin, c)
    agent = agent_with_summary(admin, c)
    conv_id = finished_call(api, admin, agent)
    assert status(api, conv_id) == ("pending", 0)

    run(api)
    assert status(api, conv_id) == ("sent", 0)
    [(mail, key)] = resend
    assert mail.to == "ana@acme.com" and key == f"call-summary/{conv_id}/ana@acme.com"
    assert mail.subject == "Llamada de Ventas a +5491155551234"
    for text in ("Juan Pérez", "Logística Sur", "Hola, soy Juan de Logística Sur.", "1 min 35 s", "Saliente",
                 f"/calls/{conv_id}", "apagalo en Mi cuenta"):
        assert text in mail.text, text
    assert "Juan Pérez" in mail.html and "&lt;" not in mail.subject

    run(api)   # ya enviado: no se repite
    assert len(resend) == 1


def test_custom_recipients_and_client_switch(api, admin, resend):
    c = make_client(admin)
    user = client_user(api, admin, c)
    agent = agent_with_summary(admin, c)

    r = user.put(f"{V1}/clients/{c['id']}/call-emails",
                 json={"enabled": True, "recipients": ["Ventas@Acme.com", "ventas@acme.com", "dueno@acme.com"]})
    assert r.status_code == 200, r.text
    assert r.json() == {"enabled": True, "recipients": ["ventas@acme.com", "dueno@acme.com"],
                        "default_recipients": ["ana@acme.com"], "agents": ["Ventas"]}
    conv_id = finished_call(api, admin, agent)
    run(api)
    assert sorted(m.to for m, _ in resend) == ["dueno@acme.com", "ventas@acme.com"]

    # Apagado en el cliente: las que quedaron pendientes no salen.
    assert user.put(f"{V1}/clients/{c['id']}/call-emails", json={"enabled": False}).json()["enabled"] is False
    conv_id = finished_call(api, admin, agent)
    run(api)
    assert status(api, conv_id) == ("skipped", 0) and len(resend) == 2


def test_no_recipients_is_skipped(api, admin, resend):
    c = make_client(admin)   # sin usuarios ni destinos
    conv_id = finished_call(api, admin, agent_with_summary(admin, c))
    run(api)
    assert status(api, conv_id) == ("skipped", 0) and resend == []


def test_retries_with_backoff_then_fails(api, admin, resend):
    c = make_client(admin)
    client_user(api, admin, c)
    conv_id = finished_call(api, admin, agent_with_summary(admin, c))
    resend.results = [SendResult("failed", error="500")] * 4

    run(api)
    assert status(api, conv_id) == ("pending", 1)
    run(api)   # todavia no paso el minuto de espera
    assert status(api, conv_id) == ("pending", 1) and len(resend) == 1
    later = lambda minutes: (lambda: utcnow() + datetime.timedelta(minutes=minutes))  # noqa: E731
    run(api, now=later(2))
    assert status(api, conv_id) == ("pending", 2)
    run(api, now=later(11))
    run(api, now=later(61))
    assert status(api, conv_id) == ("failed", 4) and len(resend) == 4


def test_without_resend_key_is_disabled(api, admin, resend):
    c = make_client(admin)
    client_user(api, admin, c)
    conv_id = finished_call(api, admin, agent_with_summary(admin, c))
    resend.results = [SendResult("disabled")]
    run(api)
    assert status(api, conv_id) == ("disabled", 0)


# ---------- API ----------

def test_call_emails_api_permissions(api, admin):
    c = make_client(admin)
    user = client_user(api, admin, c)
    agent_with_summary(admin, c, on=False)
    r = user.get(f"{V1}/clients/{c['id']}/call-emails")
    assert r.status_code == 200
    assert r.json() == {"enabled": True, "recipients": [], "default_recipients": ["ana@acme.com"], "agents": []}

    other = make_client(admin, "otro")
    assert user.get(f"{V1}/clients/{other['id']}/call-emails").status_code == 404
    assert user.put(f"{V1}/clients/{other['id']}/call-emails", json={"enabled": False}).status_code == 404
    assert admin.put(f"{V1}/clients/{other['id']}/call-emails", json={"enabled": False}).json()["enabled"] is False
    assert user.put(f"{V1}/clients/{c['id']}/call-emails",
                    json={"enabled": True, "recipients": ["no-es-un-email"]}).status_code == 422


# ---------- telefono: precargado si la llamada tiene numero, pedido si es por el link ----------

PHONE_FIELD = {"priority": 15, "label": "Teléfono", "description": "Teléfono de contacto", "type": "phone",
               "required": True, "question": "¿A qué número te llamamos?"}


def agent_with_phone(admin, client):
    d = reference_data("sales_discovery")
    return make_agent(admin, client, definition={**d, "call_summary_email": True,
                                                 "fields": {**d["fields"], "telefono": PHONE_FIELD}})


def fields_of(api, conv_id) -> dict:
    with api.sessions() as s:
        return s.get(ConversationRow, conv_id).fields


def test_phone_type_normalizes():
    from app.conversation.models import FieldSpec
    from app.conversation.workflow import coerce_value

    spec = FieldSpec.model_validate(PHONE_FIELD)
    assert coerce_value(spec, "+54 9 11 5555-1234") == "+5491155551234"
    assert coerce_value(spec, "351 555 1234") == "3515551234"
    assert coerce_value(spec, "no tengo") is None


def test_phone_preloaded_on_inbound_and_outbound_not_on_web(api, admin):
    from app.services import calls as call_service

    c = make_client(admin)
    agent = agent_with_phone(admin, c)
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541152630861", "agent_id": agent["id"]})
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, "+541152630861", "+5493515551234")
    assert fields_of(api, inbound.conversation_id)["telefono"] == "+5493515551234"
    with api.sessions() as s:   # numero oculto: lo pregunta
        hidden = call_service.start_inbound(s, api.engine, "+541152630861", "anonymous")
    assert fields_of(api, hidden.conversation_id)["telefono"] is None

    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+54 9 11 5555-1234"}).json()
    assert fields_of(api, out["conversation_id"])["telefono"] == "+5491155551234"
    state = api.engine.store.get(out["conversation_id"])
    assert state.progress.preloaded == ["telefono"]

    # Sin numero (prueba o link para llamar): queda para preguntar.
    test = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()
    assert fields_of(api, test["conversation_id"])["telefono"] is None


def test_known_phone_goes_to_classic_prompt(api, admin):
    from app.conversation.contact import prompt_block

    c = make_client(admin)
    agent = agent_with_phone(admin, c)
    out = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+54 9 11 5555-1234"}).json()
    block = prompt_block(api.engine.store.get(out["conversation_id"]))
    assert "DATOS YA CONOCIDOS (no los preguntes" in block and "- telefono: +5491155551234" in block


def test_summary_shows_phone_given_on_web_call(api, admin, resend):
    c = make_client(admin)
    client_user(api, admin, c)
    agent = agent_with_phone(admin, c)
    conv_id = finished_call(api, admin, agent)
    with api.sessions() as s:   # como una del link: sin numero, el telefono lo dio la persona
        call = s.get(CallRow, conv_id)
        call.mode, call.phone = CallMode.web, None
        conv = s.get(ConversationRow, conv_id)
        conv.fields = {**conv.fields, "telefono": "+5493515550000"}
        s.commit()
    run(api)
    [(mail, _)] = resend
    assert mail.subject == "Llamada por el link de +5493515550000 a Ventas"
    assert "- Teléfono: +5493515550000" in mail.text
    assert mail.text.count("+5493515550000") == 2   # asunto y fila: no se repite en los datos


def test_summary_web_call_without_phone(api, admin, resend):
    c = make_client(admin)
    client_user(api, admin, c)
    conv_id = finished_call(api, admin, agent_with_summary(admin, c))
    with api.sessions() as s:
        call = s.get(CallRow, conv_id)
        call.mode, call.phone = CallMode.web, None
        s.commit()
    run(api)
    [(mail, _)] = resend
    assert mail.subject == "Llamada por el link a Ventas" and "- Teléfono: No lo dio" in mail.text
