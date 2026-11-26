import os

# Antes de importar app: la API no arranca sin AUTH_SECRET, y con cookies Secure el
# TestClient (http://testserver) no las devolveria.
os.environ.setdefault("AUTH_SECRET", "test-secret-" + "x" * 32)
os.environ["AUTH_COOKIE_SECURE"] = "false"
# Los tests no dependen del .env del host: la demo arranca apagada (la prende el fixture).
os.environ["TURNSTILE_SECRET_KEY"] = ""
# Ni mails reales: sin clave de Resend el formulario de contacto solo guarda (la prende el fixture).
os.environ["RESEND_API_KEY"] = ""
os.environ["CONTACT_TO"] = ""
# Ni Mercado Pago (los tests de cobro con tarjeta lo prenden con un MP falso).
for _name in ("MP_BILLING_ACCESS_TOKEN", "MP_BILLING_PUBLIC_KEY", "MP_BILLING_WEBHOOK_SECRET",
              "MP_BILLING_TEST_PAYER_EMAIL"):
    os.environ[_name] = ""
# El default `gateway` depende de donde corren (contenedor o host): fijo el de compose.
os.environ["TRUSTED_PROXY_CIDRS"] = "127.0.0.1/32,::1/128,172.24.0.1/32"
# La CSP del .env local puede estar en Report-Only (primer deploy): los tests prueban la que bloquea.
os.environ["CSP_REPORT_ONLY"] = "false"
# Ni los trunks SIP del LiveKit del host (cargar numeros los sincroniza; app/services/livekit.py).
os.environ["LIVEKIT_SIP_SYNC"] = "false"

import shutil

import pytest

from app.agents.templates import load_reference
from app.conversation.store import ConversationStore
from app.db import Base

# El setup por test era el 72 % del tiempo de la suite (medido con --durations=0: setup
# 704 s de 977). Dos causas, atajadas aca sin tocar app/ (lo usan scripts y produccion):
# - create_schema (51 tablas) en un SQLite nuevo por test: ~260 ms. El esquema se crea
#   una vez por proceso en una plantilla y cada test arranca de una copia (`shutil.copyfile`).
# - argon2 con los parametros de produccion: ~45 ms por hash y por verificacion. En tests
#   alcanza con los parametros minimos (solo tests; produccion usa PasswordHasher()).


@pytest.fixture(scope="session")
def _esquema_tpl(tmp_path_factory):
    """Plantilla SQLite con todo el esquema, creada una vez por proceso de pytest. Con
    xdist cada worker arma la suya. Nadie escribe en ella: se copia por test."""
    from app.db import create_schema, make_engine

    ruta = tmp_path_factory.mktemp("esquema") / "schema.db"
    engine = make_engine(f"sqlite:///{ruta}")
    create_schema(engine)
    engine.dispose()
    return ruta


@pytest.fixture(autouse=True, scope="session")
def _argon2_barato():
    """Hasher de argon2 con parametros minimos para toda la sesion; al final vuelve el real."""
    from argon2 import PasswordHasher

    from app.services import security

    real = security._hasher
    security._hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    yield
    security._hasher = real


def sqlite_fresco(ruta, tpl):
    """Engine sobre una copia fresca de la plantilla del esquema (la plantilla vive en
    tmp_path_factory, una por proceso de pytest)."""
    from app.db import make_engine

    shutil.copyfile(tpl, ruta)
    return make_engine(f"sqlite:///{ruta}")


@pytest.fixture(autouse=True)
def _api_content_dir(tmp_path, monkeypatch):
    """El contenido de la API de inferencia que guardan los tests va a un directorio temporal, nunca a storage/."""
    from app.config import settings
    from app.services import api_content
    monkeypatch.setattr(settings, "call_recordings_dir", tmp_path / "recordings")
    monkeypatch.setattr(api_content, "_room", (0.0, True))
    monkeypatch.setattr(settings, "api_content_min_free_gb", 0)


@pytest.fixture(autouse=True)
def _sin_red_de_openrouter(monkeypatch):
    """Los avisos del modelo (app/services/llm_warnings.py) piden el catalogo publico de OpenRouter al validar y
    guardar: en tests, siempre 'unknown' (sin aviso). Cada test lo pisa si necesita otro resultado."""
    from app.services import llm_warnings

    async def unknown(model: str) -> str:
        return "unknown"

    monkeypatch.setattr(llm_warnings, "model_status", unknown)


@pytest.fixture
def workflow():
    return load_reference("sales_discovery")


@pytest.fixture
def store(tmp_path, _esquema_tpl):
    """SQLite por defecto: copia de la plantilla del esquema (sin `for_dsn`, que vuelve a
    correr create_all). Con TEST_DB_DSN (ej. postgresql+psycopg://u:p@host/db) corre
    contra esa base, con el esquema recreado en cada test."""
    from app.db import make_sessions

    dsn = os.getenv("TEST_DB_DSN")
    if not dsn:
        engine = sqlite_fresco(tmp_path / "conversations.db", _esquema_tpl)
        yield ConversationStore(make_sessions(engine))
        engine.dispose()
        return
    s = ConversationStore.for_dsn(dsn)
    engine = s.sessions.kw["bind"]
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield s
    engine.dispose()


@pytest.fixture
def sessions(tmp_path, _esquema_tpl):
    """sessionmaker contra un SQLite nuevo con todo el esquema (copia de la plantilla)."""
    from app.db import make_sessions

    engine = sqlite_fresco(tmp_path / "app.db", _esquema_tpl)
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
    # El de WhatsApp sobre la misma base y el mismo motor (el real usa la base del .env).
    from app.whatsapp.service import WhatsAppService, get_service
    a.wa_service = WhatsAppService(a.engine, sessions, graph_factory=lambda token: None)
    app.dependency_overrides[get_service] = lambda: a.wa_service
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
