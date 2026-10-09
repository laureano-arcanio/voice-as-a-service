"""Retencion por tier con override por cliente (app/services/retention.py)."""
import datetime
import uuid

from sqlalchemy import select, update

from app.db import utcnow
from app.models import (
    Agent,
    CallRow,
    Client,
    ConversationRow,
    Tier,
    WaAccount,
    WaMessage,
    WaThread,
)
from app.services.retention import purge


def setup(sessions, tier_days=None, client_days=None) -> str:
    with sessions() as s:
        tier = Tier(name=f"T{uuid.uuid4().hex[:6]}", retention_days=tier_days)
        s.add(tier)
        s.flush()
        slug = uuid.uuid4().hex[:8]
        client = Client(name=slug, slug=slug, tier_id=tier.id, retention_days=client_days)
        s.add(client)
        s.commit()
        return client.id


def conversation(sessions, client_id, days_ago: float, call=False, outcome="agendado") -> str:
    cid = str(uuid.uuid4())
    with sessions() as s:
        s.add(ConversationRow(id=cid, client_id=client_id, channel="voice", status="completed",
                              fields={"dni": "30111222"}, messages=[{"role": "user", "text": "soy Ana"}],
                              progress={"outcome": outcome, "undo": {"fields": {"dni": "30111222"}}}))
        s.flush()               # la conversacion antes que su llamada (FK en PostgreSQL)
        if call:
            s.add(CallRow(conversation_id=cid, client_id=client_id, mode="saliente", phone="+5493510000000",
                          status="finalizada", duration_seconds=95))
        s.commit()
        s.execute(update(ConversationRow).where(ConversationRow.id == cid)
                  .values(updated_at=utcnow() - datetime.timedelta(days=days_ago)))
        s.commit()
    return cid


def row(sessions, cid) -> ConversationRow:
    with sessions() as s:
        return s.get(ConversationRow, cid)


def test_tier_borra_lo_viejo_y_conserva_la_llamada(sessions):
    client_id = setup(sessions, tier_days=30)
    old = conversation(sessions, client_id, days_ago=40, call=True)
    recent = conversation(sessions, client_id, days_ago=10)
    assert purge(sessions) == {"conversations": 1, "wa_bodies": 0, "campaign_recipients": 0, "wa_orphans": 0}
    r = row(sessions, old)
    assert (r.messages, r.fields, r.progress) == ([], {}, {"outcome": "agendado"})
    assert r.purged_at is not None
    assert row(sessions, recent).messages == [{"role": "user", "text": "soy Ana"}]
    with sessions() as s:
        call = s.get(CallRow, old)
        assert (call.duration_seconds, call.status) == (95, "finalizada")    # facturacion intacta
    assert not any(purge(sessions).values())                                  # idempotente


def test_override_del_cliente_y_sin_retencion(sessions):
    short = setup(sessions, tier_days=365, client_days=5)
    forever = setup(sessions)
    a = conversation(sessions, short, days_ago=6)
    b = conversation(sessions, forever, days_ago=3000)
    assert purge(sessions)["conversations"] == 1
    assert row(sessions, a).purged_at is not None and row(sessions, b).purged_at is None


def test_whatsapp_cuerpos_y_contacto(sessions):
    client_id = setup(sessions, tier_days=7)
    cid = conversation(sessions, client_id, days_ago=8)
    with sessions() as s:
        client = s.get(Client, client_id)
        agent = Agent(client_id=client.id, slug="a", name="A", definition={})
        s.add(agent)
        s.flush()
        acc = WaAccount(client_id=client_id, agent_id=agent.id, phone_number_id="77", waba_id="1",
                        display_phone_number="+1")
        s.add(acc)
        s.flush()
        s.add(WaThread(conversation_id=cid, account_id=acc.id, client_id=client_id, wa_id="549351",
                       contact_name="Ana"))
        old = utcnow() - datetime.timedelta(days=8)
        s.add(WaMessage(wamid="w.old", account_id=acc.id, direction="in", wa_id="549351", type="text",
                        status="error", body={"msg": {"text": {"body": "mi DNI es 30111222"}}}, created_at=old))
        s.add(WaMessage(wamid="w.new", account_id=acc.id, direction="in", wa_id="549351", type="text",
                        status="received", body={"msg": {"text": {"body": "hola"}}}))
        s.commit()
    assert purge(sessions) == {"conversations": 1, "wa_bodies": 1, "campaign_recipients": 0, "wa_orphans": 0}
    with sessions() as s:
        bodies = {m.wamid: m.body for m in s.scalars(select(WaMessage))}
        assert bodies["w.old"] is None and bodies["w.new"] is not None
        assert s.get(WaThread, cid).contact_name is None
