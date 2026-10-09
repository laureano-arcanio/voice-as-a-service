"""Esquema de produccion (0009): tope de llamada y retencion por tier/cliente en la API,
helpers efectivos, defaults de las columnas nuevas y pool de PostgreSQL."""
import pytest
import sqlalchemy as sa

from app.config import settings
from app.db import make_engine
from app.models import (
    CallRow,
    Client,
    ConversationRow,
    Tier,
    WaCampaignRecipient,
    WaMessage,
    effective_max_call_seconds,
    effective_retention_days,
)

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_client,
    make_tier,
)


def test_tier_call_duration_and_retention(api, admin):  # noqa: F811
    tier = make_tier(admin, name="Pro", max_call_duration_seconds=1200, retention_days=90)
    assert (tier["max_call_duration_seconds"], tier["retention_days"]) == (1200, 90)
    assert make_tier(admin, name="Libre")["max_call_duration_seconds"] is None

    for bad in ({"max_call_duration_seconds": 0}, {"retention_days": 0}, {"retention_days": -5},
                {"max_call_duration_seconds": settings.call_duration_ceiling_seconds + 1}):
        assert admin.post(f"{V1}/tiers", json={"name": "x", **bad}).status_code == 422, bad
        assert admin.patch(f"{V1}/tiers/{tier['id']}", json=bad).status_code == 422, bad

    # null: vuelve al del sistema / sin borrado; lo no enviado no cambia.
    upd = admin.patch(f"{V1}/tiers/{tier['id']}", json={"max_call_duration_seconds": None}).json()
    assert (upd["max_call_duration_seconds"], upd["retention_days"]) == (None, 90)
    assert admin.get(f"{V1}/tiers/{tier['id']}").json()["retention_days"] == 90


def test_client_retention_override_and_effective(api, admin):  # noqa: F811
    tier = make_tier(admin, name="Pro", max_call_duration_seconds=600, retention_days=90)
    c = make_client(admin, tier=tier)
    assert c["retention_days"] is None
    assert (c["effective_retention_days"], c["effective_max_call_seconds"]) == (90, 600)

    r = admin.post(f"{V1}/clients", json={"name": "B", "slug": "beta", "tier_id": tier["id"], "retention_days": 30})
    assert r.status_code == 201 and r.json()["effective_retention_days"] == 30
    assert admin.post(f"{V1}/clients", json={"name": "C", "slug": "gama", "tier_id": tier["id"],
                                             "retention_days": 0}).status_code == 422

    upd = admin.patch(f"{V1}/clients/{c['id']}", json={"retention_days": 365}).json()
    assert (upd["retention_days"], upd["effective_retention_days"]) == (365, 365)
    # Otro campo en null no cambia nada; retention_days en null vuelve al del tier.
    assert admin.patch(f"{V1}/clients/{c['id']}", json={"name": None}).json()["retention_days"] == 365
    upd = admin.patch(f"{V1}/clients/{c['id']}", json={"retention_days": None}).json()
    assert (upd["retention_days"], upd["effective_retention_days"]) == (None, 90)

    # Tier sin tope: CALL_MAX_DURATION_SECONDS; sin retencion: None.
    free = make_tier(admin, name="Libre")
    upd = admin.patch(f"{V1}/clients/{c['id']}", json={"tier_id": free["id"]}).json()
    assert upd["effective_retention_days"] is None
    assert upd["effective_max_call_seconds"] == settings.call_max_duration_seconds

    # El usuario del cliente lo ve, pero no lo cambia.
    user = client_user(api, admin, c)
    assert user.get(f"{V1}/clients/{c['id']}").json()["effective_max_call_seconds"] > 0
    assert user.patch(f"{V1}/clients/{c['id']}", json={"retention_days": 1}).status_code == 403


def test_effective_helpers(monkeypatch):
    monkeypatch.setattr(settings, "call_max_duration_seconds", 900)
    monkeypatch.setattr(settings, "call_duration_ceiling_seconds", 3600)
    tier = Tier(name="t", max_call_duration_seconds=None, retention_days=None)
    client = Client(name="c", slug="c", tier=tier, retention_days=None)
    assert effective_max_call_seconds(client) == 900
    assert effective_max_call_seconds(None) == 900          # llamadas sin cliente (admin, plantillas)
    tier.max_call_duration_seconds = 1800
    assert effective_max_call_seconds(client) == 1800
    tier.max_call_duration_seconds = 7200                   # nunca mas que el corte de SIP/Asterisk
    assert effective_max_call_seconds(client) == 3600

    assert effective_retention_days(client) is None
    tier.retention_days = 180
    assert effective_retention_days(client) == 180
    client.retention_days = 30
    assert effective_retention_days(client) == 30


def test_new_column_defaults_and_idempotency_unique(sessions):
    with sessions() as s:
        tier = Tier(name="t")
        client = Client(name="c", slug="c", tier=tier)
        s.add_all([tier, client])
        s.flush()
        for cid in ("v1", "v2"):
            s.add(ConversationRow(id=cid, client_id=client.id, status="active", fields={}, messages=[]))
        s.add(WaMessage(direction="in", wa_id="549351", type="text", status="received",
                        body={"type": "text", "text": "hola"}))
        s.add(CallRow(conversation_id="v1", client_id=client.id, mode="saliente", idempotency_key="k1"))
        s.add(CallRow(conversation_id="v2", client_id=client.id, mode="saliente"))   # sin clave: no choca
        s.commit()
        msg = s.scalars(sa.select(WaMessage)).one()
        assert (msg.attempts, msg.claimed_at, msg.processed_at, msg.body["text"]) == (0, None, None, "hola")
        conv = s.get(ConversationRow, "v1")
        assert (conv.version, conv.purged_at) == (0, None)

        s.get(CallRow, "v2").idempotency_key = "k1"
        with pytest.raises(sa.exc.IntegrityError):
            s.commit()


def test_campaign_recipient_has_claimed_at():
    assert WaCampaignRecipient.__table__.c.claimed_at.nullable


def test_postgres_pool_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "db_pool_size", 7)
    monkeypatch.setattr(settings, "db_max_overflow", 3)
    monkeypatch.setattr(settings, "db_pool_timeout", 4)
    engine = make_engine("postgresql+psycopg://u:p@127.0.0.1:1/x")   # no conecta al crearlo
    assert (engine.pool.size(), engine.pool._max_overflow, engine.pool._timeout) == (7, 3, 4)
    engine.dispose()
    # SQLite no lleva esos parametros (su pool no los acepta).
    make_engine("sqlite://").dispose()
