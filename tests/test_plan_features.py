"""Funciones por plan (docs/FUNCIONES_POR_PLAN_PLAN.md): GET /plan/features y el corte de WhatsApp."""
from app.models import WaAccount
from app.whatsapp.service import WhatsAppService

from .test_api import V1, admin, client_user, make_agent, make_client, make_tier  # noqa: F401  (admin: fixture)
from .test_whatsapp_api import SECRET, account_body, token_key  # noqa: F401  (token_key: fixture)

FREE = dict(name="Free", price_ars=0, outbound_minutes=0, max_phone_numbers=0, campaign_channels=[], whatsapp=False,
            max_contacts=0, max_team_members=0, max_call_links=1)


def features(user, **params):
    r = user.get(f"{V1}/plan/features", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_free_plan_blocks_with_the_plans_that_have_it(api, admin):
    c = make_client(admin, tier=make_tier(admin, **FREE))
    make_tier(admin, name="Central", outbound_minutes=5000, max_phone_numbers=6, campaign_channels=["whatsapp"])
    make_tier(admin, name="Sucursal", price_ars=99000, public=True, sort=2, outbound_minutes=1200, max_phone_numbers=3,
              campaign_channels=["whatsapp"])
    make_tier(admin, name="Mostrador", price_ars=29000, public=True, sort=1, outbound_minutes=300, max_phone_numbers=1,
              campaign_channels=[], max_team_members=0)
    make_tier(admin, name="Otro gratis", price_ars=0)
    out = features(client_user(api, admin, c))
    assert (out["tier_name"], out["free"]) == ("Free", True)
    f = out["features"]
    assert {k for k, v in f.items() if v["enabled"]} == {"call_links"}
    # Los que se venden primero, por su orden; sin el suyo, los gratis ni los que no la tienen.
    assert f["outbound_calls"]["reason"] == ("Disponible en los planes Mostrador, Sucursal y Central, "
                                             "con números asignados.")
    assert f["campaigns_whatsapp"]["reason"] == "Disponible en los planes Sucursal y Central."
    assert f["team"]["reason"] == "Disponible en los planes Sucursal y Central."
    assert f["campaigns_voice"]["reason"] == "Escribinos y la sumamos a tu plan."


def test_paid_plan_without_numbers_has_no_outbound(api, admin):
    c = make_client(admin, outbound_minutes=300, campaign_channels=["voice"])
    f = features(admin, client_id=c["id"])["features"]
    assert f["outbound_calls"] == {"enabled": False, "reason": "Hace falta un número asignado a tu cuenta."}
    assert f["campaigns_voice"]["enabled"] and not f["campaigns_whatsapp"]["enabled"]
    assert f["whatsapp"]["enabled"] and f["team"]["enabled"] and f["contacts"]["enabled"]
    admin.post(f"{V1}/phone-numbers", json={"client_id": c["id"], "e164": "+541152630861"}).raise_for_status()
    assert features(admin, client_id=c["id"])["features"]["outbound_calls"] == {"enabled": True, "reason": None}


def test_adjustment_opens_a_feature(api, admin):
    c = make_client(admin, tier=make_tier(admin, **FREE))
    r = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments",
                   json={"field": "max_team_members", "mode": "set", "value": 2})
    assert r.status_code == 201, r.text
    assert features(admin, client_id=c["id"])["features"]["team"]["enabled"]


def test_admin_needs_client_id(admin):
    assert admin.get(f"{V1}/plan/features").status_code == 422


def test_whatsapp_account_needs_plan(api, admin):
    c = make_client(admin, tier=make_tier(admin, **FREE))
    agent = make_agent(admin, c, template="demo_booking")
    r = admin.post(f"{V1}/whatsapp/accounts", json=account_body(c, agent, access_token=SECRET))
    assert (r.status_code, r.json()["code"]) == (429, "whatsapp_not_in_plan")


def test_messages_ignored_when_plan_drops_whatsapp(api, admin):
    tier = make_tier(admin, name="Pyme")
    c = make_client(admin, tier=tier)
    agent = make_agent(admin, c, template="demo_booking")
    account_id = admin.post(f"{V1}/whatsapp/accounts", json=account_body(c, agent, access_token=SECRET)).json()["id"]
    with api.sessions() as s:
        assert WhatsAppService._why_ignore(None, s, s.get(WaAccount, account_id), "5493510000000") is None
    admin.patch(f"{V1}/tiers/{tier['id']}", json={"whatsapp": False}).raise_for_status()
    with api.sessions() as s:
        assert WhatsAppService._why_ignore(None, s, s.get(WaAccount, account_id), "5493510000000") == "plan sin WhatsApp"
