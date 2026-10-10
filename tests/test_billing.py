"""Registro autoservicio, "olvidé mi clave" y cobro de planes por transferencia
(docs/SUSCRIPCIONES_PLAN.md): pedido, pago registrado por un admin, vencimiento, gracia, caída al
Free con números suspendidos y vuelta al inventario."""
import datetime
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from app.billing import service as billing
from app.config import settings
from app.db import utcnow
from app.models import CallStatus, Client, PhoneNumber, Subscription, User
from app.services import calls as call_service
from app.services import demo, signup
from app.services.errors import QuotaExceeded

from .test_api import V1, admin, make_agent, make_tier  # noqa: F401  (admin: fixture)
from .test_mail import outbox, setup_token  # noqa: F401  (outbox: fixture)

SIGNUP = {"company": "Panadería Doña Rosa", "name": "Rosa Gómez", "email": "Rosa@Example.com",
          "turnstile_token": "ok"}


@pytest.fixture
def plans(admin):
    free = make_tier(admin, name="Free", price_ars=0, public=True, sort=0, max_phone_numbers=0, inbound_minutes=20)
    paid = make_tier(admin, name="Sucursal", price_ars=99000, public=True, sort=2, max_phone_numbers=2)
    small = make_tier(admin, name="Mostrador", price_ars=29000, public=True, sort=1, max_phone_numbers=1)
    hidden = make_tier(admin, name="A medida", price_ars=500000)
    return {"free": free, "paid": paid, "small": small, "hidden": hidden}


@pytest.fixture
def landing(api, plans, monkeypatch, outbox):  # noqa: F811
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    api.turnstile_ok = True

    async def fake_verify(token, ip):
        return api.turnstile_ok

    monkeypatch.setattr(demo, "verify_turnstile", fake_verify)
    monkeypatch.setattr(signup, "verify_turnstile", fake_verify)
    signup.limiter.reset()
    api.outbox = outbox
    api.plans = plans
    return api


def register(api, **extra):
    return api.client.post(f"{V1}/demo/signup", json={**SIGNUP, **extra})


def activate(api, mail) -> "object":
    """Crea la clave con el link del mail: devuelve un TestClient con la sesion."""
    from fastapi.testclient import TestClient

    c = TestClient(api.app)
    r = c.post(f"{V1}/auth/password-setup", json={"token": setup_token(mail), "password": "rosa-password-1"})
    assert r.status_code == 200, r.text
    return c


# ---------- registro ----------

def test_signup_creates_free_client_and_sends_activation(landing):
    r = register(landing)
    assert r.status_code == 202, r.text
    with landing.sessions() as s:
        client = s.scalar(select(Client).where(Client.created_via == "signup"))
        user = s.scalar(select(User).where(User.client_id == client.id))
    assert (client.name, client.slug, client.tier_id) == ("Panadería Doña Rosa", "panaderia_dona_rosa",
                                                          landing.plans["free"]["id"])
    assert user.email == "rosa@example.com" and user.role == "client"
    [mail] = landing.outbox
    assert mail.to == "rosa@example.com" and mail.subject == "Activá tu cuenta de Atentina"
    me = activate(landing, mail).get(f"{V1}/auth/me").json()
    assert me["client_id"] == client.id


def test_signup_with_plan_links_activation_to_plan_page(landing):
    assert register(landing, plan="Sucursal").status_code == 202
    [mail] = landing.outbox
    url = re.search(r"https://\S+/set-password\?\S+", mail.text).group(0)
    assert parse_qs(urlsplit(url).query)["next"] == ["/plan?tier=Sucursal"]
    assert register(landing, email="x@example.com", plan="<script>").status_code == 422


def test_signup_with_existing_email_sends_reset_and_creates_nothing(landing):
    assert register(landing).status_code == 202
    landing.outbox.clear()
    assert register(landing, company="Otra").status_code == 202
    with landing.sessions() as s:
        assert len(s.scalars(select(Client).where(Client.created_via == "signup")).all()) == 1
    [mail] = landing.outbox
    assert mail.subject == "Ya tenés una cuenta en Atentina"
    activate(landing, mail)


def test_signup_slug_is_unique(landing):
    register(landing)
    register(landing, email="otra@example.com")
    with landing.sessions() as s:
        slugs = sorted(s.scalars(select(Client.slug).where(Client.created_via == "signup")))
    assert slugs[0] == "panaderia_dona_rosa" and slugs[1].startswith("panaderia_dona_rosa_")


def test_signup_rejects_bots_and_disposable_emails(landing):
    landing.turnstile_ok = False
    assert register(landing).json()["code"] == "captcha_failed"
    landing.turnstile_ok = True
    assert register(landing, email="x@mailinator.com").json()["code"] == "disposable_email"
    assert register(landing, website="http://spam").status_code == 202   # trampa: no crea nada
    with landing.sessions() as s:
        assert s.scalar(select(Client).where(Client.created_via == "signup")) is None


def test_signup_ip_limit(landing, monkeypatch):
    monkeypatch.setattr(settings, "signup_ip_per_hour", 2)
    assert register(landing, email="a@example.com").status_code == 202
    assert register(landing, email="b@example.com").status_code == 202
    assert register(landing, email="c@example.com").status_code == 429


def test_signup_unavailable_without_free_tier_or_turnstile(api, admin, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret")
    assert register(api).json()["code"] == "signup_unavailable"      # sin tier Free
    make_tier(admin, name="Free", price_ars=0, public=True)
    monkeypatch.setattr(settings, "signup_enabled", False)
    assert register(api).status_code == 503


def test_unactivated_signups_are_purged(landing):
    register(landing)
    register(landing, email="activa@example.com", company="Activa")
    activate(landing, landing.outbox[-1])
    later = utcnow() + datetime.timedelta(hours=settings.password_setup_hours + 1)
    with landing.sessions() as s:
        assert signup.purge_unactivated(s) == 0               # todavia vale el link
        assert signup.purge_unactivated(s, later) == 1
        s.commit()
        assert [c.name for c in s.scalars(select(Client).where(Client.created_via == "signup"))] == ["Activa"]
        assert s.scalar(select(User).where(User.email == "rosa@example.com")) is None


# ---------- olvidé mi clave ----------

def test_password_reset(landing):
    register(landing)
    activate(landing, landing.outbox[-1])
    landing.outbox.clear()
    r = landing.client.post(f"{V1}/auth/password-reset", json={"email": "ROSA@example.com"})
    assert r.status_code == 202
    [mail] = landing.outbox
    assert mail.subject == "Creá una clave nueva"
    assert landing.client.post(f"{V1}/auth/password-reset", json={"email": "nadie@example.com"}).status_code == 202
    assert len(landing.outbox) == 1
    activate(landing, mail)


def test_password_reset_limit_per_email(landing, monkeypatch):
    monkeypatch.setattr(settings, "password_reset_email_per_hour", 1)
    body = {"email": "nadie@example.com"}
    assert landing.client.post(f"{V1}/auth/password-reset", json=body).status_code == 202
    assert landing.client.post(f"{V1}/auth/password-reset", json=body).status_code == 429


# ---------- plan por transferencia ----------

@pytest.fixture
def rosa(landing, monkeypatch):
    """Cliente del registro, con sesion; BANK_TRANSFER_INFO y aviso al admin."""
    monkeypatch.setattr(settings, "bank_transfer_info", "Titular: Atentina\nAlias: atentina.pagos")
    monkeypatch.setattr(settings, "billing_notify_to", "cobros@atentina.com.ar")
    register(landing)
    c = activate(landing, landing.outbox[-1])
    landing.outbox.clear()
    me = c.get(f"{V1}/auth/me").json()
    landing.rosa, landing.rosa_id = c, me["client_id"]
    return landing


def billing_of(api, c=None):
    r = (c or api.rosa).get(f"{V1}/clients/{api.rosa_id}/billing")
    assert r.status_code == 200, r.text
    return r.json()


def test_billing_lists_public_paid_plans(rosa):
    b = billing_of(rosa)
    assert b["tier"]["name"] == "Free" and b["tier_price_ars"] == 0 and b["subscription"] is None
    assert [p["name"] for p in b["plans"]] == ["Mostrador", "Sucursal"]     # ni Free ni el oculto
    assert b["bank"] == [{"label": "Titular", "value": "Atentina"}, {"label": "Alias", "value": "atentina.pagos"}]
    assert b["methods"] == ["transfer"]


def test_subscribe_by_transfer_and_admin_records_payment(rosa, admin):  # noqa: F811
    paid = rosa.plans["paid"]
    r = rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/subscribe", json={"tier_id": paid["id"]})
    assert r.status_code == 200, r.text
    sub = r.json()["subscription"]
    assert (sub["status"], sub["tier"]["name"], sub["amount_due"]) == ("pending", "Sucursal", 99000)
    assert r.json()["tier"]["name"] == "Free"                    # sin pago, sigue en Free
    to = sorted(m.to for m in rosa.outbox)
    assert to == ["cobros@atentina.com.ar", "rosa@example.com"]
    client_mail = next(m for m in rosa.outbox if m.to == "rosa@example.com")
    assert "$ 99.000" in client_mail.text and "atentina.pagos" in client_mail.text

    # Un plan oculto o el Free no se piden; un cliente no registra pagos.
    for tier in (rosa.plans["hidden"], rosa.plans["free"]):
        assert rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/subscribe",
                              json={"tier_id": tier["id"]}).json()["code"] == "invalid_tier"
    pay = {"tier_id": paid["id"], "amount_ars": 99000, "paid_on": str(datetime.date.today()), "note": "Galicia"}
    assert rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/payments", json=pay).status_code == 403

    rosa.outbox.clear()
    r = admin.post(f"{V1}/clients/{rosa.rosa_id}/billing/payments", json=pay)
    assert r.status_code == 201, r.text
    b = r.json()
    today = billing.limits.today()
    assert b["tier"]["name"] == "Sucursal" and b["subscription"]["status"] == "active"
    assert b["subscription"]["current_period_end"] == str(billing.add_month(today))
    assert b["payments"][0]["amount_ars"] == 99000 and b["payments"][0]["recorded_by_email"] == "admin@example.com"
    [mail] = rosa.outbox
    assert mail.subject == "Recibimos tu pago: plan Sucursal"

    # Vista Cobros y marca de facturado.
    rows = admin.get(f"{V1}/billing/subscriptions").json()
    assert [(x["client_name"], x["status"]) for x in rows] == [("Panadería Doña Rosa", "active")]
    [p] = admin.get(f"{V1}/billing/payments", params={"invoiced": False}).json()
    r = admin.patch(f"{V1}/billing/payments/{p['id']}", json={"invoiced": True})
    assert r.json()["invoiced_at"] is not None
    assert admin.get(f"{V1}/billing/payments", params={"invoiced": False}).json() == []

    # Renovacion: suma un mes al vencimiento, no a hoy.
    b = admin.post(f"{V1}/clients/{rosa.rosa_id}/billing/payments", json=pay).json()
    assert b["subscription"]["current_period_end"] == str(billing.add_month(billing.add_month(today)))


def _activate_paid(rosa, admin, tier="paid"):  # noqa: F811
    t = rosa.plans[tier]
    r = admin.post(f"{V1}/clients/{rosa.rosa_id}/billing/payments",
                   json={"tier_id": t["id"], "amount_ars": t["price_ars"], "paid_on": str(datetime.date.today())})
    assert r.status_code == 201, r.text
    return r.json()["subscription"]


def _number(api, admin, e164, agent):  # noqa: F811
    r = admin.post(f"{V1}/phone-numbers", json={"client_id": api.rosa_id, "e164": e164, "agent_id": agent["id"]})
    assert r.status_code == 201, r.text


def _tick(api, days_from_end: int):
    with api.sessions() as s:
        sub = billing.current(s, api.rosa_id) or s.scalars(select(Subscription)).first()
        end = sub.current_period_end
        local = datetime.datetime.combine(end + datetime.timedelta(days=days_from_end), datetime.time(15))
        mails = billing.tick(s, local)
        s.commit()
    return mails


def test_expiry_grace_downgrade_and_number_hold(rosa, admin):  # noqa: F811
    _activate_paid(rosa, admin)
    agent = make_agent(admin, {"id": rosa.rosa_id})
    _number(rosa, admin, "+541152630861", agent)
    _number(rosa, admin, "+541152630862", agent)
    rosa.outbox.clear()

    end = datetime.date.fromisoformat(billing_of(rosa)["subscription"]["current_period_end"])
    assert [m.subject for m in _tick(rosa, -settings.billing_reminder_days)] == [
        f"Tu plan Sucursal vence el {billing.messages.day(end)}"]
    assert _tick(rosa, -settings.billing_reminder_days) == []          # un recordatorio por periodo
    mails = _tick(rosa, 1)
    assert [m.subject for m in mails] == ["No registramos el pago del plan Sucursal"]
    b = billing_of(rosa)
    assert b["subscription"]["status"] == "past_due" and b["tier"]["name"] == "Sucursal"

    mails = _tick(rosa, settings.billing_grace_days + 1)
    assert [m.subject for m in mails] == ["Tu cuenta pasó al plan Free"]
    assert "+541152630861" in mails[0].text
    b = billing_of(rosa)
    assert b["subscription"] is None and b["tier"]["name"] == "Free"
    assert sorted(b["suspended_numbers"]) == ["+541152630861", "+541152630862"]

    # Un numero suspendido no atiende: la entrante queda rechazada.
    with rosa.sessions() as s, pytest.raises(QuotaExceeded) as e:
        call_service.start_inbound(s, rosa.engine, "+541152630861", None)
    assert e.value.code == "number_suspended"
    rejected = admin.get(f"{V1}/calls", params={"status": CallStatus.rechazada}).json()["items"]
    assert rejected[0]["ended_reason"] == "number_suspended"

    # Pagar de nuevo antes del plazo los recupera, hasta el tope del plan (Mostrador: 1).
    _activate_paid(rosa, admin, "small")
    assert len(billing_of(rosa)["suspended_numbers"]) == 1

    # Pasado el plazo, el que sigue suspendido vuelve al inventario.
    with rosa.sessions() as s:
        since = s.scalar(select(PhoneNumber.suspended_at).where(PhoneNumber.suspended_at.is_not(None)))
        billing.tick(s, since + datetime.timedelta(days=settings.billing_number_hold_days - 1))
        assert s.scalar(select(PhoneNumber).where(PhoneNumber.client_id.is_(None))) is None
        billing.tick(s, since + datetime.timedelta(days=settings.billing_number_hold_days + 1))
        s.commit()
        numbers = {n.e164: n.client_id for n in s.scalars(select(PhoneNumber))}
    assert sorted(numbers.values(), key=str) == sorted([rosa.rosa_id, None], key=str)


def test_payment_during_grace_keeps_plan(rosa, admin):  # noqa: F811
    first = _activate_paid(rosa, admin)
    _tick(rosa, 2)
    assert billing_of(rosa)["subscription"]["status"] == "past_due"
    sub = _activate_paid(rosa, admin)
    end = datetime.date.fromisoformat(first["current_period_end"])
    assert sub["status"] == "active" and sub["current_period_end"] == str(billing.add_month(end))


def test_cancel_keeps_plan_until_period_end(rosa, admin):  # noqa: F811
    _activate_paid(rosa, admin)
    b = rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/cancel").json()
    assert b["subscription"]["cancel_at_period_end"] is True and b["tier"]["name"] == "Sucursal"
    assert _tick(rosa, -settings.billing_reminder_days) == []          # sin recordatorio
    assert [m.subject for m in _tick(rosa, 1)] == ["Tu cuenta pasó al plan Free"]   # sin gracia
    assert billing_of(rosa)["tier"]["name"] == "Free"


def test_change_plan_while_active_applies_on_next_payment(rosa, admin):  # noqa: F811
    _activate_paid(rosa, admin)
    b = rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/subscribe",
                       json={"tier_id": rosa.plans["small"]["id"]}).json()
    assert b["tier"]["name"] == "Sucursal"
    assert b["subscription"]["pending_tier"]["name"] == "Mostrador" and b["subscription"]["amount_due"] == 29000


def test_admin_suspend(rosa, admin):  # noqa: F811
    rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/subscribe", json={"tier_id": rosa.plans["paid"]["id"]})
    b = admin.post(f"{V1}/clients/{rosa.rosa_id}/billing/suspend").json()
    assert b["subscription"] is None and b["tier"]["name"] == "Free"
    _activate_paid(rosa, admin)
    b = admin.post(f"{V1}/clients/{rosa.rosa_id}/billing/suspend").json()
    assert b["subscription"] is None and b["tier"]["name"] == "Free"


def test_fiscal_data(rosa):
    url = f"{V1}/clients/{rosa.rosa_id}/billing/fiscal"
    r = rosa.rosa.put(url, json={"legal_name": "Rosa Gómez", "tax_id": "27-12345678-4", "tax_condition": "monotributo"})
    assert r.status_code == 200, r.text
    assert r.json()["fiscal"] == {"legal_name": "Rosa Gómez", "tax_id": "27123456784", "tax_condition": "monotributo"}
    assert rosa.rosa.put(url, json={"legal_name": "X", "tax_id": "123", "tax_condition": "ri"}).status_code == 422


def test_other_client_cannot_see_billing(rosa, admin):  # noqa: F811
    register(rosa, email="otro@example.com", company="Otro")
    other = activate(rosa, rosa.outbox[-1])
    assert other.get(f"{V1}/clients/{rosa.rosa_id}/billing").status_code == 404


@pytest.mark.parametrize(("day", "expected"), [
    (datetime.date(2026, 1, 31), datetime.date(2026, 2, 28)),
    (datetime.date(2026, 12, 15), datetime.date(2027, 1, 15)),
    (datetime.date(2026, 10, 9), datetime.date(2026, 11, 9)),
])
def test_add_month(day, expected):
    assert billing.add_month(day) == expected
