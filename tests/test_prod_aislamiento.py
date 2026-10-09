"""Aislamiento entre clientes y API para produccion: numeros con lock (H01), saliente sin
numero propio (H05), sesion de base corta (H07), turnos por texto solo en conversaciones
de texto y control optimista (H08), cliente inactivo en solo lectura y limites por
cliente (H12) e Idempotency-Key en POST /calls."""
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.config import settings
from app.conversation.models import AgentTurn
from app.conversation.store import ConversationConflict
from app.models import CallRow, ConversationRow, PhoneNumber
from app.services import calls as call_service
from app.services import phone_numbers as number_service
from app.services import tts
from app.services.errors import Conflict, Invalid, NotFound

from .test_api import (  # noqa: F401  (admin: fixture)
    V1,
    admin,
    client_user,
    make_agent,
    make_client,
    make_tier,
)

PHONE = "+5491155551234"


def _number(adm, client, e164="+541100000001", **extra):
    r = adm.post(f"{V1}/phone-numbers", json={"client_id": client["id"], "e164": e164, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _key(adm, client, name="crm"):
    r = adm.post(f"{V1}/clients/{client['id']}/api-keys", json={"name": name})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['key']}"}


# ---------- H01: numeros ----------

def test_route_number_rereads_client_under_lock(api, admin):  # noqa: F811
    """Intercalado: la sesion 1 lee el numero (de acme); la 2 lo libera y lo asigna a beta;
    la 1 rutea al agente de acme. Sin relectura con lock comparaba contra acme en memoria."""
    acme, beta = make_client(admin, "acme"), make_client(admin, "beta")
    agent_a = make_agent(admin, acme)
    n = _number(admin, acme)
    with api.sessions() as s1, api.sessions() as s2:
        stale = s1.get(PhoneNumber, n["id"])
        assert stale.client_id == acme["id"]

        other = s2.get(PhoneNumber, n["id"])
        number_service.release(s2, other)
        s2.commit()
        number_service.assign(s2, other, beta["id"])
        s2.commit()

        assert number_service.lock(s1, stale) is True       # cambio de cliente
        assert stale.client_id == beta["id"]
        with pytest.raises(Invalid):
            number_service.set_agent(s1, stale, agent_a["id"])
        s1.rollback()
    with api.sessions() as s:
        row = s.get(PhoneNumber, n["id"])
        assert (row.client_id, row.agent_id) == (beta["id"], None)


def test_release_conflicts_if_number_changed(api, admin):  # noqa: F811
    acme, beta = make_client(admin, "acme"), make_client(admin, "beta")
    n = _number(admin, acme)
    with api.sessions() as s1, api.sessions() as s2:
        stale = s1.get(PhoneNumber, n["id"])
        other = s2.get(PhoneNumber, n["id"])
        number_service.release(s2, other)
        number_service.assign(s2, other, beta["id"])
        s2.commit()
        # El admin queria liberar el de acme: no libera el de beta.
        with pytest.raises(Conflict) as e:
            number_service.release(s1, stale)
        assert e.value.code == "number_changed"
        s1.rollback()
    with api.sessions() as s:
        assert s.get(PhoneNumber, n["id"]).client_id == beta["id"]


def test_client_cannot_route_number_it_lost(api, admin):  # noqa: F811
    acme, beta = make_client(admin, "acme"), make_client(admin, "beta")
    mine = make_agent(admin, acme)
    n = _number(admin, acme)
    ana = client_user(api, admin, acme)
    admin.post(f"{V1}/phone-numbers/{n['id']}/release")
    admin.post(f"{V1}/phone-numbers/{n['id']}/assign", json={"client_id": beta["id"]})
    assert ana.patch(f"{V1}/phone-numbers/{n['id']}", json={"agent_id": mine["id"]}).status_code == 404
    with api.sessions() as s:
        assert s.get(PhoneNumber, n["id"]).agent_id is None


def test_inbound_rejects_agent_of_other_client(api, admin):  # noqa: F811
    acme, beta = make_client(admin, "acme"), make_client(admin, "beta")
    agent_b = make_agent(admin, beta)
    n = _number(admin, acme, e164="+541152630861")
    with api.sessions() as s:     # lo que la FK compuesta impide en PostgreSQL (SQLite no la tiene)
        s.get(PhoneNumber, n["id"]).agent_id = agent_b["id"]
        s.commit()
    with api.sessions() as s, pytest.raises(NotFound) as e:
        call_service.start_inbound(s, api.engine, "+541152630861", "+5491100000000")
    assert e.value.code == "number_agent_mismatch"
    with api.sessions() as s:
        assert s.scalar(select(CallRow)) is None and s.scalar(select(ConversationRow)) is None


def test_inbound_carries_tier_max_duration(api, admin):  # noqa: F811
    tier = make_tier(admin, name="Corto", max_call_duration_seconds=120)
    c = make_client(admin, tier=tier)
    agent = make_agent(admin, c)
    _number(admin, c, e164="+541152630861", agent_id=agent["id"])
    with api.sessions() as s:
        inbound = call_service.start_inbound(s, api.engine, "+541152630861", None)
    assert inbound.max_duration_seconds == 120


# ---------- H05: caller ID ----------

def test_outbound_without_own_number_is_409(api, admin):  # noqa: F811
    acme = make_client(admin)
    agent = make_agent(admin, acme)
    ana = client_user(api, admin, acme)
    r = ana.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE})
    assert r.status_code == 409 and r.json()["code"] == "no_caller_id"
    r = api.client.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE}, headers=_key(admin, acme))
    assert r.status_code == 409 and r.json()["code"] == "no_caller_id"
    assert api.dispatched == []
    with api.sessions() as s:     # no quedo nada a medias
        assert s.scalar(select(CallRow)) is None
    # La de prueba no necesita numero; el admin esta exento (sale con el DID de Atentina).
    assert ana.post(f"{V1}/calls", json={"agent_id": agent["id"]}).status_code == 201
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE}).status_code == 201


def test_outbound_with_own_number_persists_it(api, admin):  # noqa: F811
    acme = make_client(admin)
    agent = make_agent(admin, acme)
    first = _number(admin, acme, "+541100000001")
    second = _number(admin, acme, "+541100000002")
    ana = client_user(api, admin, acme)
    out = ana.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE, "from_number_id": second["id"]})
    assert out.status_code == 201, out.text
    assert api.dispatched[-1]["from_number"] == second["e164"]
    out2 = ana.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE}).json()
    assert api.dispatched[-1]["from_number"] == first["e164"]
    with api.sessions() as s:
        assert s.get(CallRow, out.json()["conversation_id"]).phone_number_id == second["id"]
        assert s.get(CallRow, out2["conversation_id"]).phone_number_id == first["id"]


def test_outbound_uses_tier_max_duration(api, admin):  # noqa: F811
    tier = make_tier(admin, name="Corto", max_call_duration_seconds=300)
    c = make_client(admin, tier=tier)
    agent = make_agent(admin, c)
    _number(admin, c)
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE}).status_code == 201
    assert api.dispatched[-1]["max_duration_seconds"] == 300


# ---------- Idempotency-Key ----------

def test_idempotency_key_returns_same_call(api, admin):  # noqa: F811
    acme, beta = make_client(admin, "acme"), make_client(admin, "beta")
    agent, agent_b = make_agent(admin, acme), make_agent(admin, beta)
    _number(admin, acme)
    h = {"Idempotency-Key": "pedido-42"}
    first = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": PHONE}, headers=h)
    again = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+54 9 11 5555-1234"}, headers=h)
    assert first.status_code == 201 and again.status_code == 200
    assert again.json()["conversation_id"] == first.json()["conversation_id"]
    assert len(api.dispatched) == 1
    # Misma clave para otra llamada: 409. Otro cliente con la misma clave: independiente.
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"], "phone": "+5491100000000"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "idempotency_key_reused"
    assert admin.post(f"{V1}/calls", json={"agent_id": agent_b["id"]}, headers=h).status_code == 201
    # La de prueba repetida devuelve su join_url.
    h2 = {"Idempotency-Key": "prueba-1"}
    t1 = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}, headers=h2).json()
    t2 = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}, headers=h2).json()
    assert t1 == t2 and t2["join_url"].endswith(t2["room"])
    # Sin clave, cada pedido es una llamada.
    assert admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()["conversation_id"] != t1["conversation_id"]


def test_idempotency_key_race_resolved_by_unique(api, admin, monkeypatch):  # noqa: F811
    """Dos pedidos a la vez: los dos pasan la busqueda y el segundo choca con el UNIQUE
    al guardar; devuelve la del primero y no despacha."""
    acme = make_client(admin)
    agent = make_agent(admin, acme)
    h = {"Idempotency-Key": "carrera"}
    first = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}, headers=h).json()
    real = call_service._replay
    calls = []

    def first_misses(*args, **kwargs):
        calls.append(1)
        return None if len(calls) == 1 else real(*args, **kwargs)

    monkeypatch.setattr(call_service, "_replay", first_misses)
    r = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}, headers=h)
    assert r.status_code == 200 and r.json()["conversation_id"] == first["conversation_id"]
    assert len(api.dispatched) == 1
    with api.sessions() as s:
        assert len(s.scalars(select(CallRow)).all()) == 1
        assert len(s.scalars(select(ConversationRow)).all()) == 1


# ---------- H08: turnos por texto ----------

def test_turn_rejected_on_call_or_completed_conversation(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    call = admin.post(f"{V1}/calls", json={"agent_id": agent["id"]}).json()
    r = admin.post(f"{V1}/conversations/{call['conversation_id']}/turns", json={"message": "Hola"})
    assert r.status_code == 409 and r.json()["code"] == "call_conversation"

    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    api.llm.turns = [AgentTurn(assistant_message="Chau", status="completed")]
    assert admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Listo"}).status_code == 200
    r = admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Otra cosa"})
    assert r.status_code == 409 and r.json()["code"] == "conversation_completed"


def test_turn_in_progress_and_conflict_are_409(api, admin, monkeypatch):  # noqa: F811
    from app.api.routers import conversations as router

    c = make_client(admin)
    agent = make_agent(admin, c)
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    router._in_progress.add(conv)
    try:
        r = admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Hola"})
        assert r.status_code == 409 and r.json()["code"] == "turn_in_progress"
    finally:
        router._in_progress.discard(conv)

    async def conflict(conversation_id, message, *a, **kw):
        raise ConversationConflict(conversation_id)

    monkeypatch.setattr(api.engine, "process_turn", conflict)
    r = admin.post(f"{V1}/conversations/{conv}/turns", json={"message": "Hola"})
    assert r.status_code == 409 and r.json()["code"] == "conversation_conflict"
    assert conv not in router._in_progress


def test_store_optimistic_version(api, admin):  # noqa: F811
    c = make_client(admin)
    agent = make_agent(admin, c)
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    store = api.engine.store
    a, b = store.get(conv), store.get(conv)
    assert a.version == b.version == 0
    a.fields["contact_name"] = "Ana"
    store.save(a)
    assert a.version == 1 and store.get(conv).version == 1
    b.fields["contact_name"] = "Beto"       # leido antes del guardado de `a`
    with pytest.raises(ConversationConflict):
        store.save(b)
    assert store.get(conv).fields["contact_name"] == "Ana"
    # Releido, guarda; dos guardados seguidos del mismo objeto tambien.
    fresh = store.get(conv)
    store.save(fresh)
    store.save(fresh)
    assert store.get(conv).version == 3


def test_engine_turns_keep_working_with_versions(api, admin):  # noqa: F811
    """El motor relee antes de guardar (turno y extraccion): no choca consigo mismo."""
    c = make_client(admin)
    agent = make_agent(admin, c)
    api.llm.turns = [AgentTurn(next_objective="company_name", assistant_message="¿Empresa?"),
                     AgentTurn(next_objective="company_activity", assistant_message="¿Rubro?")]
    api.llm.extractions = [{"contact_name": "Juan"}, {"company_name": "Acme"}]
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    for msg in ("Juan.", "Acme."):
        r = admin.post(f"{V1}/conversations/{conv}/turns", json={"message": msg})
        assert r.status_code == 200, r.text
    state = api.engine.store.get(conv)
    assert len(state.messages) == 5 and state.version >= 2


# ---------- H07: sesion corta ----------

def test_get_principal_leaves_no_open_transaction(api, admin):  # noqa: F811
    from starlette.requests import Request

    from app.api import deps

    c = make_client(admin)
    key = _key(admin, c)["Authorization"].split()[1]
    cookie = admin.cookies.get(deps.SESSION_COOKIE)
    for creds, cookies in ((HTTPAuthorizationCredentials(scheme="Bearer", credentials=key), ""),
                           (None, f"{deps.SESSION_COOKIE}={cookie}")):
        request = Request({"type": "http", "headers": [(b"cookie", cookies.encode())] if cookies else []})
        with api.sessions() as db:
            p = deps.get_principal(request, db, creds)
            assert p.id and not db.in_transaction()


# ---------- H12: cliente inactivo y limites por cliente ----------

def test_inactive_client_is_read_only(api, admin, monkeypatch):  # noqa: F811
    async def fake_preview(voice, text):
        async def stream():
            yield b"RIFF"
        return stream()

    monkeypatch.setattr(tts, "preview", fake_preview)
    c = make_client(admin)
    agent = make_agent(admin, c)
    conv = admin.post(f"{V1}/conversations", json={"agent_id": agent["id"]}).json()["conversation_id"]
    headers = _key(admin, c)
    admin.patch(f"{V1}/clients/{c['id']}", json={"active": False})

    ana = client_user(api, admin, c)       # entra igual (login permitido)
    for path in ("/calls", f"/conversations/{conv}", "/agents", f"/calls/{conv}"):
        assert ana.get(f"{V1}{path}").status_code == 200, path
    assert api.client.get(f"{V1}/calls", headers=headers).status_code == 200

    denied = [("POST", "/conversations", {"agent_id": agent["id"]}),
              ("POST", f"/conversations/{conv}/turns", {"message": "Hola"}),
              ("POST", "/tts/preview", {"voice": "sofia", "text": "Hola"}),
              ("POST", "/calls", {"agent_id": agent["id"]}),
              ("POST", f"/clients/{c['id']}/api-keys", {"name": "otra"})]
    for method, path, body in denied:
        r = ana.request(method, f"{V1}{path}", json=body)
        assert r.status_code == 403 and r.json()["code"] == "client_inactive", (path, r.text)
    r = api.client.post(f"{V1}/calls", json={"agent_id": agent["id"]}, headers=headers)
    assert r.status_code == 403 and r.json()["code"] == "client_inactive"
    # El admin tampoco le crea claves; sus llamadas las frena la admision (429, como antes).
    r = admin.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "otra"})
    assert r.status_code == 403 and r.json()["code"] == "client_inactive"


def test_rate_limits_are_per_client_not_per_key(api, admin, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "rate_conversations_per_hour", 1)
    c = make_client(admin)
    agent = make_agent(admin, c)
    k1, k2 = _key(admin, c, "a"), _key(admin, c, "b")
    body = {"agent_id": agent["id"]}
    assert api.client.post(f"{V1}/conversations", json=body, headers=k1).status_code == 201
    assert api.client.post(f"{V1}/conversations", json=body, headers=k2).status_code == 429
    # Otro cliente tiene su propio cupo.
    other = make_client(admin, "otro")
    assert api.client.post(f"{V1}/conversations", json={"agent_id": make_agent(admin, other)["id"]},
                           headers=_key(admin, other)).status_code == 201


def test_api_keys_capped_per_client(api, admin, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "max_api_keys_per_client", 2)
    c = make_client(admin)
    ana = client_user(api, admin, c)
    ids = [ana.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": f"k{i}"}).json()["id"] for i in range(2)]
    r = ana.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "k3"})
    assert r.status_code == 409 and r.json()["code"] == "api_keys_limit"
    ana.delete(f"{V1}/clients/{c['id']}/api-keys/{ids[0]}")      # las revocadas no cuentan
    assert ana.post(f"{V1}/clients/{c['id']}/api-keys", json={"name": "k3"}).status_code == 201


def test_tts_preview_global_concurrency(api, admin, monkeypatch):  # noqa: F811
    from app.api.routers import voices as router

    async def fake_preview(voice, text):
        async def stream():
            yield b"RIFF"
            yield b"data"
        return stream()

    monkeypatch.setattr(tts, "preview", fake_preview)
    body = {"voice": "sofia", "text": "Hola"}
    r = admin.post(f"{V1}/tts/preview", json=body)
    assert r.status_code == 200 and r.content == b"RIFFdata" and router._PreviewSlots.in_use == 0

    monkeypatch.setattr(router._PreviewSlots, "in_use", settings.tts_preview_max_concurrent)
    r = admin.post(f"{V1}/tts/preview", json=body)
    assert r.status_code == 503 and r.json()["code"] == "tts_busy" and int(r.headers["Retry-After"]) > 0
    monkeypatch.setattr(router._PreviewSlots, "in_use", 0)

    async def broken(voice, text):
        raise Invalid("Voz inexistente")

    monkeypatch.setattr(tts, "preview", broken)
    assert admin.post(f"{V1}/tts/preview", json=body).status_code == 422
    assert router._PreviewSlots.in_use == 0       # el cupo se devuelve aunque falle
