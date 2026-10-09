"""Ajustes de limites por cliente (services/limits.py): la resolucion sobre el tier, que lo
apliquen la admision de llamadas, los numeros y la API de inferencia, y los endpoints de admin."""
import datetime

import pytest
from sqlalchemy import inspect

from app.api.schemas import LimitField
from app.models import (
    CallMode,
    CallRow,
    CallStatus,
    Client,
    ClientLimitAdjustment,
    Tier,
)
from app.services import api_usage, limits
from app.services.errors import Forbidden

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
    make_tier,
)

DAY = datetime.date(2026, 10, 15)


def adj(field, mode, value, starts_on=None, ends_on=None, n=0) -> ClientLimitAdjustment:
    return ClientLimitAdjustment(id=f"a{n}", field=field, mode=mode, value=value, starts_on=starts_on, ends_on=ends_on,
                                 created_at=datetime.datetime(2026, 10, 1, 0, n, tzinfo=datetime.UTC).replace(tzinfo=None))


def resolve(tier_kwargs, *adjustments, day=DAY) -> limits.Limits:
    return limits.apply(Tier(name="Pyme", **tier_kwargs), adjustments, day)


# ---------- resolucion ----------

def test_limit_fields_are_the_numeric_limits_of_tier():
    numeric = {c.name for c in inspect(Tier).columns if c.name not in
               {"id", "name", "description", "created_at", "updated_at"}}
    assert set(limits.LIMIT_FIELDS) == numeric
    assert set(LimitField.__args__) == numeric
    assert {f for f in limits.Limits.__dataclass_fields__} - {"tier_name", "adjusted"} == numeric


def test_without_adjustments_it_is_the_tier():
    r = resolve({"inbound_minutes": 100, "max_phone_numbers": None})
    assert (r.inbound_minutes, r.max_phone_numbers, r.tier_name, r.adjusted) == (100, None, "Pyme", frozenset())


def test_add_stacks_and_set_replaces():
    r = resolve({"inbound_minutes": 100},
                adj("inbound_minutes", "add", 10, n=1), adj("inbound_minutes", "add", 5, n=2))
    assert r.inbound_minutes == 115 and r.adjusted == {"inbound_minutes"}
    # set reemplaza el valor del tier; el ultimo set gana; los add se suman encima.
    r = resolve({"inbound_minutes": 100},
                adj("inbound_minutes", "set", 500, n=1), adj("inbound_minutes", "set", 300, n=2),
                adj("inbound_minutes", "add", 10, n=3))
    assert r.inbound_minutes == 310


def test_set_null_is_unlimited_and_add_over_unlimited_is_ignored():
    r = resolve({"inbound_minutes": 100}, adj("inbound_minutes", "set", None), adj("inbound_minutes", "add", 10, n=1))
    assert r.inbound_minutes is None
    r = resolve({"inbound_minutes": None}, adj("inbound_minutes", "add", 10))
    assert r.inbound_minutes is None and r.adjusted == frozenset()


def test_add_over_not_included_makes_it_included():
    assert resolve({"api_tts_minutes": 0}, adj("api_tts_minutes", "add", 30)).api_tts_minutes == 30


@pytest.mark.parametrize(("starts_on", "ends_on", "applies"), [
    (None, None, True),
    (DAY, DAY, True),                                              # los extremos son inclusivos
    (DAY - datetime.timedelta(days=3), DAY + datetime.timedelta(days=3), True),
    (DAY + datetime.timedelta(days=1), None, False),               # todavia no empezo
    (None, DAY - datetime.timedelta(days=1), False),               # ya vencio
])
def test_adjustment_window(starts_on, ends_on, applies):
    r = resolve({"inbound_minutes": 100}, adj("inbound_minutes", "add", 10, starts_on, ends_on))
    assert r.inbound_minutes == (110 if applies else 100)


# ---------- aplicacion ----------

def _client(s, **tier_limits) -> Client:
    client = Client(name="C", slug="c", tier=Tier(name="t", **tier_limits))
    s.add(client)
    s.flush()
    return client


def test_inference_check_uses_adjustments(sessions):
    with sessions() as s:
        c = _client(s, api_tts_minutes=0)
        with pytest.raises(Forbidden) as e:
            api_usage.check(s, c, "tts")
        assert e.value.code == "not_in_plan"
        s.add(ClientLimitAdjustment(client_id=c.id, field="api_tts_minutes", mode="add", value=5))
        s.flush()
        assert api_usage.check(s, c, "tts").seconds == 300
        assert api_usage.usage(s, c).tts_minutes.limit == 5


def test_call_admission_sees_extra_minutes(api, admin):
    c = make_client(admin, outbound_minutes=1)
    agent = make_agent(admin, c)
    call = {"agent_id": agent["id"], "phone": "+5491155551234"}
    assert admin.post(f"{V1}/calls", json=call).status_code == 201
    with api.sessions() as s:    # consumio el minuto del tier
        s.query(CallRow).update({"status": CallStatus.finalizada, "duration_seconds": 60,
                                 "started_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None)})
        s.commit()
    r = admin.post(f"{V1}/calls", json=call)
    assert r.status_code == 429 and r.json()["code"] == "outbound_minutes"

    r = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments",
                   json={"field": "outbound_minutes", "mode": "add", "value": 2, "note": "regalo"})
    assert r.status_code == 201
    r = admin.post(f"{V1}/calls", json=call)
    assert r.status_code == 201
    assert api.dispatched[-1]["max_duration_seconds"] == 120    # 3 min en total - 1 usado

    # Otro cliente del mismo tier no se entera.
    other = make_client(admin, "otro", tier=c["tier"])
    assert admin.get(f"{V1}/clients/{other['id']}/usage").json()["outbound"]["limit_minutes"] == 1


def test_phone_numbers_extra_line(api, admin):
    c = make_client(admin, max_phone_numbers=1)
    first, second = admin.post(f"{V1}/phone-numbers/bulk",
                               json={"numbers": ["+541100000001", "+541100000002"]}).json()["created"]
    assert admin.post(f"{V1}/phone-numbers/{first['id']}/assign", json={"client_id": c["id"]}).status_code == 200
    r = admin.post(f"{V1}/phone-numbers/{second['id']}/assign", json={"client_id": c["id"]})
    assert r.status_code == 409 and r.json()["code"] == "phone_numbers_limit"

    r = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json={"field": "max_phone_numbers", "mode": "add",
                                                                      "value": 1})
    assert r.status_code == 201
    assert admin.post(f"{V1}/phone-numbers/{second['id']}/assign", json={"client_id": c["id"]}).status_code == 200
    assert admin.get(f"{V1}/clients/{c['id']}/usage").json()["phone_numbers"] == {"used": 2, "limit": 2}

    # Quitar la linea extra con los dos numeros asignados se rechaza, y el ajuste queda.
    adj_id = r.json()["adjustments"][0]["id"]
    r = admin.delete(f"{V1}/clients/{c['id']}/limit-adjustments/{adj_id}")
    assert r.status_code == 409 and r.json()["code"] == "phone_numbers_limit"
    assert len(admin.get(f"{V1}/clients/{c['id']}/limits").json()["adjustments"]) == 1
    # Un tope propio por debajo de lo que tiene tambien.
    r = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json={"field": "max_phone_numbers", "mode": "set",
                                                                      "value": 0})      # 0 + la linea extra = 1
    assert r.status_code == 409
    assert len(admin.get(f"{V1}/clients/{c['id']}/limits").json()["adjustments"]) == 1


def test_changing_tier_keeps_adjustments_and_checks_numbers(api, admin):
    c = make_client(admin, max_phone_numbers=1)
    admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json={"field": "max_phone_numbers", "mode": "add",
                                                                  "value": 1})
    for n in admin.post(f"{V1}/phone-numbers/bulk", json={"numbers": ["+541100000001", "+541100000002"]}).json()["created"]:
        admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": c["id"]})
    same = make_tier(admin, name="Igual", max_phone_numbers=1)
    assert admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": same["id"]}).status_code == 200
    # Bajar el tier a 0 con el ajuste (+1) deja 1: menos que los 2 asignados.
    zero = make_tier(admin, name="Cero", max_phone_numbers=0)
    r = admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": zero["id"]})
    assert r.status_code == 409 and r.json()["code"] == "phone_numbers_limit"
    # Subir el tope del tier para todos no necesita revisar los ajustes y se acepta.
    assert admin.patch(f"{V1}/tiers/{same['id']}", json={"max_phone_numbers": 5}).status_code == 200


# ---------- endpoints ----------

def test_limits_view_and_adjustments_lifecycle(api, admin):
    c = make_client(admin, inbound_minutes=100)
    assert c["adjustments_count"] == 0
    view = admin.get(f"{V1}/clients/{c['id']}/limits").json()
    row = next(r for r in view["limits"] if r["field"] == "inbound_minutes")
    assert row == {"field": "inbound_minutes", "tier": 100, "effective": 100} and view["adjustments"] == []

    r = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments",
                   json={"field": "inbound_minutes", "mode": "add", "value": 10, "note": "  promo octubre "})
    assert r.status_code == 201, r.text
    created = r.json()["adjustments"][0]
    assert (created["status"], created["note"], created["created_by_email"]) == ("active", "promo octubre",
                                                                                  "admin@example.com")
    assert next(x for x in r.json()["limits"] if x["field"] == "inbound_minutes")["effective"] == 110
    assert admin.get(f"{V1}/clients/{c['id']}").json()["adjustments_count"] == 1
    assert admin.get(f"{V1}/clients/{c['id']}/usage").json()["inbound"]["limit_minutes"] == 110

    r = admin.delete(f"{V1}/clients/{c['id']}/limit-adjustments/{created['id']}")
    assert r.status_code == 200 and r.json()["adjustments"] == []
    assert admin.get(f"{V1}/clients/{c['id']}/usage").json()["inbound"]["limit_minutes"] == 100
    assert admin.delete(f"{V1}/clients/{c['id']}/limit-adjustments/{created['id']}").status_code == 404


def test_scheduled_and_expired_adjustments_are_listed_but_not_applied(api, admin):
    c = make_client(admin, inbound_minutes=100)
    today = limits.today()
    day = datetime.timedelta(days=1)
    for starts, ends in [(today + day, None), (None, today - day)]:
        r = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json={
            "field": "inbound_minutes", "mode": "add", "value": 50,
            "starts_on": starts and starts.isoformat(), "ends_on": ends and ends.isoformat()})
        assert r.status_code == 201, r.text
    view = admin.get(f"{V1}/clients/{c['id']}/limits").json()
    assert sorted(a["status"] for a in view["adjustments"]) == ["expired", "scheduled"]
    assert next(x for x in view["limits"] if x["field"] == "inbound_minutes")["effective"] == 100
    assert admin.get(f"{V1}/clients/{c['id']}").json()["adjustments_count"] == 0


def test_validation(api, admin):
    c = make_client(admin, inbound_minutes=100, outbound_minutes=None)
    url = f"{V1}/clients/{c['id']}/limit-adjustments"
    ok = {"field": "inbound_minutes", "mode": "add", "value": 10}
    assert admin.post(url, json={**ok, "value": None}).status_code == 422          # add sin cantidad
    assert admin.post(url, json={**ok, "value": 0}).status_code == 422
    assert admin.post(url, json={**ok, "value": -5}).status_code == 422
    assert admin.post(url, json={**ok, "field": "name"}).status_code == 422        # no es un limite
    assert admin.post(url, json={**ok, "mode": "multiply"}).status_code == 422
    assert admin.post(url, json={**ok, "starts_on": "2026-10-10", "ends_on": "2026-10-01"}).status_code == 422
    # Sumar a un limite que ya es ilimitado no haria nada: se avisa.
    r = admin.post(url, json={"field": "outbound_minutes", "mode": "add", "value": 10})
    assert r.status_code == 422 and r.json()["code"] == "already_unlimited"
    # set sin cantidad es ilimitado: valido.
    assert admin.post(url, json={"field": "inbound_minutes", "mode": "set", "value": None}).status_code == 201
    assert admin.get(f"{V1}/clients/{c['id']}/usage").json()["inbound"]["limit_minutes"] is None
    assert admin.post(f"{V1}/clients/nope/limit-adjustments", json=ok).status_code == 404


def test_only_admin_manages_adjustments(api, admin):
    c = make_client(admin, inbound_minutes=100)
    user = client_user(api, admin, c)
    body = {"field": "inbound_minutes", "mode": "add", "value": 10}
    assert user.get(f"{V1}/clients/{c['id']}/limits").status_code == 403
    assert user.post(f"{V1}/clients/{c['id']}/limit-adjustments", json=body).status_code == 403
    adj_id = admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json=body).json()["adjustments"][0]["id"]
    assert user.delete(f"{V1}/clients/{c['id']}/limit-adjustments/{adj_id}").status_code == 403
    # Pero ve el limite efectivo en su consumo.
    assert user.get(f"{V1}/clients/{c['id']}/usage").json()["inbound"]["limit_minutes"] == 110


def test_call_modes_unaffected(api, admin):
    """Las de prueba no consumen minutos aunque haya ajustes (la regla del tier se mantiene)."""
    c = make_client(admin, inbound_minutes=1)
    admin.post(f"{V1}/clients/{c['id']}/limit-adjustments", json={"field": "inbound_minutes", "mode": "add", "value": 1})
    with api.sessions() as s:
        client = s.get(Client, c["id"])
        from app.services import quota
        assert quota.remaining_seconds(s, client, CallMode.prueba) is None
        assert quota.remaining_seconds(s, client, CallMode.entrante) == 120
