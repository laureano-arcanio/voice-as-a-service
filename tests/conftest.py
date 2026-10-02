import os

# Antes de importar app: la API no arranca sin AUTH_SECRET, y con cookies Secure el
# TestClient (http://testserver) no las devolveria.
os.environ.setdefault("AUTH_SECRET", "test-secret-" + "x" * 32)
os.environ["AUTH_COOKIE_SECURE"] = "false"
# Los tests no dependen del .env del host: la demo arranca apagada (la prende el fixture).
os.environ["TURNSTILE_SECRET_KEY"] = ""
# El default `gateway` depende de donde corren (contenedor o host): fijo el de compose.
os.environ["TRUSTED_PROXY_CIDRS"] = "127.0.0.1/32,::1/128,172.24.0.1/32"

import pytest

from app.agents.templates import load_template
from app.conversation.store import ConversationStore
from app.db import Base


@pytest.fixture
def workflow():
    return load_template("sales_discovery")


@pytest.fixture
def store(tmp_path):
    """SQLite por defecto. Con TEST_DB_DSN (ej. postgresql+psycopg://u:p@host/db) corre
    contra esa base, con el esquema recreado en cada test."""
    dsn = os.getenv("TEST_DB_DSN")
    if not dsn:
        yield ConversationStore.for_dsn(f"sqlite:///{tmp_path}/conversations.db")
        return
    s = ConversationStore.for_dsn(dsn)
    engine = s.sessions.kw["bind"]
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield s
    engine.dispose()


@pytest.fixture
def sessions(tmp_path):
    """sessionmaker contra un SQLite nuevo con todo el esquema."""
    from app.db import create_schema, make_engine, make_sessions

    engine = make_engine(f"sqlite:///{tmp_path}/app.db")
    create_schema(engine)
    yield make_sessions(engine)
    engine.dispose()


@pytest.fixture
def api(sessions, monkeypatch):
    """App con la base de `sessions`, un motor con FakeLLM y LiveKit simulado.

    api.client: TestClient sin sesion. api.login(email, clave) -> TestClient con la cookie.
    api.dispatched: metadata de cada despacho a LiveKit.
    """
    from fastapi.testclient import TestClient

    from app.agents.definitions import DbDefinitions
    from app.api import deps
    from app.conversation.engine import ConversationEngine
    from app.conversation.store import ConversationStore
    from app.main import app
    from app.services import livekit

    from .helpers import FakeLLM

    deps.api_limiter.reset()

    class Api:
        pass

    a = Api()
    a.sessions = sessions
    a.llm = FakeLLM()
    a.engine = ConversationEngine(a.llm, ConversationStore(sessions), DbDefinitions(sessions))
    a.dispatched = []

    async def fake_dispatch(room, metadata):
        a.dispatched.append(metadata)

    monkeypatch.setattr(livekit, "dispatch_call", fake_dispatch)
    monkeypatch.setattr(livekit, "build_test_join_url", lambda room: f"https://meet.example/{room}")

    def get_db():
        with sessions() as s:
            yield s

    app.dependency_overrides[deps.get_db] = get_db
    app.dependency_overrides[deps.get_conversation_engine] = lambda: a.engine
    a.app = app
    a.client = TestClient(app)

    def login(email, password):
        c = TestClient(app)
        r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return c

    a.login = login
    yield a
    app.dependency_overrides.clear()
