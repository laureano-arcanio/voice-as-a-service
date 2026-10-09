"""Produccion (revision del 7-oct-2026): WhatsApp durable (H03), tope de turnos (H04),
consumidor unico (H14), cliente inactivo (H12), redirecciones de media (extra d) y
/health/ready. El service se prueba directo con drain(), como en test_whatsapp_service.py."""
import asyncio
import datetime
import time

import httpx
import pytest
from sqlalchemy import select, update

from app.config import settings
from app.db import utcnow
from app.models import Client, WaCampaignRecipient, WaMessage
from app.services.leader import Leader, every
from app.whatsapp import store
from app.whatsapp.graph import GraphClient, GraphError
from app.whatsapp.sender import CampaignSender
from app.whatsapp.service import WhatsAppService

from .helpers import FakeLLM
from .test_api import V1
from .test_whatsapp_api import admin  # noqa: F401  (fixture)
from .test_whatsapp_campaigns import (  # noqa: F401
    account,
    campaign_body,
    make_campaign,
    recipients,
)
from .test_whatsapp_service import (
    PNID,
    SEND_TO,
    WA_ID,
    FakeGraph,
    conversations,
    make_wa,
    messages,
    reply,
    send,
    text_payload,
)
from .test_whatsapp_signup import acme, meta  # noqa: F401  (fixtures)


def fresh(body: str, wamid: str) -> dict:
    """Mensaje de ahora: dentro de la ventana de 24 h de Meta."""
    p = text_payload(body, wamid)
    p["entry"][0]["changes"][0]["value"]["messages"][0]["timestamp"] = str(int(time.time()))
    return p


def restart(w, llm=None) -> WhatsAppService:
    """Otro proceso: memoria vacia (inbox, held), la misma base."""
    if llm is not None:
        w.llm.turns.extend(llm)
    return WhatsAppService(w.engine, w.sessions, graph_factory=lambda token: w.graph, debounce_seconds=0.05,
                           session_hours=24)


def inbound(sessions, wamid) -> WaMessage:
    with sessions() as s:
        return s.scalar(select(WaMessage).where(WaMessage.wamid == wamid))


# ---------- H03: durable ----------

async def test_guarda_el_cuerpo_antes_de_procesar(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola")))
    batch = w.service.ingest(fresh("quiero un turno", "wamid.d1"))
    # Guardado y reclamado, sin tocar el loop: es lo que pasa antes del 200 a Meta.
    row = inbound(sessions, "wamid.d1")
    assert (row.status, row.attempts) == ("processing", 1)
    assert row.body["msg"]["text"]["body"] == "quiero un turno" and row.body["pnid"] == PNID
    assert [c.wamid for c in batch.claimed] == ["wamid.d1"]
    w.service.dispatch(batch)
    await w.service.drain()
    row = inbound(sessions, "wamid.d1")
    assert row.status == "answered" and row.body is None and row.processed_at is not None
    assert w.graph.sent == [(PNID, SEND_TO, "Hola")]


async def test_proceso_muerto_entre_guardar_y_procesar_se_recupera_al_arrancar(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola de nuevo")))
    w.service.ingest(fresh("hola", "wamid.k1"))      # reclamado y el proceso muere: nunca se agenda
    with sessions() as s:                            # y uno guardado que ni llego a reclamarse
        store.save_inbound(s, wamid="wamid.k2", account_id=w.account_id, wa_id=WA_ID, type="text", meta_ts=None,
                           body={"pnid": PNID, "contact_name": None,
                                 "msg": fresh("sigo", "x")["entry"][0]["changes"][0]["value"]["messages"][0]
                                 | {"id": "wamid.k2"}})
    service = restart(w)
    assert await service.recover() == 0             # todavia frescos: pueden ser de otro proceso vivo
    assert await service.recover(stale_seconds=0) == 2
    await service.drain()
    assert [c[0] for c in w.llm.calls] == ["hola\nsigo"]     # un turno, armado desde la base
    assert [b for _, _, b in w.graph.sent] == ["Hola de nuevo"]
    for wamid, attempts in (("wamid.k1", 2), ("wamid.k2", 1)):
        row = inbound(sessions, wamid)
        assert (row.status, row.attempts, row.body) == ("answered", attempts, None)
    assert await service.recover(stale_seconds=0) == 0       # idempotente


async def test_wamid_repetido_sin_procesar_no_se_descarta(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola")))
    msg = fresh("hola", "wamid.r1")
    with sessions() as s:       # fila de antes de la 0009: received y sin cuerpo (se perdia)
        s.add(WaMessage(wamid="wamid.r1", account_id=w.account_id, direction="in", wa_id=WA_ID, type="text",
                        status="received"))
        s.commit()
    await send(w, msg)          # Meta lo reenvia: completa el cuerpo y se procesa
    assert inbound(sessions, "wamid.r1").status == "answered" and len(w.graph.sent) == 1
    await send(w, msg)          # ya respondido: ahora si se descarta
    assert len(w.graph.sent) == 1 and len(w.llm.calls) == 1


async def test_recuperacion_no_toca_lo_que_este_proceso_tiene_en_memoria(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply("Hola")))
    w.service.debounce_seconds = 0.3                 # el turno espera el debounce
    w.service.handle_payload(fresh("hola", "wamid.h1"))
    await asyncio.sleep(0)
    assert await w.service.recover(stale_seconds=0) == 0     # reclamo viejo, pero lo tiene este proceso
    await w.service.drain()
    assert len(w.llm.calls) == 1 and inbound(sessions, "wamid.h1").status == "answered"


@pytest.mark.parametrize("case", ["enviando", "intentos", "viejo", "sin_cuerpo"])
async def test_recuperacion_que_no_reprocesa(sessions, caplog, case):
    w = make_wa(sessions, llm=FakeLLM(reply("no deberia salir")))
    w.service.ingest(fresh("hola", "wamid.x1"))
    values = {"enviando": {"processed_at": utcnow()},
              "intentos": {"attempts": settings.wa_max_attempts},
              "viejo": {"created_at": utcnow() - datetime.timedelta(hours=settings.wa_recovery_max_age_hours + 1)},
              "sin_cuerpo": {"body": None}}[case]
    with sessions() as s:
        s.execute(update(WaMessage).where(WaMessage.wamid == "wamid.x1").values(**values))
        s.commit()
    assert await restart(w).recover(stale_seconds=0) == 0
    row = inbound(sessions, "wamid.x1")
    assert row.status == "error" and "Sin procesar" in row.error["message"]
    assert w.graph.sent == [] and w.llm.calls == []          # nada se reenvia a ciegas
    assert "entrante sin procesar" in caplog.text and "hola" not in caplog.text


async def test_fallo_del_llm_responde_el_aviso_y_no_traba_el_contacto(sessions):
    w = make_wa(sessions, llm=FakeLLM())             # sin turnos: el LLM falla
    await send(w, fresh("hola", "wamid.e1"))
    assert [b for _, _, b in w.graph.sent] == [settings.wa_error_reply]
    row = inbound(sessions, "wamid.e1")
    assert row.status == "error" and "Fallo el turno" in row.error["message"]
    (conv,) = conversations(sessions)
    assert conv.messages == []                       # el turno fallido no quedo a medias
    w.llm.turns.append(reply("Ahora si"))
    await send(w, fresh("hola?", "wamid.e2"))         # el siguiente mensaje anda
    assert [b for _, _, b in w.graph.sent][-1] == "Ahora si"


async def test_fallo_del_llm_fuera_de_la_ventana_no_responde(sessions):
    w = make_wa(sessions, llm=FakeLLM())
    await send(w, text_payload("hola", "wamid.e3"))   # timestamp de Meta de hace semanas
    assert w.graph.sent == [] and inbound(sessions, "wamid.e3").status == "error"


async def test_falla_de_la_base_al_guardar_levanta(sessions, monkeypatch):
    """accept levanta y el webhook responde 500 (tests/test_whatsapp_webhook.py)."""
    w = make_wa(sessions)

    def boom(*a, **kw):
        raise RuntimeError("base caida")

    monkeypatch.setattr(store, "save_inbound", boom)
    with pytest.raises(RuntimeError):
        await w.service.accept(fresh("hola", "wamid.f1"))
    assert messages(sessions, direction="in") == []


async def test_status_y_eventos_siguen_en_el_loop(sessions):
    w = make_wa(sessions)
    p = text_payload("x", "wamid.s0")
    value = p["entry"][0]["changes"][0]["value"]
    del value["messages"]
    value["statuses"] = [{"id": "wamid.out9", "status": "delivered", "recipient_id": WA_ID}]
    await w.service.accept(p)
    await w.service.drain()
    (row,) = messages(sessions, direction="out")
    assert (row.wamid, row.status) == ("wamid.out9", "delivered")


# ---------- H04: tope de turnos simultaneos ----------

async def test_turnos_simultaneos_encolan(sessions):
    running, peak = 0, 0

    class SlowLLM(FakeLLM):
        async def converse(self, workflow, state, user_message, on_message=None):
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.05)
            running -= 1
            return await super().converse(workflow, state, user_message, on_message)

    w = make_wa(sessions, llm=SlowLLM(reply("a"), reply("b"), reply("c")))
    w.service = WhatsAppService(w.engine, sessions, graph_factory=lambda token: w.graph, debounce_seconds=0.01,
                                max_concurrent_turns=1)
    for i in range(3):
        p = fresh("hola", f"wamid.c{i}")
        p["entry"][0]["changes"][0]["value"]["messages"][0]["from"] = f"54935100000{i:02d}"
        w.service.handle_payload(p)
    await w.service.drain()
    assert peak == 1 and len(w.graph.sent) == 3      # ninguno respondio "ocupado"


# ---------- H12: cliente inactivo ----------

async def test_cliente_inactivo_no_consume_llm(sessions):
    w = make_wa(sessions, llm=FakeLLM(reply()))
    with sessions() as s:
        s.get(Client, w.client_id).active = False
        s.commit()
    await send(w, fresh("hola", "wamid.i1"))
    assert w.llm.calls == [] and w.graph.sent == []
    row = inbound(sessions, "wamid.i1")
    assert row.status == "ignored" and row.body is None


def test_cliente_inactivo_no_crea_ni_lanza_campanas(api, account):  # noqa: F811
    user, acc, c = account
    r = user.post(f"{V1}/whatsapp/campaigns", json=campaign_body(acc))
    assert r.status_code == 201, r.text
    cid = r.json()["campaign"]["id"]
    with api.sessions() as s:
        s.get(Client, c["id"]).active = False
        s.commit()
    for method, path, body in (("post", "/whatsapp/campaigns", campaign_body(acc)),
                               ("post", f"/whatsapp/campaigns/{cid}/start", None),
                               ("post", f"/whatsapp/campaigns/{cid}/recipients", {"csv": "telefono\n3515550001\n"}),
                               ("post", f"/whatsapp/accounts/{acc['id']}/templates",
                                {"name": "x", "language": "es_AR", "category": "MARKETING", "body": "Hola",
                                 "examples": []})):
        r = getattr(user, method)(f"{V1}{path}", json=body)
        assert (r.status_code, r.json()["code"]) == (403, "client_inactive"), path
    # Leer y frenar si.
    assert user.get(f"{V1}/whatsapp/campaigns/{cid}").status_code == 200
    assert user.post(f"{V1}/whatsapp/campaigns/{cid}/cancel").status_code == 200


# ---------- H14: sender con reclamo atomico ----------

class SlowCampaignGraph(FakeGraph):
    def __init__(self):
        super().__init__()
        self.templates = []

    async def send_template(self, pnid, to, name, language, params=None):
        await asyncio.sleep(0.01)       # dos senders se intercalan aca
        self.templates.append(to)
        return {"messages": [{"id": f"wamid.tpl{len(self.templates)}"}]}


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


async def test_dos_senders_no_mandan_el_mismo_contacto(sessions):
    w = make_wa(sessions, graph=SlowCampaignGraph())
    phones = [f"549351555{i:04d}" for i in range(4)]   # entran en la tanda de cada uno: compiten por todos
    cid = make_campaign(w, *phones, rate=60)
    a, b = (CampaignSender(sessions, graph_factory=lambda token: w.graph, hour=lambda: 12, clock=Clock())
            for _ in range(2))
    await asyncio.gather(a.tick(), b.tick())
    assert sorted(w.graph.templates) == sorted("54351555" + p[9:] for p in phones)   # una vez cada uno
    assert {r.status for r in recipients(sessions, cid)} == {"sent"}


async def test_reclamo_atomico_del_destinatario(sessions):
    w = make_wa(sessions, graph=SlowCampaignGraph())
    cid = make_campaign(w, WA_ID)
    rid = recipients(sessions, cid)[0].id
    sender = CampaignSender(sessions, graph_factory=lambda token: w.graph, hour=lambda: 12, clock=Clock())
    info = {"campaign_id": cid, "client_id": w.client_id}
    assert sender._claim(info, rid) == (WA_ID, ["Ana0"])
    assert sender._claim(info, rid) == "skipped"
    assert recipients(sessions, cid)[0].claimed_at is not None


async def test_recover_del_sender_no_invalida_envios_frescos(sessions):
    w = make_wa(sessions, graph=SlowCampaignGraph())
    cid = make_campaign(w, WA_ID, "5493515550001")
    fresh_id, old_id = (r.id for r in recipients(sessions, cid))
    with sessions() as s:
        s.execute(update(WaCampaignRecipient).where(WaCampaignRecipient.id == fresh_id)
                  .values(status="sending", claimed_at=utcnow()))
        s.execute(update(WaCampaignRecipient).where(WaCampaignRecipient.id == old_id)
                  .values(status="sending", claimed_at=utcnow() - datetime.timedelta(hours=1)))
        s.commit()
    sender = CampaignSender(sessions, graph_factory=lambda token: w.graph)
    assert sender.recover() == 1
    status = {r.id: r.status for r in recipients(sessions, cid)}
    assert status == {fresh_id: "sending", old_id: "failed"}


# ---------- H14: lider ----------

async def test_sqlite_siempre_es_lider(sessions):
    leader = Leader(sessions.kw["bind"])
    assert leader.is_leader and leader.try_acquire() and await leader.acquire()
    leader.release()
    assert leader.is_leader


async def test_every_solo_corre_en_el_lider():
    class NotLeader:
        is_leader = False

    runs = []

    async def fn():
        runs.append(1)

    task = asyncio.create_task(every(NotLeader(), 0.01, fn, "prueba", first_delay=0))
    await asyncio.sleep(0.05)
    assert runs == []
    leader = NotLeader()
    leader.is_leader = True
    task.cancel()
    task = asyncio.create_task(every(leader, 0.01, fn, "prueba", first_delay=0))
    await asyncio.sleep(0.05)
    task.cancel()
    assert runs


def test_lock_consultivo_en_postgres():
    import os

    from sqlalchemy import create_engine

    dsn = os.getenv("TEST_DB_DSN")
    if not dsn:
        pytest.skip("sin TEST_DB_DSN (PostgreSQL)")
    engine = create_engine(dsn)
    a, b = Leader(engine, key=987654321), Leader(engine, key=987654321)
    try:
        assert a.try_acquire() is True
        assert b.try_acquire() is False and not b.is_leader
        assert a.try_acquire() is True            # renovar: sigue siendo lider
        a.release()
        assert not a.is_leader
        assert b.try_acquire() is True
    finally:
        a.release()
        b.release()
        engine.dispose()


async def test_shutdown_espera_con_tope(sessions, monkeypatch):
    from app.whatsapp import service as service_module

    monkeypatch.setattr(service_module, "_service", None)
    await service_module.shutdown(timeout=0.01)       # sin servicio: no lo crea
    assert service_module._service is None
    w = make_wa(sessions)
    monkeypatch.setattr(service_module, "_service", w.service)
    w.service._spawn(asyncio.sleep(5))
    started = time.monotonic()
    await service_module.shutdown(timeout=0.05)
    assert time.monotonic() - started < 1


# ---------- extra d: redirecciones de media ----------

async def test_descarga_sigue_redirecciones_solo_dentro_de_meta():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, request.headers.get("authorization")))
        if request.url.host == "lookaside.fbsbx.com":
            return httpx.Response(302, headers={"location": "https://scontent.whatsapp.net/v/audio.ogg"})
        if request.url.host == "scontent.whatsapp.net":
            return httpx.Response(200, content=b"OggS")
        return httpx.Response(200, content=b"no deberia")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    graph = GraphClient("tok", http=http)
    assert await graph.download_media("https://lookaside.fbsbx.com/x", 1000) == b"OggS"
    assert [h for h, _ in seen] == ["lookaside.fbsbx.com", "scontent.whatsapp.net"]
    await http.aclose()


@pytest.mark.parametrize("location", ["https://evil.example.com/robo", "http://lookaside.fbsbx.com/x"])
async def test_redireccion_fuera_de_meta_no_lleva_el_token(location):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": location})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(GraphError, match="fuera de Meta"):
        await GraphClient("tok", http=http).download_media("https://lookaside.fbsbx.com/x", 1000)
    assert seen == ["https://lookaside.fbsbx.com/x"]
    await http.aclose()


async def test_demasiadas_redirecciones():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://lookaside.fbsbx.com/otra"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(GraphError, match="redirecciones"):
        await GraphClient("tok", http=http).download_media("https://lookaside.fbsbx.com/x", 1000)
    await http.aclose()


async def test_error_de_descarga_se_lee_con_tope():
    sent = 0

    async def body():
        nonlocal sent
        for _ in range(1000):           # 1000 x 1 KB: mas que MAX_ERROR_BYTES
            sent += 1024
            yield b"x" * 1024

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=body())

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(GraphError) as e:
        await GraphClient("tok", http=http).download_media("https://lookaside.fbsbx.com/x", 10_000_000)
    assert e.value.status == 500 and sent < 200 * 1024
    await http.aclose()


# ---------- /health/ready ----------

def _local(api):
    """/health/ready solo responde a pares locales (app/main.py, _local_only)."""
    from fastapi.testclient import TestClient

    return TestClient(api.app, client=("127.0.0.1", 50000))


def test_health_ready(api):
    r = _local(api).get("/health/ready")
    assert r.status_code == 200 and r.json()["ok"] is True and r.json()["checks"]["db"] == "ok"
    assert isinstance(r.json()["checks"]["leader"], bool)
    assert api.client.get("/health").json() == {"ok": True}


def test_health_ready_sin_base(api):
    from app.api import deps

    class Broken:
        def execute(self, *a, **kw):
            raise ConnectionError("db caida")

    api.app.dependency_overrides[deps.get_db] = lambda: Broken()
    r = _local(api).get("/health/ready")
    assert r.status_code == 503 and r.json()["checks"]["db"] == "error: ConnectionError"
