"""Concurrencia real en PostgreSQL (revision de produccion del 7-oct-2026): lo que SQLite no
puede probar porque no tiene FOR UPDATE, locks consultivos ni la FK compuesta de la 0009.

Solo corren con TEST_DB_DSN=postgresql+psycopg://... contra una base DESCARTABLE: cada test
borra el esquema public y lo vuelve a crear con las migraciones (alembic upgrade head).
    docker run --rm -d --name vaas-test-pg -e POSTGRES_PASSWORD=test -p 127.0.0.1:55432:5432 postgres:16-alpine
    TEST_DB_DSN=postgresql+psycopg://postgres:test@127.0.0.1:55432/postgres pytest tests/test_prod_postgres.py
    docker rm -f vaas-test-pg
"""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa
from alembic import command

from app.agents.templates import reference_data
from app.config import settings
from app.conversation.store import ConversationConflict, ConversationStore
from app.db import make_engine, make_sessions, utcnow
from app.models import (
    CallMode,
    CallRow,
    CallStatus,
    Client,
    ConversationRow,
    PhoneNumber,
    Tier,
)
from app.services import agents as agent_service
from app.services import phone_numbers, quota
from app.services.errors import QuotaExceeded
from app.whatsapp.sender import CampaignSender

from .test_migration_0005 import _run
from .test_whatsapp_campaigns import make_campaign, recipients
from .test_whatsapp_service import make_wa

DSN = os.getenv("TEST_DB_DSN") or ""
pytestmark = pytest.mark.skipif(not DSN.startswith("postgresql"), reason="solo PostgreSQL (TEST_DB_DSN)")

# Tope de espera de un hilo bloqueado por un lock: si se pasa, el test falla en vez de colgarse.
LOCK_WAIT = 10


@pytest.fixture
def pg():
    """sessionmaker sobre el esquema de las migraciones (con la FK compuesta de la 0009)."""
    engine = make_engine(DSN)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    _run(engine, command.upgrade, "head")
    yield make_sessions(engine)
    engine.dispose()


def _seed(sessions) -> dict:
    """Dos clientes con un agente cada uno y un numero de c1 ruteado a su agente."""
    with sessions() as s:
        tier = Tier(name="T")
        s.add(tier)
        s.flush()
        ids = {}
        for slug in ("c1", "c2"):
            client = Client(name=slug, slug=slug, tier_id=tier.id)
            s.add(client)
            s.flush()
            agent = agent_service.create_agent(s, client, name=f"A {slug}", slug=f"a_{slug}", description="",
                                               definition=reference_data("demo_booking_classic"),
                                               template_id=None, user_id=None)
            s.flush()
            ids[slug], ids[f"a_{slug}"] = client.id, agent.id
        number = PhoneNumber(e164="+5493515550000", label="", provider="anura", client_id=ids["c1"],
                             agent_id=ids["a_c1"], assigned_at=utcnow())
        s.add(number)
        s.commit()
        ids["number"] = number.id
    return ids


# ---------- H01: reasignar un numero mientras el cliente lo rutea ----------

def test_lock_del_numero_serializa_y_detecta_el_cambio_de_cliente(pg):
    ids = _seed(pg)
    with pg() as admin, pg() as user:
        # El PATCH del cliente lee el numero (todavia de c1)...
        n_user = user.get(PhoneNumber, ids["number"])
        assert n_user.client_id == ids["c1"]
        user.commit()   # get_principal hace commit: la lectura no retiene nada
        # ...y el admin lo libera, con lock, sin commit todavia.
        n_admin = admin.get(PhoneNumber, ids["number"])
        phone_numbers.release(admin, n_admin)
        admin.flush()

        result = {}

        def patch():
            result["changed"] = phone_numbers.lock(user, n_user)

        t = threading.Thread(target=patch)
        t.start()
        t.join(0.5)
        assert t.is_alive(), "el lock del PATCH tiene que esperar al del admin"
        admin.commit()
        t.join(LOCK_WAIT)
        assert not t.is_alive()
        # Al tomar el lock relee: el numero ya no es de c1 (el router responde 404/409).
        assert result["changed"] is True
        assert n_user.client_id is None and n_user.agent_id is None
        user.rollback()


def test_fk_compuesta_impide_rutear_al_agente_de_otro_cliente(pg):
    ids = _seed(pg)
    with pg() as s:     # sin agente: el PATCH del cliente lo va a elegir
        s.get(PhoneNumber, ids["number"]).agent_id = None
        s.commit()
    with pg() as admin, pg() as user:
        # Camino viejo (sin lock): el cliente valida contra lo que leyo...
        n_user = user.get(PhoneNumber, ids["number"])
        user.commit()
        # ...mientras el admin pasa el numero a c2.
        n_admin = admin.get(PhoneNumber, ids["number"])
        phone_numbers.release(admin, n_admin)
        admin.flush()
        phone_numbers.assign(admin, n_admin, ids["c2"])
        admin.commit()
        # El UPDATE con el agente de c1 sobre un numero que ya es de c2: la base lo rechaza.
        n_user.agent_id = ids["a_c1"]
        with pytest.raises(sa.exc.IntegrityError):
            user.flush()
        user.rollback()
    with pg() as s:
        n = s.get(PhoneNumber, ids["number"])
        assert (n.client_id, n.agent_id) == (ids["c2"], None)
        # Y por SQL directo tampoco se puede mezclar.
        with pytest.raises(sa.exc.IntegrityError):
            s.execute(sa.update(PhoneNumber).where(PhoneNumber.id == n.id).values(agent_id=ids["a_c1"]))
            s.flush()
        s.rollback()


def test_release_que_espera_un_assign_da_conflicto(pg):
    """Dos admins: uno pasa el numero a c2 mientras el otro (que lo leyo de c1) lo libera."""
    ids = _seed(pg)
    with pg() as a, pg() as b:
        n_b = b.get(PhoneNumber, ids["number"])
        b.commit()
        n_a = a.get(PhoneNumber, ids["number"])
        phone_numbers.release(a, n_a)
        a.flush()
        phone_numbers.assign(a, n_a, ids["c2"])
        result = {}

        def release_b():
            try:
                phone_numbers.release(b, n_b)
                result["ok"] = True
            except Exception as e:  # noqa: BLE001 - se compara abajo
                result["error"] = e

        t = threading.Thread(target=release_b)
        t.start()
        t.join(0.5)
        assert t.is_alive()
        a.commit()
        t.join(LOCK_WAIT)
        assert getattr(result.get("error"), "code", None) == "number_changed"
        b.rollback()
    with pg() as s:
        assert s.get(PhoneNumber, ids["number"]).client_id == ids["c2"]


# ---------- H04: admision global con clientes concurrentes ----------

def test_admision_global_concurrente_no_supera_el_tope(pg, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_calls_global", 3)
    monkeypatch.setattr(settings, "inbound_reserve_calls", 0)
    ids = _seed(pg)
    attempts = 12
    barrier = threading.Barrier(attempts)

    def call(i: int) -> str:
        client_id = ids["c1"] if i % 2 else ids["c2"]
        barrier.wait(LOCK_WAIT)
        with pg() as s:
            try:
                quota.admit(s, client_id, CallMode.prueba)
            except QuotaExceeded as e:
                s.rollback()
                return e.code
            # Dentro del lock: la siguiente admision tiene que ver esta llamada.
            time.sleep(0.05)
            conv_id = f"conv-{i}"
            s.add(ConversationRow(id=conv_id, client_id=client_id, status="active", fields={}, messages=[]))
            s.flush()
            s.add(CallRow(conversation_id=conv_id, client_id=client_id, mode=CallMode.prueba,
                          status=CallStatus.en_curso, started_at=utcnow()))
            s.commit()
            return "ok"

    with ThreadPoolExecutor(attempts) as pool:
        codes = list(pool.map(call, range(attempts)))
    assert codes.count("ok") == 3
    assert set(codes) == {"ok", "platform_busy"}
    with pg() as s:
        assert quota.active_calls_global(s) == 3


# ---------- H14: reclamo atomico de un destinatario de campaña ----------

def test_reclamo_atomico_concurrente_de_campana(pg):
    w = make_wa(pg)
    cid = make_campaign(w, "5493515550001")
    rid = recipients(pg, cid)[0].id
    info = {"campaign_id": cid, "client_id": w.client_id}
    senders = [CampaignSender(pg, graph_factory=lambda token: None, hour=lambda: 12) for _ in range(8)]
    barrier = threading.Barrier(len(senders))

    def claim(sender):
        barrier.wait(LOCK_WAIT)
        return sender._claim(info, rid)

    with ThreadPoolExecutor(len(senders)) as pool:
        results = list(pool.map(claim, senders))
    winners = [r for r in results if not isinstance(r, str)]
    assert len(winners) == 1, results
    assert results.count("skipped") == len(senders) - 1
    r = recipients(pg, cid)[0]
    assert r.status == "sending" and r.claimed_at is not None


# ---------- H08: version optimista entre dos escritores ----------

def test_version_optimista_en_postgres(pg):
    ids = _seed(pg)
    store = ConversationStore(pg)
    with pg() as s:
        s.add(ConversationRow(id="conv-v", client_id=ids["c1"], agent_id=ids["a_c1"], agent_version=1,
                              status="active", fields={}, messages=[]))
        s.commit()
    first, second = store.get("conv-v"), store.get("conv-v")
    first.fields["nombre"] = "Ana"
    store.save(first)
    second.fields["nombre"] = "Beto"
    with pytest.raises(ConversationConflict):
        store.save(second)
    assert store.get("conv-v").fields == {"nombre": "Ana"}
