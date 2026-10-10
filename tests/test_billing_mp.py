"""Plan pago con tarjeta y debito automatico de Mercado Pago (docs/SUSCRIPCIONES_PLAN.md, fase 3), con un
MP falso que responde como el sandbox (6.2): alta con tarjeta, rechazo, cuotas, cambio de plan, baja,
webhook firmado y conciliacion."""
import datetime
import hashlib
import hmac

import pytest
from sqlalchemy import select

from app.billing import mp
from app.billing import service as billing
from app.billing import webhook
from app.config import settings
from app.models import BillingPayment, Subscription

from .test_api import V1, admin  # noqa: F401  (admin: fixture)
from .test_billing import activate, handoff, landing, plans, register  # noqa: F401  (fixtures)
from .test_mail import outbox  # noqa: F401  (fixture)

SECRET = "webhook-secret"


class FakeMP:
    """Guarda las suscripciones; `charge` simula el debito de cada mes."""

    def __init__(self):
        self.subs: dict[str, dict] = {}
        self.payments: dict[str, list[dict]] = {}
        self.calls: list[tuple] = []
        self.next_id = 0
        self.reject_cards = False

    def _pre(self, pid):
        return mp.Preapproval.of(self.subs[pid])

    def create_subscription(self, *, reason, external_reference, payer_email, card_token_id, amount, back_url):
        self.calls.append(("create", external_reference, payer_email, card_token_id, amount))
        if self.reject_cards:
            raise mp.CardRejected("La tarjeta fue rechazada. Probá con otra o revisá los datos.")
        self.next_id += 1
        pid = f"pre{self.next_id}"
        self.subs[pid] = {"id": pid, "status": "authorized", "external_reference": external_reference,
                          "next_payment_date": "2026-11-10T07:28:04.000-04:00",
                          "auto_recurring": {"transaction_amount": amount}}
        self.payments[pid] = []
        self.charge(pid, "2026-10-10T07:28:03.000-04:00")
        return self._pre(pid)

    def charge(self, pid, when, status="approved", next_date=None):
        n = len(self.payments[pid]) + 1
        self.payments[pid].append({"preapproval_id": pid, "status": "processed", "debit_date": when,
                                   "transaction_amount": self.subs[pid]["auto_recurring"]["transaction_amount"],
                                   "payment": {"id": int(f"9{self.next_id}{n}"), "status": status}})
        if next_date:
            self.subs[pid]["next_payment_date"] = next_date

    def get_subscription(self, pid):
        return self._pre(pid)

    def set_amount(self, pid, amount):
        self.calls.append(("amount", pid, amount))
        self.subs[pid]["auto_recurring"]["transaction_amount"] = amount
        return self._pre(pid)

    def cancel(self, pid):
        self.calls.append(("cancel", pid))
        self.subs[pid]["status"] = "cancelled"
        return self._pre(pid)

    def subscription_payments(self, pid):
        return list(self.payments[pid])

    def authorized_payment(self, apid):
        return {"preapproval_id": apid.split(":")[0]}

    def payment(self, payment_id):
        for pid, items in self.payments.items():
            if any(str(p["payment"]["id"]) == str(payment_id) for p in items):
                return {"point_of_interaction": {"transaction_data": {"subscription_id": pid}}}
        return {}


@pytest.fixture
def fake_mp(monkeypatch):
    fake = FakeMP()
    monkeypatch.setattr(billing, "mp_client", lambda: fake)
    monkeypatch.setattr(billing, "wait", lambda seconds: None)
    monkeypatch.setattr(settings, "mp_billing_access_token", "TEST-token")
    monkeypatch.setattr(settings, "mp_billing_public_key", "TEST-pk")
    monkeypatch.setattr(settings, "mp_billing_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "mp_billing_test_payer_email", "")
    return fake


@pytest.fixture
def rosa(landing, fake_mp):  # noqa: F811
    c = activate(landing, register(landing))
    landing.rosa = c
    landing.rosa_id = c.get(f"{V1}/auth/me").json()["client_id"]
    landing.mp = fake_mp
    landing.outbox.clear()
    return landing


def subscribe(api, tier="paid", **extra):
    return api.rosa.post(f"{V1}/clients/{api.rosa_id}/billing/subscribe",
                         json={"tier_id": api.plans[tier]["id"], "method": "mercadopago", **extra})


def billing_of(api):
    return api.rosa.get(f"{V1}/clients/{api.rosa_id}/billing").json()


def test_card_subscription_charges_and_activates(rosa):
    b = billing_of(rosa)
    assert b["methods"] == ["mercadopago", "transfer"] and b["mp_public_key"] == "TEST-pk"
    assert subscribe(rosa).json()["code"] == "card_required"
    r = subscribe(rosa, card_token_id="tok_APRO")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["tier"]["name"] == "Sucursal"
    sub = b["subscription"]
    assert (sub["method"], sub["status"], sub["current_period_end"]) == ("mercadopago", "active", "2026-11-10")
    [p] = b["payments"]
    assert (p["method"], p["amount_ars"], p["paid_on"]) == ("mercadopago", 99000, "2026-10-10")
    [(_, ref, payer, token, amount)] = rosa.mp.calls
    assert (ref, payer, token, amount) == (sub["id"], "rosa@example.com", "tok_APRO", 99000)
    assert [m.subject for m in rosa.outbox] == ["Recibimos tu pago: plan Sucursal"]


def test_rejected_card_leaves_nothing(rosa):
    rosa.mp.reject_cards = True
    r = subscribe(rosa, card_token_id="tok_OTHE")
    assert r.status_code == 422 and r.json()["code"] == "card_rejected"
    b = billing_of(rosa)
    assert b["subscription"] is None and b["tier"]["name"] == "Free"


def test_card_replaces_pending_transfer_request(rosa):
    rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/subscribe",
                   json={"tier_id": rosa.plans["small"]["id"], "method": "transfer"})
    assert billing_of(rosa)["subscription"]["method"] == "transfer"
    b = subscribe(rosa, card_token_id="tok").json()
    assert (b["subscription"]["method"], b["subscription"]["status"]) == ("mercadopago", "active")
    with rosa.sessions() as s:
        assert sorted(x.status for x in s.scalars(select(Subscription))) == ["active", "canceled"]


def test_upgrade_now_downgrade_with_next_payment(rosa):
    subscribe(rosa, tier="small", card_token_id="tok")
    b = subscribe(rosa, tier="paid").json()   # subida: ya, sin tarjeta
    assert b["tier"]["name"] == "Sucursal" and b["subscription"]["amount_due"] == 99000
    b = subscribe(rosa, tier="small").json()  # bajada: con el proximo pago
    assert b["tier"]["name"] == "Sucursal" and b["subscription"]["pending_tier"]["name"] == "Mostrador"
    assert [c[2] for c in rosa.mp.calls if c[0] == "amount"] == [99000, 29000]
    pid = next(iter(rosa.mp.subs))
    rosa.mp.charge(pid, "2026-11-10T07:28:03.000-04:00", next_date="2026-12-10T07:28:04.000-04:00")
    with rosa.sessions() as s:
        billing.sync(s, billing.by_preapproval(s, pid))
        s.commit()
    b = billing_of(rosa)
    assert b["tier"]["name"] == "Mostrador" and b["subscription"]["current_period_end"] == "2026-12-10"
    assert b["subscription"]["pending_tier"] is None


def test_cancel_keeps_plan_until_period_end(rosa):
    subscribe(rosa, card_token_id="tok")
    b = rosa.rosa.post(f"{V1}/clients/{rosa.rosa_id}/billing/cancel").json()
    assert b["subscription"]["cancel_at_period_end"] is True and b["tier"]["name"] == "Sucursal"
    assert ("cancel", "pre1") in rosa.mp.calls
    with rosa.sessions() as s:
        billing.tick(s, datetime.datetime(2026, 11, 12, 15))
        s.commit()
    assert billing_of(rosa)["tier"]["name"] == "Free"


def test_unpaid_month_goes_past_due_then_free_and_cancels_in_mp(rosa):
    subscribe(rosa, card_token_id="tok")
    pid = "pre1"
    rosa.mp.charge(pid, "2026-11-10T07:28:03.000-04:00", status="rejected")
    with rosa.sessions() as s:
        assert billing.reconcile(s, datetime.datetime(2026, 11, 11, 15)) == []   # pago rechazado: sin mail de pago
        billing.tick(s, datetime.datetime(2026, 11, 11, 15))
        s.commit()
        assert len(s.scalars(select(BillingPayment).where(BillingPayment.status == "rejected")).all()) == 1
    assert billing_of(rosa)["subscription"]["status"] == "past_due"
    with rosa.sessions() as s:
        billing.tick(s, datetime.datetime(2026, 11, 20, 15))
        s.commit()
    assert billing_of(rosa)["tier"]["name"] == "Free"
    assert ("cancel", pid) in rosa.mp.calls


def test_payment_during_grace_reactivates(rosa):
    subscribe(rosa, card_token_id="tok")
    with rosa.sessions() as s:
        billing.tick(s, datetime.datetime(2026, 11, 12, 15))
        s.commit()
    assert billing_of(rosa)["subscription"]["status"] == "past_due"
    rosa.mp.charge("pre1", "2026-11-13T07:28:03.000-04:00", next_date="2026-12-13T07:28:04.000-04:00")
    with rosa.sessions() as s:
        billing.reconcile(s, datetime.datetime(2026, 11, 13, 15))
        s.commit()
    sub = billing_of(rosa)["subscription"]
    assert (sub["status"], sub["current_period_end"], sub["grace_until"]) == ("active", "2026-12-13", None)


def test_mp_cancellation_ends_plan_at_period_end(rosa):
    subscribe(rosa, card_token_id="tok")
    rosa.mp.subs["pre1"]["status"] = "cancelled"
    with rosa.sessions() as s:
        billing.sync(s, billing.by_preapproval(s, "pre1"))
        s.commit()
    assert billing_of(rosa)["subscription"]["cancel_at_period_end"] is True


def test_payments_are_recorded_once(rosa):
    subscribe(rosa, card_token_id="tok")
    with rosa.sessions() as s:
        for _ in range(3):
            billing.sync(s, billing.by_preapproval(s, "pre1"))
        s.commit()
        assert len(s.scalars(select(BillingPayment)).all()) == 1


def test_transfer_payment_conflicts_with_card_plan(rosa, admin):  # noqa: F811
    subscribe(rosa, card_token_id="tok")
    r = admin.post(f"{V1}/clients/{rosa.rosa_id}/billing/payments",
                   json={"tier_id": rosa.plans["paid"]["id"], "amount_ars": 1, "paid_on": "2026-10-10"})
    assert r.json()["code"] == "method_mismatch"


def test_without_credentials_card_is_not_offered(rosa, monkeypatch):
    monkeypatch.setattr(settings, "mp_billing_access_token", "")
    b = billing_of(rosa)
    assert b["methods"] == ["transfer"] and b["mp_public_key"] is None
    assert subscribe(rosa, card_token_id="tok").json()["code"] == "method_unavailable"


# ---------- webhook ----------

def sign(data_id: str, request_id: str = "req-1", ts: str = "1728561000", secret: str = SECRET) -> dict:
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


def test_signature():
    headers = sign("123")
    assert mp.valid_signature(headers["x-signature"], "req-1", "123", SECRET)
    assert not mp.valid_signature(headers["x-signature"], "req-1", "124", SECRET)
    assert not mp.valid_signature(headers["x-signature"], "req-2", "123", SECRET)
    assert not mp.valid_signature(headers["x-signature"], "req-1", "123", "")
    assert not mp.valid_signature(None, "req-1", "123", SECRET)
    # Un id alfanumerico se firma en minusculas.
    assert mp.valid_signature(sign("abc")["x-signature"], "req-1", "ABC", SECRET)


def test_webhook_rejects_bad_signature(rosa):
    r = rosa.client.post("/mp/billing/webhook?type=payment&data.id=1", json={"type": "payment", "data": {"id": "1"}},
                         headers={"x-signature": "ts=1,v1=00", "x-request-id": "r"})
    assert r.status_code == 401


def test_webhook_payment_renews_subscription(rosa, monkeypatch):
    subscribe(rosa, card_token_id="tok")
    rosa.mp.charge("pre1", "2026-11-10T07:28:03.000-04:00", next_date="2026-12-10T07:28:04.000-04:00")
    payment_id = str(rosa.mp.payments["pre1"][-1]["payment"]["id"])
    monkeypatch.setattr(webhook, "get_sessionmaker", lambda: rosa.sessions)
    processed = []
    monkeypatch.setattr(webhook.asyncio, "to_thread", lambda fn, *a: _done(processed.append((fn, a))))
    r = rosa.client.post(f"/mp/billing/webhook?type=payment&data.id={payment_id}",
                         json={"type": "payment", "data": {"id": payment_id}}, headers=sign(payment_id))
    assert r.status_code == 200
    [(fn, args)] = processed
    fn(*args)   # lo que corre en segundo plano
    sub = billing_of(rosa)["subscription"]
    assert sub["current_period_end"] == "2026-12-10" and len(billing_of(rosa)["payments"]) == 2


async def _done(_):
    return None


def test_subscription_is_kept_if_sync_fails_after_creating_it_in_mp(rosa, monkeypatch):
    def broken(pid):
        raise mp.Invalid("Mercado Pago rechazó la operación.", "mp_rejected")
    monkeypatch.setattr(rosa.mp, "subscription_payments", broken)
    r = subscribe(rosa, card_token_id="tok")
    assert r.status_code == 200, r.text
    assert r.json()["subscription"]["status"] == "pending"     # la activa la conciliacion
    monkeypatch.undo()
    monkeypatch.setattr(billing, "mp_client", lambda: rosa.mp)
    monkeypatch.setattr(settings, "mp_billing_access_token", "TEST-token")
    monkeypatch.setattr(settings, "mp_billing_public_key", "TEST-pk")
    with rosa.sessions() as s:
        billing.reconcile(s)
        s.commit()
    assert billing_of(rosa)["subscription"]["status"] == "active"


def test_first_charge_that_arrives_late_still_activates(rosa, monkeypatch):
    """En el sandbox el primer cobro aparece un instante despues del alta."""
    real = rosa.mp.subscription_payments
    calls = []

    def late(pid):
        calls.append(pid)
        return [] if len(calls) == 1 else real(pid)
    monkeypatch.setattr(rosa.mp, "subscription_payments", late)
    b = subscribe(rosa, card_token_id="tok").json()
    assert b["subscription"]["status"] == "active" and len(calls) == 2


# ---------- pago en el registro (paso 2 de la landing) ----------

def test_public_plans_for_the_landing(landing, fake_mp):
    r = landing.client.get(f"{V1}/demo/plans").json()
    assert r["mp_public_key"] == "TEST-pk"
    assert [(p["name"], p["price_ars"]) for p in r["plans"]] == [("Mostrador", 29000), ("Sucursal", 99000)]


def test_signup_check_email(landing, fake_mp):
    url = f"{V1}/demo/signup/check"
    assert landing.client.post(url, json={"email": "nueva@example.com"}).status_code == 204
    register(landing)
    assert landing.client.post(url, json={"email": "ROSA@example.com"}).json()["code"] == "email_taken"
    assert landing.client.post(url, json={"email": "x@yopmail.com"}).json()["code"] == "disposable_email"


def test_signup_with_paid_plan_pays_and_creates_account(landing, fake_mp):
    assert register(landing, plan="Sucursal").json()["code"] == "card_required"
    r = register(landing, plan="Sucursal", card_token_id="tok_APRO")
    token, next_path = handoff(r)
    assert next_path == "/"                                      # al inicio, con el plan activo
    c = activate(landing, r)
    client_id = c.get(f"{V1}/auth/me").json()["client_id"]
    b = c.get(f"{V1}/clients/{client_id}/billing").json()
    assert b["tier"]["name"] == "Sucursal" and b["subscription"]["status"] == "active"
    assert [m.subject for m in landing.outbox] == ["Tu cuenta de Atentina está lista",
                                                   "Recibimos tu pago: plan Sucursal"]
    assert "plan Sucursal" in landing.outbox[0].text
    [(_, ref, payer, card, amount)] = fake_mp.calls
    assert (ref, payer, card, amount) == (b["subscription"]["id"], "rosa@example.com", "tok_APRO", 99000)


def test_signup_with_rejected_card_creates_nothing(landing, fake_mp):
    fake_mp.reject_cards = True
    r = register(landing, plan="Sucursal", card_token_id="tok_OTHE")
    assert r.status_code == 422 and r.json()["code"] == "card_rejected"
    with landing.sessions() as s:
        assert s.scalar(select(Subscription)) is None
        from app.models import Client, User
        assert s.scalar(select(Client).where(Client.created_via == "signup")) is None
        assert s.scalar(select(User).where(User.email == "rosa@example.com")) is None
    fake_mp.reject_cards = False
    assert handoff(register(landing, plan="Sucursal", card_token_id="tok_APRO"))[1] == "/"   # reintento


def test_signup_cancels_mp_subscription_if_account_is_not_saved(landing, fake_mp, monkeypatch):
    from sqlalchemy.orm import Session

    real_commit = Session.commit

    def failing_commit(self):
        if fake_mp.subs:   # despues de crear la suscripcion en MP
            raise RuntimeError("base caida")
        return real_commit(self)
    monkeypatch.setattr(Session, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        register(landing, plan="Sucursal", card_token_id="tok_APRO")
    assert ("cancel", "pre1") in fake_mp.calls
